# analyser_partie.py
# ============================================================
# Fonction clé en main pour l'oral
# Usage : python analyser_partie.py
# ============================================================

from modele import Puissance4Modele


def analyser(joueur_qui_joue, plateau, profondeur=20, temps_max=25.0):
    """
    Analyse une position et dit qui gagne et en combien de coups.

    Args:
        joueur_qui_joue : "ROUGE" ou "JAUNE"
        plateau         : liste 9x9 (0=vide, 1=rouge, 2=jaune)
        profondeur      : profondeur max de recherche
        temps_max       : temps max en secondes

    Returns:
        string lisible : "JAUNE gagne en 4 coups"
    """
    R, J = Puissance4Modele.ROUGE, Puissance4Modele.JAUNE

    m = Puissance4Modele.__new__(Puissance4Modele)
    m.lignes = 9
    m.colonnes = 9
    m.couleur_depart = R
    m.plateau = [row[:] for row in plateau]
    m.joueur_courant = R if joueur_qui_joue == "ROUGE" else J
    m.historique = []
    m.resultat = None
    m._init_zobrist()
    m._hash_courant = m._calculer_hash_complet()
    m.table_transposition = {}

    # Affichage du plateau
    sym = {0: ".", 1: "R", 2: "J"}
    print("  " + " ".join(str(i) for i in range(9)))
    for i in range(9):
        print(f"{i}|" + " ".join(sym[m.plateau[i][j]] for j in range(9)))
    print(f"\nC'est a {joueur_qui_joue} de jouer\n")

    # Analyse
    gagnant, coups = m.analyser_position(profondeur, temps_max)

    # Meilleur coup
    scores = m.calculer_scores_minimax(profondeur, temps_max)
    meilleur = max(scores, key=scores.get) if scores else None

    # Résultat lisible
    if gagnant in ("ROUGE", "JAUNE"):
        resultat = f"{gagnant} gagne en {coups} coup(s) (meilleur coup : colonne {meilleur})"
    elif gagnant == "NUL":
        resultat = f"Match nul avec jeu parfait (meilleur coup : colonne {meilleur})"
    else:
        resultat = f"Pas de victoire forcee trouvee (meilleur coup : colonne {meilleur})"

    print(f">>> {resultat}")
    return resultat


# ============================================================
#  Exemple : position du prof
# ============================================================
if __name__ == "__main__":
    plateau = [
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,1,0,0,0,0,0],
        [0,0,0,2,1,0,0,0,0],
        [0,0,0,2,2,0,1,0,0],
        [0,0,0,2,1,0,2,0,0],
        [0,2,0,1,2,1,1,0,0],
        [2,1,1,2,1,1,1,2,0],
    ]

    print("=" * 50)
    print("  ANALYSE DE LA POSITION")
    print("=" * 50)
    analyser("JAUNE", plateau)