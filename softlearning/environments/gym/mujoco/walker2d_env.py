import numpy as np
from gym.envs.mujoco import mujoco_env
from gym import utils


DEFAULT_CAMERA_CONFIG = {
    'trackbodyid': 2,
    'distance': 4.0,
    'lookat': (None, None, 1.15),
    'elevation': -20.0,
}


class Walker2dEnv(mujoco_env.MujocoEnv, utils.EzPickle):
    def __init__(self,
                 forward_reward_weight=1.0,
                 ctrl_cost_weight=1e-3,
                 survive_reward=1.0,
                 healthy_z_range=(0.8, 2.0),
                 healthy_angle_range=(-1.0, 1.0),
                 exclude_current_positions_from_observation=True):
        self._forward_reward_weight = forward_reward_weight
        self._ctrl_cost_weight = ctrl_cost_weight
        self._survive_reward = survive_reward
        self._healthy_z_range = healthy_z_range
        self._healthy_angle_range = healthy_angle_range
        self._exclude_current_positions_from_observation = (
            exclude_current_positions_from_observation)

        mujoco_env.MujocoEnv.__init__(self, "walker2d.xml", 4)
        utils.EzPickle.__init__(
            self,
            forward_reward_weight=self._forward_reward_weight,
            ctrl_cost_weight=self._ctrl_cost_weight,
            survive_reward=self._survive_reward,
            healthy_z_range=self._healthy_z_range,
            healthy_angle_range=self._healthy_angle_range,
            exclude_current_positions_from_observation=(
                self._exclude_current_positions_from_observation),
        )

    @property
    def survive_reward(self):
        return self._survive_reward

    def control_cost(self, action):
        control_cost = self._ctrl_cost_weight * np.sum(np.square(action))
        return control_cost

    @property
    def is_healthy(self):
        z, angle = self.sim.data.qpos[1:3]

        min_z, max_z = self._healthy_z_range
        min_angle, max_angle = self._healthy_angle_range

        healthy_z = min_z < z < max_z
        healthy_angle = min_angle < angle < max_angle
        is_healthy = healthy_z and healthy_angle

        return is_healthy

    @property
    def done(self):
        done = not self.is_healthy
        return done

    def _get_obs(self):
        position = self.sim.data.qpos.flat.copy()
        velocity = np.clip(
            self.sim.data.qvel.flat.copy(), -10, 10)

        if self._exclude_current_positions_from_observation:
            position = position[1:]

        observation = np.concatenate((position, velocity)).ravel()
        return observation

    def step(self, action):
        x_position_before = self.sim.data.qpos[0]
        self.do_simulation(action, self.frame_skip)
        x_position_after = self.sim.data.qpos[0]
        x_velocity = ((x_position_after - x_position_before)
                      / self.dt)

        ctrl_cost = self.control_cost(action)

        forward_reward = self._forward_reward_weight * x_velocity
        survive_reward = self.survive_reward

        rewards = forward_reward + survive_reward
        costs = ctrl_cost

        observation = self._get_obs()
        reward = rewards - costs
        done = self.done
        info = {}

        return observation, reward, done, info

    def reset_model(self):
        c = 5e-3
        qpos = self.init_qpos + self.np_random.uniform(
            low=-c, high=c, size=self.model.nq)
        qvel = self.init_qvel + self.np_random.uniform(
            low=-c, high=c, size=self.model.nv)

        self.set_state(qpos, qvel)

        observation = self._get_obs()
        return observation

    def viewer_setup(self):
        self.viewer.cam.trackbodyid = 2
        self.viewer.cam.distance = self.model.stat.extent * 0.5
        self.viewer.cam.lookat[2] = 1.15
        self.viewer.cam.elevation = -20