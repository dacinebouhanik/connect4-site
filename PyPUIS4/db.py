# db.py
import os
import psycopg2

from dotenv import load_dotenv

load_dotenv()
# =========================================================
# CONNEXION
# =========================================================

def get_conn():
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise Exception("DATABASE_URL non définie dans les variables d'environnement")

    # Ajoute sslmode=require si pas déjà présent
    if "sslmode" not in database_url:
        if "?" in database_url:
            database_url += "&sslmode=require"
        else:
            database_url += "?sslmode=require"

    try:
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        print("ERREUR CONNEXION POSTGRES :", e)
        raise

# =========================================================
# TEST
# =========================================================

def test_connexion():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT 1;")
    res = cur.fetchone()

    cur.close()
    conn.close()

    return res


# =========================================================
# COUPS (symétrie / canonique)
# =========================================================

def coups_symetrique(coups: str, nb_colonnes: int) -> str:
    """
    Ex: nb_colonnes=9, coup "1" -> sym "9"
    """
    res = []

    for ch in (coups or ""):
        if ch.isdigit():
            c = int(ch)
            c_m = nb_colonnes + 1 - c
            res.append(str(c_m))

    return "".join(res)


def coups_canonique(coups: str, nb_colonnes: int):

    sym = coups_symetrique(coups, nb_colonnes)
    can = min(coups, sym)

    return can, sym


# =========================================================
# INSERT PARTIE
# =========================================================

def inserer_partie(
    lignes,
    colonnes,
    couleur_depart,
    joueur_courant,
    statut,
    resultat,
    coups: str,
    confiance=1
):

    coups = (coups or "").strip()

    if coups == "":
        return False, "Impossible : coups vides", None

    if colonnes > 9:
        return False, "Colonnes > 9 incompatibles", None

    for ch in coups:
        if not ch.isdigit():
            return False, "Coups invalides", None

        c = int(ch)

        if c < 1 or c > colonnes:
            return False, f"Coup invalide '{ch}'", None

    can, sym = coups_canonique(coups, colonnes)

    print("DEBUG INSERT :", coups, resultat)

    conn = get_conn()

    try:

        cur = conn.cursor()

        # insertion partie
        cur.execute(
            """
            INSERT INTO games
            (lignes, colonnes, couleur_depart, joueur_courant, statut, resultat, confiance)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (lignes, colonnes, couleur_depart, joueur_courant, statut, resultat, confiance)
        )

        game_id = cur.fetchone()[0]

        # insertion coups
        cur.execute(
            """
            INSERT INTO games_coups
            (game_id, coups, coups_symetrique, coups_canonique)
            VALUES (%s,%s,%s,%s)
            """,
            (game_id, coups, sym, can)
        )

        conn.commit()
        cur.close()

        print("PARTIE INSÉRÉE ID :", game_id)

        return True, "Partie insérée", game_id

    except psycopg2.IntegrityError as e:

        conn.rollback()

        if getattr(e, "pgcode", None) == "23505":
            return False, "Doublon", None

        return False, f"Erreur intégrité : {e}", None

    except Exception as e:

        conn.rollback()

        print("ERREUR INSERT :", e)

        return False, str(e), None

    finally:

        conn.close()


# =========================================================
# LECTURE
# =========================================================

def lister_parties():

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT g.id, g.created_at, g.statut, g.resultat, g.confiance, c.coups
        FROM games g
        JOIN games_coups c ON c.game_id = g.id
        ORDER BY g.id
        """
    )

    res = cur.fetchall()

    cur.close()
    conn.close()

    return res


def lister_parties_jeu():

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT g.id, g.created_at, g.statut, g.resultat, g.confiance, c.coups
        FROM games g
        JOIN games_coups c ON c.game_id = g.id
        ORDER BY g.id DESC
        LIMIT 200
        """
    )

    res = cur.fetchall()

    cur.close()
    conn.close()

    return res


def get_partie(partie_id):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            g.id, g.created_at, g.lignes, g.colonnes,
            g.couleur_depart, g.joueur_courant,
            g.statut, g.resultat, g.confiance,
            c.coups, c.coups_symetrique, c.coups_canonique
        FROM games g
        JOIN games_coups c ON c.game_id = g.id
        WHERE g.id = %s
        """,
        (partie_id,)
    )

    res = cur.fetchone()

    cur.close()
    conn.close()

    return res


# =========================================================
# IMPORT FICHIER
# =========================================================

def extraire_coups_depuis_nom_fichier(chemin_fichier):

    nom = os.path.basename(chemin_fichier)

    base, _ = os.path.splitext(nom)

    coups = "".join(ch for ch in base if ch.isdigit())

    return coups


def inserer_partie_depuis_fichier(
    chemin_fichier,
    lignes=9,
    colonnes=9,
    couleur_depart=1,
    joueur_courant=1,
    confiance=3
):

    coups = extraire_coups_depuis_nom_fichier(chemin_fichier)

    if coups == "":
        return False, "Nom fichier invalide", None

    return inserer_partie(
        lignes=lignes,
        colonnes=colonnes,
        couleur_depart=couleur_depart,
        joueur_courant=joueur_courant,
        statut="in_progress",
        resultat=None,
        coups=coups,
        confiance=confiance
    )


# =========================================================
# IA simple : recherche parties similaires
# =========================================================

def chercher_parties_similaires(prefixe: str, limite=5000):

    prefixe = (prefixe or "").strip()

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT c.coups, g.resultat, g.confiance
        FROM games g
        JOIN games_coups c ON c.game_id = g.id
        WHERE c.coups LIKE %s
        LIMIT %s
        """,
        (prefixe + "%", limite)
    )

    res = cur.fetchall()

    cur.close()
    conn.close()

    return res