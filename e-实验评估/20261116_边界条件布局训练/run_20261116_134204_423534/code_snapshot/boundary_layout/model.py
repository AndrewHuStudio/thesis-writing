"""Boundary-conditioned inventory convolutions with random interior spatial slots."""
import math

import torch
from torch import nn

from relation_prediction.model import InventoryConvolution


def spatial_slots(inputs, generator):
    points = inputs['interior_points']
    count = len(inputs['x'])
    if count <= len(points):
        selection = torch.randperm(len(points), device=points.device, generator=generator)[:count]
    else:
        selection = torch.randint(len(points), (count,), device=points.device, generator=generator)
    noise = torch.rand((count, 2), device=points.device, generator=generator) - .5
    return points[selection], noise


class BoundaryLayoutModel(nn.Module):
    def __init__(self, hidden=64):
        super().__init__()
        self.hidden = hidden
        self.boundary_encoder = nn.Sequential(
            nn.Conv2d(2, 8, 3, padding=1), nn.ReLU(), nn.AvgPool2d(2),
            nn.Conv2d(8, 16, 3, padding=1), nn.ReLU(), nn.AdaptiveAvgPool2d((4, 4)),
            nn.Flatten(), nn.Linear(256, 64), nn.ReLU())
        self.first = InventoryConvolution(121, hidden)
        self.second = InventoryConvolution(hidden, hidden)
        self.output = nn.Linear(hidden, 4)
        nn.init.zeros_(self.output.weight)
        with torch.no_grad():
            self.output.bias.copy_(torch.tensor([0., 0., -3., -3.]))

    def forward(self, inputs, anchors, noise):
        features, extent = inputs['x'], inputs['extent']
        context = self.boundary_encoder(inputs['boundary_channels']).expand(len(features), -1)
        count = features.new_full((len(features), 1), math.log1p(len(features)) / 6)
        geometry = extent.expand(len(features), -1)
        rows = torch.cat((features, anchors / extent, noise, context, count, geometry), dim=1)
        hidden = self.second(self.first(rows))
        parameters = self.output(hidden)
        size = (.002 + .998 * parameters[:, 2:].sigmoid()) * extent
        fraction = (anchors / extent).clamp(.001, .999)
        center = (torch.logit(fraction) + parameters[:, :2]).sigmoid() * (extent - size) + size / 2
        return torch.cat((center, size), dim=1)

    def specification(self):
        return {'hidden': self.hidden}
