from db import chercher_parties_similaires

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
            stats[prochain_coup] = 0

        score = 0

        if resultat == "nul":
            score = 0.5

        elif resultat == "rouge":
            score = 1 if joueur_courant == 1 else -1

        elif resultat == "jaune":
            score = 1 if joueur_courant == 2 else -1

        stats[prochain_coup] += score * confiance

    if not stats:
        return None

    meilleur = max(stats, key=stats.get)

    col = int(meilleur) - 1

    if col not in colonnes_valides:
        return None

    return col