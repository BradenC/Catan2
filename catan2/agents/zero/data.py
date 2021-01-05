import os
import torch
from torch.utils.data import DataLoader, IterableDataset

from catan2 import config, log


class CatanDataSet(IterableDataset):
    def __init__(self, sample_dir):
        self.sample_dir = sample_dir
        self.len = 17500000

    def __len__(self):
        return self.len

    def get_sample(self):
        for f in [self.sample_dir + filename for filename in os.listdir(self.sample_dir)]:
            log.trace(f'Now taking from file {f}')
            data = torch.load(f)
            for item in data:
                yield item

    def __iter__(self):
        return self.get_sample()

    def __getitem__(self, index):
        return self.get_sample()


class CatanDataLoader(DataLoader):
    def __init__(self, directory: str, batch_size: int = None, pin_memory: bool = False):
        dataset = CatanDataSet(directory)
        batch_size = batch_size or config['ai']['batch_size']

        super().__init__(
            dataset=dataset,
            batch_size=batch_size,
            pin_memory=pin_memory
        )
