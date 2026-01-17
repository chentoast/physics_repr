import numpy as np
from .constants import *
from .object import *

__all__ = ["PGCond_AnyInGoal", "PGCond_SpecificInGoal", "PGCond_AnyTouch",
           "PGCond_SpecificTouch", "PGCond_ManyInGoal",
           "PGCond_SpecificInGoalSet", "PGCond_AnyInGoalSet",
           "PGCond_ManyInGoalSet"]

class PGCond_Base(object):

    def __init__(self):
        self.goal = self.obj = self.parent = self.dur = None

    def _getTimeIn(self):
        return -1

    def remainingTime(self):
        ti = self._getTimeIn()
        if ti == -1:
            return None
        curtime = self.parent.time - ti
        return max(self.dur - curtime, 0)

    def isWon(self):
        return self.remainingTime() == 0

    def attachHooks(self):
        raise NotImplementedError("Cannot attach hooks from base condition object")


class PGCond_AnyInGoal(PGCond_Base):

    def __init__(self, goalname, duration, parent, exclusions = []):
        self.type = "AnyInGoal"
        self.won = False
        self.goal = goalname
        self.excl = exclusions
        self.dur = duration
        self.ins = {}
        self.hasTime = True
        self.parent = parent

    def _goesIn(self, obj, goal):
        if (goal.name == self.goal and \
                    (not obj.name in self.ins.keys()) and \
                    (not obj.name in self.excl)):
            self.ins[obj.name] = self.parent.time

    def _goesOut(self, obj, goal):
        if (goal.name == self.goal and \
            obj.name in self.ins.keys() and \
                    (not goal.pointIn(obj.position))):
            del self.ins[obj.name]

    def attachHooks(self):
        self.parent.setGoalCollisionBegin(self._goesIn)
        self.parent.setGoalCollisionEnd(self._goesOut)

    def _getTimeIn(self):
        if len(self.ins) == 0:
            return -1
        mintime = min(min(self.ins.values()), self.parent.time)
        return mintime

class PGCond_ManyInGoal(PGCond_Base):

    def __init__(self, goalname, objlist, duration, parent):
        self.type = "ManyInGoal"
        self.won = False
        self.goal = goalname
        self.objlist = objlist
        self.objsin = []
        self.dur = duration
        self.tin = -1
        self.hasTime = True
        self.parent = parent

    def _goesIn(self, obj, goal):
        if (goal.name == self.goal and
            obj.name in self.objlist and
            obj.name not in self.objsin):
            self.objsin.append(obj.name)
            if len(self.objsin) == 1:
                self.tin = self.parent.time

    def _goesOut(self, obj, goal):
        if (goal.name == self.goal and
            obj.name in self.objsin):
            self.objsin.remove(obj.name)
            if len(self.objsin) == 0:
                self.tin = -1

    def attachHooks(self):
        self.parent.setGoalCollisionBegin(self._goesIn)
        self.parent.setGoalCollisionEnd(self._goesOut)

    def _getTimeIn(self):
        return self.tin


class PGCond_SpecificInGoal(PGCond_Base):

    def __init__(self, goalname, objname, duration, parent):
        self.type = "SpecificInGoal"
        self.won = False
        self.goal = goalname
        self.obj = objname
        self.dur = duration
        self.tin = -1
        self.hasTime = True
        self.parent = parent

    def _goesIn(self, obj, goal):
        if goal.name == self.goal and obj.name == self.obj:
            self.tin = self.parent.time

    def _goesOut(self, obj, goal):
        if goal.name == self.goal and obj.name == self.obj and (not goal.pointIn(obj.position)):
            self.tin = -1

    def attachHooks(self):
        self.parent.setGoalCollisionBegin(self._goesIn)
        self.parent.setGoalCollisionEnd(self._goesOut)

    def _getTimeIn(self):
        return self.tin


class PGCond_AnyTouch(PGCond_Base):

    def __init__(self, objname, duration, parent):
        self.type = "AnyTouch"
        self.won = False
        self.goal = objname
        self.dur = duration
        self.tin = -1
        self.hasTime = True
        self.parent = parent

    def _beginTouch(self, obj, goal):
        if obj.name == self.goal or goal.name == self.goal:
            self.tin = self.parent.time

    def _endTouch(self, obj, goal):
        if obj.name == self.goal or goal.name == self.goal:
            sefl.tin = -1

    def attachHooks(self):
        self.parent.setSolidCollisionBegin(self._beginTouch)
        self.parent.setSolidCollisionEnd(self._endTouch)

    def _getTimeIn(self):
        return self.tin

class PGCond_SpecificTouch(PGCond_Base):

    def __init__(self, objname1, objname2, duration, parent):
        self.type = "SpecificTouch"
        self.won = False
        self.o1 = objname1
        self.o2 = objname2
        self.dur = duration
        self.tin = -1
        self.hasTime = True
        self.parent = parent

    def _beginTouch(self, obj1, obj2):
        if (obj1.name == self.o1 and obj2.name == self.o2) or \
            (obj1.name == self.o2 and obj2.name == self.o1):
            self.tin = self.parent.time

    def _endTouch(self, obj1, obj2):
        if (obj1.name == self.o1 and obj2.name == self.o2) or \
            (obj1.name == self.o2 and obj2.name == self.o1):
            self.tin = -1

    def attachHooks(self):
        self.parent.setSolidCollisionBegin(self._beginTouch)
        self.parent.setSolidCollisionEnd(self._endTouch)

    def _getTimeIn(self):
        return self.tin


class PGCond_SpecificInGoalSet(PGCond_Base):

    def __init__(self, objname, goalset, duration, parent):
        self.type = "SpecificInGoalSet"
        self.won = False
        self.obj = objname
        self.goals = goalset
        self.dur = duration
        self.tingoals = {}
        self.hasTime = True
        self.parent = parent

    def _goesIn(self, obj, goal):
        if (obj.name == self.obj and
                goal.name in self.goals and
                goal.name not in self.tingoals.keys()):
            self.tingoals[goal.name] = self.parent.time

    def _goesOut(self, obj, goal):
        if (obj.name == self.obj and
                goal.name in self.tingoals.keys() and
                (not goal.pointIn(obj.position))):
            del self.tingoals[goal.name]

    def attachHooks(self):
        self.parent.setGoalCollisionBegin(self._goesIn)
        self.parent.setGoalCollisionEnd(self._goesOut)

    def _getTimeIn(self):
        if len(self.tingoals) == 0:
            return -1
        mintime = min(min(self.tingoals.values()), self.parent.time)
        return mintime

    def getWinningGoal(self):
        for gnm, rtm in self.tingoals.items():
            curtime = self.parent.time - rtm
            if curtime > self.dur:
                return gnm
        return "NONE"

class PGCond_AnyInGoalSet(PGCond_Base):

    def __init__(self, goalset, duration, parent):
        self.type = "AnyInGoalSet"
        self.won = False
        self.goals = goalset
        self.dur = duration
        self.tinset = {}
        self.hasTime = True
        self.parent = parent

    def _goesIn(self, obj, goal):
        k = self._makeKey(obj, goal)
        if (goal.name in self.goals and k not in self.tinset.keys()):
            self.tinset[k] = self.parent.time

    def _goesOut(self, obj, goal):
        k = self._makeKey(obj, goal)
        if (k in self.tinset.keys() and
            (not goal.pointIn(obj.position))):
            del self.tinset[k]

    def attachHooks(self):
        self.parent.setGoalCollisionBegin(self._goesIn)
        self.parent.setGoalCollisionEnd(self._goesOut)

    def _getTimeIn(self):
        if len(self.tinset) == 0:
            return -1
        mintime = min(min(self.tinset.values()), self.parent.time)
        return mintime

    def getWinningSet(self):
        for k, rtm in self.tinset.keys():
            onm, gnm = k.split('_')
            curtime = self.parent.time - rtm
            if curtime > self.dur:
                return [onm, gnm]
        return ["NONE", "NONE"]

    def getWinningGoal(self):
        return self.getWinningSet()[1]

    def getWinningObj(self):
        return self.getWinningSet()[0]

    def _makeKey(self, obj, goal):
        if "_" in obj.name or "_" in goal.name:
            raise Error("Cannot use objects/goals with underscores for this constraint")
        return obj.name + "_" + goal.name


class PGCond_ManyInGoalSet(PGCond_Base):

    def __init__(self, objset, goalset, duration, parent):
        self.type = "ManyInGoalSet"
        self.won = False
        self.objs = objset
        self.goals = goalset
        self.dur = duration
        self.tinset = {}
        self.hasTime = True
        self.parent = parent

    def _goesIn(self, obj, goal):
        k = self._makeKey(obj, goal)
        if (obj.name in self.objs) and (goal.name in self.goals) and (k not in self.tinset.keys()):
            self.tinset[k] = self.parent.time

    def _goesOut(self, obj, goal):
        k = self._makeKey(obj, goal)
        if (k in self.tinset.keys() and
            (not goal.pointIn(obj.position))):
            del self.tinset[k]

    def attachHooks(self):
        self.parent.setGoalCollisionBegin(self._goesIn)
        self.parent.setGoalCollisionEnd(self._goesOut)

    def _getTimeIn(self):
        if len(self.tinset) == 0:
            return -1
        mintime = min(min(self.tinset.values()), self.parent.time)
        return mintime

    def getWinningSet(self):
        for k, rtm in self.tinset.keys():
            onm, gnm = k.split('_')
            curtime = self.parent.time - rtm
            if curtime > self.dur:
                return [onm, gnm]
        return ["NONE", "NONE"]

    def getWinningGoal(self):
        return self.getWinningSet()[1]

    def getWinningObj(self):
        return self.getWinningSet()[0]

    def _makeKey(self, obj, goal):
        if "_" in obj.name or "_" in goal.name:
            raise Error("Cannot use objects/goals with underscores for this constraint")
        return obj.name + "_" + goal.name
