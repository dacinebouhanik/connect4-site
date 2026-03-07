# scrap_bga_selenium.py

import re
import time
from selenium.webdriver.edge.service import Service
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.microsoft import EdgeChromiumDriverManager


from db import inserer_partie


LIGNES = 9
COLONNES = 9
CONFIANCE = 3


def creer_driver():

    from selenium import webdriver
    from selenium.webdriver.edge.service import Service
    from selenium.webdriver.support.ui import WebDriverWait

    options = webdriver.EdgeOptions()

    options.add_argument("--start-maximized")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # profil isolé
    options.add_argument("--user-data-dir=edge_profile")

    # évite le bug DevToolsActivePort
    options.add_argument("--remote-debugging-port=9222")

    service = Service()

    driver = webdriver.Edge(service=service, options=options)

    wait = WebDriverWait(driver, 20)

    return driver, wait
def extraire_coups(html):
    pattern = r'"type":"playDisc".*?"x":"(\d+)"'
    coups = re.findall(pattern, html, flags=re.DOTALL)
    return "".join(coups)


def est_9x9(html):
    return ('"boardSize":9' in html) or ("9 x 9" in html) or ("9x9" in html)


def extraire_elos(html):
    pattern = r'"elo":"(\d+)"'
    elos = re.findall(pattern, html)

    if len(elos) >= 2:
        return int(elos[0]), int(elos[1])

    return None, None


def joueurs_forts(html, seuil=1600):
    elo1, elo2 = extraire_elos(html)

    if elo1 is None:
        return True

    return elo1 >= seuil and elo2 >= seuil


def partie_valide(coups):
    return len(coups) >= 12


def scraper_range(start_id, end_id):

    driver, wait = creer_driver()

    # ouvre BGA pour vérifier la connexion
    driver.get("https://boardgamearena.com")
    input("Si nécessaire connecte-toi puis appuie sur ENTER...")

    inserees = 0

    for gid in range(start_id, end_id):

        try:

            url = f"https://boardgamearena.com/archive/replay/{gid}/"
            driver.get(url)

            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(1)

            html = driver.page_source

            if not est_9x9(html):
                continue

            if not joueurs_forts(html):
                continue

            coups = extraire_coups(html)

            if not partie_valide(coups):
                continue

            ok, msg, _ = inserer_partie(
                lignes=LIGNES,
                colonnes=COLONNES,
                couleur_depart=1,
                joueur_courant=1,
                statut="finished",
                resultat=None,
                coups=coups,
                confiance=CONFIANCE
            )

            if ok:
                inserees += 1
                print("OK :", gid, "| total =", inserees)

        except Exception as e:

            print("Erreur :", gid, e)
            print("Recréation du navigateur...")

            try:
                driver.quit()
            except:
                pass

            driver, wait = creer_driver()

        time.sleep(1)

    print("Total insérées :", inserees)

    driver.quit()


if __name__ == "__main__":
    scraper_range(1000000, 1002000)