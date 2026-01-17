# first line: 112
def value_guided_construal(
    *,
    tile_array,
    construal_inverse_temp,
    feature_rewards=(("G", 0), ),
    absorbing_features=("G",),
    wall_features="#0123456789",
    default_features=(".",),
    initial_features=("S",),
    step_cost=-1,
    discount_rate=1.0-1e-5,
    planning_alg="policy_iteration"
):
    assert planning_alg in ("policy_iteration", "value_iteration")
    true_maze_params = dict(
        tile_array=tile_array,
        feature_rewards=feature_rewards,
        absorbing_features=absorbing_features,
        wall_features=wall_features,
        default_features=default_features,
        initial_features=initial_features,
        step_cost=step_cost,
        discount_rate=discount_rate,
        wall_bump_cost=0,
        wall_block_prob=1.0,
        success_prob=1-1e-5,
        include_action_effect=True,
        include_wall_effect=True,
        include_terminal_state_effect=True
    )
    true_maze = Maze(**true_maze_params)
    obstacle_chars = set(''.join(tile_array)) & set('0123456789')
    vor = {}
    for construal in powerset(obstacle_chars):
        construal = ''.join(sorted(construal))
        construed_maze = ConstruedMaze(true_maze_params, construal)
        if planning_alg == "policy_iteration":
            plan_res = PolicyIteration().plan_on(construed_maze)
        elif planning_alg == "value_iteration":
            plan_res = ValueIteration().plan_on(construed_maze)
        assert plan_res.converged
        policy_utility = plan_res.policy.evaluate_on(true_maze).initial_value
        vor[construal] = policy_utility - len(construal)
    c_dist = SoftmaxDistribution({c: v*construal_inverse_temp for c, v in vor.items()})
    obstacle_probs = {o: c_dist.expectation(lambda c: o in c) for o in obstacle_chars}
    return dict(
        obstacle_probs=obstacle_probs,
        value_of_representation=vor
    )