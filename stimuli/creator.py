import json
import os

import numpy as np

import pyGameWorld as pgw
from pyGameWorld.simulate import simulate_path, simulate_noisypaths
from dtw import dtw

# with open('default_sim_noise.json', 'r') as dsnfl:
    # defaultSimNoise = json.load(dsnfl)

def _unarray(l):
    try:
        return l.tolist()
    except:
        return l

class EventWorldCreator(object):

    def __init__(self, config_file, maxruntime=20., displayStepSize=0.02,
                 simStepSize=0.1, create=True):
        if create:
            with open(config_file, 'r') as rcfg:
                cfg = json.load(rcfg)
                self._constraint_info = cfg["constraint_info"]
                self.createFromConfig(cfg["world_info"])
        self.mrt = maxruntime  # How long until we stop a simulation for time out
        self.dSS = displayStepSize  # The time between frames for display
        self.sSS = simStepSize  # The time between captures for noisy simulation

        # Calculates the translation between display and simulation steps
        sspTol = .0000001
        sspRaw = simStepSize / displayStepSize
        ssp = int(sspRaw + sspTol)
        ssermsg = "simStepSize must be divisible by displayStepSize"
        assert (abs(ssp - sspRaw) < sspTol), ssermsg
        self._ssp = ssp

        self.noisePaths = None
        self.noiseRMSE = None
        self._run = False
        self.outcomeMisc = {}

        # Checks that this is a properly formatted world:
        #  1) Has a "SpecificInGoalSet" goal
        #  2) Has an object named "FOCUS"
        if create:
            assert self._pgw.goalCond.type in ["SpecificInGoalSet","AnyInGoalSet"], \
                "Goal type must be SpecificInGoalSet or AnyInGoalSet"
            assert "FOCUS" in self._pgw.objects.keys(),\
                "Must have an object named 'FOCUS'"

    def loadWorld(self, world):
        self._pgw = world
        self._pgw_dict = world.toDict()

    # Helper function to turn a config file into a randomly generated pyGameWorld
    # Must set self._pgw with the pyGameWorld World object,
    #   and self._pgw_dict with the dictified World
    def createFromConfig(self, cfg):
        self._pgw = None
        self._pgw_dict = None
        # raise NotImplementedError('Method should be overloaded in child class')

    # Function that checks whether the created world meets the conditions set
    # Must return a boolean: true if a good world, false otherwise
    def checkConsistency(self, cfg = None, silent=False):
        pass
        # if cfg is None:
        #     cfg = self._constraint_info
        # raise NotImplementedError('Method should be overloaded in child class')

    # Check world and output to a JSON file
    def checkAndReturn(self, passFailures=False):
        self.calcPathVariability()
        print("Checking path acceptability...")
        if not passFailures:
            if not self.checkConsistency():
                print('Failed consistency checks')
                return None
                # if not passFailures:
                #     return None
        print("Passed consistency checks")

        odict = {
            "world": self._pgw_dict,
            "outcome": {
                "goalHit": self.endgoal,
                "endTime": self.endtime,
                "sensorsHit": self.sensorHits,
                "noisePaths": self.noisePaths,
                "noiseRMSE": self.noiseRMSE,
                "other": self.outcomeMisc
            },
            "displayPath": self.paths,
            "displayCfg": {
                'displayStepSize': self.dSS
            },
        }
        return odict

    # Runs the world to determine simulated outcomes
    def run(self, npaths=40, noisedict={}):
        self.initial_run()
        if self.endgoal == 'NONE':
            print('Created world without termination')
        print("Creating noisy paths...")
        self.noisePaths = simulate_noisypaths(pgw.loadFromDict(self._pgw_dict), self.dSS, npaths, **noisedict)

    def initial_run(self):
        self.paths = simulate_path(self._pgw, self.dSS, self.mrt)
        self.endgoal = self._pgw.goalCond.getWinningGoal()
        self.endtime = self._pgw.time
        self.sensorHits = {}
        self.collisions = []
        for sh in self._pgw.sensorHits:
            if sh[0] == "FOCUS":
                self.sensorHits[sh[1]] = sh[2]
        self._run = True

    # Function that calculates the amount of variance in the noisy paths
    # Returns a list of the root mean squared error of paths over time
    def calcPathVariability(self):
        rmses = self.calcPathVarDTW(self.noisePaths)
        self.noiseRMSE = rmses

    @staticmethod
    def calcPathVarByPath(paths, objname="FOCUS"):
        nPaths = len(paths)
        nObs = len(paths[0]['path'][objname])
        rmses = []
        for i in range(nObs):
            xtot = 0
            ytot = 0
            npos = []
            for j in range(nPaths):
                x,y = paths[j]['path'][objname][i][:2]
                xtot += x
                ytot += y
                npos.append([x,y])
            apos = [xtot / nPaths, ytot / nPaths]
            totdev = 0
            for x,y in npos:
                dx = x - apos[0]
                dy = y - apos[1]
                totdev += (dx*dx + dy*dy)
            rmses.append(np.sqrt(totdev / nPaths))
        return rmses

    @staticmethod
    def calcPathVarDTW(paths, objname="FOCUS"):
        # Average the paths over time as the reference
        nPaths = len(paths)
        nObs = max([len(p['path'][objname]) for p in paths])
        avgPath = []
        for i in range(nObs):
            xtot = 0
            ytot = 0
            for j in range(nPaths):
                if i < len(paths[j]['path'][objname]):
                    x,y = paths[j]['path'][objname][i][:2]
                else:
                    x,y = paths[j]['path'][objname][-1][:2]
                xtot += x
                ytot += y
            avgPath.append([xtot / nPaths, ytot / nPaths])
        # Now do dynamic time warping for each of the simulation paths
        totDTWdist = 0
        for p in paths:
            cpath = [cp[:2] for cp in p['path'][objname]]
            d = dtw(cpath, avgPath, open_end=True)
            totDTWdist += d.normalizedDistance
        return totDTWdist / nPaths
