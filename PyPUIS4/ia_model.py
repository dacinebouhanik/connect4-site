# ia_model.py
# Réseau de neurones CNN pour Puissance 4
# Architecture inspirée d'AlphaZero

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np


class ResidualBlock(nn.Module):
    """
    Bloc résiduel (comme ResNet).
    Permet d'entraîner des réseaux profonds sans vanishing gradient.
    """
    def __init__(self, channels):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, 3, padding=1, bias=False)
        self.bn1   = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, 3, padding=1, bias=False)
        self.bn2   = nn.BatchNorm2d(channels)

    def forward(self, x):
        residual = x
        x = F.relu(self.bn1(self.conv1(x)))
        x = self.bn2(self.conv2(x))
        x += residual
        return F.relu(x)


class Puissance4CNN(nn.Module):
    """
    Réseau CNN pour Puissance 4 (9x9).

    Entrée  : tensor (batch, 3, 9, 9)
              - canal 0 : pions joueur courant
              - canal 1 : pions adversaire
              - canal 2 : indicateur de tour (1.0 si joueur 1, 0.0 si joueur 2)

    Sorties :
              - policy : distribution sur 9 colonnes (softmax)
              - value  : estimation victoire [-1, +1]
    """

    def __init__(self, channels=128, n_residual=10):
        super().__init__()

        # Couche d'entrée
        self.input_conv = nn.Conv2d(3, channels, 3, padding=1, bias=False)
        self.input_bn   = nn.BatchNorm2d(channels)

        # Blocs résiduels
        self.residuals = nn.Sequential(
            *[ResidualBlock(channels) for _ in range(n_residual)]
        )

        # Policy head
        self.policy_conv = nn.Conv2d(channels, 32, 1, bias=False)
        self.policy_bn   = nn.BatchNorm2d(32)
        self.policy_fc   = nn.Linear(32 * 9 * 9, 9)

        # Value head
        self.value_conv = nn.Conv2d(channels, 32, 1, bias=False)
        self.value_bn   = nn.BatchNorm2d(32)
        self.value_fc1  = nn.Linear(32 * 9 * 9, 256)
        self.value_fc2  = nn.Linear(256, 1)

    def forward(self, x):
        # Corps commun
        x = F.relu(self.input_bn(self.input_conv(x)))
        x = self.residuals(x)

        # Policy head
        p = F.relu(self.policy_bn(self.policy_conv(x)))
        p = p.view(p.size(0), -1)
        p = self.policy_fc(p)
        policy = F.softmax(p, dim=1)

        # Value head
        v = F.relu(self.value_bn(self.value_conv(x)))
        v = v.view(v.size(0), -1)
        v = F.relu(self.value_fc1(v))
        v = torch.tanh(self.value_fc2(v))

        return policy, v


def plateau_vers_tensor(plateau, joueur_courant):
    """
    Convertit un plateau 9x9 (liste Python) en tensor PyTorch (1, 3, 9, 9).

    Canal 0 : positions du joueur courant
    Canal 1 : positions de l'adversaire
    Canal 2 : indicateur de tour
    """
    p   = np.array(plateau, dtype=np.float32)
    adv = 2 if joueur_courant == 1 else 1

    canal0 = (p == joueur_courant).astype(np.float32)
    canal1 = (p == adv).astype(np.float32)
    canal2 = np.full((9, 9), 1.0 if joueur_courant == 1 else 0.0, dtype=np.float32)

    tensor = np.stack([canal0, canal1, canal2], axis=0)
    return torch.tensor(tensor).unsqueeze(0)