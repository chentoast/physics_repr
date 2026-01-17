import argparse
import json
import os
import re

import pygame as pg
import pygame.constants

import pyGameWorld as pgw
from pyGameWorld.transforms import Transform
from pyGameWorld import viewer

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
    # automating this part would probably best the best.
    # but due to randomness we typically need multiple runs
    # to make stimuli that look good, so we keep the manual
    # nature of this for now.
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
        pg.image.save(screen, "/".join((outdir, "img.jpg")))
        clk = pg.time.Clock()
        # cycle through manipulations, and manually generate stimuli for each one
        for manipulation in manipulations:
            KEY_DICT[pg.K_s] = factory(
                world,
                transforms,
                "save",
                screen,
                outdir,
                manipulation,
                jdict["displayCfg"]["displayStepSize"],
                noisedict,
            )
            KEY_DICT[pg.K_DELETE] = lambda: os.system(f"rm {outdir}/{manipulation}*")

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    args = parser.parse_args()

    with open(args.file) as f:
        jdict = json.load(f)

    rootdir = os.path.dirname(args.file)
    manipulations = [
        "col_early_base",
        "col_early_translate",
        "nocol_base",
        "nocol_translate",
    ]
    if jdict["worldType"] == "maybe":
        manipulations.extend(["maybecol_base", "maybecol_translate"])
    elif jdict["worldType"] == "definite":
        manipulations.extend(["col_late_base", "col_late_translate"])
    # manipulations = [
    #     "col_early_base",
    #     "col_early_rel",
    #     "col_early_irrel",
    #     "nocol_base",
    #     "nocol_irrel",
    # ]
    # if jdict["worldType"] == "maybe":
    #     manipulations.extend(["maybecol_base", "maybecol_rel", "maybecol_irrel"])
    # elif jdict["worldType"] == "definite":
    #     manipulations.extend(["col_late_base", "col_late_rel", "col_late_irrel"])

    interact(jdict, rootdir, manipulations, defaultSimNoise)
