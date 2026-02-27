# generer_parties_minimax.py

from modele import Puissance4Modele
from db import inserer_partie
import random

NB_PARTIES = 300
PROFONDEUR = 2
CONFIANCE = 2  # 2 = minimax


def ouverture_aleatoire(modele, nb_coups):
    """Joue nb_coups aléatoires pour diversifier les débuts."""
    for _ in range(nb_coups):
        valides = modele.colonnes_valides()
        if not valides:
            return

        col = random.choice(valides)
        modele.jouer_coup(col)

        # check fin
        coords = modele.verifier_victoire(modele.joueur_courant)
        if coords:
            modele.definir_resultat("rouge" if modele.joueur_courant == modele.ROUGE else "jaune")
            return

        if modele.plateau_plein():
            modele.definir_resultat("nul")
            return

        modele.changer_joueur()


def choisir_coup_minimax(modele, profondeur):
    joueur = modele.joueur_courant
    plateau_copy = [ligne[:] for ligne in modele.plateau]
    valides = modele.colonnes_valides(plateau_copy)

    if not valides:
        return None

    meilleur_score = -10**9
    meilleurs_cols = []

    for col in valides:
        lig = modele._jouer_temp(plateau_copy, col, joueur)
        if lig is None:
            continue

        score = modele.minimax(
            plateau_copy,
            profondeur - 1,
            joueur,
            modele.autre_joueur(joueur)
        )

        plateau_copy[lig][col] = modele.VIDE  # annuler le coup temp

        if score > meilleur_score:
            meilleur_score = score
            meilleurs_cols = [col]
        elif score == meilleur_score:
            meilleurs_cols.append(col)

    # tie-break aléatoire
    if meilleurs_cols:
        return random.choice(meilleurs_cols)
    return random.choice(valides)


def jouer_partie_minimax():
    modele = Puissance4Modele()
    modele.mettre_a_jour_parametres(9, 9, 1)  # force 9x9
    modele.nouvelle_partie()

    # ouverture variable 1..3 coups
    nb_ouverture = random.randint(1, 3)
    ouverture_aleatoire(modele, nb_ouverture)

    # si partie déjà finie à cause de l'ouverture
    if modele.resultat is not None:
        return modele

    # minimax jusqu'à la fin
    while True:
        col = choisir_coup_minimax(modele, PROFONDEUR)
        if col is None:
            modele.definir_resultat("nul")
            break

        joueur = modele.joueur_courant
        modele.jouer_coup(col)

        if modele.verifier_victoire(joueur):
            modele.definir_resultat("rouge" if joueur == modele.ROUGE else "jaune")
            break

        if modele.plateau_plein():
            modele.definir_resultat("nul")
            break

        modele.changer_joueur()

    return modele


def main():
    ok_count = 0
    erreurs = 0

    for i in range(NB_PARTIES):
        modele = jouer_partie_minimax()
        coups = modele.exporter_coups_string()

        ok, msg, _ = inserer_partie(
            lignes=modele.lignes,
            colonnes=modele.colonnes,
            couleur_depart=modele.couleur_depart,
            joueur_courant=modele.joueur_courant,
            statut="finished",
            resultat=modele.resultat,
            coups=coups,
            confiance=CONFIANCE
        )

        if ok:
            ok_count += 1
        else:
            erreurs += 1
            if erreurs <= 5:
                print("Exemple erreur:", msg)

        if (i + 1) % 25 == 0:
            print(f"{i+1}/{NB_PARTIES} -> ok={ok_count}, erreurs={erreurs}")

    print("Terminé.")
    print("Insérées :", ok_count)
    print("Erreurs :", erreurs)


if __name__ == "__main__":
    main()
