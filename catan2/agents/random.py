"""
An Agent Named Random
"""

from random import choice as random_choice, shuffle

from catan2 import log
from catan2.agents import Agent
from catan2.catan.actions import get_legal_action_ids, get_action_by_id
from catan2.catan.piece import City, Road, Settlement


class Random(Agent):
    """
    Bot that chooses a move randomly from all legal moves
    Each move possibility is considered separately
    e.g. if there are 3 legal road placements (and the player can afford a road) they will count as 3 possible moves
    """

    def choose_action(self):
        legal_action_ids = get_legal_action_ids(self.game)
        action_id = random_choice(legal_action_ids)
        action = get_action_by_id(self.game, action_id)

        return action
