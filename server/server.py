import json
import datetime
import sqlalchemy
import pandas as pd
from sqlalchemy import create_engine
from flask import (
    Flask,
    Response,
    request,
    abort,
    jsonify,
    redirect,
    send_file,
    render_template,
)
from flask_jwt_extended import (
    JWTManager,
    jwt_required,
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    get_current_user,
)
from flask_cors import CORS
from flask_mail import Mail, Message
from database.database import init_db, db_session
from database.models import User
from recom import recom
from qualtrics import retrieve_all, get_vars
from config import get_config
from itsdangerous import URLSafeTimedSerializer
from tracking import track_login, track_recommendation, track_inapp
from logdb.database import init_logdb, activities
from fuzz import search
from decorators import validate_json, validate_schema
from validators import login_schema, signup_schema
import traceback
from waitress import serve
import requests
import mysql
import sys
from weasyprint import HTML
import os

app = Flask("J4U-Server")
app.secret_key = get_config()["app_key"]
app.salt = get_config()["salt"]
app.config["JWT_SECRET_KEY"] = get_config()["jwt_key"]  # Change this!
CORS(app)


app.config.update(
    dict(
        MAIL_SUPPRESS_SEND=False,
        TESTING=False,
        MAIL_DEBUG=True,
        #MAIL_USE_SSL=True,
        MAIL_USE_TLS=True,
        MAIL_SERVER="smtp.unil.ch",
        #MAIL_PORT=465,
        MAIL_PORT=587,
        MAIL_USERNAME=get_config()["email_user"],
        MAIL_PASSWORD=get_config()["email_pwd"],
    )
)

mail = Mail(app)
# with mail.connect() as conn:
#    print(conn)


jwt = JWTManager(app)


def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(app.secret_key)
    token = serializer.dumps(email, salt=app.salt)
    url = "{}/verify?token={}".format(get_config()["url"], token)
    return url


def generate_reset_token(email):
    serializer = URLSafeTimedSerializer(app.secret_key)
    token = serializer.dumps(email, salt=app.salt)
    url = "{}/#/reset?token={}".format(get_config()["app_url"], token)
    return url


def confirm_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(app.secret_key)
    try:
        email = serializer.loads(token, salt=app.salt, max_age=expiration)
    except:
        return False
    return email


def generate_validity_token(date, group):
    serializer = URLSafeTimedSerializer(app.secret_key)
    obj = {"date": date, "group": group}
    token = serializer.dumps(obj, salt=app.salt)
    return token


def confirm_validity_token(token):
    serializer = URLSafeTimedSerializer(app.secret_key)
    try:
        obj = serializer.loads(token, salt=app.salt)
        date = obj["date"]
        current = datetime.date.today()
        date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        delta = date - current
        if delta.days < 0:
            return False
        else:
            return obj
    except:
        return False


def row2dict(row):
    d = {}
    for column in row.__table__.columns:
        d[column.name] = getattr(row, column.name)

    return d


@app.errorhandler(Exception)
def handle_invalid_usage(error):
    print(error)
    traceback.print_exc()
    response = jsonify(msg="Une erreur est survenue. Veuillez réessayer.")
    response.status_code = 500
    return response


@jwt.user_loader_callback_loader
def user_loader_callback(identity):
    return User.query.get(identity)


@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()


@app.route("/verify", methods=["GET"])
def verify():
    token = request.args.get("token")
    email = confirm_token(token, expiration=3600 * 24)
    if email:
        user = User.query.filter_by(email=email).first()
        user.verified = True
        db_session.commit()
        return redirect("{}/#/verified".format(get_config()["app_url"]), code=302)

        return jsonify(success=True)

    return jsonify({"msg": "error"}), 400


@app.route("/resetpassword", methods=["POST"])
def reset_password():
    token = request.json.get("token", None)
    email = confirm_token(token)
    password = request.json.get("password", None)
    if password and token and email:
        user = User.query.filter_by(email=email).first()
        user.set_password(password)
        db_session.commit()
        return jsonify(success=True)

    return jsonify({"msg": "error"}), 400


@app.route("/sendverification", methods=["GET"])
@jwt_required
def send_verification():
    # Send a verification mail
    current_user = get_current_user()
    url_conf = generate_confirmation_token(current_user.email)
    msg = Message(
        "Validation de votre inscription à J4U",
        sender="j4u@unil.ch",
        recipients=[current_user.email],
    )
    msg.html = """
                <p>
                Bonjour,
                </p>
                <p>
                Nous vous remercions pour votre participation au projet « Job For You » (J4U).
                </p>
                <p>
                Suite à votre inscription, voici un email de confirmation. Afin de valider votre compte, il vous suffit de cliquer sur le lien suivant (qui n’est actif que quelques jours) :
                </p>
                <p>
                <a href="{}">Cliquez ici pour confirmer votre adresse email</a>
                </p>
                <p>
                L’équipe J4U
                </p>
                """.format(
        url_conf
    )
    mail.send(msg)
    return jsonify(success=True)


@app.route("/resetpasswordmail", methods=["GET"])
def reset_password_mail():
    # Send a verification mail
    email = request.args.get("email")
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"msg": "Le compte n'existe pas"}), 400
    url_conf = generate_reset_token(email)
    msg = Message(
        "J4U: Réinitialisation du mot de passe. Veuillez cliquer sur le lien et suivre les instructions",
        sender="j4u@unil.ch",
        recipients=[email],
    )
    msg.html = '<a href="{}">Réinitialiser</a>'.format(url_conf)
    mail.send(msg)
    return jsonify(success=True)


@app.route("/login", methods=["POST"])
@validate_json
@validate_schema(login_schema)
def login():
    if not request.is_json:
        return jsonify({"msg": "Paramètre JSON manquant"}), 400

    email = request.json.get("email", None)
    password = request.json.get("password", None)
    if not email:
        return jsonify({"msg": "Paramètre d'utilisateur manquant"}), 400
    if not password:
        return jsonify({"msg": "Paramètre du mot-de-passe manquant"}), 400

    user = User.query.filter_by(email=email).first()

    if user and user.check_password(password):
        track_login(user.email)
        # Identity can be any data that is json serializable
        access_token = create_access_token(
            identity=user.id, expires_delta=datetime.timedelta(0, 60 * 3600)
        )
        refresh_token = create_refresh_token(identity=user.id)
        payload = row2dict(user)
        payload["accessToken"] = access_token
        payload["refreshToken"] = access_token
        del payload["pwd_hash"]
        res = jsonify(payload), 200
        return res
    else:
        return jsonify({"msg": "Email ou mot-de-passe incorrect."}), 400


@app.route("/signup", methods=["POST"])
@validate_json
@validate_schema(signup_schema)
def signup():
    form = request.json
    validity_token = form["validityToken"]
    obj = confirm_validity_token(validity_token)
    if not obj:
        return jsonify({"msg": "Lien d'inscription perime"}), 400
    new_user = User(
        civilite=form["civilite"],
        firstName=form["firstName"],
        lastName=form["lastName"],
        birthDate=form["birthDate"],
        email=form["email"],
        phone=form["phone"],
        plastaId=form["plastaId"],
        pwd=form["password"],
        group=obj["group"],
    )
    try:
        db_session.add(new_user)
        db_session.commit()
    except sqlalchemy.exc.IntegrityError as err:
        duplicated_key = err.orig.msg.split("'")[-2]
        mm = duplicated_key
        if duplicated_key == "phone":
            mm = "Ce numéro de téléphone est déjà utilisé." 
        elif duplicated_key == "email":
            mm = "Cette adresse email est déjà utilisée." 
        
        return (
            jsonify(
                {
                    "msg": "{}  Si vous avez déjà un compte et avez oublié votre mot de passe, cliquez sur  'Mot de passe oublié?' sur la page 'se connecter'".format(
                        mm
                    )
                }
            ),
            422,
        )

    # Send a verification mail
    url_conf = generate_confirmation_token(form["email"])
    msg = Message(
        "Validation de votre inscription à J4U",
        sender="j4u@unil.ch",
        recipients=[form["email"]],
    )
    msg.html = """
        <p>
            Chère participante, cher participant,
        </p>

        <p>
            Nous vous remercions pour votre inscription à l’étude “Job For You” (J4U). Afin de finaliser votre inscription, veuillez cliquer sur le lien ci-dessous :
        </p>

        <p>
            <a href="{}">Cliquez ici pour confirmer votre adresse email</a>
        </p>

        <p>
            Votre inscription vous donne accès à un outil innovant et personnalisé ! Afin d’avoir accès à cet outil, vous devez répondre à une enquête. Les résultats de l’enquête nous permettent de paramétrer l’outil au plus juste.
        </p>

        <p>
            <strong>Accédez directement à cette enquête sur la page d’accueil de notre <a href="https://j4u.unil.ch">site web</a>.</strong>
        </p>

        <p>
            L’équipe J4U vous remercie.
        </p>
        <p>
            Si vous avez des questions, vous pouvez nous contacter par email à <a href="mailto:j4u@unil.ch">j4u@unil.ch</a> ou par téléphone au 079 XXX XX XX. Pour vous désinscrire à tout moment, écrivez-nous avec « désinscription » en objet. Pour en savoir plus, lisez les <a href="https://j4u.unil.ch/#/legal">conditions générales de l’étude</a> et les <a href="https://j4u.unil.ch/#/tirage">conditions générales du tirage au sort</a>. Chaque étape augmente vos chances de gagner au tirage au sort final : la participation à l’enquête rapporte 10 billets de loterie.
        </p>
                """.format(
        url_conf
    )
    mail.send(msg)
    res = jsonify(success=True)
    return res


@app.route("/update", methods=["POST"])
@validate_json
@jwt_required
def update():
    form = request.json
    current_user = get_current_user()
    current_user.civilite = form["civilite"]
    current_user.firstName = form["firstName"]
    current_user.lastName = form["lastName"]
    current_user.birthDate = form["birthDate"]
    current_user.email = form["email"]
    current_user.phone = form["phone"]
    current_user.plastaId = form["plastaId"]
    db_session.add(current_user)
    db_session.commit()
    return jsonify(success=True)


@app.route("/recom", methods=["POST"])
@jwt_required
def recomend():
    # Abilities values
    data = request.json

    current_user = get_current_user()
    current_user.alpha = float(data.get("alpha"))
    current_user.beta = float(data.get("beta"))
    current_user.oldJobValue = int(data.get("oldJobValue"))
    current_user.oldJobLabel = data.get("oldJobLabel")
    locationValue = data.get("locationValue")
    db_session.commit()

    survey_id = current_user.surveyId

    params = get_vars(current_user) + [
        current_user.alpha,
        current_user.oldJobValue,
        current_user.beta,
    ]
    res = recom(*params)
    track_recommendation(params[-3], params[-2], params[-1], locationValue)

    return jsonify(res)


@app.route("/track", methods=["POST"])
@jwt_required
def track():
    obj = request.json
    track_inapp(obj)
    return jsonify(success=True)


@app.route("/jobprops", methods=["GET"])
@jwt_required
def job_props():
    current_user = get_current_user()
    job = request.args.get("job")
    if not job or len(job) < 3:
        return jsonify({})
    res = search(job)
    return jsonify(res)


@app.route("/link", methods=["GET"])
@jwt_required
def link():
    current_user = get_current_user()

    valid = retrieve_all(current_user.surveyId)

    if valid:
        return jsonify(success=True)

    return jsonify(success=False)


@app.route("/linkqualitrics", methods=["GET"])
def linkqualitrics():
    surveyId = request.args.get("surveyId")
    valid = retrieve_all(surveyId)

    if valid:
        environmentUrl = (
            "http://localhost:8080"
            if get_config()["app_url"] == "http://127.0.0.1:8080"
            else get_config()["app_url"]
        )
        return redirect("{}/#/logout".format(environmentUrl), code=302)
    return jsonify(success=False)


@app.route("/positions", methods=["POST"])
@jwt_required
def positions():
    data = request.json
    job = request.args.get("avam")
    oldJobLabel = data.get("oldJobLabel")

    # This parameter is only received by control-group searches
    # Under the J4U condition, oldJobValue and oldJobLabel are persisted on recom
    # Since control bypasses recom, this parameter is persisted here
    if oldJobLabel:
        oldjob = data["codes"]
        current_user = get_current_user()
        current_user.oldJobValue = oldjob[0]["value"]
        current_user.oldJobLabel = data["oldJobLabel"]
        db_session.commit()

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Postman-Token": "a22088d4-4d7f-4d72-b14d-bceb48ef23db",
        "X-Requested-With": "XMLHttpRequest",
        "cache-control": "no-cache",
    }
    # SECO's JobRoom starts pagination from 0, but our pagination component matches page number and navigation items, so we need to decrease its number by one
    params = (("page", int(data["currentPage"]) - 1), ("size", "10"), ("sort", "score"))

    if data["cantonCodes"] == [""]:
        data["cantonCodes"] = []

    data = {
        "permanent": None,
        "workloadPercentageMin": 0,
        "workloadPercentageMax": 100,
        "onlineSince": 30,
        "displayRestricted": False,
        "keywords": [],
        "professionCodes": data["codes"],
        "communalCodes": [],
        "cantonCodes": data["cantonCodes"],
    }
    response = requests.post(
        "https://www.job-room.ch/jobadservice/api/jobAdvertisements/_search",
        headers=headers,
        params=params,
        data=json.dumps(data),
    )
    res = response.json()
    res = {"totalCount": response.headers.get("X-Total-Count", "0"), "positions": res}

    import curlify
    print("="*50)
    print(curlify.to_curl(response.request))
    print("="*50)

    return jsonify(res)


@app.route("/locations", methods=["GET"])
@jwt_required
def locations():
    loc = request.args.get("loc")
    if not loc:
        loc = ""

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Postman-Token": "a22088d4-4d7f-4d72-b14d-bceb48ef23db",
        "X-Requested-With": "XMLHttpRequest",
        "cache-control": "no-cache",
        "Cookie": "_ga=GA1.2.8377990.1544699425; _jr2.ID=18287a4d-86fc-49de-870a-c342698fa58d; NG_TRANSLATE_LANG_KEY=fr; JSESSIONID=_5VkSYRAG01H_nZ3MkazegLbfhdDJwm3tqiBRAQ-; _gid=GA1.2.1508386193.1554111736",
    }

    # SECO's JobRoom starts pagination from 0, but our pagination component matches page number and navigation items, so we need to decrease its number by one
    params = (
        ("prefix", loc),
        ("resultSize", "10"),
        ("distinctByLocalityCity", "true"),
        ("_ng", "ZnI="),
    )

    response = requests.post(
        "https://www.job-room.ch/referenceservice/api/_search/localities",
        headers=headers,
        params=params,
    )

    res = response.json()

    return jsonify(res)


@app.route("/userinfos", methods=["GET"])
@jwt_required
def user_infos():
    current_user = get_current_user()
    res = row2dict(current_user)
    return jsonify(res)


@app.route("/signup-link", methods=["GET"])
def signup_link():
    date = request.args["date"]
    group = request.args["group"]
    token = generate_validity_token(date, group)
    obj = confirm_validity_token(token)
    if not obj:
        return jsonify(valid=False)
    date, group = obj["date"], obj["group"]
    url = "{}/#/signup?token={}".format(get_config()["app_url"], token)
    return jsonify(url=url, valid=True, date=date, group=group)


@app.route("/updategroup", methods=["POST"])
@validate_json
def updategroup():
    # admin_password = get_config()['UPDATE_PWD']
    admin_password = get_config()["update_pwd"]
    password = request.json["password"]
    allowedFields = ["fixedAlphaBeta", "fixedOldJobValue", "blocked", "group"]
    field = request.json["field"]
    value = request.json["value"]
    group = request.json["group"]
    if password and field and value and group and field in allowedFields:
        if password == admin_password:
            engine = create_engine(
                "mysql+mysqlconnector://{user}:{pwd}@127.0.0.1/j4u".format(
                    user=get_config()["mysql_user"], pwd=get_config()["mysql_pwd"]
                ),
                convert_unicode=True,
                pool_recycle=600,
            )
            update_query = """UPDATE `j4u`.`user`
                    SET `{}` = '{}'
                    WHERE (`group` = '{}')""".format(
                field, value, group
            )

            # if admin changed the group value, look for the new value for group
            if field == "group":
                group = value

            select_query = "SELECT * FROM j4u.user WHERE `group` = '{}'".format(group)

            with engine.connect() as con:
                con.execute(update_query)
                response = con.execute(select_query)
                con.close()
            res = [dict(row) for row in response]
            for record in res:
                del record["pwd_hash"]
            res = jsonify({"response": res})
            res.headers.set("Access-Control-Allow-Origin", "*")
            return res
        else:
            return jsonify({"response": "wrong password"}), 400
    return jsonify({"response": "error"}), 400


@app.route("/listusers", methods=["POST"])
@validate_json
def listusers():
    admin_password = get_config()["update_pwd"]
    password = request.json["password"]
    group = request.json["group"]
    if password == admin_password:
        engine = create_engine(
            "mysql+mysqlconnector://{user}:{pwd}@127.0.0.1/j4u".format(
                user=get_config()["mysql_user"], pwd=get_config()["mysql_pwd"]
            ),
            convert_unicode=True,
            pool_recycle=600,
        )
        select_query = "SELECT * FROM j4u.user"
        if group:
            select_query += " WHERE `group` = '{}'".format(group)
        with engine.connect() as con:
            response = con.execute(select_query)
            con.close()
        res = [dict(row) for row in response]
        for record in res:
            del record["pwd_hash"]
        res = jsonify({"response": res})
        res.headers.set("Access-Control-Allow-Origin", "*")
        return res
    else:
        return jsonify({"response": "wrong password"}), 400


@app.route("/certificate", methods=["POST"])
@validate_json
def certificate():
    # form = request.form
    form = request.json
    if os.environ.get("ENV") == "prod":
        certificateUrl = "https://j4u.unil.ch/"
    else:
        certificateUrl = "http://localhost:8080/dist/"

    certificateUrl += "certificate.html?civilite={}&jobTitle={}&firstName={}&lastName={}&birthDate={}&timestamp={}".format(
        form["civilite"],
        form["jobTitle"],
        form["firstName"],
        form["lastName"],
        form["birthDate"],
        form["timestamp"],
    )

    templateData = {
        "civilite": form["civilite"],
        "jobTitle": form["jobTitle"],
        "firstName": form["firstName"],
        "lastName": form["lastName"],
        "birthDate": form["birthDate"],
        "timestamp": form["timestamp"],
        "today": form["today"],
        "server": form["server"],
    }

    certificate = render_template("certificate.html", **templateData)
    HTML(string=certificate).write_pdf("000.pdf")
    return send_file("000.pdf", as_attachment=True)


@app.route("/utils/dump-activities", methods=["GET"])
def utils_dump_activities():
    x = activities.find()
    x = list(x)
    df = pd.DataFrame(x)
    csv = df.to_csv()
    return Response(
        csv,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=dump.csv"},
    )


@app.route("/formulaire", methods=["GET"])
@validate_json
def formulaire():
    return send_file("Formulaire.pdf", as_attachment=True)


if __name__ == "__main__":
    init_db()
    init_logdb()
    serve(app, host=get_config()["host"], port=get_config()["port"])

