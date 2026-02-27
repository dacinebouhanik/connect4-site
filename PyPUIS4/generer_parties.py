# generer_parties.py
import random
from db import inserer_partie

VIDE = 0
ROUGE = 1
JAUNE = 2

LIGNES = 9
COLONNES = 9


def creer_plateau():
    return [[VIDE for _ in range(COLONNES)] for _ in range(LIGNES)]


def colonne_valide(plateau, col):
    return plateau[0][col] == VIDE


def colonnes_valides(plateau):
    return [c for c in range(COLONNES) if colonne_valide(plateau, c)]


def jouer_coup(plateau, col, joueur):
    """Pose un pion dans la colonne. Retourne (ligne) ou None."""
    for lig in range(LIGNES - 1, -1, -1):
        if plateau[lig][col] == VIDE:
            plateau[lig][col] = joueur
            return lig
    return None


def victoire(plateau, joueur):
    # horizontal
    for i in range(LIGNES):
        for j in range(COLONNES - 3):
            if all(plateau[i][j+k] == joueur for k in range(4)):
                return True

    # vertical
    for j in range(COLONNES):
        for i in range(LIGNES - 3):
            if all(plateau[i+k][j] == joueur for k in range(4)):
                return True

    # diagonale \
    for i in range(LIGNES - 3):
        for j in range(COLONNES - 3):
            if all(plateau[i+k][j+k] == joueur for k in range(4)):
                return True

    # diagonale /
    for i in range(3, LIGNES):
        for j in range(COLONNES - 3):
            if all(plateau[i-k][j+k] == joueur for k in range(4)):
                return True

    return False


def simuler_partie_aleatoire():
    plateau = creer_plateau()
    coups = []
    joueur = ROUGE
    couleur_depart = ROUGE

    while True:
        valides = colonnes_valides(plateau)
        if not valides:
            # nul
            return "".join(coups), "finished", "nul", couleur_depart, joueur

        col = random.choice(valides)
        lig = jouer_coup(plateau, col, joueur)
        if lig is None:
            continue

        # on stocke le coup en 1..9
        coups.append(str(col + 1))

        if victoire(plateau, joueur):
            res = "rouge" if joueur == ROUGE else "jaune"
            return "".join(coups), "finished", res, couleur_depart, joueur

        # changer joueur
        joueur = JAUNE if joueur == ROUGE else ROUGE


def main():
    nb = 500
    ok_count = 0
    doublons = 0

    for i in range(1, nb + 1):
        coups, statut, resultat, couleur_depart, joueur_courant = simuler_partie_aleatoire()

        ok, msg, gid = inserer_partie(
            lignes=LIGNES,
            colonnes=COLONNES,
            couleur_depart=couleur_depart,
            joueur_courant=joueur_courant,
            statut=statut,
            resultat=resultat,
            coups=coups,
            confiance=1  # 1 = aléatoire
        )

        if ok:
            ok_count += 1
        else:
            # souvent c'est un doublon
            doublons += 1

        if i % 50 == 0:
            print(f"{i}/{nb} -> ok={ok_count}, doublons/erreurs={doublons}")

    print("Terminé.")
    print("Insérées :", ok_count)
    print("Doublons/erreurs :", doublons)


if __name__ == "__main__":
    main()
