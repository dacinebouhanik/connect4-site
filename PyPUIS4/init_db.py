import psycopg2
import os

database_url = os.environ.get("DATABASE_URL")

# si on est en local et que la variable n'existe pas
if database_url is None:
    print("init_db ignoré : DATABASE_URL non définie (local)")
else:
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