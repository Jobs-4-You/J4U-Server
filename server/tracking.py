from flask import request
from ua_parser import user_agent_parser
import time
from logdb.database import activities
from flask import jsonify
from flask_jwt_extended import current_user

def add_meta(obj):
    ua = request.headers.get('User-Agent')
    browser = user_agent_parser.ParseUserAgent(ua)['family']
    os = user_agent_parser.ParseOS(ua)['family']
    device = user_agent_parser.ParseDevice(ua)['family']

    obj['CLIENT_IP'] = request.remote_addr
    obj['BROWSER'] = browser
    obj['OS'] = os
    obj['DEVICE'] = device
    obj['TIMESTAMP'] = time.time()

    if current_user :
        obj['USER'] = current_user.email
    else:
        obj['USER'] = 'Anonymous'

    return obj

def track_login(email):
    obj = {
        'TYPE': 'LOGIN',
        'USEREMAIL': email
    }
    obj = add_meta(obj)
    activities.insert_one(obj)

def track_recommendation(alpha, previous_job, beta, locationValue):
    obj = {
        'TYPE': 'RECOMMENDATION',
        'ALPHA': alpha,
        'BETA': beta,
        'PREV_JOB': previous_job,
        'LOCATION': locationValue
    }

    obj = add_meta(obj)
    activities.insert_one(obj)

def track_inapp(obj):
    obj = add_meta(obj)
    activities.insert_one(obj)
    print(obj)