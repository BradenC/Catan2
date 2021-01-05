import json

from tqdm import tqdm

from catan2 import config, log
from catan2.catan import Game
from catan2.agents import Random, Simple, Zero
from catan2.experiment.vs import vs, win_ratio
from catan2.experiment.plot import plot_results


def process_results(game_results, plot=True):
    record = {
        'config': config,
        'games': game_results
    }

    with open(config['directories']['results'], 'a+') as f:
        json.dump(record, f)
        f.write('\n')

    if plot:
        plot_results(game_results)


def train(canvas=None, turn_delay_s=None):
    # Init
    vs_random_results = []
    vs_simple_results = []

    # Pick out which Agent you want
    if config['ai']['agent'].lower() == 'zero':
        agent_class = Zero
    else:
        raise NotImplementedError(f"Train does not support agents of type ${config['ai']['agent']}.")

    # Load an existing model
    if config['directories']['model']['load_from']:
        agent_class.load(filename=config['directories']['model']['load_from'])

    # Train a new model
    if config['directories']['samples']['load_from']:
        agent_class.pretrain()
        agent_class.save()
        exit()

    # Run the experiment
    for i in range(config['experiment']['num_sets']):
        for j in tqdm(range(config['experiment']['num_reps'])):
            game = Game(
                agents=[agent_class(name='ZeroOne', net_version=-1), agent_class(name='ZeroTwo', net_version=-1)],
                canvas=canvas,
                turn_delay_s=turn_delay_s
            ).start()
            agent_class.cook_samples(game.winner, i * config['experiment']['num_reps'] + j)

        log.debug(f'Finished round {i} of episodes', tags=['experiment'])

        agent_class.save(i)
        agent_class.train()

        p1, p2 = agent_class(net_version=-1), agent_class(net_version=i)
        vs_results = vs([p1, p2], config['experiment']['games_per_improvement_test'])

        if win_ratio(vs_results, p1.name) < agent_class.threshold:
            log.debug(f'Win ratio not achieved. Reverting back to version {i}.', tags=['experiment'])
            agent_class.load(i)

        vs_random_results += vs([p1, Random()], config['experiment']['games_per_ground_test'])
        vs_simple_results += vs([p1, Simple()], config['experiment']['games_per_ground_test'])

    log.info('Finished Experiment', tags=['experiment'])
    agent_class.save()

    # Look at this graph
    process_results(vs_random_results)
    process_results(vs_simple_results)
