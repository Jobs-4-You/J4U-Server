from logdb.database import jobs
import time

def search(job):
    cursor = jobs.find({'Title': {'$regex': job, '$options': 'i'}}, {"Title":1, "ISCO08":1, "_id": False}).limit(5)
    res = list(cursor)
    return res