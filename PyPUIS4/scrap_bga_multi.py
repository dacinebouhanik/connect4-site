# scrap_bga_multi.py
# Basé sur ton scraper original qui marchait bien
# Ajouts : multi-comptes en parallèle + extraction résultat + connexion auto
#
# Usage :
#   python scrap_bga_multi.py              # tous les comptes en parallèle
#   python scrap_bga_multi.py --compte 0   # seulement le compte 0 (pour tester)

import time
import os
import re
import random
import argparse
from multiprocessing import Process

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager

from db import inserer_partie, test_connexion


# =========================================================
# CONFIGURATION — MODIFIE ICI
# =========================================================

ROWS = 9
COLS = 9
BOARD_SIZE_CODE = f"{ROWS}{COLS}"

PROCESSED_DIR = "processed_matches"
os.makedirs(PROCESSED_DIR, exist_ok=True)

# ✅ Tes joueurs à scraper
PLAYER_IDS = [
    "98887363","85354625","94154229","98155590","99383805",
    "99350416","91469116","99036079", "99310859", "85354625",
    "98903893", "99041258", "98925546",
]

# ✅ Tes comptes BGA — un Firefox par compte
COMPTES_BGA = [
    {"email": "hicham5boumzgou@gmail.com", "password": "Hicham.20052005"},

]

# Délais entre chaque match pour éviter la détection
DELAI_MIN = 5
DELAI_MAX = 15


# =========================================================
# UTILS
# =========================================================

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


def creer_driver():
    options = Options()
    options.set_preference("dom.webnotifications.enabled", False)
    options.set_preference("dom.push.enabled", False)
    driver = webdriver.Firefox(
        service=Service(GeckoDriverManager().install()),
        options=options
    )
    driver.set_page_load_timeout(30)
    return driver


# =========================================================
# CONNEXION
# =========================================================

def connexion(driver, email=None, password=None):
    """
    Connexion à BGA.
    Si email/password fournis → connexion automatique.
    Sinon → attente connexion manuelle.
    """
    driver.get("https://en.boardgamearena.com/account")

    # Connexion automatique
    if email and password:
        try:
            print(f"🔐 Connexion auto : {email}")

            # ✅ Sélecteur correct (pas d'ID, on utilise autocomplete)
            email_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[autocomplete='email']")
                )
            )
            email_field.clear()
            email_field.send_keys(email)

            # Champ password
            pwd_field = driver.find_element(
                By.CSS_SELECTOR, "input[type='password']"
            )
            pwd_field.clear()
            pwd_field.send_keys(password)

            # Bouton connexion
            btn = driver.find_element(
                By.CSS_SELECTOR, "button[type='submit'], input[type='submit']"
            )
            driver.execute_script("arguments[0].click();", btn)

            # Attendre redirection
            WebDriverWait(driver, 15).until(
                lambda d: "account" not in d.current_url
            )
            print(f"✅ Connecté : {email}")
            return True

        except Exception as e:
            print(f"⚠️ Connexion auto échouée ({e}) → connexion manuelle")

    # Connexion manuelle (fallback)
    print("⏳ Connecte-toi manuellement sur BGA...")
    WebDriverWait(driver, 600).until(
        lambda d: "account" not in d.current_url
    )
    print("✅ Connexion manuelle détectée")
    return True


# =========================================================
# VÉRIFICATION TAILLE PLATEAU
# =========================================================

def is_correct_board_size(driver):
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(
                (By.ID, "gameoption_100_displayed_value")
            )
        )
        size_element  = driver.find_element(By.ID, "gameoption_100_displayed_value")
        displayed_size = size_element.text.strip()
        page_source   = driver.page_source
        expected      = f'<option value="{BOARD_SIZE_CODE}" selected="selected"'
        print("Taille affichée:", displayed_size)
        return (
            expected in page_source or
            displayed_size.replace("x", "") == BOARD_SIZE_CODE
        )
    except Exception as e:
        print("Erreur taille plateau:", e)
        return False


# =========================================================
# EXTRACTION LIENS MATCHS — identique à ton original
# =========================================================

def extract_match_links_from_profile(driver, player_url):
    print(f"\n--- Profil: {player_url} ---")
    driver.get(player_url)

    player_id     = player_url.split("id=")[-1]
    player_matches = set()

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "post"))
        )

        # Charger tout l'historique
        click_count = 0
        while True:
            try:
                btn = driver.find_element(By.ID, "board_seemore_r")
                if not btn.is_displayed():
                    break
                old_count = len(driver.find_elements(By.CLASS_NAME, "post"))
                driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", btn)
                click_count += 1
                print(f"Clic {click_count} sur 'Voir plus...'")
                WebDriverWait(driver, 10).until(
                    lambda d: len(d.find_elements(By.CLASS_NAME, "post")) > old_count
                )
                time.sleep(1)
            except NoSuchElementException:
                print(f"Plus de 'Voir plus' après {click_count} clics.")
                break
            except Exception as e:
                print(f"Erreur chargement: {e}")
                break

        # Extraire les liens
        all_posts = driver.find_elements(By.CLASS_NAME, "post")
        print(f"Total posts: {len(all_posts)}")

        for post in all_posts:
            try:
                game_name_el = post.find_element(By.CLASS_NAME, "gamename")
                game_text    = game_name_el.text
                if "Puissance Quatre" in game_text or "Connect Four" in game_text:
                    match_link = post.find_element(
                        By.CSS_SELECTOR, ".postmessage a"
                    ).get_attribute("href")
                    if "/table?table=" in match_link:
                        player_matches.add(match_link)
                        print(f"Match trouvé: {match_link}")
            except Exception:
                continue

        print(f"Total Puissance 4 : {len(player_matches)} matchs")

    except TimeoutException:
        print(f"Timeout profil {player_id}")
    except Exception as e:
        print(f"Erreur profil: {e}")

    return list(player_matches)


# =========================================================
# TRAITEMENT MATCH — ton original + extraction résultat
# =========================================================

def process_match(driver, table_url, player_id, processed_urls):

    if table_url in processed_urls:
        print("Déjà traité:", table_url)
        return False

    try:
        print("\n[Match]", table_url)
        driver.get(table_url)

        if not is_correct_board_size(driver):
            print("Plateau incorrect")
            save_processed_url(player_id, table_url)
            processed_urls.add(table_url)
            return False

        # Cliquer Review
        review_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "reviewgame"))
        )
        driver.execute_script("arguments[0].click();", review_btn)

        try:
            start_trigger = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, ".bgabutton_red, #pagemaintitletext a")
                )
            )
            start_trigger.click()
        except Exception:
            pass

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "gamelogreview"))
        )
        time.sleep(1)

        log_elements = driver.find_elements(
            By.CSS_SELECTOR, ".gamelogreview.whiteblock, .gamelogreview"
        )

        col_sequence = []
        joueur1      = None   # Rouge (joue en premier)
        joueur2      = None   # Jaune
        resultat     = None

        for entry in log_elements:
            text       = entry.text.strip()
            text_lower = text.lower()

            # ✅ Extraction des coups + identification des joueurs
            # Format BGA : "NomJoueur place un pion dans la colonne X"
            match_coup = re.search(
                r'^(.+?)\s+place un pion dans la colonne\s+(\d+)',
                text, re.IGNORECASE
            )
            if match_coup:
                nom = match_coup.group(1).strip()
                col = int(match_coup.group(2))
                if 1 <= col <= COLS:
                    col_sequence.append(col)
                    print(f"  Colonne {col} par {nom}")
                    # Le premier joueur = Rouge
                    if joueur1 is None:
                        joueur1 = nom
                    elif nom != joueur1 and joueur2 is None:
                        joueur2 = nom

            # Fallback : ancien format "place un pion colonne X"
            elif "place un pion" in text_lower:
                col_match = re.search(r'colonne\s*(\d+)', text_lower)
                if col_match:
                    col = int(col_match.group(1))
                    if 1 <= col <= COLS:
                        col_sequence.append(col)

            # ✅ Extraction du résultat
            # Format BGA : "NomJoueur a aligné quatre pions !"
            if "a aligné quatre pions" in text_lower:
                nom_gagnant = text.split(" a aligné")[0].strip()
                if joueur1 and nom_gagnant.lower() == joueur1.lower():
                    resultat = "rouge"
                elif joueur2 and nom_gagnant.lower() == joueur2.lower():
                    resultat = "jaune"
                else:
                    # Fallback : le gagnant est le dernier joueur ayant joué
                    resultat = "rouge" if len(col_sequence) % 2 == 1 else "jaune"
                print(f"  Gagnant : {nom_gagnant} → {resultat}")

        if not col_sequence:
            print("Aucun coup trouvé")
            save_processed_url(player_id, table_url)
            processed_urls.add(table_url)
            return False

        seq_str = "".join(map(str, col_sequence))
        print(f"  Séquence ({len(col_sequence)} coups): {seq_str[:40]}...")
        print(f"  Résultat: {resultat}")

        ok, msg, game_id = inserer_partie(
            lignes         = ROWS,
            colonnes       = COLS,
            couleur_depart = 1,
            joueur_courant = 1,
            statut         = "finished",
            resultat       = resultat,
            coups          = seq_str,
            confiance      = 3
        )

        print(f"  {'✅' if ok else '❌'} {msg}")

        save_processed_url(player_id, table_url)
        processed_urls.add(table_url)
        return ok

    except Exception as e:
        print(f"Erreur match: {e}")
        return False


# =========================================================
# WORKER — 1 par compte BGA
# =========================================================

def worker(compte_idx, player_ids_subset):
    print(f"\n🚀 Worker {compte_idx} | Joueurs : {player_ids_subset}")

    driver = creer_driver()
    total  = 0

    try:
        # Connexion
        compte = COMPTES_BGA[compte_idx] if compte_idx < len(COMPTES_BGA) else {}
        connexion(
            driver,
            email    = compte.get("email"),
            password = compte.get("password")
        )

        # Scraper les joueurs assignés
        for player_id in player_ids_subset:
            print(f"\n{'='*50}")
            print(f"Worker {compte_idx} → Joueur {player_id}")
            print(f"{'='*50}")

            player_url     = f"https://boardgamearena.com/player?id={player_id}"
            processed_urls = load_processed_urls(player_id)
            match_links    = extract_match_links_from_profile(driver, player_url)
            new_links      = [u for u in match_links if u not in processed_urls]

            print(f"Matchs non traités : {len(new_links)}")

            for i, url in enumerate(new_links, 1):
                print(f"\n--- Match {i}/{len(new_links)} ---")
                if process_match(driver, url, player_id, processed_urls):
                    total += 1

                # Délai aléatoire
                delai = random.uniform(DELAI_MIN, DELAI_MAX)
                print(f"⏳ Pause {delai:.1f}s...")
                time.sleep(delai)

            print(f"\nJoueur {player_id} terminé")

    except Exception as e:
        print(f"❌ Erreur worker {compte_idx} : {e}")

    finally:
        print(f"\n✅ Worker {compte_idx} terminé — {total} parties insérées")
        try:
            input("Appuie sur Entrée pour fermer...")
        except Exception:
            pass
        driver.quit()


# =========================================================
# MAIN
# =========================================================

def main(compte_idx=None):
    print("Test DB:", test_connexion())

    nb_comptes  = max(len(COMPTES_BGA), 1)

    # Répartir les joueurs entre les comptes
    repartition = [[] for _ in range(nb_comptes)]
    for i, pid in enumerate(PLAYER_IDS):
        repartition[i % nb_comptes].append(pid)

    print("\n=== RÉPARTITION ===")
    for i, joueurs in enumerate(repartition):
        print(f"  Compte {i} : {joueurs}")
    print("===================\n")

    if compte_idx is not None:
        # Mode test : un seul compte
        worker(compte_idx, repartition[compte_idx])
    else:
        # Mode normal : tous les comptes en parallèle
        processes = []
        for i in range(nb_comptes):
            if not repartition[i]:
                continue
            p = Process(target=worker, args=(i, repartition[i]))
            p.start()
            processes.append(p)
            time.sleep(2)

        for p in processes:
            p.join()

    print("\n✅ Scraping terminé !")


# =========================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--compte", type=int, default=None,
        help="Index du compte (0, 1, 2...). Sans argument = tous en parallèle."
    )
    args = parser.parse_args()
    main(compte_idx=args.compte)