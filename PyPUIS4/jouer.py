import time
import random

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager

from modele import Puissance4Modele


# =========================================================
# CONFIGURATION
# =========================================================

PROFONDEUR_IA = 7
COLONNES_BGA  = 7
LIGNES_BGA    = 6

# Le plateau 9x9 a 3 lignes vides en haut (9-6=3)
# La première ligne réelle BGA = index 3 dans le plateau 9x9
OFFSET_LIGNES = 9 - LIGNES_BGA  # = 3

ROUGE_CSS = "ff0000"
JAUNE_CSS = "ffff00"


# =========================================================
# LECTURE DU PLATEAU BGA
# =========================================================

def lire_plateau_bga(driver):
    """
    Lit le plateau via les IDs square_{col}_{row}.
    BGA : col 1..7 (gauche→droite), row 1..6 (haut→bas)
    Modèle IA : plateau 9x9, lignes 0..8 (haut→bas)

    Mapping :
      BGA row 1 → plateau[3]   (OFFSET_LIGNES=3)
      BGA row 6 → plateau[8]   (bas)
      BGA col 1 → plateau[i][0]
      BGA col 7 → plateau[i][6]
    """
    try:
        # Plateau 9x9 vide
        plateau = [[0] * 9 for _ in range(9)]

        for col_bga in range(1, COLONNES_BGA + 1):
            for row_bga in range(1, LIGNES_BGA + 1):
                case_id = f"square_{col_bga}_{row_bga}"
                case    = driver.find_element(By.ID, case_id)
                discs   = case.find_elements(By.CSS_SELECTOR, ".disc")
                if not discs:
                    continue
                disc_cls = discs[0].get_attribute("class") or ""

                # Convertir en index plateau 9x9
                row_ia = OFFSET_LIGNES + (row_bga - 1)  # 3..8
                col_ia = col_bga - 1                     # 0..6

                if ROUGE_CSS in disc_cls:
                    plateau[row_ia][col_ia] = 1
                elif JAUNE_CSS in disc_cls:
                    plateau[row_ia][col_ia] = 2

        # Affichage debug
        sym = {0: ".", 1: "R", 2: "J"}
        print("  [Grille lue]")
        for i in range(OFFSET_LIGNES, 9):
            row_bga = i - OFFSET_LIGNES + 1
            print(f"  row{row_bga}: " + " ".join(sym[plateau[i][j]] for j in range(COLONNES_BGA)))

        nb_pions = sum(plateau[i][j] for i in range(9) for j in range(9))
        print(f"  → {nb_pions} pion(s) détecté(s)")

        return plateau

    except Exception as e:
        print(f"⚠️ Erreur lecture plateau : {e}")
        return None


def detecter_mon_joueur(driver):
    try:
        script = """
            try {
                var pid     = window.gameui.player_id;
                var players = window.gameui.gamedatas.players;
                var idx     = Object.keys(players).indexOf(String(pid));
                return idx + 1;
            } catch(e) { return null; }
        """
        result = driver.execute_script(script)
        if result in (1, 2):
            emoji = "🔴 Rouge" if result == 1 else "🟡 Jaune"
            print(f"🎯 Je joue joueur {result} ({emoji})")
            return result
    except Exception:
        pass
    print("⚠️ Joueur non détecté → suppose joueur 1 (Rouge)")
    return 1


# =========================================================
# BOT
# =========================================================

class BGABot:

    def __init__(self):
        options = Options()
        options.set_preference("dom.webnotifications.enabled", False)
        options.set_preference("dom.push.enabled", False)

        print("Launching Firefox...")
        self.driver = webdriver.Firefox(
            service=Service(GeckoDriverManager().install()),
            options=options
        )
        self.driver.set_page_load_timeout(30)
        self.wait       = WebDriverWait(self.driver, 20)
        self.modele     = Puissance4Modele()
        self.mon_joueur = None

    # ── Login ──────────────────────────────────────────────

    def login(self):
        print("Opening BGA... Please log in manually.")
        self.driver.get("https://en.boardgamearena.com/account")
        WebDriverWait(self.driver, 600).until(
            lambda d: "account" not in d.current_url
        )
        print("--- LOGIN DETECTED ---")
        time.sleep(2)

    def navigate_to_game(self, game_name="connectfour"):
        url = f"https://boardgamearena.com/gamepanel?game={game_name}"
        print(f"Navigating to: {url}")
        self.driver.get(url)

    # ── Démarrage ──────────────────────────────────────────

    def start_table(self):
        print("🔍 Waiting for game to start...")
        start_xpath = "//a[contains(@class, 'bga-button')]//div[contains(text(), 'Démarrer')]"
        accept_id   = "ags_start_game_accept"

        while True:
            self.clear_popups()
            try:
                boards = self.driver.find_elements(By.ID, "board")
                if boards and boards[0].is_displayed():
                    print("✅ Board detected!")
                    return True

                accepts = self.driver.find_elements(By.ID, accept_id)
                if accepts and accepts[0].is_displayed():
                    print("✅ Clicking Accepter...")
                    self.driver.execute_script("arguments[0].click();", accepts[0])
                    time.sleep(2)
                    continue

                starts = self.driver.find_elements(By.XPATH, start_xpath)
                if starts and starts[0].is_displayed():
                    print("✅ Clicking Démarrer...")
                    self.driver.execute_script("arguments[0].click();", starts[0])
                    time.sleep(2)
                    continue

                body_cls = self.driver.find_element(
                    By.TAG_NAME, "body"
                ).get_attribute("class")
                if "current_player_is_active" in body_cls:
                    print("✅ Active turn detected.")
                    return True

                time.sleep(2)

            except WebDriverException:
                print("⌛ Connection unstable...")
                time.sleep(2)
            except Exception:
                time.sleep(2)

    # ── Vérification coups jouables ────────────────────────

    def a_des_coups_jouables(self):
        """Vérifie si au moins une colonne est jouable."""
        try:
            for col in range(1, COLONNES_BGA + 1):
                case    = self.driver.find_element(By.ID, f"square_{col}_1")
                classes = case.get_attribute("class") or ""
                if "possibleMove" in classes:
                    return True
            return False
        except Exception:
            return False

    # ── Coup IA ────────────────────────────────────────────

    def calculer_coup_ia(self):
        """
        Lit le plateau, calcule le meilleur coup.

        Mapping colonnes :
          IA retourne index 0-8 (colonnes du modèle 9x9)
          BGA attend colonne 1-7
          Donc : col_bga = col_ia + 1
        """
        plateau = lire_plateau_bga(self.driver)
        if plateau is None:
            return None

        # Injecter dans le modèle
        self.modele.plateau        = plateau
        self.modele.joueur_courant = self.mon_joueur
        self.modele.resultat       = None

        # ✅ Colonnes valides : index 0-6 (les 7 colonnes BGA)
        # Une colonne est valide si sa case du haut (OFFSET_LIGNES) est vide
        valides_ia = [
            j for j in range(COLONNES_BGA)
            if plateau[OFFSET_LIGNES][j] == 0
        ]

        if not valides_ia:
            print("⚠️ Aucune colonne valide")
            return None

        print(f"🧠 IA réfléchit... (profondeur {PROFONDEUR_IA})")
        print(f"   Colonnes valides BGA : {[v+1 for v in valides_ia]}")
        t = time.time()

        try:
            scores = self.modele.calculer_scores_minimax(PROFONDEUR_IA)
        except Exception as e:
            print(f"⚠️ Erreur IA : {e}")
            return None

        print(f"⏱️  {time.time()-t:.2f}s")
        print(f"   Scores bruts IA : {scores}")

        if not scores:
            return None

        # ✅ FIX : scores retournés avec index 0-8
        # On garde uniquement les colonnes BGA valides (index 0-6)
        scores_valides = {
            col_ia: sc for col_ia, sc in scores.items()
            if col_ia in valides_ia
        }

        if not scores_valides:
            print("⚠️ Aucun score valide")
            return None

        print(f"📊 Scores valides : { {c+1: s for c, s in sorted(scores_valides.items())} }")

        # Meilleure colonne IA (index 0-6)
        col_ia  = max(scores_valides, key=scores_valides.get)

        # ✅ Convertir en colonne BGA (1-7)
        col_bga = col_ia + 1

        print(f"✅ IA → colonne BGA {col_bga} (score={scores_valides[col_ia]})")
        return col_bga

    def play_ia_move(self):
        try:
            title = self.driver.find_element(By.ID, "pagemaintitletext").text
            if "Fin de la partie" in title or "Victoire" in title:
                print(f"🏁 Game Over : {title}")
                return "GAME_OVER"

            if not self.driver.find_elements(
                By.CSS_SELECTOR, "body.current_player_is_active"
            ):
                return "WAITING"

            print("🎮 Mon tour !")

            if self.mon_joueur is None:
                self.mon_joueur = detecter_mon_joueur(self.driver)

            if not self.a_des_coups_jouables():
                print("⏳ Aucun coup jouable")
                return "WAITING"

            col_bga = self.calculer_coup_ia()

            if col_bga and self._cliquer_colonne(col_bga):
                time.sleep(random.uniform(1, 2))
                return "MOVED"

            # Fallback aléatoire
            print("⚠️ Fallback aléatoire")
            for col in range(1, COLONNES_BGA + 1):
                try:
                    case = self.driver.find_element(By.ID, f"square_{col}_1")
                    if "possibleMove" in (case.get_attribute("class") or ""):
                        self.driver.execute_script("arguments[0].click();", case)
                        time.sleep(1)
                        return "MOVED"
                except Exception:
                    continue

            return "WAITING"

        except Exception as e:
            print(f"⌛ {e}")
            return "WAITING"

    def _cliquer_colonne(self, col_bga):
        """
        Clique sur la case row=1 de la colonne col_bga (1-7).
        BGA gère la gravité côté serveur.
        """
        try:
            case_id = f"square_{col_bga}_1"
            case    = self.driver.find_element(By.ID, case_id)
            classes = case.get_attribute("class") or ""

            if "possibleMove" not in classes:
                print(f"⚠️ Col {col_bga} non jouable")
                return False

            self.driver.execute_script("arguments[0].click();", case)
            print(f"✅ Clic colonne BGA {col_bga}")
            return True

        except Exception as e:
            print(f"⚠️ Erreur clic col {col_bga} : {e}")
            return False

    # ── Utilitaires ────────────────────────────────────────

    def clear_popups(self):
        try:
            for p in self.driver.find_elements(
                By.CSS_SELECTOR, "div[id^='continue_btn_']"
            ):
                if p.is_displayed():
                    print("🏆 Popup cleared")
                    self.driver.execute_script("arguments[0].click();", p)
                    time.sleep(1)
                    self.clear_popups()
        except Exception:
            pass

    def select_realtime_mode(self):
        print("🔄 Selecting realtime mode...")
        while True:
            try:
                btn = self.wait.until(EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    ".panel-block--buttons__mode-select .bga-dropdown-button"
                )))
                if "TEMPS RÉEL" in btn.text.upper():
                    print("✅ Mode Temps Réel confirmé.")
                    return True
                self.driver.execute_script("arguments[0].click();", btn)
                time.sleep(1.5)
                opt = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, ".bga-dropdown-option-realtime")
                    )
                )
                self.driver.execute_script("arguments[0].click();", opt)
                time.sleep(2)
            except Exception:
                print("⌛ Retry mode...")
                time.sleep(2)

    def reset_pour_nouvelle_partie(self):
        self.mon_joueur = None
        self.modele.nouvelle_partie()

    def close(self):
        print("\nBot terminé. Appuie sur Entrée pour fermer.")
        input()
        self.driver.quit()


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    bot     = BGABot()
    counter = 0

    try:
        bot.login()

        while True:
            print("\n🚀 Starting new session...")
            bot.navigate_to_game("connectfour")
            bot.select_realtime_mode()

            if bot.start_table():
                counter += 1
                print(f"\n🎮 Game #{counter}\n")

                bot.reset_pour_nouvelle_partie()
                time.sleep(2)
                bot.mon_joueur = detecter_mon_joueur(bot.driver)

                game_in_progress = True
                while game_in_progress:
                    status = bot.play_ia_move()
                    if status == "GAME_OVER":
                        print("♻️ Nouvelle partie dans 10s...")
                        time.sleep(10)
                        game_in_progress = False
                    time.sleep(3)

    except Exception as e:
        print(f"Fatal Error: {e}")
    finally:
        bot.close()