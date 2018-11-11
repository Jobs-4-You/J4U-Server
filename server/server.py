from flask import Flask, request, abort, jsonify
from flask_login import LoginManager, current_user, login_user
from flask_cors import CORS
from database.database import init_db, db_session
from database.models import User
from recom import recom

app = Flask('J4U-Server')
app.secret_key = 'super secret key'
CORS(app)

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = request.form.to_dict()
    print(form)
    user = User.query.filter_by(email=form['email']).first()
    if user is None or not user.check_password(form['password']):
        abort(400, 'Invalid email or password')
    #login_user(user, remember=form.remember_me.data)
    login_user(user)
    return jsonify(success=True)


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    # Logout the current user
    user = current_user
    user.authenticated = False
    db_session.add(user)
    db_session.commit()
    logout_user()
    return jsonify(success=True)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = request.form.to_dict()
    new_user = User(name=form['pseudo'], email=form['email'], pwd=form['password'])
    db_session.add(new_user)
    db_session.commit()
    return jsonify(success=True)


@app.route('/recom', methods=['GET'])
def recomend():
    # Abilities values
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
