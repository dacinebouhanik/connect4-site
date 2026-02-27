# db.py
import os
import psycopg2

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "connect4",
    "user": "postgres",
    "password": "311004"
}

# =========================================================
# TEST
# =========================================================

def test_connexion():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT 1;")
    res = cur.fetchone()
    cur.close()
    conn.close()
    return res


# =========================================================
# COUPS (sym / canon)
# =========================================================

def coups_symetrique(coups: str, nb_colonnes: int) -> str:
    """
    Ex: nb_colonnes=9, coup "1" -> sym "9", "2"->"8", ...
    """
    res = []
    for ch in (coups or ""):
        if ch.isdigit():
            c = int(ch)
            c_m = nb_colonnes + 1 - c
            res.append(str(c_m))
    return "".join(res)


def coups_canonique(coups: str, nb_colonnes: int) -> tuple[str, str]:
    """
    Retourne (canonique, symetrique).
    canonique = min(coups, sym) en ordre lexicographique.
    """
    sym = coups_symetrique(coups, nb_colonnes)
    can = min(coups, sym)
    return can, sym


# =========================================================
# INSERT PARTIE
# =========================================================

def inserer_partie(lignes, colonnes, couleur_depart, joueur_courant,
                   statut, resultat, coups: str, confiance=1):
    """
    Insère une partie dans games + games_coups (transaction).
    confiance :
        0 = exprès de perdre
        1 = aléatoire
        2 = minimax
        3 = BGA / import externe
    Retour: (ok, msg, id)
    """
    coups = (coups or "").strip()
    if coups == "":
        return False, "Impossible : coups vides", None

    # Sécurité simple : colonnes <= 9 si on encode coup par chiffre
    if colonnes > 9:
        return False, "Colonnes > 9 : format des coups (chiffres) incompatible.", None

    # Vérif coups dans 1..colonnes
    for ch in coups:
        if not ch.isdigit():
            return False, "Coups invalides : uniquement des chiffres attendus.", None
        c = int(ch)
        if c < 1 or c > colonnes:
            return False, f"Coup invalide '{ch}' (doit être entre 1 et {colonnes})", None

    can, sym = coups_canonique(coups, colonnes)

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()

        # Insert games (avec confiance)
        cur.execute("""
            INSERT INTO games
            (lignes, colonnes, couleur_depart, joueur_courant, statut, resultat, confiance)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (lignes, colonnes, couleur_depart, joueur_courant, statut, resultat, confiance))

        game_id = cur.fetchone()[0]

        # Insert games_coups
        cur.execute("""
            INSERT INTO games_coups
            (game_id, coups, coups_symetrique, coups_canonique)
            VALUES (%s,%s,%s,%s)
        """, (game_id, coups, sym, can))

        conn.commit()
        cur.close()
        return True, f"Partie insérée (id={game_id})", game_id

    except psycopg2.IntegrityError as e:
        conn.rollback()
        # 23505 = unique_violation (souvent doublon)
        if getattr(e, "pgcode", None) == "23505":
            return False, "Doublon : déjà dans la base (ou symétrique).", None
        return False, f"Erreur d'intégrité : {e}", None

    except Exception as e:
        conn.rollback()
        return False, f"Erreur : {e}", None

    finally:
        conn.close()


# =========================================================
# LECTURE
# =========================================================

def lister_parties():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        SELECT g.id, g.created_at, g.statut, g.resultat, g.confiance, c.coups
        FROM games g
        JOIN games_coups c ON c.game_id = g.id
        ORDER BY g.id
    """)
    res = cur.fetchall()
    cur.close()
    conn.close()
    return res


def get_partie(partie_id: int):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        SELECT
            g.id, g.created_at, g.lignes, g.colonnes, g.couleur_depart, g.joueur_courant,
            g.statut, g.resultat, g.confiance,
            c.coups, c.coups_symetrique, c.coups_canonique
        FROM games g
        JOIN games_coups c ON c.game_id = g.id
        WHERE g.id = %s
    """, (partie_id,))
    res = cur.fetchone()
    cur.close()
    conn.close()
    return res


def lister_parties_jeu():
    """
    Liste courte pour l'UI 'Charger depuis BD'
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        SELECT g.id, g.created_at, g.statut, g.resultat, g.confiance, c.coups
        FROM games g
        JOIN games_coups c ON c.game_id = g.id
        ORDER BY g.id DESC
        LIMIT 200
    """)
    res = cur.fetchall()
    cur.close()
    conn.close()
    return res


# =========================================================
# IMPORT FICHIER (.txt) : nom = "3131313.txt"
# =========================================================

def extraire_coups_depuis_nom_fichier(chemin_fichier: str) -> str:
    nom = os.path.basename(chemin_fichier)
    base, _ = os.path.splitext(nom)
    coups = "".join(ch for ch in base if ch.isdigit())
    return coups


def inserer_partie_depuis_fichier(chemin_fichier: str,
                                  lignes=9, colonnes=9,
                                  couleur_depart=1, joueur_courant=1,
                                  confiance=3):
    """
    Par défaut confiance=3 (import externe), tu peux mettre 1 si tu veux.
    """
    coups = extraire_coups_depuis_nom_fichier(chemin_fichier)

    if coups == "":
        return False, "Nom de fichier invalide. Exemple : 3131313.txt", None

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
# IA "BASE" : trouver des parties similaires
# =========================================================

def chercher_parties_similaires(prefixe: str, limite=5000):
    """
    Retourne des lignes (coups, resultat, confiance) dont coups commence par prefixe
    """
    prefixe = (prefixe or "").strip()

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        SELECT c.coups, g.resultat, g.confiance
        FROM games g
        JOIN games_coups c ON c.game_id = g.id
        WHERE c.coups LIKE %s
        LIMIT %s
    """, (prefixe + "%", limite))
    res = cur.fetchall()
    cur.close()
    conn.close()
    return res
