import tkinter

from catan2 import config
from catan2.agents import get_agent_for_player_name
from catan2.catan import Game


def play(canvas: tkinter.Canvas = None):
    agents = [get_agent_for_player_name(player_name) for player_name in config['game']['player_names']]
    Game(agents=agents, canvas=canvas).start()
