import json
import os
import glob
from multiprocess import Process, Queue
import subprocess

from create_plinko import *
from view_stimuli import *

MAKECFG = os.path.join('worldconfigs', 'plinko_maker.json')
CHECKCFG = os.path.join('worldconfigs', 'plinko_checker.json')
OUTDIR = "plinko/bin_filler_candidates"

NTRIES = 100

with open('default_sim_noise.json', 'r') as dsnfl:
    defaultSimNoise = json.load(dsnfl)

def check(worldinfo, checker, silent=True):
    goutnorm = worldinfo['outcome']['other']['event_outcomes']['goals']
    mingpct = min(goutnorm.values())
    maxgpct = max(goutnorm.values())
    if maxgpct > checker["max_largest_goal_outcome"]:
        if not silent:
            print("Not enough variance in goal outcomes")
        return False
    if maxgpct < checker["min_largest_goal_outcome"]:
        if not silent:
            print("Too much variance in goal outcomes")
        return False

    houtnorm = worldinfo['outcome']['other']['event_outcomes']['holes']
    minhpct = min(houtnorm.values())
    maxhpct = max(houtnorm.values())
    if maxhpct > checker["max_largest_hole_outcome"]:
        if not silent:
            print("Not enough variance in hole outcomes")
        return False
    if maxhpct < checker["min_largest_hole_outcome"]:
        if not silent:
            print("Too much variance in hole outcomes")
        return False

    for hole, pvars in worldinfo['outcome']['other']['path_variances'].items():
        top = pvars['top']
        btm = pvars['bottom']

        if (checker['max_dyn_top'] > -1) and (top > checker['max_dyn_top']):
            if not silent:
                print("Too much variance in the top:", hole, top)
            return False
        if (checker['max_dyn_bottom'] > -1) and (btm > checker['max_dyn_bottom']):
            if not silent:
                print("Too much variance in the bottom:", hole, btm)
            return False
        if top < checker['min_dyn_top']:
            if not silent:
                print("Too little variance in the top:", hole, top)
            return False
        if btm < checker['min_dyn_bottom']:
            if not silent:
                print("Too little variance in the bottom:", hole, btm)
            return False

    for hole, max_contingent in \
     worldinfo['outcome']['other']['contingent_goals_max_prob'].items():
        if max_contingent > checker['max_largest_contingent_goal']:
            if not silent:
                print("Too concentrated in contingent goals:", hole, max_contingent)
            return False
        if max_contingent < checker['min_largest_contingent_goal']:
            if not silent:
                print("Too little concentration in contingent goals:", hole, max_contingent)
            return False

    for hole, transit in worldinfo['outcome']['other']['focus_prop_transition'].items():
        xstd = transit['xpos_std']
        velstd = transit['vel_std']
        angstd = transit['ang_std']
        if xstd > checker['max_transition_x']:
            if not silent:
                print("Too much std in x on transition:", hole, xstd)
            return False
        if velstd > checker['max_transition_vel']:
            if not silent:
                print("Too much std in velocity on transition:", hole, velstd)
            return False
        if angstd > checker['max_transition_angle']:
            if not silent:
                print("Too much std in velocity angle on transition:",
                      hole, angstd)
            return False
        if (xstd < checker['min_transition_x'] and
            velstd < checker['min_transition_vel'] and
            angstd < checker['min_transition_angle']):
            if not silent:
                print("Too little variability in transition",
                      hole, xstd, velstd, angstd)
            return False

    mconting = max(worldinfo['outcome']['other']['min_contingent_goals'].values())
    if mconting < checker['min_goal_overlap']:
        if not silent:
            print("Too little goal overlap:", mconting)
        return False
    if mconting > checker['max_goal_overlap']:
        if not silent:
            print("Too much goal overlap:", mconting)
        return False


    return True

def generate_parallel(checker, stimbases, n_tries=NTRIES):
    def doMakeProcess(q, nalready=0, nmax=n_tries):
        while nalready < nmax:
            plcr = PlinkoCreator(MAKECFG)
            plcr.run(noisedict = defaultSimNoise)
            winfo = plcr.checkAndReturn()
            if winfo is not None:
                nalready += 1
                print("Making number", nalready)
                #print(winfo['outcome']['other'])
                for k, chk in checker.items():
                    if check(winfo, chk, True):
                        bnm = stimbases[k]
                        nexist = len(glob.glob(bnm + "*.json"))
                        if nexist < 10000: # Don't need too many...
                            onm = (bnm + "{:04d}.json").format(nexist)
                            print("----Making", onm)
                            with open(onm, 'w') as ofl:
                                json.dump(winfo, ofl)
                        else:
                            print("----Overloaded on:", onm)
                q.put(nalready)

    ntot = 0
    while ntot < n_tries:
        q = Queue()
        p = Process(target=doMakeProcess, args=(q, ntot))
        p.start()
        p.join()

        if p.exitcode != 0:
            print("Segfault: restarting process")
            # Clean up core dumps
            for coref in glob.glob("core.*"):
                subprocess.run(["rm", coref])
        while not q.empty():
            ntot = q.get()
        print("----NTot:", ntot)

def generate_one(checker, stimbases, prefix=True):
    while True:
        plcr = PlinkoCreator(MAKECFG)
        plcr.run(noisedict = defaultSimNoise)
        winfo = plcr.checkAndReturn(passFailures=False)
        if winfo is not None:
            for k, chk in checker.items():
                print(k)
                if check(winfo, chk, False):
                # if True:
                    bnm = stimbases[k]
                    nexist = len(glob.glob(bnm + "*.json"))
                    if nexist < 10000: # Don't need too many...
                        if prefix:
                            onm = (bnm + "{:04d}.json").format(nexist)
                        else:
                            onm = f"{OUTDIR}/{nexist:04d}.json"
                        print("----Saving", onm)
                        with open(onm, 'w') as ofl:
                            json.dump(winfo, ofl)
                        return
                    else:
                        print("----Overloaded on:", onm)
                else:
                    print("checker failed on ", chk)

def generate_without_check(n_tries=NTRIES):
    def doMakeProcess(q, nalready=0, nmax=n_tries):
        while nalready < nmax:
            plcr = PlinkoCreator(MAKECFG)
            plcr.run(noisedict = defaultSimNoise)
            winfo = plcr.checkAndReturn(passFailures=True)
            if winfo is not None:
                nalready += 1
                print("Making number", nalready)
                nexist = len(glob.glob(OUTDIR + "/*.json"))
                onm = f"{OUTDIR}/{nexist:04d}.json"
                print("----Making", onm)
                with open(onm, 'w') as ofl:
                    json.dump(winfo, ofl)
                q.put(nalready)

    ntot = 0
    while ntot < n_tries:
        q = Queue()
        p = Process(target=doMakeProcess, args=(q, ntot))
        p.start()
        p.join()

        if p.exitcode != 0:
            print("Segfault: restarting process")
            # Clean up core dumps
            for coref in glob.glob("core.*"):
                subprocess.run(["rm", coref])
        while not q.empty():
            ntot = q.get()
        print("----NTot:", ntot)

if __name__ == '__main__':
    with open(CHECKCFG, 'r') as cfl:
        checker = json.load(cfl)
    vgc_checker = {"vgc_control": checker.pop("vgc")}

    nmade = 0

    stimbases = {}
    for k in checker.keys():
        stimbases[k] = os.path.join(OUTDIR, k + "_plinko_")


    vgc_stimbases = {"vgc_control": os.path.join(OUTDIR, k)}

    # p, w = generate_without_check()
    # generate_one(checker, stimbases, prefix=False)
    generate_parallel(checker, stimbases)
    # generate_parallel(vgc_checker, vgc_stimbases)
    # generate_one(vgc_checker, vgc_stimbases)
    # generate_without_check()
