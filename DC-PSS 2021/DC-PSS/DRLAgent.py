import torch

from AgentMADDPG import AgentMADDPG
from Arguments import Arguments
from Run_tutorial import train_and_evaluate

MODELS = {"maddpg": AgentMADDPG}
OFF_POLICY_MODELS = ["maddpg", "td3", "sac"]
ON_POLICY_MODELS = ["ppo", "a2c"]
"""MODEL_KWARGS = {x: config.__dict__[f"{x.upper()}_PARAMS"] for x in MODELS.keys()}

NOISE = {
    "normal": NormalActionNoise,
    "ornstein_uhlenbeck": OrnsteinUhlenbeckActionNoise,
}"""


class DRLAgent:
    """Implementations of DRL algorithms
    Attributes
    ----------
        env: gym environment class
            user-defined class
    Methods
    -------
        get_model()
            setup DRL algorithms
        train_model()
            train DRL algorithms in a train dataset
            and output the trained model
        DRL_prediction()
            make a prediction in a test dataset and get results
    """

    def __init__(self, env, price_array, tech_array, turbulence_array):
        self.env = env
        self.price_array = price_array
        self.tech_array = tech_array
        self.turbulence_array = turbulence_array

    def get_model(self, model_name, model_kwargs):
        env_config = {
            "price_array": self.price_array,
            "tech_array": self.tech_array,
            "turbulence_array": self.turbulence_array,
            "if_train": True,
        }
        env = self.env(config=env_config)
        env.env_num = 1
        agent = MODELS[model_name]()
        if model_name not in MODELS:
            raise NotImplementedError("NotImplementedError")
        model = Arguments(env, agent)
        if model_name in OFF_POLICY_MODELS:
            model.if_off_policy = True
        else:
            model.if_off_policy = False

        if model_kwargs is not None:
            try:
                model.learning_rate = model_kwargs["learning_rate"]
                model.batch_size = model_kwargs["batch_size"]
                model.gamma = model_kwargs["gamma"]
                model.seed = model_kwargs["seed"]
                model.net_dim = model_kwargs["net_dimension"]
                model.target_step = model_kwargs["target_step"]
                model.eval_gap = model_kwargs["eval_gap"]
            except BaseException:
                raise ValueError(
                    "Fail to read arguments, please check 'model_kwargs' input."
                )
        return model

    def train_model(self, model, cwd, total_timesteps=5000):
        model.cwd = cwd
        model.break_step = total_timesteps
        train_and_evaluate(model)

    @staticmethod
    def DRL_prediction(model_name, cwd, net_dimension, environment):
        if model_name not in MODELS:
            raise NotImplementedError("NotImplementedError")
        model = MODELS[model_name]()
        environment.env_num = 1
        args = Arguments(env=environment, agent=model)
        if model_name in OFF_POLICY_MODELS:
            args.if_off_policy = True
        else:
            args.if_off_policy = False
        args.agent = model
        args.env = environment
        # args.agent.if_use_cri_target = True  ##Not needed for test

        # load agent
        try:
            state_dim = environment.state_dim
            action_dim = environment.action_dim

            agent = args.agent
            net_dim = net_dimension

            agent.init(net_dim, state_dim, action_dim)
            agent.save_or_load_agent(cwd=cwd, if_save=False)
            act1 = agent.agents[0].act
            act2 = agent.agents[1].act
            # act[0]
            # act[1]
            ############################################################
            # act_ddpg = agent.act
            device = agent.device

        except BaseException:
            raise ValueError("Fail to load agent!")

        # test on the testing env
        _torch = torch
        state = environment.reset()
        episode_returns = list()  # the cumulative_return / initial_account
        episode_total_assets = list()
        episode_total_assets.append(environment.initial_total_asset)
        with _torch.no_grad():
            for i in range(environment.max_step):
                s_tensor = _torch.as_tensor((state,), device=device)
                print("state", state[0, 0])
                a_tensor = 0.75 * act1(s_tensor) + 0.25 * act2(s_tensor)   # action_tanh = act.forward()
                print("a_tensor 1", act1(s_tensor))
                print("a_tensor 2", act2(s_tensor))
                action = (
                    a_tensor.detach().cpu().numpy()[0]
                )  # not need detach(), because with torch.no_grad() outside
                print("action", action[0])
                state, reward, done, _ = environment.back_test_step(action)

                print("reward", reward)
                print("=================================================")
                total_asset = (
                        environment.amount
                        + (
                                environment.price_ary[environment.day] * environment.stocks
                        ).sum()
                )
                episode_total_assets.append(total_asset)
                episode_return = total_asset / environment.initial_total_asset
                episode_returns.append(episode_return)
                if done:
                    break
        print("Test Finished!")
        # return episode total_assets on testing data
        print("episode_return", episode_return)
        return episode_total_assets
