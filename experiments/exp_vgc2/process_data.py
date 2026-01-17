import os
import json
import sqlite3
import sys

import pandas as pd

exp_name = sys.path[0].split("/")[-1]

def extract_predictions(data, out, mapping={}):
    remove_keys = {"trial_type", "trial_index", "time_elapsed", "stimulus", "type"}
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

# def extract_memory(data, out, mapping={}):
#     remove_keys = {"trial_type", "trial_index", "time_elapsed", "stimulus", "type", "slider_start", "study_id", "session_id"}
#     trial_num = 0
#     for trial in data["trials"]:
#         # print(trial.get("type", ""))
#         if trial.get("type", "") != "probe":
#             continue
#         out.setdefault("trial", []).append(trial_num)
#         for k, v in trial.items():
#             if k in remove_keys:
#                 continue
#             if k in mapping:
#                 k = mapping[k]
#             out.setdefault(k, []).append(v)
#         trial_num += 1

def save(outdir, likelihood, predictions, misc):
    outdir = "../../data/" + outdir
    if not os.path.exists(outdir):
        os.system(f"mkdir {outdir}")
    predictions.to_csv(os.path.normpath(outdir) + "/predictions.csv", index=False)
    # misc.to_csv(outdir + "misc.csv")

con = sqlite3.connect("../participants.db")

memory = {}
predictions = {}
misc = []

for i, row in enumerate(con.execute(f"select data from {exp_name}")):
    data = json.loads(row[0])

    extract_predictions(data, predictions, mapping={"subject_id": "pid"})
    # extract_memory(data, memory, mapping={"subject_id": "pid"})
    misc.append(extract_misc(data))

memory = pd.DataFrame(memory)
predictions = pd.DataFrame(predictions)

# memory["correct_conf"] = memory.apply(lambda x: 100 - x.response if x.answer == 0 else x.response, axis=1)
# memory["correct"] = (memory.response > 50).astype(int) == memory.answer & (memory.response != 50)

to_save = sys.argv[-1]
if to_save == "save":
    save(exp_name, memory, predictions, misc)