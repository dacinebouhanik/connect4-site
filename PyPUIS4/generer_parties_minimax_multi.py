from multiprocessing import Process
from generer_parties_minimax import jouer_partie_minimax
from db import inserer_partie

NB_PROCESSUS = 6
PARTIES_PAR_PROCESSUS = 100000


def worker(nb_parties):
    for _ in range(nb_parties):
        modele = jouer_partie_minimax()
        coups = modele.exporter_coups_string()

        inserer_partie(
            lignes=modele.lignes,
            colonnes=modele.colonnes,
            couleur_depart=modele.couleur_depart,
            joueur_courant=modele.joueur_courant,
            statut="finished",
            resultat=modele.resultat,
            coups=coups,
            confiance=2
        )


if __name__ == "__main__":
    processes = []

    for _ in range(NB_PROCESSUS):
        p = Process(target=worker, args=(PARTIES_PAR_PROCESSUS,))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

    print("Toutes les parties ont été générées.")