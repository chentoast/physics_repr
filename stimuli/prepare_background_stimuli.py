import argparse
import json
import os
import random

from pygame import Color
import numpy as np
import matplotlib.pyplot as plt

import pyGameWorld as pgw
from pyGameWorld.transforms import Transform
from pyGameWorld.helpers import centroidForPoly
from create_plinko import PlinkoCreator
from record import save_image, record, dump_screen

# random.seed(1234)

with open("../stimuli/default_sim_noise.json") as f:
    defaultSimNoise = json.load(f)

target_objects = {
    "hh_hl_unlink_plinko_0105": {
        "col_early": "topbump_1",
        "maybecol": "bottombump_0",
        "nocol": "topbump_4",
    },
    "hh_hl_unlink_plinko_0202": {
        "col_early": "topbump_0",
        "maybecol": "bottombump_2",
        "nocol": "topbump_2",
    },
    "hh_hl_unlink_plinko_0240": {
        "col_early": "topbump_1",
        "maybecol": "bottombump_1",
        "nocol": "topbump_0",
    },
    "hh_hl_unlink_plinko_0246": {
        "col_early": "topbump_3",
        "maybecol": "bottombump_1",
        "nocol": "topbump_2",
    },
    "hh_hl_unlink_plinko_0252": {
        "col_early": "topbump_0",
        "maybecol": "bottombump_3",
        "nocol": "bottombump_1",
    },
    "hh_hl_unlink_plinko_0269": {
        "col_early": "topbump_0",
        "maybecol": "bottombump_0",
        "nocol": "topbump_4",
    },
    "hh_hl_unlink_plinko_0315": {
        "col_early": "topbump_1",
        "maybecol": "bottombump_1",
        "nocol": "topbump_3",
    },
    "hh_hl_unlink_plinko_0393": {
        "col_early": "topbump_2",
        "maybecol": "bottombump_3",
        "nocol": "topbump_3",
    },
    "lh_hl_unlink_plinko_0036": {
        "col_early": "topbump_0",
        "col_late": "bottombump_2",
        "nocol": "bottombump_0",
    },
    "lh_hl_unlink_plinko_0049": {
        "col_early": "topbump_1",
        "col_late": "bottombump_0",
        "nocol": "topbump_3",
    },
    "lh_hl_unlink_plinko_0110": {
        "col_early": "topbump_1",
        "col_late": "bottombump_0",
        "nocol": "topbump_0",
    },
    "lh_hl_unlink_plinko_0111": {
        "col_early": "topbump_1",
        "col_late": "bottombump_1",
        "nocol": "topbump_2",
    },
    "lh_ll_unlink_plinko_0060": {
        "col_early": "topbump_4",
        "col_late": "bottombump_1",
        "nocol": "bottombump_2",
    },
    "lh_ll_unlink_plinko_0091": {
        "col_early": "topbump_2",
        "col_late": "bottombump_1",
        "nocol": "topbump_0",
    },
    "lh_ll_unlink_plinko_0155": {
        "col_early": "topbump_2",
        "col_late": "bottombump_0",
        "nocol": "bottombump_1",
    },
    "lh_ll_unlink_plinko_0217": {
        "col_early": "topbump_4",
        "col_late": "bottombump_1",
        "nocol": "bottombump_0",
    },
}

def get_x_result(jdict):
    radius = jdict["world"]["objects"]["FOCUS"]["radius"]
    for step in jdict["displayPath"]["FOCUS"]:
        if step[1] - radius < 6.5:
            return step[0]


def iter_bumpers(objects):
    for name, obj in objects.items():
        if "bump" in name:
            yield name, obj


def assign_background_foreground(objects, p=0.3):
    # p = P(object is background)
    out = {}
    for name, _ in iter_bumpers(objects):
        out[name] = False
        if random.random() < p:
            out[name] = True
    return out


def reset(exp_name):
    outdir = f"../experiments/{exp_name}/assets/targets/*"
    os.system("rm -rf " + outdir)


def save_base_stim(world, outdir, stim_data, c1=Color("#A87E57E6"), c2=Color("#5781A8E6")):
    stim = {}
    # resimulate
    new_world = world.copy()
    for name, background in stim_data["background_objs"].items():
        if background:
            del new_world.objects[name]

    tmp = PlinkoCreator(config_file=None, world=new_world)
    tmp.run(npaths=1, noisedict=defaultSimNoise)

    out = tmp.checkAndReturn(passFailures=True)
    sim_x_result = get_x_result(out)
    stim["sim_x_result"] = sim_x_result

    colors = {}

    for i, (fgc, bgc) in enumerate(((c1, c2), (c2, c1))):
        for name, bg in stim_data["background_objs"].items():
            if bg:
                colors[name] = fgc
            else:
                colors[name] = bgc

        if stim_data["filler"]:
            outfile = f"world_{i}"
        else:
            outfile = f"{stim_data['obj_cond']}_{stim_data['bg_cond']}_{i}"
        save_image(
            {"world": world.toDict()},
            f"{outdir}/{outfile}.jpg",
            obj_colors=colors,
        )

        record(
            {
                "world": world.toDict(),
                "displayPath": out["displayPath"],
                "displayCfg": out["displayCfg"],
            },
            outdir,
            f"{outfile}.mp4",
            obj_colors=colors,
        )

        stim[f"baseimg{i}"] = "/".join((f"assets/{'fillers' if stim_data['filler'] else 'targets'}/{stim_data['world']}", outfile)) + ".jpg"
        stim[f"recording{i}"] = "/".join((f"assets/{'fillers' if stim_data['filler'] else 'targets'}/{stim_data['world']}", outfile)) + ".mp4"

    return stim, out


def create_memory_stim_separate(world, stim_data):
    def annotate(v, height):
        c = centroidForPoly(v)
        r = np.sqrt((c[0] - v[0][0]) ** 2 + (c[1] - v[0][1]) ** 2)
        theta = np.random.uniform(0, 2 * np.pi)
        plt.arrow(
            c[0] + 3 * r * np.cos(theta),
            height - c[1] - 3 * r * np.sin(theta),
            -2 * r * np.cos(theta),
            2 * r * np.sin(theta),
            length_includes_head=True,
            head_width=r / 2,
            width=3,
            color="black",
        )

    memory_colors = {}
    for name, _ in iter_bumpers(world.objects):
        memory_colors[name] = (0, 0, 0, 70)

    tworld = world.copy()
    t = Transform(tworld, tworld.objects[stim_data["object"]])
    t.translate(
        {
            "shiftx": stim_data["shiftx"],
            "shifty": stim_data["shifty"],
        }
    )

    # counterbalance colors
    memory_colors[stim_data["object"]] = (0, 0, 0, 255)
    img1 = dump_screen({"world": tworld.toDict()}, obj_colors=memory_colors)
    plt.imshow(img1)
    plt.axis("off")
    annotate(tworld.objects[stim_data["object"]].vertices, tworld.dims[1])
    yield "changed"
    # plt.savefig(f"{outdir}/{stim_data['obj_cond']}_{stim_data['bg_cond']}_memory_1_changed.jpg")
    plt.clf()

    img2 = dump_screen({"world": world.toDict()}, obj_colors=memory_colors)
    plt.imshow(img2)
    plt.axis("off")
    annotate(world.objects[stim_data["object"]].vertices, world.dims[1])
    yield "orig"
    plt.clf()


def create_memory_stim_overlay(world, stim_data):
    def annotate(c1, v1, c2, v2, height):
        # texty = 40

        r = np.sqrt((c1[0] - v1[0][0]) ** 2 + (c1[1] - v1[0][1]) ** 2) + 30
        bounds = []
        if c1[0] > c2[0]: # obj1 right of obj2
            bounds = [np.pi / 6, np.pi / 2]
        else:
            bounds = [np.pi / 2, 5 * np.pi / 6]
        if c1[1] < c2[1]: # obj1 below obj2
            bounds = [-l for l in bounds]

        theta1 = np.random.uniform(*bounds)

        x1 = r * np.cos(theta1)
        y1 = r * np.sin(theta1)
        plt.text(c1[0] + x1, height - (c1[1] + y1), "(A)", fontsize=15, c=(0, 0, 0, 0.5))

        theta2 = theta1 - np.pi

        x2 = (r) * np.cos(theta2)
        y2 = (r) * np.sin(theta2)
        print(c2[0] + x2, c2[1] + y2)
        plt.text(c2[0] + x2, height - (c2[1] + y2), "(B)", fontsize=15, c=(0, 0, 0, 0.5))
        # plt.tight_layout()

    def label_objs(obj1, obj2, height):
        v1 = obj1.vertices
        c1 = centroidForPoly(v1)
        v2 = obj2.vertices
        c2 = centroidForPoly(v2)

        annotate(c1, v1, c2, v2, height)

    memory_colors = {}
    for name, _ in iter_bumpers(world.objects):
        memory_colors[name] = (0, 0, 0, 70)
    memory_colors[stim_data["object"]] = (0, 0, 0, 255)

    tworld = world.copy()
    t = Transform(tworld, tworld.objects[stim_data["object"]])
    t.translate(
        {
            "shiftx": stim_data["shiftx"],
            "shifty": stim_data["shifty"],
        }
    )

    # counterbalance letters
    objects = [tworld.objects[stim_data["object"]], world.objects[stim_data["object"]]]
    for obj1, obj2 in (objects, reversed(objects)):
        img1 = dump_screen({"world": tworld.toDict()}, obj_colors=memory_colors, obj_widths={stim_data["object"]: 5})

        # memory_colors[stim_data["obj_name"]] = orig
        img2 = dump_screen({"world": world.toDict()}, obj_colors=memory_colors, obj_widths={stim_data["object"]: 5})

        plt.imshow(img1)
        plt.imshow(img2, alpha=0.5)
        label_objs(
            obj1,
            obj2,
            img1.shape[0]
        )
        plt.axis("off")
        yield
        plt.clf()


def save_memory_stim_overlay(
    world, wname, stim_data, outdir, c1=Color("#A87E57E6"), c2=Color("#5781A8E6")
):
    stim = {"stims": []}
    # memory stimuli - reuse the one from exp1
    with open(
        f"../experiments/exp1/assets/targets/{wname}/{stim_data['obj_cond']}_translateblue.json"
    ) as f:
        transform_dict1 = json.load(f)

    stim["transform_data1"] = transform_dict1
    stim["stims"].append(
        {"world": wname, "cond": stim_data["obj_cond"], "count": 0}
    )
    for i, _ in enumerate(create_memory_stim_overlay(world, transform_dict1)):
        outfile = f"{stim_data['obj_cond']}_{stim_data['bg_cond']}_memory_1_{i}.jpg"
        stim["stims"][-1][f"img{i}"] = f"assets/targets/{wname}/{outfile}"
        # stim["stims"][-1][f"answer{i}"] = i

        plt.tight_layout()
        plt.savefig(f"{outdir}/{outfile}")

    with open(
        f"../experiments/exp1/assets/targets/{wname}/{stim_data['obj_cond']}_translate1blue.json"
    ) as f:
        transform_dict2 = json.load(f)

    stim["transform_data2"] = transform_dict2
    stim["stims"].append(
        {"world": wname, "cond": stim_data["obj_cond"], "count": 0}
    )
    for i, _ in enumerate(create_memory_stim_overlay(world, transform_dict2)):
        outfile = f"{stim_data['obj_cond']}_{stim_data['bg_cond']}_memory_2_{i}.jpg"
        stim["stims"][-1][f"img{i}"] = f"assets/targets/{wname}/{outfile}"

        plt.tight_layout()
        plt.savefig(f"{outdir}/{outfile}")

    return stim

def save_memory_stim_separate(
    world, wname, stim_data, outdir, c1=Color("#A87E57E6"), c2=Color("#5781A8E6")
):
    stim = {"stims": []}
    # memory stimuli - reuse the one from exp1
    with open(
        f"../experiments/exp1/assets/targets/{wname}/{stim_data['obj_cond']}_translateblue.json"
    ) as f:
        transform_dict1 = json.load(f)

    stim["transform_data1"] = transform_dict1
    stim["stims"].append(
        {"world": wname, "cond": stim_data["obj_cond"], "count": 0}
    )
    for changed_or_orig in create_memory_stim_separate(world, transform_dict1):
        outfile = f"{stim_data['obj_cond']}_{stim_data['bg_cond']}_memory_1_{changed_or_orig}.jpg"
        stim["stims"][-1][changed_or_orig] = f"assets/targets/{wname}/{outfile}"

        plt.tight_layout()
        plt.savefig(f"{outdir}/{outfile}")

    with open(
        f"../experiments/exp1/assets/targets/{wname}/{stim_data['obj_cond']}_translate1blue.json"
    ) as f:
        transform_dict2 = json.load(f)

    stim["transform_data2"] = transform_dict2
    stim["stims"].append(
        {"world": wname, "cond": stim_data["obj_cond"], "count": 0}
    )
    for changed_or_orig in create_memory_stim_separate(world, transform_dict2):
        outfile = f"{stim_data['obj_cond']}_{stim_data['bg_cond']}_memory_2_{changed_or_orig}.jpg"
        stim["stims"][-1][changed_or_orig] = f"assets/targets/{wname}/{outfile}"

        plt.tight_layout()
        plt.savefig(f"{outdir}/{outfile}")

    return stim

def generate_stimuli(worlds, exp_name):
    # {world:
    #  {cond:
    #   {memory: {}, bg_cond:
    #    {baseimg0, baseimg1, recording0, recording1}}}}
    stimuli = {}
    for w in worlds:
        wname = os.path.basename(w)[:-5]

        stimuli[wname] = {}

        stim_objs = target_objects[wname]
        with open(w) as f:
            jdict = json.load(f)

        world = pgw.loadFromDict(jdict["world"])
        background_objs = assign_background_foreground(world.objects)

        outdir = f"../experiments/{exp_name}/assets/targets/{wname}"
        os.system(f"mkdir -p {outdir}")
        for cond, oname in stim_objs.items():

            stimuli[wname][cond] = {}

            for bg_cond in ["foreground", "background"]:
                stim_info = {
                    "worldtype": jdict["worldType"],
                    "background_objs": {k: v for k, v in background_objs.items()},
                    "obj_cond": cond,
                    "bg_cond": bg_cond,
                    "obj_name": oname,
                    "world": wname,
                    "filler": False,
                }
                stim_info["background_objs"][oname] = bg_cond == "background"

                # NOTE: we need to solidify any objects on the way to the target object,
                # so that the ball doesn't take a completely different path
                # we take the easy way out and just solidify the collision early objects
                if cond in ["col_late", "maybecol"]:
                    stim_info["background_objs"][stim_objs["col_early"]] = False

                stim, _ = save_base_stim(world, outdir, stim_info)
                stim_info.update(stim)

                stimuli[wname][cond][bg_cond] = stim_info

            memory_stim = save_memory_stim_overlay(world, wname, stim_info, outdir)
            stimuli[wname][cond]["memory"] = memory_stim
    with open(f"../experiments/{exp_name}/assets/targets.json", "w") as f:
        json.dump(stimuli, f)

def generate_fillers(worlds, exp_name):
    stimuli = {}
    for w in worlds:
        wname = os.path.basename(w)[:-5]
        stimuli[wname] = {}

        with open(w) as f:
            jdict = json.load(f)

        world = pgw.loadFromDict(jdict["world"])
        background_objs = assign_background_foreground(world.objects)

        outdir = f"../experiments/pilot_background/assets/fillers/{wname}"
        os.system(f"mkdir -p {outdir}")

        stim_info = {
            "background_objs": {k: v for k, v in background_objs.items()},
            "world": wname,
            "filler": True,
        }

        stim, _ = save_base_stim(world, outdir, stim_info)
        stim_info.update(stim)

        stimuli[wname] = stim_info

    with open("../experiments/pilot_background/assets/fillers.json", "w") as f:
        json.dump(stimuli, f)

def generate_demo(exp_name):
    outdir = "../experiments/pilot_background/assets/demo/demo1"
    os.system(f"mkdir -p {outdir}")

    with open("plinko/demo/hh_hl_unlink_plinko_0035.json") as f:
        jdict = json.load(f)

    world = pgw.loadFromDict(jdict["world"])
    background_objs = assign_background_foreground(world.objects)
    background_objs["topbump_0"] = True

    stim_info = {
        "background_objs": {k: v for k, v in background_objs.items()},
        "world": "demo",
        "filler": True,
    }

    _ = save_base_stim(world, outdir, stim_info)

    outdir = "../experiments/pilot_background/assets/demo/demo2"
    os.system(f"mkdir -p {outdir}")
    with open("plinko/demo/hh_hl_unlink_plinko_0333.json") as f:
        jdict = json.load(f)

    world = pgw.loadFromDict(jdict["world"])
    background_objs = assign_background_foreground(world.objects)
    background_objs["topbump_1"] = False

    stim_info = {
        "background_objs": {k: v for k, v in background_objs.items()},
        "world": "demo",
        "filler": True,
    }

    _ = save_base_stim(world, outdir, stim_info)

if __name__ == "__main__":
    definites = [
        "/".join(("plinko/candidates/definite", f))
        for f in os.listdir("plinko/candidates/definite")
    ]
    maybes = [
        "/".join(("plinko/candidates/maybe", f))
        for f in os.listdir("plinko/candidates/maybe")
    ]

    worlds = definites + maybes

    reset("pilot_background1")
    # generate_stimuli(["plinko/candidates/definite/lh_hl_unlink_plinko_0036.json"])
    generate_stimuli(worlds, "pilot_background1")

    import random
    fillers = ["/".join(("plinko/fillers", f)) for f in os.listdir("plinko/fillers")]
    fillers = random.sample(fillers, k=16)
    # generate_fillers(fillers)

    # generate_demo("pilot_background1")