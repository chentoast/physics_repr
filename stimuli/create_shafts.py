from creator import EventWorldCreator, defaultSimNoise
import pyGameWorld as pgw
import random
import os
import numpy as np
import json

class ShaftsCreator(EventWorldCreator):

    def loadConfig(self, cfg):
        # Set up the world
        w = pgw.PGWorld(cfg["world_size"], cfg["gravity"])
        worldx = cfg['world_size'][0]

        # Place the ball
        ballpos = random.randint(cfg['ball_info']['pos_range'][0],
                                 cfg['ball_info']['pos_range'][1])
        ballrad = random.randint(cfg['ball_info']['rad_range'][0],
                                 cfg['ball_info']['rad_range'][1])
        w.addBall("FOCUS", [ballpos, cfg['ball_info']['y_pos']], ballrad, 'red', 1)

        # Set up the middle goals
        goal_names = []
        ngoal = cfg["goal_info"]["middle"]["number"]
        ghght = cfg['goal_info']["middle"]['height']
        gwidth = cfg['goal_info']["middle"]['gwidth']
        goalstart = cfg['world_size'][0] / 2 - ngoal / 2 * gwidth
        for i in range(ngoal):
            xmin = goalstart + i * gwidth
            xmax = goalstart + (i+1) * gwidth
            w.addContainer("goalmiddle_" + str(i),
                           [[xmin, ghght], [xmin, 0], [xmax, 0], [xmax, ghght]],
                           10, "green", "black", 0)
            goal_names.append("goalmiddle_" + str(i))

        
        ngoal = cfg["goal_info"]["left"]["number"]
        ghght = cfg['goal_info']["left"]['height']
        gwidth = cfg['goal_info']["left"]['gwidth']
        goalstart = 0
        for i in range(ngoal):
            xmin = goalstart + i * gwidth
            xmax = goalstart + (i+1) * gwidth
            w.addContainer("goalleft_" + str(i),
                           [[xmin, ghght], [xmin, 0], [xmax, 0], [xmax, ghght]],
                           10, "green", "black", 0)
            goal_names.append("goalleft_" + str(i))

        ngoal = cfg["goal_info"]["right"]["number"]
        ghght = cfg['goal_info']["right"]['height']
        gwidth = cfg['goal_info']["right"]['gwidth']
        goalstart = cfg['world_size'][0] - gwidth*ngoal
        for i in range(ngoal):
            xmin = goalstart + i * gwidth
            xmax = goalstart + (i+1) * gwidth
            w.addContainer("goalright_" + str(i),
                           [[xmin, ghght], [xmin, 0], [xmax, 0], [xmax, ghght]],
                           10, "green", "black", 0)
            goal_names.append("goalright_" + str(i))

        # Set up the middle section shafts
        nshafts_per_side = cfg['shaft_info']['number']
        secsize = cfg["world_size"][0] / 3 / nshafts_per_side

        shafts_sections = [[i*secsize, (i+1)*secsize] for i in range(nshafts_per_side)]
        divymin = random.randint(cfg['shaft_info']['ypos_range'][0],
                              cfg['shaft_info']['ypos_range'][1])
        shafts = []
        lowestL = cfg['world_size'][1]
        lowestR = cfg['world_size'][1]

        ## Create left shafts
        for ss in shafts_sections:
            shaftwidth = random.randint(cfg['shaft_info']['width_range'][0],
                                    cfg['shaft_info']['width_range'][1])
            shaftlength = random.randint(cfg['shaft_info']['length_range'][0], 
                                    cfg['shaft_info']['length_range'][1])
            if divymin-shaftlength < lowestL:
                lowestL = divymin - shaftlength
            xmin = random.randint(ss[0] + 5, ss[1] - shaftwidth - 5)
            shafts.append([[xmin, xmin + shaftwidth],[divymin, divymin-shaftlength]])

        ## Create right shafts
        for ss in shafts_sections:
            shaftwidth = random.randint(cfg['shaft_info']['width_range'][0],
                                    cfg['shaft_info']['width_range'][1])
            shaftlength = random.randint(cfg['shaft_info']['length_range'][0], 
                                    cfg['shaft_info']['length_range'][1])
            
            if divymin-shaftlength < lowestR:
                lowestR = divymin - shaftlength
            xmin = random.randint(ss[0] + 5 + 2*cfg['world_size'][0] / 3, ss[1] - shaftwidth - 5 + 2*cfg['world_size'][0] / 3)
            shafts.append([[xmin, xmin + shaftwidth],[divymin, divymin-shaftlength]])

        # Build the walls for each shaft
        for i, shaft in enumerate(shafts):
            w.addSegment('wallL_'+str(i), [shaft[0][0], shaft[1][1]], [shaft[0][0], shaft[1][0]], 10, 'black', 0)
            w.addSegment('wallR_'+str(i), [shaft[0][1], shaft[1][1]], [shaft[0][1], shaft[1][0]], 10, 'black', 0)

        # Build the protusions in each shaft
        for i, shaft in enumerate(shafts):
            shaftwidth = shaft[0][1] - shaft[0][0]
            npro = random.randint(cfg['shaft_info']['n_pro'][0], cfg['shaft_info']['n_pro'][1])
            for j in range(npro):
                proH = random.randint(cfg['shaft_info']['pro_height_range'][0], 
                                cfg['shaft_info']['pro_height_range'][1])
                proW = random.randint(int(shaftwidth / 5), int(shaftwidth / 3))
                pointH = random.randint(0, proH)
                onLeft = random.random() < .5
                start = random.randint(shaft[1][1], shaft[1][0]-proH)

                if onLeft:
                    verts = [[shaft[0][1], start], [shaft[0][1], start + proH], [shaft[0][1]+proW, start + pointH]]
                else:
                    verts = [[shaft[0][1]+shaftwidth, start], [shaft[0][1]+shaftwidth-proW, start + pointH], [shaft[0][1]+shaftwidth, start + proH]]

                w.addPoly('protrusion_'+str(i)+'_'+str(j), verts, 'black', 0)

        # Build the dividers around the shafts
        for i, shaft in enumerate(shafts[:-1]):
            pointY = random.randint(divymin, divymin+cfg['div_info']['max_div_height'])
            pointX = random.randint(shafts[i][0][1], shafts[i+1][0][0])
            verts = [[shafts[i][0][1],shafts[i][1][1]],[shafts[i][0][1], shafts[i][1][0]], [pointX, pointY], [shafts[i+1][0][0], shafts[i+1][1][0]], [shafts[i+1][0][0], shafts[i+1][1][1]]]
            w.addPoly('div'+str(i), verts, 'black', 0)

        # Build the left/right dividers
        pointY = random.randint(divymin, divymin+cfg['div_info']['max_div_height'])
        verts = [[0, shafts[0][1][1]],[0, pointY],[shafts[0][0][0], divymin],[shafts[0][0][0], shafts[0][1][1]]]
        w.addPoly('divL', verts, 'black', 0)

        pointY = random.randint(divymin, divymin+cfg['div_info']['max_div_height'])
        verts = [[shafts[-1][0][1], shafts[-1][1][1]],[shafts[-1][0][1], divymin], [cfg['world_size'][0], pointY], [cfg['world_size'][0], shafts[-1][1][1]]]
        w.addPoly('divR', verts, 'black', 0)

        #Build ball platforms, balls, slopes

        # Add left flat platform
        platL = cfg["goal_info"]["left"]["number"] * cfg["goal_info"]["left"]["gwidth"]
        platR = cfg['world_size'][0] / 2 - cfg["goal_info"]["middle"]["number"] / 2 * cfg["goal_info"]["left"]["gwidth"]
        platH = random.randint(cfg['plat_info']['plat_h'][0], min(cfg['plat_info']['plat_h'][1], lowestL - 30))

        verts = [[platL + 10, 0], [platL + 10, platH], [platR - 10, platH],[platR-10, 0]]
        w.addPoly('ballLPlatform', verts, 'black', 0)

        # Left ball
        ballR = random.randint(cfg['shaft_ball_info']['ball_r'][0], cfg['shaft_ball_info']['ball_r'][1])
        ballY = platH + ballR
        ballX = random.randint(platL, platR)
        w.addBall('ballL', [ballX, ballY], ballR, 'red', 1)
        

        # Add right flat platform
        platR = cfg['world_size'][0] - cfg["goal_info"]["right"]["number"] * cfg["goal_info"]["right"]["gwidth"]
        platL = cfg['world_size'][0] / 2 + cfg["goal_info"]["middle"]["number"] / 2 * cfg["goal_info"]["left"]["gwidth"]
        platH = random.randint(cfg['plat_info']['plat_h'][0], min(cfg['plat_info']['plat_h'][1], lowestR - 30))

        verts = [[platL + 10, 0], [platL + 10, platH], [platR - 10, platH],[platR-10, 0]]
        w.addPoly('ballRPlatform', verts, 'black', 0)

        # Right ball
        ballR = random.randint(cfg['shaft_ball_info']['ball_r'][0], cfg['shaft_ball_info']['ball_r'][1])
        ballY = platH + ballR
        ballX = random.randint(platL, platR)
        w.addBall('ballR', [ballX, ballY], ballR, 'red', 1)
        

        # Add sensors for each of the shafts
        for i, s in enumerate(shafts):
            w.addSensor('shaft_' + str(i),
                        [s[0][0], divymin-10, s[0][1], divymin])

        w.attachSpecificInGoalSet('FOCUS', goal_names, 2.)

        self._pgw = w
        self._pgw_dict = w.toDict()

    # Checks that:
    #  1) There is not too much or too little dynamic varaince on the top/bottom
    #  2) The distribution of intermediate outcomes is not too great or too little
    #  3) The distribution of end goals is not too great or too litte
    def checkConsistency(self):
        return True
        cfg = self._constraint_info

        if len(self.sensorHits.values()) == 0:
            print("Ball never touches a sensor")
            return False
        elif len(self.sensorHits.values()) > 1:
            print("Ball somehow hits multiple sensors")
            return False
        else:
            for t in self.sensorHits.values():
                splittime = t

        # Filter out noisy paths that don't terminate
        usepaths = [p for p in self.noisePaths \
                    if p['goal'] != "NONE" and len(p['sensors']) == 1]
        pct_unused = (len(self.noisePaths) - len(usepaths)) / len(self.noisePaths)
        if pct_unused > cfg['max_no_outcome']:
            print("Too many simulation paths got stuck:", pct_unused)
            return False

        # Get the variance of goal outcomes
        goutcomes = {}
        for p in usepaths:
            g = p['goal']
            if g in goutcomes:
                goutcomes[g] += 1
            else:
                goutcomes[g] = 1
        mingpct = min(goutcomes.values()) / sum(goutcomes.values())
        if (mingpct < cfg["min_smallest_goal_outcome"]) or (mingpct == 1):
            print("Not enough variance in goal outcomes")
            return False
        if mingpct > cfg["max_smallest_goal_outcome"]:
            print("Too much variance in goal outcomes")
            return False

        # Get the variance of hole outcomes
        houtcomes = {}
        for p in usepaths:
            h = p['sensors'][0][0]
            if h in houtcomes:
                houtcomes[h] += 1
            else:
                houtcomes[h] = 1
        minhpct = min(houtcomes.values()) / sum(houtcomes.values())
        if (minhpct < cfg["min_smallest_hole_outcome"]) or (minhpct == 1):
            print("Not enough variance in hole outcomes")
            return False
        if minhpct > cfg["max_smallest_hole_outcome"]:
            print("Too much variance in hole outcomes")
            return False

        # Split the paths by which hole they go through
        splitidx_display = int((splittime / self.dSS) + .0000001)
        splitidx_sim = int(np.floor(splitidx_display / self._ssp))
        splitpaths = {}
        for p in usepaths:

            hole = p['sensors'][0][0]
            splittime = p['sensors'][0][1]

            splitidx_sim = int((splittime / self.sSS) + .0000001)
            toppath = {'path': {'FOCUS': p['path']['FOCUS'][:splitidx_sim]}}
            bottompath = {'path': {'FOCUS': p['path']['FOCUS'][splitidx_sim:]}}

            if hole in splitpaths.keys():
                splitpaths[hole]['top'].append(toppath)
                splitpaths[hole]['bottom'].append(bottompath)
            else:
                splitpaths[hole] = {}
                splitpaths[hole]['top'] = [toppath]
                splitpaths[hole]['bottom'] = [bottompath]

        self.outcomeMisc['path_variances'] = {}
        for hnames, houtcomes in splitpaths.items():
            toprmses = self.calcPathVarDTW(houtcomes['top'])
            btmrmses = self.calcPathVarDTW(houtcomes['bottom'])
            self.outcomeMisc['path_variances'][hnames] = {
                'top': np.mean(toprmses),
                'bottom': np.mean(btmrmses)
            }
            if (cfg['max_dyn_top'] > -1) and (np.mean(toprmses) > cfg['max_dyn_top']):
                print("Too much variance in the top:", hnames, np.mean(toprmses))
                return False
            if (cfg['max_dyn_bottom'] > -1) and (np.mean(btmrmses) > cfg['max_dyn_bottom']):
                print("Too much variance in the bottom:", hnames, np.mean(btmrmses))
                return False
            if np.mean(toprmses) < cfg['min_dyn_top']:
                print("Too little variance in the top:", hnames, np.mean(toprmses))
                return False
            if np.mean(btmrmses) < cfg['min_dyn_bottom']:
                print("Too little variance in the bottom:", hnames, np.mean(btmrmses))
                return False

        return True


if __name__ == '__main__':

     nworldsper = 20
     cfg_files_names = ['hh_hh_shafts']

     for cfg in cfg_files_names:
         nmade = 0
         oname = os.path.join('shafts', cfg + '_{:04d}.json')
         while nmade < nworldsper:
             plcr = ShaftsCreator(os.path.join('worldconfigs', cfg + '.json'))
             winfo = plcr.checkAndReturn(noisedict = defaultSimNoise)
             if winfo is not None:
                 with open(oname.format(nmade), 'w') as ofl:
                     json.dump(winfo, ofl)
                 nmade += 1
