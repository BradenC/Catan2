from random import shuffle

from catan2 import log


class DevelopmentCard:
    cost = [0, 0, 1, 1, 1]

    def __init__(self, num=None, name=None):
        self.id = num
        self.name = name

        if self.id == 0 or self.name == 'roads':
            self.id = 0
            self.name = 'roads'
        elif self.id == 1 or self.name == 'plenty':
            self.id = 1
            self.name = 'plenty'
        elif self.id == 2 or self.name == 'monopoly':
            self.id = 2
            self.name = 'monopoly'
        elif self.id == 3 or self.name == 'knight':
            self.id = 3
            self.name = 'knight'
        elif self.id == 4 or self.name == 'vp':
            self.id = 4
            self.name = 'vp'
        else:
            log.error(
                message='Unknown resource',
                data={
                    num,
                    name
                }
            )

    # TODO
    @staticmethod
    def play(game, player, i):
        if i == 4:
            raise Exception("You can't play a VP")

        if player.development_cards[i] < 1:
            raise Exception(f'Player {player.name} does not have the development card he wants to play')

        player.development_cards[i] -= 1


development_cards =\
    2 * [0] +\
    2 * [1] +\
    2 * [2] +\
    4 * [3] +\
    2 * [4]
