# scrap_bga_requests.py

import requests
import re
import time
from db import inserer_partie

LIGNES = 9
COLONNES = 9
CONFIANCE = 3

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "fr-FR,fr;q=0.9"
}

def extraire_coups(html):
    pattern = r'"type":"playDisc".*?"x":"(\d+)"'
    coups = re.findall(pattern, html, flags=re.DOTALL)
    return "".join(coups)

def est_9x9(html):
    return '"boardSize":9' in html or "9 x 9" in html

def extraire_elos(html):
    pattern = r'"elo":"(\d+)"'
    elos = re.findall(pattern, html)

    if len(elos) >= 2:
        return int(elos[0]), int(elos[1])

    return None, None

def joueurs_forts(html, seuil=1600):
    elo1, elo2 = extraire_elos(html)

    if elo1 is None:
        return False

    return elo1 >= seuil and elo2 >= seuil

def partie_valide(coups):
    return len(coups) >= 12


def scraper_range(start_id, end_id):

    session = requests.Session()
    session.headers.update(HEADERS)

    inserees = 0

    for gid in range(start_id, end_id):

        url = f"https://boardgamearena.com/archive/replay/{gid}/"

        try:
            r = session.get(url, timeout=25)

            if r.status_code != 200:
                continue

            html = r.text

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
            print("Erreur :", gid)

        time.sleep(0.4)

    print("Total insérées :", inserees)


if __name__ == "__main__":
    scraper_range(1000000, 1020000)