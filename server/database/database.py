from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

engine = create_engine(
    'mysql+mysqlconnector://root:my-secret-pw@127.0.0.1/j4u', convert_unicode=True)
db_session = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()


def init_db():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()

    import database.models
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    from database.models import User
    admin = User(
        firstName='admin',
        lastName='nimda',
        phone='0658062948',
        email='admin@example.com',
        pwd='jdida',
        plastaId='007',
        surveyId='289431b56f314b24ccd4b9582ce4aee1',
        verified=True)
    other = User(
        firstName='other',
        lastName='nimda',
        phone='0658062947',
        email='other@example.com',
        pwd='jdida',
        plastaId='009',
        surveyId='4Th1',
        verified=True)
    ather = User(
        firstName='ather',
        lastName='nimda',
        phone='0658062949',
        email='ather@example.com',
        pwd='jdida',
        plastaId='003',
        surveyId='4TTu',
        verified=True)
    db_session.add_all([admin, other, ather])
    db_session.commit()
    print(User.query.all())
