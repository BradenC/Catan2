"""
Class defining the different Resources in Catan
"""


class Resource:
    def __init__(self, num=None, name=None):
        self.id = num
        self.name = name

        if self.id == 0 or self.name == 'wood':
            self.id = 0
            self.name = 'wood'
            self.color = "#262"
        elif self.id == 1 or self.name == 'brick':
            self.id = 1
            self.name = 'brick'
            self.color = "#E75"
        elif self.id == 2 or self.name == 'grain':
            self.id = 2
            self.name = 'grain'
            self.color = "#FC2"
        elif self.id == 3 or self.name == 'sheep':
            self.id = 3
            self.name = 'sheep'
            self.color = "#9B3"
        elif self.id == 4 or self.name == 'ore':
            self.id = 4
            self.name = 'ore'
            self.color = "#678"
        elif self.id == 5 or self.name == 'desert':
            self.id = 5
            self.name = 'desert'
            self.color = "#FCA"
        elif self.id == 6 or self.name == 'water':
            self.id = 6
            self.name = 'water'
            self.color = "#04A"
        else:
            raise Exception(f"Unknown Resource encountered: {name}")


resources = [Resource(x) for x in range(0, 6)]


HexTiles = [
    'wood',
    'grain',
    'ore',
    'ore',
    'sheep',
    'sheep',
    'brick',
    'grain',
    'wood',
    'grain',
    'wood',
    'desert',
    'sheep',
    'brick',
    'ore',
    'brick',
    'grain',
    'sheep',
    'wood'
]

HexNumbers = [6, 2, 5, 3, 9, 10, 8, 8, 4, 11, 3, 0, 10, 5, 6, 4, 9, 12, 11]
