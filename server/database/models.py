import binascii, os
from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Boolean, Float
from werkzeug.security import generate_password_hash, check_password_hash
from database.database import Base


class User(UserMixin, Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    firstName = Column(String(50))
    lastName = Column(String(50))
    email = Column(String(120), unique=True)
    phone = Column(String(16), unique=True)
    pwd_hash = Column(String(256))
    plastaId = Column(String(16), unique=True)
    formDone = Column(Boolean(), default=False)
    surveyId = Column(String(50))
    verified = Column(Boolean(), default=False)
    alpha = Column(Float, nullable=True)
    beta = Column(Float, nullable=True)
    oldJobValue = Column(Integer, nullable=True)
    oldJobLabel = Column(String(100), nullable=True)

    def __init__(self, firstName=None, lastName=None, email=None, pwd=None, phone=None, plastaId=None, surveyId=None, formDone=False, verified=False):
        self.firstName = firstName
        self.lastName = lastName
        self.phone = phone
        self.email = email
        self.set_password(pwd)
        self.plastaId = plastaId
        self.formDone = formDone
        self.verified = verified
        if surveyId is None:
            self.surveyId = binascii.b2a_hex(os.urandom(16)) 
        else:
            self.surveyId = surveyId

    def set_password(self, password):
        self.pwd_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.pwd_hash, password)

    def __repr__(self):
        return '<User {} {} {} {} {} {} {} {}>'.format(self.firstName, self.lastName, self.email, self.phone, self.plastaId, self.formDone, self.surveyId, self.verified)
