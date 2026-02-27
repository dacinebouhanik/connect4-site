from db import chercher_parties_similaires

def proposer_coup_depuis_base(coups_actuels):
    parties = chercher_parties_similaires(coups_actuels)

    if not parties:
        return None  # pas assez de données

    stats = {}

    for coups, resultat, confiance in parties:
        if len(coups) <= len(coups_actuels):
            continue

        prochain_coup = coups[len(coups_actuels)]

        if prochain_coup not in stats:
            stats[prochain_coup] = 0

        # simple scoring
        if resultat == "rouge":
            stats[prochain_coup] += 2 * confiance
        elif resultat == "jaune":
            stats[prochain_coup] += 1 * confiance
        else:
            stats[prochain_coup] += 0.5 * confiance

    if not stats:
        return None

    # meilleur score
    meilleur = max(stats, key=stats.get)
    return int(meilleur)
