import json
from time import sleep
from functools import lru_cache
from concurrent.futures import ProcessPoolExecutor, as_completed
from ast import literal_eval
from collections import Counter

import numpy as np
import pandas as pd
from scipy.optimize import minimize, differential_evolution

import pyGameWorld as pgw
from pyGameWorld.simulate import simulate_noisypaths


def loss(pars, default_sim_noise, predictions, worlds):
    print(pars)
    pars = {
        "noise_position_static": default_sim_noise["noise_position_static"],
        "noise_position_moving": pars[0],
        "noise_collision_direction": pars[1],
        "noise_collision_elasticity": pars[2],
        "noise_gravity": default_sim_noise["noise_gravity"],
    }
    pred = batch_predict(worlds, pars)

    likelihood_predictions = {k: v[0] for k, v in pred.items()}

    model_predictions = pd.DataFrame(likelihood_predictions)
    model_predictions = model_predictions.assign(object = model_predictions.index).reset_index(drop=True)
    model_predictions = pd.melt(model_predictions, id_vars = ["object"], var_name="world", value_name="model_p")

    df = pd.merge(predictions, model_predictions, on=["world", "object"], how="left")
    # breakpoint()
    best_rmse = float("inf")
    best_r = 0
    best_epsilon = 0
    for epsilon in np.linspace(0, 0.25, 6):
        collision_likelihood = df.collision_likelihood / 100
        col = (1 - epsilon) * df.model_p + epsilon * 0.5
        r = col.corr(collision_likelihood)
        rmse = np.sqrt(((col - collision_likelihood) ** 2).mean())

        print("loss: ", rmse)
        if rmse < best_rmse:
            best_rmse = rmse
            best_epsilon = epsilon
            best_r = r

    return best_epsilon, best_rmse, best_r

def endpos_loss(pars, default_sim_noise, predictions, worlds, epsilon_bins=0.1):
    print(pars)
    pars = {
        "noise_position_static": default_sim_noise["noise_position_static"],
        "noise_position_moving": pars[0],
        "noise_collision_direction": pars[1],
        "noise_collision_elasticity": pars[2],
        "noise_gravity": default_sim_noise["noise_gravity"],
    }
    pred = batch_predict(worlds, pars)

    endpos_predictions = {k: v[1] for k, v in pred.items()}
    # segregate [0, 600] into 10 bins
    endpos_predictions_binned = {k: np.histogram(v, bins=np.linspace(0, 600, 11))[0] / len(v) for k, v in endpos_predictions.items()}
    print(list(endpos_predictions_binned.values())[0])
    # endpos_predictions_binned = {k: v / v.sum() for k, v in endpos_predictions_binned.items()}

    # total variation distance
    best_tvd = float("inf")
    best_epsilon = 0
    for epsilon in np.arange(0, 0.51, epsilon_bins):
        tvd = 0
        for world, model_dist in endpos_predictions_binned.items():
            human_dist = predictions[world]
            tvd += 0.5 * np.abs(human_dist - ((1 - epsilon) * model_dist + epsilon / 10)).sum()
        print("epsilon", epsilon, "loss (tvd): ", tvd)
        if tvd < best_tvd:
            best_tvd = tvd
            best_epsilon = epsilon
    return best_epsilon, best_tvd


def batch_predict(worlds, pars):
    out = {}
    for wname, world in worlds.items():
        out[wname] = predict(pgw.loadFromDict(world), **pars)
    # breakpoint()
    return out


def predict(world, **pars):
    paths = simulate_noisypaths(world, stepsize=0.5, N=250, **pars)
    endpos = [p["path"]["FOCUS"][-1][0] for p in paths]
    # breakpoint()
    obj_freq = {}
    for name, obj in world.objects.items():
        if "bump" not in name:
            continue
        obj_freq[name] = 0
        for p in paths:
            for col in p["collisions"]:
                if name in col:
                    obj_freq[name] += 1 / len(paths)
                    break

    for name, val in obj_freq.items():
        obj_freq[name] = np.clip(val, 0.00, 1)

    # breakpoint()
    return obj_freq, endpos


def fit_exp1(method="tvd"):
    data = pd.read_csv("../data/exp_likelihood/collisions.csv")
    data = pd.wide_to_long(data, ["baseImg", "cond", "response", "rt", "time_elapsed", "world"], i="pid", j="trial").reset_index()
    data = data.assign(root = data.baseImg.str.extract("(.*base)"), collision_likelihood = data.response)
    @lru_cache
    def lookup_object(root):
        with open(f"../experiments/assets/exp1/{root[7:]}blue.json") as f:
            j = json.load(f)
            return j["object"]

    data["object"] = data.root.apply(lookup_object)
    data = data.groupby(["world", "object"]).agg({"collision_likelihood": "mean"}).reset_index()

    worlds = {w: json.load(open(f"../experiments/assets/exp1/targets/{w}/{w}.json"))["world"] for w in data.world.unique()}
    with open("../stimuli/default_sim_noise.json") as f:
        default_sim_noise = json.load(f)


    predictions = pd.read_csv("../data/exp1/predictions.csv")
    predictions = pd.wide_to_long(predictions, ["clickPositions", "clickTimes", "filler", "img", "totalTime", "true_x", "world", "catch"], i="pid", j="trial").reset_index()
    predictions = predictions.loc[predictions.filler == "0"]

    human_prediction_dist = {}
    for world in worlds:
        world_preds = predictions.loc[predictions.world == world].clickPositions.apply(lambda x: literal_eval(x)).tolist()
        flat_preds = [item for sublist in world_preds for item in sublist]
        human_prediction_dist[world] = np.histogram(np.array(flat_preds), bins=np.linspace(0, 600, 11))[0] / len(flat_preds)


    grids = [np.linspace(0, 15, 16), np.linspace(0, 0.8, 9), np.linspace(0, 0.8, 9)]
    # grids = [np.linspace(0, 15, 2), np.linspace(0, 1, 1), np.linspace(0, 1, 1)]
    pars = np.array(np.meshgrid(*grids)).T.reshape(-1, 3)
    out = []
    with ProcessPoolExecutor() as executor:
        if method == "correlation":
            futures = [executor.submit(loss, pars[i].ravel(), default_sim_noise, data, worlds) for i in range(len(pars))]
        elif method == "tvd":
            futures = [executor.submit(endpos_loss, pars[i].ravel(), default_sim_noise, human_prediction_dist, worlds) for i in range(len(pars))]
        else:
            raise ValueError("method must be 'correlation' or 'tvd'")

        for i, future in enumerate(as_completed(futures)):
            print(f"{i+1} / {len(pars)}")
            out.append((*(pars[i].ravel().tolist()), *future.result()))

    if method == "correlation":
        out = pd.DataFrame(out, columns=["noise_position_moving", "noise_collision_direction", "noise_collision_elasticity", "epsilon", "r", "rmse"])
        out.to_csv("./output/exp1/noisysim_pars_search.csv", index=False)
    else:
        out = pd.DataFrame(out, columns=["noise_position_moving", "noise_collision_direction", "noise_collision_elasticity", "epsilon", "tvd"])
        out.to_csv("./output/exp1/noisysim_pars_search_eps_tvd.csv", index=False)
    return out

def endpos_loss_vgc(pars, default_sim_noise, predictions, worlds, epsilon_bins=0.1):
    print(pars)
    pars = {
        "noise_position_static": default_sim_noise["noise_position_static"],
        "noise_position_moving": pars[0],
        "noise_collision_direction": pars[1],
        "noise_collision_elasticity": pars[2],
        "noise_gravity": default_sim_noise["noise_gravity"],
    }
    pred = batch_predict_vgc(worlds, pars)

    print(list(pred.values())[0])

    # total variation distance
    best_tvd = float("inf")
    for epsilon in np.arange(0, 0.5, epsilon_bins):
        tvd = 0
        for world, model_dist in pred.items():
            human_dist = predictions[world]
            tvd += 0.5 * np.abs(human_dist - ((1 - epsilon) * model_dist + epsilon / 5)).sum()
        print("loss (tvd): ", tvd)
        if tvd < best_tvd:
            best_tvd = tvd
    return best_tvd


def batch_predict_vgc(worlds, pars):
    out = {}
    for wname, world in worlds.items():
        out[wname] = predict_vgc(pgw.loadFromDict(world), **pars)
    # breakpoint()
    return out


def predict_vgc(world, **pars):
    paths = simulate_noisypaths(world, stepsize=0.5, N=250, **pars)
    goal_dist = Counter([path["goal"] for path in paths])

    return np.array([goal_dist.get(f"goal_{i}", 0) for i in range(5)]) / len(paths)

def fit_exp_vgc():
    data = pd.read_csv("../data/exp_vgc/predictions.csv")
    data = data.loc[~data.filler]


    worlds = {w: json.load(open(f"../experiments/assets/exp_vgc/targets/{w}/world.json"))["world"] for w in data.world.unique()}
    with open("../stimuli/default_sim_noise.json") as f:
        default_sim_noise = json.load(f)

    human_prediction_dist = {}
    for world in worlds:
        tmp = data.loc[data.world == world].response.value_counts(normalize=True).to_dict()
        human_prediction_dist[world] = np.array([tmp.get(i, 0) for i in range(5)])


    # breakpoint()
    grids = [np.linspace(0, 15, 16), np.linspace(0, 0.8, 9), np.linspace(0, 0.8, 9)]
    # grids = [np.linspace(0, 15, 2), np.linspace(0, 1, 1), np.linspace(0, 1, 1)]
    pars = np.array(np.meshgrid(*grids)).T.reshape(-1, 3)
    out = []
    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(endpos_loss_vgc, pars[i].ravel(), default_sim_noise, human_prediction_dist, worlds) for i in range(len(pars))]
        for i, future in enumerate(as_completed(futures)):
            print(f"{i+1} / {len(pars)}")
            out.append((*(pars[i].ravel().tolist()), future.result()))

    out = pd.DataFrame(out, columns=["noise_position_moving", "noise_collision_direction", "noise_collision_elasticity", "tvd"])
    out.to_csv("./noisysim_pars_search_vgc_eps_tvd.csv", index=False)
    return out


if __name__ == "__main__":
    # fit_exp_vgc()
    out = fit_exp1(method="correlation")