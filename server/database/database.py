from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from config import get_config

engine = create_engine(
    'mysql+mysqlconnector://{user}:{pwd}@127.0.0.1/j4u'.format(
        user=get_config()['mysql_user'], pwd=get_config()['mysql_pwd']),
    convert_unicode=True,
    pool_recycle=600)
db_session = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()


def init_db():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()

    import database.models

    if get_config()['mode'] == 'dev':
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)

    from database.models import User
    admin = User(
        firstName='admin',
        lastName='nimda',
        birthDate='2019-01-01',
        phone='0658062948',
        email='admin@example.com',
        pwd='jdida',
        plastaId='a111111',
        surveyId='81224',
        verified=True,
        blocked=False,
        group='123456')
    other = User(
        firstName='other',
        lastName='nimda',
        birthDate='2019-01-01',
        phone='0658062947',
        email='other@example.com',
        pwd='jdida',
        plastaId='009',
        surveyId='445511',
        verified=True)
    ather = User(
        firstName='ather',
        lastName='nimda',
        birthDate='2019-01-01',
        phone='0658062949',
        email='ather@example.com',
        pwd='jdida',
        plastaId='003',
        surveyId='9021988',
        verified=True)
    try:
        db_session.add_all([admin, other, ather])
        db_session.commit()
        print(User.query.all())
    except:
        print('Fake users already populated')
