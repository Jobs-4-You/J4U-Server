from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from config import get_config

engine = create_engine(
    "mysql+mysqlconnector://{user}:{pwd}@127.0.0.1/j4u".format(
        user=get_config()["mysql_user"], pwd=get_config()["mysql_pwd"]
    ),
    convert_unicode=True,
    pool_recycle=600,
)
db_session = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)
Base = declarative_base()
Base.query = db_session.query_property()


def init_db():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()

    import database.models

    if get_config()["mode"] == "dev":
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)

    from database.models import User, Survey, UserSurvey

    survey_id_main = "SV_6tmPFThjXFpKg17"
    survey_id_cruiser = "SV_01bq6G5QXO4Vt1r"

    survey_1 = Survey(
        surveyId=survey_id_main, surveyTitle="Qulatrics Training", mandatory=1
    )
    survey_2 = Survey(
        surveyId=survey_id_cruiser, surveyTitle="Cruiser Game", mandatory=1
    )

    admin = User(
        civilite="M",
        firstName="admin",
        lastName="nimda",
        birthDate="2019-01-01",
        phone="0658062948",
        email="admin@example.com",
        pwd="jdida",
        plastaId="a111111",
        surveyId="40340304",
        verified=True,
        blocked=False,
        fixedOldJobValue=False,
        fixedAlphaBeta=False,
        group="J4UINT_C1NE",
    )
    other = User(
        civilite="M",
        firstName="other",
        lastName="nimda",
        birthDate="2019-01-01",
        phone="0658062947",
        email="other@example.com",
        pwd="jdida",
        plastaId="009",
        surveyId="40340304",
        verified=True,
        blocked=False,
        group="CGTINT_C1NE",
    )
    ather = User(
        civilite="M",
        firstName="ather",
        lastName="nimda",
        birthDate="2019-01-01",
        phone="0658062949",
        email="ather@example.com",
        pwd="jdida",
        plastaId="003",
        surveyId="9021988",
        verified=True,
        group="ather-ather",
    )
    oother = User(
        civilite="M",
        firstName="oother",
        lastName="nimda",
        birthDate="2019-01-01",
        phone="999999999",
        email="oother@example.com",
        pwd="jdida",
        plastaId="003",
        surveyId="uuuuiuu",
        verified=True,
        group="ather-ather",
    )
    try:
        db_session.add_all([admin, other, ather, oother, survey_1, survey_2])
        db_session.commit()
        print(User.query.all())
        ###########################################################
        u = User.query.filter_by(firstName="admin").first()
        u2 = User.query.filter_by(firstName="oother").first()
        us1 = UserSurvey()
        us1.survey = survey_1
        us2 = UserSurvey()
        us2.survey = survey_2
        u.surveyList = [us1, us2]
        uss1 = UserSurvey()
        uss1.survey = survey_1
        uss2 = UserSurvey()
        uss2.survey = survey_2
        u2.surveyList = [uss1, uss2]
        db_session.add_all([u, u2])
        db_session.commit()
        u = User.query.filter_by(firstName="admin").first()
        u2 = User.query.filter_by(firstName="oother").first()
        si = [
            (x.survey.surveyId, x.survey.surveyTitle, x.survey.mandatory, x.completed)
            for x in u.surveyList
        ]
        ###########################################################

    except Exception as err:
        print(err)
