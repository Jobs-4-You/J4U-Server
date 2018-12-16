# Python 3

import requests
import zipfile
import json
import io, os
import sys
import pandas as pd
from io import StringIO

def get_vars(id):
    # Setting user Parameters
    apiToken = 'T8o9qNI2J3hnl1TlMEcn2nLShZWW0Kj1ZvyoaLAf'


    surveyId = "SV_3VjBHgE8Lu9uICN"
    fileFormat = "csv"
    dataCenter = 'eu'

    # Setting static parameters
    requestCheckProgress = 0.0
    progressStatus = "inProgress"
    baseUrl = "https://{0}.qualtrics.com/API/v3/surveys/{1}/export-responses/".format(dataCenter, surveyId)
    headers = {
        "content-type": "application/json",
        "x-api-token": apiToken,
        }

    # Step 1: Creating Data Export
    downloadRequestUrl = baseUrl
    downloadRequestPayload = json.dumps({
        'format': fileFormat,
    })
    downloadRequestResponse = requests.request("POST", downloadRequestUrl, data=downloadRequestPayload, headers=headers)
    #print(downloadRequestResponse.text)
    progressId = downloadRequestResponse.json()["result"]["progressId"]
    #print(downloadRequestResponse.text)

    # Step 2: Checking on Data Export Progress and waiting until export is ready
    while progressStatus != "complete" and progressStatus != "failed":
        #print ("progressStatus=", progressStatus)
        requestCheckUrl = baseUrl + progressId
        requestCheckResponse = requests.request("GET", requestCheckUrl, headers=headers)
        requestCheckProgress = requestCheckResponse.json()["result"]["percentComplete"]
        #print("Download is " + str(requestCheckProgress) + " complete")
        progressStatus = requestCheckResponse.json()["result"]["status"]

    #step 2.1: Check for error
    if progressStatus is "failed":
        raise Exception("export failed")

    fileId = requestCheckResponse.json()["result"]["fileId"]

    # Step 3: Downloading file
    requestDownloadUrl = baseUrl + fileId + '/file'
    requestDownload = requests.request("GET", requestDownloadUrl, headers=headers, stream=True)

    z = zipfile.ZipFile(io.BytesIO(requestDownload.content))
    data = z.read('J4U  - COGTEL AND ONET.csv')
    df = pd.read_csv(StringIO(str(data, 'utf-8')))
    cols = ['SC3','SC5', 'SC6', 'SC4', 'SC7', 'SC0', 'SC2', 'SC1', 'SC10', 'SC11', 'SC9', 'SC8']
    res = df[df['id'] == id]
    return res[cols].values[0].astype(float).tolist()
    print(res[cols])
