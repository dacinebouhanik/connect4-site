from flask import Flask, render_template, jsonify, request
from modele import Puissance4Modele
from db import inserer_partie, lister_parties_jeu, get_partie
import os
import init_db
app = Flask(__name__)

modele = Puissance4Modele()

# 2 = humain vs humain
# 1 = humain vs IA
# 0 = IA vs IA
mode = 2

# profondeur minimax
PROFONDEUR_IA = 2

# évite double sauvegarde
partie_sauvegardee = False


# =========================================================
# PAGE PRINCIPALE
# =========================================================

@app.route("/")
def accueil():
    return render_template("index.html", mode=mode)


# =========================================================
# DONNEES DU PLATEAU
# =========================================================

@app.route("/api/plateau")
def get_plateau():
    scores = None

    if mode in (0, 1) and modele.resultat is None:
        scores = modele.calculer_scores_minimax(PROFONDEUR_IA)

    return jsonify({
        "plateau": modele.plateau,
        "joueur": modele.joueur_courant,
        "resultat": modele.resultat,
        "mode": mode,
        "scores": scores
    })


# =========================================================
# CHANGER PROFONDEUR IA
# =========================================================

@app.route("/api/profondeur", methods=["POST"])
def changer_profondeur():
    global PROFONDEUR_IA
    data = request.get_json()
    PROFONDEUR_IA = int(data["profondeur"])
    print("Nouvelle profondeur IA:", PROFONDEUR_IA)
    return jsonify({"status": "ok"})


# =========================================================
# SAUVEGARDE PARTIE
# =========================================================

def enregistrer_si_finie():

    global partie_sauvegardee

    print("DEBUG : appel enregistrer_si_finie")

    if modele.resultat is None:
        print("DEBUG : resultat None")
        return

    if partie_sauvegardee:
        print("DEBUG : deja sauvegardee")
        return

    coups = modele.exporter_coups_string()

    print("DEBUG coups :", coups)

    confiance = 1 if mode == 2 else 2

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

    print("RESULTAT INSERT :", ok, msg, gid)

    partie_sauvegardee = True
# =========================================================
# VERIFICATION FIN DE PARTIE
# =========================================================

def verifier_fin():
    coords = modele.verifier_victoire(modele.joueur_courant)

    if coords is not None:
        gagnant = "rouge" if modele.joueur_courant == modele.ROUGE else "jaune"
        modele.definir_resultat(gagnant)
        print("VICTOIRE :", gagnant)
        enregistrer_si_finie()
        return True

    if modele.plateau_plein():
        modele.definir_resultat("nul")
        print("MATCH NUL")
        enregistrer_si_finie()
        return True

    return False


# =========================================================
# IA
# =========================================================

def jouer_ia():

    if modele.resultat is not None:
        return

    scores = modele.calculer_scores_minimax(PROFONDEUR_IA)

    if not scores:
        modele.definir_resultat("nul")
        enregistrer_si_finie()
        return

    col = max(scores, key=scores.get)

    modele.jouer_coup(col)

    if not verifier_fin():
        modele.changer_joueur()


# =========================================================
# JOUER COUP HUMAIN
# =========================================================

@app.route("/api/jouer", methods=["POST"])
def jouer():

    data = request.get_json()
    col = int(data["col"])

    if modele.resultat is not None:
        return jsonify({"status": "fin"})

    lig = modele.jouer_coup(col)

    if lig is None:
        return jsonify({"status": "col_invalide"})

    if not verifier_fin():
        modele.changer_joueur()

    if mode == 1 and modele.resultat is None:
        jouer_ia()

    return jsonify({"status": "ok"})


# =========================================================
# IA vs IA
# =========================================================

@app.route("/api/ia_step", methods=["POST"])
def ia_step():

    if mode != 0:
        return jsonify({"status": "erreur_mode"})

    if modele.resultat is not None:
        return jsonify({"status": "fin"})

    jouer_ia()
    return jsonify({"status": "ok"})


# =========================================================
# NOUVELLE PARTIE
# =========================================================

@app.route("/api/nouvelle")
def nouvelle():

    global partie_sauvegardee

    modele.nouvelle_partie()
    partie_sauvegardee = False

    return jsonify({"status": "reset"})


# =========================================================
# ANNULER COUP
# =========================================================

@app.route("/api/annuler")
def annuler():

    global partie_sauvegardee

    modele.annuler_dernier_coup()
    partie_sauvegardee = False

    return jsonify({"status": "ok"})


# =========================================================
# CHANGER MODE
# =========================================================

@app.route("/api/mode", methods=["POST"])
def changer_mode():

    global mode, partie_sauvegardee

    data = request.get_json()
    mode = int(data["mode"])

    modele.nouvelle_partie()
    partie_sauvegardee = False

    return jsonify({"status": "ok"})


# =========================================================
# HISTORIQUE
# =========================================================

@app.route("/api/historique")
def historique():

    parties = lister_parties_jeu()

    data = []
    for p in parties:
        data.append({
            "id": p[0],
            "date": str(p[1]),
            "statut": p[2],
            "resultat": p[3],
            "confiance": p[4],
            "coups": p[5]
        })

    return jsonify(data)


# =========================================================
# CHARGER PARTIE
# =========================================================

@app.route("/api/charger/<int:partie_id>")
def charger_partie(partie_id):

    global partie_sauvegardee

    partie = get_partie(partie_id)

    if not partie:
        return jsonify({"status": "erreur"})

    modele.charger_depuis_bd(partie)

    partie_sauvegardee = True

    return jsonify({"status": "ok"})


# =========================================================
# LANCEMENT (RENDER)
# =========================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)