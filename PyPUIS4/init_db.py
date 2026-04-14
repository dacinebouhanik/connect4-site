import psycopg2
import os

def init_db():
    database_url = os.environ.get("DATABASE_URL")

    if database_url is None:
        print("init_db ignoré : DATABASE_URL non définie (local)")
        return

    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id SERIAL PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            lignes INT,
            colonnes INT,
            couleur_depart INT,
            joueur_courant INT,
            statut TEXT,
            resultat TEXT,
            confiance INT
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS games_coups (
            id SERIAL PRIMARY KEY,
            game_id INT REFERENCES games(id),
            coups TEXT,
            coups_symetrique TEXT,
            coups_canonique TEXT
        );
        """)

        conn.commit()
        cur.close()
        conn.close()

        print("Tables PostgreSQL vérifiées/créées")

    except Exception as e:
        print(f"init_db warning : {e}")
        print("L'application continue sans init_db.")