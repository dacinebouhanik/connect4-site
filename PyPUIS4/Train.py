# train.py
# Entraînement du CNN sur toutes les parties de la BD
# avec pondération par qualité et augmentation par symétrie
#
# Usage :
#   python train.py
#   python train.py --epochs 20 --batch_size 256

import os
import argparse
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm

from ia_model import Puissance4CNN, plateau_vers_tensor
from db import get_conn


# =========================================================
# CONFIGURATION
# =========================================================

LIGNES   = 9
COLONNES = 9
DEVICE   = "cuda" if torch.cuda.is_available() else "cpu"

# ✅ Pondération par qualité des parties
# Plus la confiance est haute, plus les exemples sont répétés
REPETITIONS = {
    1: 1,    # parties aléatoires  → vues 1 fois
    2: 3,    # parties minimax     → vues 3 fois
    3: 10,   # top joueurs BGA     → vues 10 fois
}

print(f"Device : {DEVICE}")
print(f"Pondération : confiance 1=×1 | confiance 2=×3 | confiance 3=×10")


# =========================================================
# AUGMENTATION — SYMÉTRIE
# =========================================================

def miroir_plateau(plateau):
    """Miroir horizontal : col 0 ↔ col 8, col 1 ↔ col 7..."""
    return [ligne[::-1] for ligne in plateau]

def miroir_policy(policy):
    """Inverse le vecteur policy."""
    return policy[::-1].copy()


# =========================================================
# EXTRACTION DES DONNÉES
# =========================================================

def reconstruire_plateau(coups_str, jusqu_a_coup):
    """Reconstruit le plateau après `jusqu_a_coup` coups."""
    plateau = [[0] * COLONNES for _ in range(LIGNES)]
    joueur  = 1

    for i, ch in enumerate(coups_str):
        if i >= jusqu_a_coup:
            break
        if not ch.isdigit():
            continue
        col = int(ch) - 1
        if col < 0 or col >= COLONNES:
            continue
        for lig in range(LIGNES - 1, -1, -1):
            if plateau[lig][col] == 0:
                plateau[lig][col] = joueur
                break
        joueur = 2 if joueur == 1 else 1

    return plateau, joueur


def resultat_vers_value(resultat, joueur_courant):
    """+1 si gagné, -1 si perdu, 0 si nul."""
    if resultat == "rouge":
        return 1.0 if joueur_courant == 1 else -1.0
    elif resultat == "jaune":
        return 1.0 if joueur_courant == 2 else -1.0
    return 0.0


def charger_donnees_bd(limite=None):
    """
    Charge toutes les parties de la BD.

    Pour chaque partie :
    - Répétition selon la confiance (1x, 3x ou 10x)
    - Augmentation par symétrie (×2)

    Résultat : parties confiance 3 sont vues 20x plus
               que les parties aléatoires (10 répétitions × 2 symétrie)
    """
    print("\n📥 Chargement des parties depuis la BD...")

    conn = get_conn()
    cur  = conn.cursor()

    query = """
        SELECT g.resultat, g.confiance, c.coups, g.couleur_depart
        FROM games g
        JOIN games_coups c ON c.game_id = g.id
        WHERE g.resultat IS NOT NULL
          AND g.resultat != ''
          AND c.coups IS NOT NULL
          AND LENGTH(c.coups) > 0
        ORDER BY g.confiance DESC
    """
    if limite:
        query += f" LIMIT {limite}"

    cur.execute(query)
    parties = cur.fetchall()
    cur.close()
    conn.close()

    # Compter par confiance
    stats = {}
    for _, conf, _, _ in parties:
        stats[conf] = stats.get(conf, 0) + 1

    print(f"✅ {len(parties)} parties chargées :")
    for conf, nb in sorted(stats.items()):
        rep = REPETITIONS.get(conf, 1)
        print(f"   Confiance {conf} : {nb} parties × {rep} répétitions "
              f"× 2 symétrie = {nb * rep * 2 * 20:.0f} exemples estimés")

    X_list      = []
    policy_list = []
    value_list  = []
    skipped     = 0

    for resultat, confiance, coups_str, couleur_depart in tqdm(
        parties, desc="Génération exemples"
    ):
        if not coups_str or not resultat:
            skipped += 1
            continue

        coups_str = coups_str.strip()
        nb_coups  = len(coups_str)

        if nb_coups < 4:
            skipped += 1
            continue

        # Nombre de répétitions selon la confiance
        nb_rep = REPETITIONS.get(int(confiance), 1)

        for i in range(nb_coups):
            ch = coups_str[i]
            if not ch.isdigit():
                continue

            col_jouee = int(ch) - 1
            if col_jouee < 0 or col_jouee >= COLONNES:
                continue

            plateau, joueur = reconstruire_plateau(coups_str, i)

            policy = np.zeros(COLONNES, dtype=np.float32)
            policy[col_jouee] = 1.0

            value  = resultat_vers_value(resultat, joueur)
            tensor = plateau_vers_tensor(plateau, joueur).squeeze(0).numpy()

            # Symétrie
            plateau_mir = miroir_plateau(plateau)
            policy_mir  = miroir_policy(policy)
            tensor_mir  = plateau_vers_tensor(plateau_mir, joueur).squeeze(0).numpy()

            # ✅ Répéter nb_rep fois selon la qualité
            for _ in range(nb_rep):
                # Original
                X_list.append(tensor)
                policy_list.append(policy)
                value_list.append(value)

                # Symétrique
                X_list.append(tensor_mir)
                policy_list.append(policy_mir)
                value_list.append(value)

    total    = len(X_list)
    originaux = total // 2

    print(f"\n✅ {total:,} exemples générés :")
    print(f"   {originaux:,} originaux × 2 avec symétrie")
    print(f"   {skipped} parties ignorées")

    X        = np.array(X_list,      dtype=np.float32)
    y_policy = np.array(policy_list, dtype=np.float32)
    y_value  = np.array(value_list,  dtype=np.float32).reshape(-1, 1)

    return X, y_policy, y_value


# =========================================================
# DATASET PYTORCH
# =========================================================

class Puissance4Dataset(Dataset):
    def __init__(self, X, y_policy, y_value):
        self.X        = torch.tensor(X)
        self.y_policy = torch.tensor(y_policy)
        self.y_value  = torch.tensor(y_value)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y_policy[idx], self.y_value[idx]


# =========================================================
# ENTRAÎNEMENT
# =========================================================

def train(epochs=20, batch_size=256, lr=0.001):

    X, y_policy, y_value = charger_donnees_bd()

    if len(X) == 0:
        print("❌ Aucune donnée chargée !")
        return

    # Split 90/10
    n       = len(X)
    n_val   = int(n * 0.1)
    idx     = np.random.permutation(n)
    idx_tr  = idx[n_val:]
    idx_val = idx[:n_val]

    train_ds = Puissance4Dataset(X[idx_tr], y_policy[idx_tr], y_value[idx_tr])
    val_ds   = Puissance4Dataset(X[idx_val], y_policy[idx_val], y_value[idx_val])

    train_loader = DataLoader(
        train_ds, batch_size=batch_size, shuffle=True,
        num_workers=2, pin_memory=True
    )
    val_loader = DataLoader(
        val_ds, batch_size=batch_size, shuffle=False,
        num_workers=2, pin_memory=True
    )

    print(f"\n📊 Train : {len(train_ds):,} | Val : {len(val_ds):,}")

    model     = Puissance4CNN(channels=128, n_residual=10).to(DEVICE)
    nb_params = sum(p.numel() for p in model.parameters())
    print(f"🧠 Paramètres : {nb_params:,}")

    optimizer = optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    loss_policy_fn = nn.CrossEntropyLoss()
    loss_value_fn  = nn.MSELoss()

    best_val_loss = float("inf")

    print(f"\n🚀 Entraînement sur {epochs} epochs...\n")

    for epoch in range(1, epochs + 1):

        # Train
        model.train()
        total_loss = total_p = total_v = 0

        for X_b, p_b, v_b in tqdm(train_loader, desc=f"Epoch {epoch:3d}/{epochs}"):
            X_b = X_b.to(DEVICE)
            p_b = p_b.to(DEVICE)
            v_b = v_b.to(DEVICE)

            policy_pred, value_pred = model(X_b)

            loss_p = loss_policy_fn(policy_pred, p_b)
            loss_v = loss_value_fn(value_pred, v_b)
            loss   = loss_p + loss_v

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            total_loss += loss.item()
            total_p    += loss_p.item()
            total_v    += loss_v.item()

        scheduler.step()
        n_tr = len(train_loader)

        # Validation
        model.eval()
        val_loss = val_p = val_v = val_acc = 0

        with torch.no_grad():
            for X_b, p_b, v_b in val_loader:
                X_b = X_b.to(DEVICE)
                p_b = p_b.to(DEVICE)
                v_b = v_b.to(DEVICE)

                policy_pred, value_pred = model(X_b)

                lp = loss_policy_fn(policy_pred, p_b)
                lv = loss_value_fn(value_pred, v_b)

                val_loss += (lp + lv).item()
                val_p    += lp.item()
                val_v    += lv.item()

                pred_col = policy_pred.argmax(dim=1)
                true_col = p_b.argmax(dim=1)
                val_acc  += (pred_col == true_col).float().mean().item()

        n_val_b = len(val_loader)

        print(
            f"  Loss {total_loss/n_tr:.4f} "
            f"(P={total_p/n_tr:.4f} V={total_v/n_tr:.4f}) | "
            f"Val {val_loss/n_val_b:.4f} "
            f"(P={val_p/n_val_b:.4f} V={val_v/n_val_b:.4f}) | "
            f"Acc {val_acc/n_val_b:.3f} | "
            f"LR {scheduler.get_last_lr()[0]:.6f}"
        )

        # Sauvegarder le meilleur modèle
        if val_loss / n_val_b < best_val_loss:
            best_val_loss = val_loss / n_val_b
            torch.save({
                "epoch":    epoch,
                "model":    model.state_dict(),
                "val_loss": best_val_loss,
            }, "modele_ia_best.pt")
            print(f"  💾 Meilleur modèle sauvegardé (val_loss={best_val_loss:.4f})")

    torch.save(model.state_dict(), "modele_ia_final.pt")
    print(f"\n✅ Entraînement terminé !")
    print(f"   Meilleur val_loss : {best_val_loss:.4f}")
    print(f"   Fichiers : modele_ia_best.pt / modele_ia_final.pt")


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs",     type=int,   default=20)
    parser.add_argument("--batch_size", type=int,   default=256)
    parser.add_argument("--lr",         type=float, default=0.001)
    args = parser.parse_args()

    train(
        epochs     = args.epochs,
        batch_size = args.batch_size,
        lr         = args.lr,
    )