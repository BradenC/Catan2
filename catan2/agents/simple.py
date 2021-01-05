"""
An Agent Named Simple
"""

from random import shuffle

from catan2.agents import Agent
from catan2.catan.actions import\
    find_legal_lane_ids_for_roads,\
    find_legal_point_ids_for_settlements,\
    find_legal_point_ids_for_cities
from catan2.catan.piece import Building, City, Road, Settlement


class Simple(Agent):
    """
    Simple chooses a move based on a basic priority over all legal moves
    Also sorts legal trades, so it's _slightly_ better than BasicBot
    """

    def choose_action(self):
        if self.game.can_roll():
            return self.player.roll, [], {}

        legal_points_for_cities = [self.game.board.points[k] for k in find_legal_point_ids_for_cities(self.game)]
        if self.player.can_buy_piece(City) and len(self.player.settlements) > 0:
            shuffle(legal_points_for_cities)
            return self.player.build, [City, best_point(self.player, legal_points_for_cities)], {}

        legal_points_for_settlements = [self.game.board.points[k] for k in find_legal_point_ids_for_settlements(self.game)]
        if self.player.can_buy_piece(Settlement) and len(legal_points_for_settlements) > 0:
            shuffle(legal_points_for_settlements)
            return self.player.build, [Settlement, best_point(self.player, legal_points_for_settlements)], {}

        legal_lanes_for_roads = [self.game.board.lanes[k] for k in find_legal_lane_ids_for_roads(self.game)]
        if self.player.can_buy_piece(Road) and len(legal_lanes_for_roads) > 0:
            shuffle(legal_lanes_for_roads)
            return self.player.build, [Road, legal_lanes_for_roads[0]], {}

        if min(self.player.resource_cards) == 0 and max(self.player.resource_cards) >= 4:
            return self.player.trade, find_best_trade_actions(self.player), {}

        if self.game.can_end_turn():
            return self.player.end_turn, [], {}


def best_point(player, points):
    return max([(point, calc_point_value(player, point)) for point in points], key=lambda x: x[1])[0]


def calc_point_value(player, point):
    res_gen_player_current = [res + 1 for res in player.resource_generation]
    res_gen_point_discounted = [a/b for (a, b) in zip(point.resource_generation, res_gen_player_current)]

    return sum(res_gen_point_discounted)


def find_best_trade_actions(player):
    resources_to_give = [key for (key, val) in enumerate(player.resource_cards) if val >= 4]
    resources_to_receive = [key for (key, val) in enumerate(player.resource_cards) if val == 0]

    return resources_to_give[0], resources_to_receive[0]
