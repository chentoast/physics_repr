import json
import os
import re
import sqlite3

exp_cond = "exp1_binary"
rootdir = "../experiments/" + exp_cond

def get_x_result(jdict):
    radius = jdict["world"]["objects"]["FOCUS"]["radius"]
    for step in jdict["displayPath"]["FOCUS"]:
        if step[1] - radius < 6.5:
            return step[0]

def get_x_result_binary(jdict):
    path = jdict["displayPath"]["FOCUS"]
    return path[-1][0]


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
                "world": fname,
                "img": f"assets/fillers/{fname}.jpg",
                "recording": f"assets/fillers/{fname}.mp4",
                "sim_x_result": get_x_result(jdict),
                "filler": True,
                "catch": False,
            }
        )
    with open(f"{rootdir}/assets/fillers.json", "w") as f:
        json.dump(out, f)


def generate_catch():
    out = []
    # files = set(f.split(".")[0] for f in os.listdir(f"{rootdir}/assets/catch"))
    files = ["catch1", "catch2"]
    for fname in files:
        with open(f"{rootdir}/assets/catch/" + fname + ".json") as f:
            jdict = json.load(f)
        out.append(
            {
                "world": fname,
                "img": f"assets/catch/{fname}.jpg",
                "recording": f"assets/catch/{fname}.mp4",
                "sim_x_result": get_x_result(jdict),
                "filler": True,
                "catch": True,
            }
        )
    with open(f"{rootdir}/assets/catch.json", "w") as f:
        json.dump(out, f)

def generate_target_stimuli_json():
    # used for exp1_binary
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

    targets = []

    for dir in os.listdir(rootdir + "/assets/targets"):
        if not os.path.isdir(f"{rootdir}/assets/targets/{dir}"):
            continue

        with open(f"{rootdir}/assets/targets/{dir}/{dir}.json") as f:
            jdict = json.load(f)

        world = dir
        worldtype = jdict["worldType"]
        sim_x_result = get_x_result_binary(jdict)

        stim = {
                "world": world,
                "worldtype": worldtype,
                "sim_x_result": sim_x_result,
                "img": f"assets/targets/{world}/img.jpg",
                "recording": f"assets/targets/{world}/recording.mp4",
                "filler": False,
                "catch": False,
        }


        for cond in conds[worldtype]:
            cond_root = "_".join(cond.split("_")[:-1])

            with open(f"{rootdir}/assets/targets/{world}/{cond_root}_basered.json") as f:
                obj_name = json.load(f)["object"]

            stim.update({
                f"{cond}_baseImgRed": f"assets/targets/{world}/{cond_root}_basered.jpg",
                f"{cond}_baseImgBlue": f"assets/targets/{world}/{cond_root}_baseblue.jpg",
                f"{cond}_modifiedImgRed0": f"assets/targets/{world}/{cond_root}_translatered.jpg",
                f"{cond}_modifiedImgBlue0": f"assets/targets/{world}/{cond_root}_translateblue.jpg",
                f"{cond}_modifiedImgRed1": f"assets/targets/{world}/{cond_root}_translate1red.jpg",
                f"{cond}_modifiedImgBlue1": f"assets/targets/{world}/{cond_root}_translate1blue.jpg",
                f"{cond}_count0": 0,
                f"{cond}_count1": 0,
                f"{cond}_object": obj_name,
            })
            # (world, cond, img, baseImgRed, baseImgBlue, modifiedImgRed, modifiedImgBlue, recording, filler, count)

        targets.append(stim)

    return targets


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
    pass
    # out = generate_targets()
    out = generate_catch()
    # out = generate_fillers()
    # out = generate_counterfactuals()
    # targets = generate_target_stimuli_json()

    # with open(f"{rootdir}/assets/targets.json", "w") as f:
    #     json.dump(targets, f, indent=2)


    # from record import save_image, record

    # with open("./plinko/exp1_demos/demo.json") as f:
    #     jdict = json.load(f)

    # save_image(jdict, f"{rootdir}/assets/demo.jpg")
    # record(jdict, f"{rootdir}/assets/", outfile="demo.mp4")

    # with open("./plinko/exp1_demos/demo1.json") as f:
    #     jdict = json.load(f)

    # save_image(jdict, f"{rootdir}/assets/demo1.jpg")
    # record(jdict, f"{rootdir}/assets/", outfile="demo1.mp4")

    # with open("./plinko/exp1_demos/catch1.json") as f:
    #     jdict = json.load(f)

    # save_image(jdict, f"{rootdir}/assets/catch/catch1.jpg")
    # record(jdict, f"{rootdir}/assets/catch/", outfile="catch1.mp4")
    # os.system(f"cp ./plinko/exp1_demos/catch1.json {rootdir}/assets/catch/catch1.json")

    # with open("./plinko/exp1_demos/catch2.json") as f:
    #     jdict = json.load(f)

    # os.system(f"cp ./plinko/exp1_demos/catch2.json {rootdir}/assets/catch/catch2.json")
    # save_image(jdict, f"{rootdir}/assets/catch/catch2.jpg")
    # record(jdict, f"{rootdir}/assets/catch/", outfile="catch2.mp4")