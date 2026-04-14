# ia_joueur.py
# Utilise le CNN entraîné pour jouer
# S'intègre avec modele.py existant

import os
import torch
import numpy as np
from ia_model import Puissance4CNN, plateau_vers_tensor

DEVICE   = "cuda" if torch.cuda.is_available() else "cpu"
COLONNES = 9


class IAJoueurCNN:
    """
    Joueur IA basé sur le CNN entraîné.

    Modes :
      - "cnn_pur"     : utilise uniquement le CNN (rapide, ~5ms)
      - "cnn_minimax" : CNN guide le minimax (plus fort)
    """

    def __init__(self, chemin_modele="modele_ia_best.pt"):
        self.modele = None
        self._charger_modele(chemin_modele)

    def _charger_modele(self, chemin):
        try:
            self.modele = Puissance4CNN(channels=128, n_residual=10).to(DEVICE)
            checkpoint  = torch.load(chemin, map_location=DEVICE)

            if "model" in checkpoint:
                self.modele.load_state_dict(checkpoint["model"])
                print(f"✅ CNN chargé — epoch {checkpoint.get('epoch','?')} "
                      f"val_loss={checkpoint.get('val_loss', 0):.4f}")
            else:
                self.modele.load_state_dict(checkpoint)
                print(f"✅ CNN chargé depuis {chemin}")

            self.modele.eval()

        except FileNotFoundError:
            print(f"⚠️  Modèle non trouvé : {chemin}")
            print("    Lance d'abord : python train.py")
            self.modele = None
        except Exception as e:
            print(f"⚠️  Erreur chargement : {e}")
            self.modele = None

    def est_pret(self):
        return self.modele is not None

    def predire(self, plateau, joueur_courant):
        """
        Retourne (policy, value) pour la position donnée.

        policy : np.array(9,)  — probabilités par colonne
        value  : float         — estimation [-1, +1]
        """
        if not self.est_pret():
            return np.ones(9) / 9, 0.0

        tensor = plateau_vers_tensor(plateau, joueur_courant).to(DEVICE)

        with torch.no_grad():
            policy, value = self.modele(tensor)

        return policy[0].cpu().numpy(), value[0, 0].cpu().item()

    def meilleur_coup(self, plateau, joueur_courant, colonnes_valides=None):
        """
        Retourne la colonne avec la meilleure probabilité policy
        parmi les colonnes valides.
        """
        policy, value = self.predire(plateau, joueur_courant)

        if colonnes_valides is None:
            colonnes_valides = [j for j in range(COLONNES) if plateau[0][j] == 0]

        if not colonnes_valides:
            return None, policy, value

        masque = np.full(COLONNES, -np.inf)
        for col in colonnes_valides:
            masque[col] = policy[col]

        return int(np.argmax(masque)), policy, value

    def scores_par_colonne(self, plateau, joueur_courant, colonnes_valides=None):
        """
        Retourne un dict {col: score} compatible avec calculer_scores_minimax.
        Permet l'intégration directe dans app.py.
        """
        policy, value = self.predire(plateau, joueur_courant)

        if colonnes_valides is None:
            colonnes_valides = [j for j in range(COLONNES) if plateau[0][j] == 0]

        return {col: int(policy[col] * 10000) for col in colonnes_valides}


# =========================================================
# MINIMAX GUIDÉ PAR CNN
# =========================================================

class MinimaxCNN:
    """
    Minimax où :
    - La fonction d'évaluation est remplacée par le CNN (value head)
    - Les coups sont triés par probabilité CNN (policy head)
      → améliore massivement l'élagage alpha-bêta
    """

    def __init__(self, modele_jeu, ia_cnn, profondeur=4):
        self.m          = modele_jeu
        self.cnn        = ia_cnn
        self.profondeur = profondeur

    def evaluer_avec_cnn(self, plateau, joueur_max):
        """Remplace evaluer_plateau() par la prédiction CNN."""
        if not self.cnn.est_pret():
            return self.m.evaluer_plateau(plateau, joueur_max)
        _, value = self.cnn.predire(plateau, joueur_max)
        return int(value * 50000)

    def calculer_meilleur_coup(self):
        """
        Version améliorée de calculer_scores_minimax
        qui utilise le CNN comme heuristique.
        """
        plateau    = [ligne[:] for ligne in self.m.plateau]
        joueur_max = self.m.joueur_courant
        adv        = self.m.autre_joueur(joueur_max)
        valides    = self.m.trier_colonnes(self.m.colonnes_valides(plateau))
        scores     = {}

        # Étape 0 : victoire immédiate
        for col in valides:
            pt  = [l[:] for l in plateau]
            lig = self.m._jouer_temp(pt, col, joueur_max)
            if lig is None:
                continue
            if self.m._verifier_victoire_sur_plateau(pt, joueur_max):
                return {col: 100_000_000}

        # Étape 1 : bloquer victoire adverse
        for col in valides:
            pt  = [l[:] for l in plateau]
            lig = self.m._jouer_temp(pt, col, adv)
            if lig is None:
                continue
            if self.m._verifier_victoire_sur_plateau(pt, adv):
                pt2  = [l[:] for l in plateau]
                lig2 = self.m._jouer_temp(pt2, col, joueur_max)
                if lig2 is not None:
                    return {col: 90_000_000}

        # Étape 2 : trier par policy CNN puis minimax
        policy, _ = self.cnn.predire(plateau, joueur_max)
        valides_tries = sorted(valides, key=lambda c: -policy[c])

        for col in valides_tries:
            pt  = [l[:] for l in plateau]
            lig = self.m._jouer_temp(pt, col, joueur_max)
            if lig is None:
                continue
            score = self._minimax(
                pt, self.profondeur - 1,
                -10**18, 10**18,
                joueur_max, adv
            )
            scores[col] = score

        return scores

    def _minimax(self, plateau, profondeur, alpha, beta, joueur_max, joueur_courant):
        adv = self.m.autre_joueur(joueur_max)

        if self.m._verifier_victoire_sur_plateau(plateau, joueur_max):
            return 100_000_000 - profondeur
        if self.m._verifier_victoire_sur_plateau(plateau, adv):
            return -100_000_000 + profondeur
        if profondeur == 0 or self.m.plateau_plein(plateau):
            return self.evaluer_avec_cnn(plateau, joueur_max)

        # Trier par policy CNN
        valides = self.m.trier_colonnes(self.m.colonnes_valides(plateau))
        if self.cnn.est_pret():
            policy_loc, _ = self.cnn.predire(plateau, joueur_courant)
            valides = sorted(valides, key=lambda c: -policy_loc[c])

        if joueur_courant == joueur_max:
            best = -10**18
            for col in valides:
                lig = self.m._jouer_temp(plateau, col, joueur_courant)
                if lig is None:
                    continue
                sc = self._minimax(
                    plateau, profondeur - 1, alpha, beta,
                    joueur_max, adv
                )
                plateau[lig][col] = 0
                best  = max(best, sc)
                alpha = max(alpha, sc)
                if alpha >= beta:
                    break
            return best
        else:
            worst = 10**18
            for col in valides:
                lig = self.m._jouer_temp(plateau, col, joueur_courant)
                if lig is None:
                    continue
                sc = self._minimax(
                    plateau, profondeur - 1, alpha, beta,
                    joueur_max, joueur_max
                )
                plateau[lig][col] = 0
                worst = min(worst, sc)
                beta  = min(beta, sc)
                if alpha >= beta:
                    break
            return worst


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    print("=== Test IAJoueurCNN ===\n")

    chemin = "modele_ia_best.pt"

    if not os.path.exists(chemin):
        print("⚠️  Modèle non trouvé — crée un modèle vierge pour tester")
        from ia_model import Puissance4CNN
        m = Puissance4CNN(channels=128, n_residual=10)
        torch.save(m.state_dict(), chemin)

    ia = IAJoueurCNN(chemin)

    if ia.est_pret():
        plateau = [[0]*9 for _ in range(9)]
        col, policy, value = ia.meilleur_coup(plateau, 1)
        print(f"Plateau vide → colonne {col+1} | value={value:.3f}")
        print(f"Policy : { {i+1: round(float(p), 3) for i, p in enumerate(policy)} }")
    else:
        print("❌ Modèle non disponible")