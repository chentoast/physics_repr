import multiprocessing as mp

from .noisyWorld import noisifyWorld
import pyGameWorld as pgw


# Returns the paths of all of the dynamic objects in the scene
def simulate_path(world, stepsize, maxtime=20.0):
    running = True
    pathdict = dict()
    tracknames = []
    for onm, o in world.objects.items():
        if not o.isStatic():
            tracknames.append(onm)
            pathdict[onm] = [
                [o.position[0], o.position[1], o.rotation, o.velocity[0], o.velocity[1]]
            ]
    while running:
        world.step(stepsize)
        for onm in tracknames:
            pathdict[onm].append(
                [
                    world.objects[onm].position[0],
                    world.objects[onm].position[1],
                    world.objects[onm].rotation,
                    world.objects[onm].velocity[0],
                    world.objects[onm].velocity[1],
                ]
            )
        if (world.checkEnd()) or (world.time >= maxtime):
            running = False
    return pathdict


# Returns a set of paths of the focus object under noisy physics
def simulate_noisypaths(
    world,
    stepsize,
    N=20,
    noise_position_static=0.0,
    noise_position_moving=5.0,
    noise_collision_direction=0.2,
    noise_collision_elasticity=0.2,
    noise_gravity=0.1,
    noise_object_friction=0.1,
    noise_object_density=0.1,
    noise_object_elasticity=0.1,
    per_object_noise={},
):
    # assert self._run, "Must have .run() before calculating noisy paths"
    paths = []
    # breakpoint()
    for _ in range(N):
        nw = noisifyWorld(
            world,
            noise_position_static,
            noise_position_moving,
            noise_collision_direction,
            noise_collision_elasticity,
            noise_gravity,
            noise_object_friction,
            noise_object_density,
            noise_object_elasticity,
            per_object_noise,
        )

        thispath = simulate_path(nw, stepsize)
        # while not (nw.checkEnd() or (nw.time > self.mrt)):
        #        nw.step(self.sSS)

        thisSensHits = []
        for sh in nw.sensorHits:
            if sh[0] == "FOCUS":
                thisSensHits.append([sh[1], sh[2]])
        paths.append(
            {
                "path": thispath,
                "sensors": thisSensHits,
                "collisions": nw.collisionEvents,
                "goal": nw.goalCond.getWinningGoal(),
            }
        )
    return paths


def simulate_one_noisypath(param):
    # assert self._run, "Must have .run() before calculating noisy paths"
    (
        world,
        stepsize,
        noise_position_static,
        noise_position_moving,
        noise_collision_direction,
        noise_collision_elasticity,
        noise_gravity,
        noise_object_friction,
        noise_object_density,
        noise_object_elasticity,
        per_object_noise,
    ) = param
    print("--" * 50)
    nw = noisifyWorld(
        pgw.loadFromDict(world),
        noise_position_static,
        noise_position_moving,
        noise_collision_direction,
        noise_collision_elasticity,
        noise_gravity,
        noise_object_friction,
        noise_object_density,
        noise_object_elasticity,
        per_object_noise,
    )
    print(nw)

    thispath = simulate_path(nw, stepsize)
    # while not (nw.checkEnd() or (nw.time > self.mrt)):
    #        nw.step(self.sSS)

    thisSensHits = []
    for sh in nw.sensorHits:
        if sh[0] == "FOCUS":
            thisSensHits.append([sh[1], sh[2]])
    return {
        "path": thispath,
        "sensors": thisSensHits,
        "collisions": nw.collisionEvents,
        "goal": nw.goalCond.getWinningGoal(),
    }


# Returns a set of paths of the focus object under noisy physics
def simulate_noisypaths_parallel(
    world,
    stepsize,
    N=20,
    noise_position_static=0.0,
    noise_position_moving=5.0,
    noise_collision_direction=0.2,
    noise_collision_elasticity=0.2,
    noise_gravity=0.1,
    noise_object_friction=0.1,
    noise_object_density=0.1,
    noise_object_elasticity=0.1,
    per_object_noise={},
):
    # def simulate_noisypath(world):
    # # assert self._run, "Must have .run() before calculating noisy paths"
    #     nw = noisifyWorld(
    #         world,
    #         noise_position_static,
    #         noise_position_moving,
    #         noise_collision_direction,
    #         noise_collision_elasticity,
    #         noise_gravity,
    #         noise_object_friction,
    #         noise_object_density,
    #         noise_object_elasticity,
    #         per_object_noise
    #     )

    #     thispath = simulate_path(nw, stepsize)
    #     # while not (nw.checkEnd() or (nw.time > self.mrt)):
    #     #        nw.step(self.sSS)

    #     thisSensHits = []
    #     for sh in nw.sensorHits:
    #         if sh[0] == "FOCUS":
    #             thisSensHits.append([sh[1], sh[2]])
    #     return {
    #             "path": thispath,
    #             "sensors": thisSensHits,
    #             "collisions": nw.collisionEvents,
    #             "goal": nw.goalCond.getWinningGoal(),
    #         }

    iters = [
        (
            world,
            stepsize,
            noise_position_static,
            noise_position_moving,
            noise_collision_direction,
            noise_collision_elasticity,
            noise_gravity,
            noise_object_friction,
            noise_object_density,
            noise_object_elasticity,
            per_object_noise,
        )
    ] * N
    with mp.Pool(mp.cpu_count()) as p:
        paths = p.map(
            simulate_one_noisypath,
            [
                (
                    # world.copy(),
                    world,
                    stepsize,
                    noise_position_static,
                    noise_position_moving,
                    noise_collision_direction,
                    noise_collision_elasticity,
                    noise_gravity,
                    noise_object_friction,
                    noise_object_density,
                    noise_object_elasticity,
                    per_object_noise,
                )
                for _ in range(N)
            ],
        )

    return paths
