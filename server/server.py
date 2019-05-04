import json
import datetime
import sqlalchemy
from sqlalchemy import create_engine
from flask import Flask, request, abort, jsonify, redirect
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, create_refresh_token, get_jwt_identity, get_current_user
from flask_cors import CORS
from flask_mail import Mail, Message
from database.database import init_db, db_session
from database.models import User
from recom import recom
from qualtrics import retrieve_all, get_vars
from config import get_config
from itsdangerous import URLSafeTimedSerializer
from tracking import track_login, track_recommendation, track_inapp
from logdb.database import init_logdb
from fuzz import search
from decorators import validate_json, validate_schema
from validators import login_schema, signup_schema
import traceback
from waitress import serve
import requests
import mysql
import sys

app = Flask('J4U-Server')
app.secret_key = get_config()['app_key']
app.salt = get_config()['salt']
app.config['JWT_SECRET_KEY'] = get_config()['jwt_key']  # Change this!
CORS(app)

app.config.update(
    dict(
        MAIL_SUPPRESS_SEND=False,
        TESTING=False,
        MAIL_DEBUG=True,
        MAIL_USE_SSL=True,
        MAIL_SERVER='smtp.unil.ch',
        MAIL_PORT=465,
        MAIL_USERNAME=get_config()['email_user'],
        MAIL_PASSWORD=get_config()['email_pwd'],
    ))

mail = Mail(app)

jwt = JWTManager(app)


def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(app.secret_key)
    token = serializer.dumps(email, salt=app.salt)
    url = '{}/verify?token={}'.format(get_config()['url'], token)
    return url

def generate_reset_token(email):
    serializer = URLSafeTimedSerializer(app.secret_key)
    token = serializer.dumps(email, salt=app.salt)
    url = '{}/#/reset?token={}'.format(get_config()['app_url'], token)
    return url


def confirm_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(app.secret_key)
    try:
        email = serializer.loads(token, salt=app.salt, max_age=expiration)
    except:
        return False
    return email


def row2dict(row):
    d = {}
    for column in row.__table__.columns:
        d[column.name] = getattr(row, column.name)

    return d


@app.errorhandler(Exception)
def handle_invalid_usage(error):
    print(error)
    traceback.print_exc()
    response = jsonify(msg='Une erreur est survenue. Veuillez réessayer.')
    response.status_code = 500
    return response


@jwt.user_loader_callback_loader
def user_loader_callback(identity):
    return User.query.get(identity)


@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()


@app.route('/verify', methods=['GET'])
def verify():
    token = request.args.get('token')
    email = confirm_token(token)
    if email:
        user = User.query.filter_by(email=email).first()
        user.verified = True
        db_session.commit()
        return redirect(
            '{}/#/verified'.format(get_config()['app_url']), code=302)

        return jsonify(success=True)

    return jsonify({"msg": "error"}), 400

@app.route('/resetpassword', methods=['POST'])
def reset_password():
    token = request.json.get('token', None)
    email = confirm_token(token)
    password = request.json.get('password', None)
    if password and token and email:
        user = User.query.filter_by(email=email).first()
        user.set_password(password)
        db_session.commit()
        return jsonify(success=True)

    return jsonify({"msg": "error"}), 400

@app.route('/sendverification', methods=['GET'])
@jwt_required
def send_verification():
    # Send a verification mail
    current_user = get_current_user()
    url_conf = generate_confirmation_token(current_user.email)
    msg = Message(
        'J4U: Activation de compte :',
        sender='j4u@unil.ch',
        recipients=[current_user.email])
    msg.html = '<a href="{}">Cliquez ici pour confirmer votre adresse email</a>'.format(
        url_conf)
    mail.send(msg)
    return jsonify(success=True)

@app.route('/resetpasswordmail', methods=['GET'])
def reset_password_mail():
    # Send a verification mail
    email = request.args.get('email')
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"msg": "Le compte n'existe pas"}), 400
    url_conf = generate_reset_token(email)
    msg = Message(
        'J4U: Réinitialisation du mot de passe. Veuillez cliquer sur le lien et suivre les instructions',
        sender='j4u@unil.ch',
        recipients=[email])
    msg.html = '<a href="{}">Réinitialiser</a>'.format(
        url_conf)
    mail.send(msg)
    return jsonify(success=True)


@app.route('/login', methods=['POST'])
@validate_json
@validate_schema(login_schema)
def login():
    if not request.is_json:
        return jsonify({"msg": "Paramètre JSON manquant"}), 400

    email = request.json.get('email', None)
    password = request.json.get('password', None)
    if not email:
        return jsonify({"msg": "Paramètre d'utilisateur manquant"}), 400
    if not password:
        return jsonify({"msg": "Paramètre du mot-de-passe manquant"}), 400

    user = User.query.filter_by(email=email).first()

    if user and user.check_password(password):
        track_login(user.email)
        # Identity can be any data that is json serializable
        access_token = create_access_token(
            identity=user.id, expires_delta=datetime.timedelta(0, 60 * 3600))
        refresh_token = create_refresh_token(identity=user.id)
        payload = row2dict(user)
        payload['accessToken'] = access_token
        payload['refreshToken'] = access_token
        del payload['pwd_hash']
        return jsonify(payload), 200
    else:
        return jsonify({"msg": "Email ou mot-de-passe incorrect."}), 400


@app.route('/signup', methods=['POST'])
@validate_json
@validate_schema(signup_schema)
def signup():
    form = request.json
    new_user = User(
        firstName=form['firstName'],
        lastName=form['lastName'],
        birthDate=form['birthDate'],
        email=form['email'],
        phone=form['phone'],
        plastaId=form['plastaId'],
        pwd=form['password'],
        group=form['group'])
    try:
        db_session.add(new_user)
        db_session.commit()
    except sqlalchemy.exc.IntegrityError as err:
        duplicated_key = err.orig.msg.split("'")[-2]
        return jsonify({"msg": "{} est déja utilisée. Si vous avez déja un compte et oublié votre mot de passe, cliquer sur 'Renvoi du mot de passe' sur la page de login".format(duplicated_key)}), 422

    # Send a verification mail
    url_conf = generate_confirmation_token(form['email'])
    msg = Message(
        'J4U: Activation de compte :',
        sender='j4u@unil.ch',
        recipients=[form['email']])
    msg.html = '<a href="{}">Cliquez ici pour confirmer votre adresse email</a>'.format(
        url_conf)
    mail.send(msg)
    return jsonify(success=True)

@app.route('/update', methods=['POST'])
@validate_json
@jwt_required
def update():
    form = request.json
    current_user = get_current_user()
    current_user.firstName=form['firstName']
    current_user.lastName=form['lastName']
    current_user.birthDate=form['birthDate']
    current_user.email=form['email']
    current_user.phone=form['phone']
    current_user.plastaId=form['plastaId']
    db_session.add(current_user)
    db_session.commit()
    return jsonify(success=True)


@app.route('/recom', methods=['POST'])
@jwt_required
def recomend():
    # Abilities values
    data = request.json

    current_user = get_current_user()
    current_user.alpha = float(data.get('alpha'))
    current_user.beta = float(data.get('beta'))
    current_user.oldJobValue = int(data.get('oldJobValue'))
    current_user.oldJobLabel = (data.get('oldJobLabel'))
    locationValue = (data.get('locationValue'))
    db_session.commit()

    survey_id = current_user.surveyId

    params = get_vars(current_user) + [
        current_user.alpha, current_user.oldJobValue, current_user.beta
    ]
    res = recom(*params)
    track_recommendation(params[-3], params[-2], params[-1], locationValue)

    return jsonify(res)


@app.route('/track', methods=['POST'])
@jwt_required
def track():
    obj = request.json
    track_inapp(obj)
    return jsonify(success=True)


@app.route('/jobprops', methods=['GET'])
@jwt_required
def job_props():
    current_user = get_current_user()
    job = request.args.get('job')
    if not job:
        job = ''
    res = search(job)
    return jsonify(res)


@app.route('/link', methods=['GET'])
@jwt_required
def link():
    current_user = get_current_user()

    valid = retrieve_all(current_user.surveyId)

    if valid:
        return jsonify(success=True)

    return jsonify(success=False)

@app.route('/linkqualitrics', methods=['GET'])
def linkqualitrics():
    surveyId = request.args.get('surveyId')
    valid = retrieve_all(surveyId)

    if valid:
        environmentUrl = "http://localhost:8080" if get_config()['app_url'] == "http://127.0.0.1:8080" else get_config()['app_url']
        return redirect('{}/#/logout'.format(environmentUrl), code=302)
    return jsonify(success=False)


@app.route('/positions', methods=['POST'])
@jwt_required
def positions():
    data = request.json
    job = request.args.get('avam')
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'Postman-Token': 'a22088d4-4d7f-4d72-b14d-bceb48ef23db',
        'X-Requested-With': 'XMLHttpRequest',
        'cache-control': 'no-cache',
    }
    # SECO's JobRoom starts pagination from 0, but our pagination component matches page number and navigation items, so we need to decrease its number by one
    params = (
        ('page', int(data['currentPage'])-1),
        ('size', '10'),
        ('sort', 'score'),
    )

    if data['cantonCodes'] == [""] :
        data['cantonCodes'] = []

    data = {
        "permanent": None,
        "workloadPercentageMin": 0,
        "workloadPercentageMax": 100,
        "onlineSince": 30,
        "displayRestricted": False,
        "keywords": [],
        "professionCodes": data['codes'],
        "communalCodes": [],
        "cantonCodes": data['cantonCodes']
    }
    response = requests.post(
        'https://www.job-room.ch/jobadservice/api/jobAdvertisements/_search',
        headers=headers,
        params=params,
        data=json.dumps(data))
    res = response.json()
    res = {'totalCount': response.headers['X-Total-Count'], 'positions': res}

    return jsonify(res)

@app.route('/locations', methods=['GET'])
@jwt_required
def locations():
    loc = request.args.get('loc')
    if not loc:
        loc = ''

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'Postman-Token': 'a22088d4-4d7f-4d72-b14d-bceb48ef23db',
        'X-Requested-With': 'XMLHttpRequest',
        'cache-control': 'no-cache',
        'Cookie': '_ga=GA1.2.8377990.1544699425; _jr2.ID=18287a4d-86fc-49de-870a-c342698fa58d; NG_TRANSLATE_LANG_KEY=fr; JSESSIONID=_5VkSYRAG01H_nZ3MkazegLbfhdDJwm3tqiBRAQ-; _gid=GA1.2.1508386193.1554111736'
    }

    # SECO's JobRoom starts pagination from 0, but our pagination component matches page number and navigation items, so we need to decrease its number by one
    params = (
        ('prefix', loc),
        ('resultSize', '10'),
        ('distinctByLocalityCity', 'true'),
        ('_ng','ZnI=')
    )

    response = requests.post(
    'https://www.job-room.ch/referenceservice/api/_search/localities',
    headers=headers,
    params=params)


    res = response.json()

    return jsonify(res)

@app.route('/userinfos', methods=['GET'])
@jwt_required
def user_infos():
    current_user = get_current_user()
    res = row2dict(current_user)
    return jsonify(res)

@app.route('/updategroup', methods=['POST'])
@validate_json
def updategroup():
    admin_password = get_config()['admin_pword']
    password = request.json['password']
    field = request.json['field']
    value = request.json['value']
    group = request.json['group']
    if password and field and value and group:
        if password == admin_password :
            engine = create_engine(
                'mysql+mysqlconnector://root:my-secret-pw@127.0.0.1/j4u', convert_unicode=True, pool_recycle=600)
            # Temporarily turning off safe updates as group is not a key column
            update_query = """UPDATE `j4u`.`user`
                    SET `{}` = '{}' 
                    WHERE (`group` = '{}')""".format(field,value,group)
            select_query = "SELECT * FROM j4u.user WHERE `group` = '{}'".format(group)

            with engine.connect() as con:
                con.execute(update_query)
                response = con.execute(select_query)
                con.close()
            res = jsonify({'response': [dict(row) for row in response]})
            res.headers['Access-Control-Allow-Origin'] = '*'
            return res
        else :
            return jsonify({"response": "wrong password"}), 400
    return jsonify({"response": "error"}), 400

if __name__ == "__main__":
    init_db()
    init_logdb()
    #app.run(host=get_config()['host'], port=get_config()['port'])
    serve(app, host=get_config()['host'], port=get_config()['port'])
