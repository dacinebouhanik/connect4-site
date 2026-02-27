# interface_scraping.py

import re
import time
import tkinter as tk
from tkinter import messagebox

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from db import inserer_partie



LIGNES = 9
COLONNES = 9
COULEUR_DEPART = 1
JOUEUR_COURANT = 1
CONFIANCE = 3


def extraire_coups_depuis_html(html):
    pattern = r'"type":"playDisc".*?"x":"(\d+)"'
    coups = re.findall(pattern, html, flags=re.DOTALL)
    return "".join(coups)


def scraper_partie(numero_partie):
    url = f"https://boardgamearena.com/archive/replay/{numero_partie}/"

    options = webdriver.EdgeOptions()
    driver = webdriver.Edge(options=options)
    wait = WebDriverWait(driver, 20)

    try:
        driver.get("https://boardgamearena.com")
        input("Connecte-toi si nécessaire puis appuie sur ENTER...")

        driver.get(url)

        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(3)

        html = driver.page_source
        coups = extraire_coups_depuis_html(html)

        if not coups:
            return False, "Aucun coup trouvé."

        ok, msg, _ = inserer_partie(
            lignes=LIGNES,
            colonnes=COLONNES,
            couleur_depart=COULEUR_DEPART,
            joueur_courant=JOUEUR_COURANT,
            statut="finished",
            resultat=None,
            coups=coups,
            confiance=CONFIANCE
        )

        return ok, msg

    except Exception as e:
        return False, str(e)

    finally:
        driver.quit()


# ---------- Interface simple ----------

def lancer_interface():
    def valider():
        numero = entry.get().strip()
        if not numero:
            messagebox.showwarning("Erreur", "Entre un numéro de partie.")
            return

        ok, msg = scraper_partie(numero)
        if ok:
            messagebox.showinfo("Succès", msg)
        else:
            messagebox.showerror("Erreur", msg)

    root = tk.Tk()
    root.title("Import BGA")

    tk.Label(root, text="Numéro de partie BGA :").pack(pady=5)

    entry = tk.Entry(root, width=30)
    entry.pack(pady=5)

    tk.Button(root, text="Importer", command=valider).pack(pady=10)

    root.mainloop()


if __name__ == "__main__":
    lancer_interface()