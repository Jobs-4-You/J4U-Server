from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Boolean
from werkzeug.security import generate_password_hash, check_password_hash
from database.database import Base


class User(UserMixin, Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    email = Column(String(120), unique=True)
    pwd_hash = Column(String(32), unique=True)
    form_done = Column(Boolean())

    def __init__(self, name=None, email=None, pwd=None, form_done=False):
        self.name = name
        self.email = email
        self.form_done = form_done

    def set_password(self, password):
        self.pwd_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.pwd_hash, password)

    def __repr__(self):
        return '<User {} {} {}>'.format(self.name, self.email, self.form_done)
