from flask import Flask, render_template, jsonify, request, session
from modele import Puissance4Modele
from db import inserer_partie, lister_parties_jeu, get_partie
import os
import random
import init_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "puissance4_secret_key_2024")

# =========================================================
# GESTION DES SESSIONS — 1 état par visiteur
# =========================================================

sessions = {}

def get_state():
    sid = session.get("sid")
    if sid is None or sid not in sessions:
        sid = os.urandom(16).hex()
        session["sid"] = sid
        sessions[sid] = creer_etat()
    return sessions[sid]

def creer_etat():
    return {
        "modele":             Puissance4Modele(),
        "mode":               2,          # 2=HvH, 1=HvIA, 0=IAvIA, 3=Situation
        "ia_rouge":           "minimax",
        "ia_jaune":           "minimax",
        "profondeur_rouge":   4,
        "profondeur_jaune":   4,
        "partie_sauvegardee": False,
        "pion_editeur":       1,          # 1=ROUGE, 2=JAUNE (mode situation)
    }

# =========================================================
# PAGE PRINCIPALE
# =========================================================

@app.route("/")
def accueil():
    state = get_state()
    return render_template("index.html", mode=state["mode"])

# =========================================================
# DONNÉES DU PLATEAU
# =========================================================

@app.route("/api/plateau")
def get_plateau():
    state  = get_state()
    modele = state["modele"]
    return jsonify({
        "plateau":          modele.plateau,
        "joueur":           modele.joueur_courant,
        "resultat":         modele.resultat,
        "mode":             state["mode"],
        "profondeur_rouge": state["profondeur_rouge"],
        "profondeur_jaune": state["profondeur_jaune"],
        "ia_rouge":         state["ia_rouge"],
        "ia_jaune":         state["ia_jaune"],
        "couleur_depart":   modele.couleur_depart,
        "pion_editeur":     state["pion_editeur"],
    })

# =========================================================
# CHANGER MODE
# =========================================================

@app.route("/api/mode", methods=["POST"])
def changer_mode():
    state = get_state()
    data  = request.get_json()
    state["mode"] = int(data["mode"])
    return jsonify({"status": "ok", "mode": state["mode"]})

# =========================================================
# CHANGER PROFONDEUR
# =========================================================

@app.route("/api/profondeur", methods=["POST"])
def changer_profondeur():
    state  = get_state()
    data   = request.get_json()
    joueur = data.get("joueur", "rouge")
    prof   = int(data.get("profondeur", 4))
    if joueur == "rouge":
        state["profondeur_rouge"] = prof
    else:
        state["profondeur_jaune"] = prof
    return jsonify({"status": "ok"})

# =========================================================
# CHANGER TYPE IA
# =========================================================

@app.route("/api/ia_type", methods=["POST"])
def changer_ia():
    state = get_state()
    data  = request.get_json()
    state["ia_rouge"] = data["rouge"]
    state["ia_jaune"] = data["jaune"]
    return jsonify({"status": "ok"})

# =========================================================
# CHANGER JOUEUR QUI COMMENCE
# =========================================================

@app.route("/api/couleur_depart", methods=["POST"])
def couleur_depart():
    state   = get_state()
    modele  = state["modele"]
    data    = request.get_json()
    couleur = int(data.get("couleur", 1))
    modele.couleur_depart = couleur
    modele.nouvelle_partie()
    state["partie_sauvegardee"] = False
    return jsonify({
        "status":  "ok",
        "plateau": modele.plateau,
        "joueur":  modele.joueur_courant,
    })

# =========================================================
# SAUVEGARDE
# =========================================================

def enregistrer_si_finie(state):
    modele = state["modele"]
    if modele.resultat is None or state["partie_sauvegardee"]:
        return
    coups     = modele.exporter_coups_string()
    confiance = 1 if state["mode"] == 2 else 2
    ok, msg, gid = inserer_partie(
        lignes=modele.lignes,
        colonnes=modele.colonnes,
        couleur_depart=modele.couleur_depart,
        joueur_courant=modele.joueur_courant,
        statut="finished",
        resultat=modele.resultat,
        coups=coups,
        confiance=confiance
    )
    print(f"[DB] Sauvegardé : {ok} {msg} id={gid}")
    state["partie_sauvegardee"] = True

# =========================================================
# FIN DE PARTIE
# =========================================================

def verifier_fin(state):
    modele = state["modele"]
    coords = modele.verifier_victoire(modele.joueur_courant)
    if coords is not None:
        gagnant = "rouge" if modele.joueur_courant == modele.ROUGE else "jaune"
        modele.definir_resultat(gagnant)
        enregistrer_si_finie(state)
        return True
    if modele.plateau_plein():
        modele.definir_resultat("nul")
        enregistrer_si_finie(state)
        return True
    return False

# =========================================================
# COUP IA
# =========================================================

def jouer_ia(state):
    modele = state["modele"]
    if modele.resultat is not None:
        return None

    joueur = modele.joueur_courant
    if joueur == modele.ROUGE:
        ia_type    = state["ia_rouge"]
        profondeur = state["profondeur_rouge"]
    else:
        ia_type    = state["ia_jaune"]
        profondeur = state["profondeur_jaune"]

    if ia_type == "aleatoire":
        col = modele.coup_aleatoire()
    else:
        scores = modele.calculer_scores_minimax(profondeur)
        if not scores:
            modele.definir_resultat("nul")
            enregistrer_si_finie(state)
            return None
        best_score = max(scores.values())
        best_cols  = [c for c, s in scores.items() if s == best_score]
        centre     = modele.colonnes // 2
        col        = min(best_cols, key=lambda c: abs(c - centre))

    modele.jouer_coup(col)
    print(f"[IA] Joueur {'ROUGE' if joueur==1 else 'JAUNE'} → colonne {col}")

    if not verifier_fin(state):
        modele.changer_joueur()

    return col

# =========================================================
# JOUER COUP HUMAIN (mode normal)
# =========================================================

@app.route("/api/jouer", methods=["POST"])
def jouer():
    state  = get_state()
    modele = state["modele"]

    if modele.resultat is not None:
        return jsonify({"status": "fin"})

    data = request.get_json()
    col  = int(data["col"])

    lig = modele.jouer_coup(col)
    if lig is None:
        return jsonify({"status": "col_invalide"})

    if not verifier_fin(state):
        modele.changer_joueur()

    return jsonify({
        "status":   "ok",
        "plateau":  modele.plateau,
        "joueur":   modele.joueur_courant,
        "resultat": modele.resultat,
    })

# =========================================================
# COUP IA
# =========================================================

@app.route("/api/ia_step", methods=["POST"])
def ia_step():
    state  = get_state()
    modele = state["modele"]

    if state["mode"] not in (0, 1):
        return jsonify({"status": "erreur_mode"})

    if modele.resultat is not None:
        return jsonify({"status": "fin"})

    col = jouer_ia(state)

    return jsonify({
        "status":   "ok",
        "col":      col,
        "plateau":  modele.plateau,
        "joueur":   modele.joueur_courant,
        "resultat": modele.resultat,
    })

# =========================================================
# MODE SITUATION — PLACER UN PION LIBREMENT
# =========================================================

@app.route("/api/situation/placer", methods=["POST"])
def situation_placer():
    """Place ou efface un pion librement sur n'importe quelle case."""
    state  = get_state()
    modele = state["modele"]
    data   = request.get_json()

    lig    = int(data["lig"])
    col    = int(data["col"])
    couleur = int(data.get("couleur", state["pion_editeur"]))  # 0=effacer, 1=rouge, 2=jaune

    if 0 <= lig < modele.lignes and 0 <= col < modele.colonnes:
        modele.plateau[lig][col] = couleur

    # Vérifie si une victoire existe déjà sur le plateau édité
    victoire_rouge = modele._verifier_victoire_sur_plateau(modele.plateau, modele.ROUGE)
    victoire_jaune = modele._verifier_victoire_sur_plateau(modele.plateau, modele.JAUNE)

    return jsonify({
        "status":         "ok",
        "plateau":        modele.plateau,
        "victoire_rouge": victoire_rouge,
        "victoire_jaune": victoire_jaune,
    })

# =========================================================
# MODE SITUATION — CHANGER LE PION ACTIF DE L'ÉDITEUR
# =========================================================

@app.route("/api/situation/pion", methods=["POST"])
def situation_pion():
    state = get_state()
    data  = request.get_json()
    state["pion_editeur"] = int(data.get("pion", 1))
    return jsonify({"status": "ok", "pion_editeur": state["pion_editeur"]})

# =========================================================
# MODE SITUATION — EFFACER TOUT LE PLATEAU
# =========================================================

@app.route("/api/situation/effacer", methods=["POST"])
def situation_effacer():
    state  = get_state()
    modele = state["modele"]
    modele.plateau  = modele.creer_plateau()
    modele.historique = []
    modele.resultat   = None
    return jsonify({"status": "ok", "plateau": modele.plateau})

# =========================================================
# MODE SITUATION — ANALYSER LA POSITION
# Répond : qui gagne, en combien de coups
# =========================================================

@app.route("/api/situation/analyser", methods=["POST"])
def situation_analyser():
    state  = get_state()
    modele = state["modele"]
    data   = request.get_json() or {}

    joueur_analyse = int(data.get("joueur", modele.ROUGE))
    modele.joueur_courant = joueur_analyse

    # Vérifie victoire déjà présente
    if modele._verifier_victoire_sur_plateau(modele.plateau, modele.ROUGE):
        return jsonify({
            "gagnant": "rouge",
            "coups":   0,
            "message": "🔴 Rouge a déjà gagné sur ce plateau !"
        })

    if modele._verifier_victoire_sur_plateau(modele.plateau, modele.JAUNE):
        return jsonify({
            "gagnant": "jaune",
            "coups":   0,
            "message": "🟡 Jaune a déjà gagné sur ce plateau !"
        })

    if modele.plateau_plein():
        return jsonify({
            "gagnant": "nul",
            "coups":   0,
            "message": "🤝 Plateau plein — match nul !"
        })

    # ✅ Profondeur minimum 6 pour l'analyse de situation
    profondeur = state["profondeur_rouge"] if joueur_analyse == modele.ROUGE else state["profondeur_jaune"]
    profondeur = max(profondeur, 7)

    scores = modele.calculer_scores_minimax(profondeur)

    if not scores:
        return jsonify({
            "gagnant": "inconnu",
            "coups":   -1,
            "message": "❓ Impossible d'analyser cette position."
        })

    best_score = max(scores.values())
    best_cols = [c for c, s in scores.items() if s == best_score]
    meilleur_col = min(best_cols)  # prend la colonne la plus à gauche

    nom_joueur = "Rouge" if joueur_analyse == modele.ROUGE else "Jaune"
    emoji      = "🔴"    if joueur_analyse == modele.ROUGE else "🟡"

    if best_score >= 99000000:
        # ✅ Calcul correct du nombre de coups
        coups_restants = 100000000 - best_score
        # coups_restants = 0 → victoire immédiate = 1 coup
        # coups_restants = 1 → gagne en 2 coups etc.
        nb_coups = coups_restants + 1
        message = f"{emoji} {nom_joueur} gagne en {nb_coups} coup(s) ! Jouer colonne {meilleur_col + 1}."
        gagnant = "rouge" if joueur_analyse == modele.ROUGE else "jaune"

    elif best_score <= -99000000:
        adv       = "Jaune" if joueur_analyse == modele.ROUGE else "Rouge"
        emoji_adv = "🟡"    if joueur_analyse == modele.ROUGE else "🔴"
        coups_restants = best_score + 100000000
        nb_coups  = abs(coups_restants) + 1
        message = f"{emoji_adv} {adv} gagne en {nb_coups} coup(s). Position perdue pour {nom_joueur}."
        gagnant = "jaune" if joueur_analyse == modele.ROUGE else "rouge"

    else:
        message = f"⚖️ Position équilibrée. Meilleur coup pour {nom_joueur} : colonne {meilleur_col + 1}. (score={best_score})"
        gagnant = "equilibre"

    return jsonify({
        "gagnant":      gagnant,
        "meilleur_col": meilleur_col,
        "score":        best_score,
        "message":      message,
        "scores":       scores,
    })

# =========================================================
# NOUVELLE PARTIE
# =========================================================

@app.route("/api/nouvelle", methods=["GET", "POST"])
def nouvelle():
    state  = get_state()
    modele = state["modele"]
    data   = request.get_json(silent=True) or {}

    if "couleur_depart" in data:
        modele.couleur_depart = int(data["couleur_depart"])

    modele.nouvelle_partie()
    state["partie_sauvegardee"] = False

    return jsonify({
        "status":  "reset",
        "plateau": modele.plateau,
        "joueur":  modele.joueur_courant,
    })

# =========================================================
# ANNULER COUP
# =========================================================

@app.route("/api/annuler")
def annuler():
    state  = get_state()
    modele = state["modele"]
    modele.annuler_dernier_coup()
    state["partie_sauvegardee"] = False
    return jsonify({
        "status":  "ok",
        "plateau": modele.plateau,
        "joueur":  modele.joueur_courant,
    })

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
    state  = get_state()
    partie = get_partie(partie_id)
    if not partie:
        return jsonify({"status": "erreur"})
    state["modele"].charger_depuis_bd(partie)
    state["partie_sauvegardee"] = True
    return jsonify({"status": "ok"})

# =========================================================
# LANCEMENT
# =========================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)