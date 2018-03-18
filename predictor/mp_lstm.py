import torch
import torch.autograd as autograd
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import torch.multiprocessing as mp

import argparse

# from predictor.data_loader import TrainDataLoader  # in mac
from data_loader import TrainDataLoader  # in ubuntu


class LSTMPredict(nn.Module):

    def __init__(self, input_size, hidden_size, num_layers, tag_size):
        super(LSTMPredict, self).__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        # self.in2lstm = nn.Linear(tag_size, input_size)
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers)
        self.init_lstm()

        self.lstm2tag = nn.Linear(hidden_size, tag_size)
        # nn.init.normal(self.lstm2tag.weight)

        self.hidden = self.init_hidden()  # initial hidden state for LSTM network

    def init_lstm(self):
        for name, weights in self.lstm.named_parameters():
            if len(weights.data.shape) == 2:
                nn.init.kaiming_normal(weights)
            if len(weights.data.shape) == 1:
                nn.init.normal(weights)

    def init_hidden(self):
        hx = torch.nn.init.xavier_normal(autograd.Variable(torch.randn(self.num_layers, 1, self.hidden_size)))
        cx = torch.nn.init.xavier_normal(autograd.Variable(torch.randn(self.num_layers, 1, self.hidden_size)))
        hidden = (hx, cx)
        return hidden

    def forward(self, orientations):
        # orientation_seq is a 2 dimensional tensor with shape [seq_len, tag_size]
        # lstm_in is a 2 dimensional tensor with shape [seq_len, input_size]
        # inputs is a 3 dimensional tensor with shape [seq_len, 1, -1]
        lstm_out, self.hidden = self.lstm(orientations, self.hidden)
        # print(lstm_out)
        tag_scores = F.tanh(self.lstm2tag(lstm_out.view(-1, self.hidden_size)))
        # print(tag_scores)
        return tag_scores


def train_model(rank, lock, counter, model, data_loader, learning_rate=0.0001, epoch=10, count_max=10000,
                hidden_size=128, num_layers=1):
    loss_function = nn.MSELoss()

    # train_losses = []
    # optimizer = optim.SGD(model.parameters(), lr=learning_rate, momentum=0.9, nesterov=True)
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    for poch in range(epoch):
        count = 0
        batch_loss = 0.0
        # optimizer = optim.SGD(model.parameters(), lr=learning_rate, momentum=0.9, nesterov=True)
        # optimizer = optim.Adam(model.parameters(), lr=learning_rate)
        # learning_rate *= 0.5
        for inputs, label in data_loader:
            # inputs = train_data[i: i+30]
            if count == count_max:
                break
            inputs = torch.FloatTensor(inputs).view(30, 1, -1)
            inputs = autograd.Variable(inputs)
            # print(inputs)
            # label = torch.FloatTensor(train_data[i+1: i+31])
            label = torch.FloatTensor(label)
            label = autograd.Variable(label)
            # print(inputs.size(), label.size())
            model.zero_grad()
            model.hidden = model.init_hidden()
            output = model(inputs)
            # sum_loss = 0.0
            # for index in range(len(output)):
            #     sum_loss += loss_function(output[index], label[index])
            # loss = sum_loss / len(output)
            loss = loss_function(output, label)

            if count % 1000 == 0:
                batch_loss = batch_loss / 1000
                # train_losses.append(batch_loss)
                print(rank, poch, count, batch_loss)
                batch_loss = 0.0
            else:
                batch_loss += loss
                # print(loss)

            with lock:
                counter.value += 1

            loss.backward()
            optimizer.step()
            # print(inputs)

            count += 1

    # loss_name = 'loss-' + str(hidden_size) + '-' + str(num_layers) + '-' + str(rank) + '.dat'
    # save_loss(train_losses, loss_name)
    # print('saved loss data: ' + loss_name)


def save_loss(losses, path):
    with open(path, "w+") as f:
        for loss in losses:
            f.write(str(loss) + "\n")


def main_train(model, data_loader, hidden_size, num_layers, num_processes, epoch=1, count_max=100000):
    # model = LSTMPredict(input_size=4, hidden_size=hidden_size, num_layers=num_layers, tag_size=4)
    model.share_memory()

    counter = mp.Value('i', 0)
    lock = mp.Lock()

    learning_rate = 0.0001
    processes = []
    for rank in range(num_processes):
        p = mp.Process(target=train_model, args=(rank, lock, counter, model, data_loader, learning_rate, epoch,
                                                 count_max, hidden_size, num_layers))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()


def try_hyper_para(hidden_size_list, num_layer_list, data_loader, epoch, count_max):
    for hidden_size in hidden_size_list:
        for num_layers in num_layer_list:
            model = LSTMPredict(input_size=4, hidden_size=hidden_size, num_layers=num_layers, tag_size=4)
            main_train(model, data_loader, hidden_size=hidden_size, num_layers=num_layers, num_processes=4, epoch=epoch,
                       count_max=count_max)
            print("finished training")
            model_name = 'mp-adam-lstm-' + str(hidden_size) + '-' + str(num_layers) + '.model'
            # loss_name = 'loss-' + str(hidden_size) + '-' + str(num_layers) + '.dat'
            torch.save(model, model_name)
            print('saved model: ' + model_name)
            # save_loss(losses, loss_name)
            # print('saved loss data: ' + loss_name)


if __name__ == "__main__":
    # parser = argparse.ArgumentParser(description='lstm predictor running on Liunx')
    # parser.add_argument('--num-process', type=int, default=4,
    #                     help='how many training processes to use (default 4)')
    # parser.add_argument('--count_max', type=int, default=100000,
    #                     help='how many samples in one epoch (default 100000)')
    # parser.add_argument('--epoch', type=int, default=3,
    #                     help='how many epochs in each training processes (default 3)')
    #
    # args = parser.parse_args()
    # num_processes = args.num_process
    # count_max = args.count_max
    # epoch = args.epoc

    data_loader = TrainDataLoader()
    hidden_size_list = [128, 256]
    num_layer_list = [1]
    try_hyper_para(hidden_size_list, num_layer_list, data_loader, epoch=3, count_max=100000)
    # main_train(data_loader, hidden_size=128, num_layers=1, num_processes=15, epoch=4, count_max=300000)

    # model = torch.load("lstm-512-1.model")
    # print(validate(model, train_data))
    # model = torch.load("lstm-256-1.model")
    # print(validate(model, train_data))
    # model = torch.load("lstm-128-2.model")
    # print(validate(model, train_data))
    # print(avg_prediction(train_data))





