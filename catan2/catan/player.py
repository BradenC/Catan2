"""
Class containing about a Player

A Player is the interface thru which an Agent impacts a game.

An Agent lives outside of a game and makes decisions.
A Player lives within a game and executes decisions.
"""

from __future__ import annotations
from copy import copy

import typing
if typing.TYPE_CHECKING:
    from catan2.catan.game import Game
    from catan2.agents import Agent

from catan2 import config, log
from catan2.catan.actions import action, get_action_by_id, get_legal_action_ids
from catan2.catan.board import Lane, Point
from catan2.constants import PLAYER_X, PLAYER_Y
from catan2.catan.development_card import DevelopmentCard
from catan2.catan.piece import City, Road, Settlement
from catan2.catan.resource import resources


class Player:
    def __init__(self, game: Game, agent: Agent = None, original: Player = None):
        if agent is not None:
            self._new_player(game, agent)
        elif original is not None:
            self._copy_player(game, original)
        else:
            raise Exception('Cannot create Player. You must provide either Agent or Player')

    def _copy_player(self, game, original_player):
        self.game = game
        self.resource_cards = copy(original_player.resource_cards)
        self.resource_generation = copy(original_player.resource_generation)
        self.development_cards = copy(original_player.development_cards)

        self.cities = []
        self.settlements = []
        self.roads = []
        for city in original_player.cities:
            city.copy(self)
        for settlement in original_player.settlements:
            settlement.copy(self)
        for road in original_player.roads:
            road.copy(self)

        self.turn_num = original_player.turn_num
        self._is_cpu = original_player.is_cpu
        self._name = original_player.name
        self._num = original_player.num
        self._color = original_player.color

    def _new_player(self, game, agent):
        self.game = game

        agent.player = self
        self.agent = agent
        self._name = self.agent.name
        self._is_cpu = not type(agent).__name__ == 'Human'

        self._num = None
        self._color = None

        # wood, brick, grain, sheep, ore
        self.resource_cards = [0] * 5
        self.resource_generation = [0] * 5
        self.development_cards = [0] * 5
        self.cities = []
        self.roads = []
        self.settlements = []
        self.turn_num = 0

    @property
    def color(self):
        return self._color

    @property
    def is_cpu(self):
        return self._is_cpu

    @property
    def name(self):
        return self._name

    @property
    def num(self):
        return self._num

    @num.setter
    def num(self, num):
        if self._num is not None:
            raise Exception('Cannot set num again')

        self._num = num

        if self._num == 0:
            self._color = 'purple'
        elif self._num == 1:
            self._color = 'blue'
        elif self._num == 2:
            self._color = 'maroon'
        elif self._num == 3:
            self._color = 'cyan'
        else:
            raise Exception("There aren't enough colors in the world for this many players.")

    @property
    def victory_points(self):
        return len(self.settlements) + 2*len(self.cities) + self.development_cards[4]

    @property
    def has_won(self):
        return self.victory_points >= config['game']['victory_points_to_win']

    @property
    def num_remaining_cities(self):
        return City.max_per_player - len(self.cities)

    @property
    def num_remaining_roads(self):
        return Road.max_per_player - len(self.roads)

    @property
    def num_remaining_settlements(self):
        return Settlement.max_per_player - len(self.settlements)

    @action
    def end_turn(self):
        if not self.game.can_end_turn():
            raise Exception(f'ERROR {self.name} cannot end turn')

        self.game.end_turn()

    @action
    def roll(self):
        if not self.game.can_roll():
            raise Exception(f'ERROR {self.name} cannot roll')

        self.game.roll()

    @action
    def trade(self, give_resource, receive_resource):
        if self.resource_cards[give_resource] < 4:
            raise Exception(f'ERROR {self.name} cannot trade - not enough {give_resource} to give')

        self.resource_cards[give_resource] -= 4
        self.resource_cards[receive_resource] += 1

    @action
    def build(self, piece_type, location):
        if self.can_buy_piece(piece_type) and self.can_place_piece(piece_type, location):
            self.pay_for_piece(piece_type)
            self.place_piece(piece_type, location)

    @action
    def buy_development_card(self):
        if not self.can_afford_development_card():
            raise Exception(f'ERROR {self.name} cannot afford a development card')

        for i in range(5):
            self.resource_cards[i] -= DevelopmentCard.cost[i]

        self.development_cards[self.game.development_card_deck.pop()] += 1

    @action
    def play_development_card(self, i):
        DevelopmentCard.play(self.game, self, i)

    def choose_and_do_action(self):
        if self.game.depth == 0:
            log.debug(f"It's {self.name} (p{self.num})'s ({self.turn_num})th turn", tags=['game'])

        if self.game.can_roll():
            self.roll()
            return

        legal_action_ids = get_legal_action_ids(self.game)
        if len(legal_action_ids) == 1:
            func, args, kwargs = get_action_by_id(self.game, legal_action_ids[0])
            func(*args, **kwargs)
        else:
            func, args, kwargs = self.agent.choose_action()
            func(*args, **kwargs)
        # func, args, kwargs = self.agent.choose_action()
        # func(*args, **kwargs)

    def can_afford_development_card(self):
        for i in range(5):
            if self.resource_cards[i] < DevelopmentCard.cost[i]:
                return False

        if len(self.game.development_card_deck) == 0:
            return False

        return True

    def can_buy_piece(self, piece_type):
        if piece_type.get_num_placed_by(self) >= piece_type.max_per_player:
            return False

        if self.game.is_setup_phase():
            if piece_type == Settlement and len(self.settlements) == self.turn_num:
                return True
            if piece_type == Road and len(self.roads) == len(self.settlements) - 1:
                return True
            return False

        for i in range(5):
            if self.resource_cards[i] < piece_type.cost[i]:
                return False

        if piece_type.get_num_placed_by(self) == piece_type.max_per_player:
            return False

        return True

    def pay_for_piece(self, piece_type):
        if not self.game.is_setup_phase():
            for i in range(5):
                self.resource_cards[i] -= piece_type.cost[i]

    def can_place_piece_on_point(self, piece_type, point):
        if piece_type == City:
            if self.game.is_setup_phase() or point.piece is None or point.piece.owner != self:
                return False
        elif piece_type == Settlement:
            if point.is_crowded():
                return False
            elif not self.game.is_setup_phase() and not point.is_reachable_by(self):
                return False

        return True

    def can_place_piece_on_lane(self, lane):
        return lane.is_reachable_by(self)

    def can_place_piece(self, piece_type, location):
        if isinstance(location, Point):
            return self.can_place_piece_on_point(piece_type, location)
        elif isinstance(location, Lane):
            return self.can_place_piece_on_lane(location)

    def remove_piece_from_player(self, piece):
        if not isinstance(piece, Settlement):
            log.warn(f'How in the world are you removing a {type(piece).__name__}?')

        self.settlements.remove(piece)
        self.resource_generation = [x - y for (x, y) in zip(self.resource_generation, piece.resource_generation)]

    def add_piece_to_player(self, piece):
        if isinstance(piece, Road):
            self.roads.append(piece)
            return

        if isinstance(piece, City):
            self.cities.append(piece)
        elif isinstance(piece, Settlement):
            self.settlements.append(piece)

    def place_piece(self, piece_type, location):
        piece_type(location, self)

    def draw_name_banner(self, x, y):
        if 'name_banner' in self.game.graphics:
            self.game.canvas.delete(self.game.graphics['name_banner'][0])
            self.game.canvas.delete(self.game.graphics['name_banner'][1])

        rect = self.game.canvas.create_rectangle(x, y, x + 20, y + 60, fill=self.color)
        text = self.game.canvas.create_text(x + 30, y - 16, fill="white", text=self.name, font="default 60 bold", anchor="nw")
        self.game.graphics['name_banner'] = (rect, text)

    def draw_resource_cards(self, x, y):
        y += 100
        i = 0

        if 'res_cards' not in self.game.graphics:
            self.game.graphics['res_cards'] = [None] * len(self.resource_cards)

        for res in resources:
            if res.name == 'water' or res.name == 'desert':
                continue

            if self.game.graphics['res_cards'][i]:
                self.game.canvas.delete(self.game.graphics['res_cards'][i][0])
                self.game.canvas.delete(self.game.graphics['res_cards'][i][1])

            rect = self.game.canvas.create_rectangle(x, y, x + 70, y + 100, outline=res.color, width=4)
            text = self.game.canvas.create_text(x + 35, y + 50, text=self.resource_cards[i], font="default 50", fill=res.color)

            self.game.graphics['res_cards'][i] = (rect, text)
            x += 90
            i += 1

    def draw_development_card(self, x, y, text, number):
        card = self.game.canvas.create_rectangle(x, y, x + 70, y + 40, outline='white', width=4)
        text = self.game.canvas.create_text(x - 10, y + 20, text=text, fill='white', font='default 20', anchor='e')
        number = self.game.canvas.create_text(x + 35, y + 20, text=number, fill='white', font='default 20')
        self.game.graphics['development_cards'] += [card, text, number]

    def draw_development_cards(self, x, y):
        if 'development_cards' in self.game.graphics:
            for g in self.game.graphics['development_cards']:
                self.game.canvas.delete(g)

        # draw buy card
        card = self.game.canvas.create_rectangle(x + 360, y + 250, x + 430, y + 290, outline='white', width=4)
        text = self.game.canvas.create_text(x + 395, y + 270, text='buy', font='default 20', fill='white')
        self.game.graphics['development_cards'] = [card, text]

        # draw held development cards
        card_display_names = ['build two roads', 'year of plenty', 'monopoly', 'soldier', 'vp']
        for i in range(5):
            self.draw_development_card(x + 360, y + i * 50, card_display_names[i], self.development_cards[i])

    def draw_remaining_settlements(self, x, y):
        settlement_coords = Point.calc_polygon_coords_from_x_y(x + 40, y + 15)

        text = self.game.canvas.create_text(x, y, text=self.num_remaining_settlements, font='default 20', fill='white', anchor='nw')
        shape = self.game.canvas.create_polygon(settlement_coords, fill='black', outline=self.color, width=3)
        self.game.graphics['remaining_pieces'] = [text, shape]

    def draw_remaining_cities(self, x, y):
        city_coords = Point.calc_polygon_coords_from_x_y(x + 40, y + 15)

        text = self.game.canvas.create_text(x, y, text=self.num_remaining_cities, font='default 20', fill='white', anchor='nw')
        shape = self.game.canvas.create_polygon(city_coords, fill=self.color)
        self.game.graphics['remaining_pieces'] += [text, shape]

    def draw_remaining_roads(self, x, y):
        road_coords = [
            x + 50, y + 5,
            x + 50, y + 25,
            x + 130, y + 25,
            x + 130, y + 5
        ]

        text = self.game.canvas.create_text(x, y, text=self.num_remaining_roads, font='default 20', fill='white', anchor='nw')
        shape = self.game.canvas.create_polygon(road_coords, fill=self.color)
        self.game.graphics['remaining_pieces'] += [text, shape]

    def draw_remaining_pieces(self, x, y):
        if 'remaining_pieces' in self.game.graphics:
            for g in self.game.graphics['remaining_pieces']:
                self.game.canvas.delete(g)

        self.draw_remaining_settlements(x, y + 50)
        self.draw_remaining_cities(x + 80, y + 50)
        self.draw_remaining_roads(x, y + 100)

    def draw(self):
        self.draw_name_banner(PLAYER_X, PLAYER_Y)
        self.draw_resource_cards(PLAYER_X + 38, PLAYER_Y)
        self.draw_development_cards(PLAYER_X + 38, PLAYER_Y + 220)
        self.draw_remaining_pieces(PLAYER_X + 38, PLAYER_Y + 375)

    def stringify_stats(self):
        roads = len(self.roads)
        settlements = len(self.settlements)
        cities = len(self.cities)

        stat_string = f"""\
| Name: {self.name}
| Victory Points: {self.victory_points}
| Roads: {roads}
| Settlements: {settlements}
| Cities: {cities}
| Resource Cards: {self.resource_cards}
| Development Cards: {[]}
"""
        return stat_string

    def to_dict(self):
        return {
            'name': self.name,
            'num': self.num,
            'agent_type': type(self.agent).__name__,
            'victory_points': self.victory_points,
            'num_roads': len(self.roads),
            'num_settlements': len(self.settlements),
            'num_cities': len(self.cities),
            'resource_cards': self.resource_cards,
            'development_cards': self.development_cards
        }

    def copy(self, game):
        return Player(game=game, original=self)
