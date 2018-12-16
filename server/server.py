from flask import Flask, request, abort, jsonify
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity, get_current_user
from flask_cors import CORS
from database.database import init_db, db_session
from database.models import User
from recom import recom
from qualtrics import get_vars

app = Flask('J4U-Server')
app.secret_key = 'super secret key'
app.config['JWT_SECRET_KEY'] = 'super-secret'  # Change this!
CORS(app)

jwt = JWTManager(app)

@jwt.user_loader_callback_loader
def user_loader_callback(identity):
    return User.query.get(identity)


@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()


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

    print(email)
    user = User.query.filter_by(email=email).first()
    
    if user and user.check_password(password):
        # Identity can be any data that is json serializable
        access_token = create_access_token(identity=user.id)
        return jsonify(access_token=access_token), 200
    else:
        return jsonify({"msg": "Missing password parameter"}), 400
    



@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = request.form.to_dict()
    new_user = User(
        name=form['pseudo'], email=form['email'], pwd=form['password'])
    db_session.add(new_user)
    db_session.commit()
    return jsonify(success=True)


@app.route('/recom', methods=['POST'])
@jwt_required
def recomend():
    # Abilities values
    current_user = get_current_user()
    survey_id = current_user.survey_id

    data = request.json
    params = get_vars(survey_id) + [data.get('alpha'), data.get('oldJobValue'), data.get('beta')]
    res = recom(*params)
    return jsonify(res)






    return '', 200
    params = [
        int(request.args.get('var1')),
        int(request.args.get('var2')),
        int(request.args.get('var3')),
        int(request.args.get('var4')),
        int(request.args.get('var5')),
        int(request.args.get('var6')),
        int(request.args.get('var7')),
        int(request.args.get('var8')),
        int(request.args.get('var9')),
        int(request.args.get('var10')),
        int(request.args.get('var11')),
        int(request.args.get('var12')),
        int(request.args.get('var13')),
        str(request.args.get('var14')),
        int(request.args.get('var15')),
    ]
    print(params)
    res = recom(*params)

    return jsonify(res)


if __name__ == "__main__":
    init_db()
    app.run()
