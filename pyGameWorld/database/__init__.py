import pymysql
import pymysql.cursors
import json

__all__ = ['openConnection','closeConnection','downloadTrialFromConnection','downloadTrials']

def openConnection(cfgfl):
    with open(cfgfl,'rU') as cfl:
        cfg = json.load(cfl)
    return pymysql.connect(**cfg)

def closeConnection(conn):
    conn.close()

def downloadTrialFromConnection(trialname, conn, old_list=False):
    if not old_list:
        qry = '''Select `TrialData` FROM `trial_list` WHERE `TrialName` = '%s';''' % trialname
    else:
        qry = '''Select `TrialData` FROM `old_trial_list` WHERE `TrialName` = '%s';''' % trialname
    curs = conn.cursor()
    curs.execute(qry)

    nr = 0
    for dat, in curs:
        nr += 1

    if nr > 1:
        raise Exception('Uh oh... more than one trial of that name found: ' + trialname)
    elif nr == 0:
        raise Exception('No trial of that name found: ' + trialname)

    return json.loads(dat)

def downloadTrials(trialnames, conn_cfg, old_list=False):
    conn = openConnection(conn_cfg)
    trs = dict()
    for trn in trialnames:
        trs[trn] = downloadTrialFromConnection(trn, conn, old_list=old_list)
    conn.close()
    return trs
