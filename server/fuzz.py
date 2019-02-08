from logdb.database import jobs
import time

def search(job):
    cursor = jobs.find({'label': {'$regex': job, '$options': 'i'}}, {"label":1, "value":1, "_id": False}).limit(5)
    res = list(cursor)
    return res