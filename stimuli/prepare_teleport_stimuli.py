import json
import os

import matplotlib.pyplot as plt
import numpy as np
import pygame as pg
import pygame.constants
from pygame import Color

import pyGameWorld as pgw
from create_plinko import PlinkoCreator, PlinkoTeleportCreator
from pyGameWorld.helpers import centroidForPoly
from pyGameWorld.transforms import Transform
from pyGameWorld import viewer
from record import dump_screen, save_image, record
# from view_stimuli import simulate

with open("default_sim_noise.json", "r") as f:
    defaultSimNoise = json.load(f)


def workshop(jdict, file, outdir="plinko/bouncer_candidates/"):
    from copy import deepcopy

    jdict_old = deepcopy(jdict)

    def draw(jdict, screen):
        world = pgw.loadFromDict(jdict["world"])
        paths = [p["path"] for p in jdict["outcome"]["noisePaths"]]
        s = viewer.drawPaths(world, paths)

        paths = [p["path"] for p in jdict["outcome"]["noisePaths1"]]
        s = viewer.drawPaths(
            pgw.loadFromDict(jdict["world1"]),
            paths,
            sc=s,
            path_color=(0, 0, 255),
        )
        return s

    def translate(jdict, pos, object):
        center = centroidForPoly(object.vertices)
        print("center", center)
        diff = (pos[0] - center[0], pos[1] - center[1])

        for i, v in enumerate(object.vertices):
            jdict["world"]["objects"][object.name]["vertices"][i][0] += diff[0]
            jdict["world"]["objects"][object.name]["vertices"][i][1] += diff[1]

            jdict["world1"]["objects"][object.name]["vertices"][i][0] += diff[0]
            jdict["world1"]["objects"][object.name]["vertices"][i][1] += diff[1]

        return jdict

    def translate_teleporter(jdict, pos, object):
        center = centroidForPoly(object.vertices)
        print("center", center)
        diff = (pos[0] - center[0], pos[1] - center[1])

        for i, v in enumerate(object.vertices):
            jdict["world"]["objects"][object.name]["vertices"][i][0] += diff[0]
            jdict["world"]["objects"][object.name]["vertices"][i][1] += diff[1]

            jdict["world1"]["objects"][object.name]["vertices"][i][0] += diff[0]
            jdict["world1"]["objects"][object.name]["vertices"][i][1] += diff[1]

        return jdict

    def delete(jdict, object):
        jdict["world"]["objects"].pop(object.name)
        jdict["world1"]["objects"].pop(object.name)
        return jdict

    def delete_vertex(jdict, pos, object):
        o = jdict["world"]["objects"][object.name]
        i = min(
            ((i, v) for i, v in enumerate(o["vertices"])),
            key=lambda x: (x[1][0] - pos[0]) ** 2 + (x[1][1] - pos[1]) ** 2,
        )[0]
        o["vertices"] = o["vertices"][:i] + o["vertices"][i + 1 :]
        jdict["world1"]["objects"][object.name]["vertices"] = (
            o["vertices"][:i] + o["vertices"][i + 1 :]
        )

        return jdict

    def resimulate(jdict):
        w1 = pgw.loadFromDict(jdict["world"])
        w2 = pgw.loadFromDict(jdict["world1"])

        creator = PlinkoTeleportCreator(None, create=False)
        creator.loadWorld((w1, w2))
        creator.run(noisedict=defaultSimNoise)
        return creator.checkAndReturn(passFailures=True)

    def step(jdict, screen, **kw):
        world = pgw.loadFromDict(jdict["world"])
        s = draw(jdict, screen)
        yield s

        clk = pg.time.Clock()
        running = True

        selected_obj = ""
        while running:
            for e in pg.event.get():
                if e.type == pg.QUIT or (e.type == pg.KEYDOWN and e.key == pg.K_ESCAPE):
                    running = False
                elif e.type == pg.KEYDOWN and e.key == pg.K_a:
                    print("getting object name under cursor")
                    pos = pg.mouse.get_pos()
                    obj = world.getObjectUnderCursor(world._invert(pos))
                    if not obj:
                        continue
                    print(obj.name)
                elif e.type == pg.KEYDOWN and e.key == pg.K_p:
                    print("getting mouse coordinates")
                    pos = pg.mouse.get_pos()
                    pos = world._invert(pos)
                    print(pos)
                elif e.type == pg.KEYDOWN and e.key == pg.K_d:
                    print("deleting object under cursor")
                    pos = pg.mouse.get_pos()
                    obj = world.getObjectUnderCursor(world._invert(pos))
                    if not obj:
                        continue

                    delete(jdict, obj)
                    w1 = pgw.loadFromDict(jdict["world"])
                    w2 = pgw.loadFromDict(jdict["world1"])

                    creator = PlinkoTeleportCreator(None, create=False)
                    creator.loadWorld((w1, w2))
                    creator.run(noisedict=defaultSimNoise)
                    jdict = creator.checkAndReturn(passFailures=True)
                    s = draw(jdict, screen)
                elif e.type == pg.KEYDOWN and e.key == pg.K_s:
                    print("selecting object under cursor")
                    pos = pg.mouse.get_pos()
                    obj = world.getObjectUnderCursor(world._invert(pos))
                    if not obj:
                        selected_obj = ""
                        continue
                    selected_obj = obj.name
                    print("selected", selected_obj)
                elif e.type == pg.KEYDOWN and e.key == pg.K_m:
                    print("moving selected object to cursor")
                    if selected_obj == "":
                        continue

                    pos = pg.mouse.get_pos()
                    pos = world._invert(pos)
                    obj = world.objects[selected_obj]
                    jdict = translate(jdict, pos, obj)
                    selected_obj = ""

                    jdict = resimulate(jdict)

                    s = draw(jdict, screen)

                    world = pgw.loadFromDict(jdict["world"])
                elif e.type == pg.KEYDOWN and e.key == pg.K_x:
                    print("deleting object vertex")
                    if selected_obj == "":
                        continue

                    pos = pg.mouse.get_pos()
                    pos = world._invert(pos)
                    obj = world.objects[selected_obj]
                    jdict = delete_vertex(jdict, pos, obj)
                    selected_obj = ""

                    jdict = resimulate(jdict)
                    s = draw(jdict, screen)

                    world = pgw.loadFromDict(jdict["world"])
                elif e.type == pg.KEYDOWN and e.key == pg.K_o:
                    print("creating new object")

                    pos = world._invert(pg.mouse.get_pos())
                    bump = PlinkoCreator._makeBumper(
                        json.load(open("worldconfigs/plinko_maker.json"))["world_info"],
                        [],
                        None,
                        None,
                        x=pos[0],
                        y=pos[1],
                    )
                    new_obj = {
                        "type": "Poly",
                        "color": [0, 0, 0, 255],
                        "density": 0.0,
                        "friction": 0.5,
                        "elasticity": 0.5,
                        "vertices": bump[0],
                    }
                    i = max(
                        int(name.split("_")[1])
                        for name in jdict["world"]["objects"]
                        if "bump" in name
                    )
                    jdict["world"]["objects"][f"bump_{i+1}"] = new_obj
                    jdict["world1"]["objects"][f"bump_{i+1}"] = new_obj

                    jdict = resimulate(jdict)

                    s = draw(jdict, screen)

                    world = pgw.loadFromDict(jdict["world"])
                elif e.type == pg.KEYDOWN and e.key == pg.K_r:
                    print("resetting back to original")
                    jdict = deepcopy(jdict_old)
                elif e.type == pg.KEYDOWN and e.key == pg.K_j:
                    print("saving")
                    outfile = file.split(".")[0] + "_edited.json"
                    with open(outdir + outfile, "w") as f:
                        json.dump(jdict, f)
            clk.tick(20)
            yield s

    for _ in viewer.view(jdict, step):
        pass


def resimulate(jdict):
    w1 = pgw.loadFromDict(jdict["world"])
    w2 = pgw.loadFromDict(jdict["world1"])

    creator = PlinkoTeleportCreator(None, create=False)
    creator.loadWorld((w1, w2))
    creator.run(noisedict=defaultSimNoise)
    return creator.checkAndReturn(passFailures=True)


def generate_targets(jdicts, names, clear=False):
    if clear:
        os.system("rm -rf ../experiments/assets/exp_teleporter/targets/*")
    for n, j in zip(names, jdicts):
        if "edited" in n:
            n = n.replace("_edited", "")
        root = n.split(".")[0]
        print(root)
        dir = f"../experiments/assets/exp_teleporter/targets/{root}"
        if not os.path.exists(dir):
            os.makedirs(dir)

        for worldtype in ["1", "2"]:
            for color_idx in [0, 1]:
                colors = [(140, 92, 71, 150), (1, 97, 128, 150)]
                outfile = f"{dir}/img{worldtype}_{color_idx+1}.png"
                save_image(
                    j,
                    outfile,
                    obj_colors={
                        "teleport_entry": colors[color_idx],
                        "teleport_exit": colors[1 - color_idx],
                    },
                    split=(worldtype == "2"),
                )
                record(
                    j,
                    dir,
                    f"recording{worldtype}_{color_idx+1}.mp4",
                    obj_colors={
                        "teleport_entry": colors[color_idx],
                        "teleport_exit": colors[1 - color_idx],
                    },
                    split=(worldtype == "2"),
                )

        with open("/".join((dir, root + "_edited.json")), "w") as f:
            json.dump(j, f)


def make_stimuli(jdict, outdir, noisedict):
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

    def step(jdict, screen):
        # for colors in ["1", "2"]:
        #     print("entry is", ["brown", "blue"][int(colors) - 1])
        world = pgw.loadFromDict(jdict["world"])
        #     if colors == "1":  # entry brown, exit blue
        #         obj_colors = {
        #             "teleport_entry": (140, 92, 71, 150),
        #             "teleport_exit": (1, 97, 128, 150),
        #         }
        #     else:  # entry blue, exit brown
        #         obj_colors = {
        #             "teleport_entry": (1, 97, 128, 150),
        #             "teleport_exit": (140, 92, 71, 150),
        #         }

        transforms = {}
        for name, obj in world.objects.items():
            transforms[name] = Transform(world, obj)

        KEY_DICT = {
            pg.K_z: factory(world, transforms, "color", "red"),
            pg.K_b: factory(world, transforms, "color", "blue"),
            # pg.K_x: factory(world, transforms, "perturb_vertex"),
            # pg.K_c: factory(world, transforms, "perturb_vertex_cached"),
            # pg.K_v: factory(world, transforms, "mirror_perturb"),
            pg.K_f: factory(world, transforms, "translate"),
            pg.K_g: factory(world, transforms, "mirror_translate"),
            pg.K_r: factory(world, transforms, "restore"),
        }

        # yield viewer.drawWorld(world, obj_colors=obj_colors)
        yield viewer.drawWorld(world)
        clk = pg.time.Clock()

        # 1 -> ball goes through teleporter
        # 2 -> ball does not go through teleporter, and passes through exit
        # for manipulation in ["base_1", "base_2", "base_nocol"]:
        for manipulation in ["translate_1", "translate_2", "translate_nocol"]:
            # for manipulation in ["base_nocol", "nocol_translate"]:
            # for manipulation in ["nocol_translate"]:
            print(f"currently generating manipulation {manipulation}, press space to go to next,")
            running = True
            while running:
                for e in pg.event.get():
                    if e.type == pygame.constants.QUIT:
                        running = False
                        pg.quit()
                        return
                    elif e.type == pg.KEYDOWN and e.key == pg.K_s:
                        fname = manipulation + "_"
                        pos = pg.mouse.get_pos()
                        obj = world.getObjectUnderCursor(world._invert(pos))
                        if not obj:
                            return

                        print("saving ", fname)
                        transforms[obj.name].save(screen, outdir, fname)
                    elif e.type == pg.KEYDOWN and e.key == pg.K_SPACE:
                        running = False
                    elif e.type == pg.KEYDOWN and e.key == pg.K_BACKSPACE:
                        print("clearing manipulation")
                        print(f"rm {outdir}/{manipulation}*")
                        os.system(f"rm {outdir}/{manipulation}*")
                    elif e.type == pg.KEYDOWN:
                        func = KEY_DICT.get(e.key, None)
                        if not func:
                            continue

                        func()

                        # yield viewer.drawWorld(world, obj_colors=obj_colors)
                        yield viewer.drawWorld(world)
                clk.tick(5.0)

    for _ in viewer.view(jdict, step):
        pass


def create_memory_stim_overlay(world, stim_data, colors=False):
    outlines = not colors

    def annotate(c1, v1, c2, v2, height):
        # texty = 40

        r = np.sqrt((c1[0] - v1[0][0]) ** 2 + (c1[1] - v1[0][1]) ** 2) + 30
        bounds = []
        if c1[0] > c2[0]:  # obj1 right of obj2
            bounds = [np.pi / 6, np.pi / 2]
        else:
            bounds = [np.pi / 2, 5 * np.pi / 6]
        if c1[1] < c2[1]:  # obj1 below obj2
            bounds = [-pt for pt in bounds]

        theta1 = np.random.uniform(*bounds)

        x1 = r * np.cos(theta1)
        y1 = r * np.sin(theta1)
        plt.text(c1[0] + x1, height - (c1[1] + y1), "(A)", fontsize=15, c=(0, 0, 0, 0.5))

        theta2 = theta1 - np.pi

        x2 = r * np.cos(theta2)
        y2 = r * np.sin(theta2)
        # print(c2[0] + x2, c2[1] + y2)
        plt.text(c2[0] + x2, height - (c2[1] + y2), "(B)", fontsize=15, c=(0, 0, 0, 0.5))
        # plt.tight_layout()

    def label_objs(obj1, obj2, height):
        v1 = obj1.vertices
        c1 = centroidForPoly(v1)
        v2 = obj2.vertices
        c2 = centroidForPoly(v2)

        annotate(c1, v1, c2, v2, height)

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
    memory_colors = {}
    for name, _ in world.objects.items():
        if "bump" not in name:
            continue
        if name == stim_data["object"]:
            continue
        memory_colors[name] = (0, 0, 0, 70)

    if outlines:
        memory_colors[stim_data["object"]] = (0, 0, 0, 255)

    for obj1, obj2 in (objects, reversed(objects)):
        if colors:
            obj1.color = (0, 0, 255, 255)
            obj2.color = (255, 0, 0, 255)

        widths = {stim_data["object"]: 5} if outlines else {}

        tdict = tworld.toDict()
        wdict = world.toDict()

        img1 = dump_screen(
            {"world": tdict},
            obj_colors=memory_colors,
            obj_widths=widths,
        )

        # memory_colors[stim_data["obj_name"]] = orig
        img2 = dump_screen(
            {"world": wdict},
            obj_colors=memory_colors,
            obj_widths=widths,
        )

        plt.imshow(img1)
        plt.imshow(img2, alpha=0.5)

        if outlines:
            label_objs(obj1, obj2, img1.shape[0])

        plt.axis("off")
        yield
        plt.clf()


def save_memory_stim_overlay(
    world, wname, outdir, worldtype, colors=False, c1=Color("#A87E57E6"), c2=Color("#5781A8E6")
):
    for probeobj in ["1", "2"]:
        with open(
            f"../experiments/assets/exp_teleporter/targets/{wname}/translate_{probeobj}_.json"
        ) as f:
            transform_dict1 = json.load(f)

        prefix = "color" if colors else "outline"
        for i, _ in enumerate(create_memory_stim_overlay(world, transform_dict1, colors=colors)):
            outfile = f"{prefix}stim_world{worldtype}_probe{probeobj}_1_{i}.png"

            plt.tight_layout()
            plt.savefig(f"{outdir}/{outfile}")

        with open(
            f"../experiments/assets/exp_teleporter/targets/{wname}/translate_{probeobj}_1.json"
        ) as f:
            transform_dict2 = json.load(f)

        for i, _ in enumerate(create_memory_stim_overlay(world, transform_dict2, colors=colors)):
            outfile = f"{prefix}stim_world{worldtype}_probe{probeobj}_2_{i}.png"

            plt.tight_layout()
            plt.savefig(f"{outdir}/{outfile}")


def save_control_stim_overlay(
    world, wname, outdir, worldtype, colors=False, c1=Color("#A87E57E6"), c2=Color("#5781A8E6")
):
    with open(f"../experiments/assets/exp_teleporter/targets/{wname}/translate_nocol_.json") as f:
        transform_dict1 = json.load(f)

    prefix = "color" if colors else "outline"
    for i, _ in enumerate(create_memory_stim_overlay(world, transform_dict1, colors=colors)):
        outfile = f"{prefix}stim_world{worldtype}_probe0_1_{i}.png"

        plt.tight_layout()
        plt.savefig(f"{outdir}/{outfile}")

    with open(f"../experiments/assets/exp_teleporter/targets/{wname}/translate_nocol_1.json") as f:
        transform_dict2 = json.load(f)

    for i, _ in enumerate(create_memory_stim_overlay(world, transform_dict2, colors=colors)):
        outfile = f"{prefix}stim_world{worldtype}_probe0_2_{i}.png"

        plt.tight_layout()
        plt.savefig(f"{outdir}/{outfile}")


def save_norming_stim(world, wname, worldtype):
    for probeobj in ["nocol", "1", "2"]:
        with open(
            f"../experiments/assets/exp_teleporter/targets/{wname}/base_{probeobj}_red.json"
        ) as f:
            tdict = json.load(f)

        memory_colors = {}
        for name, _ in world["objects"].items():
            if "bump" not in name:
                continue
            memory_colors[name] = (0, 0, 0, 70)

        memory_colors[tdict["object"]] = (255, 0, 0, 255)

        img = dump_screen(
            {"world": world},
            obj_colors=memory_colors,
        )
        plt.imshow(img)
        plt.axis("off")

        color_idx = int(worldtype) - 1
        outfile = f"../experiments/assets/exp_teleporter/targets/{wname}/normstim_color{color_idx}_{probeobj}"
        plt.savefig(outfile)
        plt.clf()


def generate_target_json(dir):
    prefix = "outline"

    out = []
    for world in [
        f
        for f in os.listdir(os.path.join(dir, "targets"))
        if "json" not in f and "DS_Store" not in f
    ]:  # don't look at me
        if "edited" in world:
            world = (world[: world.index("_edited")],)
        item = {
            "world": world,
            "filler": False,
            "probe0_count": 0,
            "probe1_count": 0,
            "probe2_count": 0,
        }
        for worldtype in ["1", "2"]:
            # probeobj type - 0 for nocol, 1 teleporter consistent, 2 for noteleport consistent
            x_result = json.load(open(f"{dir}/targets/{world}/{world}_edited.json"))[
                f"displayPath{'' if worldtype == '1' else '1'}"
            ]["FOCUS"][-1][0]
            item["sim_x_result" + worldtype] = x_result
            for color_idx in [0, 1]:
                item[f"img{worldtype}_{color_idx+1}"] = (
                    f"assets/targets/{world}/img{worldtype}_{color_idx+1}.png"
                )
                item[f"recording{worldtype}_{color_idx+1}"] = (
                    f"assets/targets/{world}/recording{worldtype}_{color_idx+1}.mp4"
                )
                for i, probe_obj in enumerate(
                    ["nocol", "teleport_consistent", "noteleport_consistent"]
                ):
                    # stim_idx = color_idx if worldtype == "1" else 1 - color_idx
                    item[f"color{color_idx}_{probe_obj}_shift1_img0"] = (
                        f"assets/targets/{world}/{prefix}stim_world{color_idx+1}_probe{i}_1_0.png"
                    )
                    item[f"color{color_idx}_{probe_obj}_shift1_img1"] = (
                        f"assets/targets/{world}/{prefix}stim_world{color_idx+1}_probe{i}_1_1.png"
                    )
                    item[f"color{color_idx}_{probe_obj}_shift2_img0"] = (
                        f"assets/targets/{world}/{prefix}stim_world{color_idx+1}_probe{i}_2_0.png"
                    )
                    item[f"color{color_idx}_{probe_obj}_shift2_img1"] = (
                        f"assets/targets/{world}/{prefix}stim_world{color_idx+1}_probe{i}_2_1.png"
                    )
        out.append(item)
        # image naming convention: stim_{worldtype}_probe{probeobj}_{stimulinum}_{counterbalance}.png
        # consistent if probeobj == worldtype, inconsistent otherwise
    print(out)
    print(os.path.join(dir, "") + "targets.json", "w")
    with open(os.path.join(dir, "") + "targets.json", "w") as f:
        json.dump(out, f)


def generate_fillers(files, jdicts, dir):
    for j, f in zip(jdicts, files):
        if "edited" in f:
            f = f.replace("_edited", "")

        with open(f"{dir}/{f}", "w") as file:
            json.dump(j, file)

        for worldtype in ["1", "2"]:
            for color_idx in [0, 1]:
                colors = [(140, 92, 71, 150), (1, 97, 128, 150)]  # brown, blue
                outfile = f"{dir}/{f.split('.')[0]}-img{worldtype}_{color_idx+1}.png"
                save_image(
                    j,
                    outfile,
                    obj_colors={
                        "teleport_entry": colors[color_idx],
                        "teleport_exit": colors[1 - color_idx],
                    },
                    split=(worldtype == "2"),
                )
                record(
                    j,
                    dir,
                    f"{f.split('.')[0]}-recording{worldtype}_{color_idx+1}.mp4",
                    obj_colors={
                        "teleport_entry": colors[color_idx],
                        "teleport_exit": colors[1 - color_idx],
                    },
                    split=(worldtype == "2"),
                )


def generate_filler_json(dir):
    out = []
    for world in [f for f in os.listdir(dir + "/fillers") if "json" in f and "demo" not in f]:
        world = world.split(".")[0]
        if "edited" in world:
            wname = world[: world.index("_edited")]
        else:
            wname = world
        item = {
            "world": wname,
            "filler": True,
        }
        for worldtype in ["1", "2"]:
            x_result = json.load(open(f"{dir}/fillers/{world}.json"))[
                f"displayPath{'' if worldtype == '1' else '1'}"
            ]["FOCUS"][-1][0]
            item["sim_x_result" + worldtype] = x_result
            for color_idx in [0, 1]:
                item[f"img{worldtype}_{color_idx+1}"] = (
                    f"assets/fillers/{wname}-img{worldtype}_{color_idx+1}.png"
                )
                item[f"recording{worldtype}_{color_idx+1}"] = (
                    f"assets/fillers/{wname}-recording{worldtype}_{color_idx+1}.mp4"
                )
        out.append(item)
    print(out)
    print(len(out))
    with open(os.path.join(dir, "") + "fillers.json", "w") as f:
        json.dump(out, f)


if __name__ == "__main__":
    dir = "plinko/teleporter_worlds/"
    files = [f for f in os.listdir(dir) if "json" in f and "edited" in f]
    # files = [
    #     "lh_ll_unlink_plinko_0004.json",
    #     "lh_ll_unlink_plinko_0006.json",
    #     "lh_ll_unlink_plinko_0013.json",
    #     "lh_ll_unlink_plinko_0015.json",
    #     "lh_ll_unlink_plinko_0022.json",
    #     "lh_ll_unlink_plinko_0027.json",
    # ]
    # files = ["lh_hl_unlink_plinko_0000_edited.json"]
    jdicts = [json.load(open(os.path.join(dir, f))) for f in files]
    files = [f.replace("_edited", "") for f in files]

    # files = ["plinko/demo_edited.json"]
    # jdicts = [json.load(open(f)) for f in files]

    # for j, file in zip(jdicts, files):
    # print(file)
    # workshop(j, file, outdir=dir)
    # workshop(j, file, outdir="plinko/teleporter_fillers/")

    # generate_targets(jdicts, files)
    # for j, f in zip(jdicts, files):
    #     print("now generating stimuli for: ", f)
    #     outdir = f"../experiments/assets/exp_teleporter/targets/{f.split('.')[0]}"
    #     make_stimuli(j, outdir, defaultSimNoise)

    # files = [f for f in os.listdir("../experiments/assets/exp_teleporter/targets") if not f.startswith(".")]
    # jdicts = [
    #     json.load(open(f"../experiments/assets/exp_teleporter/targets/{f}/{f}_edited.json"))
    #     for f in files
    # ]

    for j, f in zip(jdicts, files):
        print(f)
        for worldtype in ["1", "2"]:
            # save_norming_stim(j["world" if worldtype == "1" else "world1"], f.split(".")[0], worldtype)
            outdir = f"../experiments/assets/exp_teleporter/targets/{f.split('.')[0]}"
            save_control_stim_overlay(
                pgw.loadFromDict(j["world" if worldtype == "1" else "world1"]),
                f.split(".")[0],
                outdir,
                worldtype,
                colors=False,
            )
            save_memory_stim_overlay(
                pgw.loadFromDict(j["world" if worldtype == "1" else "world1"]),
                f.split(".")[0],
                outdir,
                worldtype,
                colors=False,
            )
    generate_target_json("../experiments/assets/exp_teleporter")

    # generate filler stimuli
    # files = [f for f in os.listdir("plinko/teleporter_fillers") if "json" in f and "edited" in f]
    # jdicts = [json.load(open("plinko/teleporter_fillers/" + f)) for f in files]
    # generate_fillers(files, jdicts, dir="../experiments/assets/exp_teleporter/fillers")
    # generate_filler_json("../experiments/assets/exp_teleporter")
    pass  #
