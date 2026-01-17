import os
import json
import sqlite3

import pandas as pd

def extract_predictions(data):
    remove_keys = {"trial_type", "trial_index", "time_elapsed", "stimulus", "type", "subject_id", "study_id", "session_id"}
    out = {}
    idx = 0
    for trial in data["trials"]:
        if trial.get("type", None) == "prediction":
            out.update({f"{k}{idx}": v for k, v in sorted(trial.items()) if k not in remove_keys})
            idx += 1

    out["pid"] = data["trials"][-1].get("subject_id", None)
    return out

def extract_predictions(data, out, mapping={}):
    remove_keys = {"trial_type", "trial_index", "time_elapsed", "stimulus", "type", "slider_start", "study_id", "session_id",
                   "obj_name", "obj_cond", "worldtype", "img0", "img1", "bg_cond", "cond", "count"}
    trial_num = 0
    for trial in data["trials"]:
        if trial.get("type", "") == "prediction":
            out.setdefault("trial", []).append(trial_num)
            for k, v in trial.items():
                if k in remove_keys:
                    continue
                if k in mapping:
                    k = mapping[k]
                out.setdefault(k, []).append(v)
            trial_num += 1
        elif trial.get("type", "") == "show_points":
            out.setdefault("points", []).append(trial["points"])

def extract_misc(data):
    out = []
    for trial in data["trials"]:
        if trial.get("trial_type", None) == "survey-text":
            out.append(trial["response"])
    return out

def extract_memory(data, out, mapping={}):
    remove_keys = {"trial_type", "trial_index", "time_elapsed", "stimulus", "type", "slider_start", "study_id", "session_id"}
    trial_num = 0
    for trial in data["trials"]:
        # print(trial.get("type", ""))
        if trial.get("type", "") != "probe":
            continue
        out.setdefault("trial", []).append(trial_num)
        for k, v in trial.items():
            if k in remove_keys:
                continue
            if k in mapping:
                k = mapping[k]
            out.setdefault(k, []).append(v)
        trial_num += 1

def save(outdir, memory, predictions, misc):
    outdir = "../../data/" + outdir
    if not os.path.exists(outdir):
        os.system(f"mkdir {outdir}")
    memory.to_csv(os.path.normpath(outdir) + "/memory.csv", index=False)
    predictions.to_csv(os.path.normpath(outdir) + "/predictions.csv", index=False)
    # misc.to_csv(outdir + "misc.csv")

con = sqlite3.connect("../participants.db")

memory = {}
predictions = {}
misc = []

for row in con.execute("select data from exp_background"):
    data = json.loads(row[0])

    extract_predictions(data, predictions, mapping={"subject_id": "pid"})
    extract_memory(data, memory, mapping={"subject_id": "pid"})
    misc.append(extract_misc(data))

memory = pd.DataFrame(memory)
predictions = pd.DataFrame(predictions)

save("exp_background", memory, predictions, misc)

