from db import chercher_parties_similaires
import random


def proposer_coup_depuis_base(coups_actuels, joueur_courant, colonnes_valides):

    parties = chercher_parties_similaires(coups_actuels)

    if not parties:
        return None

    stats = {}

    for coups, resultat, confiance in parties:

        if len(coups) <= len(coups_actuels):
            continue

        prochain_coup = coups[len(coups_actuels)]

        if prochain_coup not in stats:
            stats[prochain_coup] = {
                "score": 0,
                "parties": 0
            }

        score = 0

        if resultat == "nul":
            score = 0.2

        elif resultat == "rouge":
            score = 1 if joueur_courant == 1 else -1

        elif resultat == "jaune":
            score = 1 if joueur_courant == 2 else -1

        stats[prochain_coup]["score"] += score * confiance
        stats[prochain_coup]["parties"] += 1

    if not stats:
        return None


    # supprimer coups avec trop peu de données
    MIN_PARTIES = 3

    coups_valides = {}

    for coup, data in stats.items():

        if data["parties"] >= MIN_PARTIES:

            moyenne = data["score"] / data["parties"]

            coups_valides[coup] = moyenne


    if not coups_valides:
        return None


    # trouver meilleur score
    best_score = max(coups_valides.values())

    meilleurs_coups = [
        int(c) - 1
        for c, s in coups_valides.items()
        if s == best_score
    ]


    # garder seulement colonnes jouables
    meilleurs_coups = [
        c for c in meilleurs_coups
        if c in colonnes_valides
    ]

    if not meilleurs_coups:
        return None


    return random.choice(meilleurs_coups)