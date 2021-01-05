"""
An Agent Named Human
"""

from catan2.agents import Agent


class Human(Agent):
    """
    Human agent does not do much of anything.
    Instead the game hangs and allows a real human to take actions.
    """
    def __init__(self, name: str = None):
        super().__init__(name)

    def choose_action(self):
        """
        No-op for the computer. The actual human has to choose!
        """
