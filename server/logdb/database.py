from pymongo import MongoClient, TEXT
import json
from config import get_config

client = MongoClient(
    'localhost',
    username='root',
    password='my-secret-pw')

db = client['j4u-logs']

activities = db['activities']
jobs = db['jobs']


def init_logdb():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()

    if get_config()['mode'] == 'dev':
        activities.drop()

    jobs.drop()
    with open('jobs.json') as f:
        data = json.load(f)

    jobs.insert_many(data)
    jobs.create_index([('Title', TEXT)])
