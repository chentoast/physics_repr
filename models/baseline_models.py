# import multiprocessing as mp
import os
import json
# from time import sleep
# from random import random
import itertools as it
from collections import Counter

import pandas as pd
import numpy as np
# import pygame as pg
from scipy.special import softmax

import pyGameWorld as pgw
from pyGameWorld.transforms import Transform
# from pyGameWorld.viewer import drawWorld, drawPaths
import pyGameWorld.simulation_divergences as divergences
from pyGameWorld.simulate import simulate_noisypaths, simulate_noisypaths_parallel

import sys
from pathlib import Path

root = Path(__file__).absolute().parent.parent
sys.path.append(str(root / "stimuli"))
from create_plinko import PlinkoCreator

conds = {
    "maybe": ["col_early_translate", "nocol_translate", "maybecol_translate"],
    "definite": ["col_early_translate", "nocol_translate", "col_late_translate"],
    "all": ["col_early_translate", "nocol_translate", "maybecol_translate", "col_late_translate"]
}

def powerset(iterable):
    return it.chain.from_iterable(it.combinations(iterable, r) for r in range(len(iterable)+1))

def batch_vgc(worlds, noisysim_pars, alpha, n_simulations=100):
    out = []
    for wname, world in worlds.items():
        print(wname)
        construals = vgc(pgw.loadFromDict(world), noisysim_pars=noisysim_pars, n_simulations=n_simulations)
        preds = vgc_object_preds(construals, temperature=float(alpha))
        world_predictions = pd.DataFrame({"object": list(preds.keys()), "vgc": list(preds.values())})
        world_predictions["world"] = wname
        out.append(world_predictions)

    return pd.concat(out)

def vgc(world, noisysim_pars, repr_cost=1.0, n_simulations=100):
    # NOTE: VGC assumes the value function is utility - cost, where cost=#objects
    # for the navigation domain, the utility scale was roughly [-1/1e-5, -20].
    # here, the wasserstein distance is theoretically equal to [0, -600],
    # but in practice the optimal utility ranges from -10 to -20, depending on how many simulations are run.
    # because the utility scales are similar enough, we fix repr_cost=1.0 to avoid introducing
    # a second free parameter.
    width = 1
    reference_paths = simulate_noisypaths(world, 1/60, N=n_simulations, **noisysim_pars)
    reference_endpoints = [path["path"]["FOCUS"][-1][0] / width for path in reference_paths]

    # sometimes the ball clips through the floor. clamp these values
    reference_endpoints = [min(max(0, x), 600/width) for x in reference_endpoints]

    out = []
    objects = [name for name in world.objects if "bump" in name]
    for construal_names in powerset(objects):
        # print(construal_names)
        _world = world.copy()
        for name in objects:
            if name not in construal_names:
                del _world.objects[name]

        construal_paths = simulate_noisypaths(_world, 1/60, N=n_simulations, **noisysim_pars)
        construal_endpoints = [path["path"]["FOCUS"][-1][0] / width for path in construal_paths]
        construal_endpoints = [min(max(0, x), 600/width) for x in construal_endpoints]

        utility = -divergences.mae(reference_endpoints, construal_endpoints)
        score = utility - repr_cost * len(construal_names)
        out.append({"construal": construal_names, "score": score, "utility": utility})

    return out

def vgc_mse(world, noisysim_pars, true_endpoint, repr_cost=1.0, n_simulations=100):
    out = []
    objects = [name for name in world.objects if "bump" in name]
    for construal_names in powerset(objects):
        _world = world.copy()
        for name in objects:
            if name not in construal_names:
                del _world.objects[name]

        construal_paths = simulate_noisypaths(_world, 1/60, N=n_simulations, **noisysim_pars)
        construal_endpoints = [path["path"]["FOCUS"][-1][0] for path in construal_paths]
        construal_endpoints = [min(max(0, x), 600) for x in construal_endpoints]

        utility = -np.sqrt(((true_endpoint - np.array(construal_endpoints)) ** 2).mean())
        score = utility - repr_cost * len(construal_names)
        out.append({"construal": construal_names, "score": score, "utility": utility})

    return out

def vgc_discrete(world, noisysim_pars, utility_scaling=1.0, repr_cost=1.0, n_simulations=100):
    print("starting")
    np.random.seed(None)
    # for worlds with discrete outcomes
    reference_paths = simulate_noisypaths(world, 1/60, N=n_simulations, **noisysim_pars)
    reference_goal_counts = Counter([path["goal"] for path in reference_paths if path["goal"] != "NONE"])
    reference_goal_counts = {k: v / sum(reference_goal_counts.values()) for k, v in reference_goal_counts.items()}
    print(reference_goal_counts)

    out = []
    objects = [name for name in world.objects if "bump" in name]
    for construal_names in powerset(objects):
        _world = world.copy()
        for name in objects:
            if name not in construal_names:
                del _world.objects[name]

        construal_paths = simulate_noisypaths(_world, 1/60, N=n_simulations, **noisysim_pars)
        # construal_endpoints = [path["path"]["FOCUS"][-1][0] / width for path in construal_paths]
        construal_goal_counts = Counter([path["goal"] for path in construal_paths if path["goal"] != "NONE"])
        construal_goal_counts = {k: v / sum(construal_goal_counts.values()) for k, v in construal_goal_counts.items()}

        # we use total variation instead of 1-Wasserstein because TV works on non-metric spaces, thus is a better fit for discrete outcomes
        utility = -sum(
            abs(reference_goal_counts.get(k, 0) - construal_goal_counts.get(k, 0)) / 2 for k in reference_goal_counts
        ) / utility_scaling
        score = utility - repr_cost * len(construal_names)
        out.append({"construal": construal_names, "score": score, "utility": utility})

    return out

def vgc_discrete1(world, ground_truth, noisysim_pars, repr_cost=1.0, n_simulations=100):
    # for worlds with discrete outcomes
    print(ground_truth)

    out = []
    objects = [name for name in world.objects if "bump" in name]
    for construal_names in powerset(objects):
        _world = world.copy()
        for name in objects:
            if name not in construal_names:
                del _world.objects[name]

        construal_paths = simulate_noisypaths(_world, 1/60, N=n_simulations, **noisysim_pars)
        # construal_endpoints = [path["path"]["FOCUS"][-1][0] / width for path in construal_paths]
        construal_goal_counts = Counter([path["goal"] for path in construal_paths])
        construal_goal_counts = {k: v / len(construal_paths) for k, v in construal_goal_counts.items()}

        # we use total variation instead of 1-Wasserstein because TV works on non-metric spaces, thus is a better fit for discrete outcomes
        utility = -sum(
            abs(ground_truth.get(k, 0) - construal_goal_counts.get(k, 0)) / 2 for k in ground_truth
        )
        score = utility - repr_cost * len(construal_names)
        out.append({"construal": construal_names, "score": score, "utility": utility})

    return out


def vgc_object_preds(construals, temperature=1.0):
    scores = np.array([construal["score"] for construal in construals])
    probs = softmax(scores / temperature)

    out = {}
    for prob, data in zip(probs, construals):
        for name in data["construal"]:
            if name not in out:
                out[name] = 0

            out[name] += prob


    return out


def validate_all():
    properties = ["shiftx", "shifty"]
    out = dict(zip(conds["all"], [{k: [] for k in properties} for _ in conds["all"]]))
    for dir in os.listdir("transformed_stimuli"):
        tmp = validate_dir("transformed_stimuli/" + dir, properties)
        # breakpoint()
        for cond, properties in out.items():
            for prop, val in properties.items():
                p = tmp.get(cond, {}).get(prop, None)
                if p:
                    val.extend(p)

    return out


def validate_dir(dir, properties):
    out = {}
    for file in os.listdir(dir):
        if not file.endswith("json"):
            continue

        print(file)
        try:
            cond = next(s for s in conds["all"] if s in file)
        except StopIteration:
            continue

        with open(dir + "/" + file) as f:
            stats = json.load(f)

        cond_dict = out.setdefault(cond, {})

        for p in properties:
            cond_dict.setdefault(p, []).append(stats["transform_data"][p])

    return out

def apply_transform(world, transformdict):
    world = world.copy()
    obj = transformdict["object"]

    transform = Transform(world, world.objects[obj])
    transform.translate(transform_data=transformdict)
    # transform.color("blue")
    return world


def resimulate(transformed_world):
    # out = PlinkoCreator(config_file=None, world=transformed_world)
    out = PlinkoCreator(config_file=None, create=False)
    out.loadWorld(transformed_world)
    out.run(
        npaths=100,
        noisedict={
            "noise_collision_direction": 0.6,
            "noise_collision_elasticity": 0.6,
            "noise_gravity": 0.2,
        },
    )

    return out

def counterfactual_delete(worlds, noisysim_pars):
    ret = {}

    for wname, w in worlds.items():
        ret[wname] = {}
        original = w.copy()
        ret[wname]["original"] = simulate_noisypaths(original, 1/60, N=250, **noisysim_pars)

        objects = [name for name in w.objects if "bump" in name]
        for n in objects:
            print(wname, n)

            tworld = w.copy()
            del tworld.objects[n]
            ret[wname][n] = simulate_noisypaths(tworld, 1/60, N=250, **noisysim_pars)

    return ret


def counterfactual_translate(worlds, noisysim_pars):
    # prefix = "../experiments/exp1/assets/targets/"
    prefix = root / "experiments" / "exp1" / "assets" / "targets"
    ret = {}

    for wname, w in worlds.items():
        ret[wname] = {}
        original = w.copy()
        ret[wname]["original"] = simulate_noisypaths(original, 1/60, N=250, **noisysim_pars)

        manipulations = [f"{cond}blue.json" for cond in conds["all"]]
        manipulations.extend([f"{cond}1blue.json" for cond in conds["all"]])

        for m in manipulations:
            if m not in os.listdir(f"{str(prefix)}/{wname}"):
                continue

            print(wname, m)

            with open(f"{str(prefix)}/{wname}/{m}") as f:
                transform_dict = json.load(f)

            tworld = apply_transform(w.copy(), transform_dict)
            ret[wname][transform_dict["object"] + ("#1" if "1" in m else "")] = simulate_noisypaths(tworld, 1/60, N=250, **noisysim_pars)

    return ret


def across_sim_variability(jdict, divergence, n_runs=10):
    sims = simulate_noisypaths(
        pgw.loadFromDict(jdict["world"]),
        stepsize=0.02,
        N=500,
        noise_collision_direction=0.25,
        noise_collision_elasticity=0.25,
        noise_gravity=0.1,
    )
    out = []
    for _ in range(n_runs):
        new_world = pgw.loadFromDict(jdict["world"])
        new_sims = simulate_noisypaths(
            new_world,
            stepsize=0.02,
            N=len(sims),
            noise_collision_direction=0.25,
            noise_collision_elasticity=0.25,
            noise_gravity=0.0,
        )

        endpos = np.array([p["path"]["FOCUS"][-1][0] for p in sims])
        endpos_new = np.array([p["path"]["FOCUS"][-1][0] for p in new_sims])

        out.append(divergence(endpos, endpos_new))
    return out


def batch_results(results, divergence):
    out = {"value": [], "obj_name": [], "world": []}
    for world, _data in results.items():
        original_paths = _data["original"]
        for obj_name, counterfactual_paths in _data.items():
            if obj_name == "original":
                continue
            endpos = np.array(
                [p["path"]["FOCUS"][-1][0] for p in original_paths]
            )
            endpos_modified = np.array(
                [p["path"]["FOCUS"][-1][0] for p in counterfactual_paths]
            )

            value = divergence(endpos, endpos_modified)
            out["value"].append(value)
            out["obj_name"].append(obj_name)
            out["world"].append(world)
    return out

if __name__ == "__main__":
    pass
    # with open(
    #     "transformed_stimuli/lh_hl_unlink_plinko_0036/lh_hl_unlink_plinko_0036.json"
    # ) as f:
    #     jdict = json.load(f)

    # with open(
    #     "transformed_stimuli_del/lh_hl_unlink_plinko_0036/col_late_translate1blue.json"
    # ) as f:
    #     jdict_modified = json.load(f)
    # out = batch_resimulate(transformtype="translate")
    # batch_resimulate("counterfactual_stim_del")

    # batch_results(view_modified_paths)
    # out = batch_results(make_aggregator(divergences.mae), "transformed_stimuli_small")

    # out = validate_all()
    # norms_by_cond = dict(zip(conds, [[] for _ in conds]))
    # for cond, val in norms_by_cond.items():
    #     for x, y in zip(out[cond]["shiftx"], out[cond]["shifty"]):
    #         val.append(np.sqrt(x**2 + y**2))
    # norms_by_cond = {k: np.array(v) for k, v in norms_by_cond.items()}
    # for k, v in norms_by_cond.items():
    #     print(k)
    #     print(v.mean())
    #     print(np.median(v))
