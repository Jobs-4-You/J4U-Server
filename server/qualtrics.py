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


def min_max_scaler(domain, target, x, inverse=False):
    x = np.clip(x, domain[0], domain[1])
    normalized = (x - domain[0]) / (domain[1] - domain[0])
    res = normalized * (target[1] - target[0]) + target[0]
    if inverse:
        res = target[1] - res + target[0]
    return res


name_to_var = {
    "Sc_Fluency": ("var1", partial(min_max_scaler, [0, 30], [1, 7])),
    "Sc_Induc_Reas": ("var2", partial(min_max_scaler, [0, 8], [1, 7])),
    "score_matrices": ("var3", partial(min_max_scaler, [0, 1], [1, 7])),
    "Sc_WM": ("var4", partial(min_max_scaler, [0, 12], [1, 7])),
    "Sc_MOY_RT": ("var5", partial(min_max_scaler, [0, 5], [1, 7], inverse=True)),
    "Sc_Verbal_Com": ("var6", partial(min_max_scaler, [0, 48], [1, 7])),
    "score_PM": ("var7", partial(min_max_scaler, [0, 1], [1, 7])),
    "score_metacog": ("var8", partial(min_max_scaler, [0, 1], [1, 7], inverse=True)),
    "Sc_Leader": ("var9", partial(min_max_scaler, [6, 24], [1, 5])),
    "Sc_Self_cont": ("var10", partial(min_max_scaler, [13, 65], [1, 5])),
    "Sc_Stress_Tol": ("var11", partial(min_max_scaler, [0, 40], [1, 5], inverse=True)),
    "Sc_Adapt": ("var12", partial(min_max_scaler, [8, 40], [1, 5])),
}


def process(df_main, df_cruiser):
    df_main = df_main.loc[df_main["Finished"] != "0", :]
    df_cruiser = df_cruiser.loc[df_cruiser["Finished"] != "0", :]
    cols_SC = [(x, df_main[x].iloc[0]) for x in df_main.columns if "SC" in x]
    df_main = df_main.rename(columns={before: after for before, after in cols_SC})
    df_main = df_main.iloc[2:]
    df_cruiser = df_cruiser.iloc[2:]
    ##########
    df_main = df_main.rename(columns={"id": "ID"})
    ##########
    df_cruiser = df_cruiser[df_cruiser["ID"].notnull()]
    df_main = df_main.reset_index().set_index("ID")
    df_cruiser = df_cruiser.reset_index().set_index("ID")
    df_main = df_main.loc[~df_main.index.duplicated(keep="first")]
    df_cruiser = df_cruiser.loc[~df_cruiser.index.duplicated(keep="first")]
    df = pd.concat([df_main, df_cruiser], axis=1, join="inner")
    df["Sc_Fluency"] = df["COG_VF1"].str.split().apply(
        lambda x: len(x) if type(x) == list else x
    ) + df["COG_VF2"].str.split().apply(lambda x: len(x) if type(x) == list else x)
    df["Sc_Fluency"] *= 0.5

    df = df[list(name_to_var.keys())]
    df = df.apply(pd.to_numeric, errors="coerce")
    for col, (_, mapper) in name_to_var.items():
        df[col] = df[col].apply(mapper)
    df = df.reset_index()
    df = df.fillna(3)
    print(df['ID'])
    return df


def get_surveys():
    # Setting user Parameters
    apiToken = "T8o9qNI2J3hnl1TlMEcn2nLShZWW0Kj1ZvyoaLAf"

    survey_id_main = "SV_6tmPFThjXFpKg17"
    survey_id_cruiser = "SV_01bq6G5QXO4Vt1r"
    fileFormat = "csv"
    dataCenter = "eu"

    def dw_survey(surveyId):
        # Setting static parameters
        requestCheckProgress = 0.0
        progressStatus = "inProgress"
        baseUrl = "https://{0}.qualtrics.com/API/v3/surveys/{1}/export-responses/".format(
            dataCenter, surveyId
        )
        headers = {"content-type": "application/json", "x-api-token": apiToken}

        # Step 1: Creating Data Export
        downloadRequestUrl = baseUrl
        downloadRequestPayload = json.dumps({"format": fileFormat})
        downloadRequestResponse = requests.request(
            "POST", downloadRequestUrl, data=downloadRequestPayload, headers=headers
        )
        # print(downloadRequestResponse.text)
        print(downloadRequestResponse.json())
        progressId = downloadRequestResponse.json()["result"]["progressId"]
        # print(downloadRequestResponse.text)

        # Step 2: Checking on Data Export Progress and waiting until export is ready
        while progressStatus != "complete" and progressStatus != "failed":
            # print ("progressStatus=", progressStatus)
            requestCheckUrl = baseUrl + progressId
            requestCheckResponse = requests.request(
                "GET", requestCheckUrl, headers=headers
            )
            requestCheckProgress = requestCheckResponse.json()["result"][
                "percentComplete"
            ]
            # print("Download is " + str(requestCheckProgress) + " complete")
            progressStatus = requestCheckResponse.json()["result"]["status"]

        # step 2.1: Check for error
        if progressStatus is "failed":
            raise Exception("export failed")

        fileId = requestCheckResponse.json()["result"]["fileId"]

        # Step 3: Downloading file
        requestDownloadUrl = baseUrl + fileId + "/file"
        requestDownload = requests.request(
            "GET", requestDownloadUrl, headers=headers, stream=True
        )

        z = zipfile.ZipFile(io.BytesIO(requestDownload.content))
        return z

    z_main = dw_survey(survey_id_main)
    z_cruiser = dw_survey(survey_id_cruiser)
    data_main = z_main.read("COG-12.csv")
    data_cruiser = z_cruiser.read("J4U - CRUISER.csv")
    df_main = pd.read_csv(StringIO(str(data_main, "utf-8")))
    df_cruiser = pd.read_csv(StringIO(str(data_cruiser, "utf-8")))
    df = process(df_main, df_cruiser)
    return df


def retrieve_all(surveyId):
    df = get_surveys()
    uois = User.query.filter_by(formDone=False).all()
    for uoi in uois:
        if uoi.surveyId in df["ID"].unique():
            v = df[df["ID"] == uoi.surveyId][df.columns[1:]].values[0]
            f = Features(*v)
            uoi.features = f
            uoi.formDone = True
            db_session.add(uoi)

    db_session.commit()

    if surveyId in df["ID"].unique():
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
