"""
Functions that help deal with actions being taken in a Game

For a standard 6x6 Catan board, the actions are mapped to IDs as
0         | roll
1         | end turn
2         | buy development card
3 - 6     | play development card
7 - 78    | build road
79 - 132  | build settlement
133 - 166 | build city
167 - 206 | trade
"""

from catan2 import log
from catan2.catan.piece import City, Road, Settlement


def action(func):
    def action_wrapper(*args, **kwargs):
        player = args[0]

        log_func = log.debug if player.game.depth == 0 else log.trace
        log_func(
            data={
                'player_num': player.num,
                'player_name': player.name,
                'depth': player.game.depth,
                'function': func.__name__
            },
            tags=['actions']
        )

        func(*args, **kwargs)

        player.game.draw()

        if not player.is_cpu:
            player.game.turn_loop()

    return action_wrapper


def get_num_unique_actions(game):
    """
    On a standard Catan board, return 207
    Since I only use a standard Catan board, nobody calls this
    """
    num_roll_actions = 1
    num_end_turn_actions = 1
    num_buy_development_card_actions = 1
    num_play_development_card_actions = 4
    num_road_actions = len(game.board.lanes)
    num_settlement_actions = len(game.board.points)
    num_city_actions = len(game.board.points)
    num_trade_actions = 20
    return \
        num_roll_actions \
        + num_end_turn_actions \
        + num_buy_development_card_actions \
        + num_play_development_card_actions \
        + num_road_actions \
        + num_settlement_actions \
        + num_city_actions \
        + num_trade_actions


def find_legal_trade_actions(game):
    legal_trades = []
    resource_ids = range(0, 5)

    for from_resource_id, from_resource_amount in enumerate(game.current_player.resource_cards):
        if from_resource_amount >= 4:
            legal_trades += [(from_resource_id, to_resource_id) for to_resource_id in resource_ids if from_resource_id != to_resource_id]

    return legal_trades


def find_legal_lane_ids_for_roads(game):
    legal_lane_ids = []

    if game.current_player.can_buy_piece(Road):
        for k, lane in enumerate(game.board.lanes):
            if lane.is_reachable_by(game.current_player) and lane.piece is None:
                legal_lane_ids.append(k)

    return legal_lane_ids


def find_legal_point_ids_for_settlements(game):
    legal_point_ids = []

    if game.current_player.can_buy_piece(Settlement):
        for k, point in enumerate(game.board.points):
            if (point.is_reachable_by(game.current_player) or game.is_setup_phase()) and not point.is_crowded():
                legal_point_ids.append(k)

    return legal_point_ids


def find_legal_point_ids_for_cities(game):
    legal_point_ids = []

    if game.current_player.can_buy_piece(City):
        for k, point in enumerate(game.board.points):
            if isinstance(point.piece, Settlement) and point.owner == game.current_player:
                legal_point_ids.append(k)

    return legal_point_ids


def trade_id_to_pair(trade_id):
    from_res = trade_id // 4
    to_res = trade_id % 4

    if from_res <= to_res:
        to_res = to_res + 1 if to_res < 4 else 0

    return from_res, to_res


def trade_pair_to_id(pair):
    from_res, to_res = pair

    trade_id = from_res * 4 + to_res
    if from_res < to_res:
        trade_id -= 1

    return trade_id


def get_legal_action_ids(game):
    """Find all legal moves for the current player"""

    if game.is_finished:
        return []

    if game.can_roll():
        return [0]

    roll_start = 0
    end_turn_start = roll_start + 1
    buy_development_card_start = end_turn_start + 1
    play_development_card_start = buy_development_card_start + 1
    road_start = play_development_card_start + 4
    settlement_start = road_start + len(game.board.axial_lanes)
    city_start = settlement_start + len(game.board.axial_points)
    trade_start = city_start + len(game.board.axial_points)

    end_turn = [end_turn_start] if game.can_end_turn() else []

    # There is one buy development card action, and 4 play actions. (Five total card types, but you can't play a VP)
    buy_development_card_actions = [buy_development_card_start] if game.current_player.can_afford_development_card() else []
    play_development_card_actions = [k + play_development_card_start for (k, v) in enumerate(game.current_player.development_cards[:4]) if v > 0]

    road_actions = [k + road_start for k in find_legal_lane_ids_for_roads(game)]
    settlement_actions = [k + settlement_start for k in find_legal_point_ids_for_settlements(game)]
    city_actions = [k + city_start for k in find_legal_point_ids_for_cities(game)]
    trade_actions = [trade_pair_to_id(resource) + trade_start for resource in find_legal_trade_actions(game)]

    if game.depth == 0:
        log.trace(f'end turn: {end_turn}\n'
                  f'buy_development_card_actions: {buy_development_card_actions}\n'
                  f'play_development_card_actions: {play_development_card_actions}\n'
                  f'road_actions: {road_actions}\n'
                  f'settlement_actions: {settlement_actions}\n'
                  f'city_actions: {city_actions}\n'
                  f'trade_actions: {trade_actions}',
                  tags=['actions'])

    return\
        end_turn +\
        buy_development_card_actions +\
        play_development_card_actions +\
        road_actions +\
        settlement_actions +\
        city_actions +\
        trade_actions


def get_action_by_id(game, action_id):
    roll_start = 0
    end_turn_start = roll_start + 1
    buy_development_card_start = end_turn_start + 1
    play_development_card_start = buy_development_card_start + 1
    road_start = play_development_card_start + 4
    settlement_start = road_start + len(game.board.axial_lanes)
    city_start = settlement_start + len(game.board.axial_points)
    trade_start = city_start + len(game.board.axial_points)

    func = None
    args = []
    kwargs = {}

    if action_id == 0:
        func = game.current_player.roll

    elif action_id < buy_development_card_start:
        func = game.current_player.end_turn

    elif action_id < play_development_card_start:
        func = game.current_player.buy_development_card

    elif action_id < road_start:
        func = game.current_player.play_development_card
        args = [action_id - play_development_card_start]

    elif action_id < trade_start:
        func = game.current_player.build

        if action_id < settlement_start:
            args = (Road, game.board.lanes[action_id - road_start])
        elif action_id < city_start:
            args = (Settlement, game.board.points[action_id - settlement_start])
        else:
            args = (City, game.board.points[action_id - city_start])

    else:
        func = game.current_player.trade

        trade_id = action_id - trade_start
        args = trade_id_to_pair(trade_id)

    return func, args, kwargs
