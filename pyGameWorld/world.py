from __future__ import division  # Just in case
import pymunk as pm
import numpy as np
from .constants import *
from .object import *
from .conditions import *
from .helpers import word2Color, distanceToObject
from copy import deepcopy
import pdb

__all__ = ["PGWorld", "loadFromDict"]


########################################
# Loading
########################################


def loadFromDict(d):
    d = deepcopy(d)
    def_elast = float(d["defaults"]["elasticity"])
    def_fric = float(d["defaults"]["friction"])

    pgw = PGWorld(
        d["dims"],
        d["gravity"],
        [False, False, False, False],
        d["bts"],
        float(d["defaults"]["density"]),
        def_elast,
        def_fric,
        word2Color(d["defaults"]["bk_color"]),
        word2Color(d["defaults"]["color"]),
    )

    for nm, o in d["objects"].items():
        elasticity = float(o.get("elasticity", def_elast))
        friction = float(o.get("friction", def_fric))
        density = float(o.get("density", d["defaults"]["density"]))

        if o["type"] == "Poly":
            pgw.addPoly(
                nm,
                o["vertices"],
                word2Color(o["color"]),
                density,
                elasticity,
                friction,
            )
        elif o["type"] == "Ball":
            pgw.addBall(
                nm,
                o["position"],
                o["radius"],
                word2Color(o["color"]),
                density,
                elasticity,
                friction,
            )
        elif o["type"] == "Segment":
            pgw.addSegment(
                nm,
                o["p1"],
                o["p2"],
                o["width"],
                word2Color(o["color"]),
                density,
                elasticity,
                friction,
            )
        elif o["type"] == "Container":
            if "innerColor" not in o:
                if "color" in o:
                    ic = word2Color(o["color"])
                else:
                    ic = None
            else:
                ic = word2Color(o["innerColor"])
            if "outerColor" not in o:
                oc = DEFAULT_COLOR
            else:
                oc = word2Color(o["outerColor"])
            pgw.addContainer(
                nm, o["points"], o["width"], ic, oc, density, elasticity, friction
            )
        elif o["type"] == "Goal":
            pgw.addPolyGoal(nm, o["vertices"], word2Color(o["color"]))
        # elif o["type"] == "Teleporter":
        #     pgw.addTeleporter(nm, o["position"], o["radius"], o["exit_coord"], word2Color(o["color"]))
        elif o["type"] == "Compound":
            pgw.addCompound(
                nm,
                o["polys"],
                word2Color(o["color"]),
                density,
                elasticity,
                friction,
            )
        else:
            raise Exception("Invalid object type given")

    for nm, o in d["sensors"].items():
        if o["type"] == "Teleporter":
            pgw.addTeleporter(nm, o["position"], o["radius"], o["exit_coord"], o["is_entry"], word2Color(o["color"]))
            continue
        color = o.get("color", "none")
        pgw.addPolySensor(nm, o["vertices"], color)

    for nm, b in d["blocks"].items():
        pgw.addPolyBlock(nm, b["vertices"], word2Color(b["color"]))

    if d["gcond"] is not None:
        g = d["gcond"]
        if g["type"] == "AnyInGoal":
            excl = g.get("exclusions", [])
            pgw.attachAnyInGoal(g["goal"], float(g["duration"]), excl)
        elif g["type"] == "SpecificInGoal":
            pgw.attachSpecificInGoal(g["goal"], g["obj"], float(g["duration"]))
        elif g["type"] == "ManyInGoal":
            pgw.attachManyInGoal(g["goal"], g["objlist"], float(g["duration"]))
        elif g["type"] == "AnyTouch":
            pgw.attachAnyTouch(g["goal"], float(g["duration"]))
        elif g["type"] == "SpecificTouch":
            pgw.attachSpecificTouch(g["goal"], g["obj"], float(g["duration"]))
        elif g["type"] == "SpecificInGoalSet":
            pgw.attachSpecificInGoalSet(g["obj"], g["goalset"], g["duration"])
        elif g["type"] == "AnyInGoalSet":
            pgw.attachAnyInGoalSet(g["goalset"], g["duration"])
        elif g["type"] == "ManyInGoalSet":
            pgw.attachManyInGoalSet(g["objset"], g["goalset"], g["duration"])
        else:
            raise Exception("In valid goal condition type given")

    return pgw


def _emptyCollisionHandler(arb, space):
    return True


def _emptyObjectHandler(o1, o2):
    return


def resolveArbiter(arb):
    shs = arb.shapes
    o1, o2 = shs
    return o1.name, o2.name


def pullCollisionInformation(arb):
    norm = list(arb.contact_point_set.normal)
    setpoints = []
    for cp in arb.contact_point_set.points:
        setpoints.append([list(cp.point_a), list(cp.point_b), cp.distance])
    restitution = arb.restitution
    return [norm, restitution, setpoints]


def _listify(l):
    if hasattr(l, "__iter__") and not isinstance(l, str):
        return [_listify(i) for i in l]
    else:
        return l


class PGWorld(object):
    def __init__(
        self,
        dimensions,
        gravity,
        closed_ends=[True, True, True, True],
        basic_timestep=0.01,
        def_density=DEFAULT_DENSITY,
        def_elasticity=DEFAULT_ELASTICITY,
        def_friction=DEFAULT_FRICTION,
        bk_col=(255, 255, 255),
        def_col=(0, 0, 0),
    ):

        assert (
            len(closed_ends) == 4
        ), "closed_ends must have length 4 boolean array (l,b,r,t)"

        self.def_density = def_density
        self.def_elasticity = def_elasticity
        self.def_friction = def_friction
        self.bk_col = bk_col
        self.def_col = def_col

        self.dims = dimensions
        self.bts = basic_timestep
        self.time = 0
        self.hasPlaceCollision = False

        self.resume_time = float("inf")
        self.pause_ctx = [{}, 0]
        self.teleported = False

        self._cpSpace = pm.Space()
        self._cpSpace.gravity = (0, -gravity)
        self._cpSpace.sleep_time_threshold = 5.0

        self.objects = dict()
        self.blockers = dict()
        self.sensors = dict()
        self.constraints = dict()  # Not implemented yet
        self.sensorHits = []

        self.goalCond = None
        self.winCallback = None
        self._collisionEvents = []
        self._ssBegin = _emptyCollisionHandler
        self._ssPre = _emptyCollisionHandler
        self._ssPost = _emptyCollisionHandler
        self._ssEnd = _emptyCollisionHandler
        self._sgBegin = _emptyCollisionHandler
        self._sgEnd = _emptyCollisionHandler

        def doSolidSolidBegin(arb, space, data):
            # pdb.set_trace()
            return self._solidSolidBegin(arb, space, data)

        def doSolidSolidPre(arb, space, data):
            return self._solidSolidPre(arb, space, data)

        def doSolidSolidPost(arb, space, data):
            return self._solidSolidPost(arb, space, data)

        def doSolidSolidEnd(arb, space, data):
            return self._solidSolidEnd(arb, space, data)

        def doSolidGoalBegin(arb, space, data):
            return self._solidGoalBegin(arb, space, data)

        def doSolidGoalEnd(arb, space, data):
            return self._solidGoalEnd(arb, space, data)

        def doSolidSensorBegin(arb, space, data):
            return self._checkSensors(arb, space, data)

        ssch = self._cpSpace.add_collision_handler(COLTYPE_SOLID, COLTYPE_SOLID)
        ssch.begin = doSolidSolidBegin
        ssch.pre_solve = doSolidSolidPre
        ssch.post_solve = doSolidSolidPost
        ssch.separate = doSolidSolidEnd

        psch = self._cpSpace.add_collision_handler(COLTYPE_PLACED, COLTYPE_SOLID)
        psch.begin = doSolidSolidBegin
        psch.pre_solve = doSolidSolidPre
        psch.post_solve = doSolidSolidPost
        psch.separate = doSolidSolidEnd

        ssench = self._cpSpace.add_collision_handler(COLTYPE_SOLID, COLTYPE_GOAL)
        ssench.begin = doSolidGoalBegin
        ssench.separate = doSolidGoalEnd

        psench = self._cpSpace.add_collision_handler(COLTYPE_PLACED, COLTYPE_GOAL)
        psench.begin = doSolidGoalBegin
        psench.separate = doSolidGoalEnd

        sensorch = self._cpSpace.add_collision_handler(COLTYPE_SOLID, COLTYPE_SENSOR)
        sensorch.begin = doSolidSensorBegin
        psensorch = self._cpSpace.add_collision_handler(COLTYPE_PLACED, COLTYPE_SENSOR)
        psensorch.begin = doSolidSensorBegin

        def _teleport(arb, space, data):
            onm, snm = resolveArbiter(arb)
            obj = self.getObject(onm)
            teleporter = self.sensors[snm]

            # move obj to teleporter exit
            obj._cpBody.position = teleporter.exit_coord
            self.teleported = True
            return True

        teleporterch = self._cpSpace.add_collision_handler(COLTYPE_SOLID, COLTYPE_TELEPORTER)
        teleporterch.begin = _teleport

        if closed_ends[0]:
            self.addBox("_LeftWall", [-1, -1, 1, self.dims[1] + 1], self.def_col, 0)
        if closed_ends[1]:
            self.addBox("_BottomWall", [-1, -1, self.dims[0] + 1, 1], self.def_col, 0)
        if closed_ends[2]:
            self.addBox(
                "_RightWall",
                [self.dims[0] - 1, -1, self.dims[0] + 1, self.dims[1] + 1],
                self.def_col,
                0,
            )
        if closed_ends[3]:
            self.addBox(
                "_TopWall",
                [-1, self.dims[1] - 1, self.dims[0] + 1, self.dims[1] + 1],
                self.def_col,
                0,
            )

    def step(self, t):
        nsteps = int(np.floor(t / self.bts))
        remtime = self.bts % t
        self.time += t

        for i in range(nsteps):
            self._cpSpace.step(self.bts)

            # if we teleported, pause_ctx for 20 steps
            if self.teleported:
                self.resume_time = self.time + 0.1
                old_gravity = self.gravity
                self.pause_ctx[1] = old_gravity
                self.setGravity(0)

                for oname, obj in self.objects.items():
                    if obj.isStatic():
                        continue
                    self.pause_ctx[0][oname] = obj._cpBody.velocity
                    obj._cpBody.velocity = (0, 0)

                self.teleported = False

            if self.time > self.resume_time:
                for oname, obj in self.objects.items():
                    if obj.isStatic():
                        continue
                    v = self.pause_ctx[0][oname]
                    # dampen exit velocity
                    obj._cpBody.velocity = v[0] * 0.6, v[1] * 0.6
                self.setGravity(self.pause_ctx[1])
                self.resume_time = float("inf")

            if self.checkEnd() and self.winCallback is not None:
                self.winCallback()
        if remtime / self.bts > 0.01:
            self._cpSpace.step(remtime)
        if self.checkEnd() and self.winCallback is not None:
            self.winCallback()

    def _invert(self, pt):
        return (pt[0], self.dims[1] - pt[1])

    def _yinvert(self, y):
        return self.dims[1] - y

    def checkEnd(self):
        if self.goalCond is None:
            return False
        return self.goalCond.isWon()

    def getObjectUnderCursor(self, pos):
        for _, obj in self.objects.items():
            if obj.contains(pos):
                return obj
        return None

    def getObject(self, name):
        assert name in self.objects.keys(), "No object by that name: " + name
        return self.objects[name]

    def setObject(self, name, obj):
        self.objects[name] = obj

    def getSensor(self, name):
        assert name in self.sensors.keys(), "No sensor by that name: " + name
        return self.sensors[name]

    def getGravity(self):
        return -self._cpSpace.gravity.y

    def setGravity(self, val):
        self._cpSpace.gravity = (0, -val)

    ########################################
    # Adding things to the world
    ########################################
    def addPoly(
        self, name, vertices, color, density=None, elasticity=None, friction=None
    ):
        assert name not in self.objects.keys(), "Name already taken: " + name
        if density is None:
            density = self.def_density
        if elasticity is None:
            elasticity = self.def_elasticity
        if friction is None:
            friction = self.def_friction

        thisObj = PGPoly(
            name, self._cpSpace, vertices, density, elasticity, friction, color
        )
        self.objects[name] = thisObj
        return thisObj

    def addBox(self, name, bounds, color, density=None, elasticity=None, friction=None):
        assert name not in self.objects.keys(), "Name already taken: " + name
        assert len(bounds) == 4, "Need four numbers for bounds [l,b,r,t]"
        if density is None:
            density = self.def_density
        if elasticity is None:
            elasticity = self.def_elasticity
        if friction is None:
            friction = self.def_friction

        l = bounds[0]
        b = bounds[1]
        r = bounds[2]
        t = bounds[3]
        vertices = [(l, b), (l, t), (r, t), (r, b)]

        thisObj = PGPoly(
            name, self._cpSpace, vertices, density, elasticity, friction, color
        )
        self.objects[name] = thisObj
        return thisObj

    def addBall(
        self,
        name,
        position,
        radius,
        color,
        density=None,
        elasticity=None,
        friction=None,
    ):
        assert name not in self.objects.keys(), "Name already taken: " + name
        if density is None:
            density = self.def_density
        if elasticity is None:
            elasticity = self.def_elasticity
        if friction is None:
            friction = self.def_friction

        thisObj = PGBall(
            name, self._cpSpace, position, radius, density, elasticity, friction, color
        )
        self.objects[name] = thisObj
        return thisObj

    def addSegment(
        self, name, p1, p2, width, color, density=None, elasticity=None, friction=None
    ):
        assert name not in self.objects.keys(), "Name already taken: " + name
        if density is None:
            density = self.def_density
        if elasticity is None:
            elasticity = self.def_elasticity
        if friction is None:
            friction = self.def_friction

        thisObj = PGSeg(
            name, self._cpSpace, p1, p2, width, density, elasticity, friction, color
        )
        self.objects[name] = thisObj
        return thisObj

    def addContainer(
        self,
        name,
        ptlist,
        width,
        inner_color,
        outer_color,
        density=None,
        elasticity=None,
        friction=None,
    ):
        assert name not in self.objects.keys(), "Name already taken: " + name
        if density is None:
            density = self.def_density
        if elasticity is None:
            elasticity = self.def_elasticity
        if friction is None:
            friction = self.def_friction

        thisObj = PGContainer(
            name,
            self._cpSpace,
            ptlist,
            width,
            density,
            elasticity,
            friction,
            inner_color,
            outer_color,
        )
        self.objects[name] = thisObj
        return thisObj

    def addCompound(
        self, name, polys, color, density=None, elasticity=None, friction=None
    ):
        assert name not in self.objects.keys(), "Name already taken: " + name
        if density is None:
            density = self.def_density
        if elasticity is None:
            elasticity = self.def_elasticity
        if friction is None:
            friction = self.def_friction

        thisObj = PGCompound(
            name, self._cpSpace, polys, density, elasticity, friction, color
        )
        self.objects[name] = thisObj
        return thisObj

    def addPolyGoal(self, name, vertices, color):
        assert name not in self.objects.keys(), "Name already taken: " + name
        thisObj = PGGoal(name, self._cpSpace, vertices, color)
        self.objects[name] = thisObj
        return thisObj

    def addBoxGoal(self, name, bounds, color):
        assert name not in self.objects.keys(), "Name already taken: " + name
        assert len(bounds) == 4, "Need four numbers for bounds [l,b,r,t]"
        l = bounds[0]
        b = bounds[1]
        r = bounds[2]
        t = bounds[3]
        vertices = [(l, b), (l, t), (r, t), (r, b)]
        thisObj = PGGoal(name, self._cpSpace, vertices, color)
        self.objects[name] = thisObj
        return thisObj

    # def addTeleporter(self, name, vertices, exit_coord, color):
    #     obj = PGTeleporter(name, self._cpSpace, vertices, exit_coord, color=color)
    #     self.objects[name] = obj
    #     return obj
    def addTeleporter(self, name, center, radius, exit_coord, is_entry, color):
        if not is_entry:
            exit_coord = center
        obj = PGTeleporter(name, self._cpSpace, center, radius, exit_coord, is_entry, color=color)
        self.sensors[name] = obj
        return obj

    def addSensor(self, name, bounds):
        assert name not in self.sensors.keys(), "Name already taken: " + name
        assert len(bounds) == 4, "Need four numbers for bounds [l,b,r,t]"
        l = bounds[0]
        b = bounds[1]
        r = bounds[2]
        t = bounds[3]
        vertices = [(l, b), (l, t), (r, t), (r, b)]
        thisObj = PGSensor(name, self._cpSpace, vertices)
        self.sensors[name] = thisObj
        return thisObj

    def addPolySensor(self, name, vertices, color="none"):
        assert name not in self.sensors.keys(), "Name already taken: " + name
        thisObj = PGSensor(name, self._cpSpace, vertices, color)
        self.sensors[name] = thisObj
        return thisObj

    def addPlacedPoly(
        self, name, vertices, color, density=None, elasticity=None, friction=None
    ):
        thisObj = self.addPoly(name, vertices, color, density, elasticity, friction)
        thisObj._cpShape.collision_type = COLTYPE_PLACED
        return thisObj

    def addPlacedCompound(
        self, name, polys, color, density=None, elasticity=None, friction=None
    ):
        thisObj = self.addCompound(name, polys, color, density, elasticity, friction)
        for cpsh in thisObj._cpShapes:
            cpsh.collision_type = COLTYPE_PLACED
        return thisObj

    def addBlock(self, name, bounds, color):
        assert name not in self.blockers.keys(), "Name already taken: " + name
        assert len(bounds) == 4, "Need four numbers for bounds [l,b,r,t]"
        l = bounds[0]
        b = bounds[1]
        r = bounds[2]
        t = bounds[3]
        vertices = [(l, b), (l, t), (r, t), (r, b)]
        thisObj = PGBlocker(name, self._cpSpace, vertices, color)
        self.blockers[name] = thisObj
        return thisObj

    def addPolyBlock(self, name, vertices, color):
        assert name not in self.blockers.keys(), "Name already taken: " + name
        thisObj = PGBlocker(name, self._cpSpace, vertices, color)
        self.blockers[name] = thisObj
        return thisObj

    def reset(self):
        self.resetCollisions()
        self.sensorHits = []

    ########################################
    # Callbacks
    ########################################
    def getSolidCollisionPre(self):
        return self._ssPre

    def setSolidCollisionPre(self, fnc=_emptyObjectHandler):
        assert callable(fnc), "Must pass legal function to callback setter"
        self._ssPre = fnc

    def getSolidCollisionPost(self):
        return self._ssPost

    def setSolidCollisionPost(self, fnc=_emptyObjectHandler):
        assert callable(fnc), "Must pass legal function to callback setter"
        self._ssPost = fnc

    def getSolidCollisionBegin(self):
        return self._ssBegin

    def setSolidCollisionBegin(self, fnc=_emptyObjectHandler):
        assert callable(fnc), "Must pass legal function to callback setter"
        self._ssBegin = fnc

    def getSolidCollisionEnd(self):
        return self._ssEnd

    def setSolidCollisionEnd(self, fnc=_emptyObjectHandler):
        assert callable(fnc), "Must pass legal function to callback setter"
        self._ssEnd = fnc

    def getGoalCollisionBegin(self):
        return self._sgBegin

    def setGoalCollisionBegin(self, fnc=_emptyObjectHandler):
        assert callable(fnc), "Must pass legal function to callback setter"
        self._sgBegin = fnc

    def getGoalCollisionEnd(self):
        return self._sgEnd

    def setGoalCollisionEnd(self, fnc=_emptyObjectHandler):
        assert callable(fnc), "Must pass legal function to callback setter"
        self._sgEnd = fnc

    def _solidSolidPre(self, arb, space, data):
        onms = resolveArbiter(arb)
        o1 = self.getObject(onms[0])
        o2 = self.getObject(onms[1])
        self._ssPre(o1, o2)
        return True

    def _solidSolidPost(self, arb, space, data):
        onms = resolveArbiter(arb)
        o1 = self.getObject(onms[0])
        o2 = self.getObject(onms[1])
        self._ssPost(o1, o2)
        return True

    def _solidSolidBegin(self, arb, space, data):
        onms = resolveArbiter(arb)
        o1 = self.getObject(onms[0])
        o2 = self.getObject(onms[1])
        # Add any non-static/static collisions to the events
        if not (o1.isStatic() and o2.isStatic()):
            collision_info = pullCollisionInformation(arb)
            self._collisionEvents.append(
                [onms[0], onms[1], "begin", self.time, collision_info]
            )
        self._ssBegin(o1, o2)
        return True

    def _solidSolidEnd(self, arb, space, data):
        onms = resolveArbiter(arb)
        o1 = self.getObject(onms[0])
        o2 = self.getObject(onms[1])
        # Add any non-static/static collisions to the events
        if not (o1.isStatic() and o2.isStatic()):
            collision_info = pullCollisionInformation(arb)
            self._collisionEvents.append(
                [onms[0], onms[1], "end", self.time, collision_info]
            )
        self._ssEnd(o1, o2)
        return True

    def _solidGoalBegin(self, arb, space, data):
        onms = resolveArbiter(arb)
        o1 = self.getObject(onms[0])
        o2 = self.getObject(onms[1])
        self._sgBegin(o1, o2)
        return True

    def _solidGoalEnd(self, arb, space, data):
        onms = resolveArbiter(arb)
        o1 = self.getObject(onms[0])
        o2 = self.getObject(onms[1])
        self._sgEnd(o1, o2)
        return True

    def _checkSensors(self, arb, space, data):
        onm, snm = resolveArbiter(arb)
        obj = self.getObject(onm)
        sensor = self.getSensor(snm)
        # Iterate through the existing sensors and add if not there
        alreadyHit = False
        for exhits in self.sensorHits:
            if exhits[0] == onm and exhits[1] == snm:
                alreadyHit = True
                break
        if not alreadyHit:
            self.sensorHits.append([onm, snm, self.time])
        return True

    ########################################
    # Success conditions
    ########################################
    def _getCallbackOnWin(self):
        return self.winCallback

    def _setCallbackOnWin(self, fnc):
        assert callable(fnc), "Must pass legal function to callback setter"
        self.winCallback = fnc

    def attachAnyInGoal(self, goalname, duration, exclusions=[]):
        self.goalCond = PGCond_AnyInGoal(goalname, duration, self, exclusions)
        self.goalCond.attachHooks()

    def attachSpecificInGoal(self, goalname, objname, duration):
        self.goalCond = PGCond_SpecificInGoal(goalname, objname, duration, self)
        self.goalCond.attachHooks()

    def attachManyInGoal(self, goalname, objlist, duration):
        self.goalCond = PGCond_ManyInGoal(goalname, objlist, duration, self)
        self.goalCond.attachHooks()

    def attachAnyTouch(self, objname, duration):
        self.goalCond = PGCond_AnyTouch(objname, duration, self)
        self.goalCond.attachHooks()

    def attachSpecificTouch(self, obj1, obj2, duration):
        self.goalCond = PGCond_SpecificTouch(obj1, obj2, duration, self)
        self.goalCond.attachHooks()

    def attachSpecificInGoalSet(self, obj, goalset, duration):
        self.goalCond = PGCond_SpecificInGoalSet(obj, goalset, duration, self)
        self.goalCond.attachHooks()

    def attachAnyInGoalSet(self, goalset, duration):
        self.goalCond = PGCond_AnyInGoalSet(goalset, duration, self)
        self.goalCond.attachHooks()

    def attachManyInGoalSet(self, objset, goalset, duration):
        self.goalCond = PGCond_ManyInGoalSet(objset, goalset, duration, self)
        self.goalCond.attachHooks()

    def checkFinishers(self):
        return self.goalCond is not None and self.winCallback is not None

    ########################################
    # Checking collisions
    ########################################

    def resetCollisions(self):
        self._collisionEvents = []

    def _getCollisionEvents(self):
        return self._collisionEvents

    ########################################
    # Misc
    ########################################
    def checkCollision(self, pos, verts):
        nvert = [(v[0] + pos[0], v[1] + pos[1]) for v in verts]
        tmpBody = pm.Body(1, 1)
        placeShape = pm.Poly(tmpBody, nvert)
        placeShape.collision_type = COLTYPE_CHECKER
        placeShape.sensor = True
        self._cpSpace.step(0.000001)

        self.hasPlaceCollision = False
        squery = self._cpSpace.shape_query(placeShape)
        """ Code doesn't account for blockers (sensors)
        if len(squery) == 0:
            return False
        else:
            for sq in squery:
                for p in sq.contact_point_set.points:
                    if p.distance > 0:
                        return True
            return False
        """
        return len(squery) > 0

    def checkCircleCollision(self, pos, rad):
        tmpBody = pm.Body(1, 1)
        placeShape = pm.Circle(tmpBody, rad, pos)
        placeShape.collision_type = COLTYPE_CHECKER
        placeShape.sensor = True
        self._cpSpace.step(0.000001)

        self.hasPlaceCollision = False
        squery = self._cpSpace.shape_query(placeShape)
        return len(squery) > 0

    def kick(self, objectname, impulse, position):
        o = self.getObject(objectname)
        o.kick(impulse, position)

    def distanceToGoal(self, point):
        assert self.goalCond, "Goal condition must be specified to get distance"
        # Special case... requires getting two distances
        if type(self.goalCond) == PGCond_SpecificTouch:
            o1 = self.getObject(self.goalCond.o1)
            o2 = self.getObject(self.goalCond.o2)
            # in this case, we actually want the distance between these two objects...
            return np.abs(
                o1.distanceFromPoint([0, 0]) - o2.distanceFromPoint([0, 0])
            )  # distance between these two objects is thing that matters
        else:
            gobj = self.getObject(self.goalCond.goal)
            return max(gobj.distanceFromPoint(point), 0)

    def distanceToGoalContainer(self, point):
        """Specifies that for container objects, you want the distance to the top of the container"""
        assert self.goalCond, "Goal condition must be specified to get distance"
        # Special case... requires getting two distances
        if type(self.goalCond) == PGCond_SpecificTouch:
            o1 = self.getObject(self.goalCond.o1)
            o2 = self.getObject(self.goalCond.o2)
            # in this case, we actually want the distance between these two objects...
            return np.abs(
                o1.distanceFromPoint([0, 0]) - o2.distanceFromPoint([0, 0])
            )  # distance between these two objects is thing that matters
        else:
            gobj = self.getObject(self.goalCond.goal)
            if gobj.type != "Container":
                return gobj.distanceFromPoint(point)
            else:
                if self.distanceToGoal(point) == 0:
                    return 0
                else:
                    return distanceToObject(gobj, point)

    def getDynamicObjects(self):
        return [
            self.objects[i]
            for i in self.objects.keys()
            if not self.objects[i].isStatic()
        ]

    def toDict(self):
        wdict = dict()
        wdict["dims"] = tuple(self.dims)
        wdict["bts"] = self.bts
        wdict["gravity"] = self.gravity
        wdict["defaults"] = dict(
            density=self.def_density,
            friction=self.def_friction,
            elasticity=self.def_elasticity,
            color=self.def_col,
            bk_color=self.bk_col,
        )

        wdict["objects"] = dict()
        for nm, o in self.objects.items():
            if isinstance(o.color, str):
                col = o.color
            else:
                col = list(o.color)
            attrs = dict(
                type=o.type,
                color=col,
                density=o.density,
                friction=o.friction,
                elasticity=o.elasticity,
            )
            if o.type == "Poly":
                attrs["vertices"] = _listify(o.vertices)
            elif o.type == "Ball":
                attrs["position"] = list(o.position)
                attrs["radius"] = o.radius
            elif o.type == "Segment":
                attrs["p1"], attrs["p2"] = _listify(o.points)
                attrs["width"] = o.r * 2
            elif o.type == "Container":
                attrs["points"] = _listify(o.vertices)
                attrs["width"] = o.r * 2
                attrs["innerColor"] = o.inner_color
                attrs["outerColor"] = o.outer_color
            # elif o.type == "Teleporter":
            #     attrs["radius"] = o.radius
            #     attrs["position"] = o.center
            #     attrs["exit_coord"] = list(o.exit_coord)
            elif o.type == "Goal":
                attrs["vertices"] = _listify(o.vertices)
            elif o.type == "Compound":
                attrs["polys"] = _listify(o.polys)
            else:
                raise Exception("Invalid object type provided")
            wdict["objects"][nm] = attrs

        wdict["sensors"] = dict()
        for nm, o in self.sensors.items():
            attrs = {}
            if o.type == "Teleporter":
                attrs["type"] = "Teleporter"
                attrs["color"] = o.color
                attrs["radius"] = o.radius
                attrs["position"] = o.center
                attrs["exit_coord"] = list(o.exit_coord)
                attrs["is_entry"] = o.is_entry
            else:
                attrs = dict(type=o.type, vertices=_listify(o.vertices), color=o.color)
            wdict["sensors"][nm] = attrs

        wdict["blocks"] = dict()
        for nm, b in self.blockers.items():
            attrs = {"color": list(b.color), "vertices": _listify(b.vertices)}
            wdict["blocks"][nm] = attrs

        wdict["constraints"] = dict()

        if self.goalCond is None:
            wdict["gcond"] = None
        else:
            gc = self.goalCond
            if gc.type == "AnyInGoal":
                wdict["gcond"] = {
                    "type": gc.type,
                    "goal": gc.goal,
                    "obj": "-",
                    "exclusions": gc.excl,
                    "duration": gc.dur,
                }
            elif gc.type == "SpecificInGoal":
                wdict["gcond"] = {
                    "type": gc.type,
                    "goal": gc.goal,
                    "obj": gc.obj,
                    "duration": gc.dur,
                }
            elif gc.type == "ManyInGoal":
                wdict["gcond"] = {
                    "type": gc.type,
                    "goal": gc.goal,
                    "objlist": gc.objlist,
                    "duration": gc.dur,
                }
            elif gc.type == "AnyTouch":
                wdict["gcond"] = {
                    "type": gc.type,
                    "goal": gc.goal,
                    "obj": "-",
                    "duration": gc.dur,
                }
            elif gc.type == "SpecificTouch":
                wdict["gcond"] = {
                    "type": gc.type,
                    "goal": gc.o1,
                    "obj": gc.o2,
                    "duration": gc.dur,
                }
            elif gc.type == "SpecificInGoalSet":
                wdict["gcond"] = {
                    "type": gc.type,
                    "goalset": gc.goals,
                    "obj": gc.obj,
                    "duration": gc.dur,
                }
            elif gc.type == "AnyInGoalSet":
                wdict["gcond"] = {
                    "type": gc.type,
                    "goalset": gc.goals,
                    "duration": gc.dur,
                }
            elif gc.type == "ManyInGoalSet":
                wdict["gcond"] = {
                    "type": gc.type,
                    "objset": gc.objs,
                    "goalset": gc.goals,
                    "duration": gc.dur,
                }
            else:
                raise Exception("Invalid goal condition type provided")

        return wdict

    def copy(self):
        return loadFromDict(self.toDict())

    ########################################
    # Properties (yay pythonic things!)
    ########################################
    gravity = property(getGravity, setGravity)
    solidCollisionPre = property(getSolidCollisionPre, setSolidCollisionPre)
    solidCollisionPost = property(getSolidCollisionPost, setSolidCollisionPost)
    solidCollisionBegin = property(getSolidCollisionBegin, setSolidCollisionBegin)
    solidCollisionEnd = property(getSolidCollisionEnd, setSolidCollisionEnd)
    goalCollisionBegin = property(getGoalCollisionBegin, setGoalCollisionBegin)
    goalCollisionEnd = property(getGoalCollisionEnd, setGoalCollisionEnd)
    callbackOnWin = property(_getCallbackOnWin, _setCallbackOnWin)
    collisionEvents = property(_getCollisionEvents)
