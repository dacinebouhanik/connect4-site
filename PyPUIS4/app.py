from flask import Flask, render_template, jsonify, request
from modele import Puissance4Modele
from db import inserer_partie, lister_parties_jeu, get_partie
import os
import sys
import init_db

sys.setrecursionlimit(10000)
init_db.init_db()

app = Flask(__name__)

# =========================================================
# HELPERS
# =========================================================

def modele_depuis_data(data):
    """Reconstruit un modèle depuis les données envoyées par le client."""
    m = Puissance4Modele.__new__(Puissance4Modele)
    m.lignes         = data.get("lignes", 9)
    m.colonnes       = data.get("colonnes", 9)
    m.couleur_depart = data.get("couleur_depart", 1)
    m.joueur_courant = data.get("joueur_courant", 1)
    m.resultat       = data.get("resultat", None)
    m.historique     = [tuple(h) for h in data.get("historique", [])]

    plateau = data.get("plateau")
    if plateau:
        m.plateau = plateau
    else:
        m.plateau = m.creer_plateau()

    # Initialiser Zobrist pour la table de transposition
    m._init_zobrist()
    m._hash_courant = m._calculer_hash_complet()
    m.table_transposition = {}

    return m


def decoder_score(score, joueur_courant):
    """
    Décode le score minimax en (gagnant, nb_coups).
    Convention : SCORE_VICTOIRE = 1_000_000
    """
    SV = Puissance4Modele.SCORE_VICTOIRE

    if score > SV // 2:
        demi = SV - score
        coups = (demi + 1) // 2
        gagnant = "rouge" if joueur_courant == Puissance4Modele.ROUGE else "jaune"
        return gagnant, coups

    if score < -(SV // 2):
        demi = SV + score
        coups = (demi + 1) // 2
        adv = Puissance4Modele.JAUNE if joueur_courant == Puissance4Modele.ROUGE else Puissance4Modele.ROUGE
        gagnant = "rouge" if adv == Puissance4Modele.ROUGE else "jaune"
        return gagnant, coups

    return None, None

# =========================================================
# PAGE PRINCIPALE
# =========================================================

@app.route("/")
def accueil():
    return render_template("index.html")

# =========================================================
# NOUVELLE PARTIE
# =========================================================

@app.route("/api/nouvelle", methods=["POST"])
def nouvelle():
    data = request.get_json(silent=True) or {}
    m = Puissance4Modele()
    m.lignes         = data.get("lignes", 9)
    m.colonnes       = data.get("colonnes", 9)
    m.couleur_depart = data.get("couleur_depart", 1)
    m.joueur_courant = m.couleur_depart
    m.plateau        = m.creer_plateau()
    m.historique     = []
    m.resultat       = None

    return jsonify({
        "status":         "ok",
        "plateau":        m.plateau,
        "joueur_courant": m.joueur_courant,
        "couleur_depart": m.couleur_depart,
        "lignes":         m.lignes,
        "colonnes":       m.colonnes,
        "historique":     [],
        "resultat":       None,
    })

# =========================================================
# JOUER COUP HUMAIN
# =========================================================

@app.route("/api/jouer", methods=["POST"])
def jouer():
    data   = request.get_json()
    modele = modele_depuis_data(data)
    col    = int(data["col"])

    if modele.resultat is not None:
        return jsonify({"status": "fin"})

    lig = modele.jouer_coup(col)
    if lig is None:
        return jsonify({"status": "col_invalide"})

    coords = modele.verifier_victoire(modele.joueur_courant)
    if coords is not None:
        gagnant = "rouge" if modele.joueur_courant == modele.ROUGE else "jaune"
        modele.definir_resultat(gagnant)
    elif modele.plateau_plein():
        modele.definir_resultat("nul")
    else:
        modele.changer_joueur()

    return jsonify({
        "status":         "ok",
        "plateau":        modele.plateau,
        "joueur_courant": modele.joueur_courant,
        "historique":     [list(h) for h in modele.historique],
        "resultat":       modele.resultat,
    })

# =========================================================
# COUP IA
# =========================================================

@app.route("/api/ia_step", methods=["POST"])
def ia_step():
    data       = request.get_json()
    modele     = modele_depuis_data(data)
    ia_type    = data.get("ia_type", "minimax")
    profondeur = min(int(data.get("profondeur", 7)), 10)

    if modele.resultat is not None:
        return jsonify({"status": "fin"})

    if ia_type == "aleatoire":
        col = modele.coup_aleatoire()
    else:
        scores = modele.calculer_scores_minimax(profondeur)
        if not scores:
            modele.definir_resultat("nul")
            return jsonify({"status": "nul"})
        best_score = max(scores.values())
        best_cols  = [c for c, s in scores.items() if s == best_score]
        centre     = modele.colonnes // 2
        col        = min(best_cols, key=lambda c: abs(c - centre))

    modele.jouer_coup(col)

    coords = modele.verifier_victoire(modele.joueur_courant)
    if coords is not None:
        gagnant = "rouge" if modele.joueur_courant == modele.ROUGE else "jaune"
        modele.definir_resultat(gagnant)
    elif modele.plateau_plein():
        modele.definir_resultat("nul")
    else:
        modele.changer_joueur()

    return jsonify({
        "status":         "ok",
        "col":            col,
        "plateau":        modele.plateau,
        "joueur_courant": modele.joueur_courant,
        "historique":     [list(h) for h in modele.historique],
        "resultat":       modele.resultat,
    })

# =========================================================
# ANNULER COUP
# =========================================================

@app.route("/api/annuler", methods=["POST"])
def annuler():
    data   = request.get_json()
    modele = modele_depuis_data(data)

    modele.annuler_dernier_coup()

    return jsonify({
        "status":         "ok",
        "plateau":        modele.plateau,
        "joueur_courant": modele.joueur_courant,
        "historique":     [list(h) for h in modele.historique],
        "resultat":       modele.resultat,
    })

# =========================================================
# CONSEIL IA
# =========================================================

@app.route("/api/conseil", methods=["POST"])
def conseil():
    data       = request.get_json()
    modele     = modele_depuis_data(data)
    profondeur = min(int(data.get("profondeur", 7)), 10)

    if modele.resultat is not None:
        return jsonify({"status": "fin"})

    scores = modele.calculer_scores_minimax(profondeur)
    if not scores:
        return jsonify({"status": "erreur"})

    best_score   = max(scores.values())
    best_cols    = [c for c, s in scores.items() if s == best_score]
    centre       = modele.colonnes // 2
    meilleur_col = min(best_cols, key=lambda c: abs(c - centre))

    gagnant, nb_coups = decoder_score(best_score, modele.joueur_courant)

    if gagnant is not None:
        nom_g = "Rouge" if gagnant == "rouge" else "Jaune"
        nom_j = "Rouge" if modele.joueur_courant == modele.ROUGE else "Jaune"
        if gagnant == ("rouge" if modele.joueur_courant == modele.ROUGE else "jaune"):
            verdict = "victoire"
        else:
            verdict = "defaite"
    elif best_score > 500:
        verdict = "avantage"
    elif best_score < -500:
        verdict = "desavantage"
    else:
        verdict = "equilibre"

    return jsonify({
        "status":       "ok",
        "meilleur_col": meilleur_col,
        "score":        best_score,
        "verdict":      verdict,
        "scores":       scores,
        "nb_coups":     nb_coups,
    })

# =========================================================
# MODE SITUATION — PLACER UN PION
# =========================================================

@app.route("/api/situation/placer", methods=["POST"])
def situation_placer():
    data    = request.get_json()
    modele  = modele_depuis_data(data)
    lig     = int(data["lig"])
    col     = int(data["col"])
    couleur = int(data.get("couleur", 1))

    if 0 <= lig < modele.lignes and 0 <= col < modele.colonnes:
        modele.plateau[lig][col] = couleur

    victoire_rouge = modele._verifier_victoire_sur_plateau(modele.plateau, modele.ROUGE)
    victoire_jaune = modele._verifier_victoire_sur_plateau(modele.plateau, modele.JAUNE)

    return jsonify({
        "status":         "ok",
        "plateau":        modele.plateau,
        "victoire_rouge": victoire_rouge,
        "victoire_jaune": victoire_jaune,
    })

# =========================================================
# MODE SITUATION — ANALYSER (CORRIGÉ)
# =========================================================

@app.route("/api/situation/analyser", methods=["POST"])
def situation_analyser():
    data           = request.get_json() or {}
    modele         = modele_depuis_data(data)
    joueur_analyse = int(data.get("joueur_analyse", modele.ROUGE))
    profondeur     = max(int(data.get("profondeur", 12)), 8)

    modele.joueur_courant = joueur_analyse

    if modele._verifier_victoire_sur_plateau(modele.plateau, modele.ROUGE):
        return jsonify({"gagnant": "rouge", "message": "🔴 Rouge a déjà gagné !"})
    if modele._verifier_victoire_sur_plateau(modele.plateau, modele.JAUNE):
        return jsonify({"gagnant": "jaune", "message": "🟡 Jaune a déjà gagné !"})
    if modele.plateau_plein():
        return jsonify({"gagnant": "nul", "message": "🤝 Plateau plein !"})

    scores = modele.calculer_scores_minimax(profondeur)
    if not scores:
        return jsonify({"gagnant": "inconnu", "message": "❓ Impossible d'analyser."})

    best_score   = max(scores.values())
    best_cols    = [c for c, s in scores.items() if s == best_score]
    meilleur_col = min(best_cols)
    nom_joueur   = "Rouge" if joueur_analyse == modele.ROUGE else "Jaune"
    emoji        = "🔴"    if joueur_analyse == modele.ROUGE else "🟡"

    gagnant, nb_coups = decoder_score(best_score, joueur_analyse)

    adv_nom = "Jaune" if joueur_analyse == modele.ROUGE else "Rouge"
    adv_emoji = "🟡" if joueur_analyse == modele.ROUGE else "🔴"

    if gagnant is not None:
        nom_g   = "Rouge" if gagnant == "rouge" else "Jaune"
        emoji_g = "🔴"    if gagnant == "rouge" else "🟡"

        if gagnant == ("rouge" if joueur_analyse == modele.ROUGE else "jaune"):
            message = f"{emoji_g} {nom_g} gagne en {nb_coups} coup(s) ! Meilleur coup : colonne {meilleur_col + 1}."
        else:
            message = f"{emoji_g} {nom_g} gagne en {nb_coups} coup(s). Perdu pour {nom_joueur}."
    elif best_score > 200:
        message = f"{emoji} Avantage {nom_joueur}. {nom_joueur} doit jouer colonne {meilleur_col + 1}."
        gagnant = "rouge" if joueur_analyse == modele.ROUGE else "jaune"
    elif best_score < -200:
        message = f"{adv_emoji} Avantage {adv_nom}. {nom_joueur} doit jouer colonne {meilleur_col + 1} pour résister."
        gagnant = "rouge" if joueur_analyse == modele.JAUNE else "jaune"
    elif best_score > 50:
        message = f"{emoji} Léger avantage {nom_joueur}. {nom_joueur} doit jouer colonne {meilleur_col + 1}."
        gagnant = "equilibre"
    elif best_score < -50:
        message = f"{adv_emoji} Léger avantage {adv_nom}. {nom_joueur} doit jouer colonne {meilleur_col + 1} pour résister."
        gagnant = "equilibre"
    else:
        message = f"⚖️ Position équilibrée. {nom_joueur} doit jouer colonne {meilleur_col + 1}."
        gagnant = "equilibre"

    return jsonify({
        "gagnant":      gagnant,
        "meilleur_col": meilleur_col,
        "score":        best_score,
        "message":      message,
        "scores":       {str(k): v for k, v in scores.items()},
        "nb_coups":     nb_coups,
    })

# =========================================================
# SAUVEGARDER PARTIE
# =========================================================

@app.route("/api/sauvegarder", methods=["POST"])
def sauvegarder():
    data    = request.get_json()
    modele  = modele_depuis_data(data)
    mode    = int(data.get("mode", 2))
    coups   = modele.exporter_coups_string()

    if not coups:
        return jsonify({"status": "vide"})

    confiance = 1 if mode == 2 else 2
    try:
        ok, msg, gid = inserer_partie(
            lignes=modele.lignes, colonnes=modele.colonnes,
            couleur_depart=modele.couleur_depart,
            joueur_courant=modele.joueur_courant,
            statut="finished", resultat=modele.resultat,
            coups=coups, confiance=confiance
        )
        return jsonify({"status": "ok", "id": gid})
    except Exception as e:
        return jsonify({"status": "erreur", "message": str(e)})

# =========================================================
# HISTORIQUE
# =========================================================

@app.route("/api/historique")
def historique():
    parties = lister_parties_jeu()
    data = []
    for p in parties:
        data.append({
            "id":        p[0],
            "date":      str(p[1]),
            "statut":    p[2],
            "resultat":  p[3],
            "confiance": p[4],
            "coups":     p[5]
        })
    return jsonify(data)

# =========================================================
# CHARGER PARTIE
# =========================================================

@app.route("/api/charger/<int:partie_id>")
def charger_partie(partie_id):
    partie = get_partie(partie_id)
    if not partie:
        return jsonify({"status": "erreur"})

    modele = Puissance4Modele()
    modele.charger_depuis_bd(partie)

    return jsonify({
        "status":         "ok",
        "plateau":        modele.plateau,
        "joueur_courant": modele.joueur_courant,
        "couleur_depart": modele.couleur_depart,
        "historique":     [list(h) for h in modele.historique],
        "resultat":       modele.resultat,
        "lignes":         modele.lignes,
        "colonnes":       modele.colonnes,
    })

# =========================================================
# LANCEMENT
# =========================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)