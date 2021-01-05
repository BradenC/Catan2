from .agent import Agent
from .basic import Basic
from .human import Human
from .random import Random
from .simple import Simple
from .zero.zero import Zero


def get_agent_for_player_name(player_name):
    if player_name.lower() == 'basic':
        return Basic(player_name)
    elif player_name.lower() == 'random':
        return Random(player_name)
    elif player_name.lower() == 'simple':
        return Simple(player_name)
    if player_name.lower() == 'zero':
        return Zero(player_name)
    else:
        return Human(player_name)
