import numpy as np
import tensorflow as tf
from ai_tf import creer_cerveau_tf, preparer_tenseur
from modele import Puissance4Modele


def generer_donnees_entrainement(nb_parties=100):
    """Fait jouer le Minimax contre lui-même pour créer des exemples"""
    X = []  # Les plateaux (Entrées)
    Y = []  # Les meilleurs coups (Sorties)

    jeu = Puissance4Modele()

    for i in range(nb_parties):
        jeu.nouvelle_partie()
        print(f"Simulation partie {i + 1}/{nb_parties}...")

        while jeu.resultat is None:
            # 1. On demande au Minimax le meilleur coup (Profondeur 2 ou 3 suffit)
            scores = jeu.calculer_scores_minimax(3)
            if not scores: break

            best_col = max(scores, key=scores.get)

            # 2. On enregistre la situation AVANT de jouer
            tenseur = preparer_tenseur(jeu.plateau, jeu.joueur_courant)
            X.append(tenseur)

            # 3. On crée la "cible" (un vecteur de 9 avec 1 sur le bon coup)
            cible = np.zeros(9)
            cible[best_col] = 1.0
            Y.append(cible)

            # 4. On joue le coup pour continuer la partie
            jeu.jouer_coup(best_col)
            jeu.verifier_victoire(jeu.joueur_courant)
            if not jeu.resultat:
                jeu.changer_joueur()

    return np.array(X), np.array(Y)


# --- LANCEMENT DE L'ENTRAÎNEMENT ---
if __name__ == "__main__":
    # 1. On génère 200 parties de prof (Minimax)
    print("Mise en place de l'école... Génération des données.")
    X_train, Y_train = generer_donnees_entrainement(200)

    # 2. On crée le cerveau
    cerveau = creer_cerveau_tf()

    # 3. L'IA étudie les données (10 passages sur les données)
    print("L'IA étudie les coups du maître...")
    cerveau.fit(X_train, Y_train, epochs=10, batch_size=32)

    # 4. On sauvegarde le cerveau entraîné
    cerveau.save('cerveau_expert.h5')
    print("Entraînement terminé ! Fichier 'cerveau_expert.h5' créé.")