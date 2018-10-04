from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Boolean
from database.database import Base

class User(UserMixin, Base):
  __tablename__ = 'users'
  id = Column(Integer, primary_key=True)
  name = Column(String(50))
  email = Column(String(120), unique=True)
  form_done = Column(Boolean())

  def __init__(self, name=None, email=None, form_done=False):
    self.name = name
    self.email = email
    self.form_done = form_done

  def __repr__(self):
    return '<User {} {} {}>'.format(self.name, self.email, self.form_done)