import argparse
import json
import os
from collections import Counter

import pygame as pg
from pygame.constants import QUIT

import pyGameWorld as pgw
import pyGameWorld.viewer as viewer
from create_plinko import PlinkoCreator
from pyGameWorld.helpers import centroidForPoly


with open("default_sim_noise.json", "r") as dsnfl:
    defaultSimNoise = json.load(dsnfl)

noisysim_pars = defaultSimNoise
noisysim_pars = {
    "noise_position_static": 0.0,
    "noise_position_moving": 5.0,
    "noise_collision_direction": 0.8,
    "noise_collision_elasticity": 0.6,
    "noise_gravity": 0.0,
}

def workshop(jdict, file, outdir, extension="_edited"):
    print(extension)
    from copy import deepcopy

    jdict_old = deepcopy(jdict)

    def draw(jdict, screen):
        world = pgw.loadFromDict(jdict["world"])
        paths = [p["path"] for p in jdict["outcome"]["noisePaths"]]
        s = viewer.drawPaths(world, paths)

        return s

    def translate(jdict, pos, object):
        center = centroidForPoly(object.vertices)
        print("center", center)
        diff = (pos[0] - center[0], pos[1] - center[1])

        for i, v in enumerate(object.vertices):
            jdict["world"]["objects"][object.name]["vertices"][i][0] += diff[0]
            jdict["world"]["objects"][object.name]["vertices"][i][1] += diff[1]

        return jdict

    def delete(jdict, object):
        jdict["world"]["objects"].pop(object.name)
        return jdict

    def delete_vertex(jdict, pos, object):
        o = jdict["world"]["objects"][object.name]
        i = min(
            ((i, v) for i, v in enumerate(o["vertices"])),
            key=lambda x: (x[1][0] - pos[0]) ** 2 + (x[1][1] - pos[1]) ** 2,
        )[0]
        o["vertices"] = o["vertices"][:i] + o["vertices"][i + 1 :]
        jdict["world"]["objects"][object.name]["vertices"] = (
            o["vertices"][:i] + o["vertices"][i + 1 :]
        )

        return jdict

    def resimulate(jdict):
        w1 = pgw.loadFromDict(jdict["world"])

        creator = PlinkoCreator(None, create=False)
        creator.loadWorld(w1)
        creator.run(noisedict=noisysim_pars, npaths=100)
        out = creator.checkAndReturn(passFailures=True)
        cnt = Counter([p["goal"] for p in out["outcome"]["noisePaths"] if p["goal"] != "NONE"])
        print({k: v / sum(cnt.values()) for k, v in cnt.items()})
        return out

    def step(jdict, screen, **kw):
        nonlocal jdict_old
        world = pgw.loadFromDict(jdict["world"])
        s = draw(jdict, screen)
        yield s

        clk = pg.time.Clock()
        running = True

        selected_obj = ""
        selected_vertex = None
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
                    jdict = resimulate(jdict)
                    s = draw(jdict, screen)
                elif e.type == pg.KEYDOWN and e.key == pg.K_c:
                    print("selecting vertex of seelected object")
                    if selected_obj == "":
                        continue

                    pos = world._invert(pg.mouse.get_pos())
                    vertices = world.objects[selected_obj].vertices
                    i = min(
                        ((i, v) for i, v in enumerate(vertices)),
                        key=lambda x: (x[1][0] - pos[0]) ** 2 + (x[1][1] - pos[1]) ** 2,
                    )[0]
                    print("selected vertex at", vertices[i])
                    selected_vertex = i
                elif e.type == pg.KEYDOWN and e.key == pg.K_x:
                    print("deleting selected object vertex")
                    if selected_obj == "" or selected_vertex is None:
                        continue
                    jdict["world"]["objects"][selected_obj]["vertices"] = (
                        jdict["world"]["objects"][selected_obj]["vertices"][
                            : selected_vertex
                        ]
                        + jdict["world"]["objects"][selected_obj]["vertices"][
                            selected_vertex + 1 :
                        ]
                    )
                    jdict = resimulate(jdict)
                    s = draw(jdict, screen)
                    world = pgw.loadFromDict(jdict["world"])
                    # selected_vertex = None
                    # selected_obj = ""
                elif e.type == pg.KEYDOWN and e.key == pg.K_v:
                    print("moving selected vertex to cursor")
                    if selected_obj == "" or selected_vertex is None:
                        continue
                    pos = world._invert(pg.mouse.get_pos())
                    jdict["world"]["objects"][selected_obj]["vertices"][
                        selected_vertex
                    ] = pos
                    jdict = resimulate(jdict)
                    s = draw(jdict, screen)

                    world = pgw.loadFromDict(jdict["world"])
                    # selected_vertex = None
                    # selected_obj = ""
                elif e.type == pg.KEYDOWN and e.key == pg.K_s:
                    print("selecting object under cursor")
                    pos = pg.mouse.get_pos()
                    obj = world.getObjectUnderCursor(world._invert(pos))
                    if not obj:
                        selected_obj = ""
                        continue
                    selected_obj = obj.name
                    print("selected", selected_obj)
                elif e.type == pg.KEYDOWN and e.key == pg.K_b:
                    print("moving FOCUS position")
                    pos = world._invert(pg.mouse.get_pos())

                    jdict["world"]["objects"]["FOCUS"]["position"][0] = pos[0]
                    jdict = resimulate(jdict)
                    s = draw(jdict, screen)
                    world = pgw.loadFromDict(jdict["world"])

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
                    # selected_obj = ""

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

                    jdict = resimulate(jdict)

                    s = draw(jdict, screen)

                    world = pgw.loadFromDict(jdict["world"])
                elif e.type == pg.KEYDOWN and e.key == pg.K_r:
                    print("resetting back to original")
                    jdict = deepcopy(jdict_old)

                    s = draw(jdict, screen)
                    world = pgw.loadFromDict(jdict["world"])
                elif e.type == pg.KEYDOWN and e.key == pg.K_j:
                    outfile = file.split(".")[0] + extension + ".json"
                    print("saving to", outfile)
                    with open(outdir + outfile, "w") as f:
                        json.dump(jdict, f)
                    jdict_old = deepcopy(jdict)
            clk.tick(20)
            yield s

    for _ in viewer.view(jdict, step):
        pass


# def workshop(jdict, **kw):
#     def draw(jdict, screen, paths=True, split=False):
#         world = pgw.loadFromDict(jdict["world"])
#         if paths:
#             paths = [p["path"] for p in jdict["outcome"]["noisePaths"]]
#             s = viewer.drawPaths(world, paths)

#             print(split)
#             if split:
#                 paths = [p["path"] for p in jdict["outcome"]["noisePaths1"]]
#                 s = viewer.drawPaths(
#                     pgw.loadFromDict(jdict["world1"]),
#                     paths,
#                     sc=s,
#                     path_color=(0, 0, 255),
#                 )
#         else:
#             s = viewer.drawWorld(world)
#         return s

#     def step(jdict, screen, paths=True, split=False, **kw):
#         world = pgw.loadFromDict(jdict["world"])
#         s = draw(jdict, screen, paths, split)
#         yield s

#         clk = pg.time.Clock()
#         running = True

#         while running:
#             for e in pg.event.get():
#                 if e.type == QUIT:
#                     running = False
#                 elif e.type == pg.KEYDOWN and e.key == pg.K_a:
#                     print("getting object name under cursor")
#                     pos = pg.mouse.get_pos()
#                     obj = world.getObjectUnderCursor(world._invert(pos))
#                     if not obj:
#                         continue
#                     print(obj.name)
#                 elif e.type == pg.KEYDOWN and e.key == pg.K_p:
#                     print("getting mouse coordinates")
#                     pos = pg.mouse.get_pos()
#                     pos = world._invert(pos)
#                     print(pos)
#             clk.tick(20)
#             yield s

#     for _ in viewer.view(jdict, step, **kw):
#         pass


def inspect(jdict, **kw):
    def step(jdict, screen, paths=True, split=False, **kw):
        world = pgw.loadFromDict(jdict["world"])
        if paths:
            paths = [p["path"] for p in jdict["outcome"]["noisePaths"]]
            s = viewer.drawPaths(world, paths)

            print(split)
            if split:
                paths = [p["path"] for p in jdict["outcome"]["noisePaths1"]]
                s = viewer.drawPaths(
                    pgw.loadFromDict(jdict["world1"]),
                    paths,
                    sc=s,
                    path_color=(0, 0, 255),
                )
        else:
            s = viewer.drawWorld(world)

        yield s

        clk = pg.time.Clock()
        running = True
        while running:
            for e in pg.event.get():
                if e.type == QUIT:
                    running = False
                elif e.type == pg.KEYDOWN and e.key == pg.K_a:
                    pos = pg.mouse.get_pos()
                    obj = world.getObjectUnderCursor(world._invert(pos))
                    if not obj:
                        continue
                    print(obj.name)
                elif e.type == pg.KEYDOWN and e.key == pg.K_p:
                    pos = pg.mouse.get_pos()
                    pos = world._invert(pos)
                    print(pos)
                elif e.type == pg.KEYDOWN and e.key == pg.K_s:
                    pg.image.save(screen, "tmp.png")
            clk.tick(20)
            yield s

    for _ in viewer.view(jdict, step, **kw):
        pass


def view(jdict, **kw):
    def step(jdict, screen):
        world = pgw.loadFromDict(jdict["world"])

        s = viewer.drawWorld(world)
        yield s

        clk = pg.time.Clock()
        running = True
        while running:
            for e in pg.event.get():
                if e.type == QUIT or (e.type == pg.KEYDOWN and e.key == pg.K_RETURN):
                    running = False
                elif e.type == pg.KEYDOWN and e.key == pg.K_RETURN:
                    running = False
            clk.tick(20)
            yield s
        pg.quit()

    for _ in viewer.view(jdict, step):
        pass


def viewPaths(jdict, **kw):
    def step(jdict, screen, split=False, drawstart=True, drawend=True, **kw):
        world = pgw.loadFromDict(jdict["world"])
        paths = [p["path"] for p in jdict["outcome"]["noisePaths"]]

        s = viewer.drawPaths(world, paths, draw_start=drawstart, draw_end=drawend)
        # s = None

        if split:
            world = pgw.loadFromDict(jdict["world1"])
            paths = [p["path"] for p in jdict["outcome"]["noisePaths1"]]
            s = viewer.drawPaths(
                pgw.loadFromDict(jdict["world1"]),
                paths,
                sc=s,
                path_color=(0, 0, 255),
                draw_start=drawstart,
                draw_end=drawend,
            )
        yield s

        clk = pg.time.Clock()
        running = True
        while running:
            for e in pg.event.get():
                if e.type == QUIT or (e.type == pg.KEYDOWN and e.key == pg.K_RETURN):
                    running = False
                elif e.type == pg.KEYDOWN and e.key == pg.K_RETURN:
                    running = False
            clk.tick(20)
            yield s
        pg.quit()

    for _ in viewer.view(jdict, step, **kw):
        pass


def viewDisplayPath(jdict, **kw):
    def step(jdict, screen, split=False, drawstart=True, drawend=True, **kw):
        world = pgw.loadFromDict(jdict["world"])

        s = viewer.drawPaths(world, [jdict["displayPath"]], draw_end=drawend)

        if split:
            s = viewer.drawPaths(
                pgw.loadFromDict(jdict["world1"]),
                [jdict["displayPath1"]],
                sc=s,
                path_color=(0, 0, 255),
            )
        yield s

        clk = pg.time.Clock()
        running = True
        while running:
            for e in pg.event.get():
                if e.type == QUIT:
                    running = False
                elif e.type == pg.KEYDOWN and e.key == pg.K_RETURN:
                    running = False
                elif e.type == pg.KEYDOWN and e.key == pg.K_s:
                    pg.image.save(screen, "tmp.png")
            clk.tick(20)
            yield s
        pg.quit()

    for _ in viewer.view(jdict, step, **kw):
        pass


def simulate(jdict, flags=0, **kw):
    def step(jdict, screen, split=False, **kw):
        if split:
            world = pgw.loadFromDict(jdict["world1"])
            path = jdict["displayPath1"]
        else:
            world = pgw.loadFromDict(jdict["world"])
            path = jdict["displayPath"]

        hz = int(1.0 / jdict["displayCfg"]["displayStepSize"])

        yield viewer.drawWorld(world)
        clk = pg.time.Clock()

        i = 0
        while not viewer.pathDone(world, path, i):
            yield viewer.pathStep(world, path, i, clk, hz)
            i += 1

    for _ in viewer.view(jdict, step, flags=flags, **kw):
        pass


def simulate_noise(jdict, idx=1, flags=0, **kw):
    def step(jdict, screen):
        world = pgw.loadFromDict(jdict["world"])
        # if idx == -1:
        #     idx = random.randint(0, len(jdict['outcome']['noisePaths']))
        path = jdict["outcome"]["noisePaths"][idx]["path"]
        hz = int(1.0 / jdict["displayCfg"]["displayStepSize"])

        yield viewer.drawWorld(world, **kw)
        clk = pg.time.Clock()

        i = 0
        while not viewer.pathDone(world, path, i):
            yield viewer.pathStep(world, path, i, clk, hz, **kw)
            i += 1

    return viewer.view(jdict, step, flags=flags)


if __name__ == "__main__":
    from ast import literal_eval

    parser = argparse.ArgumentParser()
    parser.add_argument("--dir")
    parser.add_argument("--outdir")
    parser.add_argument("--kwargs")
    parser.add_argument("viewer")
    parser.add_argument("files", nargs=argparse.REMAINDER)

    args = parser.parse_args()
    kw = {}
    if args.kwargs:
        kw = dict(
            (pair.split(":")[0], literal_eval(pair.split(":")[1]))
            for pair in args.kwargs.split(",")
        )

    print(kw)

    func = globals().get(args.viewer, None)
    if not func:
        raise Exception("invalid viewing function")
    if args.files:
        for fname in args.files:
            kw["file"] = fname.split("/")[-1]
            kw["outdir"] = args.outdir
            print(fname)
            with open(fname) as f:
                jdict = json.load(f)
                func(jdict, **kw)
                # view(jdict)
    elif args.dir:
        for fname in os.listdir(args.dir):
            with open(args.dir + fname) as f:
                jdict = json.load(f)
            kw["file"] = fname.split("/")[-1]
            kw["outdir"] = args.outdir
            print(kw["file"])
            func(jdict, **kw)
        # dump(save_image_paths, args.dir, "plinko/images")