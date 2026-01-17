import json
from functools import lru_cache
import concurrent.futures
import os

import numpy as np
import pymunk as pm
from scipy.spatial.distance import cosine
import scipy.stats as sps
import pandas as pd

import pyGameWorld as pgw
from pyGameWorld.noisyWorld import noisifyWorld
from pyGameWorld.simulate import simulate_noisypaths, simulate_noisypaths_parallel

with open("/Users/tony/repos/physics_events/stimuli/default_sim_noise.json") as f:
    defaultSimNoise = json.load(f)


@lru_cache
def lookup_transform(wname, cond):
    with open(f"../../experiments/assets/exp1/targets/{wname}/{cond}blue.json") as f:
        t1 = json.load(f)

    with open(f"../../experiments/assets/exp1/targets/{wname}/{cond}1blue.json") as f:
        t2 = json.load(f)

    return [t1["shiftx"], t1["shifty"]], [t2["shiftx"], t2["shifty"]]


def lookahead(world: pgw.world.PGWorld, radius, tracked):
    tmpbody = pm.Body(1, 1)
    spotlight = pm.Circle(tmpbody, radius, world.objects["FOCUS"].position.tolist())

    query = world._cpSpace.shape_query(spotlight)
    if len(query) < 1:
        return

    for queryresult in query:
        if queryresult.shape is None:
            continue
        # if queryresult.shape.name == "FOCUS" or queryresult.shape.sensor or queryresult.shape.name.startswith("_"):
        if "bump" not in queryresult.shape.name:
            # don't count the focus object
            continue

        if queryresult.shape.name in tracked:
            continue

        shape = queryresult.shape

        dr = shape.center_of_gravity - world.objects["FOCUS"]._cpBody.position
        v = world.objects["FOCUS"]._cpBody.velocity

        distance = np.clip(1 - cosine(dr.normalized(), v.normalized()), 0, 1)

        yield shape.name, distance


def process_model(world, radius, n_sims, noisysim_pars, similarity=True, decay=1.0):
    obj_reprs = {name: 0.0 for name in world.objects if "bump" in name}
    maxtime = 20.0
    for _ in range(n_sims):
        sim_reprs = {name: 0.0 for name in world.objects if "bump" in name}
        steps_since_tracked = {name: 0 for name in world.objects if "bump" in name}
        nw = noisifyWorld(world, **noisysim_pars)

        tracked = set()

        running = True
        paths = {}
        tracknames = []
        steps = 1
        for onm, o in world.objects.items():
            if o.isStatic():
                continue
            tracknames.append(onm)
            paths[onm] = [[o.position[0], o.position[1], o.rotation, o.velocity[0], o.velocity[1]]]
        while running:
            nw.step(1 / 60)
            for onm in tracknames:
                paths[onm].append(
                    [
                        nw.objects[onm].position[0],
                        nw.objects[onm].position[1],
                        nw.objects[onm].rotation,
                        nw.objects[onm].velocity[0],
                        nw.objects[onm].velocity[1],
                    ]
                )

            for obj, distance in lookahead(nw, radius, tracked):
                sim_reprs[obj] = distance if similarity else 1.0
                steps_since_tracked[obj] = 1
                for _obj in sim_reprs:
                    if _obj != obj:
                        if steps_since_tracked[_obj] == 0:
                            continue
                        # sim_reprs[_obj] *= decay
                        # power law
                        sim_reprs[_obj] = sim_reprs[_obj] * (1 + 1 / steps_since_tracked[_obj]) ** (
                            -decay
                        )
                        steps_since_tracked[_obj] += 1

                tracked.add(obj)

            if (nw.checkEnd()) or (nw.time >= maxtime):
                running = False

        for obj, distance in sim_reprs.items():
            obj_reprs[obj] += distance
    return {k: v / n_sims for k, v in obj_reprs.items()}, paths


def model_predict(worlds, noisysim_pars, radius=25, n_sims=50, decay=0.0):
    out = []
    for wname, world in worlds.items():
        print(wname)
        # out[wname] = process_model(world, radius=radius, n_sims=n_sims)
        if isinstance(world, dict):
            world = pgw.loadFromDict(world["world"])
        obj_probs, _ = process_model(
            world, radius=radius, n_sims=n_sims, noisysim_pars=noisysim_pars, decay=decay
        )
        data = {"obj_name": list(obj_probs.keys()), "model_p": list(obj_probs.values())}
        world_predictions = pd.DataFrame(data)
        world_predictions["world"] = wname
        out.append(world_predictions)
    return pd.concat(out)


def fit_decay(worlds, human_data, noisysim_pars, radius=25, n_sims=50):
    losses = pd.DataFrame(columns=["decay", "cor"])
    decays = np.linspace(0, 1.0, 16)
    for decay in decays:
        model_data = model_predict(worlds, noisysim_pars, radius=radius, n_sims=n_sims, decay=decay)
        merged = human_data.merge(
            model_data.rename(columns={"obj_name": "object"}), on=["world", "object"]
        )
        corr = merged[["correct", "model_p"]].corr().iloc[0, 1]
        losses.loc[len(losses)] = [decay, corr]
    return losses


def fit_decay_rmse(worlds, human_data, noisysim_pars, radius=25, n_sims=50):
    losses = pd.DataFrame(columns=["decay", "rmse"])
    decays = np.linspace(0, 1.0, 16)
    for decay in decays:
        model_data = model_predict(worlds, noisysim_pars, radius=radius, n_sims=n_sims, decay=decay)
        merged = human_data.merge(
            model_data.rename(columns={"obj_name": "object"}), on=["world", "object"]
        )
        merged["model_p"] = 0.333 + 0.667 * merged["model_p"] # scale to [0.333, 1]
        rmse = np.sqrt(((merged["correct"] - merged["model_p"]) ** 2).mean())
        losses.loc[len(losses)] = [decay, rmse]
    return losses


def bootstrap_ci(worlds, human_data, noisysim_pars, n_boot=100, loss="rmse"):
    decays = []
    all_predictions = []
    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = []
        for _ in range(n_boot):
            subsample = human_data.sample(frac=1, replace=True)
            subsample_agg = subsample.groupby(["world", "object"]).correct.mean().reset_index()
            if loss == "cor":
                futures.append(executor.submit(fit_decay, worlds, subsample_agg, noisysim_pars))
            else:
                futures.append(executor.submit(fit_decay_rmse, worlds, subsample_agg, noisysim_pars))

        for future in concurrent.futures.as_completed(futures):
            losses = future.result()
            print(f"finished {future}")
            if loss == "rmse":
                best_decay = losses.loc[losses.rmse.idxmin(), "decay"]
            else:
                best_decay = losses.loc[losses.cor.idxmax(), "decay"]

            decays.append(best_decay)
            all_predictions.append(model_predict(worlds, noisysim_pars, decay=best_decay.item()))
    return decays, pd.concat(all_predictions)


def object_pos_dist(encoding: float, kappa, n_sims=100):
    """
    Assume an object is represented with encoding weight p
    Therefore, if we run n_sims simulations, we expect
    the object to be present in the buffer in p * n_sims of those simulations

    We assume that encoding the object corresponds to sampling from a 2D Gaussian
    with mean at the object's position, and std kappa.
    Thus, the expected uncertainty in the object's position is given by the posterior gaussian
    conditioned on those p * n_sims samples.
    """
    expected_n_encoded = int(encoding * n_sims)
    posterior_var = (1 / (expected_n_encoded * (kappa**-2))) if expected_n_encoded > 0 else 10000

    return posterior_var


def forced_choice(obj_pos_var, lure, alpha=1.0):
    """
    Given the choice between an object at the true position and a lure object, compute the probability
    that the true object is chosen over the lure.
    """
    mu = np.array([0.0, 0.0])
    sigma = np.sqrt(np.array([[obj_pos_var, 0.0], [0.0, obj_pos_var]]))

    dist = sps.multivariate_normal(mu, sigma)

    p_true = dist.logpdf([0.0, 0.0])
    p_lure = dist.logpdf(lure)

    return 1 / (1 + np.exp(-alpha * (p_true - p_lure)))


if __name__ == "__main__":
    exp = "exp1"

    if exp == "exp1":
        data = pd.read_csv("../data/exp1/memory.csv")
        data = pd.wide_to_long(
            data,
            [
                "rt",
                "correct",
                "answer",
                "cond",
                "world",
                "baseImg",
                "modifiedImg",
                "binary_response",
                "response",
            ],
            i="pid",
            j="trial",
        ).reset_index()
    else:
        data = pd.read_csv(f"../data/{exp}/memory.csv")


    @lru_cache
    def lookup_object(filename):
        with open(f"../experiments/{exp}/{filename[:-4]}.json") as f:
            transform = json.load(f)
            return transform["object"]

    data["object"] = data.modifiedImg.apply(lookup_object)
    worlds = {
        w: json.load(open(f"../experiments/assets/{exp}/targets/{w}/{w}.json"))["world"]
        for w in data.world.unique()
    }
    noisysim_pars = {
        "noise_position_static": 0.0,
        "noise_position_moving": 10.0,
        # "noise_position_moving": 5.0,
        "noise_collision_direction": 0.78,
        "noise_collision_elasticity": 0.67,
        "noise_gravity": 0.0,
    }

    w = pgw.loadFromDict(list(worlds.values())[0])
    tmp1 = simulate_noisypaths_parallel(list(worlds.values())[0], 1 / 60, N=2, **noisysim_pars)
    tmp2 = simulate_noisypaths(pgw.loadFromDict(list(worlds.values())[0]), 1 / 60, N=2, **noisysim_pars)

    import pyGameWorld.viewer as view
    import matplotlib.pyplot as plt

    plt.figure()
    view._draw_world_mpl(w)
    view._draw_paths_mpl(w, [p["path"] for p in tmp1])
    plt.axis("off")
    plt.axis("equal")

    plt.figure()
    view._draw_world_mpl(w)
    view._draw_paths_mpl(w, [p["path"] for p in tmp2])
    plt.axis("off")
    plt.axis("equal")

    # decays, all_predictions = bootstrap_ci(worlds, data, noisysim_pars, n_boot=20)

    # if os.path.exists("jit_decays.csv"):
    #     pd.DataFrame(decays, columns=["decay"]).to_csv(
    #         "jit_decays.csv", index=False, header=False, mode="a"
    #     )
    # else:
    #     pd.DataFrame(decays, columns=["decay"]).to_csv("jit_decays.csv", index=False)

    # if os.path.exists("jit_bootstrap.csv"):
    #     all_predictions.to_csv("jit_bootstrap.csv", index=False, header=False, mode="a")
    # else:
    #     all_predictions.to_csv("jit_bootstrap.csv", index=False)
