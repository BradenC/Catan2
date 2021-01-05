"""
Game logic
"""

from copy import copy
from random import randint, seed, shuffle
from tkinter import Canvas
from time import sleep, time

from catan2.agents import Agent
from catan2 import config, log

from catan2.catan.player import Player
from catan2.catan.board import Board
from catan2.constants import DICE_WIDTH, END_TURN_X, END_TURN_Y, ROLL_X, ROLL_Y
from catan2.catan.development_card import development_cards


# Generator that answers the question "whose turn is it anyway?"
def player_loop(players):
    i = 0

    # Setup phase
    while i < len(players):
        yield players[i]
        i += 1

    i -= 1
    while i >= 0:
        yield players[i]
        i -= 1

    # Regular play
    while True:
        if i < len(players) - 1:
            i += 1
        else:
            i = 0

        yield players[i]


def shuffle_players(players):
    shuffle(players)
    for i, player in enumerate(players):
        player.num = i


class Game:
    def __init__(self, agents: [Agent] = None, is_random: bool = False, canvas: Canvas = None, turn_delay_s: float = None):
        if agents is None:
            return

        if config['game']['seed']:
            seed(config['game']['seed'])

        self.board = Board(self, is_random)
        self.depth = 0
        self.development_card_deck = copy(development_cards)
        shuffle(self.development_card_deck)
        self.last_roll = (None, None)
        self.turn_num = 0
        self.winner = None
        self._current_player_num = 0

        if agents:
            self.players = [Player(self, agent) for agent in agents]
            shuffle_players(self.players)

            self.player_loop = player_loop(self.players)
            self.current_player = next(self.player_loop)

        self.canvas = canvas
        if self.canvas is not None:
            self.canvas.delete("all")
            self.graphics = {}
            self.turn_delay_s = turn_delay_s or config['graphics']['turn_delay_s']

        self.start_time = self.end_time = None

    @property
    def current_player(self):
        return self.players[self._current_player_num]

    @current_player.setter
    def current_player(self, player):
        self._current_player_num = player.num

    def start(self):
        self.start_time = time()
        self.turn_loop()
        self.end_time = time()
        self.finish()
        return self

    def turn_loop(self):
        while self.current_player.is_cpu and not self.is_finished:
            if self.canvas:
                sleep(self.turn_delay_s)
            self.current_player.choose_and_do_action()

    def is_setup_phase(self):
        return self.turn_num < len(self.players) * 2

    @property
    def duration(self):
        return self.end_time - self.start_time

    @property
    def is_finished(self):
        for player in self.players:
            if player.victory_points >= config['game']['victory_points_to_win']:
                return True

        return False

    def clear_dice(self):
        self.last_roll = (None, None)

    def can_roll(self):
        if self.is_setup_phase():
            return False

        if self.last_roll[0]:
            return False

        return True

    def roll(self):
        d1 = randint(1, 6)
        d2 = randint(1, 6)
        self.last_roll = (d1, d2)

        self.board.give_resources(d1 + d2)

    def can_end_turn(self):
        if self.is_setup_phase():
            if len(self.current_player.settlements) == len(self.current_player.roads) == self.current_player.turn_num + 1:
                return True
        elif self.last_roll[0]:
            return True

        return False

    def end_turn(self):
        if not self.can_end_turn():
            error_message = f"Illegal end turn by player number {self.current_player.num}"
            log.error(message=error_message, tags=['actions', 'game'])
            raise Exception(error_message)

        self.turn_num += 1
        self.clear_dice()

        self.current_player.turn_num += 1
        self.current_player = next(self.player_loop)

    def draw_die(self, x, y, val):
        rect = self.canvas.create_rectangle(x, y, x + 60, y + 60, fill="white")

        if not val and not self.is_setup_phase() and not self.current_player.is_cpu:
            self.canvas.tag_bind(rect, "<Button-1>", lambda event: self.current_player.roll())
            return

        self.graphics['dice'].append(rect)

        if val == 1:
            self.graphics['dice'] += [
                self.canvas.create_oval(x + 3 / 8 * DICE_WIDTH, y + 3 / 8 * DICE_WIDTH, x + 5 / 8 * DICE_WIDTH, y + 5 / 8 * DICE_WIDTH, fill="black")
            ]
        elif val == 2:
            self.graphics['dice'] += [
                self.canvas.create_oval(x + 1 / 8 * DICE_WIDTH, y + 1 / 8 * DICE_WIDTH, x + 3 / 8 * DICE_WIDTH, y + 3 / 8 * DICE_WIDTH, fill="black"),
                self.canvas.create_oval(x + 5 / 8 * DICE_WIDTH, y + 5 / 8 * DICE_WIDTH, x + 7 / 8 * DICE_WIDTH, y + 7 / 8 * DICE_WIDTH, fill="black")
            ]
        elif val == 3:
            self.graphics['dice'] += [
                self.canvas.create_oval(x + 1 / 8 * DICE_WIDTH, y + 1 / 8 * DICE_WIDTH, x + 3 / 8 * DICE_WIDTH, y + 3 / 8 * DICE_WIDTH, fill="black"),
                self.canvas.create_oval(x + 3 / 8 * DICE_WIDTH, y + 3 / 8 * DICE_WIDTH, x + 5 / 8 * DICE_WIDTH, y + 5 / 8 * DICE_WIDTH, fill="black"),
                self.canvas.create_oval(x + 5 / 8 * DICE_WIDTH, y + 5 / 8 * DICE_WIDTH, x + 7 / 8 * DICE_WIDTH, y + 7 / 8 * DICE_WIDTH, fill="black")
            ]
        elif val == 4:
            self.graphics['dice'] += [
                self.canvas.create_oval(x + 1 / 8 * DICE_WIDTH, y + 1 / 8 * DICE_WIDTH, x + 3 / 8 * DICE_WIDTH, y + 3 / 8 * DICE_WIDTH, fill="black"),
                self.canvas.create_oval(x + 5 / 8 * DICE_WIDTH, y + 1 / 8 * DICE_WIDTH, x + 7 / 8 * DICE_WIDTH, y + 3 / 8 * DICE_WIDTH, fill="black"),
                self.canvas.create_oval(x + 1 / 8 * DICE_WIDTH, y + 5 / 8 * DICE_WIDTH, x + 3 / 8 * DICE_WIDTH, y + 7 / 8 * DICE_WIDTH, fill="black"),
                self.canvas.create_oval(x + 5 / 8 * DICE_WIDTH, y + 5 / 8 * DICE_WIDTH, x + 7 / 8 * DICE_WIDTH, y + 7 / 8 * DICE_WIDTH, fill="black")
            ]
        elif val == 5:
            self.graphics['dice'] += [
                self.canvas.create_oval(x + 1 / 8 * DICE_WIDTH, y + 1 / 8 * DICE_WIDTH, x + 3 / 8 * DICE_WIDTH, y + 3 / 8 * DICE_WIDTH, fill="black"),
                self.canvas.create_oval(x + 5 / 8 * DICE_WIDTH, y + 1 / 8 * DICE_WIDTH, x + 7 / 8 * DICE_WIDTH, y + 3 / 8 * DICE_WIDTH, fill="black"),
                self.canvas.create_oval(x + 1 / 8 * DICE_WIDTH, y + 5 / 8 * DICE_WIDTH, x + 3 / 8 * DICE_WIDTH, y + 7 / 8 * DICE_WIDTH, fill="black"),
                self.canvas.create_oval(x + 5 / 8 * DICE_WIDTH, y + 5 / 8 * DICE_WIDTH, x + 7 / 8 * DICE_WIDTH, y + 7 / 8 * DICE_WIDTH, fill="black"),
                self.canvas.create_oval(x + 3 / 8 * DICE_WIDTH, y + 3 / 8 * DICE_WIDTH, x + 5 / 8 * DICE_WIDTH, y + 5 / 8 * DICE_WIDTH, fill="black")
            ]
        elif val == 6:
            self.graphics['dice'] += [
                self.canvas.create_oval(x + 1 / 8 * DICE_WIDTH, y + 1 / 16 * DICE_WIDTH, x + 3 / 8 * DICE_WIDTH, y + 5 / 16 * DICE_WIDTH, fill="black"),
                self.canvas.create_oval(x + 1 / 8 * DICE_WIDTH, y + 6 / 16 * DICE_WIDTH, x + 3 / 8 * DICE_WIDTH, y + 10 / 16 * DICE_WIDTH, fill="black"),
                self.canvas.create_oval(x + 1 / 8 * DICE_WIDTH, y + 11 / 16 * DICE_WIDTH, x + 3 / 8 * DICE_WIDTH, y + 15 / 16 * DICE_WIDTH, fill="black"),
                self.canvas.create_oval(x + 5 / 8 * DICE_WIDTH, y + 1 / 16 * DICE_WIDTH, x + 7 / 8 * DICE_WIDTH, y + 5 / 16 * DICE_WIDTH, fill="black"),
                self.canvas.create_oval(x + 5 / 8 * DICE_WIDTH, y + 6 / 16 * DICE_WIDTH, x + 7 / 8 * DICE_WIDTH, y + 10 / 16 * DICE_WIDTH, fill="black"),
                self.canvas.create_oval(x + 5 / 8 * DICE_WIDTH, y + 11 / 16 * DICE_WIDTH, x + 7 / 8 * DICE_WIDTH, y + 15 / 16 * DICE_WIDTH, fill="black")
            ]

    def draw_dice(self):
        if 'dice' in self.graphics:
            for g in self.graphics['dice']:
                self.canvas.delete(g)

        self.graphics['dice'] = []

        x = ROLL_X
        y = ROLL_Y

        self.draw_die(x, y, self.last_roll[0]),
        self.draw_die(x + DICE_WIDTH + 20, y, self.last_roll[1])

    def draw_end_turn(self):
        if 'end_turn' in self.graphics:
            self.canvas.delete(self.graphics['end_turn'])

        if not self.can_end_turn() or self.current_player.is_cpu:
            return

        text = self.canvas.create_text(END_TURN_X, END_TURN_Y, text="End Turn", fill="white", font="default 30", anchor="nw")

        if not self.current_player.is_cpu:
            self.canvas.tag_bind(text, "<Button-1>", lambda event: self.current_player.end_turn())

        self.graphics['end_turn'] = text

    def draw(self):
        if self.depth == 0 and self.canvas:
            self.board.draw()
            self.current_player.draw()
            self.draw_dice()
            self.draw_end_turn()
            self.canvas.update()

    def game_recap(self):
        time_string = "{:.4f}".format(self.duration) + 's'

        return '\n\n' \
               'Game Stats \n\n' \
               f"| Winner: {self.current_player.name}\n" \
               f"| Time: {time_string}\n" \
               f"| Turns: {self.turn_num}"

    def player_recap(self):
        player_recap = '\n\nPlayer Stats\n'
        for player in self.players:
            player_recap += ('\n' + player.stringify_stats())

        return player_recap

    def finish(self):
        self.winner = self.current_player
        self.draw()

        log.info('Game Over', data=self.to_dict(), tags=['game'])

    def to_dict(self):
        return {
            'duration_seconds': "{:.4f}".format(self.duration) + 's',
            'num_turns': self.turn_num,
            'winner': self.winner.name,
            'players': [player.to_dict() for player in self.players]
        }

    def copy(self):
        game = Game()
        game.depth = self.depth + 1

        # Create an identical empty board
        game.board = self.board.copy(game)

        # Create identical players, with their cards and pieces
        game.players = [player.copy(game) for player in self.players]
        game.player_loop = player_loop(game.players)

        # Set the correct current_player
        for _ in range(self.turn_num + 1):
            game.current_player = next(game.player_loop)

        if self.current_player.num != game.current_player.num or self.current_player.name != game.current_player.name:
            raise Exception('Game did not copy Players correctly')

        game.turn_num = self.turn_num
        game.last_roll = self.last_roll

        game.development_card_deck = copy(self.development_card_deck)

        return game
