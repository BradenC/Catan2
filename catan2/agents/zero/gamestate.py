"""
Game State

Copy the description of the current state of a game into a portable format.
This format can be easily copied, or turned into a tensor.
"""

import numpy as np
import torch

from .device import device


class GameState:
    _board_tensor = None  # The board doesn't change during the game, so only compute it once

    num_layers = {
        'board': 5,
        'pieces': 6,
        'resource_cards': 10,
        'development_cards': 10
    }

    def __init__(self, game):
        self.game = game

        board_tensor = self.get_board_tensor()
        piece_tensor = self.get_piece_tensor()
        resource_card_tensor = self.get_resource_card_tensor()
        development_card_tensor = self.get_development_card_tensor()

        complete_game_tensor = np.concatenate((
            board_tensor,
            piece_tensor,
            resource_card_tensor,
            development_card_tensor
        ), axis=0)

        self._t = torch.as_tensor(complete_game_tensor, device=device)

    @property
    def tensor(self):
        return self._t

    @staticmethod
    def get_player_list_with_current_player_first(game):
        player_list = game.players.copy()
        i = player_list.index(game.current_player)
        player_list[0], player_list[i] = player_list[i], player_list[0]

        return player_list

    def get_board_tensor(self):
        if GameState._board_tensor is None:
            GameState._board_tensor = self.tensorify_board()

        return GameState._board_tensor

    def tensorify_board(self):
        board = self.game.board
        num_layers = GameState.num_layers['board']
        t = np.zeros((num_layers, board.width, board.width), dtype=int)

        for h in self.game.board.hexes:
            if h.resource.id > 4: continue
            t[h.resource.id][h.q][h.r] = h.roll_chance

        return t

    def get_piece_tensor(self):
        board = self.game.board
        num_layers = GameState.num_layers['pieces']
        t = np.zeros((num_layers, board.width, board.width), dtype=int)

        for p, player in enumerate(self.get_player_list_with_current_player_first(self.game)):
            for road in player.roads:
                for point in road.lane.points:
                    for h in point.hexes:
                        t[h.q][h.r][p*3] = 1
            for settlement in player.settlements:
                for h in settlement.point.hexes:
                    t[p*3 + 1][h.q][h.r] = 1
            for city in player.cities:
                for h in city.point.hexes:
                    t[p*3 + 1][h.q][h.r] = 1

        return t

    def get_resource_card_tensor(self):
        board = self.game.board
        num_layers = GameState.num_layers['resource_cards']
        t = np.zeros((num_layers, board.width, board.width), dtype=int)

        for p, player in enumerate(self.get_player_list_with_current_player_first(self.game)):
            for i, amt in enumerate(player.resource_cards):
                t[(p*5 + i), :, :] = amt

        return t

    def get_development_card_tensor(self):
        board = self.game.board
        num_layers = GameState.num_layers['development_cards']
        t = np.zeros((num_layers, board.width, board.width), dtype=int)

        for p, player in enumerate(self.get_player_list_with_current_player_first(self.game)):
            for d, amt in enumerate(player.development_cards):
                t[(p * 5 + d), :, :] = amt

        return t
