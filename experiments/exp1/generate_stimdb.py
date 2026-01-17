import json
import os
import re
import sqlite3

exp_cond = "control2"
rootdir = "../experiments/" + exp_cond

def get_x_result(jdict):
    radius = jdict["world"]["objects"]["FOCUS"]["radius"]
    for step in jdict["displayPath"]["FOCUS"]:
        if step[1] - radius < 6.5:
            return step[0]


def generate_targets():
    con = sqlite3.connect(rootdir + "/assets/stims.db")
    cursor = con.cursor()
    cursor.execute("drop table if exists worlds")
    cursor.execute("drop table if exists stims")
    cursor.execute(
        "create table worlds(id integer primary key, world, worldtype, count, sim_x_result)"
    )
    cursor.execute(
        "create table stims(id integer primary key,world, cond, img, baseImgRed, baseImgBlue, modifiedImgRed, modifiedImgBlue, recording, filler, count)"
    )

    conds = {
        "maybe": [
            "col_early_translate",
            "nocol_translate",
            "maybecol_translate",
        ],
        "definite": [
            "col_early_translate",
            "nocol_translate",
            "col_late_translate",
        ],
    }
    for dir in os.listdir(rootdir + "/assets/targets"):
        with open(f"{rootdir}/assets/targets/{dir}/{dir}.json") as f:
            jdict = json.load(f)

        cursor.execute(
            "insert into worlds (world, worldtype, count, sim_x_result) values (?,?,0,?)",
            (
                dir,
                jdict["worldType"],
                get_x_result(jdict),
            ),
        )
        con.commit()
        try:
            for cond in conds[jdict["worldType"]]:
                generate_stimuli(dir, cond, cursor, con)
        except:
            print(dir)
    con.close()


def generate_stimuli(world, cond, cursor, con):
    root = "_".join(cond.split("_")[:-1])
    modified_files = set()
    for f in os.listdir(f"{rootdir}/assets/targets/" + world):
        match = re.match(f"({cond}\d?)", f)
        if match:
            modified_files.add(match.group(1))
    for modified_file in modified_files:
        cursor.execute(
            """
        insert into stims (world, cond, img, baseImgRed, baseImgBlue, modifiedImgRed, modifiedImgBlue, recording, filler, count)
        values (?,?,?,?,?,?,?,?,0,0)""",
            (
                world,
                cond,
                f"{exp_cond}/assets/targets/{world}/img.jpg",
                f"{exp_cond}/assets/targets/{world}/{root + '_basered.jpg'}",
                f"{exp_cond}/assets/targets/{world}/{root + '_baseblue.jpg'}",
                f"{exp_cond}/assets/targets/{world}/{modified_file}red.jpg",
                f"{exp_cond}/assets/targets/{world}/{modified_file}blue.jpg",
                f"{exp_cond}/assets/targets/{world}/{cond}.mp4",
            ),
        )
        con.commit()
    print(cond)


def generate_fillers():
    out = []
    files = set(f.split(".")[0] for f in os.listdir(f"{rootdir}/assets/fillers"))
    for fname in files:
        with open(f"{rootdir}/assets/fillers/{fname}.json") as f:
            jdict = json.load(f)
        out.append(
            {
                "img": f"{exp_cond}/assets/fillers/{fname}.jpg",
                "recording": f"{exp_cond}/assets/fillers/{fname}.mp4",
                "sim_x_result": get_x_result(jdict),
                "filler": True,
                "catch": False,
            }
        )
    with open(f"{rootdir}/assets/fillers.json", "w") as f:
        json.dump(out, f)


def generate_catch():
    out = []
    files = set(f.split(".")[0] for f in os.listdir(f"{rootdir}/assets/catch"))
    for fname in files:
        with open(f"{rootdir}/assets/catch/" + fname + ".json") as f:
            jdict = json.load(f)
        out.append(
            {
                "img": f"{exp_cond}/assets/catch/{fname}.jpg",
                "recording": f"{exp_cond}/assets/catch/{fname}.mp4",
                "sim_x_result": get_x_result(jdict),
                "filler": True,
                "catch": True,
            }
        )
    with open(f"{rootdir}/assets/catch.json", "w") as f:
        json.dump(out, f)


# def generate_counterfactuals():
#     out = []
#     os.system("mkdir assets/counterfactuals")
#     dirs = os.listdir("assets/targets")
#     for dir in dirs:
#         with open(f"assets/{dir}/{dir}.json") as f:
#             jdict = json.load(f)
#         for cond in ["col_early", "col_late", "maybecol", "nocol"]:
#             file = f"assets/{dir}/{dir}/{cond}_translate.json"
#             if os.path.exists(file):
#                 with open(file) as f:
#                     transform = json.load(f)




if __name__ == "__main__":
    out = generate_targets()
    out = generate_catch()
    out = generate_fillers()
    # out = generate_counterfactuals()
