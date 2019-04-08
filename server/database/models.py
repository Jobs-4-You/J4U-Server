import binascii, os
from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, Date
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from database.database import Base


class Features(Base):
    __tablename__ = 'features'
    id = Column(Integer, primary_key=True)
    userId = Column(ForeignKey('user.id'), nullable=False, unique=True)
    var1 = Column(Float, nullable=False)
    var2 = Column(Float, nullable=False)
    var3 = Column(Float, nullable=False)
    var4 = Column(Float, nullable=False)
    var5 = Column(Float, nullable=False)
    var6 = Column(Float, nullable=False)
    var7 = Column(Float, nullable=False)
    var8 = Column(Float, nullable=False)
    var9 = Column(Float, nullable=False)
    var10 = Column(Float, nullable=False)
    var11 = Column(Float, nullable=False)
    var12 = Column(Float, nullable=False)

    def __init__(self, var1, var2, var3, var4, var5, var6, var7, var8, var9, var10, var11, var12):
        self.var1 = var1
        self.var2 = var2
        self.var3 = var3
        self.var4 = var4
        self.var5 = var5
        self.var6 = var6
        self.var7 = var7
        self.var8 = var8
        self.var9 = var9
        self.var10 = var10
        self.var11 = var11
        self.var12 = var12


class User(UserMixin, Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    firstName = Column(String(50))
    lastName = Column(String(50))
    birthDate = Column(Date())
    email = Column(String(120), unique=True)
    phone = Column(String(16), unique=True)
    pwd_hash = Column(String(256))
    plastaId = Column(String(16), unique=True)
    formDone = Column(Boolean(), default=False)
    surveyId = Column(String(50))
    verified = Column(Boolean(), default=False)
    alpha = Column(Float, nullable=True, default=50)
    beta = Column(Float, nullable=True, default=50)
    oldJobValue = Column(Integer, nullable=True)
    oldJobLabel = Column(String(100), nullable=True)
    features = relationship(Features, uselist=False)

    def __init__(self, firstName=None, lastName=None, email=None, pwd=None, phone=None, plastaId=None, surveyId=None, formDone=False, verified=False, birthDate=None):
        self.firstName = firstName
        self.lastName = lastName
        self.birthDate = birthDate
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
        return '<User {} {} {} {} {} {} {} {} {}>'.format(self.firstName, self.lastName, self.email, self.phone, self.plastaId, self.formDone, self.surveyId, self.verified, self.birthDate)

