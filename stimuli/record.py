import os
import json
import glob

import numpy as np
import pygame as pg

import pyGameWorld as pgw
import pyGameWorld.viewer as viewer

def dump_screen(jdict, **kw):
    if kw.get("paths", False):
        idxes = kw.pop("paths")
        paths = [p['path'] for i, p in enumerate(jdict['outcome']['noisePaths']) if i in idxes]
    else:
        paths = []
    world = pgw.loadFromDict(jdict['world'])
    pg.init()
    scr = pg.display.set_mode(jdict['world']['dims'],
                              flags=pg.HIDDEN)
    scr.fill((255, 255, 255, 255))
    scr.blit(viewer.drawPaths(world, paths, **kw), [0, 0])
    return np.transpose(np.array(pg.surfarray.pixels3d(scr)), axes=(1, 0, 2))

def save_image(jdict, outfile, **kw):
    world = pgw.loadFromDict(jdict['world'])
    if kw.pop("split", None):
      world = pgw.loadFromDict(jdict["world1"])

    pg.init()
    scr = pg.display.set_mode(jdict['world']['dims'],
                              flags=pg.HIDDEN)
    scr.fill((255, 255, 255, 255))
    scr.blit(viewer.drawWorld(world, **kw), [0, 0])
    pg.image.save(scr, outfile)

def save_image_paths(jdict, outfile):
    paths = [p['path'] for p in jdict['outcome']['noisePaths']]
    world = pgw.loadFromDict(jdict['world'])
    pg.init()
    scr = pg.display.set_mode(jdict['world']['dims'],
                              flags=pg.HIDDEN)
    scr.fill((255, 255, 255, 255))
    scr.blit(viewer.drawPaths(world, paths), [0, 0])
    pg.image.save(scr, outfile)

def save_image_paths_noinit(jdict, outfile):
    paths = [p['path'] for p in jdict['outcome']['noisePaths']]
    world = pgw.loadFromDict(jdict['world'])
    pg.init()
    scr = pg.display.set_mode(jdict['world']['dims'],
                              flags=pg.HIDDEN)
    scr.fill((255, 255, 255, 255))
    scr.blit(viewer.drawPathsNoInit(world, paths), [0, 0])
    pg.image.save(scr, outfile)

def save_image_displaypath(jdict, outfile):
    world = pgw.loadFromDict(jdict['world'])
    pg.init()
    scr = pg.display.set_mode(jdict['world']['dims'],
                              flags=pg.HIDDEN)
    scr.fill((255, 255, 255, 255))
    scr.blit(viewer.drawPaths(world, [jdict["displayPath"]]), [0, 0])
    pg.image.save(scr, outfile)

def dump(save_fn, basedir, outdir):
    sim_files = [f for f in os.listdir(basedir) if os.path.isfile("/".join((basedir, f))) and "json" in f]
    for fname in sim_files:
        with open("/".join((basedir, fname)), 'r') as f:
            jdict = json.load(f)
            print("=" * 50)
            print("viewing ", fname)
            outfile = "/".join((outdir, fname.split(".")[0] + ".jpg"))
            save_fn(jdict, outfile)

def record(jdict, outdir, outfile="recording.mp4", **kw):
    hz = int(1./ jdict['displayCfg']['displayStepSize'])
    os.system(f"mkdir -p {outdir}/tmp")
    def step(jdict, screen, split=False, **kw):
        if split:
            world = pgw.loadFromDict(jdict["world1"])
            path = jdict["displayPath1"]
        else:
            world = pgw.loadFromDict(jdict["world"])
            path = jdict["displayPath"]

        yield viewer.drawWorld(world, **kw)
        clk = pg.time.Clock()

        count = 0
        for _ in range(30):
            pg.image.save(screen, f"{outdir}/tmp/{count}.jpg")
            count += 1

        i = 0
        while not viewer.pathDone(world, path, i):
            w = viewer.pathStep(world, path, i, clk, hz, **kw)
            pg.image.save(screen, f"{outdir}/tmp/{count + i}.jpg")
            i += 1
            yield w

    for _ in viewer.view(jdict, step, **kw):
      pass
    os.system(f"ffmpeg -y -framerate {hz} -i {outdir}/tmp/%d.jpg {outdir}/{outfile}")
    os.system(f"rm -rf {outdir}/tmp")

# utilities to batch generate videos for fillers and targets
def generate_filler_vids():
  fillers = glob.glob("../experiments/assets/fillers/*.json")
  for f in fillers:
    filler_vid(f)

def filler_vid(fname):
  with open(fname) as f:
    jdict = json.load(f)

  outdir = os.path.dirname(fname)
  world = fname.split("/")[-1].split(".")[0]
  print(outdir)
  print(world)
  record(jdict, outdir, outfile=world + ".mp4")

def generate_target_vids():
  path = "../experiments/assets/targets"
  worlds = [path + "/" + o for o in os.listdir(path)]
  for w in worlds:
    target_vid(w)

def target_vid(dir):
  world = dir.split("/")[-1]

  with open("/".join((dir, world + ".json")) )as f:
    jdict = json.load(f)

  print(dir)
  record(jdict, dir)

if __name__ == "__main__":
  pass
    # plinko/fillers/hh_hl_unlink_plinko_0163.json
    # with open(sys.argv[1]) as f:
    #     jdict = json.load(f)
    # record(jdict, "../experiments/assets", "out.mp4")
