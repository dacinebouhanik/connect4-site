# modele_corrige.py
import json, random, os, time


class Puissance4Modele:
    VIDE = 0
    ROUGE = 1
    JAUNE = 2
    SCORE_VICTOIRE = 1_000_000
    DOSSIER_SAUVES = "sauvegardes"

    def __init__(self, chemin_config="config.json"):
        self.chemin_config = chemin_config
        self.charger_config()
        self.plateau = self.creer_plateau()
        self.joueur_courant = self.couleur_depart
        self.historique = []
        self.numero_partie = 1
        self.resultat = None
        self._init_zobrist()
        self._hash_courant = self._calculer_hash_complet()
        self.table_transposition = {}
        os.makedirs(self.DOSSIER_SAUVES, exist_ok=True)

    # ================ ZOBRIST ================
    def _init_zobrist(self):
        rng = random.Random(42)
        self._zobrist = {}
        for i in range(self.lignes):
            for j in range(self.colonnes):
                for joueur in (self.ROUGE, self.JAUNE):
                    self._zobrist[(i, j, joueur)] = rng.getrandbits(64)

    def _calculer_hash_complet(self):
        h = 0
        for i in range(self.lignes):
            for j in range(self.colonnes):
                if self.plateau[i][j] != self.VIDE:
                    h ^= self._zobrist[(i, j, self.plateau[i][j])]
        return h

    # ================ CONFIG ================
    def charger_config(self):
        if not os.path.exists(self.chemin_config):
            self.config = {"lignes": 9, "colonnes": 9, "couleur_depart": 1}
        else:
            with open(self.chemin_config, "r", encoding="utf-8") as f:
                contenu = f.read().strip()
            if contenu == "":
                self.config = {"lignes": 9, "colonnes": 9, "couleur_depart": 1}
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

    # ================ PLATEAU ================
    def creer_plateau(self):
        return [[self.VIDE] * self.colonnes for _ in range(self.lignes)]

    def nouvelle_partie(self):
        self.plateau = self.creer_plateau()
        self.joueur_courant = self.couleur_depart
        self.historique = []
        self.numero_partie += 1
        self.resultat = None
        self._hash_courant = 0
        self.table_transposition = {}

    def jouer_coup(self, colonne):
        if colonne < 0 or colonne >= self.colonnes:
            return None
        for lig in range(self.lignes - 1, -1, -1):
            if self.plateau[lig][colonne] == self.VIDE:
                self.plateau[lig][colonne] = self.joueur_courant
                self.historique.append((lig, colonne, self.joueur_courant))
                self._hash_courant ^= self._zobrist[(lig, colonne, self.joueur_courant)]
                return lig
        return None

    def annuler_dernier_coup(self):
        if not self.historique:
            return False
        lig, col, joueur = self.historique.pop()
        self._hash_courant ^= self._zobrist[(lig, col, joueur)]
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
        for j in range(self.colonnes):
            if plateau[0][j] == self.VIDE:
                return False
        return True

    def definir_resultat(self, resultat):
        self.resultat = resultat

    # ================ VICTOIRE INCREMENTALE ================
    def _victoire_autour(self, plateau, lig, col, joueur):
        L, C = self.lignes, self.colonnes
        for di, dj in ((0,1),(1,0),(1,1),(1,-1)):
            count = 1
            r, c = lig + di, col + dj
            while 0 <= r < L and 0 <= c < C and plateau[r][c] == joueur:
                count += 1; r += di; c += dj
            r, c = lig - di, col - dj
            while 0 <= r < L and 0 <= c < C and plateau[r][c] == joueur:
                count += 1; r -= di; c -= dj
            if count >= 4:
                return True
        return False

    def _verifier_victoire_sur_plateau(self, plateau, joueur):
        L, C = self.lignes, self.colonnes
        for i in range(L):
            for j in range(C - 3):
                if plateau[i][j] == joueur and plateau[i][j+1] == joueur and plateau[i][j+2] == joueur and plateau[i][j+3] == joueur:
                    return True
        for j in range(C):
            for i in range(L - 3):
                if plateau[i][j] == joueur and plateau[i+1][j] == joueur and plateau[i+2][j] == joueur and plateau[i+3][j] == joueur:
                    return True
        for i in range(L - 3):
            for j in range(C - 3):
                if plateau[i][j] == joueur and plateau[i+1][j+1] == joueur and plateau[i+2][j+2] == joueur and plateau[i+3][j+3] == joueur:
                    return True
        for i in range(3, L):
            for j in range(C - 3):
                if plateau[i][j] == joueur and plateau[i-1][j+1] == joueur and plateau[i-2][j+2] == joueur and plateau[i-3][j+3] == joueur:
                    return True
        return False

    def verifier_victoire(self, joueur):
        if not self._verifier_victoire_sur_plateau(self.plateau, joueur):
            return None
        p = self.plateau; L, C = self.lignes, self.colonnes
        for i in range(L):
            for j in range(C-3):
                if p[i][j]==joueur and p[i][j+1]==joueur and p[i][j+2]==joueur and p[i][j+3]==joueur:
                    return [(i,j),(i,j+1),(i,j+2),(i,j+3)]
        for j in range(C):
            for i in range(L-3):
                if p[i][j]==joueur and p[i+1][j]==joueur and p[i+2][j]==joueur and p[i+3][j]==joueur:
                    return [(i,j),(i+1,j),(i+2,j),(i+3,j)]
        for i in range(L-3):
            for j in range(C-3):
                if p[i][j]==joueur and p[i+1][j+1]==joueur and p[i+2][j+2]==joueur and p[i+3][j+3]==joueur:
                    return [(i,j),(i+1,j+1),(i+2,j+2),(i+3,j+3)]
        for i in range(3,L):
            for j in range(C-3):
                if p[i][j]==joueur and p[i-1][j+1]==joueur and p[i-2][j+2]==joueur and p[i-3][j+3]==joueur:
                    return [(i,j),(i-1,j+1),(i-2,j+2),(i-3,j+3)]
        return None

    # ================ UTILITAIRES ================
    def colonnes_valides(self, plateau=None):
        if plateau is None: plateau = self.plateau
        return [j for j in range(self.colonnes) if plateau[0][j] == self.VIDE]

    def trier_colonnes(self, colonnes):
        centre = self.colonnes // 2
        return sorted(colonnes, key=lambda c: abs(c - centre))

    def coup_aleatoire(self):
        valides = self.colonnes_valides()
        return random.choice(valides) if valides else None

    def _jouer_temp(self, plateau, col, joueur):
        if col < 0 or col >= self.colonnes: return None
        for lig in range(self.lignes - 1, -1, -1):
            if plateau[lig][col] == self.VIDE:
                plateau[lig][col] = joueur
                return lig
        return None

    def _ligne_libre(self, plateau, col):
        for lig in range(self.lignes - 1, -1, -1):
            if plateau[lig][col] == self.VIDE:
                return lig
        return None

    # ================ HEURISTIQUE ================
    def _score_fenetre(self, fenetre, joueur_max):
        adv = self.autre_joueur(joueur_max)
        c_j = fenetre.count(joueur_max)
        c_a = fenetre.count(adv)
        c_v = fenetre.count(self.VIDE)
        if c_j > 0 and c_a > 0: return 0
        if c_j == 3 and c_v == 1: return 200
        if c_j == 2 and c_v == 2: return 50
        if c_a == 3 and c_v == 1: return -220
        if c_a == 2 and c_v == 2: return -60
        return 0

    def evaluer_plateau(self, plateau, joueur_max):
        score = 0; L, C = self.lignes, self.colonnes; centre = C // 2
        for i in range(L):
            if plateau[i][centre] == joueur_max: score += 20
        for i in range(L):
            for j in range(C-3):
                score += self._score_fenetre([plateau[i][j+k] for k in range(4)], joueur_max)
        for j in range(C):
            for i in range(L-3):
                score += self._score_fenetre([plateau[i+k][j] for k in range(4)], joueur_max)
        for i in range(L-3):
            for j in range(C-3):
                score += self._score_fenetre([plateau[i+k][j+k] for k in range(4)], joueur_max)
        for i in range(3,L):
            for j in range(C-3):
                score += self._score_fenetre([plateau[i-k][j+k] for k in range(4)], joueur_max)
        return score

    # ================ TRI INTELLIGENT ================
    def _trier_coups(self, plateau, joueur_courant, tt_best_col=None):
        """
        Ordre de priorité :
          1. Victoire immédiate
          2. Double menace (fork) → victoire forcée en 2
          3. Blocage adverse
          4. Bloquer double menace adverse
          5. Centre d'abord
        """
        valides = self.colonnes_valides(plateau)
        adv = self.autre_joueur(joueur_courant)
        centre = self.colonnes // 2
        gagnants, forks, bloquants, anti_forks, normaux = [], [], [], [], []

        for col in valides:
            if col == tt_best_col:
                continue
            lig = self._ligne_libre(plateau, col)
            if lig is None: continue

            # 1. Victoire immédiate ?
            plateau[lig][col] = joueur_courant
            if self._victoire_autour(plateau, lig, col, joueur_courant):
                plateau[lig][col] = self.VIDE; gagnants.append(col); continue

            # 2. Double menace (fork) ?
            if self._compte_menaces(plateau, joueur_courant) >= 2:
                plateau[lig][col] = self.VIDE; forks.append(col); continue
            plateau[lig][col] = self.VIDE

            # 3. Blocage victoire adverse ?
            plateau[lig][col] = adv
            if self._victoire_autour(plateau, lig, col, adv):
                plateau[lig][col] = self.VIDE; bloquants.append(col); continue

            # 4. Bloquer fork adverse ?
            if self._compte_menaces(plateau, adv) >= 2:
                plateau[lig][col] = self.VIDE; anti_forks.append(col); continue
            plateau[lig][col] = self.VIDE

            normaux.append(col)

        normaux.sort(key=lambda c: abs(c - centre))
        result = gagnants + forks + bloquants + anti_forks + normaux
        if tt_best_col is not None and tt_best_col in valides:
            result.insert(0, tt_best_col)
        return result

    def _compte_menaces(self, plateau, joueur):
        """Compte combien de colonnes donnent une victoire immédiate."""
        count = 0
        for col in range(self.colonnes):
            if plateau[0][col] != self.VIDE:
                continue
            lig = self._ligne_libre(plateau, col)
            if lig is None: continue
            plateau[lig][col] = joueur
            if self._victoire_autour(plateau, lig, col, joueur):
                count += 1
            plateau[lig][col] = self.VIDE
            if count >= 2:
                return count
        return count

    # ================ MINIMAX OPTIMISE ================
    def minimax_alpha_beta(self, plateau, depth, max_depth, alpha, beta,
                           joueur_max, joueur_courant, zhash,
                           dernier_lig=None, dernier_col=None, dernier_joueur=None):

        # Victoire du dernier joueur (O(1))
        if dernier_lig is not None and dernier_joueur is not None:
            if self._victoire_autour(plateau, dernier_lig, dernier_col, dernier_joueur):
                if dernier_joueur == joueur_max:
                    return self.SCORE_VICTOIRE - depth
                else:
                    return -self.SCORE_VICTOIRE + depth

            # Double menace du dernier joueur = victoire forcée en +2
            # (l'adversaire ne peut bloquer qu'une seule colonne)
            if self._compte_menaces(plateau, dernier_joueur) >= 2:
                if dernier_joueur == joueur_max:
                    return self.SCORE_VICTOIRE - (depth + 2)
                else:
                    return -self.SCORE_VICTOIRE + (depth + 2)

        if self.plateau_plein(plateau): return 0
        if depth >= max_depth:
            return self.evaluer_plateau(plateau, joueur_max)

        # Transposition table lookup
        tt_key = (zhash, joueur_courant)
        tt_entry = self.table_transposition.get(tt_key)
        depth_restante = max_depth - depth
        tt_best_col = None

        if tt_entry is not None:
            tt_dr, tt_flag, tt_score, tt_bc = tt_entry
            tt_best_col = tt_bc
            if tt_dr >= depth_restante:
                if tt_flag == 0: return tt_score
                elif tt_flag == 1 and tt_score > alpha: alpha = tt_score
                elif tt_flag == 2 and tt_score < beta: beta = tt_score
                if alpha >= beta: return tt_score

        coups = self._trier_coups(plateau, joueur_courant, tt_best_col)
        if not coups: return 0

        original_alpha = alpha
        adv = self.autre_joueur(joueur_courant)
        best = -10**18 if joueur_courant == joueur_max else 10**18
        best_col = coups[0]

        for col in coups:
            lig = self._jouer_temp(plateau, col, joueur_courant)
            if lig is None: continue
            new_hash = zhash ^ self._zobrist[(lig, col, joueur_courant)]

            score = self.minimax_alpha_beta(
                plateau, depth+1, max_depth, alpha, beta,
                joueur_max, adv, new_hash, lig, col, joueur_courant
            )
            plateau[lig][col] = self.VIDE

            if joueur_courant == joueur_max:
                if score > best: best = score; best_col = col
                alpha = max(alpha, score)
            else:
                if score < best: best = score; best_col = col
                beta = min(beta, score)
            if alpha >= beta: break

        # Store TT avec le meilleur coup
        if best <= original_alpha: flag = 2
        elif best >= beta: flag = 1
        else: flag = 0
        self.table_transposition[tt_key] = (depth_restante, flag, best, best_col)

        return best

    # ================ ITERATIVE DEEPENING ================
    def calculer_scores_minimax(self, profondeur, temps_max=25.0):
        """
        Iterative deepening : cherche prof 2, 4, 6... jusqu'à `profondeur`.
        La TT des passes précédentes accélère les suivantes.
        S'arrête si le temps dépasse `temps_max`.
        """
        self.table_transposition = {}
        joueur_max = self.joueur_courant
        adv = self.autre_joueur(joueur_max)

        zhash = 0
        for i in range(self.lignes):
            for j in range(self.colonnes):
                if self.plateau[i][j] != self.VIDE:
                    zhash ^= self._zobrist[(i, j, self.plateau[i][j])]

        coups_init = self._trier_coups(self.plateau, joueur_max)

        # Victoire immédiate
        for col in coups_init:
            pt = [r[:] for r in self.plateau]
            lig = self._jouer_temp(pt, col, joueur_max)
            if lig is not None and self._victoire_autour(pt, lig, col, joueur_max):
                return {col: self.SCORE_VICTOIRE - 1}

        derniers_scores = {}
        t_start = time.time()

        for d in range(2, profondeur + 1, 2):
            scores = {}
            for col in coups_init:
                if time.time() - t_start > temps_max:
                    return derniers_scores if derniers_scores else scores

                pt = [r[:] for r in self.plateau]
                lig = self._jouer_temp(pt, col, joueur_max)
                if lig is None: continue

                new_hash = zhash ^ self._zobrist[(lig, col, joueur_max)]
                score = self.minimax_alpha_beta(
                    pt, 1, d, -10**18, 10**18,
                    joueur_max, adv, new_hash, lig, col, joueur_max
                )
                scores[col] = score

            derniers_scores = scores

            # Si victoire forcée trouvée, inutile de chercher plus
            best = max(scores.values()) if scores else 0
            if best > self.SCORE_VICTOIRE // 2:
                break

        return derniers_scores

    # ================ ANALYSE POSITION ================
    def analyser_position(self, profondeur=20, temps_max=25.0):
        scores = self.calculer_scores_minimax(profondeur, temps_max)
        if not scores: return ("NUL", None)

        best_score = max(scores.values())

        if best_score > self.SCORE_VICTOIRE // 2:
            demi_coups = self.SCORE_VICTOIRE - best_score
            coups = (demi_coups + 1) // 2
            gagnant = "ROUGE" if self.joueur_courant == self.ROUGE else "JAUNE"
            return (gagnant, coups)

        if best_score < -(self.SCORE_VICTOIRE // 2):
            demi_coups = self.SCORE_VICTOIRE + best_score
            coups = (demi_coups + 1) // 2
            adv = self.autre_joueur(self.joueur_courant)
            gagnant = "ROUGE" if adv == self.ROUGE else "JAUNE"
            return (gagnant, coups)

        if best_score == 0 and self.plateau_plein():
            return ("NUL", None)
        return ("INCERTAIN", None)

    def meilleur_coup(self, profondeur=20, temps_max=25.0):
        scores = self.calculer_scores_minimax(profondeur, temps_max)
        if not scores: return None
        return max(scores, key=scores.get)

    # ================ WRAPPER LEGACY ================
    def minimax(self, plateau, profondeur, joueur_max, joueur_courant):
        zhash = 0
        for i in range(self.lignes):
            for j in range(self.colonnes):
                if plateau[i][j] != self.VIDE:
                    zhash ^= self._zobrist[(i, j, plateau[i][j])]
        return self.minimax_alpha_beta(
            plateau, 0, profondeur, -10**18, 10**18,
            joueur_max, joueur_courant, zhash
        )

    # ================ UTILITAIRES IA ================
    def est_coup_dangereux(self, plateau, col, joueur):
        lig = self._jouer_temp(plateau, col, joueur)
        if lig is None: return True
        adv = self.autre_joueur(joueur)
        dangereux = False
        for c in self.colonnes_valides(plateau):
            l2 = self._jouer_temp(plateau, c, adv)
            if l2 is None: continue
            if self._victoire_autour(plateau, l2, c, adv):
                dangereux = True; plateau[l2][c] = self.VIDE; break
            plateau[l2][c] = self.VIDE
        plateau[lig][col] = self.VIDE
        return dangereux

    def est_coup_jouable(self, plateau, col):
        return plateau[0][col] == self.VIDE

    def est_double_menace_apres_coup(self, plateau, joueur):
        coups_gagnants = 0
        for col in self.colonnes_valides(plateau):
            lig = self._jouer_temp(plateau, col, joueur)
            if lig is not None:
                if self._victoire_autour(plateau, lig, col, joueur):
                    coups_gagnants += 1
                plateau[lig][col] = self.VIDE
        return coups_gagnants >= 2

    def mettre_a_jour_parametres(self, lignes, colonnes, couleur_depart):
        if lignes < 4 or colonnes < 4: return False
        self.lignes = lignes
        self.colonnes = colonnes
        self.couleur_depart = couleur_depart
        self._init_zobrist()
        self.sauver_config()
        self.nouvelle_partie()
        return True

    # ================ BD UTILS ================
    def exporter_coups_string(self) -> str:
        return "".join(str(col + 1) for (_, col, _) in self.historique)

    def charger_depuis_bd(self, partie_tuple):
        (pid, created_at, lignes, colonnes, couleur_depart, joueur_courant,
         statut, resultat, confiance, coups, coups_sym, coups_can) = partie_tuple
        self.lignes = lignes
        self.colonnes = colonnes
        self.couleur_depart = couleur_depart
        self.plateau = [[self.VIDE]*self.colonnes for _ in range(self.lignes)]
        self.historique = []
        self.numero_partie = pid
        self.resultat = resultat
        joueur = self.couleur_depart
        for ch in (coups or ""):
            if not ch.isdigit(): continue
            col = int(ch) - 1
            if 0 <= col < self.colonnes:
                for lig in range(self.lignes - 1, -1, -1):
                    if self.plateau[lig][col] == self.VIDE:
                        self.plateau[lig][col] = joueur
                        self.historique.append((lig, col, joueur))
                        break
                joueur = self.autre_joueur(joueur)
        self.joueur_courant = (
            joueur_courant if joueur_courant in (self.ROUGE, self.JAUNE) else joueur
        )