from vue import demander_mode, demander_parametres_robot
from controleur import Puissance4Controleur


if __name__ == "__main__":
    mode = demander_mode()

    #paramètres par dFt du rbt
    algo_robot = "aleatoire"
    profondeur = 3

    #Si au moins un rbot joue on dmd les paramètres
    if mode in (2, 3):
        algo_robot, profondeur = demander_parametres_robot()

    ctrl = Puissance4Controleur(mode, algo_robot=algo_robot,
                                profondeur_minimax=profondeur)
    ctrl.vue.lancer()
