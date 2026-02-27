# controleur.py

from db import inserer_partie, lister_parties_jeu, get_partie

from modele import Puissance4Modele
from vue import Puissance4Vue


class Puissance4Controleur:
    def __init__(self, mode, algo_robot="aleatoire", profondeur_minimax=3):
        self.mode = mode
        self.algo_robot = algo_robot      # "aleatoire" ou "minimax"
        self.profondeur_minimax = profondeur_minimax

        self.modele = Puissance4Modele()
        self.vue = Puissance4Vue(self.modele, self, mode)

        # mode 2 : on considère que l'humain est ROUGE
        self.humain = self.modele.ROUGE if mode == 2 else None

        # pour la relecture
        self.replay_coups = None
        self.replay_index = 0

        if self.mode == 3:
            # robots vs robots
            self.vue.root.after(400, self.robot_joue)

    # ------------------- utilitaire confiance -------------------

    def calculer_confiance(self) -> int:
        """
        Indice de confiance simple.
        1 = aléatoire
        2 = minimax
        3 = BGA (plus tard)
        4 = humain (optionnel, si tu veux distinguer)
        """
        # 2 humains
        if self.mode == 1:
            return 4

        # au moins un robot
        if self.algo_robot == "minimax":
            return 2
        return 1

    # ------------------- actions appelées par la vue -------------------

    def clic_souris(self, event):
        if self.mode == 3:
            return  # robots, pas de clic

        col = event.x // 60
        self.jouer_coup_humain(col)

    def nouvelle_partie(self):
        self.modele.nouvelle_partie()
        self.vue.redimensionner_canvas()
        self.vue.afficher_scores_minimax(None)
        self.vue.dessiner_plateau()
        self.vue.canvas.bind("<Button-1>", self.clic_souris)
        self.vue.mettre_texte_mode()
        self.vue.mettre_texte_joueur()

        if self.mode == 3:
            self.vue.root.after(400, self.robot_joue)

    def annuler_coup(self):
        if not self.modele.annuler_dernier_coup():
            self.vue.mettre_texte_joueur("Aucun coup à annuler.")
            return
        self.vue.canvas.bind("<Button-1>", self.clic_souris)
        self.vue.afficher_scores_minimax(None)
        self.vue.dessiner_plateau()
        self.vue.mettre_texte_joueur()

    def sauvegarder_partie(self):
        coups = self.modele.exporter_coups_string()

        statut = "finished" if self.modele.resultat is not None else "in_progress"
        resultat = self.modele.resultat  # "rouge"/"jaune"/"nul"/None

        confiance = self.calculer_confiance()

        ok, msg, new_id = inserer_partie(
            lignes=self.modele.lignes,
            colonnes=self.modele.colonnes,
            couleur_depart=self.modele.couleur_depart,
            joueur_courant=self.modele.joueur_courant,
            statut=statut,
            resultat=resultat,
            coups=coups,
            confiance=confiance
        )

        self.vue.mettre_texte_joueur(msg)

    def charger_partie(self):
        import tkinter as tk
        from tkinter import messagebox

        parties = lister_parties_jeu()
        if not parties:
            self.vue.mettre_texte_joueur("Aucune partie en base.")
            return

        fen = tk.Toplevel(self.vue.root)
        fen.title("Charger depuis la BD")
        fen.geometry("560x340")

        tk.Label(fen, text="Parties en base :", font=("Arial", 11, "bold")).pack(pady=5)

        liste = tk.Listbox(fen, width=80, height=12)
        liste.pack(padx=10, pady=5, fill="both", expand=True)

        ids = []
        # selon ton db.py lister_parties_jeu renvoie : id, created_at, statut, resultat, confiance, coups
        for (pid, created_at, statut, resultat, confiance, coups) in parties:
            liste.insert(tk.END, f"ID {pid} | {statut} | res={resultat} | conf={confiance} | coups={coups}")
            ids.append(pid)

        def charger_selection():
            sel = liste.curselection()
            if not sel:
                messagebox.showinfo("Charger", "Sélectionne une partie.")
                return

            pid = ids[sel[0]]
            partie = get_partie(pid)
            if not partie:
                messagebox.showerror("Charger", "Partie introuvable en base.")
                return

            # charge dans le modèle
            self.modele.charger_depuis_bd(partie)

            # met à jour l'UI
            self.vue.redimensionner_canvas()
            self.vue.afficher_scores_minimax(None)
            self.vue.dessiner_plateau()
            self.vue.mettre_texte_mode()

            if self.modele.resultat is None:
                self.vue.mettre_texte_joueur(f"Partie BD {pid} chargée - à jouer")
                self.vue.canvas.bind("<Button-1>", self.clic_souris)
            else:
                self.vue.canvas.unbind("<Button-1>")
                self.vue.mettre_texte_joueur(f"Partie BD {pid} chargée - résultat : {self.modele.resultat}")

            fen.destroy()

        tk.Button(fen, text="Charger", command=charger_selection).pack(pady=8)

    def ouvrir_parametres(self):
        import tkinter as tk
        from vue import BG_FENETRE, COULEUR_TEXTE

        fen = tk.Toplevel(self.vue.root)
        fen.title("Paramètres")
        fen.configure(bg=BG_FENETRE)

        tk.Label(fen, text="Lignes :", bg=BG_FENETRE, fg=COULEUR_TEXTE).grid(row=0, column=0, padx=5, pady=5, sticky="e")
        tk.Label(fen, text="Colonnes :", bg=BG_FENETRE, fg=COULEUR_TEXTE).grid(row=1, column=0, padx=5, pady=5, sticky="e")
        tk.Label(fen, text="Couleur départ (1=Rouge, 2=Jaune) :", bg=BG_FENETRE, fg=COULEUR_TEXTE).grid(row=2, column=0, padx=5, pady=5, sticky="e")

        entry_lignes = tk.Entry(fen)
        entry_colonnes = tk.Entry(fen)
        entry_couleur = tk.Entry(fen)

        entry_lignes.grid(row=0, column=1, padx=5, pady=5)
        entry_colonnes.grid(row=1, column=1, padx=5, pady=5)
        entry_couleur.grid(row=2, column=1, padx=5, pady=5)

        entry_lignes.insert(0, str(self.modele.lignes))
        entry_colonnes.insert(0, str(self.modele.colonnes))
        entry_couleur.insert(0, str(self.modele.couleur_depart))

        def enregistrer():
            try:
                nl = int(entry_lignes.get())
                nc = int(entry_colonnes.get())
                cdep = int(entry_couleur.get())
            except ValueError:
                self.vue.mettre_texte_joueur("Paramètres invalides (entiers).")
                return

            if not self.modele.mettre_a_jour_parametres(nl, nc, cdep):
                self.vue.mettre_texte_joueur("Paramètres refusés.")
                return

            self.vue.redimensionner_canvas()
            self.vue.afficher_scores_minimax(None)
            self.vue.dessiner_plateau()
            self.vue.canvas.bind("<Button-1>", self.clic_souris)
            self.vue.mettre_texte_joueur("Paramètres mis à jour (Partie 1).")
            self.vue.mettre_texte_mode()
            fen.destroy()

        tk.Button(fen, text="Enregistrer", command=enregistrer).grid(row=3, column=0, columnspan=2, pady=10)

    # ---------- logique de jeu (humain) ----------

    def jouer_coup_humain(self, col):
        self.vue.afficher_scores_minimax(None)

        lig = self.modele.jouer_coup(col)
        if lig is None:
            self.vue.mettre_texte_joueur("Coup impossible (colonne pleine ?).")
            return

        self.vue.dessiner_plateau()

        coords = self.modele.verifier_victoire(self.modele.joueur_courant)
        if coords:
            if self.modele.joueur_courant == self.modele.ROUGE:
                self.modele.definir_resultat("rouge")
                gagnant_txt = "Rouge"
            else:
                self.modele.definir_resultat("jaune")
                gagnant_txt = "Jaune"

            self.vue.mettre_texte_joueur(f"Partie {self.modele.numero_partie} - Le joueur {gagnant_txt} a gagné !")
            self.vue.surligner_victoire(coords)
            self.vue.canvas.unbind("<Button-1>")
            return

        if self.modele.plateau_plein():
            self.modele.definir_resultat("nul")
            self.vue.mettre_texte_joueur(f"Partie {self.modele.numero_partie} - Match nul !")
            self.vue.canvas.unbind("<Button-1>")
            return

        self.modele.changer_joueur()
        self.vue.mettre_texte_joueur()

        if self.mode == 2 and self.modele.joueur_courant != self.humain:
            self.vue.root.after(400, self.robot_joue)

    # ---------- robot (aléatoire ou minimax) ----------

    def robot_joue(self):
        self.vue.afficher_scores_minimax(None)

        if self.algo_robot == "minimax":
            scores = {}
            plateau = [ligne[:] for ligne in self.modele.plateau]
            joueur_max = self.modele.joueur_courant
            valides = self.modele.colonnes_valides(plateau)

            for col in valides:
                lig = self.modele._jouer_temp(plateau, col, joueur_max)
                if lig is None:
                    continue
                score = self.modele.minimax(
                    plateau,
                    self.profondeur_minimax - 1,
                    joueur_max,
                    self.modele.autre_joueur(joueur_max)
                )
                plateau[lig][col] = self.modele.VIDE
                scores[col] = score

                self.vue.afficher_scores_minimax(scores)
                self.vue.root.update_idletasks()

            if not scores:
                self.vue.mettre_texte_joueur(f"Partie {self.modele.numero_partie} - Plus de coups possibles.")
                return

            col = max(scores, key=scores.get)
        else:
            col = self.modele.coup_aleatoire()
            if col is None:
                self.vue.mettre_texte_joueur(f"Partie {self.modele.numero_partie} - Plus de coups possibles.")
                return

        lig = self.modele.jouer_coup(col)
        if lig is None:
            return

        self.vue.dessiner_plateau()

        coords = self.modele.verifier_victoire(self.modele.joueur_courant)
        if coords:
            if self.modele.joueur_courant == self.modele.ROUGE:
                self.modele.definir_resultat("rouge")
                gagnant_txt = "Rouge"
            else:
                self.modele.definir_resultat("jaune")
                gagnant_txt = "Jaune"

            self.vue.mettre_texte_joueur(f"Partie {self.modele.numero_partie} - Le joueur {gagnant_txt} a gagné !")
            self.vue.surligner_victoire(coords)
            self.vue.canvas.unbind("<Button-1>")
            return

        if self.modele.plateau_plein():
            self.modele.definir_resultat("nul")
            self.vue.mettre_texte_joueur(f"Partie {self.modele.numero_partie} - Match nul !")
            self.vue.canvas.unbind("<Button-1>")
            return

        self.modele.changer_joueur()
        self.vue.mettre_texte_joueur()

        if self.mode == 3:
            self.vue.root.after(400, self.robot_joue)
