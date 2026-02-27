import tkinter as tk
from tkinter import filedialog, messagebox

from db import lister_parties, get_partie, inserer_partie_depuis_fichier

TAILLE_CASE = 50


class ExplorateurBD:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Explorateur de parties - Connect 4")
        self.root.geometry("1100x600")

        titre = tk.Label(self.root, text="Parties enregistrées", font=("Arial", 16, "bold"))
        titre.pack(pady=10)

        btn_import = tk.Button(
            self.root,
            text="📥 Importer un fichier .txt",
            command=self.importer_fichier
        )
        btn_import.pack(pady=5)

        frame_global = tk.Frame(self.root)
        frame_global.pack(fill="both", expand=True, padx=10, pady=10)

        # ================= GAUCHE =================
        frame_gauche = tk.Frame(frame_global)
        frame_gauche.pack(side="left", fill="y")

        self.liste = tk.Listbox(frame_gauche, width=55, height=22)
        self.liste.pack(side="left", fill="y")

        scrollbar = tk.Scrollbar(frame_gauche, orient="vertical", command=self.liste.yview)
        scrollbar.pack(side="left", fill="y")
        self.liste.config(yscrollcommand=scrollbar.set)

        # ================= DROITE =================
        frame_droite = tk.Frame(frame_global)
        frame_droite.pack(side="left", fill="both", expand=True, padx=15)

        tk.Label(frame_droite, text="Détails de la partie", font=("Arial", 12, "bold")).pack(anchor="w")

        self.txt_details = tk.Text(frame_droite, height=10)
        self.txt_details.pack(fill="x")

        # -------- Modes --------
        frame_modes = tk.Frame(frame_droite)
        frame_modes.pack(anchor="w", pady=(8, 0))

        tk.Label(frame_modes, text="Mode :", font=("Arial", 10, "bold")).pack(side="left", padx=(0, 8))

        self.mode_var = tk.StringVar(value="normal")

        tk.Radiobutton(frame_modes, text="Normal",
                       variable=self.mode_var, value="normal",
                       command=self.changer_mode).pack(side="left", padx=5)

        tk.Radiobutton(frame_modes, text="Symétrique",
                       variable=self.mode_var, value="sym",
                       command=self.changer_mode).pack(side="left", padx=5)

        tk.Radiobutton(frame_modes, text="Canonique",
                       variable=self.mode_var, value="can",
                       command=self.changer_mode).pack(side="left", padx=5)

        tk.Label(frame_droite, text="Plateau", font=("Arial", 12, "bold")).pack(anchor="w", pady=(10, 0))

        frame_plateau_nav = tk.Frame(frame_droite)
        frame_plateau_nav.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(frame_plateau_nav, bg="#1e3a5f")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.afficher_coup())

        frame_nav = tk.Frame(frame_plateau_nav, width=200)
        frame_nav.pack(side="left", fill="y", padx=15)

        tk.Label(frame_nav, text="Navigation", font=("Arial", 12, "bold")).pack(pady=(10, 10))

        self.lbl_coup = tk.Label(frame_nav, text="Coup : - / -")
        self.lbl_coup.pack(pady=(0, 10))

        tk.Button(frame_nav, text="⏮ Début", width=14, command=self.aller_debut).pack(pady=4)
        tk.Button(frame_nav, text="◀ Précédent", width=14, command=self.precedent).pack(pady=4)
        tk.Button(frame_nav, text="Suivant ▶", width=14, command=self.suivant).pack(pady=4)
        tk.Button(frame_nav, text="Fin ⏭", width=14, command=self.aller_fin).pack(pady=4)

        # ================= VARIABLES =================
        self.ids = []
        self.partie_selectionnee = None

        self.coups_normal = ""
        self.coups_sym = ""
        self.coups_can = ""
        self.coups_actifs = ""
        self.index_coup = 0

        self.charger_parties()
        self.liste.bind("<<ListboxSelect>>", self.on_select)

        self.root.mainloop()

    # ================= IMPORT =================
    def importer_fichier(self):
        chemin = filedialog.askopenfilename(
            title="Choisir un fichier de partie",
            filetypes=[("Fichiers texte", "*.txt")]
        )
        if not chemin:
            return

        # 🔥 CORRECTION ICI
        ok, msg, _ = inserer_partie_depuis_fichier(chemin)

        if ok:
            messagebox.showinfo("Import", msg)
            self.charger_parties()
        else:
            messagebox.showwarning("Import", msg)

    # ================= LISTE =================
    def charger_parties(self):
        self.liste.delete(0, tk.END)
        self.ids = []

        parties = lister_parties()
        for p in parties:
            partie_id = p[0]
            statut = p[2]
            resultat = p[3]
            confiance = p[4]
            coups = p[5]

            txt = f"ID {partie_id} | {statut} | res={resultat} | conf={confiance} | coups={coups}"
            self.liste.insert(tk.END, txt)
            self.ids.append(partie_id)

    # ================= PLATEAU =================
    def creer_plateau_vide(self, lignes, colonnes):
        return [[0 for _ in range(colonnes)] for _ in range(lignes)]

    def jouer_coup_plateau(self, plateau, col, joueur):
        for i in range(len(plateau) - 1, -1, -1):
            if plateau[i][col] == 0:
                plateau[i][col] = joueur
                return True
        return False

    def reconstruire_plateau(self, coups, lignes, colonnes, nb):
        plateau = self.creer_plateau_vide(lignes, colonnes)
        joueur = 1
        joues = 0

        for ch in coups:
            if joues >= nb:
                break
            if ch.isdigit():
                col = int(ch) - 1
                if 0 <= col < colonnes:
                    if self.jouer_coup_plateau(plateau, col, joueur):
                        joueur = 2 if joueur == 1 else 1
                        joues += 1
        return plateau

    def dessiner_plateau(self, plateau):
        self.canvas.delete("all")

        lignes = len(plateau)
        colonnes = len(plateau[0]) if lignes else 0
        if not lignes or not colonnes:
            return

        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()

        marge = 10
        case = min(TAILLE_CASE, (w - 2*marge)//colonnes, (h - 2*marge)//lignes)
        if case <= 0:
            return

        offset_x = (w - colonnes*case)//2
        offset_y = (h - lignes*case)//2
        pad = max(2, case//10)

        for i in range(lignes):
            for j in range(colonnes):
                x1 = offset_x + j*case
                y1 = offset_y + i*case
                x2 = x1 + case
                y2 = y1 + case

                couleur = "white"
                if plateau[i][j] == 1:
                    couleur = "#d62828"
                elif plateau[i][j] == 2:
                    couleur = "#ffd60a"

                self.canvas.create_oval(x1+pad, y1+pad, x2-pad, y2-pad,
                                        fill=couleur, outline="white")

    # ================= AFFICHAGE =================
    def afficher_coup(self):
        if not self.partie_selectionnee:
            return

        (pid, created_at, lignes, colonnes, couleur_depart, joueur_courant,
         statut, resultat, confiance, coups, coups_sym, coups_can) = self.partie_selectionnee

        total = len(self.coups_actifs)
        self.index_coup = max(0, min(self.index_coup, total))

        self.lbl_coup.config(text=f"Coup : {self.index_coup} / {total}")

        plateau = self.reconstruire_plateau(self.coups_actifs, lignes, colonnes, self.index_coup)
        self.dessiner_plateau(plateau)

    # ================= MODES =================
    def changer_mode(self):
        m = self.mode_var.get()
        if m == "normal":
            self.coups_actifs = self.coups_normal
        elif m == "sym":
            self.coups_actifs = self.coups_sym
        else:
            self.coups_actifs = self.coups_can

        self.index_coup = min(self.index_coup, len(self.coups_actifs))
        self.afficher_coup()

    # ================= NAVIGATION =================
    def aller_debut(self):
        self.index_coup = 0
        self.afficher_coup()

    def aller_fin(self):
        self.index_coup = len(self.coups_actifs)
        self.afficher_coup()

    def precedent(self):
        self.index_coup -= 1
        self.afficher_coup()

    def suivant(self):
        self.index_coup += 1
        self.afficher_coup()

    # ================= SELECTION =================
    def on_select(self, event=None):
        sel = self.liste.curselection()
        if not sel:
            return

        partie_id = self.ids[sel[0]]
        partie = get_partie(partie_id)
        if not partie:
            return

        self.partie_selectionnee = partie

        (pid, created_at, lignes, colonnes, couleur_depart, joueur_courant,
         statut, resultat, confiance, coups, coups_sym, coups_can) = partie

        self.coups_normal = coups or ""
        self.coups_sym = coups_sym or ""
        self.coups_can = coups_can or ""
        self.index_coup = len(self.coups_normal)

        self.changer_mode()

        self.txt_details.delete("1.0", tk.END)
        self.txt_details.insert(tk.END,
            f"ID : {pid}\n"
            f"Date : {created_at}\n"
            f"Taille : {lignes} x {colonnes}\n"
            f"Couleur départ : {couleur_depart}\n"
            f"Joueur courant : {joueur_courant}\n"
            f"Statut : {statut}\n"
            f"Résultat : {resultat}\n"
            f"Confiance : {confiance}\n\n"
            f"Coups (normal) : {self.coups_normal}\n"
            f"Coups (symétrique) : {self.coups_sym}\n"
            f"Coups (canonique) : {self.coups_can}\n"
        )


if __name__ == "__main__":
    ExplorateurBD()
