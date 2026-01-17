import os
import json


stimtypes = ["ll_ll", "ll_hl", "ll_lh", "ll_hh",
             "hl_hh_trMat", "lh_hh_trNM", "hl_lh_trMat", "hl_lh_trNM",
             "hl_hl_trMat", "hl_hl_trNM", "hl_ll",
             "lh_hh", "lh_lh", "lh_hl_link", "lh_hl_unlink",
             "lh_ll_link", "lh_ll_unlink",
             "hh_hh", "hh_lh", "hh_hl_link", "hh_hl_unlink",
             "hh_ll_link", "hh_ll_unlink"]


#stimtypes = ["ll_ll", "ll_lh", "ll_hl", "ll_hh",
#             "lh_ll", "lh_lh_trNM", "lh_lh_trMat", "lh_hl_trNM", "lh_hl_trMat",
#             "lh_hh_trNM", "lh_hh_trMat",
#             "hl_hh", "hl_hl", "hl_lh_link", "hl_lh_unlink",
#             "hl_ll_link", "hl_ll_unlink",
#             "hh_hh", "hh_hl", "hh_lh_link", "hh_lh_unlink",
#             "hh_ll_link", "hh_ll_unlink"]

def makeTop(s):
    r = {}
    dyn, ev = s
    if dyn == 'h':
        r['max_dyn_top'] = -1
        r['min_dyn_top'] = 8
    elif dyn == 'l':
        r['max_dyn_top'] = 5
        r['min_dyn_top'] = -1
    else:
        raise IOError('top:' + str(s))
    if ev == 'h':
        r['max_largest_hole_outcome'] = 0.7
        r['min_largest_hole_outcome'] = 0.0
    elif ev == 'l':
        r['max_largest_hole_outcome'] = 1.0
        r['min_largest_hole_outcome'] = 0.95
    else:
        raise IOError('top:' + str(s))
    return r

def makeBottom(s):
    r = {}
    dyn, ev = s
    if dyn == 'h':
        r['max_dyn_bottom'] = -1
        r['min_dyn_bottom'] = 20
    elif dyn == 'l':
        r['max_dyn_bottom'] = 10
        r['min_dyn_bottom'] = -1
    else:
        raise IOError('bottom:' + str(s))
    if ev == 'h':
        r['max_largest_contingent_goal'] = 0.7
        r['min_largest_contingent_goal'] = 0.0
    elif ev == 'l':
        r['max_largest_contingent_goal'] = 1.0
        r['min_largest_contingent_goal'] = 0.95
    else:
        raise IOError('bottom:' + str(s))
    return r

def makeAnnot(s):
    if s == 'trNM':
        return {
            "max_transition_x": 10,
            "max_transition_vel": 10,
            "max_transition_angle": 0.2,
            "min_transition_x": 0,
            "min_transition_vel": 0,
            "min_transition_angle": 0,
            "min_goal_overlap": 0.,
            "max_goal_overlap": 1.
        }
    elif s == 'trMat':
        return {
            "max_transition_x": 9999,
            "max_transition_vel": 9999,
            "max_transition_angle": 9999,
            "min_transition_x": 10,
            "min_transition_vel": 10,
            "min_transition_angle": 0.2,
            "min_goal_overlap": 0.,
            "max_goal_overlap": 1.
        }
    elif s == 'unlink':
        return {
            "max_transition_x": 9999,
            "max_transition_vel": 9999,
            "max_transition_angle": 9999,
            "min_transition_x": 0,
            "min_transition_vel": 0,
            "min_transition_angle": 0,
            "min_goal_overlap": 0.25,
            "max_goal_overlap": 1.
        }
    elif s == 'link':
        return {
            "max_transition_x": 9999,
            "max_transition_vel": 9999,
            "max_transition_angle": 9999,
            "min_transition_x": 0,
            "min_transition_vel": 0,
            "min_transition_angle": 0,
            "min_goal_overlap": 0.,
            "max_goal_overlap": 0.02
        }
    else:
        raise IOError('annot:' + str(s))

def makeDict(tp):
    base = {
        "max_no_outcome": 0.05,
        "max_largest_goal_outcome": 1.0,
        "min_largest_goal_outcome": 0.0
    }
    spl = tp.split('_')
    if len(spl) == 3:
        adict = makeAnnot(spl[2])
    else:
        adict = {
            "max_transition_x": 9999,
            "max_transition_vel": 9999,
            "max_transition_angle": 9999,
            "min_transition_x": 0,
            "min_transition_vel": 0,
            "min_transition_angle": 0,
            "min_goal_overlap": 0.,
            "max_goal_overlap": 1.0
        }
    base.update(makeTop(spl[0]))
    base.update(makeBottom(spl[1]))
    base.update(adict)
    return base

if __name__ == '__main__':

    mdict = dict([(tp, makeDict(tp)) for tp in stimtypes])
    with open(os.path.join("worldconfigs", 'plinko_checker.json'), 'w') as ofl:
        json.dump(mdict, ofl)
