import tkinter as tk

TAILLE_CASE = 60

BG_FENETRE = "#0b1f33"
BG_PLATEAU = "#1e3a5f"
COULEUR_TEXTE = "white"

# Style uniforme boutons
BOUTON_STYLE = {
    "bg": "#26486b",
    "fg": "white",
    "activebackground": "#3b5f86",
    "activeforeground": "white",
    "relief": "flat",
    "bd": 1,
    "font": ("Arial", 10, "bold"),
    "cursor": "hand2",
}


# ---------- Fenêtre de choix du mode ----------

def demander_mode():
    """Fenêtre qui renvoie 1, 2 ou 3 selon le mode choisi."""
    resultat = {"mode": 1}

    def choisir(m):
        resultat["mode"] = m
        fen.destroy()

    fen = tk.Tk()
    fen.title("Choisir un mode")
    fen.configure(bg=BG_FENETRE)
    fen.resizable(False, False)

    tk.Label(
        fen,
        text="Choisis un mode de jeu :",
        bg=BG_FENETRE,
        fg=COULEUR_TEXTE,
        font=("Arial", 14, "bold")
    ).pack(pady=15)

    cadre = tk.Frame(fen, bg=BG_FENETRE)
    cadre.pack(pady=5)

    tk.Button(
        cadre,
        text="2 joueurs humains",
        command=lambda: choisir(1),
        width=20,
        **BOUTON_STYLE
    ).pack(pady=4)

    tk.Button(
        cadre,
        text="1 joueur vs robot",
        command=lambda: choisir(2),
        width=20,
        **BOUTON_STYLE
    ).pack(pady=4)

    tk.Button(
        cadre,
        text="0 joueur (robots)",
        command=lambda: choisir(3),
        width=20,
        **BOUTON_STYLE
    ).pack(pady=4)

    fen.mainloop()
    return resultat["mode"]


def demander_parametres_robot():
    """Fenêtre qui permet de choisir : aléatoire / minimax + profondeur.
    Retourne (algo, profondeur)."""
    resultat = {"algo": "aleatoire", "prof": 3}

    def valider():
        try:
            p = int(entree_profondeur.get())
        except ValueError:
            p = 3
        resultat["algo"] = var_algo.get()
        resultat["prof"] = max(1, p)
        fen.destroy()

    fen = tk.Tk()
    fen.title("Paramètres du robot")
    fen.configure(bg=BG_FENETRE)
    fen.resizable(False, False)

    tk.Label(
        fen,
        text="Stratégie du robot :",
        bg=BG_FENETRE,
        fg=COULEUR_TEXTE,
        font=("Arial", 12, "bold")
    ).grid(row=0, column=0, columnspan=2, pady=(10, 5), padx=10, sticky="w")

    var_algo = tk.StringVar(value="aleatoire")

    tk.Radiobutton(
        fen, text="Aléatoire",
        variable=var_algo, value="aleatoire",
        bg=BG_FENETRE, fg=COULEUR_TEXTE,
        selectcolor=BG_PLATEAU,
        activebackground=BG_FENETRE
    ).grid(row=1, column=0, columnspan=2, sticky="w", padx=20)

    tk.Radiobutton(
        fen, text="Minimax",
        variable=var_algo, value="minimax",
        bg=BG_FENETRE, fg=COULEUR_TEXTE,
        selectcolor=BG_PLATEAU,
        activebackground=BG_FENETRE
    ).grid(row=2, column=0, columnspan=2, sticky="w", padx=20)

    tk.Label(
        fen,
        text="Profondeur (si minimax) :",
        bg=BG_FENETRE,
        fg=COULEUR_TEXTE
    ).grid(row=3, column=0, padx=10, pady=(10, 5), sticky="e")

    entree_profondeur = tk.Entry(fen, width=5)
    entree_profondeur.insert(0, "3")
    entree_profondeur.grid(row=3, column=1, pady=(10, 5), sticky="w")

    tk.Button(
        fen, text="Valider",
        command=valider,
        **BOUTON_STYLE
    ).grid(row=4, column=0, columnspan=2, pady=10)

    fen.mainloop()
    return resultat["algo"], resultat["prof"]


# ---------- Vue principale ----------

class Puissance4Vue:
    def __init__(self, modele, controleur, mode):
        self.modele = modele
        self.controleur = controleur
        self.mode = mode

        # scores minimax {colonne: valeur} (ou None)
        self.scores_minimax = None

        self.root = tk.Tk()
        self.root.title("Puissance 4")
        self.root.configure(bg=BG_FENETRE)
        self.root.minsize(700, 600)

        # Titre
        self.label_titre = tk.Label(
            self.root, text="Puissance 4",
            font=("Arial", 24, "bold"),
            bg=BG_FENETRE, fg=COULEUR_TEXTE
        )
        self.label_titre.pack(pady=(10, 0))

        # Info partie
        self.label_info = tk.Label(
            self.root, font=("Arial", 14, "bold"),
            bg=BG_FENETRE, fg=COULEUR_TEXTE
        )
        self.label_info.pack(pady=(5, 0))

        # Mode
        self.label_mode = tk.Label(
            self.root, font=("Arial", 10),
            bg=BG_FENETRE, fg="#d0d0d0"
        )
        self.label_mode.pack(pady=(2, 10))

        # Zone boutons
        frame_boutons = tk.Frame(self.root, bg=BG_FENETRE)
        frame_boutons.pack(pady=5)

        tk.Button(
            frame_boutons, text="Nouvelle partie",
            command=self.controleur.nouvelle_partie,
            **BOUTON_STYLE
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            frame_boutons, text="Annuler coup",
            command=self.controleur.annuler_coup,
            **BOUTON_STYLE
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            frame_boutons, text="Sauvegarder",
            command=self.controleur.sauvegarder_partie,
            **BOUTON_STYLE
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            frame_boutons, text="Charger",
            command=self.controleur.charger_partie,
            **BOUTON_STYLE
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            frame_boutons, text="Paramètres",
            command=self.controleur.ouvrir_parametres,
            **BOUTON_STYLE
        ).pack(side=tk.LEFT, padx=5)

        # Canvas du plateau (+30px pour les numéros / scores)
        self.canvas = tk.Canvas(
            self.root,
            width=self.modele.colonnes * TAILLE_CASE,
            height=self.modele.lignes * TAILLE_CASE + 30,
            bg=BG_PLATEAU,
            highlightthickness=0
        )
        self.canvas.pack(pady=10)

        self.canvas.bind("<Button-1>", self.controleur.clic_souris)

        self.mettre_texte_mode()
        self.mettre_texte_joueur()
        self.dessiner_plateau()

    # ---------------- Utilities ----------------

    def mettre_texte_mode(self):
        modes = {
            1: "2 joueurs humains",
            2: "1 joueur vs robot",
            3: "0 joueur (robot vs robot)"
        }
        self.label_mode.config(text=f"Mode : {modes.get(self.mode, '?')}")

    def mettre_texte_joueur(self, texte=None):
        if texte is not None:
            self.label_info.config(text=texte)
        else:
            joueur = self.modele.joueur_courant
            couleur = "Rouge" if joueur == self.modele.ROUGE else "Jaune"
            self.label_info.config(
                text=f"Partie {self.modele.numero_partie} - Au tour du joueur {couleur}"
            )

    def redimensionner_canvas(self):
        self.canvas.config(
            width=self.modele.colonnes * TAILLE_CASE,
            height=self.modele.lignes * TAILLE_CASE + 30
        )

    def dessiner_plateau(self):
        self.canvas.delete("all")

        # Pions
        for i in range(self.modele.lignes):
            for j in range(self.modele.colonnes):
                x1 = j * TAILLE_CASE
                y1 = i * TAILLE_CASE
                x2 = x1 + TAILLE_CASE
                y2 = y1 + TAILLE_CASE

                couleur = "white"
                if self.modele.plateau[i][j] == self.modele.ROUGE:
                    couleur = "#d62828"   # rouge foncé
                elif self.modele.plateau[i][j] == self.modele.JAUNE:
                    couleur = "#ffd60a"   # jaune

                self.canvas.create_oval(
                    x1 + 5, y1 + 5, x2 - 5, y2 - 5,
                    fill=couleur, outline="white"
                )

        # Numéros de colonnes + scores minimax
        base_y = self.modele.lignes * TAILLE_CASE + 12
        score_y = self.modele.lignes * TAILLE_CASE + 25

        for j in range(self.modele.colonnes):
            x = j * TAILLE_CASE + TAILLE_CASE // 2
            # numéro
            self.canvas.create_text(
                x, base_y,
                text=str(j + 1),
                fill="white",
                font=("Arial", 9, "bold")
            )
            # score minimax éventuel
            if self.scores_minimax is not None:
                val = self.scores_minimax.get(j)
                if val is not None:
                    self.canvas.create_text(
                        x, score_y,
                        text=str(val),
                        fill="#90ee90",   # vert clair
                        font=("Arial", 8)
                    )

    def surligner_victoire(self, coords):
        for (i, j) in coords:
            x1 = j * TAILLE_CASE
            y1 = i * TAILLE_CASE
            x2 = x1 + TAILLE_CASE
            y2 = y1 + TAILLE_CASE
            self.canvas.create_oval(
                x1 + 3, y1 + 3, x2 - 3, y2 - 3,
                outline="lime",
                width=3
            )

    def afficher_scores_minimax(self, scores):
        """scores : dict {col: valeur} ou None pour effacer."""
        self.scores_minimax = scores
        self.dessiner_plateau()

    def lancer(self):
        self.root.mainloop()