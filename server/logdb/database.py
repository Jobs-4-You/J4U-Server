from pymongo import MongoClient

client = MongoClient(
    'localhost',
    username='root',
    password='my-secret-pw')

db = client['j4u-logs']

activities = db['activities']


def init_logdb():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()

    activities.drop()
