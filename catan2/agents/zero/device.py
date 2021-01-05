import torch

from catan2 import config

if config['ai']['gpu']:
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
else:
    device = torch.device("cpu")
