from __future__ import division, print_function
import pymunk as pm
import pygame as pg
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import multivariate_normal as mvnm
from ..world import *
from ..constants import *
from ..object import *
from pygame.constants import QUIT
#from .visualize_likelihoods import *
import pdb
__all__ = ['drawWorld', 'demonstrateWorld', 'demonstrateTPPlacement',
           'visualizePath', 'drawPathSingleImage', 'drawPathSingleImageWithTools', 'drawWorldWithTools', 'visualizeScreen', 'drawPathSingleImageBasic',
           'makeImageArray', 'makeImageArrayNoPath','drawTool', '_draw_line_gradient',
           'drawMultiPathSingleImage', 'drawMultiPathSingleImageBasic',
           'drawGaussianOnTrial', 'drawGaussianScreen']
#, 'visualize_bayesopt_likelihoods']

#COLORS=[(255,0,0,255),(0,255,0,255),(0,0,255,255)]
COLORS=[(255,0,255,255), (225,225,0, 255),(0, 255, 255, 255)]
#COLORS=[(255,0,255,255), (215,185,10, 255),(0, 255, 255, 255)]
WHITE = (255, 255, 255, 255)
#COLORDICT = {'obj1': (255,0,255,255), 'obj2': (255,255,0,255), 'obj3': (0,255,255,255)}
def _lighten_rgb(rgba, amt=.2):
    assert 0 <= amt <= 1, "Lightening must be between 0 and 1"
    r = int(255- ((255-rgba[0]) * (1-amt)))
    g = int(255- ((255-rgba[1]) * (1-amt)))
    b = int(255- ((255-rgba[2]) * (1-amt)))
    if len(rgba) == 3:
        return (r, g, b)
    else:
        return (r, g, b, rgba[3])

def _draw_line_gradient(start, end, steps, rgba, surf):
    diffs = np.array(end) - np.array(start)
    dX = (end[0] - start[0]) / steps
    dY = (end[1] - start[1]) / steps

    points = np.array(start) + np.array([[dX,dY]])*np.array([range(0,steps),]*2).transpose()
    cols = [_lighten_rgb(rgba, amt=0.9*step/steps) for step in range(0, steps)]
    for i, point in enumerate(points[:-1]):
        pg.draw.line(surf, cols[i], point, points[i+1], 3)
    return surf

def _filter_unique(mylist):
    newlist = []
    for ml in mylist:
        if ml not in newlist:
            newlist.append(ml)
    return newlist

def _draw_obj(o, s, makept, lighten_amt=0, color=None, width=None):
    col = color or _lighten_rgb(o.color, lighten_amt)
    # if o.type == 'Poly' or o.type == 'Teleporter':
    if o.type == 'Poly':
        width = width or 0
        vtxs = [makept(v) for v in o.vertices]
        pg.draw.polygon(s, col, vtxs, width=width)
    # elif o.type == 'Sensor':
    #     width = width or 0
    #     vtxs = [makept(v) for v in o.vertices]
    #     pg.draw.polygon(s, col, vtxs, width=width)
        # pos = makept(o.position)
        # rad = int(o.radius)
        # pg.draw.circle(s, col, pos, rad)
    elif o.type == 'Ball' or o.type == 'Teleporter':
        pos = makept(o.position)
        rad = int(o.radius)
        pg.draw.circle(s, col, pos, rad)
        # Draw small segment that adds a window
        if o.isStatic():
            rot = 0
        else:
            rot = o.rotation
        mixcol = [int((3.*oc + 510.)/5.) for oc in o.color]
        mixcol = _lighten_rgb(mixcol, lighten_amt)
        if not o.isStatic():
            for radj in range(5):
                ru = radj*np.pi / 2.5 + rot
                pts = [(.65*rad*np.sin(ru) + pos[0], .65*rad*np.cos(ru) + pos[1]),
                       (.7 * rad * np.sin(ru) + pos[0], .7 * rad * np.cos(ru) + pos[1]),
                       (.7 * rad * np.sin(ru+np.pi/20.) + pos[0], .7 * rad * np.cos(ru+np.pi/20.) + pos[1]),
                       (.65 * rad * np.sin(ru+np.pi/20.) + pos[0], .65 * rad * np.cos(ru+np.pi/20.) + pos[1])]
                pg.draw.polygon(s, mixcol, pts)
    elif o.type == 'Segment':
        pa, pb = [makept(p) for p in o.points]
        pg.draw.line(s, col, pa, pb, o.r, width=2)
    elif o.type == 'Container':
        for poly in o.polys:
            ocol = _lighten_rgb(o.outer_color, lighten_amt)
            vtxs = [makept(p) for p in poly]
            pg.draw.polygon(s, ocol, vtxs)
        garea = [makept(p) for p in o.vertices]
        if o.inner_color is not None:
            acolor = (o.inner_color[0], o.inner_color[1], o.inner_color[2], 128)
            acolor = _lighten_rgb(acolor, lighten_amt)
            pg.draw.polygon(s, acolor, garea)
    elif o.type == 'Compound':
        for poly in o.polys:
            vtxs = [makept(p) for p in poly]
            pg.draw.polygon(s, col, vtxs)
    elif o.type == 'Goal':
        if o.color is not None:
            vtxs = [makept(v) for v in o.vertices]
            pg.draw.polygon(s, col, vtxs)
    else:
        print ("Error: invalid object type for drawing:", o.type)

def _draw_tool(toolverts, makept, size=[90, 90], color=(0,0,0,255)):
    s = pg.Surface(size)
    s.fill(WHITE)
    for poly in toolverts:
        vtxs = [makept(p) for p in poly]
        pg.draw.polygon(s, color, vtxs)
    return s

def view(jdict, step, flags=0, **kw):
    pg.init()
    scr = pg.display.set_mode(jdict['world']['dims'], flags=flags)
    white = (255, 255, 255, 255)

    for s in step(jdict, scr, **kw):
        scr.fill(white)
        scr.blit(s, [0, 0])
        pg.event.pump()
        pg.display.flip()

        yield np.transpose(np.array(pg.surfarray.pixels3d(scr)), axes=(1, 0, 2))

def drawWorld(world, backgroundOnly=False, lightenPlaced=False, obj_colors={}, obj_widths={}, **kw):
    s = pg.Surface(world.dims, pg.SRCALPHA)
    # s = pg.Surface(world.dims)
    s.fill(world.bk_col)

    def makept(p):
        return [int(i) for i in world._invert(p)]

    for b in world.blockers.values():
        drawpts = [makept(p) for p in b.vertices]
        pg.draw.polygon(s, b.color, drawpts)

    for o in world.objects.values():
        color = obj_colors.get(o.name, None)
        width = obj_widths.get(o.name, None)
        if not backgroundOnly or o.isStatic():
            if lightenPlaced and o.name == 'PLACED':
                _draw_obj(o, s, makept, .5, color=color, width=width)
            else:
                _draw_obj(o, s, makept, color=color, width=width)
    if "teleport_exit" in world.sensors:
        _draw_obj(world.sensors["teleport_exit"], s, makept, color=obj_colors.get("teleport_exit", None))
    if "teleport_entry" in world.sensors:
        _draw_obj(world.sensors["teleport_entry"], s, makept, color=obj_colors.get("teleport_entry", None))
    if "FOCUS" in world.objects:
        _draw_obj(world.objects["FOCUS"], s, makept)
    return s

def pathDone(world, path, i):
    if len(path[(list(path.keys())[0])]) == 2:
        nsteps = len(path[list(path.keys())[0]][0])
    else:
        nsteps = len(path[list(path.keys())[0]])

    rad = world.objects["FOCUS"].radius
    if len(path["FOCUS"]) <= i or path["FOCUS"][i][1] - rad < 6.5:
        return True
    return i == nsteps

def pathStep(world, path, i, clk, hz=30., **kw):
    for onm, o in world.objects.items():
        if not o.isStatic():
            if len(path[onm])==2:
                o.setPos(path[onm][0][i])
                o.setRot(path[onm][1][i])
            else:
                o.setPos(path[onm][i][0:2])
                #o.setRot(path[onm][i][2])
    clk.tick(hz)
    return drawWorld(world, **kw)

def drawPaths(world, path_set, pathSize=3, lighten_amt=.5, path_color=None, draw_start=True, draw_end=True, sc=None, **kw):
    if not sc:
        sc = drawWorld(world, **kw)
    # set up the drawing
    def makept(p):
        return [int(i) for i in world._invert(p)]
    # draw the paths in the background
    for path in path_set:
        for onm, o in world.objects.items():
            if not o.isStatic():
                if path_color:
                    col = path_color
                elif o.type == 'Container':
                    col = o.outer_color
                else:
                    col = o.color
                pthcol = _lighten_rgb(col, .7)
                if len(path[onm]) == 2:
                    poss = path[onm][0]
                else:
                    poss = path[onm]
                #for p in poss:
                #    pg.draw.circle(sc, pthcol, makept(p), pathSize)
                pts = _filter_unique([makept(p) for p in poss])
                if len(pts) > 1:
                    pg.draw.lines(sc, pthcol, False, pts, pathSize)
    # Draw the initial tools, lightened
    if not draw_start:
        return sc

    for onm, o in world.objects.items():
        if not o.isStatic():
            _draw_obj(o, sc, makept, lighten_amt=lighten_amt)
    # Draw the end tools
    if not draw_end:
        return sc

    for path in path_set:
        for onm, o in world.objects.items():
            if not o.isStatic():
                if len(path[onm]) == 2:
                    o.setPos(path[onm][0][-1])
                    o.setRot(path[onm][1][-1])
                else:
                    o.setPos(path[onm][-1][:2])
                _draw_obj(o, sc, makept, lighten_amt=.6)
    return sc

def drawTool(tool, color=(0,0,255), toolbox_size=(90, 90)):
    s = pg.Surface(toolbox_size)
    def resc(p):
        return [int(p[0] +toolbox_size[0]/2),
                int(toolbox_size[1]/2 - p[1])]
    s.fill((255,255,255))
    for poly in tool:
        pg.draw.polygon(s, color, [resc(p) for p in poly])

    s_arr = pg.surfarray.array3d(s)
    return s_arr

def _def_inv(p):
    return(p)

def _draw_field(llh_fnc, lg_dim, sm_dim, color_func, clamp_low, clamp_high):
    px_per = lg_dim / sm_dim / 2
    pts_raw = np.linspace(0, lg_dim, sm_dim, False) + px_per
    pts = [int(p) for p in pts_raw]

    s = pg.Surface((sm_dim, sm_dim)).convert_alpha()
    s.fill((0, 0, 0, 0))
    for i, x in enumerate(pts):
        for j, y in enumerate(pts):
            llh = llh_fnc([x,y])
            col = color_func(llh)
            #print(x,y,llh,col)
            s.set_at((i, sm_dim-j), col)
    return s

def drawGaussianScreen(sc, mu, sig, color=(255, 255, 0),
                         clamp_low=-20, clamp_high=0, dim_size=60):
    mu = np.array(mu)
    cov = np.diag(sig)
    cdiff = clamp_high - clamp_low

    def ptcalc(p):
        return mvnm.logpdf(p, mean=mu, cov=cov)

    def llh2col(llh):
        clamped = min(max(llh, clamp_low), clamp_high)
        interp = int((clamped - clamp_low) * (255 / cdiff))
        return (color[0], color[1], color[2], interp)

    maxx, maxy = sc.get_size()
    assert maxx == maxy, "Only works with square screens"
    s_sm = _draw_field(ptcalc, maxx, dim_size, llh2col, clamp_low, clamp_high)
    s = pg.transform.smoothscale(s_sm, (600, 600))
    return s

def drawGaussianOnTrial(worlddict, mu, sig, color=(255,255,0),
                        clamp_low=-20, clamp_high=0, dim_size=60):
    assert len(mu) == 2 and  len(sig) == 2, "Malformed Gaussian parameters"
    world = loadFromDict(worlddict)
    def makept(p):
        return [int(i) for i in world._invert(p)]
    sc = drawWorld(world)
    gs = drawGaussianScreen(sc, mu, sig, color, clamp_low,
                                clamp_high, dim_size)
    sc.blit(gs, (0, 0))
    #for b in world.blockers.values():
    #    drawpts = [makept(p) for p in b.vertices]
    #    pg.draw.polygon(gs, b.color, drawpts)

    #for o in world.objects.values():
    #    _draw_obj(o, gs, makept)

    return sc

def makeImageArray(worlddict, path, sample_ratio=1):
    world = loadFromDict(worlddict)
    #pg.init()
    images = [drawWorld(world)]
    if len(path[(list(path.keys())[0])]) == 2:
        nsteps = len(path[list(path.keys())[0]][0])
    else:
        nsteps = len(path[list(path.keys())[0]])

    for i in range(1,nsteps,sample_ratio):
        for onm, o in world.objects.items():
            if not o.isStatic():
                if len(path[onm])==2:
                    o.setPos(path[onm][0][i])
                    o.setRot(path[onm][1][i])
                else:
                    o.setPos(path[onm][i][0:2])
                    o.setRot(path[onm][i][2])
        images.append(drawWorld(world))
    return images

def makeImageArrayNoPath(worlddict, path_length):
    world = loadFromDict(worlddict)
    #pg.init()
    images = [drawWorld(world)]
    nsteps = path_length
    return images*int(nsteps)

def visualizeScreen(tp):
    #pg.init()
    pg.display.set_mode((10,10))
    s = drawWorldWithTools(tp, backgroundOnly=False)
    i = s.convert_alpha()
    pg.image.save(i, 'test.png')
    pg.quit()

def drawPathSingleImageWithTools(tp, path, pathSize=3, lighten_amt=.5, worlddict=None, with_tools=False):
    # set up the drawing
    if worlddict is None:
        worlddict = tp._worlddict
    world = loadFromDict(worlddict)
    #pg.init()
    #sc = pg.display.set_mode(world.dims)
    if not with_tools:
        sc = drawWorld(world, backgroundOnly=True)#, worlddict=worlddict)
    else:
        sc = drawWorldWithTools(tp, backgroundOnly=True, worlddict=worlddict)
    def makept(p):
        return [int(i) for i in world._invert(p)]
    # draw the paths in the background
    for onm, o in world.objects.items():
        if not o.isStatic():
            if o.type == 'Container':
                col = o.outer_color
            else:
                col = o.color
            pthcol = _lighten_rgb(col, lighten_amt)
            if len(path[onm]) == 2:
                poss = path[onm][0]
            else:
                poss = [path[onm][i][0:2] for i in range(0, len(path[onm]))]
            #for p in poss:
            #    pg.draw.circle(sc, pthcol, makept(p), pathSize)
            pts = _filter_unique([makept(p) for p in poss])

            if len(pts) > 1:
                steps = len(pts)
                cols = [_lighten_rgb(col, amt=0.9*step/steps) for step in range(0, steps)]
                for i,pt in enumerate(pts[:-1]):
                    color = cols[i]
                    pg.draw.line(sc, color, pt, pts[i+1], 3)
                    #_draw_line_gradient(pt, pts[i+1], 5, col, sc)
                #pg.draw.lines(sc, pthcol, False, pts, pathSize)
    # Draw the initial tools, lightened
    for onm, o in world.objects.items():
        if not o.isStatic():
            _draw_obj(o, sc, makept, lighten_amt=lighten_amt)
    # Draw the end tools
    for onm, o in world.objects.items():
        if not o.isStatic():
            if len(path[onm])==2:
                o.setPos(path[onm][0][-1])
                o.setRot(path[onm][1][-1])
            else:
                o.setPos(path[onm][-1][0:2])
            _draw_obj(o, sc, makept)

    #pg.display.flip()

    #pg.quit()
    return sc

def drawTool(tool):

    def maketoolpt(p):
        return [int(p[0] + 45), int(45-p[1])]

    s = _draw_tool(tool, maketoolpt, [90,90])

    return s

def drawWorldWithTools(tp, backgroundOnly=False, worlddict=None):
    if worlddict is not None:
        world = loadFromDict(worlddict)
    else:
        world = loadFromDict(tp._worlddict)
    s = pg.Surface((world.dims[0] + 150, world.dims[1]))
    s.fill(world.bk_col)

    def makept(p):
        return [int(i) for i in world._invert(p)]

    def maketoolpt(p):
        return [int(p[0] + 45), int(45-p[1])]

    for b in world.blockers.values():
        drawpts = [makept(p) for p in b.vertices]
        pg.draw.polygon(s, b.color, drawpts)

    for o in world.objects.values():
        if not backgroundOnly or o.isStatic():
            _draw_obj(o, s, makept)

    for i, t in enumerate(tp._tools.keys()):
        col = COLORS[i]
        newsc = pg.Surface([96, 96])
        newsc.fill(col)
        toolsc = _draw_tool(tp._tools[t], maketoolpt, [90,90])
        newsc.blit(toolsc, [3, 3])
        s.blit(newsc, (630, 137 + 110*i))
    return s

def demonstrateWorld(world, hz = 30.):
    pg.init()
    sc = pg.display.set_mode(world.dims)
    clk = pg.time.Clock()
    sc.blit(drawWorld(world), (0,0))
    pg.display.flip()
    running = True
    tps = 1./hz
    clk.tick(hz)
    dispFinish = True
    while running:
        world.step(tps)
        sc.blit(drawWorld(world), (0, 0))
        pg.display.flip()
        clk.tick(hz)
        for e in pg.event.get():
            if e.type == QUIT:
                running = False
        if dispFinish and world.checkEnd():
            print("Goal accomplished")
            dispFinish = False
    pg.quit()

def demonstrateTPPlacement(toolpicker, toolname, position, maxtime=20.,
                           noise_dict=None, hz=30.):
    tps = 1./hz
    toolpicker.bts = tps
    if noise_dict:
        pth, ocm, etime, wd = toolpicker.runFullNoisyPath(toolname, position, maxtime, returnDict=True, **noise_dict)
    else:
        pth, ocm, etime, wd = toolpicker.observeFullPlacementPath(toolname, position, maxtime, returnDict=True)
    world = loadFromDict(wd)
    print (ocm)
    pg.init()
    sc = pg.display.set_mode(world.dims)
    clk = pg.time.Clock()
    sc.blit(drawWorld(world), (0, 0))
    pg.display.flip()
    clk.tick(hz)
    t = 0
    i = 0
    dispFinish = True
    while t < etime:
        for onm, o in world.objects.items():
            if not o.isStatic():
                o.setPos(pth[onm][0][i])
                o.setRot(pth[onm][1][i])
        i += 1
        t += tps
        sc.blit(drawWorld(world), (0,0))
        pg.display.flip()
        for e in pg.event.get():
            if e.type == QUIT:
                pg.quit()
                return
    pg.quit()

def _draw_obj_mpl(o, makept, lighten_amt=0, color=None, width=None, **kw):
    col = color or o.color
    col = _lighten_rgb(col, lighten_amt)
    col = [c/255. for c in col]
    if o.type == 'Poly':
        width = width or 0
        vtxs = [makept(v) for v in o.vertices]
        plt.gca().add_patch(plt.Polygon(vtxs, facecolor=col, lw=width, gid=o.name, **kw))
    elif o.type == 'Ball' or o.type == 'Teleporter':
        pos = makept(o.position)
        rad = int(o.radius)
        plt.gca().add_patch(plt.Circle(pos, radius=rad, facecolor=col, gid=o.name))
        # pg.draw.circle(col, pos, rad)
        # Draw small segment that adds a window
        if o.isStatic():
            rot = 0
        else:
            rot = o.rotation
        # mixcol = [int((3.*oc + 510.)/5.) for oc in o.color]
        # mixcol = _lighten_rgb(mixcol, lighten_amt)
        # mixcol = [mc/255. for mc in mixcol]
        # if not o.isStatic():
        #     for radj in range(5):
        #         ru = radj*np.pi / 2.5 + rot
        #         pts = [(.65*rad*np.sin(ru) + pos[0], .65*rad*np.cos(ru) + pos[1]),
        #                (.7 * rad * np.sin(ru) + pos[0], .7 * rad * np.cos(ru) + pos[1]),
        #                (.7 * rad * np.sin(ru+np.pi/20.) + pos[0], .7 * rad * np.cos(ru+np.pi/20.) + pos[1]),
        #                (.65 * rad * np.sin(ru+np.pi/20.) + pos[0], .65 * rad * np.cos(ru+np.pi/20.) + pos[1])]
        #         # pg.draw.polygon(mixcol, pts)
        #         plt.gca().add_patch(plt.Polygon(pts, color=mixcol))
    elif o.type == 'Segment':
        pa, pb = [makept(p) for p in o.points]
        if width is None:
            width = o.r
        plt.plot(pa, pb, color=col, lw=width)
    elif o.type == 'Container':
        # TODO: currently don't draw border. but should fix this
        for poly in o.polys:
            ocol = _lighten_rgb(o.outer_color, lighten_amt)
            ocol = [oc/255. for oc in ocol]
            vtxs = [makept(p) for p in poly]
            plt.gca().add_patch(plt.Polygon(vtxs, color=ocol))
        garea = [makept(p) for p in o.vertices]
        if o.inner_color is not None:
            acolor = (o.inner_color[0], o.inner_color[1], o.inner_color[2], 128) if color is None else color
            acolor = _lighten_rgb(acolor, lighten_amt)
            acolor = [ac/255. for ac in acolor]
            plt.gca().add_patch(plt.Polygon(garea, color=acolor))
        # for poly in o.polys:
        #     ocol = _lighten_rgb(o.outer_color, lighten_amt)
        #     vtxs = [makept(p) for p in poly]
        #     pg.draw.polygon(s, ocol, vtxs)
        # garea = [makept(p) for p in o.vertices]
        # if o.inner_color is not None:
        #     acolor = (o.inner_color[0], o.inner_color[1], o.inner_color[2], 128)
        #     acolor = _lighten_rgb(acolor, lighten_amt)
        #     pg.draw.polygon(s, acolor, garea)
    elif o.type == 'Compound':
        for poly in o.polys:
            vtxs = [makept(p) for p in poly]
            plt.gca().add_patch(plt.Polygon(vtxs, color=col))
    elif o.type == 'Goal':
        if o.color is not None:
            vtxs = [makept(v) for v in o.vertices]
            plt.gca().add_patch(plt.Polygon(vtxs, color=col))
    else:
        print ("Error: invalid object type for drawing:", o.type)

def _draw_world_mpl(world, backgroundOnly=False, lightenPlaced=False, obj_colors={}, obj_widths={}, draw_start=True, other_object_props=None):
    def makept(p):
        _p = [min(max(p[0], 0), world.dims[0]), min(max(p[1], 0), world.dims[1])]
        return _p

    # for b in world.blockers.values():
    #     drawpts = [makept(p) for p in b.vertices]
    #     pg.draw.polygon(s, b.color, drawpts)

    for o in world.objects.values():
        if o.name == "FOCUS":
            continue
        color = obj_colors.get(o.name, None)
        width = obj_widths.get(o.name, None)
        if other_object_props:
            props = other_object_props.get(o.name, {})
        else:
            props = {}
        if not backgroundOnly or o.isStatic():
            if lightenPlaced and o.name == 'PLACED':
                _draw_obj_mpl(o, makept, .5, color=color, width=width, **props)
            else:
                _draw_obj_mpl(o, makept, color=color, width=width, **props)
    if "teleport_exit" in world.sensors:
        _draw_obj_mpl(world.sensors["teleport_exit"], makept, color=obj_colors.get("teleport_exit", None))
    if "teleport_entry" in world.sensors:
        _draw_obj_mpl(world.sensors["teleport_entry"], makept, color=obj_colors.get("teleport_entry", None))
    if "FOCUS" in world.objects and draw_start:
        color = obj_colors.get("FOCUS", None)
        _draw_obj_mpl(world.objects["FOCUS"], makept, color=color)

def _draw_paths_mpl(world, path_set, pathSize=3, lighten_amt=.5, path_color=None, draw_start=True, draw_end=True, **kw):
    world = world.copy()
    def makept(p):
        return p

    for path in path_set:
        for onm, o in world.objects.items():
            if o.isStatic():
                continue
            if path_color:
                col = path_color
            elif o.type == 'Container':
                col = o.outer_color
            else:
                col = o.color
            pthcol = _lighten_rgb(col, .7)
            pthcol = [p/255. for p in pthcol]
            # if len(path[onm]) == 2:
            #     poss = path[onm][0]
            # else:
            poss = path[onm]
            #for p in poss:
            #    pg.draw.circle(sc, pthcol, makept(p), pathSize)
            pts = _filter_unique([makept(p) for p in poss])
            x, y, *_ = zip(*pts)
            alpha = kw.get('alpha', 1.0)
            if len(pts) > 1:
                plt.plot(x, y, color=pthcol, lw=pathSize, alpha=alpha, **kw)
    # Draw the initial tools, lightened
    if draw_start:
        for onm, o in world.objects.items():
            if not o.isStatic():
                _draw_obj_mpl(o, makept, lighten_amt=lighten_amt, color=path_color)
    # Draw the end tools
    if draw_end:
        for path in path_set:
            for onm, o in world.objects.items():
                if not o.isStatic():
                    # if len(path[onm]) == 2:
                    #     o.setPos(path[onm][0][-1])
                    #     o.setRot(path[onm][1][-1])
                    # else:
                    o.setPos(path[onm][-1][:2])
                    _draw_obj_mpl(o, makept, lighten_amt=.6, color=path_color)