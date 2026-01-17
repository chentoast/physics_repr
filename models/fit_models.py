import os
import json

import numpy as np
import pandas as pd
from scipy.optimize import minimize

import pyGameWorld as pgw
from baseline_models import Cone, Collisions

def fit_model(model, data):
    return minimize(model.loss, model.get_initial_pars(), (data, ), bounds=model.get_par_bounds())

def load_worlds(root):
    worlds = {}
    for world in os.listdir(root):
        path = "/".join((root, world, world + ".json"))

        with open(path) as f:
            worlds[world] = pgw.loadFromDict(json.load(f)["world"])

    return worlds

if __name__ == "__main__":
    data = pd.read_csv("../data/pilot_translate2/model_data.csv")
    # obj_memory = dict(zip(["object", "memory"], [data["object"], data["correct"]]))
    # print(obj_memory)

    worlds = load_worlds("../experiments/assets/targets")
    model = Cone(worlds)
    # model = Collisions(worlds)
    fit = fit_model(model, data)