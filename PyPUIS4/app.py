from flask import Flask, render_template, jsonify, request, session
from modele import Puissance4Modele
from db import inserer_partie, lister_parties_jeu, get_partie
import os
import init_db
import sys
sys.setrecursionlimit(10000)

init_db.init_db()
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "puissance4_secret_key_2024")

def etat_defaut():
    return {
        "mode":               2,
        "ia_rouge":           "minimax",
        "ia_jaune":           "minimax",
        "profondeur_rouge":   4,
        "profondeur_jaune":   4,
        "partie_sauvegardee": False,
        "pion_editeur":       1,
        "plateau":            None,
        "joueur_courant":     1,
        "couleur_depart":     1,
        "historique":         [],
        "resultat":           None,
        "lignes":             9,
        "colonnes":           9,
    }

def get_tab_id():
    return request.headers.get("X-Tab-Id", "default")

def get_state():
    tab_id = get_tab_id()
    if "tabs" not in session:
        session["tabs"] = {}
    if tab_id not in session["tabs"]:
        session["tabs"][tab_id] = etat_defaut()
        session.modified = True
    return session["tabs"][tab_id]

def sauver_state(state):
    tab_id = get_tab_id()
    if "tabs" not in session:
        session["tabs"] = {}
    session["tabs"][tab_id] = state
    session.modified = True

def modele_depuis_state(state):
    m = Puissance4Modele()
    m.lignes          = state["lignes"]
    m.colonnes        = state["colonnes"]
    m.couleur_depart  = state["couleur_depart"]
    m.joueur_courant  = state["joueur_courant"]
    m.resultat        = state["resultat"]
    m.historique      = [tuple(h) for h in state["historique"]]
    if state["plateau"] is not None:
        m.plateau = state["plateau"]
    else:
        m.plateau = m.creer_plateau()
    return m

def state_depuis_modele(state, modele):
    state["plateau"]         = modele.plateau
    state["joueur_courant"]  = modele.joueur_courant
    state["couleur_depart"]  = modele.couleur_depart
    state["resultat"]        = modele.resultat
    state["historique"]      = [list(h) for h in modele.historique]
    state["lignes"]          = modele.lignes
    state["colonnes"]        = modele.colonnes
    return state

@app.route("/")
def accueil():
    return render_template("index.html")

@app.route("/api/plateau")
def get_plateau():
    state  = get_state()
    modele = modele_depuis_state(state)
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

@app.route("/api/mode", methods=["POST"])
def changer_mode():
    state = get_state()
    data  = request.get_json()
    ancien_mode  = state["mode"]
    nouveau_mode = int(data["mode"])
    state["mode"] = nouveau_mode
    if ancien_mode == 3 and nouveau_mode != 3:
        joueur = int(data.get("joueur_courant", state.get("joueur_courant", 1)))
        state["joueur_courant"] = joueur
        state["resultat"] = None
        state["historique"] = []
        state["partie_sauvegardee"] = False
    sauver_state(state)
    return jsonify({"status": "ok", "mode": state["mode"]})

@app.route("/api/profondeur", methods=["POST"])
def changer_profondeur():
    state  = get_state()
    data   = request.get_json()
    joueur = data.get("joueur", "rouge")
    prof   = int(data.get("profondeur", 7))
    if joueur == "rouge":
        state["profondeur_rouge"] = prof
    else:
        state["profondeur_jaune"] = prof
    sauver_state(state)
    return jsonify({"status": "ok"})

@app.route("/api/ia_type", methods=["POST"])
def changer_ia():
    state = get_state()
    data  = request.get_json()
    state["ia_rouge"] = data["rouge"]
    state["ia_jaune"] = data["jaune"]
    sauver_state(state)
    return jsonify({"status": "ok"})

@app.route("/api/couleur_depart", methods=["POST"])
def couleur_depart():
    state  = get_state()
    data   = request.get_json()
    couleur = int(data.get("couleur", 1))
    modele = modele_depuis_state(state)
    modele.couleur_depart = couleur
    modele.nouvelle_partie()
    state = state_depuis_modele(state, modele)
    state["partie_sauvegardee"] = False
    sauver_state(state)
    return jsonify({"status": "ok", "plateau": modele.plateau, "joueur": modele.joueur_courant})

def enregistrer_si_finie(state, modele):
    if modele.resultat is None or state["partie_sauvegardee"]:
        return
    try:
        coups     = modele.exporter_coups_string()
        confiance = 1 if state["mode"] == 2 else 2
        ok, msg, gid = inserer_partie(
            lignes=modele.lignes, colonnes=modele.colonnes,
            couleur_depart=modele.couleur_depart, joueur_courant=modele.joueur_courant,
            statut="finished", resultat=modele.resultat, coups=coups, confiance=confiance
        )
        print(f"[DB] Sauvegardé : {ok} {msg} id={gid}")
        state["partie_sauvegardee"] = True
    except Exception as e:
        print(f"[DB] Erreur sauvegarde (ignorée) : {e}")
        state["partie_sauvegardee"] = True

def verifier_fin(state, modele):
    coords = modele.verifier_victoire(modele.joueur_courant)
    if coords is not None:
        gagnant = "rouge" if modele.joueur_courant == modele.ROUGE else "jaune"
        modele.definir_resultat(gagnant)
        enregistrer_si_finie(state, modele)
        return True
    if modele.plateau_plein():
        modele.definir_resultat("nul")
        enregistrer_si_finie(state, modele)
        return True
    return False

def jouer_ia(state, modele):
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
            enregistrer_si_finie(state, modele)
            return None
        best_score = max(scores.values())
        best_cols  = [c for c, s in scores.items() if s == best_score]
        centre     = modele.colonnes // 2
        col        = min(best_cols, key=lambda c: abs(c - centre))
    modele.jouer_coup(col)
    if not verifier_fin(state, modele):
        modele.changer_joueur()
    return col

@app.route("/api/jouer", methods=["POST"])
def jouer():
    state  = get_state()
    modele = modele_depuis_state(state)
    if modele.resultat is not None:
        return jsonify({"status": "fin"})
    data = request.get_json()
    col  = int(data["col"])
    lig = modele.jouer_coup(col)
    if lig is None:
        return jsonify({"status": "col_invalide"})
    if not verifier_fin(state, modele):
        modele.changer_joueur()
    state = state_depuis_modele(state, modele)
    sauver_state(state)
    return jsonify({"status": "ok", "plateau": modele.plateau, "joueur": modele.joueur_courant, "resultat": modele.resultat})

@app.route("/api/ia_step", methods=["POST"])
def ia_step():
    state  = get_state()
    modele = modele_depuis_state(state)
    if state["mode"] not in (0, 1):
        return jsonify({"status": "erreur_mode"})
    if modele.resultat is not None:
        return jsonify({"status": "fin"})
    col = jouer_ia(state, modele)
    state = state_depuis_modele(state, modele)
    sauver_state(state)
    return jsonify({"status": "ok", "col": col, "plateau": modele.plateau, "joueur": modele.joueur_courant, "resultat": modele.resultat})

@app.route("/api/situation/placer", methods=["POST"])
def situation_placer():
    state  = get_state()
    modele = modele_depuis_state(state)
    data   = request.get_json()
    lig    = int(data["lig"])
    col    = int(data["col"])
    couleur = int(data.get("couleur", state["pion_editeur"]))
    if 0 <= lig < modele.lignes and 0 <= col < modele.colonnes:
        modele.plateau[lig][col] = couleur
    victoire_rouge = modele._verifier_victoire_sur_plateau(modele.plateau, modele.ROUGE)
    victoire_jaune = modele._verifier_victoire_sur_plateau(modele.plateau, modele.JAUNE)
    state = state_depuis_modele(state, modele)
    sauver_state(state)
    return jsonify({"status": "ok", "plateau": modele.plateau, "victoire_rouge": victoire_rouge, "victoire_jaune": victoire_jaune})

@app.route("/api/situation/pion", methods=["POST"])
def situation_pion():
    state = get_state()
    data  = request.get_json()
    state["pion_editeur"] = int(data.get("pion", 1))
    sauver_state(state)
    return jsonify({"status": "ok", "pion_editeur": state["pion_editeur"]})

@app.route("/api/situation/effacer", methods=["POST"])
def situation_effacer():
    state  = get_state()
    modele = modele_depuis_state(state)
    modele.plateau    = modele.creer_plateau()
    modele.historique = []
    modele.resultat   = None
    state = state_depuis_modele(state, modele)
    sauver_state(state)
    return jsonify({"status": "ok", "plateau": modele.plateau})

@app.route("/api/situation/analyser", methods=["POST"])
def situation_analyser():
    state  = get_state()
    modele = modele_depuis_state(state)
    data   = request.get_json() or {}
    joueur_analyse = int(data.get("joueur", modele.ROUGE))
    modele.joueur_courant = joueur_analyse
    if modele._verifier_victoire_sur_plateau(modele.plateau, modele.ROUGE):
        return jsonify({"gagnant": "rouge", "coups": 0, "message": "🔴 Rouge a déjà gagné sur ce plateau !"})
    if modele._verifier_victoire_sur_plateau(modele.plateau, modele.JAUNE):
        return jsonify({"gagnant": "jaune", "coups": 0, "message": "🟡 Jaune a déjà gagné sur ce plateau !"})
    if modele.plateau_plein():
        return jsonify({"gagnant": "nul", "coups": 0, "message": "🤝 Plateau plein — match nul !"})
    profondeur = state["profondeur_rouge"] if joueur_analyse == modele.ROUGE else state["profondeur_jaune"]
    profondeur = max(profondeur, 7)
    scores = modele.calculer_scores_minimax(profondeur)
    if not scores:
        return jsonify({"gagnant": "inconnu", "coups": -1, "message": "❓ Impossible d'analyser cette position."})
    best_score  = max(scores.values())
    best_cols   = [c for c, s in scores.items() if s == best_score]
    meilleur_col = min(best_cols)
    nom_joueur = "Rouge" if joueur_analyse == modele.ROUGE else "Jaune"
    emoji      = "🔴"    if joueur_analyse == modele.ROUGE else "🟡"
    if best_score >= 99000000:
        nb_coups = (100000000 - best_score) + 1
        message  = f"{emoji} {nom_joueur} gagne en {nb_coups} coup(s) ! Jouer colonne {meilleur_col + 1}."
        gagnant  = "rouge" if joueur_analyse == modele.ROUGE else "jaune"
    elif best_score <= -99000000:
        adv       = "Jaune" if joueur_analyse == modele.ROUGE else "Rouge"
        emoji_adv = "🟡"    if joueur_analyse == modele.ROUGE else "🔴"
        nb_coups  = abs(best_score + 100000000) + 1
        message   = f"{emoji_adv} {adv} gagne en {nb_coups} coup(s). Position perdue pour {nom_joueur}."
        gagnant   = "jaune" if joueur_analyse == modele.ROUGE else "rouge"
    else:
        message = f"⚖️ Position équilibrée. Meilleur coup pour {nom_joueur} : colonne {meilleur_col + 1}. (score={best_score})"
        gagnant = "equilibre"
    return jsonify({"gagnant": gagnant, "meilleur_col": meilleur_col, "score": best_score, "message": message, "scores": scores})

@app.route("/api/conseil")
def conseil():
    state  = get_state()
    modele = modele_depuis_state(state)
    if modele.resultat is not None:
        return jsonify({"status": "fin"})
    joueur = modele.joueur_courant
    profondeur = state["profondeur_rouge"] if joueur == modele.ROUGE else state["profondeur_jaune"]
    profondeur = min(profondeur, 4)
    scores = modele.calculer_scores_minimax(profondeur)
    if not scores:
        return jsonify({"status": "erreur"})
    best_score  = max(scores.values())
    best_cols   = [c for c, s in scores.items() if s == best_score]
    centre      = modele.colonnes // 2
    meilleur_col = min(best_cols, key=lambda c: abs(c - centre))
    if best_score >= 99000000:
        verdict = "victoire"
    elif best_score <= -99000000:
        verdict = "defaite"
    elif best_score > 1000:
        verdict = "avantage"
    elif best_score < -1000:
        verdict = "desavantage"
    else:
        verdict = "equilibre"
    return jsonify({"status": "ok", "meilleur_col": meilleur_col, "score": best_score, "verdict": verdict, "scores": scores, "joueur": joueur})

@app.route("/api/nouvelle", methods=["GET", "POST"])
def nouvelle():
    state  = get_state()
    modele = modele_depuis_state(state)
    data   = request.get_json(silent=True) or {}
    if "couleur_depart" in data:
        modele.couleur_depart = int(data["couleur_depart"])
    modele.nouvelle_partie()
    state = state_depuis_modele(state, modele)
    state["partie_sauvegardee"] = False
    sauver_state(state)
    return jsonify({"status": "reset", "plateau": modele.plateau, "joueur": modele.joueur_courant})

@app.route("/api/annuler")
def annuler():
    state  = get_state()
    modele = modele_depuis_state(state)
    modele.annuler_dernier_coup()
    state = state_depuis_modele(state, modele)
    state["partie_sauvegardee"] = False
    sauver_state(state)
    return jsonify({"status": "ok", "plateau": modele.plateau, "joueur": modele.joueur_courant})

@app.route("/api/historique")
def historique():
    parties = lister_parties_jeu()
    data = []
    for p in parties:
        data.append({"id": p[0], "date": str(p[1]), "statut": p[2], "resultat": p[3], "confiance": p[4], "coups": p[5]})
    return jsonify(data)

@app.route("/api/charger/<int:partie_id>")
def charger_partie(partie_id):
    state  = get_state()
    partie = get_partie(partie_id)
    if not partie:
        return jsonify({"status": "erreur"})
    modele = Puissance4Modele()
    modele.charger_depuis_bd(partie)
    state = state_depuis_modele(state, modele)
    state["partie_sauvegardee"] = True
    sauver_state(state)
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)