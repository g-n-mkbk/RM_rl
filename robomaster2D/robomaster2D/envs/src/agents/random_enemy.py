import numpy as np

from robomaster2D.envs.src.agents_base import Base_Agent


class My_Agent(Base_Agent):
    def __init__(self, _id, options):
        super().__init__(_id, options)
        self.name = 'random_enemy'

    def decode_actions(self, game_state, actions=None):
        self.orders.reset()
        for i, robot_id in enumerate(self.robot_ids):
            if game_state.robots[robot_id].hp <= 0:
                continue
            self.orders.set[i].x = np.random.randint(-1, 2)
            self.orders.set[i].y = np.random.randint(-1, 2)
            self.orders.set[i].rotate = np.random.randint(-1, 2)
            if self.enemy_num > 1:
                self.orders.set[i].shoot_target_enemy = np.random.randint(0, self.enemy_num)
            if (not self.use_action_mask) or game_state.robots[robot_id].aimed_enemy is not None:
                self.orders.set[i].shoot = np.random.randint(0, 2)
        return self.orders
