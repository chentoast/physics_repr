import math
import random
import os
import json
from copy import deepcopy

import numpy as np
import scipy as sp

from creator import EventWorldCreator
import pyGameWorld as pgw
from pyGameWorld.simulate import simulate_path, simulate_noisypaths


class PlinkoCreator(EventWorldCreator):
    def createFromConfig(self, cfg):
        w = self.createWorld(cfg)
        # self.createBall(w, cfg)
        self.createBall(w, cfg, ballpos=300) # for vgc experiment, fix ball position
        self.createGoals(cfg, w)
        if cfg["area_type"]["top"] == "bumpers":
            self.createTopBumpers(
                cfg,
                w,
                top=cfg["ball_info"]["y_pos"] - self._ball["ballrad"] - 10,
                bottom=cfg["world_size"][1] // 2,
            )
        if cfg["area_type"]["bottom"] == "bumpers":
            self.createBottomBumpers(
                cfg,
                w,
                top=cfg["world_size"][1] // 2,
                bottom=cfg["goal_info"]["height"] + 10,
            )

        # create sensor to allow us to split the path into top/bottom
        w.addSensor(
            "hole_0",
            [
                0,
                cfg["world_size"][1] // 2 - 10,
                cfg["world_size"][0],
                cfg["world_size"][1] // 2,
            ],
        )
        self._pgw = w
        self._pgw_dict = w.toDict()
        self._ngoals = cfg["goal_info"]["number"]
        self._nholes = 1

    def createWorld(self, cfg):
        w = pgw.PGWorld(cfg["world_size"], cfg["gravity"])
        return w

    def createBall(self, w, cfg, **kw):
        # Place the ball
        ballpos = kw.get("ballpos", None) or random.randint(
            cfg["ball_info"]["pos_range"][0], cfg["ball_info"]["pos_range"][1]
        )
        ballrad = kw.get("ballrad", None) or random.randint(
            cfg["ball_info"]["rad_range"][0], cfg["ball_info"]["rad_range"][1]
        )
        color = kw.get("color", None) or "red"
        elasticity = kw.get("elasticity", None)
        w.addBall(
            "FOCUS",
            [ballpos, cfg["ball_info"]["y_pos"]],
            ballrad,
            color,
            1,
            elasticity=elasticity,
        )

        self._ball = {"ballpos": ballpos, "ballrad": ballrad}

    def createGoals(self, cfg, w):
        # Set up the goals
        goal_names = []
        if cfg["goal_info"]["eq_space"]:
            ngoal = cfg["goal_info"]["number"]
            ea_sp = cfg["world_size"][0] / ngoal
            ghght = cfg["goal_info"]["height"]
            for i in range(ngoal):
                xmin = i * ea_sp
                xmax = (i + 1) * ea_sp
                w.addContainer(
                    "goal_" + str(i),
                    [[xmin, ghght], [xmin, 0], [xmax, 0], [xmax, ghght]],
                    10,
                    "green",
                    "black",
                    0,
                )
                goal_names.append("goal_" + str(i))
            w.attachSpecificInGoalSet("FOCUS", goal_names, 0.1)
        else:
            raise NotImplementedError("Unequal goal sizes not implemented yet")

    def createTopBumpers(self, cfg, w, top, bottom):
        bumps = []
        nbumps = random.randint(
            cfg["bumper_info"]["number_range"][0], cfg["bumper_info"]["number_range"][1]
        )
        while len(bumps) < nbumps:
            propb = self._makeBumper(cfg, bumps, bottom, top)
            if propb is not None:
                bumps.append(propb)
        for i, (vertices, _, __) in enumerate(bumps):
            w.addPoly(f"topbump_{i}", vertices, "black", 0)

    def createBottomBumpers(self, cfg, w, top, bottom):
        bumps = []
        # if cfg['hole_info']['has_chute']:
        #     top -= cfg['hole_info']['divider_height']
        nbumps = random.randint(
            cfg["bumper_info"]["number_range"][0], cfg["bumper_info"]["number_range"][1]
        )
        while len(bumps) < nbumps:
            propb = self._makeBumper(cfg, bumps, bottom, top)
            if propb is not None:
                bumps.append(propb)
        for i, (vertices, _, __) in enumerate(bumps):
            w.addPoly(f"bottombump_{i}", vertices, "black", 0)

    @staticmethod
    def _makeBumper(cfg, existBumps, bottom, top, x=None, y=None, divider=None):
        worldx = cfg["world_size"][0]

        # Propose new bumper
        rad = random.randint(cfg["bumper_info"]["rad_range"][0], cfg["bumper_info"]["rad_range"][1])
        nSides = random.randint(cfg["bumper_info"]["min_sides"], cfg["bumper_info"]["max_sides"])

        centerx = x or random.randint(0 + rad, worldx - rad)
        centery = y or random.randint(bottom + rad, top - rad)

        # sample vertices as points on a circle with radius rad
        vertices = [None] * nSides
        thetas = [(2 * math.pi * i) / nSides for i in range(1, nSides + 1)]
        for i in range(nSides):
            theta = thetas[i] + random.random() * 1.2 - 0.6
            px = rad * math.cos(theta)
            py = rad * math.sin(theta)

            vertices[i] = (centerx + px, centery + py)

        if divider is not None:
            # Add logic to make sure that the bumpers don't overlap
            raise NotImplementedError("Dividers not yet implemented")

        for _, ebpos, ebrad in existBumps:
            dx = ebpos[0] - centerx
            dy = ebpos[1] - centery
            dist = np.sqrt(dx * dx + dy * dy)
            if dist < (ebrad + rad):
                return None
        return (vertices, (centerx, centery), rad)

    def checkAndReturn(self, passFailures=False):
        odict = super().checkAndReturn(passFailures)
        if odict is None:
            return None
        odict["worldType"] = self.classifyWorld(self.noisePaths)
        return odict

    # Checks that:
    #  1) There is not too much or too little dynamic varaince on the top/bottom
    #  2) The distribution of intermediate outcomes is not too great or too little
    #  3) The distribution of end goals is not too great or too litte
    def checkConsistency(self, cfg=None, silent=False):
        if cfg is None:
            cfg = getattr(self, "_constraint_info", None)
            if not cfg:
                print("no constraints: returning without checking consistency")
                return True

        if len(self.sensorHits.values()) == 0:
            print("Ball never touches a sensor")
            return False
        # elif len(self.sensorHits.values()) > 1:
        #     print("Ball somehow hits multiple sensors")
        #     return False

        # Filter out noisy paths that don't terminate
        usepaths = self.filterPaths(self.noisePaths)
        pct_unused = (len(self.noisePaths) - len(usepaths)) / len(self.noisePaths)
        if pct_unused > cfg["max_no_outcome"]:
            if not silent:
                print("Too many simulation paths got stuck:", pct_unused)
            return False

        if not self.checkGoalVariance(usepaths, cfg, silent):
            return False

        splitpaths = self.splitPaths(usepaths)
        if not self.checkPaths(splitpaths, cfg, silent):
            return False

        # Go through all goals and check lowest contingent p for each
        goalnames = ["goal_" + str(i) for i in range(self._ngoals)]
        low_contingent = {}
        for g in goalnames:
            cps = [p[g] for p in self.norm_contingent.values()]
            low_contingent[g] = min(cps)
        self.outcomeMisc["min_contingent_goals"] = low_contingent
        mconting = max(low_contingent.values())
        if mconting < cfg["min_goal_overlap"]:
            if not silent:
                print("Too little goal overlap:", mconting)
            return False
        if mconting > cfg["max_goal_overlap"]:
            if not silent:
                print("Too much goal overlap:", mconting)
            return False

        return True

    def filterPaths(self, paths):
        return [p for p in paths if p["goal"] != "NONE" and len(p["sensors"]) == 1]

    def splitPaths(self, paths):
        # Split the paths by which hole they go through - and also into their top / bottom portions
        for t in self.sensorHits.values():
            splittime = t
        splitidx_display = int((splittime / self.dSS) + 0.0000001)
        splitidx_sim = int(np.floor(splitidx_display / self._ssp))
        contingent_g = dict(
            [
                (
                    "hole_" + str(i),
                    dict([("goal_" + str(i), 0) for i in range(self._ngoals)]),
                )
                for i in range(self._nholes)
            ]
        )
        splitpaths = {}
        for p in paths:
            # Split the path into top/bottom
            hole = p["sensors"][0][0]
            splittime = p["sensors"][0][1]

            splitidx_sim = int((splittime / self.sSS) + 0.0000001)
            toppath = {"path": {"FOCUS": p["path"]["FOCUS"][:splitidx_sim]}}
            bottompath = {"path": {"FOCUS": p["path"]["FOCUS"][splitidx_sim:]}}

            # Find the contingent goal probabilities
            contingent_g[hole][p["goal"]] += 1

            if hole in splitpaths.keys():
                splitpaths[hole]["top"].append(toppath)
                splitpaths[hole]["bottom"].append(bottompath)
            else:
                splitpaths[hole] = {}
                splitpaths[hole]["top"] = [toppath]
                splitpaths[hole]["bottom"] = [bottompath]

        self.contingent_g = contingent_g

        return splitpaths

    def checkGoalVariance(self, paths, cfg, silent):
        # Get the variance of goal outcomes
        goutcomes = dict([("goal_" + str(i), 0) for i in range(self._ngoals)])
        for p in paths:
            g = p["goal"]
            goutcomes[g] += 1
        gtot = sum(goutcomes.values())
        houtcomes = dict([("hole_" + str(i), 0) for i in range(self._nholes)])
        goutnorm = dict([(k, v / gtot) for k, v in goutcomes.items()])
        houtnorm = dict([(k, v / gtot) for k, v in houtcomes.items()])

        # mingpct = min(goutnorm.values())
        maxgpct = max(goutnorm.values())

        self.outcomeMisc["event_outcomes"] = {"holes": houtnorm, "goals": goutnorm}

        if maxgpct > cfg["max_largest_goal_outcome"]:
            if not silent:
                print("Not enough variance in goal outcomes")
            return False
        if maxgpct < cfg["min_largest_goal_outcome"]:
            if not silent:
                print("Too much variance in goal outcomes")
            return False

        return True

    def checkPaths(self, splitpaths, cfg, silent):
        norm_contingent = {}
        foc_at_split = dict([("hole_" + str(i), []) for i in range(self._nholes)])

        self.outcomeMisc["path_variances"] = {}
        self.outcomeMisc["contingent_goals_max_prob"] = {}
        self.outcomeMisc["focus_prop_transition"] = {}

        for hnames, houtcomes in splitpaths.items():
            toprmses = self.calcPathVarDTW(houtcomes["top"])
            btmrmses = self.calcPathVarDTW(houtcomes["bottom"])
            self.outcomeMisc["path_variances"][hnames] = {
                "top": np.mean(toprmses),
                "bottom": np.mean(btmrmses),
            }

            if (cfg["max_dyn_top"] > -1) and (np.mean(toprmses) > cfg["max_dyn_top"]):
                if not silent:
                    print("Too much variance in the top:", hnames, np.mean(toprmses))
                return False
            if (cfg["max_dyn_bottom"] > -1) and (np.mean(btmrmses) > cfg["max_dyn_bottom"]):
                if not silent:
                    print("Too much variance in the bottom:", hnames, np.mean(btmrmses))
                return False
            if np.mean(toprmses) < cfg["min_dyn_top"]:
                if not silent:
                    print("Too little variance in the top:", hnames, np.mean(toprmses))
                return False
            if np.mean(btmrmses) < cfg["min_dyn_bottom"]:
                if not silent:
                    print("Too little variance in the bottom:", hnames, np.mean(btmrmses))
                return False

            # Get contingent goal probabilities
            toth = sum(self.contingent_g[hnames].values())
            max_contingent = max(self.contingent_g[hnames].values()) / toth
            norm_contingent[hnames] = dict(
                [(h, v / toth) for h, v in self.contingent_g[hnames].items()]
            )
            self.outcomeMisc["contingent_goals_max_prob"][hnames] = max_contingent

            if max_contingent > cfg["max_largest_contingent_goal"]:
                if not silent:
                    print("Too concentrated in contingent goals:", hnames, max_contingent)
                return False
            if max_contingent < cfg["min_largest_contingent_goal"]:
                if not silent:
                    print(
                        "Too little concentration in contingent goals:",
                        hnames,
                        max_contingent,
                    )
                return False

            # Check how much variance there is in position/velocity going into
            # the bottom part
            br_xs = [p[0] for p in foc_at_split[hnames]]
            br_vs = [p[3:] for p in foc_at_split[hnames]]

            def _euclid(v):
                return np.sqrt(v[0] * v[0] + v[1] * v[1])

            br_vel = [_euclid(p) for p in br_vs]
            br_ang = [np.arctan2(p[1], p[0]) for p in br_vs]

            xstd = np.std(br_xs)
            velstd = np.std(br_vel)
            angstd = sp.stats.circstd(br_ang)
            self.outcomeMisc["focus_prop_transition"][hnames] = {
                "xpos_std": xstd,
                "vel_std": velstd,
                "ang_std": angstd,
            }
            if xstd > cfg["max_transition_x"]:
                if not silent:
                    print("Too much std in x on transition:", hnames, xstd)
                return False
            if velstd > cfg["max_transition_vel"]:
                if not silent:
                    print("Too much std in velocity on transition:", hnames, velstd)
                return False
            if angstd > cfg["max_transition_angle"]:
                if not silent:
                    print("Too much std in velocity angle on transition:", hnames, angstd)
                return False
            if (
                xstd < cfg["min_transition_x"]
                and velstd < cfg["min_transition_vel"]
                and angstd < cfg["min_transition_angle"]
            ):
                if not silent:
                    print(
                        "Too little variability in transition",
                        hnames,
                        xstd,
                        velstd,
                        angstd,
                    )
                return False

        self.norm_contingent = norm_contingent
        return True

    def classifyWorld(self, pathCollisions):
        bottoms = [k for k in self._pgw.objects if k.startswith("bottom")]
        for o in bottoms:
            n_collisions = 0
            for path in pathCollisions:
                for col in path["collisions"]:
                    if col[0] == "FOCUS" and col[1] == o:
                        n_collisions += 1
                        break
            p_collisions = n_collisions / len(pathCollisions)
            if p_collisions > 0.4 and p_collisions < 0.6:
                return "maybe"
            if p_collisions > 0.95:
                return "definite"
        return "NA"

class PlinkoSplitCreator(PlinkoCreator):
    def loadWorld(self, worlds):
        self._pgw = worlds[0]
        self._pgw_dict = self._pgw.toDict()

        self._pgw2 = worlds[1]
        self._pgw_dict2 = self._pgw2.toDict()

    def createFromConfig(self, cfg):
        self.cfg = cfg
        w = self.createWorld(cfg)
        self.w = w

        # it's a bit annoying to delete objects in a world, so we'll just save the ball position and radius and re-create it when necessary
        self.ballpos = random.randint(
            cfg["ball_info"]["pos_range"][0], cfg["ball_info"]["pos_range"][1]
        )
        self.ballrad = random.randint(
            cfg["ball_info"]["rad_range"][0], cfg["ball_info"]["rad_range"][1]
        )

        self.createGoals(cfg, self.w)

        self._bumps = []
        self.createSplitBlock()

        self.def_elasticity = 0.1
        self.alt_elasticity = cfg.get("alt_elasticity", None) or 0.8
        self.bumper_elasticity = 0.5
        self.simulateSplit(cfg)

        for i in range(np.random.randint(1, 5)):
            bump = self._makeBumper(
                self.cfg,
                self._bumps,
                bottom=0,
                top=self.cfg["ball_info"]["y_pos"] - self._ball["ballrad"] - 10,
            )
            if bump is None:
                continue
            self._bumps.append(bump)
        self.w.addPoly(f"bump_{i + 3}", bump[0], "black", 0, 0.8)

        # create sensor to allow us to split the path into top/bottom
        self.w.addSensor(
            "hole_0",
            [
                0,
                cfg["world_size"][1] // 2 - 10,
                cfg["world_size"][0],
                cfg["world_size"][1] // 2,
            ],
        )

        self._pgw = self.w
        self._pgw2 = self.w.copy()
        self.createBall(
            self._pgw,
            cfg,
            ballpos=self.ballpos,
            ballrad=self.ballrad,
            elasticity=self.def_elasticity,
            color="red",
        )
        self.createBall(
            self._pgw2,
            cfg,
            ballpos=self.ballpos,
            ballrad=self.ballrad,
            elasticity=self.alt_elasticity,
            color="blue",
        )

        self._pgw_dict = self._pgw.toDict()
        self._pgw_dict2 = self._pgw2.toDict()
        self._ngoals = cfg["goal_info"]["number"]
        self._nholes = 1

    def createSplitBlock(self):
        vertices, center, rad = self._makeBumper(
            self.cfg,
            [],
            bottom=self.cfg["world_size"][1] // 2,
            # top=self.cfg["ball_info"]["y_pos"] - self._ball["ballrad"] - 50,
            top=self.cfg["ball_info"]["y_pos"] - self.ballrad - 50,
            # x=self._ball["ballpos"],
            x=self.ballpos,
        )
        self.w.addPoly("bump_0", vertices, "black", 0)

        self._bumps.append((vertices, center, rad))

    def simulateSplit(self, cfg):
        i = 1
        print("simulating with elasticity", self.alt_elasticity)

        def simulateAndPlace(w, elasticity=0.5, starttime=0, stepsize=0.02):
            self.createBall(
                w, cfg, ballpos=self.ballpos, ballrad=self.ballrad, elasticity=elasticity
            )
            path = simulate_path(w, stepsize)
            starttime = 0
            for o1, o2, event, t, data in w.collisionEvents:
                if o1 == "FOCUS" and o2 == "bump_0" and event == "end":
                    starttime = t
                    break

            print("times", starttime, len(path["FOCUS"]) * stepsize)

            sampled_t = np.random.uniform(starttime + 0.3, len(path["FOCUS"]) * stepsize - 0.3)
            print("sampled", sampled_t, sampled_t / stepsize)

            loc = path["FOCUS"][int(sampled_t / stepsize)][:2]
            print("placed object location", loc)
            bump = self._makeBumper(self.cfg, self._bumps, bottom=0, top=0, x=loc[0], y=loc[1])

            if bump is None:
                return

            self.w.addPoly(f"bump_{i}", bump[0], "red", 0)
            self._bumps.append(bump)

        # new_world = self.w.copy()
        # del new_world.objects["FOCUS"]
        # self.createBall(
        #     new_world,
        #     cfg,
        #     ballpos=self._ball["ballpos"],
        #     ballrad=self._ball["ballrad"],
        #     elasticity=alt_elasticity,
        # )

        simulateAndPlace(self.w.copy(), elasticity=self.def_elasticity)

        i += 1

        simulateAndPlace(self.w.copy(), elasticity=self.alt_elasticity)

    # Runs the world to determine simulated outcomes
    def initial_run(self):
        self.paths = simulate_path(self._pgw, 0.02, 20.0)
        self.paths1 = simulate_path(self._pgw2, 0.02, 20.0)

        self.endgoal = self._pgw.goalCond.getWinningGoal()
        self.endtime = self._pgw.time
        self.sensorHits = {}
        self.collisions = []
        for sh in self._pgw.sensorHits:
            if sh[0] == "FOCUS":
                self.sensorHits[sh[1]] = sh[2]
        self._run = True

    def run(self, npaths=40, noisedict={}):
        self.initial_run()
        if self.endgoal == "NONE":
            print("Created world without termination")
        print("Creating noisy paths...")
        self.noisePaths = simulate_noisypaths(
            pgw.loadFromDict(self._pgw_dict), self.dSS, npaths, **noisedict
        )
        self.noisePaths1 = simulate_noisypaths(
            pgw.loadFromDict(self._pgw_dict2), self.dSS, npaths, **noisedict
        )

    def checkAndReturn(self, passFailures=False):
        self.calcPathVariability()
        print("Checking path acceptability...")
        if not self.checkConsistency():
            print("Failed consistency checks")
            if not passFailures:
                return None
        print("Passed consistency checks")

        odict = {
            "world": self._pgw_dict,
            "world1": self._pgw_dict2,
            "outcome": {
                "goalHit": self.endgoal,
                "endTime": self.endtime,
                "sensorsHit": self.sensorHits,
                "noisePaths": self.noisePaths,
                "noisePaths1": self.noisePaths1,
                "noiseRMSE": self.noiseRMSE,
                "other": self.outcomeMisc,
            },
            "displayPath": self.paths,
            "displayPath1": self.paths1,
            "displayCfg": {"displayStepSize": self.dSS},
        }
        return odict

    def loadFromSingle(self, jdict, cfg={}):
        jdict = deepcopy(jdict)

        for name, _ in jdict["world"]["objects"].items():
            jdict["world"]["objects"][name]["elasticity"] = 0.8

        # create a split world from a dictionary dump of a single ball world
        self._pgw_dict = jdict["world"]
        self._pgw_dict2 = deepcopy(jdict["world"])

        self._pgw_dict["objects"]["FOCUS"]["elasticity"] = 0.1

        self._pgw_dict2["objects"]["FOCUS"]["elasticity"] = 0.8
        self._pgw_dict2["objects"]["FOCUS"]["color"] = "blue"

        self._pgw = pgw.loadFromDict(self._pgw_dict)
        self._pgw2 = pgw.loadFromDict(self._pgw_dict2)


class PlinkoTeleportCreator(PlinkoCreator):
    def loadWorld(self, worlds):
        self._pgw = worlds[0]
        self._pgw_dict = self._pgw.toDict()

        self._pgw1 = worlds[1]
        self._pgw_dict1 = self._pgw1.toDict()

    def createFromConfig(self, cfg):
        self.cfg = cfg
        w = self.createWorld(cfg)
        self.w = w
        self.w1 = w.copy()

        self.createBall(
            self.w,
            cfg,
            # elasticity=self.def_elasticity,
            color="red",
        )
        self.createBall(
            self.w1,
            cfg,
            ballpos=self._ball["ballpos"],
            ballrad=self._ball["ballrad"],
            color="red",
        )

        self.createGoals(cfg, self.w)
        self.createGoals(cfg, self.w1)
        self.createTeleporter()
        self._bumps = []

        # bumper_elasticity = 0.8
        for i in range(np.random.randint(2, 6)):
            bump = self._makeBumper(
                self.cfg,
                self._bumps,
                bottom=cfg["goal_info"]["height"] + 10,
                top=cfg["ball_info"]["y_pos"] - self._ball["ballrad"] - 10,
            )
            if bump is None:
                continue
            self._bumps.append(bump)
            self.w.addPoly(f"bump_{i}", bump[0], "black", 0)
            self.w1.addPoly(f"bump_{i}", bump[0], "black", 0)

        # create sensor to allow us to split the path into top/bottom
        self.w.addSensor(
            "hole_0",
            [
                0,
                cfg["world_size"][1] // 2 - 10,
                cfg["world_size"][0],
                cfg["world_size"][1] // 2,
            ],
        )

        self._pgw = self.w
        self._pgw1 = self.w1

        self._pgw_dict = self._pgw.toDict()
        self._pgw_dict1 = self._pgw1.toDict()
        self._ngoals = cfg["goal_info"]["number"]
        self._nholes = 1

    def createTeleporter(self):
        bottom = self.cfg["world_size"][1] // 2
        top = self.cfg["ball_info"]["y_pos"] - self._ball["ballrad"] - 10
        rad = self._ball["ballrad"]
        c = (
            self._ball["ballpos"],
            random.randint(bottom + rad, top - rad),
        )
        c1 = (
            random.randint(0 + rad, self.cfg["world_size"][0] - rad),
            random.randint(bottom + rad, top - rad),
        )

        r = random.randint(
            self.cfg["bumper_info"]["rad_range"][0], self.cfg["bumper_info"]["rad_range"][1]
        )
        color1 = (140, 92, 71, 150)
        color2 = (1, 97, 128, 150)
        self.w.addTeleporter("teleport_entry", list(c), r, list(c1), is_entry=True, color=color1)
        self.w.addTeleporter("teleport_exit", list(c1), r, list(c1), is_entry=False, color=color2)

        self.w1.addTeleporter("teleport_entry", list(c1), r, list(c), is_entry=True, color=color1)
        self.w1.addTeleporter("teleport_exit", list(c), r, list(c), is_entry=False, color=color2)

    # Runs the world to determine simulated outcomes
    def initial_run(self):
        self.paths = simulate_path(self._pgw, 0.02, 20.0)
        self.paths1 = simulate_path(self._pgw1, 0.02, 20.0)

        self.endgoal = self._pgw.goalCond.getWinningGoal()
        self.endtime = self._pgw.time
        self.sensorHits = {}
        self.collisions = []
        for sh in self._pgw.sensorHits:
            if sh[0] == "FOCUS":
                self.sensorHits[sh[1]] = sh[2]
        self._run = True

    def run(self, npaths=40, noisedict={}):
        self.initial_run()
        if self.endgoal == "NONE":
            print("Created world without termination")
        print("Creating noisy paths...")
        self.noisePaths = simulate_noisypaths(
            pgw.loadFromDict(self._pgw_dict), self.dSS, npaths, **noisedict
        )
        self.noisePaths1 = simulate_noisypaths(
            pgw.loadFromDict(self._pgw_dict1), self.dSS, npaths, **noisedict
        )

    def checkAndReturn(self, passFailures=False):
        self.calcPathVariability()
        print("Checking path acceptability...")
        if not self.checkConsistency():
            print("Failed consistency checks")
            if not passFailures:
                return None
        print("Passed consistency checks")

        odict = {
            "world": self._pgw_dict,
            "world1": self._pgw_dict1,
            "outcome": {
                "goalHit": self.endgoal,
                "endTime": self.endtime,
                "sensorsHit": self.sensorHits,
                "noisePaths": self.noisePaths,
                "noisePaths1": self.noisePaths1,
                "noiseRMSE": self.noiseRMSE,
                "other": self.outcomeMisc,
            },
            "displayPath": self.paths,
            "displayPath1": self.paths1,
            "displayCfg": {"displayStepSize": self.dSS},
        }
        return odict

    def loadFromSingle(self, jdict, cfg={}):
        jdict = deepcopy(jdict)

        for name, _ in jdict["world"]["objects"].items():
            jdict["world"]["objects"][name]["elasticity"] = 0.8

        # create a split world from a dictionary dump of a single ball world
        self._pgw_dict = jdict["world"]
        self._pgw_dict1 = deepcopy(jdict["world"])

        self._pgw_dict["objects"]["FOCUS"]["elasticity"] = 0.1

        self._pgw_dict1["objects"]["FOCUS"]["elasticity"] = 0.8
        self._pgw_dict1["objects"]["FOCUS"]["color"] = "blue"

        self._pgw = pgw.loadFromDict(self._pgw_dict)
        self._pgw2 = pgw.loadFromDict(self._pgw_dict1)


class PlinkoFunnelCreator(PlinkoCreator):
    def loadConfig(self, cfg):
        print("load config")
        print("=" * 50)
        w = self.createWorld(cfg)
        self.createGoals(cfg, w)
        self.createFunnels(cfg, w)
        if cfg["area_type"]["top"] == "bumpers":
            self.createTopBumpers(
                cfg,
                w,
                top=cfg["ball_info"]["y_pos"] - self._ball["ballrad"] - 10,
                bottom=self._funnels["ymax"] + 10,
            )
        if cfg["area_type"]["bottom"] == "bumpers":
            top = self._funnels["ymin"] - 10
            if cfg["hole_info"]["has_chute"]:
                top -= cfg["hole_info"]["divider_height"]
            self.createBottomBumpers(cfg, w, top=top, bottom=cfg["goal_info"]["height"] + 10)

        self._pgw = w
        self._pgw_dict = w.toDict()
        self._nholes = cfg["hole_info"]["number"]
        self._ngoals = cfg["goal_info"]["number"]

    def createFunnels(self, cfg, w):
        nhole = cfg["hole_info"]["number"]
        print(nhole)
        secsize = cfg["world_size"][0] / nhole
        hole_sections = [[i * secsize, (i + 1) * secsize] for i in range(nhole)]
        divymin = random.randint(
            cfg["hole_info"]["ypos_range"][0], cfg["hole_info"]["ypos_range"][1]
        )
        holes = []
        for hs in hole_sections:
            hwidth = random.randint(
                cfg["hole_info"]["width_range"][0], cfg["hole_info"]["width_range"][1]
            )
            xmin = random.randint(hs[0] + 5, hs[1] - hwidth - 5)
            holes.append([xmin, xmin + hwidth])
        # Build the top/bottom divider around the holes,
        # add some padding just for space
        dh = cfg["hole_info"]["divider_height"]
        divverts = [[0, divymin + dh], [holes[0][0], divymin]]
        if cfg["hole_info"]["has_chute"]:
            divverts.append([holes[0][0], divymin - dh])
            divverts.append([0, divymin - dh])
        else:
            divverts.append([0, divymin])
        w.addPoly("divL", divverts, "black", 0)

        if len(holes) > 1:
            for i in range(len(holes) - 1):
                midpt = (holes[i][1] + holes[i + 1][0]) / 2
                divverts = [
                    [holes[i][1], divymin],
                    [midpt, divymin + dh],
                    [holes[i + 1][0], divymin],
                ]
                if cfg["hole_info"]["has_chute"]:
                    divverts.append([holes[i + 1][0], divymin - dh])
                    divverts.append([holes[i][1], divymin - dh])
            w.addPoly("div" + str(i), divverts, "black", 0)

        divverts = [[holes[-1][1], divymin], [cfg["world_size"][0], divymin + dh]]
        if cfg["hole_info"]["has_chute"]:
            divverts.append([cfg["world_size"][0], divymin - dh])
            divverts.append([holes[-1][1], divymin - dh])
        else:
            divverts.append([cfg["world_size"][0], divymin])
        w.addPoly("divR", divverts, "black", 0)

        # Add sensors for each of the holes
        for i, h in enumerate(holes):
            w.addSensor("hole_" + str(i), [h[0], divymin - 10, h[1], divymin])

        self._funnels = {"ymin": divymin, "ymax": divymin + dh}


if __name__ == "__main__":
    with open("default_sim_noise.json", "r") as dsnfl:
        defaultSimNoise = json.load(dsnfl)
    nworldsper = 1

    nmade = 0
    oname = "tmpplinko.json"
    while nmade < nworldsper:
        plcr = PlinkoCreator(os.path.join("worldconfigs", "plinko_maker.json"))
        winfo = plcr.checkAndReturn(noisedict=defaultSimNoise)
        if winfo is not None:
            with open(oname.format(nmade), "w") as ofl:
                json.dump(winfo, ofl)
            nmade += 1
