from flask import Flask, abort, jsonify
from flask_login import LoginManager, current_user, login_user
from database.database import init_db, db_session
from database.models import User

app = Flask('J4U-Server')

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
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
          abort(400, 'Invalid email or password')
        login_user(user, remember=form.remember_me.data)
        return jsonify(success=True)


if __name__ == "__main__":
    init_db()
    app.run()
