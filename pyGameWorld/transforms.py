import glob
import json
import math
import os
import random

import numpy as np
import pygame as pg
from scipy.spatial import ConvexHull

from .object import PGPoly
from .helpers import centroidForPoly
from .simulate import simulate_noisypaths

def polygon_area(p):
    return 0.5 * abs(sum(x0*y1 - x1*y0
                         for ((x0, y0), (x1, y1)) in segments(p)))

def segments(p):
    return zip(p, p[1:] + [p[0]])

def flip_angle(angle: float) -> float:
    # Flip the angle by negating its sine and cosine
    flipped_angle = math.atan2(-math.sin(angle), -math.cos(angle))
    return flipped_angle

def wrap(func):
    def called_with_obj_pos(self, **kw):
        pos = pg.mouse.get_pos()
        obj = self.world.getObjectUnderCursor(self.world._invert(pos))
        self.obj = obj
        if obj:
            new_obj = func(self, obj, **kw)
            self.store(obj)
            self.world.setObject(obj.name, new_obj)

    return called_with_obj_pos

class Transform:
    def __init__(self, world, object):
        self.world = world
        self.object = object
        self.transform_data = {} # statistics from last transform run
        self.old_object = object

    def save(self, screen, outdir, fname, stepsize=0.01, noisedict={}):
        import re
        root = "/".join((outdir, fname))
        # find the next available filename
        nexist = [
            f for f in os.listdir(outdir)
            if re.match(rf"{re.escape(fname)}(\d+)?{self.transform_data.get('color', '')}\.jpg", f)
        ]
        print(nexist)
        if nexist:
            # name collision
            # fname = f"{fname}{len(nexist)}"
            fname = f"{fname}{len(nexist)}"

        fname = fname + self.transform_data.get("color", "")
        root = "/".join((outdir, fname))

        print(f"saving {fname}:")
        pg.image.save(screen, root + ".jpg")

        # re-run simulations with modified world
        # noisepaths = simulate_noisypaths(self.world, stepsize, **noisedict)
        # self.transform_data["noisePaths"] = noisepaths
        # breakpoint()
        with open(root + ".json", "w") as f:
            json.dump(self.transform_data, f)
        print("finished saving!")

    def restore(self):
        self.object = self.old_object
        self.world.setObject(self.object.name, self.object)
        self.transform_data = {}

    def color(self, col):
        color_dict = {
            "red": (255, 0, 0),
            "blue": (0, 0, 255)
        }
        self.object = PGPoly(self.object.name, self.object.space, self.object.vertices, density=0, color=color_dict[col])
        self.world.setObject(self.object.name, self.object)
        self.transform_data.update({
            "object": self.object.name,
            "color": col
        })
        self.transform_data.setdefault("type", []).append("color")

    def _translate(self, obj, **transform_data):
        # instead of modifying the object like we do for vertex perturbations,
        # keep the object, and add a new one
        vertices = obj.vertices

        shiftx = transform_data.get("shiftx", None)
        shifty = transform_data.get("shifty", None)

        if not shiftx:
            shiftx = random.random() * 50 + 10
            shifty = random.random() * 50 + 10

            if random.random() < .5:
                shiftx *= -1
            if random.random() < .5:
                shifty *= -1

        shift = np.array([shiftx, shifty])

        vertices_new = [(v + shift).tolist() for v in vertices]

        self.object = PGPoly(self.object.name, self.object.space, vertices_new, density=0, color=(0, 0, 255, 200))
        self.world.setObject(self.object.name, self.object)
        self.world.objects[self.object.name].static = True

        self.transform_data = {
            "type": ["translation"],
            "shiftx": shiftx,
            "shifty": shifty,
            "object": obj.name
        }

    def translate(self, transform_data={}):
        self._translate(self.object, **transform_data)

    def mirror_translate(self):
        if not self.transform_data.get("shiftx", None):
            return None

        data = {}
        data["shiftx"] = -self.transform_data["shiftx"]
        data["shifty"] = -self.transform_data["shifty"]

        self._translate(self.old_object, **data)

    def _perturb_vertex(self, object, **data):
        vertices = object.vertices

        vertex = vertices[0]
        idx = 0
        # closest vertex to cursor
        pos = pg.mouse.get_pos()
        pos = np.array(self.world._invert(pos))
        distance = 500
        for i, v in enumerate(vertices):
            if np.sum((v - pos) ** 2) < distance:
                idx = i
                vertex = v
                distance = np.sum((v - pos) ** 2)

        r = data.get("radius", None) or np.random.exponential(5) + 10
        theta = data.get("angle", None) or np.random.random() * 2 * math.pi
        shift = data.get("shift", None)
        if shift is None:
            shift = np.array([r * np.cos(theta), r * np.sin(theta)])

        vertices_new = vertices[:idx] + [vertex + shift] + vertices[idx+1:]
        self.object = PGPoly(self.object.name, self.object.space, vertices_new, density=0, color=(255, 0, 0, 255))
        self.world.setObject(self.object.name, self.object)

        old_area = polygon_area([vertices[idx] for idx in ConvexHull(vertices).vertices])
        new_area = polygon_area([vertices_new[idx] for idx in ConvexHull(vertices_new).vertices])
        change_area = new_area / old_area

        self.transform_data = {
            "type": "vertex_perturbation",
            "object": self.object.name,
            "shift": list(shift),
            "angle": theta,
            "radius": r,
            "vertex": idx,
            "change_area": change_area
        }

    def perturb_vertex(self):
        self._perturb_vertex(self.object)

    def perturb_vertex_cached(self):
        shift = self.transform_data.get("shift", None)
        if shift is None:
            return

        data = {}
        data["shift"] = shift
        data["radius"] = self.transform_data["radius"]
        data["angle"] = self.transform_data["angle"]

        self._perturb_vertex(self.object, **data)

    def mirror_perturb(self):
        shift = self.transform_data.get("shift", None)
        if shift is None:
            return None

        data = {}
        data["shift"] = -np.array(shift)
        data["radius"] = self.transform_data["radius"]
        data["angle"] = flip_angle(self.transform_data["angle"])

        self._perturb_vertex(self.old_object, **data)

    def drop_vertex(self):
        vertices = self.old_object.vertices
        i = random.randint(0, len(vertices) - 1)
        vertices_new = vertices[:i] + vertices[i+1:]
        self.object = PGPoly(self.object.name, self.object.space, vertices_new, color=(255, 0, 0, 255))
        self.world.setObject(self.object.name, self.object)

        self.transform_data = {
            "type": "vertex_perturbation",
            "object": self.object.name,
        }

    # NOT USED AND NOT UPDATED

    # @wrap
    # def add_vertex(self, object):
    #     vertices = object.vertices
    #     center = centroidForPoly(vertices)
    #     i = random.randint(0, len(vertices) - 1)
    #     j = (i + 1) % len(vertices)

    #     # hack to make new vertex bulge out.
    #     rad1 = math.sqrt(np.power(vertices[i] - center, 2).sum()) + 5
    #     rad2 = math.sqrt(np.power(vertices[j] - center, 2).sum()) + 5
    #     rad = (rad1 + rad2) / 2

    #     midpoint = (vertices[i] + vertices[j]) / 2
    #     theta = math.atan2(midpoint[1] - center[1], midpoint[0] - center[0])
    #     vertex_new = np.array([rad * math.cos(theta), rad * math.sin(theta)]) + center
    #     vertices_new = vertices[:i + 1] + [vertex_new] + vertices[i + 1:]
    #     return PGPoly(object.name, object.space, vertices_new, color=(255, 0, 0, 255))


    # @wrap
    # def rotate(self, object, theta):
    #     vertices = object.vertices
    #     center = centroidForPoly(vertices)

    #     rotation_mat = np.array([[np.cos(theta), -np.sin(theta)],
    #                             [np.sin(theta), np.cos(theta)]])

    #     vertices_new = [(rotation_mat @ (v - center)) + center for v in vertices]
    #     return PGPoly(object.name, object.space, vertices_new, color=(255, 0, 0, 255))
