"""
Pieces are things that go on the Board

Piece constructors automatically create all links
- double link with Location on Board
- double link with Player

You probably shouldn't to save the result of the constructor
"""
from __future__ import annotations

import typing
if typing.TYPE_CHECKING:
    from catan2.catan.board import BoardPart, Lane, Point
    from catan2.catan.player import Player

from abc import ABC, abstractmethod


class Piece(ABC):
    max_per_player = None
    cost = None

    def __init__(self, location: BoardPart, owner: Player):
        self._owner = owner
        self._location = location
        location.piece = self

    @property
    def location(self):
        return self._location

    @property
    def owner(self):
        return self._owner

    @abstractmethod
    def copy(self, player):
        pass


class Road(Piece):
    max_per_player = 15
    cost = [1, 1, 0, 0, 0]

    def __init__(self, location: Lane = None, owner: Player = None, original: Road = None):
        if location is not None and owner is not None:
            self._new_road(location, owner)
        elif original is not None:
            self._copy_road(original, owner)

    def _new_road(self, location, owner):
        super().__init__(location, owner)
        owner.roads.append(self)

    def _copy_road(self, original: Road, copied_player: Player):
        copied_lane = copied_player.game.board.get_lane(original.lane.points[0].q, original.lane.points[0].r, original.lane.points[1].q, original.lane.points[1].r)
        self._new_road(copied_lane, copied_player)

    @staticmethod
    def get_num_placed_by(player):
        return len(player.roads)

    @property
    def lane(self):
        return self._location

    @lane.setter
    def lane(self, lane):
        self._location = lane

    def copy(self, copied_player):
        Road(original=self, owner=copied_player)


class Building(Piece, ABC):
    resource_collection = None

    def __init__(self, location: Point = None, owner: Player = None, original: Building = None):
        if location is not None and owner is not None:
            self._new_building(location, owner)
        elif original is not None:
            self._copy_building(original, owner)
        else:
            raise Exception('Cannot create Building. You must provide either Location or Building')

    def _new_building(self, location, owner):
        super().__init__(location, owner)
        owner.resource_generation = [x + y for (x, y) in zip(owner.resource_generation, self.point.resource_generation)]

    def _copy_building(self, original, copied_player):
        copied_point = copied_player.game.board.axial_points[(original.point.q, original.point.r)]
        self._new_building(copied_point, copied_player)

    @property
    def point(self):
        return self._location

    @point.setter
    def point(self, point):
        self._location = point

    def copy(self, copied_player):
        type(self)(original=self, owner=copied_player)


class Settlement(Building):
    max_per_player = 5
    cost = [1, 1, 1, 1, 0]
    resource_collection_rate = 1

    def __init__(self, location: Point = None, owner: Player = None, original: Settlement = None):
        super().__init__(location, owner, original)
        owner.settlements.append(self)

    @staticmethod
    def get_num_placed_by(player):
        return len(player.settlements)


class City(Building):
    max_per_player = 4
    cost = [0, 0, 0, 2, 3]
    resource_collection_rate = 2

    def __init__(self, location: Point = None, owner: Player = None, original: City = None):
        if location is not None and location.piece:
            owner.settlements.remove(location.piece)
        super().__init__(location, owner, original)
        owner.cities.append(self)

    @staticmethod
    def get_num_placed_by(player):
        return len(player.cities)

    def copy(self, copied_player):
        super().copy(copied_player)
        # Normally building a city assumes going +1 from an existing settlement.
        # Copies, however, do replace an existing settlement.
        # So we need to +1 again to get to the +2.
        copied_player.resource_generation = [x + y for (x, y) in zip(copied_player.resource_generation, self.point.resource_generation)]
