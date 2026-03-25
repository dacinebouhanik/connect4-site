# test_complet_ia.py

from modele import Puissance4Modele


# ---------------- CHARGER POSITION PROF ----------------

def charger_position_prof(modele):
    V = modele.VIDE
    R = modele.ROUGE
    J = modele.JAUNE

    modele.plateau = [
        [V, V, V, V, V, V, V, V, V],  # L9
        [V, V, V, V, V, V, V, V, V],  # L8
        [V, V, V, V, V, V, V, V, V],  # L7
        [V, V, V, R, V, V, V, V, V],  # L6
        [V, V, V, J, R, V, V, V, V],  # L5
        [V, V, V, J, J, V, R, V, V],  # L4
        [V, V, V, J, R, V, J, V, V],  # L3
        [J, J, V, R, J, V, R, V, V],  # L2
        [J, R, R, J, R, R, R, J, V],  # L1
    ]

    modele.joueur_courant = J
    modele.historique = []
    modele.resultat = None


# ---------------- AFFICHAGE ----------------

def afficher_plateau(modele):
    symboles = {
        modele.VIDE: ".",
        modele.ROUGE: "R",
        modele.JAUNE: "J"
    }

    print("\nPlateau actuel :\n")
    for i, ligne in enumerate(modele.plateau):
        print(f"L{modele.lignes - i} :", " ".join(symboles[x] for x in ligne))
    print()


# ---------------- TEST MINIMAX ----------------

def test_minimax(modele, profondeur=5):
    print("===== TEST MINIMAX =====\n")

    scores = modele.calculer_scores_minimax(profondeur)

    print("Scores :")
    for col in sorted(scores):
        print(f"col {col} -> {scores[col]}")

    if scores:
        meilleur = max(scores, key=scores.get)
        print("\nMeilleur coup trouvé :", meilleur)
    else:
        print("Aucun coup trouvé")

    print("\n========================\n")


# ---------------- TEST DOUBLE MENACE ----------------

def test_double_menace(modele):
    print("===== TEST DOUBLE MENACE =====\n")

    joueur = modele.joueur_courant

    for col in range(modele.colonnes):
        pt = [ligne[:] for ligne in modele.plateau]

        lig = modele._jouer_temp(pt, col, joueur)
        if lig is None:
            print(f"col {col} -> impossible")
            continue

        # Double menace
        dm = modele.est_double_menace_apres_coup(pt, joueur)

        # Compter coups gagnants
        coups_gagnants = 0
        for c2 in modele.colonnes_valides(pt):
            l2 = modele._jouer_temp(pt, c2, joueur)
            if l2 is not None:
                if modele._verifier_victoire_sur_plateau(pt, joueur):
                    coups_gagnants += 1
                pt[l2][c2] = modele.VIDE

        # Score heuristique
        score = modele.evaluer_plateau(pt, joueur)

        print(f"col {col} -> double menace ? {dm} | coups gagnants = {coups_gagnants} | score = {score}")

        pt[lig][col] = modele.VIDE

    print("\n=============================\n")


# ---------------- TEST PROFONDEUR ----------------

def test_profondeurs(modele):
    print("===== TEST PROFONDEUR =====\n")

    for d in range(3, 8):
        scores = modele.calculer_scores_minimax(profondeur=d)
        if scores:
            meilleur = max(scores, key=scores.get)
            print(f"profondeur {d} -> meilleur coup : {meilleur}")
        else:
            print(f"profondeur {d} -> aucun coup")

    print("\n===========================\n")


# ---------------- MAIN ----------------

if __name__ == "__main__":
    modele = Puissance4Modele()

    charger_position_prof(modele)
    afficher_plateau(modele)

    test_minimax(modele, profondeur=5)
    test_double_menace(modele)
    test_profondeurs(modele)