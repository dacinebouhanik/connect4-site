from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager

from db import inserer_partie

import time
import re

ROWS = 9
COLS = 9


def scraper_partie_bga(table_id):

    options = Options()

    driver = webdriver.Firefox(
        service=Service(GeckoDriverManager().install()),
        options=options
    )

    wait = WebDriverWait(driver, 600)

    driver.get("https://boardgamearena.com/account")

    print("Connecte-toi sur BGA dans le navigateur...")

    wait.until(lambda d: "account" not in d.current_url)

    print("Connexion détectée !")

    try:

        table_url = f"https://boardgamearena.com/gamereview?table={table_id}"

        print("Ouverture table:", table_url)

        driver.get(table_url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # bouton review
        try:

            review_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "reviewgame"))
            )

            driver.execute_script("arguments[0].click();", review_btn)

            print("Bouton review cliqué")

        except:
            print("Pas de bouton review")

        # démarrer replay
        try:

            start_trigger = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, ".bgabutton_red, #pagemaintitletext a")
                )
            )

            start_trigger.click()

            print("Replay démarré")

        except:
            pass

        # attendre logs
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".gamelogreview"))
        )

        time.sleep(2)

        log_elements = driver.find_elements(
            By.CSS_SELECTOR,
            ".gamelogreview.whiteblock, .gamelogreview"
        )

        col_sequence = []

        for entry in log_elements:

            text = entry.text.lower()

            if "place un pion" not in text and "plays in column" not in text:
                continue

            col_match = re.search(r'colonne\s*(\d+)', text)

            if not col_match:
                col_match = re.search(r'column\s*(\d+)', text)

            if col_match:

                col = int(col_match.group(1))

                if 1 <= col <= COLS:

                    col_sequence.append(col)

                    print("Placement colonne", col)

        if not col_sequence:

            print("Aucun coup trouvé")

            return None

        seq_str = "".join(map(str, col_sequence))

        print("Séquence:", seq_str)

        # ------------------------
        # DETECTION RESULTAT
        # ------------------------

        resultat = None

        try:

            title = driver.find_element(By.ID, "pagemaintitletext").text.lower()

            if "rouge" in title or "red" in title:
                resultat = "rouge"

            elif "jaune" in title or "yellow" in title:
                resultat = "jaune"

            elif "draw" in title or "nul" in title:
                resultat = "nul"

        except:
            pass

        print("Résultat détecté :", resultat)

        # ------------------------
        # INSERTION BASE
        # ------------------------

        ok, msg, gid = inserer_partie(

            lignes=ROWS,
            colonnes=COLS,
            couleur_depart=1,
            joueur_courant=1,
            statut="finished",
            resultat=resultat,
            coups=seq_str,
            confiance=3
        )

        print(msg)

        return seq_str

    except Exception as e:

        print("Erreur scraping:", e)

        return None

    finally:

        driver.quit()