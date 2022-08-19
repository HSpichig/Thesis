#imports des différents modules utiles au projet
import pandas as pd
import sqlite3
from datetime import *
import re
import os
import subprocess
import numpy as np

#Cette fonction permet de créer un dataframe contenant toutes les dates allant de la date du début (Start) à la date de fin (End)
def create_default_dataframe(Start,End) :
    #création du datetime pour la date de départ
    x = datetime.strptime(Start.strftime("%d/%m/%y ") + "13:00:00","%d/%m/%y %H:%M:%S")
    date_list = []
    #boucle ajoutant la date pour chaque jour contenu entre la date de départ et la date d'arrivée
    while x.date() <= End :
        date_list.append(x.date())
        x += timedelta(hours=24)

    #création d'un dataframe à partir de cette liste de dates
    df_dict = {"Date" : date_list}
    df = pd.DataFrame(df_dict)

    return df


#fonction permettant de créer plusieurs évènements se déroulant chacun sur une journée lorsque l'un des évènements se déroule sur plusieurs jours
def set_time_and_sort(df):
    #compteur
    c = 1
    #parcourt le dataframe et supprime les anomalies (timestamp plus petits que 0)
    for x in df.index:
        if df.loc[x]["Start_ts"] < 0 or df.loc[x]["End_ts"] < 0:
            df = df.drop(index=x, axis=0)
            print(f"ignoring line {x}")
    #à chaque fois
    while True :
        #indique le numéro de passage
        print("passage n " + str(c))
        c += 1
        test = False
        l1 = []
        c2 = 0
        counter = 0
        #parcourt tous les éléments du dataframe
        for x in df.index:
            #si un évènement a lieu sur plusieurs jours et que le compteur est plus petit que 31
            if datetime.fromtimestamp(df.loc[x]["Start_ts"]).date() != datetime.fromtimestamp(
                    df.loc[x]["End_ts"]).date() and c <= 31:
                test = True
                #copie les éléments relatifs à cet évènement deux fois
                temp_dic_1 = {index: df.loc[x][index] for index in df.loc[x].index}
                temp_dic_2 = {index: df.loc[x][index] for index in df.loc[x].index}
                #modifie la date de fin de la première copie pour qu'elle se termine le même jour que la date de commencement, mais à 23:59:59
                End_dt_1 = datetime.strptime(str(datetime.fromtimestamp(temp_dic_1["Start_ts"]).date()) + " 23:59:59",
                                             "%Y-%m-%d %H:%M:%S")
                # modifie la date de commencement de la deuxième copie. Cette date sera le jour suivant le jour de commencement, mais à 00:00:00
                Start_temp = datetime.fromtimestamp(temp_dic_2["Start_ts"]) + timedelta(days=1)
                Start_dt_2 = datetime.strptime(str(Start_temp.date()) + " 00:00:00",
                                               "%Y-%m-%d %H:%M:%S")
                #récalcule la durée des évènements
                temp_dic_1["End_ts"] = int(datetime.timestamp(End_dt_1))
                temp_dic_1["Duration"] = temp_dic_1["End_ts"] - (temp_dic_1["Start_ts"])
                temp_dic_2["Start_ts"] = int(datetime.timestamp(Start_dt_2))
                temp_dic_2["Duration"] = (temp_dic_2["End_ts"]) - temp_dic_2["Start_ts"]
                #ajoute les deux éléments fraichement créés à une liste, et supprimme l'ancien
                l1.append(temp_dic_1)
                l1.append(temp_dic_2)
                df = df.drop(index=x, axis=0)
                c2 += 1
        print(f"{c2} elements were cleaned")

        #s'il n'y a plus d'éléments à traiter ou que le compteur dépasse 31, sort de la boucle
        if test == False :
            print("No more element to clean")
            break
        #ajoutes les évènements nouvellement créés au dataframe avant de recommencer la boucle
        d = {key: [] for key in l1[0].keys()}
        for dico in l1:
            for key in dico.keys():
                d[key].append(dico[key])

        df = pd.concat([pd.DataFrame(d), df]).sort_values(by=["Start_ts"]).reset_index()
        df = df.drop(columns="index")

    #lorsque la boucle est finie, calcule les champs manquants nécessaires
    df = df.assign(
        #date et heure de commencement
        Start_Date=list(map(lambda x: datetime.fromtimestamp(int(x)).date(), df.Start_ts)),
        Start_Time=list(map(lambda x: datetime.fromtimestamp(int(x)).time(), df.Start_ts)),
        #date et heure de fin
        End_Date=list(map(lambda x: datetime.fromtimestamp(int(x)).date(), df.End_ts)),
        End_Time=list(map(lambda x: datetime.fromtimestamp(int(x)).time(), df.End_ts)),
        #datetime de commencement et de fin
        Start_dt=list(map(lambda x: datetime.fromtimestamp(int(x)), df.Start_ts)),
        End_dt=list(map(lambda x: datetime.fromtimestamp(int(x)), df.End_ts)),
        #champ utile à l'agrégation
        Count=lambda y: [1 for _ in df.Z_PK]
    )
    #retourne le dataframe nettoyé
    return df

#fonction permettant de contrôler si un évènement a eu lieu durant une session ou non (il n'appartient pas à une session si le début et la fin de l'évènement se situent tous deux avant le début de la session ou après la fin de la session
def is_in_session(start,end,time):
    return 0 if ((start<datetime.strptime(start.strftime("%Y-%m-%d ") + time[0],"%Y-%m-%d %H:%M:%S") and end<datetime.strptime(end.strftime("%Y-%m-%d ") + time[0],"%Y-%m-%d %H:%M:%S")) or (start>datetime.strptime(start.strftime("%Y-%m-%d ") + time[1],"%Y-%m-%d %H:%M:%S") and end>datetime.strptime(end.strftime("%Y-%m-%d ") + time[1],"%Y-%m-%d %H:%M:%S"))) else 1

#fonction permettant de créer les différentes sessions d'utilisation du téléphone
def set_sessions(df) :
    l = []
    #crée 12 sessions de 2h (00:00:00-01:59:59 / 02:00:00-03:59:59 / ...)
    for x in range(12) :
        if x >= 5 :
            l.append((str(2*x) + ":00:00",str(2*x+1) + ":59:59"))
        else :
            l.append(("0" + str(2*x) + ":00:00","0" + str(2*x+1) + ":59:59","%H:%M:%S"))

    #pour chacune des sessions, contrôle si l'évènement a eu lieu durant la session (1) ou non (0)
    df = df.assign(
        Session_0=list(map(lambda x,y: is_in_session(x,y,l[0]) ,df.Start_dt,df.End_dt)),
        Session_1=list(map(lambda x,y: is_in_session(x,y,l[1]) ,df.Start_dt,df.End_dt)),
        Session_2=list(map(lambda x,y: is_in_session(x,y,l[2]) ,df.Start_dt,df.End_dt)),
        Session_3=list(map(lambda x,y: is_in_session(x,y,l[3]) ,df.Start_dt,df.End_dt)),
        Session_4=list(map(lambda x,y: is_in_session(x,y,l[4]) ,df.Start_dt,df.End_dt)),
        Session_5=list(map(lambda x,y: is_in_session(x,y,l[5]) ,df.Start_dt,df.End_dt)),
        Session_6=list(map(lambda x,y: is_in_session(x,y,l[6]) ,df.Start_dt,df.End_dt)),
        Session_7=list(map(lambda x,y: is_in_session(x,y,l[7]) ,df.Start_dt,df.End_dt)),
        Session_8=list(map(lambda x,y: is_in_session(x,y,l[8]) ,df.Start_dt,df.End_dt)),
        Session_9=list(map(lambda x,y: is_in_session(x,y,l[9]) ,df.Start_dt,df.End_dt)),
        Session_10=list(map(lambda x,y: is_in_session(x,y,l[10]) ,df.Start_dt,df.End_dt)),
        Session_11=list(map(lambda x,y: is_in_session(x,y,l[11]) ,df.Start_dt,df.End_dt))
    )

    #retourne le dataframe
    return df

#fonction permettant de créer le datframe de base pour les évènements non ponctuels
def get_default_df_knowledge_non_ponctual(Start,End,name):
    #récupère le dataframe avec tous les jours d'utilisation
    df = create_default_dataframe(Start, End)

    #créé les colonnes de 0
    df = df.assign(col_1=[0 for x in df.Date],
                   col_2=[0 for x in df.Date],
                   col_3=[0 for x in df.Date],
                   col_4=[0 for x in df.Date],
                   col_5=[0 for x in df.Date],
                   col_6=[0 for x in df.Date])

    #renomme les colonnes sous le format : nom_évènement + nom_variable
    df = df.rename(
        columns={"col_1": name + "_1_nb", "col_2": name + "_0_nb",
                 "col_3": name + "_1_duration",
                 "col_4": name + "_0_duration", "col_5": name + "_1_duration_mean",
                 "col_6": name + "_0_duration_mean"})

    #Met la date en index et retourne le dataframe
    df = df.rename(columns={"Date": "Start_Date"})
    df = df.set_index("Start_Date")

    return df

#fonction permettant d'agréger les données des évènements non ponctuels
def anonimize_knowledge_dataframe_non_ponctual_events(df,name):

    #nombre de position on
    is_on = df.loc[(df.ValueDouble != 0.0) & (df.ValueDouble != 2.0)][["Start_Date", "Count"]].groupby("Start_Date").sum("Count")
    is_on = is_on.rename(columns={"Count": name + "_1_nb"})

    # nombre de position off
    is_off = df.loc[(df.ValueDouble == 0.0) | (df.ValueDouble == 2.0)][["Start_Date", "Count"]].groupby("Start_Date").sum("Count")
    is_off = is_off.rename(columns={"Count": name + "_0_nb"})

    # durée totale en position on
    is_on_duration = df.loc[(df.ValueDouble == 1.0)][["Start_Date", "Duration"]].groupby("Start_Date").sum(
        "Duration")
    is_on_duration = is_on_duration.rename(columns={"Duration": name + "_1_duration"})

    # durée totale en position off
    is_off_duration = df.loc[(df.ValueDouble == 0.0)][["Start_Date", "Duration"]].groupby("Start_Date").sum(
        "Duration")
    is_off_duration = is_off_duration.rename(columns={"Duration": name + "_0_duration"})

    # durée moyenne en position on
    is_on_duration_mean = df.loc[(df.ValueDouble == 1.0)][["Start_Date", "Duration"]].groupby("Start_Date").mean(
        "Duration")
    is_on_duration_mean = is_on_duration_mean.rename(columns={"Duration": name + "_1_duration_mean"})

    # durée moyenne en position off
    is_off_duration_mean = df.loc[(df.ValueDouble == 0.0)][["Start_Date", "Duration"]].groupby("Start_Date").mean(
        "Duration")
    is_off_duration_mean = is_off_duration_mean.rename(columns={"Duration": name + "_0_duration_mean"})

    #regroupement des dataframe, liés par la date qui est devenue l'index via les groupby
    merge = pd.concat(
        [is_on,is_off,is_on_duration,is_off_duration,is_on_duration_mean,is_off_duration_mean],
        axis=1)
    #remplissage des éléments nuls avec des 0 et retour du dataframe
    merge = merge.fillna(0)
    return merge

#fonction permettant de créer le dataframe de base pour les éléments ponctuels
def get_default_df_knowledge_ponctual(Start,End,name):
    #création du dataframe avec les jours d'utilisation
    df = create_default_dataframe(Start, End)

    #création des colonnes de 0
    df = df.assign(col_1=[0 for x in df.Date],
                   col_2=[0 for x in df.Date],
                   col_3=[0 for x in df.Date])

    #renomme les colonnes au format : nom_évènement + nom_variable
    df = df.rename(
        columns={"col_1": name + "_event_nb", "col_2": name + "_event_duration",
                 "col_3": name + "_event_duration_mean"})

    #Met la date en index et retourne le dataframe
    df = df.rename(columns={"Date":"Start_Date"})
    df = df.set_index("Start_Date")

    return df

#fonction permettant d'agréger les données relatives aux évènements ponctuels
def anonimize_knowledge_dataframe_ponctual_events(df,name):
    #nombre d'évènements
    event = df.loc[(df.ValueDouble != 0.0)][["Start_Date", "Count"]].groupby("Start_Date").sum("Count")
    event = event.rename(columns={"Count": name + "_event_nb"})

    #durée totale des évènements
    event_duration = df.loc[(df.ValueDouble != 0.0)][["Start_Date", "Duration"]].groupby("Start_Date").sum(
        "Duration")
    event_duration = event_duration.rename(columns={"Duration": name + "_event_duration"})

    #durée moyenne des évènements
    event_duration_mean = df.loc[(df.ValueDouble != 0.0)][["Start_Date", "Duration"]].groupby("Start_Date").mean(
        "Duration")
    event_duration_mean = event_duration_mean.rename(columns={"Duration": name + "_event_duration_mean"})

    #fusion des dataframe via la date (devenue index avec les groupby)
    merge = pd.concat(
        [event,event_duration,event_duration_mean],
        axis=1)

    #remplissage des éléments nuls avec des 0 et retour du dataframe
    merge = merge.fillna(0)
    return merge

#création du dataframe de base pour les éléments notification
def get_default_df_knowledge_notification(Start,End):
    #récupération du dataframe avec les jours d'utilisation
    df = create_default_dataframe(Start, End)

    #création des colonnes de 0 (nommées correctement car les 6 noms sont connus)
    df = df.assign(Hidden=[0 for x in df.Date],
                   Receive=[0 for x in df.Date],
                   Dismiss=[0 for x in df.Date],
                   Orb=[0 for x in df.Date],
                   IndirectClear=[0 for x in df.Date],
                   DefaultAction=[0 for x in df.Date])

    #La date est mise en index et le dataframe est retourné
    df = df.rename(columns={"Date": "Start_Date"})
    df = df.set_index("Start_Date")

    return df

#fonction permettant d'agréger les données liées aux évènements notifications
def anonimize_knowledge_notification(df) :

    #nombre de notifications hidden
    Hidden = df.loc[(df.Value == "Hidden")][["Start_Date", "Count"]].groupby("Start_Date").sum("Count")
    Hidden = Hidden.rename(columns={"Count": "Hidden_nb"})

    # nombre de notifications receive
    Receive = df.loc[(df.Value == "Receive")][["Start_Date", "Count"]].groupby("Start_Date").sum("Count")
    Receive = Receive.rename(columns={"Count": "Receive_nb"})

    # nombre de notifications dismiss
    Dismiss = df.loc[(df.Value == "Dismiss")][["Start_Date", "Count"]].groupby("Start_Date").sum("Count")
    Dismiss = Dismiss.rename(columns={"Count": "Dismiss_nb"})

    # nombre de notifications orb
    Orb = df.loc[(df.Value == "Orb")][["Start_Date", "Count"]].groupby("Start_Date").sum("Count")
    Orb = Orb.rename(columns={"Count": "Orb_nb"})

    # nombre de notifications indirectclear
    IndirectClear = df.loc[(df.Value == "IndirectClear")][["Start_Date", "Count"]].groupby("Start_Date").sum("Count")
    IndirectClear = IndirectClear.rename(columns={"Count": "IndirectClear_nb"})

    # nombre de notifications defaultaction
    DefaultAction = df.loc[(df.Value == "DefaultAction")][["Start_Date", "Count"]].groupby("Start_Date").sum("Count")
    DefaultAction = DefaultAction.rename(columns={"Count": "DefaultAction_nb"})

    #fusion des dataframe via la date (mise en index par le groupby)
    merge = pd.concat(
        [Hidden,Receive,Dismiss,Orb,IndirectClear,DefaultAction],
        axis=1)

    #remplissage des éléments nuls avec des 0 et retour du dataframe
    merge = merge.fillna(0)
    return merge

#fonction permettant de créer le dataframe de base pour les données batterie et siri
def get_default_df_knowledge_percentage_siri(Start,End,name):
    #récupération du dataframe composé des jours d'utilisation
    df = create_default_dataframe(Start, End)

    #création de la colonne de 0
    df = df.assign(col_1=[0 for x in df.Date])

    #renommage de la colone (nom_évènement + nom_variable)
    df = df.rename(
        columns={"col_1": name + "_nb"})

    #Mise en index de la date et retour du dataframe
    df = df.rename(columns={"Date": "Start_Date"})
    df = df.set_index("Start_Date")

    return df

#fonction permettant d'anonimiser les données liées aux évènements batterie et siri
def anonimize_percentage_and_siri(df, name) :

    #nombre d'occurences de l'évènement
    Count = df[["Start_Date", "Count"]].groupby("Start_Date").sum("Count")
    Count = Count.rename(columns={"Count": name + "_nb"})

    #remplissage des valeurs nulles avec des 0 et retour du dataframe
    Count = Count.fillna(0)

    return Count

#fonction permettant de récupérer le datframe de base pour les évènements liés à l'utilisation d'applications
def get_default_df_knowledge_app_usage(Start,End,name) :
    #récupération du dataframe contenant les jours d'utilisation
    df = create_default_dataframe(Start, End)

    #création des colonnes de 0
    df = df.assign(col_1=[0 for x in df.Date],
                   col_2=[0 for x in df.Date],
                   col_3=[0 for x in df.Date],
                   col_4=[0 for x in df.Date],
                   col_5=[0 for x in df.Date],
                   col_6=[0 for x in df.Date],
                   col_7=[0 for x in df.Date],
                   col_8=[0 for x in df.Date],
                   col_9=[0 for x in df.Date],
                   col_10=[0 for x in df.Date],
                   col_11=[0 for x in df.Date],
                   col_12=[0 for x in df.Date])

    #renommage des colonnes (nom_évènement + nom_variable)
    df = df.rename(
        columns={"col_1": name + "_Session_0", "col_2": name + "_Session_1", "col_3": name + "_Session_2",
                 "col_4": name + "_Session_3", "col_5": name + "_Session_4",
                 "col_6": name + "_Session_5",
                 "col_7": name + "_Session_6", "col_8": name + "_Session_7",
                 "col_9": name + "_Session_8",
                 "col_10": name + "_Session_9", "col_11": name + "_Session_10","col_12":name + "_Session_11"})

    #Mise en index de la date et retour du dataframe
    df = df.rename(columns={"Date": "Start_Date"})
    df = df.set_index("Start_Date")

    return df

#fonction permettant d'agréger les données liées aux évènements d'utilisation des applications
def anonimize_app_usage(df,name) :
    #utilisation du téléphone dans la session 0
    Session_0 = df[["Start_Date","Session_0"]].groupby("Start_Date").sum("Count")
    Session_0 = Session_0.assign(Session_0=list(map(lambda x : 1 if int(x)>0 else 0,Session_0.Session_0)))
    Session_0 = Session_0.rename(columns={"Session_0" : name + "_Session_0"})

    # utilisation du téléphone dans la session 1
    Session_1 = df[["Start_Date", "Session_1"]].groupby("Start_Date").sum("Count")
    Session_1 = Session_1.assign(Session_1=list(map(lambda x: 1 if int(x) > 0 else 0, Session_1.Session_1)))
    Session_1 = Session_1.rename(columns={"Session_1": name + "_Session_1"})

    # utilisation du téléphone dans la session 2
    Session_2 = df[["Start_Date", "Session_2"]].groupby("Start_Date").sum("Count")
    Session_2 = Session_2.assign(Session_2=list(map(lambda x: 1 if int(x) > 0 else 0, Session_2.Session_2)))
    Session_2 = Session_2.rename(columns={"Session_2": name + "_Session_2"})

    # utilisation du téléphone dans la session 3
    Session_3 = df[["Start_Date", "Session_3"]].groupby("Start_Date").sum("Count")
    Session_3 = Session_3.assign(Session_3=list(map(lambda x: 1 if int(x) > 0 else 0, Session_3.Session_3)))
    Session_3 = Session_3.rename(columns={"Session_3": name + "_Session_3"})

    # utilisation du téléphone dans la session 4
    Session_4 = df[["Start_Date", "Session_4"]].groupby("Start_Date").sum("Count")
    Session_4 = Session_4.assign(Session_4=list(map(lambda x: 1 if int(x) > 0 else 0, Session_4.Session_4)))
    Session_4 = Session_4.rename(columns={"Session_4": name + "_Session_4"})

    # utilisation du téléphone dans la session 5
    Session_5 = df[["Start_Date", "Session_5"]].groupby("Start_Date").sum("Count")
    Session_5 = Session_5.assign(Session_5=list(map(lambda x: 1 if int(x) > 0 else 0, Session_5.Session_5)))
    Session_5 = Session_5.rename(columns={"Session_5": name + "_Session_5"})

    # utilisation du téléphone dans la session 6
    Session_6 = df[["Start_Date", "Session_6"]].groupby("Start_Date").sum("Count")
    Session_6 = Session_6.assign(Session_6=list(map(lambda x: 1 if int(x) > 0 else 0, Session_6.Session_6)))
    Session_6 = Session_6.rename(columns={"Session_6": name + "_Session_6"})

    # utilisation du téléphone dans la session 7
    Session_7 = df[["Start_Date", "Session_7"]].groupby("Start_Date").sum("Count")
    Session_7 = Session_7.assign(Session_7=list(map(lambda x: 1 if int(x) > 0 else 0, Session_7.Session_7)))
    Session_7 = Session_7.rename(columns={"Session_7": name + "_Session_7"})

    # utilisation du téléphone dans la session 8
    Session_8 = df[["Start_Date", "Session_8"]].groupby("Start_Date").sum("Count")
    Session_8 = Session_8.assign(Session_8=list(map(lambda x: 1 if int(x) > 0 else 0, Session_8.Session_8)))
    Session_8 = Session_8.rename(columns={"Session_8": name + "_Session_8"})

    # utilisation du téléphone dans la session 9
    Session_9 = df[["Start_Date", "Session_9"]].groupby("Start_Date").sum("Count")
    Session_9 = Session_9.assign(Session_9=list(map(lambda x: 1 if int(x) > 0 else 0, Session_9.Session_9)))
    Session_9 = Session_9.rename(columns={"Session_9": name + "_Session_9"})

    # utilisation du téléphone dans la session 10
    Session_10 = df[["Start_Date", "Session_10"]].groupby("Start_Date").sum("Count")
    Session_10 = Session_10.assign(Session_10=list(map(lambda x: 1 if int(x) > 0 else 0, Session_10.Session_10)))
    Session_10 = Session_10.rename(columns={"Session_10": name + "_Session_10"})

    # utilisation du téléphone dans la session 11
    Session_11 = df[["Start_Date", "Session_11"]].groupby("Start_Date").sum("Count")
    Session_11 = Session_11.assign(Session_11=list(map(lambda x: 1 if int(x) > 0 else 0, Session_11.Session_11)))
    Session_11 = Session_11.rename(columns={"Session_11": name + "_Session_11"})

    #fusion des dataframe via la date (mise en index par les groupby)
    merge = pd.concat(
        [Session_0,Session_1,Session_2,Session_3,Session_4,Session_5,Session_6,Session_7,Session_8,Session_9,Session_10,Session_11],
        axis=1)
    #remplissage des éléments vides avec des 0 et retour du dataframe
    merge = merge.fillna(0)
    return merge

#fonction permettant de récupérer les évènements de knowledgec, puis de les agréger
def KnowledgeC_Events(Start,End,path) :
    print("Start KnowledgeC events")
    #requête SQLite
    print(path)
    db = sqlite3.connect(path)
    df = pd.read_sql_query('SELECT ZOBJECT.Z_PK, (ZOBJECT.ZSTARTDATE + 978307200) as "Start_ts", datetime((ZOBJECT.ZSTARTDATE) + 978307200,"unixepoch") as "Start_dt", (ZOBJECT.ZENDDATE + 978307200) as "End_ts",datetime((ZOBJECT.ZENDDATE) + 978307200,"unixepoch") as "End_dt", (ZOBJECT.ZENDDATE-ZOBJECT.ZSTARTDATE) as "Duration", ZOBJECT.ZSTREAMNAME as "Name", ZOBJECT.ZVALUESTRING as "Value", ZOBJECT.ZVALUEDOUBLE as "ValueDouble" FROM ZOBJECT ORDER BY Start_ts',
                           db)
    db.close()

    #nettoyage du dataframe
    df = set_time_and_sort(df)

    #création des sessions
    df = set_sessions(df)

    #récupération des évènements ayant eu lieu durant la période d'utilisation
    df = df.loc[(df.Start_Date>=Start) & (df.End_Date<=End)]

    #récupération des évènements "/display/orientation"
    #si le dataframe est vide, récupère le dataframe de base pour les évènements non ponctuels, sinon récupère le dataframe des données agrégées
    df_orientation = df.loc[(df.Name=="/display/orientation")]
    if len(df_orientation) ==0 :
        df_orientation = get_default_df_knowledge_non_ponctual(Start,End,"orientation")
    else :
        df_orientation = anonimize_knowledge_dataframe_non_ponctual_events(df_orientation,"orientation")

    # récupération des évènements "/device/isPluggedIn"
    # si le dataframe est vide, récupère le dataframe de base pour les évènements non ponctuels, sinon récupère le dataframe des données agrégées
    df_plugged = df.loc[(df.Name=="/device/isPluggedIn")]
    if len(df_plugged)==0 :
        df_plugged = get_default_df_knowledge_non_ponctual(Start,End,"isPlugged")
    else :
        df_plugged = anonimize_knowledge_dataframe_non_ponctual_events(df_plugged,"isPlugged")

    # récupération des évènements "/display/isBacklit"
    # si le dataframe est vide, récupère le dataframe de base pour les évènements non ponctuels, sinon récupère le dataframe des données agrégées
    df_isbacklit = df.loc[(df.Name=="/display/isBacklit")]
    if len(df_isbacklit)==0 :
        df_isbacklit = get_default_df_knowledge_non_ponctual(Start,End,"isBacklit")
    else :
        df_isbacklit = anonimize_knowledge_dataframe_non_ponctual_events(df_isbacklit,"isBacklit")

    # récupération des évènements "/device/isLocked"
    # si le dataframe est vide, récupère le dataframe de base pour les évènements non ponctuels, sinon récupère le dataframe des données agrégées
    df_islocked = df.loc[(df.Name=="/device/isLocked")]
    if len(df_islocked) == 0 :
        df_islocked = get_default_df_knowledge_non_ponctual(Start,End,"isLocked")
    else :
        df_islocked = anonimize_knowledge_dataframe_non_ponctual_events(df_islocked,"isLocked")

    # récupération des évènements "/system/airplaneMode"
    # si le dataframe est vide, récupère le dataframe de base pour les évènements non ponctuels, sinon récupère le dataframe des données agrégées
    df_airplane = df.loc[(df.Name=="/system/airplaneMode")]
    if len(df_airplane)==0:
        df_airplane = get_default_df_knowledge_non_ponctual(Start,End,"airplaneMode")
    else :
        df_airplane = anonimize_knowledge_dataframe_non_ponctual_events(df_airplane,"airplaneMode")

    # récupération des évènements "/wifi/connection"
    # si le dataframe est vide, récupère le dataframe de base pour les évènements ponctuels, sinon récupère le dataframe des données agrégées
    df_wifi = df.loc[(df.Name=="/wifi/connection")]
    if len(df_wifi)==0 :
        df_wifi = get_default_df_knowledge_ponctual(Start,End,"wifi")
    else :
        df_wifi = anonimize_knowledge_dataframe_ponctual_events(df_wifi,"wifi")

    # récupération des évènements "/bluetooth/isConnected"
    # si le dataframe est vide, récupère le dataframe de base pour les évènements non ponctuels, sinon récupère le dataframe des données agrégées
    df_bluetooth = df.loc[(df.Name=="/bluetooth/isConnected")]
    if len(df_bluetooth) == 0 :
        df_bluetooth = get_default_df_knowledge_non_ponctual(Start,End,"Bluetooth")
    else :
        df_bluetooth = anonimize_knowledge_dataframe_non_ponctual_events(df_bluetooth,"Bluetooth")

    # récupération des évènements "/device/batterySaver"
    # si le dataframe est vide, récupère le dataframe de base pour les évènements ponctuels, sinon récupère le dataframe des données agrégées
    df_batterysaver = df.loc[(df.Name=="/device/batterySaver")]
    if len(df_batterysaver)==0:
        df_batterysaver = get_default_df_knowledge_ponctual(Start,End,"batterySaver")
    else :
        df_batterysaver = anonimize_knowledge_dataframe_ponctual_events(df_batterysaver,"batterySaver")

    # récupération des évènements "/audio/outputRoute"
    # si le dataframe est vide, récupère le dataframe de base pour les évènements non ponctuels, sinon récupère le dataframe des données agrégées
    df_audiooutput = df.loc[(df.Name=="/audio/outputRoute")]
    if len(df_audiooutput)==0:
        df_audiooutput = get_default_df_knowledge_non_ponctual(Start,End,"audioOutput")
    else :
        df_audiooutput = anonimize_knowledge_dataframe_non_ponctual_events(df_audiooutput,"audioOutput")

    # récupération des évènements "/audio/inputRoute"
    # si le dataframe est vide, récupère le dataframe de base pour les évènements non ponctuels, sinon récupère le dataframe des données agrégées
    df_audioinput = df.loc[(df.Name=="/audio/inputRoute")]
    if len(df_audioinput)==0:
        df_audioinput = get_default_df_knowledge_non_ponctual(Start,End,"audioInput")
    else :
        df_audioinput = anonimize_knowledge_dataframe_non_ponctual_events(df_audioinput,"audioInput")

    # récupération des évènements notification
    # si le dataframe est vide, récupère le dataframe de base pour les évènements notifications, sinon récupère le dataframe des données agrégées
    df_notificationusage = df.loc[(df.Name=="/notification/usage")]
    if len(df_notificationusage) == 0 :
        df_notificationusage = get_default_df_knowledge_notification(Start,End)
    else:
        df_notificationusage = anonimize_knowledge_notification(df_notificationusage)

    # récupération des évènements "/device/lowPowerMode"
    # si le dataframe est vide, récupère le dataframe de base pour les évènements non ponctuels, sinon récupère le dataframe des données agrégées
    df_lowpowermode = df.loc[(df.Name=="/device/lowPowerMode")]
    if len(df_lowpowermode)==0:
        df_lowpowermode = get_default_df_knowledge_non_ponctual(Start,End,"lowPowermode")
    else :
        df_lowpowermode = anonimize_knowledge_dataframe_non_ponctual_events(df_lowpowermode,"lowPowermode")

    # récupération des évènements batterie
    # si le dataframe est vide, récupère le dataframe de base pour les évènements batterie et siri, sinon récupère le dataframe des données agrégées
    df_batterypercentage = df.loc[(df.Name=="/device/batteryPercentage")]
    if len(df_batterypercentage) == 0:
        df_batterypercentage = get_default_df_knowledge_percentage_siri(Start,End,"batteryPercentage")
    else :
        df_batterypercentage = anonimize_percentage_and_siri(df_batterypercentage,"batteryPercentage")

    # récupération des évènements siri
    # si le dataframe est vide, récupère le dataframe de base pour les évènements batterie et siri, sinon récupère le dataframe des données agrégées
    df_siri = df.loc[(df.Name=="/siri/ui")]
    if len(df_siri)==0:
        df_siri = get_default_df_knowledge_percentage_siri(Start,End,"siri")
    else :
        df_siri = anonimize_percentage_and_siri(df_siri,"siri")

    # récupération des évènements "/media/nowPlaying"
    # si le dataframe est vide, récupère le dataframe de base pour les évènements non ponctuels, sinon récupère le dataframe des données agrégées
    df_mediaplaying = df.loc[(df.Name=="/media/nowPlaying")]
    if len(df_mediaplaying)==0 :
        df_mediaplaying = get_default_df_knowledge_non_ponctual(Start,End,"mediaPlaying")
    else :
        df_mediaplaying = anonimize_knowledge_dataframe_non_ponctual_events(df_mediaplaying,"mediaPlaying")

    # récupération des évènements "/app/usage"
    # si le dataframe est vide, récupère le dataframe de base pour les évènements ponctuels et pour les évènements d'utilisation d'applications,
    # sinon récupère les dataframes des données agrégées
    df_appusage = df.loc[(df.Name=="/app/usage")]
    if len(df_appusage)==0 :
        df_appusage_1 = get_default_df_knowledge_app_usage(Start,End,"appUsage")
        df_appusage_2 = get_default_df_knowledge_ponctual(Start,End,"appUsage")
    else :
        df_appusage_1 = anonimize_app_usage(df_appusage,"appUsage")
        df_appusage_2 = anonimize_knowledge_dataframe_ponctual_events(df_appusage,"appUsage")

    # récupération des évènements "/app/inFocus"
    # si le dataframe est vide, récupère le dataframe de base pour les évènements ponctuels et pour les évènements d'utilisation d'applications,
    # sinon récupère les dataframes des données agrégées
    df_appinfocus = df.loc[(df.Name=="/app/inFocus")]
    if len(df_appinfocus)==0 :
        df_appinfocus_1 = get_default_df_knowledge_app_usage(Start,End,"appInfocus")
        df_appinfocus_2 = get_default_df_knowledge_ponctual(Start,End,"appInfocus")
    else :
        df_appinfocus_1 = anonimize_app_usage(df_appinfocus,"appInfocus")
        df_appinfocus_2 = anonimize_knowledge_dataframe_ponctual_events(df_appinfocus,"appInfocus")

    #fusion de tous les dataframe via la date (qui a été mise en index par les groupby)
    merge = pd.concat(
        [df_orientation,df_plugged,df_isbacklit,df_islocked,df_airplane,df_wifi,df_bluetooth,df_batterysaver,df_audioinput,
         df_audiooutput,df_notificationusage,df_lowpowermode,df_batterypercentage,df_siri,df_mediaplaying,df_appusage_1,
         df_appusage_2,df_appinfocus_1,df_appinfocus_2],
        axis=1)

    #remplissage des éléments nuls avec des 0
    merge = merge.fillna(0)
    #Mise en index de la date
    merge = merge.reset_index()
    merge = merge.rename(columns={"Start_Date" : "Date"})
    merge = merge.set_index("Date")

    #enregistrement dans un csv et retour du dataframe
    merge.to_csv("knowledge.csv")

    return merge

#fonction permettant de récupérer le dataframe de base pour les données liées au lockdown
def get_default_df_lockdown(Start,End):
    #récupération du dataframe contenant les jours d'utilisation
    df = create_default_dataframe(Start,End)

    #création de la colonne de 0
    df = df.assign(Starting_up_nb=[0 for x in df.Date])

    #mise en index de la date et retour du dataframe
    df = df.set_index("Date")
    return df

#fonction permettant de récupéréer les données liées au lockdown, de calculer les champs manquants et d'agréger les données
def Lockdown(Start,End,path):
    #si le chemin vaut 0, la base de données est indisponible et le dataframe de base pour le lockdown est retourné
    if path == 0  :
        return get_default_df_lockdown(Start,End)

    day = []
    count = []
    f = open(path)
    #ouvre le fichier lockdown et parcourt les lignes
    for x in f.readlines() :
        #s'il y a "main: Starting Up" dans la ligne, récupère la date et ajoute 1 au compteur
        if "main: Starting Up" in x :
            y = x.split(" ")[0] + " " + x.split(" ")[1].split(".")[0]
            z = datetime.strptime(y,"%m/%d/%y %H:%M:%S")
            day.append(z)
            count.append(1)
        else :
            pass
    #créé un dataframe avec toutes les informations sur les mises en route du téléphone
    data_lockdown = {"Date_dt": day, "Count": count, "Date_ts": list(map(lambda x : x.timestamp(),day))}
    df = pd.DataFrame(data_lockdown)

    #si le dataframe là est vide, retourne celui de base pour les données lockdown
    if len(df) == 0  :
        return get_default_df_lockdown(Start,End)

    #calcule la date et l'heure pour chaque évènement
    df = df.assign(Date=list(map(lambda x: datetime.fromtimestamp(int(x)).date(), df.Date_ts)),
        Time=list(map(lambda x: datetime.fromtimestamp(int(x)).time(), df.Date_ts)))

    # si le dataframe ne contient aucun élément durant la période d'utilisation, retourne celui de base pour les données lockdown
    if len(df.loc[(df.Date>=Start) & (df.Date<=End)]) == 0  :
        return get_default_df_lockdown(Start,End)

    #nombre d'allumages du téléphone
    df_anonimized = df.loc[(df.Date>=Start) & (df.Date<=End)][["Date","Count"]].groupby("Date").sum("Count")
    df_anonimized = df_anonimized.rename(columns={"Count" : "Starting_up_nb"})

    #enregistre le dataframe et le retourne
    df_anonimized.to_csv("lockdown.csv")
    return df_anonimized

if __name__ == '__main__':
    #Date du début de l'utilisation au format "dd.mm.yy à hh:mm:ss"
    Start = datetime.strptime("06.04.22 à 00:00:00","%d.%m.%y à %H:%M:%S").date()
    # Date de fin de l'utilisation au format "dd.mm.yy à hh:mm:ss"
    End = datetime.strptime("06.04.22 à 23:59:59", "%d.%m.%y à %H:%M:%S").date()
    #id messenger de l'utilisateur si messenger est installé, sinon 0
    #chemin du dossier contenant les différents dossiers dans lesquels sont stockées les fichiers et bases de données
    Base_path = ""
    # même chemin qu'avant mais en brut
    Brut_base_path = r""
    #id de l'utilisateur
    id_user = 2
    #id du téléphone
    id_phone = 2


    #appelle toutes les fonctions qui récupèrent les données, calcule les champ manquants et agrègent les données
    #il faut donner la date de début d'utilisation, la date de fin d'utilisation et le chemin des bases de données
    #si la base de données n'est pas disponible ou n'existe pas, il faut mettre 0
    #pour certaines fonctions, il faur donner des paramètres en plus (ud_messenger ou liste des mails)
    print("début du programme : " + str(datetime.now()))
    kn = KnowledgeC_Events(Start,End,Base_path + "/knowledgeC.db")
    lo = Lockdown(Start,End,Base_path + "/lockdownd.log")


    #fusionne tous les dataframe (via la date)
    merge = pd.concat([kn,lo],axis=1)

    #rempli les éléments nuls de 0
    merge = merge.fillna(0)

    #enregistre le dataframe final dans un fichier csv
    merge.to_csv("anonimized_data_user_" + str(id_user) + "_phone_" + str(id_phone) +"_2.csv")
    print("fin programme : " +str(datetime.now()))



#Auteur : Michelet Gaëtan
#Adapted by Hannes Spichiger