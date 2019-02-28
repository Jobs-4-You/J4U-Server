import requests
import zipfile
import json
import io, os
import sys
import pandas as pd
import numpy as np
from io import StringIO
from database.database import db_session
from database.models import User, Features


def get_surveys():
    # Setting user Parameters
    apiToken = 'T8o9qNI2J3hnl1TlMEcn2nLShZWW0Kj1ZvyoaLAf'

    surveyId = "SV_3VjBHgE8Lu9uICN"
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
    data = z.read('J4U  - COGTEL AND ONET.csv')
    df = pd.read_csv(StringIO(str(data, 'utf-8')))
    df = df[(df['Finished'] == '1') & (df['id.1'].notnull())]
    cols = [
        'id.1', 'SC3', 'SC5', 'SC6', 'SC4', 'SC7', 'SC0', 'SC2', 'SC1', 'SC10',
        'SC11', 'SC9', 'SC8'
    ]
    return df[cols]


def retrieve_all(surveyId):
    df = get_surveys()
    uois = User.query.filter_by(formDone=False).all()

    for uoi in uois:
        if uoi.surveyId in df['id.1'].unique():
            v = df[df['id.1'] == uoi.surveyId][df.columns[1:]].values[0]
            f = Features(*v)
            uoi.features = f
            uoi.formDone = True
            db_session.add(uoi)

    db_session.commit()

    if surveyId in df['id'].unique():
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


df = get_surveys().values
print(df)
