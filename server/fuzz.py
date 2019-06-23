from logdb.database import jobs
import time


def search(job):
    cursor = jobs.find(
        {"Title": {"$regex": job, "$options": "i"}},
        {"Title": 1, "ISCO08": 1, "AVAM": 1, "_id": False},
    ).limit(15)
    res = list(cursor)
    for r in res:
        r["Title"] = r["Title"].capitalize()
    return res
