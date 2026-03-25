import os
import time
import random

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager


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
        self.wait = WebDriverWait(self.driver, 20)

    def login(self):

        print("Opening BGA... Please log in manually if prompted.")

        self.driver.get("https://en.boardgamearena.com/account")

        login_wait = WebDriverWait(self.driver, 600)

        login_wait.until(lambda d: "account" not in d.current_url)

        print("\n--- LOGIN DETECTED ---")

        time.sleep(2)

    def navigate_to_game(self, game_name="connectfour"):

        url = f"https://boardgamearena.com/gamepanel?game={game_name}"

        print(f"Navigating to: {url}")

        self.driver.get(url)

    def start_table(self):

        print("🔍 Monitoring table state (Waiting for Start or Accept)...")

        start_xpath = "//a[contains(@class, 'bga-button')]//div[contains(text(), 'Démarrer')]"
        accept_id = "ags_start_game_accept"
        board_id = "board"

        while True:

            self.clear_popups()

            try:

                board_elements = self.driver.find_elements(By.ID, board_id)

                if board_elements and board_elements[0].is_displayed():

                    print("✅ Game board detected! Transitioning to play loop.")

                    return True

                accept_btns = self.driver.find_elements(By.ID, accept_id)

                if accept_btns and accept_btns[0].is_displayed():

                    print("✅ Opponent found! Clicking 'Accepter'...")

                    self.driver.execute_script("arguments[0].click();", accept_btns[0])

                    time.sleep(2)

                    continue

                start_btns = self.driver.find_elements(By.XPATH, start_xpath)

                if start_btns and start_btns[0].is_displayed():

                    print("✅ Clicking 'Démarrer' to open the table...")

                    self.driver.execute_script("arguments[0].click();", start_btns[0])

                    time.sleep(2)

                    continue

                body_class = self.driver.find_element(By.TAG_NAME, "body").get_attribute("class")

                if "current_player_is_active" in body_class:

                    print("✅ Active turn detected via body class.")

                    return True

                time.sleep(2)

            except WebDriverException:

                print("⌛ Connection unstable, retrying...")

                time.sleep(2)

            except Exception:

                time.sleep(2)

    def play_random_move(self):

        try:

            title_text = self.driver.find_element(By.ID, "pagemaintitletext").text

            if "Fin de la partie" in title_text or "Victoire" in title_text:

                print(f"🏁 Game Over Detected: {title_text}")

                return "GAME_OVER"

            is_active = self.driver.find_elements(By.CSS_SELECTOR, "body.current_player_is_active")

            if not is_active:

                return "WAITING"

            print("🎲 My turn! Playing...")

            clickable_squares = self.driver.find_elements(By.CSS_SELECTOR, "#board .square.possibleMove")

            if clickable_squares:

                target = random.choice(clickable_squares)

                self.driver.execute_script("arguments[0].click();", target)

                time.sleep(random.randint(2,4))

                return "MOVED"

            return "WAITING"

        except Exception:

            print("⌛ Polling game state...")

            return "WAITING"

    def clear_popups(self):

        try:

            popups = self.driver.find_elements(By.CSS_SELECTOR, "div[id^='continue_btn_']")

            for popup in popups:

                if popup.is_displayed():

                    print("🏆 Trophy popup detected! Clearing...")

                    self.driver.execute_script("arguments[0].click();", popup)

                    time.sleep(1)

                    self.clear_popups()

        except Exception:

            pass

    def select_realtime_mode(self):

        print("🔄 Selecting realtime mode...")

        while True:

            try:

                dropdown_button = self.wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, ".panel-block--buttons__mode-select .bga-dropdown-button")
                ))

                current_mode_text = dropdown_button.text.upper()

                if "TEMPS RÉEL" in current_mode_text:

                    print("✅ Mode Temps Réel confirmé.")

                    return True

                print(f"Mode actuel : {current_mode_text}")

                self.driver.execute_script("arguments[0].click();", dropdown_button)

                time.sleep(1.5)

                realtime_option = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".bga-dropdown-option-realtime"))
                )

                self.driver.execute_script("arguments[0].click();", realtime_option)

                time.sleep(2)

            except Exception:

                print("⌛ Retry selecting mode...")

                time.sleep(2)

    def close(self):

        print("\nBot terminé. Appuie sur Entrée pour fermer.")

        input()

        self.driver.quit()


if __name__ == "__main__":

    bot = BGABot()

    counter = 0

    try:

        bot.login()

        while True:

            print("\n🚀 Starting a new session...")

            bot.navigate_to_game("connectfour")

            bot.select_realtime_mode()

            if bot.start_table():

                counter += 1

                print(f"\n🎮 Playing game number {counter}\n")

                game_in_progress = True

                while game_in_progress:

                    status = bot.play_random_move()

                    if status == "GAME_OVER":

                        print("♻️ Game ended. Starting a new one in 10 seconds...")

                        time.sleep(10)

                        game_in_progress = False

                    time.sleep(3)

    except Exception as main_error:

        print(f"Fatal Error: {main_error}")

    finally:

        bot.close()
