# generer_parties_minimax.py

from modele import Puissance4Modele
from db import inserer_partie
import random

NB_PARTIES = 300
CONFIANCE  = 2    # 2 = minimax


def ouverture_aleatoire(modele, nb_coups):
    """Joue nb_coups aléatoires pour diversifier les débuts de partie."""
    for _ in range(nb_coups):
        valides = modele.colonnes_valides()
        if not valides:
            return

        col = random.choice(valides)
        modele.jouer_coup(col)

        coords = modele.verifier_victoire(modele.joueur_courant)
        if coords:
            modele.definir_resultat(
                "rouge" if modele.joueur_courant == modele.ROUGE else "jaune"
            )
            return

        if modele.plateau_plein():
            modele.definir_resultat("nul")
            return

        modele.changer_joueur()


def choisir_coup(modele, profondeur, epsilon=0.10):
    """
    Choisit un coup via calculer_scores_minimax.

    ✅ epsilon-greedy : 10% du temps joue aléatoirement
       → évite que toutes les parties soient identiques
       → génère plus de positions diversifiées pour l'entraînement
    """
    # Exploration aléatoire
    if random.random() < epsilon:
        valides = modele.colonnes_valides()
        return random.choice(valides) if valides else None

    scores = modele.calculer_scores_minimax(profondeur)

    if not scores:
        return None

    best_score = max(scores.values())
    best_cols  = [col for col, sc in scores.items() if sc == best_score]

    # Tie-break : préférer la colonne centrale
    centre = modele.colonnes // 2
    return min(best_cols, key=lambda c: abs(c - centre))


def jouer_partie_minimax():
    """
    Joue une partie complète avec variété :
    - Ouverture aléatoire 2..6 coups
    - Profondeur rouge et jaune tirées indépendamment (3, 4 ou 5)
    - Epsilon-greedy 10% pour éviter le déterminisme total
    """
    modele = Puissance4Modele()
    modele.mettre_a_jour_parametres(9, 9, 1)
    modele.nouvelle_partie()

    # ✅ Profondeurs différentes pour chaque joueur → parties variées
    profondeur_rouge =7
    profondeur_jaune =7

    # ✅ Ouverture plus large (2..6 coups) → positions de départ diversifiées
    nb_ouverture = random.randint(2, 6)
    ouverture_aleatoire(modele, nb_ouverture)

    if modele.resultat is not None:
        return modele

    # Minimax jusqu'à la fin
    while True:
        joueur     = modele.joueur_courant
        profondeur = profondeur_rouge if joueur == modele.ROUGE else profondeur_jaune

        col = choisir_coup(modele, profondeur, epsilon=0.10)

        if col is None:
            modele.definir_resultat("nul")
            break

        modele.jouer_coup(col)

        if modele.verifier_victoire(joueur):
            modele.definir_resultat(
                "rouge" if joueur == modele.ROUGE else "jaune"
            )
            break

        if modele.plateau_plein():
            modele.definir_resultat("nul")
            break

        modele.changer_joueur()

    return modele


def main():
    ok_count = 0
    erreurs  = 0
    doublons = 0

    print(f"Génération de {NB_PARTIES} parties minimax...")

    for i in range(NB_PARTIES):
        modele = jouer_partie_minimax()
        coups  = modele.exporter_coups_string()

        ok, msg, _ = inserer_partie(
            lignes         = modele.lignes,
            colonnes       = modele.colonnes,
            couleur_depart = modele.couleur_depart,
            joueur_courant = modele.joueur_courant,
            statut         = "finished",
            resultat       = modele.resultat,
            coups          = coups,
            confiance      = CONFIANCE
        )

        if ok:
            ok_count += 1
        elif "Doublon" in msg:
            doublons += 1
        else:
            erreurs += 1
            if erreurs <= 5:
                print(f"  Erreur : {msg}")

        if (i + 1) % 25 == 0:
            print(
                f"  {i+1}/{NB_PARTIES} → "
                f"ok={ok_count} | doublons={doublons} | erreurs={erreurs}"
            )

    print(f"\nTerminé.")
    print(f"  Insérées : {ok_count}")
    print(f"  Doublons : {doublons}")
    print(f"  Erreurs  : {erreurs}")


if __name__ == "__main__":
    main()
