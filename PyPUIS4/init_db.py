import psycopg2
import os

conn = psycopg2.connect(os.environ["DATABASE_URL"])
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

print("Tables créées")