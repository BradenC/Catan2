"""
Entrypoint for Catan2
"""

import argparse
import os
import sys
import tkinter
from datetime import datetime

from catan2 import config
from catan2.constants import CANVAS_HEIGHT, CANVAS_WIDTH
from catan2.mode import play, sample, train
from catan2.logger import log


# What time is it, Mr. Fox?
now_string = datetime.today().strftime('%Y-%m-%d_%H-%M-%S')


# Path setup
current_path = os.path.abspath('..')
parent_path = os.path.dirname(current_path)

sys.path.append(parent_path)
sys.path.append(current_path)


# Set up current run's directory
if config['directories']['local']:
    base_dir = current_path + '/Catan2/runs/'
else:
    base_dir = 'D:/Catan2/runs/'

run_dir = base_dir + now_string + '/'
model_dir = run_dir + 'models/'
sample_dir = run_dir + 'samples/'

os.mkdir(run_dir)
os.mkdir(model_dir)
os.mkdir(sample_dir)

config['directories']['run'] = run_dir
config['directories']['results'] = run_dir + 'results'
config['directories']['model']['save_to'] = model_dir
config['directories']['samples']['save_to'] = sample_dir


# Parse Arguments
parser = argparse.ArgumentParser()

parser.add_argument('-a', '--agent', type=str, default='zero', choices=['zero'])
parser.add_argument('-g', '--graphics', action='store_true')
parser.add_argument('--load_samples', type=str)
parser.add_argument('--load_model', type=str)
parser.add_argument('--log_level', type=str, choices=['critical', 'error', 'warn', 'info', 'debug', 'trace'])
parser.add_argument('--mcts_depth', type=int)
parser.add_argument('--mode', type=str, choices=['play', 'sample', 'train'])
parser.add_argument('--num_epochs', type=int)
parser.add_argument('--num_samples', type=int)
parser.add_argument('--num_rounds', type=int)
parser.add_argument('--players', nargs=2, type=str)
parser.add_argument('--turn_delay_s', type=float)


# Save arguments to config
args = parser.parse_args()

config['ai']['agent']                      = args.agent or config['ai']['agent']
config['ai']['num_epochs']                 = args.num_epochs or config['ai']['num_epochs']
config['ai']['zero']['mcts']['iterations'] = args.mcts_depth if args.mcts_depth is not None else config['ai']['zero']['mcts']['iterations']
config['experiment']['num_samples']        = args.num_samples or config['experiment']['num_samples']
config['game']['player_names']             = args.players or config['game']['player_names']
config['graphics']['display']              = args.graphics or config['graphics']['display']
config['graphics']['turn_delay_s']         = args.turn_delay_s or config['graphics']['turn_delay_s']
config['logging']['level']                 = args.log_level or config['logging']['level']
config['mode']                             = args.mode or config['mode']

config['directories']['samples']['load_from'] = 'D:/Catan2/samples/' + args.load_samples + '/' if args.load_samples else ''
config['directories']['model']['load_from']   = 'D:/Catan2/models/' + args.load_model + '.pt' if args.load_model else ''


# Set up logger
log.setup(filename=f"{run_dir}/log", level=config['logging']['level'])


# Log config
log.info(data=config)


# Say hi
print(f"""

  /                 \\
 /                   \\
-----------------------
|  Welcome To Catan2  |
-----------------------
| {now_string} |
-----------------------
 \\                   /
  \\                 /
""")

# Set game mode
if config['mode'] == 'play':
    play_catan = play
elif config['mode'] == 'sample':
    play_catan = sample
elif config['mode'] == 'train':
    play_catan = train
else:
    raise Exception(f"Unknown mode encountered: {config['mode']}")

# Play with graphics
if config['graphics']['display']:

    # Setup canvas
    root = tkinter.Tk()
    canvas = tkinter.Canvas(root, width=CANVAS_WIDTH, height=CANVAS_HEIGHT)
    canvas['bg'] = 'black'

    # Setup game
    canvas.after(0, play_catan, canvas)
    canvas.pack()
    root.mainloop()

# Play without graphics
else:
    play_catan()
