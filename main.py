import os

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import optim

from model import MemN2N
from helpers import dataloader, get_fname, get_params


def train(train_iter, model, optimizer, epochs, max_clip):
    total_loss = 0
    next_epoch_to_report = 0
    pad = model.vocab.stoi['<pad>']

    for _, batch in enumerate(train_iter, start=1):
        story = batch.story
        query = batch.query
        answer = batch.answer

        optimizer.zero_grad()
        outputs = model(story, query)
        loss = F.nll_loss(outputs, answer.view(-1), ignore_index=pad, size_average=False)
        loss.backward()
        nn.utils.clip_grad_norm(model.parameters(), max_clip)
        optimizer.step()
        total_loss += loss.data[0]

        if train_iter.epoch == next_epoch_to_report:
            print("#! epoch {:d} average batch loss: {:5.1f}".format(
                int(train_iter.epoch), total_loss/len(train_iter)*100))
            next_epoch_to_report += 10
        if int(train_iter.epoch) == train_iter.epoch:
            total_loss = 0
        if train_iter.epoch == epochs:
            break


def eval(test_iter, model):
    total_error = 0

    for k, batch in enumerate(test_iter, start=1):
        story = batch.story
        query = batch.query
        answer = batch.answer
        outputs = model(story, query)
        _, outputs = torch.max(outputs, -1)
        total_error += torch.mean((outputs != answer.view(-1)).float()).data[0]
    print("#! average error: {:5.1f}".format(total_error/k*100))


def run(config):
    print("#! preparing data...")
    train_iter, test_iter, vocab = dataloader(config.batch_size, config.memory_size, config.task,
                                              config.joint, config.tenk)

    print("#! instantiating model...")
    model = MemN2N(get_params(config, vocab))
    optimizer = optim.Adam(model.parameters(), config.lr)

    if config.file:
        with open(os.path.join(config.save_dir, config.file), 'rb') as f:
            model.load_state_dict(torch.load(f))

    if config.train:
        print("#! training...")
        train(train_iter, model, optimizer, config.num_epochs, config.max_clip)
        if not os.path.isdir(config.save_dir):
            os.makedirs(config.save_dir)
        torch.save(model.state_dict(), os.path.join(config.save_dir, get_fname(config)))

    print("#! testing...")
    eval(test_iter, model)