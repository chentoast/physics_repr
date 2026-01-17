import argparse
import json
import os
from pathlib import Path

import pygame as pg
import pygame.constants
from copy import deepcopy

import pyGameWorld as pgw
from create_plinko import PlinkoCreator
from pyGameWorld.transforms import Transform
from pyGameWorld import viewer
import record

with open("default_sim_noise.json", "r") as dsnfl:
    defaultSimNoise = json.load(dsnfl)

def factory(world, transforms, fn_name, *a):
    # dispatch to the transform associated with the object under cursor
    def fn():
        pos = pg.mouse.get_pos()
        obj = world.getObjectUnderCursor(world._invert(pos))
        if not obj:
            return

        func = getattr(transforms[obj.name], fn_name, None)
        if not func:
            return
        func(*a)

    return fn


def interact(jdict, outdir, manipulations, noisedict):
    print(outdir)
    # automating this part would probably best the best.
    # but for now, just do it manually
    def step(jdict, screen):
        world = pgw.loadFromDict(jdict["world"])

        transforms = {}
        for name, obj in world.objects.items():
            transforms[name] = Transform(world, obj)

        KEY_DICT = {
            pg.K_z: factory(world, transforms, "color", "red"),
            pg.K_b: factory(world, transforms, "color", "blue"),
            pg.K_x: factory(world, transforms, "perturb_vertex"),
            pg.K_c: factory(world, transforms, "perturb_vertex_cached"),
            pg.K_v: factory(world, transforms, "mirror_perturb"),
            pg.K_f: factory(world, transforms, "translate"),
            pg.K_g: factory(world, transforms, "mirror_translate"),
            pg.K_r: factory(world, transforms, "restore"),
        }

        yield viewer.drawWorld(world)
        clk = pg.time.Clock()
        # cycle through manipulations, and manually generate stimuli for each one
        for manipulation in manipulations:
            KEY_DICT[pg.K_s] = factory(
                world,
                transforms,
                "save",
                screen,
                str(outdir),
                manipulation,
                jdict["displayCfg"]["displayStepSize"],
                noisedict,
            )
            KEY_DICT[pg.K_DELETE] = lambda: os.system(f"rm {outdir / manipulation}*")
            # KEY_DICT[pg.K_DELETE] = lambda: print("deleted")

            print(
                f"currently generating manipulation {manipulation}, press space to go to next,"
            )
            running = True
            while running:
                for e in pg.event.get():
                    if e.type == pygame.constants.QUIT:
                        pg.quit()
                        return
                    elif e.type == pg.KEYDOWN and e.key == pg.K_SPACE:
                        running = False
                    elif e.type == pg.KEYDOWN:
                        func = KEY_DICT.get(e.key, None)
                        if not func:
                            continue

                        func()
                        yield viewer.drawWorld(world)
            clk.tick(5.0)

    for _ in viewer.view(jdict, step):
        pass

def dump(jdict, name, outdir, extension=""):
    if not os.path.exists(outdir / name):
        os.makedirs(outdir / name)

    # dump the json file to the output directory
    with open(os.path.join(outdir / name, f"world{extension}.json"), "w") as f:
        json.dump(jdict, f, indent=4)

    outfile = outdir / name / f"img{extension}.jpg"
    record.save_image(jdict, outfile)
    record.record(jdict, outdir / name, outfile=f"recording{extension}.mp4")

def counterfactual_delete(jdict):
    def resimulate(jdict):
        w = pgw.loadFromDict(jdict["world"])
        creator = PlinkoCreator(None, create=False)
        creator.loadWorld(w)
        creator.run(noisedict=defaultSimNoise)

        return creator.checkAndReturn(passFailures=True)

    jdict = deepcopy(jdict)
    # generate counterfactuals
    first_collision = next(iter(jdict["outcome"]["noisePaths"][0]["collisions"]))
    obj = first_collision[1]

    del jdict["world"]["objects"][obj]
    return resimulate(jdict)


def make_json(outdir, exclude, filler, memory_stimuli=False):
    exclude = [s.replace(".json", "") for s in exclude]
    out = []
    for directory in os.listdir(outdir):
        if not os.path.isdir(outdir / directory):
            continue
        if directory in exclude:
            continue

        target = os.path.join(outdir, directory, "world.json")
        with open(target, "r") as f:
            jdict = json.load(f)

        if filler:
            root = Path("assets") / "fillers" / directory
        else:
            root = Path("assets") / "targets" / directory
        data = {
            "img": (root / "img.jpg").as_posix(),
            "recording": (root / "recording.mp4").as_posix(),
            "world": directory,
            "true_goal": jdict["outcome"]["goalHit"],
            "filler": filler,
            "worldtype": jdict["worldType"]
        }
        # if not filler:
        #     data = {**data,
        #             "img_del": (root / "img_delete.jpg").as_posix(),
        #             "recording_del": (root / "recording_delete.mp4").as_posix(),
        #     }

        if memory_stimuli:
            probes = ["col1"]

            full_path = Path("../experiments/assets/exp_vgc/targets") / directory
            with open(full_path / "col1.json", "r") as f:
                col1 = json.load(f)["object"]

            data = {**data,
                "col1": col1,
                "col1_basered": (root / "base1red.jpg").as_posix(),
                "col1_probered0": (root / "col1red.jpg").as_posix(),
                "col1_probered1": (root / "col11red.jpg").as_posix(),
                "col1_baseblue": (root / "base1blue.jpg").as_posix(),
                "col1_probeblue0": (root / "col1.jpg").as_posix(),
                "col1_probeblue1": (root / "col11.jpg").as_posix(),
            }

            if "col2.json" in os.listdir(full_path):
                probes.append("col2")
                with open(full_path / "col2.json", "r") as f:
                    col2 = json.load(f)["object"]

                data = {**data,
                    "col2": col2,
                    "col2_basered": (root / "base2red.jpg").as_posix(),
                    "col2_probered0": (root / "col2red.jpg").as_posix(),
                    "col2_probered1": (root / "col21red.jpg").as_posix(),
                    "col2_baseblue": (root / "base2blue.jpg").as_posix(),
                    "col2_probeblue0": (root / "col2.jpg").as_posix(),
                    "col2_probeblue1": (root / "col21.jpg").as_posix(),
                }

            data["probes"] = probes
        out.append(data)
    return out

def make_json_exp2(outdir, exclude, filler, memory_stimuli=False):
    exclude = [s.replace(".json", "") for s in exclude]
    out = []
    for directory in os.listdir(outdir):
        if not os.path.isdir(outdir / directory):
            continue
        if directory in exclude:
            continue

        target = os.path.join(outdir, directory, "world.json")
        with open(target, "r") as f:
            jdict = json.load(f)

        if filler:
            root = Path("assets") / "fillers" / directory
        else:
            root = Path("assets") / "targets" / directory
        data = {
            "img": (root / "img.jpg").as_posix(),
            "recording": (root / "recording.mp4").as_posix(),
            "world": directory,
            "true_goal": jdict["outcome"]["goalHit"],
            "filler": filler,
            "worldtype": jdict["worldType"]
        }
        # if not filler:
        #     data = {**data,
        #             "img_del": (root / "img_delete.jpg").as_posix(),
        #             "recording_del": (root / "recording_delete.mp4").as_posix(),
        #     }

        if memory_stimuli:
            probes = ["col1"]

            full_path = Path("../experiments/assets/exp_vgc2/targets") / directory
            with open(full_path / "col1red.json", "r") as f:
                col1 = json.load(f)["object"]

            data = {**data,
                "col1": col1,
                "col1_basered": (root / "base1red.jpg").as_posix(),
                "col1_probered0": (root / "col1red.jpg").as_posix(),
                "col1_probered1": (root / "col11red.jpg").as_posix(),
                "col1_baseblue": (root / "base1blue.jpg").as_posix(),
                "col1_probeblue0": (root / "col1blue.jpg").as_posix(),
                "col1_probeblue1": (root / "col11blue.jpg").as_posix(),
            }

            if "col2.json" in os.listdir(full_path):
                probes.append("col2")
                with open(full_path / "col2red.json", "r") as f:
                    col2 = json.load(f)["object"]

                data = {**data,
                    "col2": col2,
                    "col2_basered": (root / "base2red.jpg").as_posix(),
                    "col2_probered0": (root / "col2red.jpg").as_posix(),
                    "col2_probered1": (root / "col21red.jpg").as_posix(),
                    "col2_baseblue": (root / "base2blue.jpg").as_posix(),
                    "col2_probeblue0": (root / "col2blue.jpg").as_posix(),
                    "col2_probeblue1": (root / "col21blue.jpg").as_posix(),
                }

            data["probes"] = probes
        out.append(data)
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "outdir",
        type=str,
        help="output directory for stimuli",
    )
    parser.add_argument(
        "--indir",
        type=str,
        help="directory containing json files to load",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="json file to load",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        default="",
        help="list of files to exclude",
    )
    args = parser.parse_args()

    exclude = args.exclude.split(",")
    print(exclude)
    outdir = Path(args.outdir)
    if args.indir:
        indir = Path(args.indir)

        files = os.listdir(indir)

        for fi in files:
            if fi in exclude:
                continue
            with open(indir / fi, "r") as jfile:
                jdict = json.load(jfile)

            fi = fi.replace("_edited", "")

            # dump(jdict, fi.split(".")[0], outdir)
            # jdict_del = counterfactual_delete(jdict)
            # dump(jdict_del, fi.split(".")[0], outdir, extension="_delete")
            # interact(jdict, outdir / fi.split(".")[0], ["base1", "base2", "col1", "col2"], defaultSimNoise)
    elif args.file:
        file = Path(args.file)
        with open(file, "r") as f:
            jdict = json.load(f)

        print(file.stem)
        # dump(jdict, file.stem, outdir)

    targets = make_json_exp2(outdir, exclude, False, True)
    with open(outdir / "targets.json", "w") as f:
        json.dump(targets, f, indent=4)

    # fillers = make_json_exp2(outdir, exclude, True)
    # if not outdir.exists():
    #     outdir.mkdir(parents=True)

    # with open(outdir / "fillers.json", "w") as f:
    #     json.dump(fillers, f, indent=4)