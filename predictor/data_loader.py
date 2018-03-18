import os
import fnmatch
import numpy as np
import random
import torch


VIEWPORT_TRACE = '../datasets/viewport_trace/'
TRAIN_DATASET = VIEWPORT_TRACE + 'train-dataset/'
TEST_DATASET = VIEWPORT_TRACE + 'test-dataset/'
TRAIN_SAMPLE_LENGTH = 30
LABEL_SAMPLE_LENGTH = 30
TEST_LABEL_LENGTH = 90
BATCH_SIZE = 32


class TrainDataLoader:
    """
    This class is for training dataset loading
    """
    def __init__(self, trace_folder=TRAIN_DATASET, random_seed=10):
        """
        :param trace_folder:
        :param random_seed:
        :return: none
        """
        np.random.seed(random_seed)

        self.trace_folder = trace_folder
        self.all_vp_unit, _ = self._load_viewport_unit()
        # pick a random viewport trace file
        self.vp_idx = np.random.randint(low=0, high=len(self.all_vp_unit))
        # self.vp_idx = np.random.randint(low=0, high=45)
        self.vp_unit = self.all_vp_unit[self.vp_idx]
        self.unit_start_max = len(self.vp_unit) - LABEL_SAMPLE_LENGTH - 2
        self.unit_idx = 0

    def _load_viewport_unit(self):
        all_vp_time = []
        all_vp_unit = []
        for root, dirnames, filenames in os.walk(self.trace_folder):
            for filename in fnmatch.filter(filenames, '*.txt'):
                if filename == 'formAnswers.txt' or filename == 'testInfo.txt':
                    continue
                trace_file = os.path.join(root, filename)
                vp_time = []
                vp_unit = []
                with open(trace_file, 'r') as f:
                    for line in f:
                        if len(line) > 10:
                            parse = line.split()
                            vp_time.append(parse[0])
                            vp_unit.append(self._str_to_float(parse[2:6]))
                all_vp_time.append(vp_time)
                all_vp_unit.append(vp_unit)

        return all_vp_unit, all_vp_time

    @staticmethod
    def _str_to_float(str_list):
        float_list = []
        for string in str_list:
            float_list.append(float(string))
        return float_list

    def __iter__(self):
        return self

    def __next__(self):
        self.unit_idx += 1
        if self.unit_idx >= self.unit_start_max:
            self.vp_idx = np.random.randint(len(self.all_vp_unit))
            self.vp_unit = self.all_vp_unit[self.vp_idx]
            self.unit_start_max = len(self.vp_unit) - LABEL_SAMPLE_LENGTH - TRAIN_SAMPLE_LENGTH - 1
            self.unit_idx = 0
        train_sample = self.vp_unit[self.unit_idx: self.unit_idx + TRAIN_SAMPLE_LENGTH]
        label_sample = self.vp_unit[self.unit_idx + 1: self.unit_idx + 1 + TRAIN_SAMPLE_LENGTH]
        return train_sample, label_sample


class TestDataLoader:
    """
    This class is for test dataset loading
    """
    def __init__(self, trace_folder=TEST_DATASET, random_seed=10):
        """
        :param trace_folder:
        :param random_seed:
        :return: none
        """
        np.random.seed(random_seed)

        self.trace_folder = trace_folder
        self.all_vp_unit, _ = self._load_viewport_unit()
        # pick a random viewport trace file
        self.vp_idx = 0
        self.vp_unit = self.all_vp_unit[self.vp_idx]
        self.unit_start_max = len(self.vp_unit) - TEST_LABEL_LENGTH - TRAIN_SAMPLE_LENGTH - 1
        self.unit_idx = 0

    def _load_viewport_unit(self):
        all_vp_time = []
        all_vp_unit = []
        for root, dirnames, filenames in os.walk(self.trace_folder):
            for filename in fnmatch.filter(filenames, '*.txt'):
                if filename == 'formAnswers.txt' or filename == 'testInfo.txt':
                    continue
                trace_file = os.path.join(root, filename)
                vp_time = []
                vp_unit = []
                with open(trace_file, 'r') as f:
                    for line in f:
                        if len(line) > 10:
                            parse = line.split()
                            vp_time.append(parse[0])
                            vp_unit.append(self._str_to_float(parse[2:6]))
                all_vp_time.append(vp_time)
                all_vp_unit.append(vp_unit)

        return all_vp_unit, all_vp_time

    @staticmethod
    def _str_to_float(str_list):
        float_list = []
        for string in str_list:
            float_list.append(float(string))
        return float_list

    def __iter__(self):
        return self

    def __next__(self):
        self.unit_idx += 1
        if self.unit_idx >= self.unit_start_max:
            self.vp_idx += 1
            if self.vp_idx >= len(self.all_vp_unit):
                raise StopIteration
            self.vp_unit = self.all_vp_unit[self.vp_idx]
            self.unit_start_max = len(self.vp_unit) - TEST_LABEL_LENGTH - TRAIN_SAMPLE_LENGTH - 1
            self.unit_idx = 0
        train_sample = self.vp_unit[self.unit_idx: self.unit_idx + TRAIN_SAMPLE_LENGTH]
        label_sample = self.vp_unit[self.unit_idx + TRAIN_SAMPLE_LENGTH: self.unit_idx +
                                    TRAIN_SAMPLE_LENGTH + TEST_LABEL_LENGTH]

        return train_sample, label_sample


class CudaTrainLoader:
    def __init__(self, train_data_loader, batch_size=BATCH_SIZE):
        self.batch_size = batch_size
        self.data_loader = train_data_loader

    def __iter__(self):
        return self

    def __next__(self):
        batch_train_sample = []
        batch_label_sample = []
        count = 0
        for train_sample, label_sample in self.data_loader:
            count += 1
            batch_train_sample.append(train_sample)
            batch_label_sample.append(label_sample)
            if count == self.batch_size:
                break
        return torch.FloatTensor(batch_train_sample), torch.FloatTensor(batch_label_sample)


if __name__ == '__main__':
    data_loader = TrainDataLoader()
    # count = 0
    # for train, label in data_loader:
    #     count += 1
    #     print('train: ')
    #     print(train)
    #     print('label: ')
    #     print(label)
    #     if count == 10:
    #         break

    cuda_data_loader = CudaTrainLoader(data_loader)
    count = 0
    for train, label in cuda_data_loader:
        # print(train.size(), label.size())
        print(train)
        print(label)
        count += 1
        if count == 1:
            break


