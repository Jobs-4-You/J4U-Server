from flask import Flask, request, abort, jsonify, redirect
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity, get_current_user
from flask_cors import CORS
from flask_mail import Mail, Message
from database.database import init_db, db_session
from database.models import User
from recom import recom
from qualtrics import get_vars
from config import get_config
from itsdangerous import URLSafeTimedSerializer
from tracking import track_login, track_recommendation, track_inapp
from logdb.database import init_logdb

app = Flask('J4U-Server')
app.secret_key = 'super secret key'
app.salt = 'super salt key'
app.config['JWT_SECRET_KEY'] = 'super-secret'  # Change this!
CORS(app)

app.config.update(dict(
    MAIL_SUPPRESS_SEND = False,
    TESTING = False,
    MAIL_DEBUG = True,
    MAIL_USE_SSL = True,
    MAIL_SERVER = 'smtp.unil.ch',
    MAIL_PORT = 465,
    MAIL_USERNAME = 'jvaubien',
    MAIL_PASSWORD = 'alimonboss74!',
))

mail = Mail(app)

jwt = JWTManager(app)

def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(app.secret_key)
    token = serializer.dumps(email, salt=app.salt)
    url = '{}/verify?token={}'.format(get_config()['url'], token)
    return url

def confirm_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(app.secret_key)
    try:
        email = serializer.loads(
            token,
            salt=app.salt,
            max_age=expiration
        )
    except:
        return False
    return email

def row2dict(row):
    d = {}
    for column in row.__table__.columns:
        d[column.name] = getattr(row, column.name)

    return d



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
        return redirect('{}/#/verified'.format(get_config()['app_url']), code=302)

        return jsonify(success=True)

    return jsonify({"msg": "error"}), 400


@app.route('/login', methods=['POST'])
def login():
    if not request.is_json:
        return jsonify({"msg": "Missing JSON in request"}), 400

    email = request.json.get('email', None)
    password = request.json.get('password', None)
    if not email:
        return jsonify({"msg": "Missing username parameter"}), 400
    if not password:
        return jsonify({"msg": "Missing password parameter"}), 400

    user = User.query.filter_by(email=email).first()

    if user and user.check_password(password):
        track_login(user.email)
        # Identity can be any data that is json serializable
        access_token = create_access_token(identity=user.id)
        payload = row2dict(user)
        payload['access_token'] = access_token
        return jsonify(payload), 200
    else:
        return jsonify({"msg": "Missing password parameter"}), 400


@app.route('/signup', methods=['POST'])
def signup():
    form = request.json
    print(form)
    new_user = User(
        firstName=form['firstName'],
        lastName=form['lastName'],
        email=form['email'],
        phone=form['phone'],
        plastaId=form['plastaId'],
        pwd=form['password'])
    db_session.add(new_user)
    db_session.commit()

    # Send a verification mail
    url_conf = generate_confirmation_token(form['email'])
    msg = Message('J4U: activate your account:',
        sender='jvaubien@unil.ch',
        recipients=[form['email']])
    msg.html = '<a href="{}">Click here to confirm your email address</a>'.format(url_conf)
    mail.send(msg)
    return jsonify(success=True)


@app.route('/recom', methods=['POST'])
@jwt_required
def recomend():
    # Abilities values
    current_user = get_current_user()
    survey_id = current_user.surveyId

    data = request.json
    print(data)
    params = get_vars(survey_id) + [
        float(data.get('alpha')),
        data.get('oldJobValue'),
        float(data.get('beta'))
    ]
    res = recom(*params)
    track_recommendation(params[-3], params[-2], params[-1])
    return jsonify(res)


@app.route('/track', methods=['POST'])
@jwt_required
def track():
    obj = request.json
    track_inapp(obj)
    return jsonify(success=True)


if __name__ == "__main__":
    init_db()
    init_logdb()
    app.run(host=get_config()['host'], port=get_config()['port'])
