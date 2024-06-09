from collections import OrderedDict
from hydra.utils import instantiate

from omegaconf import DictConfig
from test import test_server
from train import TrainTestPipe
import torch

from model import test



def get_on_fit_config(config: DictConfig):
    """Return function that prepares config to send to clients."""

    def fit_config_fn(server_round: int):
        # This function will be executed by the strategy in its
        # `configure_fit()` method.

        # Here we are returning the same config on each round but
        # here you might use the `server_round` input argument to
        # adapt over time these settings so clients. For example, you
        # might want clients to use a different learning rate at later
        # stages in the FL process (e.g. smaller lr after N rounds)

        return {
            "lr": config.lr,
            "momentum": config.momentum,
            "local_epochs": config.local_epochs,
        }

    return fit_config_fn


def get_evaluate_fn(model_cfg, testloader):
    """Define function for global evaluation on the server."""

    def evaluate_fn(server_round: int, parameters, config):
        # This function is called by the strategy's `evaluate()` method
        # and receives as input arguments the current round number and the
        # parameters of the global model.
        # this function takes these parameters and evaluates the global model
        # on a evaluation / test dataset.

        #model = instantiate(model_cfg)


        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

        ttp = TrainTestPipe(block_num=model_cfg.block_num,
                                 class_num=model_cfg.class_num, 
                                 device=device,
                                 lr=model_cfg.lr,
                                 momentum=model_cfg.momentum,
                                 head_num=model_cfg.head_num,
                                 img_dim=model_cfg.img_dim,
                                 in_channels=model_cfg.in_channels,
                                 mlp_dim=model_cfg.mlp_dim, 
                                 model_path=model_cfg.model_path, 
                                 out_channels=model_cfg.out_channels,
                                 patch_dim=model_cfg.patch_dim, 
                                  weight_decay=model_cfg.weight_decay)
        
        model = ttp.transunet.model


        params_dict = zip(model.state_dict().keys(), parameters)
        state_dict = OrderedDict({k: torch.Tensor(v) for k, v in params_dict})
        model.load_state_dict(state_dict, strict=True)

        # Here we evaluate the global model on the test set. Recall that in more
        # realistic settings you'd only do this at the end of your FL experiment
        # you can use the `server_round` input argument to determine if this is the
        # last round. If it's not, then preferably use a global validation set.
        #loss, accuracy = test(model, testloader, device)
        loss , metrics = test_server(model, testloader, device)


        # Report the loss and any other metric (inside a dictionary). In this case
        # we report the global test accuracy.
        return loss, {"IOU": metrics[0],
                      "F1": metrics[1],
                      "accuracy": metrics[2],
                      "recall": metrics[3],
                      "precision": metrics[4]}

    return evaluate_fn