import requests
import zipfile
import json
import io, os
import sys
import pandas as pd
import numpy as np
from functools import partial
from io import StringIO
from database.database import db_session
from database.models import User, Features


def min_max_scaler(domain, target, x):
    normalized = (x - domain[0]) / (domain[1] - domain[0])
    res = normalized * (target[1] - target[0]) + target[0]
    return res


name_to_var = {
    'FluencyofIdeas': ('var1', partial(min_max_scaler, [0, 5], [1, 5])),
    'Sc_Induc_Reas': ('var2', partial(min_max_scaler, [0, 8], [1, 5])),
    'CategoryFlexibility': ('var3', partial(min_max_scaler, [0, 12], [1, 5])),
    'Sc_WM': ('var4', partial(min_max_scaler, [0, 12], [1, 5])),
    'Sc_RT': ('var5', partial(min_max_scaler, [0, 10], [1, 5])),
    'Sc_Verbal_Com': ('var6', partial(min_max_scaler, [0, 48], [1, 5])),
    'Monitoring': ('var7', partial(min_max_scaler, [0, 5], [1, 5])),
    'TimeManagement': ('var8', partial(min_max_scaler, [0, 5], [1, 5])),
    'Sc_Leader': ('var9', partial(min_max_scaler, [6, 24], [1, 5])),
    'Sc_Self_cont': ('var10', partial(min_max_scaler, [13, 65], [1, 5])),
    'Sc_Stress_Tol': ('var11', partial(min_max_scaler, [0, 40], [1, 5])),
    'Sc_Adapt': ('var12', partial(min_max_scaler, [8, 40], [1, 5]))
}


def process(df):
    needed_cols = list(name_to_var.keys())
    cols = [c for c in df.columns if 'SC' in c and df[c].iloc[0] in needed_cols]

    print(df['MOY_RT'])
    exit()
    print(df.iloc[[0, 2]])
    exit()
    ######### Remove when we have complete survey data ##
    #####################################################
    #####################################################
    present_cols = df[cols].iloc[0]
    missing = set(needed_cols) - set(present_cols)
    for i, col in zip(range(100, 200), missing):
        df['SC{}'.format(i)] = df[cols[1]]
        df['SC{}'.format(i)].iloc[0] = col

    cols = [c for c in df.columns if 'SC' in c and df[c].iloc[0] in needed_cols]
    #####################################################
    #####################################################

    a = {df[x].iloc[0]: x for x in cols}
    ordered_cols = [a[x] for x in needed_cols]

    for x in cols:
        name = df[x].iloc[0]
        r = name_to_var.get(name)

        v, scaler = r
        df[x].iloc[2:] = df[x].iloc[2:].astype(float).apply(scaler)

    cols = ['ResponseId'] + ordered_cols
    df = df[(df['Finished'] == '1') & (df['ResponseId'].notnull())]
    print(df['ResponseId'])
    return df[cols]


def get_surveys():
    # Setting user Parameters
    apiToken = 'T8o9qNI2J3hnl1TlMEcn2nLShZWW0Kj1ZvyoaLAf'

    surveyId = "SV_6tmPFThjXFpKg17"
    fileFormat = "csv"
    dataCenter = 'eu'

    # Setting static parameters
    requestCheckProgress = 0.0
    progressStatus = "inProgress"
    baseUrl = "https://{0}.qualtrics.com/API/v3/surveys/{1}/export-responses/".format(
        dataCenter, surveyId)
    headers = {
        "content-type": "application/json",
        "x-api-token": apiToken,
    }

    # Step 1: Creating Data Export
    downloadRequestUrl = baseUrl
    downloadRequestPayload = json.dumps({
        'format': fileFormat,
    })
    downloadRequestResponse = requests.request(
        "POST",
        downloadRequestUrl,
        data=downloadRequestPayload,
        headers=headers)
    #print(downloadRequestResponse.text)
    print(downloadRequestResponse.json())
    progressId = downloadRequestResponse.json()["result"]["progressId"]
    #print(downloadRequestResponse.text)

    # Step 2: Checking on Data Export Progress and waiting until export is ready
    while progressStatus != "complete" and progressStatus != "failed":
        #print ("progressStatus=", progressStatus)
        requestCheckUrl = baseUrl + progressId
        requestCheckResponse = requests.request(
            "GET", requestCheckUrl, headers=headers)
        requestCheckProgress = requestCheckResponse.json(
        )["result"]["percentComplete"]
        #print("Download is " + str(requestCheckProgress) + " complete")
        progressStatus = requestCheckResponse.json()["result"]["status"]

    #step 2.1: Check for error
    if progressStatus is "failed":
        raise Exception("export failed")

    fileId = requestCheckResponse.json()["result"]["fileId"]

    # Step 3: Downloading file
    requestDownloadUrl = baseUrl + fileId + '/file'
    requestDownload = requests.request(
        "GET", requestDownloadUrl, headers=headers, stream=True)

    z = zipfile.ZipFile(io.BytesIO(requestDownload.content))
    data = z.read('COG-12.csv')
    df = pd.read_csv(StringIO(str(data, 'utf-8')))
    df = process(df)
    return df


def retrieve_all(surveyId):
    df = get_surveys()
    uois = User.query.filter_by(formDone=False).all()
    for uoi in uois:
        if uoi.surveyId in df['ResponseId'].unique():
            v = df[df['ResponseId'] == uoi.surveyId][df.columns[1:]].values[0]
            f = Features(*v)
            uoi.features = f
            uoi.formDone = True
            db_session.add(uoi)

    db_session.commit()

    if surveyId in df['ResponseId'].unique():
        return True
    return False


def get_vars(user):
    return [
        user.features.var1,
        user.features.var2,
        user.features.var3,
        user.features.var4,
        user.features.var5,
        user.features.var6,
        user.features.var7,
        user.features.var8,
        user.features.var9,
        user.features.var10,
        user.features.var11,
        user.features.var12,
    ]

df = get_surveys()
print(df)