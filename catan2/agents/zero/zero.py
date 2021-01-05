"""
An Agent Named Zero
"""

import random
import timeit
import torch

from catan2 import config, log
from catan2.agents import Agent
from catan2.catan.actions import get_action_by_id, get_legal_action_ids
from catan2.catan.player import Player
from catan2.constants import NUM_UNIQUE_ACTIONS

from .cnn import CNN
from .data import CatanDataLoader
from .device import device
from .gamestate import GameState
from .mcts import MCT


def even_pi(game):
    legal_action_ids = get_legal_action_ids(game)
    num_choices = len(legal_action_ids)
    return [1/num_choices if i in legal_action_ids else 0 for i in range(NUM_UNIQUE_ACTIONS)]


class Zero(Agent):
    """
    Zero chooses a move based off of a Monte Carlo Tree Search, using a CNN to represent game states
    similar to the approach taken by DeepMind's AlphaZero
    """
    raw_samples: [(GameState, [float])] = []
    cooked_samples: [(torch.tensor, torch.tensor, torch.tensor)]
    threshold = .55
    _net: CNN = CNN().to(device)

    def __init__(self, name: str = None, net_version: int = None):
        super().__init__(name)
        self.net = None
        self.mct = MCT()
        self.mcts_iterations = config['ai']['zero']['mcts']['iterations']

        if net_version is not None:
            self._load(net_version)
        else:
            self.net = CNN().to(device)

        log.trace(message=f"A new instance of Zero ({self.name}) has been created")

    def choose_action(self):
        if self.mcts_iterations > 0:
            pi = self.mct.search(self.game, self.net, self.mcts_iterations)
        else:
            pi = even_pi(self.game)
        action_id = random.choices(population=range(len(pi)), weights=pi, k=1)[0]

        self.raw_samples.append((
            GameState(self.game).tensor,
            pi,
            self.game.current_player
        ))

        log.debug(message=f"{self.name} chose action id {action_id}")

        return get_action_by_id(self.game, action_id)

    def _load(self, net_version: int = None, filename: str = None):
        if net_version == -1:
            self.net = Zero._net
        else:
            self.net = CNN().to(device)
            if net_version is not None:
                self.net.load(net_version=net_version, filename=filename)
                self._name += f"_{net_version}"

    @staticmethod
    def save(version: int = None, filename: str = None):
        Zero._net.save(net_version=version, filename=filename)

    @staticmethod
    def load(version: int = None, filename: str = None):
        Zero._net.load(net_version=version, filename=filename)
        Zero._net.set_optimizer()

    @staticmethod
    def cook_samples(winner: Player, file_num: int):
        Zero.cooked_samples = [(
            sample[0],
            torch.as_tensor(sample[1], dtype=torch.float, device=device),
            torch.as_tensor(1 if sample[2] == winner else -1, dtype=torch.short, device=device)
        ) for sample in Zero.raw_samples]
        Zero.raw_samples = []
        torch.save(Zero.cooked_samples, config['directories']['samples']['save_to'] + '_' + str(file_num))

    @staticmethod
    def pretrain():
        train_dir = config['directories']['samples']['load_from'] + 'Train/'
        dev_dir = config['directories']['samples']['load_from'] + 'Dev/'

        train_set = CatanDataLoader(train_dir)
        dev_set = CatanDataLoader(dev_dir)

        start = timeit.default_timer()
        Zero.train(train_set, dev_set)
        end = timeit.default_timer()

        log.info(f'pretrain duration: {end - start}', tags=['experiment'])

    @staticmethod
    def train(train_set=None, dev_set=None, test_set=None):
        train_set = train_set or Zero.cooked_samples
        print_every_this_many_samples = 100000
        print_loss_frequency = print_every_this_many_samples / config['ai']['batch_size']

        # Train
        for epoch in range(config['ai']['num_epochs']):
            start = timeit.default_timer()
            epoch_loss = 0.0
            running_loss = 0.0
            for i, sample in enumerate(train_set):
                game_state, pi_target, v_target = sample

                # zero the parameter gradients
                Zero._net.optimizer.zero_grad()

                # forward + backward + optimize
                pi_out, v_out = Zero._net(game_state)
                loss = Zero._net.criterion(pi_out, pi_target, v_out, v_target)
                loss.backward()
                Zero._net.optimizer.step()

                # print statistics
                epoch_loss += loss.item()
                running_loss += loss.item()
                if (i+1) % print_loss_frequency == 0:
                    log.info(f'[{epoch + 1}, {(i+1) * config["ai"]["batch_size"]}] loss: {running_loss / print_every_this_many_samples}', tags=['experiment'])
                    running_loss = 0.0

            Zero._net.scheduler.step()
            end = timeit.default_timer()
            train_stats = {
                'duration': end - start,
                'epoch_loss': epoch_loss/(i * config['ai']['batch_size'])
            }
            log.info(f'epoch finished', data=train_stats, tags=['experiment'])

            # Check progress
            if dev_set is not None and config['logging']['categories']['experiment']:
                start = timeit.default_timer()
                dev_loss = 0.0
                with torch.no_grad():
                    for i, sample in enumerate(dev_set):
                        game_state, pi_target, v_target = sample

                        # forward
                        pi_out, v_out = Zero._net(game_state)
                        loss = Zero._net.criterion(pi_out, pi_target, v_out, v_target)

                        # record statistics
                        dev_loss += loss.item()

                end = timeit.default_timer()
                train_stats = {
                    'duration': end - start,
                    'dev_loss': dev_loss/(i * config['ai']['batch_size'])
                }
                log.info(f'dev finished', data=train_stats, tags=['experiment'])

        log.info('Regularization', data=Zero._net.criterion.regularizer.tolist())
        Zero.cooked_samples = []
