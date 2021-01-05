from tqdm import tqdm

from catan2 import log
from catan2.catan.game import Game
from catan2.agents import Agent


def count_wins(game_results, player_name):
    return sum([1 if game['winner'] == player_name else 0 for game in game_results])


def win_ratio(game_results, player_name):
    return count_wins(game_results, player_name) / len(game_results)


def vs(agents: [Agent], num_games: int = 1):
    game_results = []

    for _ in tqdm(range(num_games)):
        game = Game(agents)
        game.start()

        game_results.append(game.to_dict())

    log.info(
        message=f'Player {agents[0].name} won {count_wins(game_results, agents[0].name)}/{num_games} games against {agents[1].name}',
        tags=['experiment']
    )

    return game_results
