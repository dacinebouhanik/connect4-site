from selenium import webdriver
from selenium.common import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager

import time
import os
import re

from db import inserer_partie, test_connexion
from modele import Puissance4Modele


print("Test DB:", test_connexion())


# ================= CONFIGURATION =================

ROWS = 9
COLS = 9

PLAYER_IDS = ["99036079","99310859","85354625","98903893","99041258","98925546"]

BOARD_SIZE_CODE = f"{ROWS}{COLS}"

PROCESSED_DIR = "processed_matches"
os.makedirs(PROCESSED_DIR, exist_ok=True)

# =================================================


options = Options()

driver = webdriver.Firefox(
    service=Service(GeckoDriverManager().install()),
    options=options
)


# =================================================
# UTILS
# =================================================

def load_processed_urls(player_id):

    filepath = os.path.join(PROCESSED_DIR, f"{player_id}.txt")

    if not os.path.exists(filepath):
        return set()

    with open(filepath, "r") as f:
        return set(line.strip() for line in f)


def save_processed_url(player_id, url):

    filepath = os.path.join(PROCESSED_DIR, f"{player_id}.txt")

    with open(filepath, "a") as f:
        f.write(url + "\n")


# =================================================
# VERIFICATION TAILLE
# =================================================

def is_correct_board_size(driver):

    try:

        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "gameoption_100_displayed_value"))
        )

        size_element = driver.find_element(By.ID, "gameoption_100_displayed_value")

        displayed_size = size_element.text.strip()

        page_source = driver.page_source

        expected_pattern = f'<option value="{BOARD_SIZE_CODE}" selected="selected"'

        print("Taille affichée:", displayed_size)

        return expected_pattern in page_source or displayed_size.replace("x", "") == BOARD_SIZE_CODE

    except Exception as e:

        print("Erreur taille plateau:", e)

        return False


# =================================================
# EXTRACTION MATCHS
# =================================================

def extract_match_links_from_profile(player_url):
    """Extrait les liens des matchs depuis le profil d'un joueur en chargeant TOUT l'historique d'abord"""
    print(f"--- Navigation vers le profil: {player_url} ---")
    driver.get(player_url)

    player_id = player_url.split("id=")[-1]
    player_matches = set()

    try:
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, "post"))
        )

        print("Chargement de TOUT l'historique...")
        page_count = 0
        click_count = 0

        # ÉTAPE 1: Cliquer sur "Voir plus" jusqu'à ce qu'il n'y en ait plus
        while True:
            try:
                # Chercher le bouton "Voir plus..."
                see_more_btn = driver.find_element(By.ID, "board_seemore_r")

                if see_more_btn.is_displayed():
                    # Compter les posts avant le clic
                    old_post_count = len(driver.find_elements(By.CLASS_NAME, "post"))

                    # Faire défiler jusqu'au bouton et cliquer
                    driver.execute_script("arguments[0].scrollIntoView(true);", see_more_btn)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", see_more_btn)

                    click_count += 1
                    print(f"Clic {click_count} sur 'Voir plus...'")

                    # Attendre que de nouveaux posts soient chargés
                    WebDriverWait(driver, 10).until(
                        lambda d: len(d.find_elements(By.CLASS_NAME, "post")) > old_post_count
                    )

                    # Petite pause pour laisser le contenu se stabiliser
                    time.sleep(1)
                else:
                    print("Bouton 'Voir plus' non affiché.")
                    break

            except NoSuchElementException:
                print(f"Plus de bouton 'Voir plus...' disponible après {click_count} clics.")
                break
            except Exception as e:
                print(f"Erreur lors du chargement supplémentaire: {e}")
                break

        print(f"Chargement terminé. {click_count} clics effectués.")

        # ÉTAPE 2: Maintenant que TOUT l'historique est chargé, extraire tous les liens
        print("Extraction de tous les matchs Puissance 4...")

        # Récupérer TOUS les posts maintenant que tout est chargé
        all_posts = driver.find_elements(By.CLASS_NAME, "post")
        print(f"Total posts dans l'historique: {len(all_posts)}")

        for post in all_posts:
            try:
                # Vérifier si c'est un match de Puissance 4
                game_name_el = post.find_element(By.CLASS_NAME, "gamename")
                game_text = game_name_el.text

                if "Puissance Quatre" in game_text or "Connect Four" in game_text:
                    # Extraire le lien du match
                    match_link = post.find_element(By.CSS_SELECTOR, ".postmessage a").get_attribute("href")

                    if "/table?table=" in match_link:
                        player_matches.add(match_link)
                        print(f"Match trouvé: {match_link}")
            except Exception as e:
                # Ignorer les posts sans lien ou avec d'autres erreurs
                continue

        print(f"\n--- RÉSULTAT POUR JOUEUR {player_id} ---")
        print(f"Total Puissance Quatre matches trouvés: {len(player_matches)}")
        print(f"(sur {len(all_posts)} posts au total)")

    except TimeoutException:
        print(f"Timeout en attendant le profil {player_id}")
    except Exception as e:
        print(f"Erreur inattendue pour {player_id}: {e}")

    return list(player_matches)




# =================================================
# TRAITEMENT MATCH
# =================================================

def process_match(table_url, player_id, processed_urls):

    if table_url in processed_urls:

        print("Déjà traité:", table_url)

        return False

    try:

        print("\n[Match]", table_url)

        driver.get(table_url)

        if not is_correct_board_size(driver):

            print("Plateau incorrect")

            return False

        review_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "reviewgame"))
        )

        driver.execute_script("arguments[0].click();", review_btn)

        try:

            start_trigger = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".bgabutton_red, #pagemaintitletext a"))
            )

            start_trigger.click()

        except:
            pass

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "gamelogreview"))
        )

        time.sleep(1)

        log_elements = driver.find_elements(By.CSS_SELECTOR, ".gamelogreview.whiteblock, .gamelogreview")

        col_sequence = []

        for entry in log_elements:

            text = entry.text.lower()

            if "place un pion" not in text:
                continue

            col_match = re.search(r'colonne\s*(\d+)', text)

            if col_match:

                col = int(col_match.group(1))

                if 1 <= col <= COLS:

                    col_sequence.append(col)

                    print("Placement colonne", col)

        if not col_sequence:

            print("Aucun coup trouvé")

            return False

        seq_str = "".join(map(str, col_sequence))

        print("Séquence:", seq_str)

        ok, msg, game_id = inserer_partie(

            lignes=ROWS,
            colonnes=COLS,
            couleur_depart=1,
            joueur_courant=1,
            statut="finished",
            resultat=None,
            coups=seq_str,
            confiance=3
        )

        print(msg)

        save_processed_url(player_id, table_url)

        processed_urls.add(table_url)

        return ok

    except Exception as e:

        print("Erreur match:", e)

        return False


# =================================================
# MAIN
# =================================================

def main():

    print("=== CONFIGURATION ===")
    print("Taille du plateau:", ROWS, "x", COLS)
    print("Joueurs à scraper:", PLAYER_IDS)
    print("=====================\n")

    print("Ouverture de BGA...")

    driver.get("https://en.boardgamearena.com/account")

    wait = WebDriverWait(driver, 600)

    print("Attente de la connexion...")

    wait.until(lambda d: "account" not in d.current_url)

    print("\n--- CONNEXION DETECTEE ---\n")

    all_new_matches = 0

    for player_id in PLAYER_IDS:

        print("=== TRAITEMENT JOUEUR", player_id, "===")

        player_url = f"https://boardgamearena.com/player?id={player_id}"

        processed_urls = load_processed_urls(player_id)

        match_links = extract_match_links_from_profile(player_url)

        print("Matchs trouvés:", len(match_links))

        new_links = [u for u in match_links if u not in processed_urls]

        print("Matchs non traités:", len(new_links))

        new_matches = 0

        for i, url in enumerate(new_links, 1):

            print(f"\n--- Match {i}/{len(new_links)} ---")

            if process_match(url, player_id, processed_urls):

                new_matches += 1
                all_new_matches += 1

            time.sleep(3)

        print("\nJoueur terminé :", player_id)
        print("Nouveaux matchs ajoutés :", new_matches)

    print("\n=== SCRAPING TERMINÉ ===")
    print("Total nouveaux matchs ajoutés :", all_new_matches)


# =================================================

if __name__ == "__main__":

    try:
        main()

    finally:

        input("\nAppuie sur Entrée pour fermer")

        driver.quit()