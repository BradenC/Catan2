"""
Class containing information about the layout of the Catan Board
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from math import ceil, floor, sqrt
from random import shuffle

import typing
if typing.TYPE_CHECKING:
    from catan2.catan.game import Game

from catan2 import log
from catan2.constants import BOARD_WIDTH
from catan2.catan.resource import HexNumbers, HexTiles, Resource
from catan2.catan.piece import City, Road, Settlement

CELL_SIZE_X = 150
CELL_SIZE_Y = 135

HEX_SIDE_LENGTH = 80
HEX_WIDTH = sqrt(3) * HEX_SIDE_LENGTH
HEX_HEIGHT = 2 * HEX_SIDE_LENGTH
HEX_TIP_HEIGHT = HEX_SIDE_LENGTH / 2
HEX_TOKEN_WIDTH = HEX_SIDE_LENGTH / 2

LANE_WIDTH = CELL_SIZE_X - HEX_WIDTH
LANE_LENGTH = HEX_SIDE_LENGTH

MAP_OFFSET_X = 40
MAP_OFFSET_Y = 80


class BoardPart(ABC):
    def __init__(self):
        self.piece = None
        self.q = None
        self.r = None

    @property
    def owner(self):
        if self.piece:
            if self.piece.location != self:
                raise Exception('piece location is not where it should be')
            return self.piece.owner
        else:
            return None

    @property
    @abstractmethod
    def color(self):
        pass

    @abstractmethod
    def on_click(self, event):
        pass

    @abstractmethod
    def draw(self):
        pass


class Hex(BoardPart):
    roll_chance_arr = [0, 0, 1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1]

    def __init__(self, board, q, r, resource, num):
        self.board = board

        self.resource = Resource(name=resource)
        self.num = num
        self.roll_chance = Hex.roll_chance_arr[self.num]

        self.q = q
        self.r = r

        self._points = []
        self.polygon_coords = self.calc_polygon_coords()
        self.token_coords = self.calc_token_coords()

        self.graphics = []

    def stringify(self):
        return f"({self.q}, {self.r}) - {self.num:02} - {self.resource.name}"

    @property
    def color(self):
        return self.resource.color

    @property
    def points(self):
        return self._points

    def make_point(self, q, r):
        point = self.board.assert_point(q, r)
        self._points.append(point)
        point.add_hex(self)

    def make_points(self):
        self.make_point((3 * self.q) + 1, (3 * self.r) - 2)  # N
        self.make_point((3 * self.q) + 2, (3 * self.r) - 1)  # NE
        self.make_point((3 * self.q) + 1, (3 * self.r) + 1)  # SE
        self.make_point((3 * self.q) - 1, (3 * self.r) + 2)  # S
        self.make_point((3 * self.q) - 2, (3 * self.r) + 1)  # SW
        self.make_point((3 * self.q) - 1, (3 * self.r) - 1)  # NW

    def make_lanes(self):
        Lane.from_points(self.points[0], self.points[1])
        Lane.from_points(self.points[1], self.points[2])
        Lane.from_points(self.points[2], self.points[3])
        Lane.from_points(self.points[3], self.points[4])
        Lane.from_points(self.points[4], self.points[5])
        Lane.from_points(self.points[5], self.points[0])

    def calc_polygon_coords(self):
        _x = MAP_OFFSET_X + CELL_SIZE_X * (self.q + self.r / 2)
        _y = MAP_OFFSET_Y + CELL_SIZE_Y * self.r

        return [
            _x, _y,
            _x + HEX_WIDTH / 2, _y + HEX_TIP_HEIGHT,
            _x + HEX_WIDTH / 2, _y + HEX_TIP_HEIGHT + HEX_SIDE_LENGTH,
            _x, _y + HEX_HEIGHT,
            _x - HEX_WIDTH / 2, _y + HEX_TIP_HEIGHT + HEX_SIDE_LENGTH,
            _x - HEX_WIDTH / 2, _y + HEX_TIP_HEIGHT,
        ]

    def calc_token_coords(self):
        _x = MAP_OFFSET_X + CELL_SIZE_X * (self.q + self.r / 2)
        _y = MAP_OFFSET_Y + CELL_SIZE_Y * self.r + HEX_SIDE_LENGTH - HEX_TOKEN_WIDTH / 2

        return [
            _x - HEX_TOKEN_WIDTH/2, _y,
            _x + HEX_TOKEN_WIDTH/2, _y + HEX_TOKEN_WIDTH
        ], [
            _x, _y + HEX_TOKEN_WIDTH/2
        ]

    def give_resources(self):
        for point in self.points:
            if point.piece:
                point.owner.resource_cards[self.resource.id] += point.piece.resource_collection_rate

    def on_click(self, event):
        pass

    def draw_hex(self):
        h = self.board.game.canvas.create_polygon(self.polygon_coords, fill=self.color)
        self.board.game.canvas.tag_bind(h, '<Button-1>', self.on_click)

        self.graphics.append(h)

    def draw_token(self):
        if self.resource.name == 'desert':
            return

        oval_points, text_points = self.token_coords

        oval = self.board.game.canvas.create_oval(oval_points, fill="#FFF")
        text = self.board.game.canvas.create_text(text_points, font="Times 14", text=self.num)

        self.board.game.canvas.tag_bind(oval, '<Button-1>', self.on_click)
        self.board.game.canvas.tag_bind(text, '<Button-1>', self.on_click)

        self.graphics.append(oval)
        self.graphics.append(text)

    def draw(self):
        for g in self.graphics:
            self.board.game.canvas.delete(g)

        self.graphics = []

        self.draw_hex()
        self.draw_token()


class Lane(BoardPart):
    def __init__(self, board, points):
        self.board = board

        self.piece = None

        self._color = "#111"
        self.graphics = None

        self.points = points
        self.polygon_coords = self.calc_polygon_coords()

    @property
    def color(self):
        if self.owner:
            return self.owner.color
        else:
            return self._color

    def calc_polygon_coords(self):
        if abs(self.points[0].r - self.points[1].r) == 2:  # |
            q = max(self.points[0].q, self.points[1].q)
            r = min(self.points[0].r, self.points[1].r)

            _x = MAP_OFFSET_X + CELL_SIZE_X * q / 3 - LANE_WIDTH / 2 + CELL_SIZE_X * r / 6
            _y = MAP_OFFSET_Y + CELL_SIZE_Y * r / 3 + LANE_LENGTH

            return [
                _x, _y,
                _x + LANE_WIDTH, _y,
                _x + LANE_WIDTH, _y + LANE_LENGTH,
                _x, _y + LANE_LENGTH
            ]
        elif abs(self.points[0].q - self.points[1].q) == 1:  # \
            q = min(self.points[0].q, self.points[1].q)
            r = min(self.points[0].r, self.points[1].r)

            _x = MAP_OFFSET_X + CELL_SIZE_X * q / 3 + CELL_SIZE_X * r / 6
            _y = MAP_OFFSET_Y + CELL_SIZE_Y * r / 3 + LANE_LENGTH + LANE_WIDTH * sqrt(3)/2 - 3

            return [
                _x,                                            _y,
                _x + LANE_WIDTH / 2,                           _y - LANE_WIDTH * sqrt(3)/2,
                _x + LANE_WIDTH / 2 + LANE_LENGTH * sqrt(3)/2, _y - LANE_WIDTH * sqrt(3)/2 + LANE_LENGTH / 2,
                _x + LANE_LENGTH * sqrt(3)/2,                  _y + LANE_LENGTH / 2
            ]
        elif abs(self.points[0].q - self.points[1].q) == 2:  # /
            q = max(self.points[0].q, self.points[1].q)
            r = min(self.points[0].r, self.points[1].r)

            _x = MAP_OFFSET_X + CELL_SIZE_X * q / 3 + CELL_SIZE_X * r / 6
            _y = MAP_OFFSET_Y + CELL_SIZE_Y * r / 3 + LANE_LENGTH + LANE_WIDTH * sqrt(3)/2 - 3

            return [
                _x,                                            _y,
                _x - LANE_WIDTH / 2,                           _y - LANE_WIDTH * sqrt(3)/2,
                _x - LANE_WIDTH / 2 - LANE_LENGTH - sqrt(3)/2, _y - LANE_WIDTH * sqrt(3)/2 + LANE_LENGTH / 2 + 6,
                _x - LANE_LENGTH * sqrt(3)/2,                  _y + LANE_LENGTH / 2 + 4
            ]
        raise Exception(f"Points {self.points[0].stringify()} and {self.points[1].stringify()} are not a valid line.")

    @staticmethod
    def from_points(p1, p2):
        board = p1.board
        return board.assert_lane(p1.q, p1.r, p2.q, p2.r)

    def is_reachable_by(self, player):
        if self.board.game.is_setup_phase():
            return any(point.piece is not None and point.piece == self.board.game.current_player.settlements[-1] for point in self.points)

        return self.points[0].is_reachable_by(player) or self.points[1].is_reachable_by(player)

    def on_click(self, event):
        if not (self.is_reachable_by(self.board.game.current_player)):
            return

        self.board.game.current_player.build(Road, self)

        self.board.game.draw()

    def draw(self):
        if self.graphics:
            self.board.game.canvas.delete(self.graphics)

        lane = self.board.game.canvas.create_polygon(self.polygon_coords, fill=self.color)

        if not self.piece:
            self.board.game.canvas.tag_bind(lane, '<Button-1>', self.on_click)

        self.graphics = lane


class Point(BoardPart):
    def __init__(self, board, q, r):
        self.board = board
        self.q = q
        self.r = r

        self.lanes = []
        self.hexes = []

        self.piece = None
        self.resource_generation = [0] * 5
        self._color = "#111"

        self.graphics = None

        self.polygon_coords = self.calc_polygon_coords()

    @property
    def color(self):
        if self.owner:
            return self.owner.color
        else:
            return self._color

    @staticmethod
    def calc_polygon_coords_from_x_y(x, y):
        # points are drawn as little hexes, with the following side_length, width, height
        s = LANE_WIDTH
        w = s * sqrt(3)
        h = s * 2

        return [
            x, y - h/2,
            x + w/2, y - h/4,
            x + w/2, y + h/4,
            x, y + h/2,
            x - w/2, y + h/4,
            x - w/2, y - h/4
        ]

    def calc_polygon_coords(self):
        _x = MAP_OFFSET_X + CELL_SIZE_X * self.q / 3 + CELL_SIZE_X * self.r / 6
        _y = MAP_OFFSET_Y + CELL_SIZE_Y * self.r / 3 + HEX_SIDE_LENGTH - 1

        return Point.calc_polygon_coords_from_x_y(_x, _y)

    def add_hex(self, h):
        if len(self.hexes) == 3:
            log.critical(message='Point attempted to connect with >4 hexes.')
        if h.num:
            self.resource_generation[h.resource.id] += h.roll_chance

        self.hexes.append(h)

    def is_crowded(self):
        for lane in self.lanes:
            for point in lane.points:
                if point.piece:
                    return True

        return False

    def is_reachable_by(self, player):
        if self.piece and self.piece.owner == player:
            return True

        for lane in self.lanes:
            if lane.piece and lane.piece.owner == player:
                return True

        return False

    def on_click(self, event):
        if not self.piece:
            self.board.game.current_player.build(Settlement, self)
        elif isinstance(self.piece, Settlement):
            self.board.game.current_player.build(City, self)

    def stringify(self):
        return F"({self.q}, {self.r})"

    def draw(self):
        if self.graphics:
            self.board.game.canvas.delete(self.graphics)

        if self.piece:
            if isinstance(self.piece, Settlement):
                self.graphics = self.board.game.canvas.create_polygon(self.polygon_coords, fill='black', outline=self.piece.owner.color, width=5)
            elif isinstance(self.piece, City):
                self.graphics = self.board.game.canvas.create_polygon(self.polygon_coords, fill=self.piece.owner.color)
        else:
            self.graphics = self.board.game.canvas.create_polygon(self.polygon_coords, fill=self._color)
            self.board.game.canvas.tag_bind(self.graphics, '<Button-1>', self.on_click)


class Board:
    def __init__(self, game: Game, random: bool = False, width: int = BOARD_WIDTH):
        self.game = game
        self.width = width

        self.axial_hexes = [[None] * self.width for _ in range(self.width)]
        self.axial_points = {}
        self.axial_lanes = {}

        self.hexes = []
        self.points = []
        self.lanes = []

        self.make_hexes(random)
        self.make_points()
        self.make_lanes()

    @property
    def min_coordinate_sum(self):
        return int(self.width / 2)

    @property
    def max_coordinate_sum(self):
        return int((self.width * 2) - self.min_coordinate_sum - 2)

    def make_hexes(self, random):
        resource_tiles = HexTiles.copy()
        number_tokens = HexNumbers.copy()

        if random:
            shuffle(resource_tiles)
            shuffle(number_tokens)

        for r in range(self.width):
            for q in range(self.width):
                if self.min_coordinate_sum <= q + r <= self.max_coordinate_sum:
                    h = Hex(self, q, r, resource_tiles.pop(), number_tokens.pop())
                    self.axial_hexes[q][r] = h
                    self.hexes.append(h)

    def assert_point(self, q, r):
        if (q, r) not in self.axial_points:
            point = Point(self, q, r)
            self.axial_points[(q, r)] = point
            self.points.append(point)
        return self.axial_points[(q, r)]

    def make_points(self):
        for h in self.hexes:
            h.make_points()

    def get_lane(self, q1, r1, q2, r2):
        return self.axial_lanes.get(((q1, r1), (q2, r2))) or self.axial_lanes.get(((q2, r2), (q1, r1))) or None

    def assert_lane(self, q1, r1, q2, r2):
        lane = self.get_lane(q1, r1, q2, r2)

        if lane is None:
            p1 = self.axial_points[(q1, r1)]
            p2 = self.axial_points[(q2, r2)]
            lane = Lane(self, [p1, p2])
            p1.lanes.append(lane)
            p2.lanes.append(lane)
            self.axial_lanes[((q1, r1), (q2, r2))] = lane
            self.lanes.append(lane)

        return lane

    def make_lanes(self):
        for h in self.hexes:
            h.make_lanes()

    def give_resources(self, roll):
        for h in self.hexes:
            if h.num == roll:
                h.give_resources()

    def draw_hexes(self):
        for h in self.hexes:
            h.draw()

    def draw_points(self):
        for k, point in self.axial_points.items():
            point.draw()

    def draw_lanes(self):
        for k, lane in self.axial_lanes.items():
            lane.draw()

    def draw(self):
        self.draw_hexes()
        self.draw_lanes()
        self.draw_points()

    # TODO make this work for random boards
    def copy(self, game):
        b = Board(game)
        return b
