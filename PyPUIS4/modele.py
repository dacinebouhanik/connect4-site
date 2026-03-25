# modele.py
import json
import random
import os


class Puissance4Modele:
    VIDE = 0
    ROUGE = 1
    JAUNE = 2

    DOSSIER_SAUVES = "sauvegardes"

    def __init__(self, chemin_config="config.json"):
        self.chemin_config = chemin_config
        self.charger_config()

        self.plateau = self.creer_plateau()
        self.joueur_courant = self.couleur_depart
        self.historique = []
        self.numero_partie = 1
        self.resultat = None

        os.makedirs(self.DOSSIER_SAUVES, exist_ok=True)

    # ---------------- CONFIG ----------------

    def charger_config(self):
        if not os.path.exists(self.chemin_config):
            self.config = {
                "lignes": 9,
                "colonnes": 9,
                "couleur_depart": 1
            }
        else:
            with open(self.chemin_config, "r", encoding="utf-8") as f:
                contenu = f.read().strip()

            if contenu == "":
                self.config = {
                    "lignes": 9,
                    "colonnes": 9,
                    "couleur_depart": 1
                }
            else:
                self.config = json.loads(contenu)

        self.lignes = self.config["lignes"]
        self.colonnes = self.config["colonnes"]
        self.couleur_depart = self.config["couleur_depart"]

    def sauver_config(self):
        self.config["lignes"] = self.lignes
        self.config["colonnes"] = self.colonnes
        self.config["couleur_depart"] = self.couleur_depart
        with open(self.chemin_config, "w") as f:
            json.dump(self.config, f)

    # ---------------- PLATEAU ----------------

    def creer_plateau(self):
        plateau = []
        for _ in range(self.lignes):
            plateau.append([self.VIDE] * self.colonnes)
        return plateau

    def nouvelle_partie(self):
        self.plateau = self.creer_plateau()
        self.joueur_courant = self.couleur_depart
        self.historique = []
        self.numero_partie += 1
        self.resultat = None

    def jouer_coup(self, colonne):
        """Renvoie la ligne jouée ou None si impossible."""
        if colonne < 0 or colonne >= self.colonnes:
            return None

        for lig in range(self.lignes - 1, -1, -1):
            if self.plateau[lig][colonne] == self.VIDE:
                self.plateau[lig][colonne] = self.joueur_courant
                self.historique.append((lig, colonne, self.joueur_courant))
                return lig
        return None

    def annuler_dernier_coup(self):
        if not self.historique:
            return False
        lig, col, joueur = self.historique.pop()
        self.plateau[lig][col] = self.VIDE
        self.joueur_courant = joueur
        self.resultat = None
        return True

    def changer_joueur(self):
        self.joueur_courant = self.JAUNE if self.joueur_courant == self.ROUGE else self.ROUGE

    def autre_joueur(self, joueur):
        return self.JAUNE if joueur == self.ROUGE else self.ROUGE

    def plateau_plein(self, plateau=None):
        if plateau is None:
            plateau = self.plateau
        for i in range(self.lignes):
            for j in range(self.colonnes):
                if plateau[i][j] == self.VIDE:
                    return False
        return True

    def definir_resultat(self, resultat):
        self.resultat = resultat

    # ---------------- VICTOIRE ----------------

    def _verifier_victoire_sur_plateau(self, plateau, joueur):
        # horizontal
        for i in range(self.lignes):
            for j in range(self.colonnes - 3):
                if (plateau[i][j] == joueur and plateau[i][j+1] == joueur and
                    plateau[i][j+2] == joueur and plateau[i][j+3] == joueur):
                    return True

        # vertical
        for j in range(self.colonnes):
            for i in range(self.lignes - 3):
                if (plateau[i][j] == joueur and plateau[i+1][j] == joueur and
                    plateau[i+2][j] == joueur and plateau[i+3][j] == joueur):
                    return True

        # diagonale \
        for i in range(self.lignes - 3):
            for j in range(self.colonnes - 3):
                if (plateau[i][j] == joueur and plateau[i+1][j+1] == joueur and
                    plateau[i+2][j+2] == joueur and plateau[i+3][j+3] == joueur):
                    return True

        # diagonale /
        for i in range(3, self.lignes):
            for j in range(self.colonnes - 3):
                if (plateau[i][j] == joueur and plateau[i-1][j+1] == joueur and
                    plateau[i-2][j+2] == joueur and plateau[i-3][j+3] == joueur):
                    return True

        return False

    def verifier_victoire(self, joueur):
        """Renvoie coordonnées gagnantes (liste) ou None."""
        if not self._verifier_victoire_sur_plateau(self.plateau, joueur):
            return None

        p = self.plateau
        # horizontal
        for i in range(self.lignes):
            for j in range(self.colonnes - 3):
                if (p[i][j] == joueur and p[i][j+1] == joueur and
                        p[i][j+2] == joueur and p[i][j+3] == joueur):
                    return [(i, j), (i, j+1), (i, j+2), (i, j+3)]
        # vertical
        for j in range(self.colonnes):
            for i in range(self.lignes - 3):
                if (p[i][j] == joueur and p[i+1][j] == joueur and
                        p[i+2][j] == joueur and p[i+3][j] == joueur):
                    return [(i, j), (i+1, j), (i+2, j), (i+3, j)]
        # diag \
        for i in range(self.lignes - 3):
            for j in range(self.colonnes - 3):
                if (p[i][j] == joueur and p[i+1][j+1] == joueur and
                        p[i+2][j+2] == joueur and p[i+3][j+3] == joueur):
                    return [(i, j), (i+1, j+1), (i+2, j+2), (i+3, j+3)]
        # diag /
        for i in range(3, self.lignes):
            for j in range(self.colonnes - 3):
                if (p[i][j] == joueur and p[i-1][j+1] == joueur and
                        p[i-2][j+2] == joueur and p[i-3][j+3] == joueur):
                    return [(i, j), (i-1, j+1), (i-2, j+2), (i-3, j+3)]

        return None

    # ---------------- COUPS ----------------

    def colonnes_valides(self, plateau=None):
        if plateau is None:
            plateau = self.plateau
        return [j for j in range(self.colonnes) if plateau[0][j] == self.VIDE]

    def coup_aleatoire(self):
        valides = self.colonnes_valides()
        if not valides:
            return None
        return random.choice(valides)

    def _jouer_temp(self, plateau, col, joueur):
        if col < 0 or col >= self.colonnes:
            return None
        for lig in range(self.lignes - 1, -1, -1):
            if plateau[lig][col] == self.VIDE:
                plateau[lig][col] = joueur
                return lig
        return None

    # ---------------- HEURISTIQUE ----------------

    def _score_fenetre(self, fenetre, joueur_max):
        """fenetre = liste de 4 cases."""
        adv = self.autre_joueur(joueur_max)

        c_j = fenetre.count(joueur_max)
        c_a = fenetre.count(adv)
        c_v = fenetre.count(self.VIDE)

        if c_j == 4:
            return 100000
        if c_a == 4:
            return -100000

        if c_j == 3 and c_v == 1:
            return 200
        if c_j == 2 and c_v == 2:
            return 50

        if c_a == 3 and c_v == 1:
            return -220
        if c_a == 2 and c_v == 2:
            return -60

        return 0

    def evaluer_plateau(self, plateau, joueur_max):
        """Score heuristique global du plateau."""
        score = 0

        # Bonus centre
        centre = self.colonnes // 2
        col_centre = [plateau[i][centre] for i in range(self.lignes)]
        score += col_centre.count(joueur_max) * 20

        # Horizontal
        for i in range(self.lignes):
            for j in range(self.colonnes - 3):
                fen = [plateau[i][j+k] for k in range(4)]
                score += self._score_fenetre(fen, joueur_max)

        # Vertical
        for j in range(self.colonnes):
            for i in range(self.lignes - 3):
                fen = [plateau[i+k][j] for k in range(4)]
                score += self._score_fenetre(fen, joueur_max)

        # Diag \
        for i in range(self.lignes - 3):
            for j in range(self.colonnes - 3):
                fen = [plateau[i+k][j+k] for k in range(4)]
                score += self._score_fenetre(fen, joueur_max)

        # Diag /
        for i in range(3, self.lignes):
            for j in range(self.colonnes - 3):
                fen = [plateau[i-k][j+k] for k in range(4)]
                score += self._score_fenetre(fen, joueur_max)

        return score

    def mettre_a_jour_parametres(self, lignes, colonnes, couleur_depart):
        if lignes < 4 or colonnes < 4:
            return False
        self.lignes = lignes
        self.colonnes = colonnes
        self.couleur_depart = couleur_depart
        self.sauver_config()
        self.nouvelle_partie()
        return True

    # ---------------- MINIMAX + ALPHA-BETA ----------------

    def minimax_alpha_beta(self, plateau, profondeur, alpha, beta, joueur_max, joueur_courant):
        """
        Minimax avec élagage alpha-bêta.
        CORRECTION : suppression du bloc redondant de victoire dans MIN.
        """
        adv = self.autre_joueur(joueur_max)

        # ── États terminaux ──
        if self._verifier_victoire_sur_plateau(plateau, joueur_max):
            return 100000000 - profondeur

        if self._verifier_victoire_sur_plateau(plateau, adv):
            return -100000000 + profondeur

        if profondeur == 0 or self.plateau_plein(plateau):
            return self.evaluer_plateau(plateau, joueur_max)

        valides = self.trier_colonnes(self.colonnes_valides(plateau))

        # ── Joueur MAX ──
        if joueur_courant == joueur_max:
            meilleur = -10 ** 18
            for col in valides:
                lig = self._jouer_temp(plateau, col, joueur_courant)
                if lig is None:
                    continue
                score = self.minimax_alpha_beta(
                    plateau, profondeur - 1, alpha, beta,
                    joueur_max, self.autre_joueur(joueur_courant)
                )
                plateau[lig][col] = self.VIDE
                meilleur = max(meilleur, score)
                alpha = max(alpha, score)
                if alpha >= beta:
                    break
            return meilleur

        # ── Joueur MIN ──
        # CORRECTION BUG 2 : suppression du bloc "victoire immédiate" redondant
        # La vérification en tête de fonction gère déjà ce cas au niveau suivant.
        else:
            pire = 10 ** 18
            for col in valides:
                lig = self._jouer_temp(plateau, col, joueur_courant)
                if lig is None:
                    continue
                score = self.minimax_alpha_beta(
                    plateau, profondeur - 1, alpha, beta,
                    joueur_max, self.autre_joueur(joueur_courant)
                )
                plateau[lig][col] = self.VIDE
                pire = min(pire, score)
                beta = min(beta, score)
                if alpha >= beta:
                    break
            return pire

    def trier_colonnes(self, colonnes):
        """Trie du centre vers les bords pour améliorer l'élagage alpha-bêta."""
        centre = self.colonnes // 2
        return sorted(colonnes, key=lambda c: abs(c - centre))

    def calculer_scores_minimax(self, profondeur):
        scores = {}
        plateau = [ligne[:] for ligne in self.plateau]
        joueur_max = self.joueur_courant
        adv = self.autre_joueur(joueur_max)
        toutes_valides = self.trier_colonnes(self.colonnes_valides(plateau))

        # ── ÉTAPE 0 : Victoire immédiate ──
        for col in toutes_valides:
            pt = [ligne[:] for ligne in plateau]
            lig = self._jouer_temp(pt, col, joueur_max)
            if lig is None:
                continue
            if self._verifier_victoire_sur_plateau(pt, joueur_max):
                return {col: 100_000_000}

        # ── ÉTAPE 1 : Bloquer victoire immédiate adverse ──
        for col in toutes_valides:
            pt = [ligne[:] for ligne in plateau]
            lig = self._jouer_temp(pt, col, adv)
            if lig is None:
                continue
            if self._verifier_victoire_sur_plateau(pt, adv):
                pt2 = [ligne[:] for ligne in plateau]
                lig2 = self._jouer_temp(pt2, col, joueur_max)
                if lig2 is not None:
                    score = self.minimax_alpha_beta(
                        pt2, profondeur - 1, -10 ** 18, 10 ** 18,
                        joueur_max, self.autre_joueur(joueur_max)
                    )
                    return {col: score}

        # ── ÉTAPE 2 : Double menace — détection explicite AVANT minimax ──
        # Raison : le minimax peut rater ce cas si l'heuristique
        # sous-évalue la position intermédiaire et que l'élagage coupe la branche.
        for col in toutes_valides:
            pt = [ligne[:] for ligne in plateau]
            lig = self._jouer_temp(pt, col, joueur_max)
            if lig is None:
                continue

            if self.est_double_menace_apres_coup(pt, joueur_max):
                # Score fixe élevé — garantit la sélection de ce coup
                # Le décalage par distance au centre départage les égalités
                scores[col] = 50_000_000 - abs(col - self.colonnes // 2)
                continue

            # ── ÉTAPE 3 : Minimax pur ──
            score = self.minimax_alpha_beta(
                pt, profondeur - 1, -10 ** 18, 10 ** 18,
                joueur_max, self.autre_joueur(joueur_max)
            )
            scores[col] = score

        return scores

    def minimax(self, plateau, profondeur, joueur_max, joueur_courant):
        """Wrapper minimax sans alpha-bêta (usage externe)."""
        return self.minimax_alpha_beta(
            plateau, profondeur, -10 ** 18, 10 ** 18,
            joueur_max, joueur_courant
        )

    # ---------------- UTILITAIRES IA ----------------

    def est_coup_dangereux(self, plateau, col, joueur):
        """
        Retourne True si jouer col permet à l'adversaire de gagner immédiatement.
        CORRECTION BUG 3 : restauration propre du plateau dans tous les cas.
        """
        lig = self._jouer_temp(plateau, col, joueur)
        if lig is None:
            return True

        adv = self.autre_joueur(joueur)
        dangereux = False

        for c in self.colonnes_valides(plateau):
            l2 = self._jouer_temp(plateau, c, adv)
            if l2 is None:
                continue  # colonne pleine — skip sans corrompre le plateau
            if self._verifier_victoire_sur_plateau(plateau, adv):
                dangereux = True
                plateau[l2][c] = self.VIDE
                break
            plateau[l2][c] = self.VIDE

        plateau[lig][col] = self.VIDE  # toujours retiré en dernier
        return dangereux

    def est_coup_jouable(self, plateau, col):
        return plateau[0][col] == self.VIDE

    def est_double_menace_apres_coup(self, plateau, joueur):
        """
        Retourne True si le plateau actuel contient >= 2 coups gagnants immédiats.
        Doit être appelé sur un plateau où le coup a DÉJÀ été joué.
        """
        coups_gagnants = 0
        for col in self.colonnes_valides(plateau):
            lig = self._jouer_temp(plateau, col, joueur)
            if lig is not None:
                if self._verifier_victoire_sur_plateau(plateau, joueur):
                    coups_gagnants += 1
                plateau[lig][col] = self.VIDE
        return coups_gagnants >= 2

    # ---------------- BD UTILS ----------------

    def exporter_coups_string(self) -> str:
        return "".join(str(col + 1) for (_, col, _) in self.historique)

    def charger_depuis_bd(self, partie_tuple):
        (pid, created_at, lignes, colonnes, couleur_depart, joueur_courant,
         statut, resultat, confiance, coups, coups_sym, coups_can) = partie_tuple

        self.lignes = lignes
        self.colonnes = colonnes
        self.couleur_depart = couleur_depart

        self.plateau = [[self.VIDE for _ in range(self.colonnes)] for _ in range(self.lignes)]
        self.historique = []
        self.numero_partie = pid
        self.resultat = resultat

        joueur = self.couleur_depart
        for ch in (coups or ""):
            if not ch.isdigit():
                continue
            col = int(ch) - 1
            if 0 <= col < self.colonnes:
                for lig in range(self.lignes - 1, -1, -1):
                    if self.plateau[lig][col] == self.VIDE:
                        self.plateau[lig][col] = joueur
                        self.historique.append((lig, col, joueur))
                        break
                joueur = self.JAUNE if joueur == self.ROUGE else self.ROUGE

        self.joueur_courant = (
            joueur_courant if joueur_courant in (self.ROUGE, self.JAUNE) else joueur
        )