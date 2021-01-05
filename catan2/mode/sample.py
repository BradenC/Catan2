from tqdm import tqdm

from catan2 import config
from catan2.agents import Zero
from catan2.catan import Game


def sample(canvas=None):
    if config['ai']['agent'].lower() != 'zero':
        raise NotImplementedError('Sample only supports Zero')

    for i in tqdm(range(config['experiment']['num_samples'])):
        winner = Game(
            agents=[Zero('ZeroOne'), Zero('ZeroTwo')],
            canvas=canvas
        ).start().winner

        Zero.cook_samples(winner, i)
