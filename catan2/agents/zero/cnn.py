"""
Convolutional Neural Net

Given a game state s, predict the policy MCTS(s) will come up with
"""

import torch
import torch.nn.functional as F
from torch import nn, optim

from catan2 import config
from catan2.constants import BOARD_WIDTH, NUM_UNIQUE_ACTIONS

from .device import device
from .gamestate import GameState

NUM_GAME_LAYERS = sum(v for k, v in GameState.num_layers.items())


class ConvBlock(nn.Module):
    out_channels = 32

    def __init__(self):
        super().__init__()

        self.conv1 = nn.Conv2d(in_channels=NUM_GAME_LAYERS, out_channels=self.out_channels, kernel_size=5, stride=1, padding=2)
        self.bn1 = nn.BatchNorm2d(self.out_channels)

    def forward(self, s):
        s = s.view(-1, NUM_GAME_LAYERS, BOARD_WIDTH, BOARD_WIDTH).float()
        s = self.conv1(s)
        s = self.bn1(s)
        s = F.relu(s)
        return s


class ResBlock(nn.Module):
    in_planes = ConvBlock.out_channels
    planes = in_planes
    out_planes = planes

    def __init__(self):
        super().__init__()

        self.layer1 = nn.Sequential(
            nn.Conv2d(self.in_planes, self.planes, kernel_size=5, stride=1, padding=2, bias=False),
            nn.BatchNorm2d(self.planes),
            nn.ReLU()
        )

        self.layer2 = nn.Sequential(
            nn.Conv2d(self.planes, self.out_planes, kernel_size=5, stride=1, padding=2, bias=False),
            nn.BatchNorm2d(self.out_planes)
        )

    def forward(self, x):
        residual = x
        out = self.layer1(x)
        out = self.layer2(out)
        out += residual
        out = F.relu(out)
        return out


class OutBlock(nn.Module):
    in_planes = ResBlock.out_planes
    bn_planes = 3
    v_fc_size = p_fc_size = int(in_planes / 2)

    def __init__(self):
        super().__init__()

        # value
        self.v_conv = nn.Conv2d(self.in_planes, self.bn_planes, kernel_size=1)
        self.v_bn = nn.BatchNorm2d(self.bn_planes)
        self.v_fc1 = nn.Linear(self.bn_planes * BOARD_WIDTH * BOARD_WIDTH, self.v_fc_size)
        self.v_fc2 = nn.Linear(self.v_fc_size, 1)

        # policy
        self.p_conv = nn.Conv2d(self.in_planes, self.p_fc_size, kernel_size=1)
        self.p_bn = nn.BatchNorm2d(self.p_fc_size)
        self.p_fc = nn.Linear(self.p_fc_size * BOARD_WIDTH * BOARD_WIDTH, NUM_UNIQUE_ACTIONS)
        self.p_softmax = nn.Softmax(dim=1)

    def forward(self, s):
        v = self.v_conv(s)
        v = self.v_bn(v)
        v = F.relu(v)
        v = v.view(-1, self.bn_planes * BOARD_WIDTH * BOARD_WIDTH)  # batch_size X channel X height X width
        v = self.v_fc1(v)
        v = F.relu(v)
        v = self.v_fc2(v)
        v = torch.tanh(v)

        p = self.p_conv(s)
        p = self.p_bn(p)
        p = F.relu(p)
        p = p.view(-1, BOARD_WIDTH * BOARD_WIDTH * self.p_fc_size)
        p = self.p_fc(p)
        p = self.p_softmax(p)
        # p = p.exp()

        return p, v


class AlphaLoss(nn.Module):
    # N.B. This is an approximation of .999^n
    # As long as batch_size << 10k, the approximation is good enough
    alpha = 1 - (.0001 * config['ai']['batch_size'])
    regularizer = torch.ones(NUM_UNIQUE_ACTIONS).to(device)/NUM_UNIQUE_ACTIONS

    def forward(self, pi_x, pi_y, val_x, val_y):
        # Regularize
        legal_moves = pi_y.ceil().mean(dim=0)
        AlphaLoss.regularizer = AlphaLoss.alpha * AlphaLoss.regularizer + (1 - AlphaLoss.alpha) * legal_moves

        # Policy Error
        cross_entropy_loss = (-pi_y * ((1e-8 + pi_x).log()))
        regularized_loss = cross_entropy_loss / self.regularizer.sqrt()
        policy_error = torch.sum(regularized_loss)

        # Value Error
        val_x = val_x.view(-1)
        value_error = torch.sum((val_x - val_y) ** 2) * 10

        # Total Error
        total_error = (value_error + policy_error)

        return total_error


class CNN(nn.Module):
    def __init__(self):
        super().__init__()

        # Build the net
        self.conv = ConvBlock()
        for block in range(config['ai']['zero']['net']['res_layers']):
            setattr(self, "res_%i" % block, ResBlock())
        self.outblock = OutBlock()

        self.criterion = AlphaLoss()

        # Optimize
        self.set_optimizer()
        self.set_scheduler()

        # Regularization term
        # self.regularize_moves = torch.as_tensor([
        #     7.0051e-42, 9.5287e-01, 1.6934e-01, 2.4998e-02, 2.0972e-02, 2.3787e-02,
        #     5.3991e-02, 1.2153e-02, 2.5380e-02, 2.2147e-02, 1.8408e-02, 1.6115e-02,
        #     1.2814e-02, 1.4467e-02, 1.4470e-02, 2.1848e-02, 2.2678e-02, 1.4976e-02,
        #     1.0452e-02, 1.3737e-02, 2.0268e-02, 2.2238e-02, 1.5673e-02, 2.3724e-02,
        #     2.4123e-02, 2.0758e-02, 1.6346e-02, 1.8718e-02, 2.4203e-02, 2.5304e-02,
        #     2.4611e-02, 2.2942e-02, 2.4309e-02, 2.5434e-02, 1.2505e-02, 1.5032e-02,
        #     2.2663e-02, 2.3025e-02, 2.3273e-02, 1.7276e-02, 1.9611e-02, 1.2585e-02,
        #     1.1701e-02, 2.5010e-02, 2.3071e-02, 2.1339e-02, 2.6720e-02, 2.9365e-02,
        #     2.7499e-02, 2.0283e-02, 2.7830e-02, 2.3686e-02, 1.3587e-02, 1.3105e-02,
        #     1.3451e-02, 2.2226e-02, 2.6119e-02, 1.8090e-02, 1.7372e-02, 1.9997e-02,
        #     2.0613e-02, 2.5425e-02, 1.9419e-02, 2.5644e-02, 1.9190e-02, 2.2444e-02,
        #     1.6848e-02, 1.2302e-02, 1.7298e-02, 1.7191e-02, 1.5018e-02, 1.3479e-02,
        #     1.7718e-02, 2.0120e-02, 1.7131e-02, 1.6598e-02, 1.3918e-02, 1.2903e-02,
        #     1.5749e-02, 2.5665e-02, 2.6521e-02, 2.5694e-02, 2.6094e-02, 2.5530e-02,
        #     2.7364e-02, 2.5710e-02, 2.6464e-02, 2.5885e-02, 2.8207e-02, 2.4343e-02,
        #     2.5785e-02, 2.3850e-02, 2.5439e-02, 2.4702e-02, 2.7306e-02, 2.4477e-02,
        #     2.6680e-02, 2.6057e-02, 2.8726e-02, 2.4123e-02, 2.6567e-02, 2.5082e-02,
        #     2.5798e-02, 2.6917e-02, 2.8295e-02, 2.7527e-02, 2.6138e-02, 2.3622e-02,
        #     2.9350e-02, 2.6537e-02, 2.9314e-02, 2.9665e-02, 2.9403e-02, 2.6666e-02,
        #     2.5472e-02, 2.4646e-02, 2.3254e-02, 2.7487e-02, 2.2533e-02, 2.6220e-02,
        #     2.9070e-02, 2.7125e-02, 2.6143e-02, 2.4164e-02, 2.5930e-02, 2.4424e-02,
        #     2.4456e-02, 2.3677e-02, 2.5600e-02, 2.4585e-02, 2.5772e-02, 2.6171e-02,
        #     2.4527e-02, 1.8716e-03, 1.7956e-03, 3.5986e-03, 3.9020e-03, 1.7331e-03,
        #     1.9251e-03, 8.1622e-04, 1.6349e-03, 2.2625e-03, 2.9247e-03, 1.6390e-03,
        #     7.6944e-04, 1.9119e-03, 2.9035e-03, 3.0318e-03, 3.7452e-03, 2.1262e-03,
        #     8.2516e-04, 3.2391e-03, 5.3251e-03, 3.8309e-03, 2.9531e-03, 1.1766e-03,
        #     1.4602e-03, 3.9666e-03, 4.7171e-03, 8.4857e-04, 2.1358e-03, 1.7237e-03,
        #     4.0401e-03, 2.2360e-03, 3.7908e-03, 3.0087e-03, 3.1334e-03, 3.3681e-03,
        #     1.1477e-03, 3.3990e-03, 3.3318e-03, 3.5086e-03, 2.3476e-03, 4.3013e-03,
        #     2.6269e-03, 2.0445e-03, 3.7214e-03, 2.6344e-03, 1.8309e-03, 9.2287e-04,
        #     2.5311e-03, 2.0672e-03, 1.9061e-03, 2.7554e-03, 2.1005e-03, 2.6918e-03,
        #     7.6777e-04, 1.2470e-01, 1.2470e-01, 1.2470e-01, 1.2470e-01, 1.3399e-01,
        #     1.3399e-01, 1.3399e-01, 1.3399e-01, 1.4046e-01, 1.4046e-01, 1.4046e-01,
        #     1.4046e-01, 1.0918e-01, 1.0918e-01, 1.0918e-01, 1.0918e-01, 1.3219e-01,
        #     1.3219e-01, 1.3219e-01, 1.3219e-01])

    @property
    def regularize_moves(self):
        return self.criterion.regularizer

    def set_optimizer(self):
        if config['ai']['zero']['net']['optimizer'] == 'Adam':
            self.optimizer = optim.Adam(
                self.parameters(),
                lr=config['ai']['zero']['net']['learning rate']
            )
        elif config['ai']['zero']['net']['optimizer'] == 'SGD':
            self.optimizer = optim.SGD(
                self.parameters(),
                lr=config['training']['learning rate'],
                momentum=config['ai']['zero']['net']['momentum']
            )
        else:
            raise NotImplementedError(f"Cannot create net - optimizer of type {config['ai']['zero']['net']['optimizer']} not implemented")

    def set_scheduler(self):
        self.scheduler = torch.optim.lr_scheduler.MultiStepLR(
            self.optimizer,
            milestones=[milestone // config['ai']['batch_size'] for milestone in config['ai']['zero']['net']['milestones']],
            gamma=config['ai']['zero']['net']['lr_gamma']
        )

    @staticmethod
    def get_path(net_version: int = None):
        version = f'_{net_version}' if net_version is not None else ''
        return config['directories']['model']['save_to'] + f'/zero{version}.pt'

    def forward(self, s):
        s = self.conv(s)
        for block in range(config['ai']['zero']['net']['res_layers']):
            s = getattr(self, "res_%i" % block)(s)
        s = self.outblock(s)

        return s

    def load(self, net_version: int = None, filename: str = None):
        filename = filename or self.get_path(net_version)
        self.load_state_dict(torch.load(filename))
        self.to(device)

    def save(self, net_version: int = None, filename: str = None):
        filename = filename or self.get_path(net_version)
        torch.save(self.state_dict(), filename)
