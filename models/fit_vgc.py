import os
from functools import lru_cache
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from itertools import product

import pandas as pd
import numpy as np

import baseline_models as baseline
import pyGameWorld as pgw

def cache_construals(n_simulations):
    memory = pd.read_csv("../data/exp1/memory.csv")
    data = pd.wide_to_long(memory, ["rt", "correct", "answer", "cond", "world", "baseImg", "modifiedImg",
                                    "binary_response", "response"],
                                i="pid", j="trial").reset_index()

    data = data.assign(root = data.baseImg.str.extract("(.*base)"),
                    confidence = np.abs(50 - data.response),
                    acc_confidence = data.apply(lambda x: 100 - x.response if (x.answer == 0) else x.response, axis=1))
    data["cond"] = pd.Categorical(data["cond"], categories=["col_early_translate", "col_late_translate", "maybecol_translate", "nocol_translate"], ordered=True)

    @lru_cache
    def lookup_object(root):
        with open(f"../experiments/assets/exp1/{root[7:]}blue.json") as f:
            j = json.load(f)
            return j["object"]

    data["object"] = data.root.apply(lookup_object)
    data = data.groupby(["world", "object"]).agg({"correct": "mean"}).reset_index()
    worlds = {
        w: json.load(open(f"../experiments/assets/exp1/targets/{w}/{w}.json"))["world"]
        for w in data.world.unique()
    }

    noisysim_pars = {
        "noise_position_static": 0.0,

        # "noise_position_moving": 10.0,
        # "noise_position_moving": 5.0,
        # "noise_collision_direction": 0.78,
        # "noise_collision_elasticity": 0.67,
        "noise_position_moving": 5.0,
        "noise_collision_direction": 0.8,
        "noise_collision_elasticity": 0.6,
        "noise_gravity": 0.0,
    }
    for wname, world in worlds.items():
        print(wname)
        construals = baseline.vgc(pgw.loadFromDict(world), noisysim_pars=noisysim_pars, n_simulations=n_simulations)

        with open(f"./output/exp1/cache/{wname}_construals.json", "w") as f:
            json.dump(construals, f)

def cache_construals_vgc(n_simulations):
    data = pd.read_csv("../data/exp_vgc/memory.csv")
    data["correct"] = data.correct_conf.map(lambda x: 1.0 if x > 50 else 0.0)
    data = data.groupby(["world", "object"]).agg({"correct": "mean"}).reset_index()
    worlds = {
        w: json.load(open(f"../experiments/assets/exp_vgc/targets/{w}/world.json"))
        for w in data.world.unique()
    }

    noisysim_pars = {
        "noise_position_static": 0.0,
        "noise_position_moving": 8.00,
        "noise_collision_direction": 0.6,
        "noise_collision_elasticity": 0.0,
        "noise_gravity": 0.0,
    }

    np.random.seed(None)
    for w, world in worlds.items():
        print(w)
        construals = baseline.vgc_discrete(pgw.loadFromDict(world["world"]), noisysim_pars=noisysim_pars, n_simulations=n_simulations)
        with open("./output/exp_vgc/cache/{}_construals.json".format(w), "w") as f:
            json.dump(construals, f, indent=2)

def wrapper(wdict, noisysim_pars, n_simulations):
    construals = baseline.vgc_discrete(pgw.loadFromDict(wdict), noisysim_pars=noisysim_pars, n_simulations=n_simulations)
    return construals

def cache_construals_vgc2(n_simulations):
    worlds = {
        w: json.load(open(f"../experiments/assets/exp_vgc2/targets/{w}/world.json"))
        for w in os.listdir("../experiments/assets/exp_vgc2/targets/") if os.path.isdir(os.path.join("../experiments/assets/exp_vgc2/targets/", w))
    }

    noisysim_pars = {
        "noise_position_static": 0.0,
        "noise_position_moving": 5.0,
        "noise_collision_direction": 0.8,
        "noise_collision_elasticity": 0.6,
        "noise_gravity": 0.0,
    }

    # np.random.seed(None)
    for w, world in worlds.items():
        print(w)
    with ProcessPoolExecutor() as executor:
        futures = {}
        for w, world in worlds.items():
            print(w)
            futures[executor.submit(wrapper, world["world"], noisysim_pars, n_simulations)] = w
        for future in as_completed(futures):
            w = futures[future]
            construals = future.result()
            print(f"Finished {w}")
        # construals = baseline.vgc_discrete(pgw.loadFromDict(world["world"]), noisysim_pars=noisysim_pars, n_simulations=n_simulations)
            with open("./output/exp_vgc2/cache/{}_construals.json".format(w), "w") as f:
                json.dump(construals, f, indent=2)

def predict(alpha, data, worlds, noisysim_pars, use_cached=True):
    # vgc_predictions = baseline.batch_vgc(worlds, noisysim_pars=noisysim_pars, alpha=alpha, n_simulations=250)
    vgc_predictions = []
    for wname, world in worlds.items():
        print(wname)
        if use_cached:
            with open(f"./output/exp1/cache/{wname}_construals.json") as f:
                construals = json.load(f)
        else:
            construals = baseline.vgc(pgw.loadFromDict(world), noisysim_pars=noisysim_pars, n_simulations=250)

        preds = baseline.vgc_object_preds(construals, temperature=float(alpha))
        world_predictions = pd.DataFrame({"object": list(preds.keys()), "vgc": list(preds.values())})
        world_predictions["world"] = wname
        vgc_predictions.append(world_predictions)

    vgc_predictions = pd.concat(vgc_predictions)

    _joint = pd.merge(
        data,
        vgc_predictions,
        on=["world", "object"],
        how="left",
    )
    _joint = _joint.assign(alpha=alpha)
    _joint.to_csv("./output/exp1/vgc_predictions_alpha_{}.csv".format(round(alpha, 2)), index=False)
    return (alpha, np.sqrt(((_joint.correct - (_joint.vgc * 0.667 + 0.333)) ** 2).mean()), _joint.correct.corr(_joint.vgc))

def predict_exp_vgc(alpha, repr_cost, data, worlds, noisysim_pars, use_cached=True):
    np.random.seed(None)
    vgc_predictions = []
    for w, world in worlds.items():
        print(w)
        if use_cached:
            with open(f"./output/exp_vgc/cache/{w}_construals.json") as f:
                construals = json.load(f)
                for c in construals:
                    c["utility"] = c["utility"] / repr_cost
                    c["score"] = c["utility"] - len(c["construal"])
        else:
            construals = baseline.vgc_discrete(pgw.loadFromDict(world["world"]), noisysim_pars=noisysim_pars, n_simulations=250, utility_scaling=repr_cost)
            with open("./output/exp_vgc/cache/{}_construals_alpha_{}_scaling_{}.json".format(w, round(alpha, 2), round(repr_cost, 3)), "w") as f:
                json.dump(construals, f, indent=2)

        preds = baseline.vgc_object_preds(construals, temperature=alpha)
        world_predictions = pd.DataFrame({"object": list(preds.keys()), "vgc": list(preds.values())})
        world_predictions["world"] = w
        vgc_predictions.append(world_predictions)
    vgc_predictions = pd.concat(vgc_predictions, ignore_index=True)
    _joint = pd.merge(
        data,
        vgc_predictions,
        on=["world", "object"],
        how="left",
    )
    _joint.to_csv("./output/exp_vgc/vgc_predictions_alpha_{}_scaling_{}.csv".format(round(alpha, 2), round(repr_cost, 3)), index=False)
    return (alpha, np.sqrt(((_joint.correct - (_joint.vgc * 0.667 + 0.333)) ** 2).mean()), _joint.correct.corr(_joint.vgc))

def fit_exp1():
    memory = pd.read_csv("../data/exp1/memory.csv")
    data = pd.wide_to_long(memory, ["rt", "correct", "answer", "cond", "world", "baseImg", "modifiedImg",
                                    "binary_response", "response"],
                                i="pid", j="trial").reset_index()

    data = data.assign(root = data.baseImg.str.extract("(.*base)"),
                    confidence = np.abs(50 - data.response),
                    acc_confidence = data.apply(lambda x: 100 - x.response if (x.answer == 0) else x.response, axis=1))
    data["cond"] = pd.Categorical(data["cond"], categories=["col_early_translate", "col_late_translate", "maybecol_translate", "nocol_translate"], ordered=True)

    @lru_cache
    def lookup_object(root):
        with open(f"../experiments/assets/exp1/{root[7:]}blue.json") as f:
            j = json.load(f)
            return j["object"]

    data["object"] = data.root.apply(lookup_object)
    data = data.groupby(["world", "object"]).agg({"correct": "mean"}).reset_index()





    worlds = {
        w: json.load(open(f"../experiments/assets/exp1/targets/{w}/{w}.json"))["world"]
        for w in data.world.unique()
    }

    noisysim_pars = {
        "noise_position_static": 0.0,

        # "noise_position_moving": 10.0,
        # "noise_position_moving": 5.0,
        # "noise_collision_direction": 0.78,
        # "noise_collision_elasticity": 0.67,
        "noise_position_moving": 5.0,
        "noise_collision_direction": 0.8,
        "noise_collision_elasticity": 0.6,
        "noise_gravity": 0.0,
    }


    losses = []
    print("==== Starting fitting ====")
    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(predict, alpha, data, worlds, noisysim_pars) for alpha in np.linspace(0.1, 500, 101)]
        for future in futures:
            res = future.result()
            print(f"alpha={res[0]:.2f}, rmse={res[1]:.4f}, r={res[2]:.4f}")
            losses.append(future.result())

    losses = pd.DataFrame(losses, columns=["alpha", "rmse", "r"])
    losses = losses.sort_values("rmse", ascending=True)
    losses.to_csv("./output/exp1/vgc_fitting.csv", index=False)

    best_alpha = float(losses.iloc[0].alpha)
    print("fitting complete, best alpha: {:.2f}".format(best_alpha))

    best_predictions = baseline.batch_vgc(worlds, noisysim_pars=noisysim_pars, alpha=best_alpha)
    best_predictions.to_csv("./output/exp1/best_vgc_predictions.csv", index=False)
    return losses, best_predictions

# def fit_exp_vgc(repr_cost):
#     # theoretically, worst possible utility is -2.0
#     # in plinko,
#     # so, we fix repr_cost = 0.02, so that utility range is [-100.0, 0], just like in exp1
#     data = pd.read_csv("../data/exp_vgc/memory.csv")
#     data["correct"] = data.correct_conf.map(lambda x: 1.0 if x > 50 else 0.0)
#     data = data.groupby(["world", "object"]).agg({"correct": "mean"}).reset_index()
#     worlds = {
#         w: json.load(open(f"../experiments/assets/exp_vgc/targets/{w}/world.json"))
#         for w in data.world.unique()
#     }
#     for wname, w in worlds.items():
#         print(wname)
#         pgw.loadFromDict(w["world"])

#     noisysim_pars = {
#         "noise_position_static": 0.0,
#         "noise_position_moving": 8.00,
#         "noise_collision_direction": 0.6,
#         "noise_collision_elasticity": 0.0,
#         "noise_gravity": 0.0,
#     }

#     losses = []
#     print("==== Starting fitting ====")
#     with ProcessPoolExecutor(max_workers=11) as executor:
#         # futures = [executor.submit(predict_exp_vgc, alpha, repr_cost, data, worlds, noisysim_pars) for (alpha, repr_cost) in product(np.linspace(0.01, 5, 11), np.linspace(0, 1.0, 9))]
#         futures = [executor.submit(predict_exp_vgc, alpha, repr_cost, data, worlds, noisysim_pars) for alpha in np.linspace(0.01, 400, 151)]
#         for future in futures:
#             res = future.result()
#             print(f"alpha={res[0]:.2f}, rmse={res[1]:.4f}, r={res[2]:.4f}")
#             losses.append(future.result())

#     losses = pd.DataFrame(losses, columns=["alpha", "rmse", "r"])
#     losses = losses.sort_values("rmse", ascending=True)
#     losses.to_csv("./output/exp_vgc/vgc_fitting_exp_vgc.csv", index=False)

#     best_alpha = float(losses.iloc[0].alpha)

#     best_predictions = []
#     # for w, world in worlds.items():
#     #     print(w)
#     #     construals = baseline.vgc_discrete(pgw.loadFromDict(world["world"]), noisysim_pars=noisysim_pars, n_simulations=150)
#     #     preds = baseline.vgc_object_preds(construals, temperature=best_alpha)
#     #     world_predictions = pd.DataFrame({"object": list(preds.keys()), "vgc": list(preds.values())})
#     #     world_predictions["world"] = w
#     #     best_predictions.append(world_predictions)
#     # best_predictions = pd.concat(best_predictions, ignore_index=True)
#     # best_predictions.to_csv("./output/exp_vgc/best_vgc_predictions_exp_vgc.csv", index=False)

#     return losses, best_predictions


if __name__ == "__main__":
    # cache_construals(n_simulations=250)
    losses, best_predictions = fit_exp1()
    # cache_construals_vgc(n_simulations=250)
    # cache_construals_vgc2(n_simulations=500)
    # losses, best_predictions = fit_exp_vgc(repr_cost=0.01)