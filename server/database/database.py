from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

engine = create_engine(
    'mysql://root:my-secret-pw@127.0.0.1/j4u', convert_unicode=True)
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
    admin = User(name='admin_jdid', email='admin@example.com', pwd='jdida')
    db_session.add(admin)
    db_session.commit()
    print(User.query.all())
