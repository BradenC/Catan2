"""
Monte Carlo Tree Search

Look it up
"""
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, wait
import timeit
import numpy as np
import torch
import typing

from catan2 import config, log
from catan2.catan.actions import get_action_by_id, get_legal_action_ids

from .gamestate import GameState

NUM_UNIQUE_ACTIONS = 207


class MCTNode:
    # executor = ProcessPoolExecutor(max_workers=6)
    # executor = ThreadPoolExecutor(max_workers=6)

    def __init__(self, game, net, action_id=None, parent=None):
        log.trace(f"id: {id(self)}", tags=['mcts'])
        self.game = game.copy()

        self.w = 0  # total q value
        self.n = 0  # number of visits

        self.action_id = action_id
        self.parent = parent
        self.original_priors = None
        self.legal_action_ids = get_legal_action_ids(self.game)
        self.priors = None
        self.children = [0] * NUM_UNIQUE_ACTIONS

        self.expansion = None

        if action_id is not None:
            func, args, kwargs = get_action_by_id(self.game, action_id)
            func(*args, **kwargs)

        # If the new game state leaves a player with exactly 1 move, automatically take that move
        self.legal_action_ids = get_legal_action_ids(self.game)
        while len(self.legal_action_ids) == 1:
            func, args, kwargs = get_action_by_id(self.game, self.legal_action_ids[0])
            func(*args, **kwargs)

            self.legal_action_ids = get_legal_action_ids(self.game)

        if self.game.is_finished:
            return

        if config['ai']['zero']['mcts']['parallel']:
            self.expansion = self.executor.submit(self.expand)
            self.expansion.node = self
            self.expansion.add_done_callback(MCTNode.backup_from_future)
        else:
            self.expand(net)
            self.backup()

    @property
    def q(self):
        if self.game.is_finished:
            return 1
        else:
            n = self.n or 1
            return self.w / n

    @property
    def pi(self):
        pi = np.asarray([0 if not isinstance(s, MCTNode) else s.n for s in self.children])
        pi_sum = np.sum(pi)
        if pi_sum > 0:
            pi = pi/pi_sum

        return pi

    def calc_u_for_child(self, i):
        if self.priors[i] == 0:
            return float("-inf")

        s = self.children[i]
        c_puct = config['ai']['zero']['mcts']['c_puct']

        if isinstance(s, MCTNode):
            # if s.expansion is not None and s.expansion.running():
            #     expanding.append(s)
            #     continue
            q = s.q if s.game.current_player.num == self.game.current_player.num else -s.q
            return q + c_puct * self.priors[i] * np.sqrt(self.n) / (1 + s.n)
        else:
            return self.q + c_puct * self.priors[i] * np.sqrt(self.n)

    def favorite_child(self, net):
        log.trace(f'node id: {id(self)}', tags=['mcts'])

        expanding = []

        us = [self.calc_u_for_child(i) for i in range(NUM_UNIQUE_ACTIONS)]
        best_a = np.argmax(us)

        if us[best_a] == float("-inf"):
            if len(expanding) > 0:
                log.trace("Favorite child is already expanding. Waiting...", tags=['mcts'])
                node = np.random.choice(expanding)
                wait([node.expansion])
                return node
            else:
                log.error("No legal moves detected", data={
                    "player_num": self.game.player.num,
                    "original_priors": self.original_priors.data.numpy().tolist(),
                    "legal_actions": get_legal_action_ids(self.game),
                    "priors": self.priors.data.numpy().tolist()
                })
                raise Exception(f"No legal moves for player {self.game.player.name}")

        a = best_a

        if not isinstance(self.children[a], MCTNode):
            log.trace("Favorite child is new", tags=['mcts'])
            self.children[a] = MCTNode(self.game, net, a, parent=self)
        else:
            log.trace("Favorite child is already expanded", tags=['mcts'])

        return self.children[a]

    def expand(self, net):
        log.trace(f'node id: {id(self)}', tags=['mcts'])
        MCT.expand_count += 1

        with torch.no_grad():
            child_priors, value_estimate = net(GameState(self.game).tensor)

        self.priors = child_priors.view(-1).cpu()
        self.original_priors = self.priors.clone()
        self.w = value_estimate.item()

        if self.parent is None:
            self.add_dirichlet_noise()

        masked_priors = torch.zeros(207)
        masked_priors[self.legal_action_ids] = self.priors[self.legal_action_ids]
        self.priors = masked_priors

        self.priors /= self.priors.sum()

    def add_dirichlet_noise(self):
        eps = config['ai']['zero']['dirichlet']['epsilon']

        alphas = (np.ones(NUM_UNIQUE_ACTIONS,) * config['ai']['zero']['dirichlet']['alpha'])
        noise = torch.from_numpy(np.random.default_rng().dirichlet(alphas))

        torch.add(self.priors * (1 - eps), noise * eps, out=self.priors)

    def backup(self):
        log.trace(f'node id: {id(self)}', tags=['mcts'])

        val = self.q
        current = self

        while current.parent is not None:
            if current.game.current_player.num != current.parent.game.current_player.num:
                val *= -1

            current = current.parent
            current.w += val

    @staticmethod
    def backup_from_future(fut):
        fut.node.backup()

    @staticmethod
    def stringify_tensor(t):
        ret = ''
        for i in range(np.shape(t)[2]):
            ret += f'{t[:,:,i]}\n'

        return ret

    def log(self):
        # s = GameState(self.game)
        # s_ = self.stringify_tensor(s.get_board_tensor())
        # s_p = self.stringify_tensor(s.get_piece_tensor())
        # s_r = self.stringify_tensor(s.get_resource_card_tensor())
        # s_d = self.stringify_tensor(s.get_development_card_tensor())

        log.debug(f'''\
parent id: {id(self.parent)}
self id: {id(self)}
depth: {self.game.depth}
action id: {self.action_id}
player: {self.game.current_player.name} (p{self.game.current_player.num})
victory points: {self.game.current_player.victory_points}
cards: {self.game.current_player.resource_cards}
legal action ids: {self.legal_action_ids}

q: {self.q}
n: {self.n}

a, n, p, q, u:
{
        np.asarray([
            (
                i,
                s.n,
                self.priors[i].item(),
                s.q if s.game.current_player.num == self.game.current_player.num else -s.q,
                (s.q if s.game.current_player.num == self.game.current_player.num else -s.q) + config['ai']['zero']['mcts']['c_puct'] * self.priors[i].item() * np.sqrt(self.n) / (1 + s.n)
            )
                for i, s in enumerate(self.children) if isinstance(s, MCTNode)
        ])
}

original_priors:
{self.original_priors}

priors:
{self.priors}
''')

# pieces:
# {s_p}
#
# resource cards:
# {s_r}
#
# development_cards:
# {s_d}

        for node in self.children:
            if isinstance(node, MCTNode):
                node.log()
        log.debug('up')


class MCT:
    expand_count = 0

    def __init__(self):
        self.root = None

    def search(self, game, net, num_iterations=None):
        # Reset search stats
        MCT.expand_count = 0

        # Start the timer
        start = timeit.default_timer()

        # Search
        self.root = MCTNode(game, net)
        self.root.n = 1
        if config['ai']['zero']['mcts']['parallel']:
            wait([self.root.expansion])

        for i in range(num_iterations-1):
            log.trace(f'Return to root - iteration {i}', tags=['mcts'])

            current = self.root
            current.n += 1

            while current.n > 1:
                current = current.favorite_child(net)
                current.n += 1

                if current.game.is_finished:
                    current.backup()
                    break

        # Stop the timer
        end = timeit.default_timer()

        # Log
        self.log(duration=end-start)

        return self.pi

    @property
    def pi(self):
        return self.root.pi

    def log(self, duration):
        if config['logging']['categories']['mcts']:
            np.set_printoptions(linewidth=120, suppress=True, precision=8)
            torch.set_printoptions(linewidth=120, precision=8, profile='full')
            log.debug(f'Search Complete\n'
                      f'Player: {self.root.game.current_player.name} (p{self.root.game.current_player.num})\n'
                      f'Duration: {duration}s\n'
                      f'Expand Count: {MCT.expand_count}\n'
                      f'Duration/Expand: {duration / MCT.expand_count}')
            self.root.log()
