"""Residual graph convolution over an inventory graph and symmetric pair decoding."""
import torch
from torch import nn
from torch.nn import functional as functional


class InventoryConvolution(nn.Module):
    def __init__(self, inputs, outputs):
        super().__init__()
        self.node = nn.Linear(inputs, outputs)
        self.message = nn.Linear(inputs, outputs, bias=False)

    def forward(self, x):
        # D^-1/2 (A+I) D^-1/2 is 11^T/n for the complete inventory graph.
        pooled = x.mean(dim=0, keepdim=True)
        return functional.relu(self.node(x) + self.message(pooled))


class SpaceRelationGCN(nn.Module):
    def __init__(self, features=50, hidden=32):
        super().__init__()
        self.features, self.hidden = features, hidden
        self.first = InventoryConvolution(features, hidden)
        self.second = InventoryConvolution(hidden, hidden)
        self.decoder = nn.Sequential(
            nn.Linear(3 * hidden, hidden), nn.ReLU(), nn.Linear(hidden, 1))

    def encode(self, x):
        return self.second(self.first(x))

    def decode(self, embeddings, pairs):
        left, right = embeddings[pairs[:, 0]], embeddings[pairs[:, 1]]
        features = torch.cat((left + right, (left - right).abs(), left * right), dim=1)
        return self.decoder(features).squeeze(-1)

    def score_pairs(self, x, pairs):
        return self.decode(self.encode(x), pairs)

    def specification(self):
        return {'features': self.features, 'hidden': self.hidden}


def pu_risk(positive_logits, population_logits, prior):
    """Non-negative PU logistic risk with an explicitly assumed class prior."""
    if not 0 < prior < 1:
        raise ValueError('Positive class prior must lie strictly between zero and one')
    if positive_logits.numel() == 0 or population_logits.numel() == 0:
        raise ValueError('PU risk needs positive and population samples')
    positive_risk = prior * functional.softplus(-positive_logits).mean()
    negative_risk = (functional.softplus(population_logits).mean()
                     - prior * functional.softplus(positive_logits).mean())
    return positive_risk + negative_risk.clamp_min(0)


def assumed_prior(sample, multiplier):
    rate = len(sample['positive_pairs']) / len(sample['all_pairs'])
    return min(.5, multiplier * rate)


def graph_loss(model, sample, population_pairs, multiplier):
    embeddings = model.encode(sample['x'])
    positives = model.decode(embeddings, sample['positive_pairs'])
    population = model.decode(embeddings, population_pairs)
    loss = pu_risk(positives, population, assumed_prior(sample, multiplier))
    if len(sample['negative_pairs']):
        negatives = model.decode(embeddings, sample['negative_pairs'])
        loss = loss + functional.softplus(negatives).mean()
    return loss


def load_checkpoint(path):
    checkpoint = torch.load(path, map_location='cpu', weights_only=True)
    model = SpaceRelationGCN(**checkpoint['model_specification'])
    model.load_state_dict(checkpoint['state_dict'])
    return model.eval(), checkpoint
