"""
Agent superclass from which all types of Agents derive

An Agent lives outside of a game, and can play several games.
"""

from abc import ABC, abstractmethod


class Agent(ABC):
    def __init__(self, name: str = None):
        self._name = name or type(self).__name__
        self.player = None

    @property
    def name(self):
        return self._name

    @property
    def game(self):
        return self.player.game

    @abstractmethod
    def choose_action(self):
        """
        Choose an action for the agent to perform

        returns
            function
            args
            kwargs
        """
