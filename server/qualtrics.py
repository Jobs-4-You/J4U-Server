import requests
import zipfile
import json
import io, os
import sys
import pandas as pd
import numpy as np
from functools import partial
from io import StringIO
from database.database import db_session, Base, engine
from database.models import User, Features, Survey, UserSurvey


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
    print(df["ID"])
    return df


def dw_survey(surveyId):
    # Setting user Parameters
    apiToken = "T8o9qNI2J3hnl1TlMEcn2nLShZWW0Kj1ZvyoaLAf"
    fileFormat = "csv"
    dataCenter = "eu"

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
    # print(downloadRequestResponse.json())
    progressId = downloadRequestResponse.json()["result"]["progressId"]
    # print(downloadRequestResponse.text)

    # Step 2: Checking on Data Export Progress and waiting until export is ready
    while progressStatus != "complete" and progressStatus != "failed":
        # print ("progressStatus=", progressStatus)
        requestCheckUrl = baseUrl + progressId
        requestCheckResponse = requests.request("GET", requestCheckUrl, headers=headers)
        requestCheckProgress = requestCheckResponse.json()["result"]["percentComplete"]
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
    survey_name = z.namelist()[0]
    data = z.read(survey_name)
    df = pd.read_csv(StringIO(str(data, "utf-8")))

    return df


def get_surveys():

    survey_id_main = "SV_6tmPFThjXFpKg17"
    survey_id_cruiser = "SV_01bq6G5QXO4Vt1r"

    df_main = dw_survey(survey_id_main)
    df_cruiser = dw_survey(survey_id_cruiser)
    # data_main = z_main.read("COG-12_Baseline.csv")
    # data_cruiser = z_cruiser.read("J4U - CRUISER.csv")
    # df_main = pd.read_csv(StringIO(str(data_main, "utf-8")))
    # df_cruiser = pd.read_csv(StringIO(str(data_cruiser, "utf-8")))
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


def update_completion(user):
    print("Start completion update")
    user_survey_id = user.surveyId
    survey_list = user.surveyList
    survey_ids = [x.survey.surveyId for x in survey_list]
    survey_keys = [x.survey.id for x in survey_list]

    dfs = [dw_survey(x).rename(columns={"id": "ID"}) for x in survey_ids]
    dfs = [df.loc[df["Finished"] != "0", "ID"].dropna() for df in dfs]
    dfs = [df.iloc[2:].tolist() for df in dfs]
    dfs = [User.query.filter(User.surveyId.in_(ids)).all() for ids in dfs]
    dfs = [[u.id for u in us] for us in dfs]

    for s, u in zip(survey_keys, dfs):
        matches = UserSurvey.query.filter(
            UserSurvey.surveyId == s, UserSurvey.userId.in_(u)
        ).all()
        for x in matches:
            x.completed = True
        db_session.add_all(matches)
    db_session.commit()

    print("End completion update")


def check_completion(user):
    print("Start completion check")
    user_survey_id = user.surveyId
    survey_list = user.surveyList

    records = []

    for survey_assoc in survey_list:
        record = {
            "title": survey_assoc.survey.surveyTitle,
            "surveyId": survey_assoc.survey.surveyId,
            "completed": survey_assoc.completed,
            "mandatory": survey_assoc.survey.mandatory,
        }
        records.append(record)

    print("End completion check")
    return records


if __name__ == "__main__":

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    survey_id_main = "SV_6tmPFThjXFpKg17"
    survey_id_cruiser = "SV_01bq6G5QXO4Vt1r"

    survey_1 = Survey(
        surveyId=survey_id_main, surveyTitle="Qulatrics Training", mandatory=1
    )
    survey_2 = Survey(
        surveyId=survey_id_cruiser, surveyTitle="Cruiser Game", mandatory=1
    )

    admin = User(
        civilite="M",
        firstName="admin",
        lastName="nimda",
        birthDate="2019-01-01",
        phone="0658062948",
        email="admin@example.com",
        pwd="jdida",
        plastaId="a111111",
        surveyId="40340304",
        verified=True,
        blocked=False,
        fixedOldJobValue=False,
        fixedAlphaBeta=False,
        group="J4UINT_C1NE",
    )
    other = User(
        civilite="M",
        firstName="other",
        lastName="nimda",
        birthDate="2019-01-01",
        phone="0658062947",
        email="other@example.com",
        pwd="jdida",
        plastaId="009",
        surveyId="40340304",
        verified=True,
        blocked=False,
        group="CGTINT_C1NE",
    )
    ather = User(
        civilite="M",
        firstName="ather",
        lastName="nimda",
        birthDate="2019-01-01",
        phone="0658062949",
        email="ather@example.com",
        pwd="jdida",
        plastaId="003",
        surveyId="9021988",
        verified=True,
        group="ather-ather",
    )
    oother = User(
        civilite="M",
        firstName="oother",
        lastName="nimda",
        birthDate="2019-01-01",
        phone="999999999",
        email="oother@example.com",
        pwd="jdida",
        plastaId="003",
        surveyId="uuuuiuu",
        verified=True,
        group="ather-ather",
    )
    try:
        db_session.add_all([admin, other, ather, oother, survey_1, survey_2])
        db_session.commit()
        print(User.query.all())
        ###########################################################
        u = User.query.filter_by(firstName="admin").first()
        u2 = User.query.filter_by(firstName="oother").first()
        us1 = UserSurvey()
        us1.survey = survey_1
        us2 = UserSurvey()
        us2.survey = survey_2
        u.surveyList = [us1, us2]
        uss1 = UserSurvey()
        uss1.survey = survey_1
        uss2 = UserSurvey()
        uss2.survey = survey_2
        u2.surveyList = [uss1, uss2]
        db_session.add_all([u, u2])
        db_session.commit()
        u = User.query.filter_by(firstName="admin").first()
        u2 = User.query.filter_by(firstName="oother").first()
        si = [
            (x.survey.surveyId, x.survey.surveyTitle, x.survey.mandatory, x.completed)
            for x in u.surveyList
        ]
        check_completion(u)
        update_completion(u)
        check_completion(u)
        print("-" * 20)
        check_completion(u2)
        ###########################################################

    except Exception as err:
        print(err)
