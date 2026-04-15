/* ================================================
   ÉTAT GLOBAL — tout est ici, zéro serveur
================================================ */

const ETAT = {
    plateau:        null,
    joueur_courant: 1,
    joueur_humain: 1,
    couleur_depart: 1,
    historique:     [],
    resultat:       null,
    lignes:         9,
    colonnes:       9,

    mode:           2,   // 0=IAvIA, 1=HvIA, 2=HvH, 3=Situation
    ia_rouge:       "minimax",
    ia_jaune:       "minimax",
    profondeur_rouge: 4,
    profondeur_jaune: 4,
    pion_editeur:   1,

    partie_sauvegardee: false,
    timer_ia:       null,
    delai_ia:       600,
    en_train:       false,

    // Replay
    replay_actif:   false,
    replay_coups:   [],
    replay_index:   0,
};

// Seuil pour détecter victoire/défaite (doit matcher modele.py)
const SEUIL_VICTOIRE = 500000;

/* ================================================
   INITIALISATION
================================================ */

document.addEventListener("DOMContentLoaded", async () => {
    await nouvellePartie();
});

/* ================================================
   NOUVELLE PARTIE
================================================ */

async function nouvellePartie() {
    stopperTimerIA();
    ETAT.en_train = false;
    ETAT.replay_actif = false;

    const ctrl = document.getElementById("replayControls");
    if (ctrl) ctrl.remove();

    const res  = await fetch("/api/nouvelle", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({
            lignes:         ETAT.lignes,
            colonnes:       ETAT.colonnes,
            couleur_depart: ETAT.couleur_depart,
        })
    });
    const data = await res.json();

    ETAT.plateau        = data.plateau;
    ETAT.joueur_courant = data.joueur_courant;
    ETAT.historique     = data.historique;
    ETAT.resultat       = null;
    ETAT.partie_sauvegardee = false;

    cacherConseil();
    mettreAJourUI();
}

/* ================================================
   METTRE À JOUR L'UI
================================================ */

function mettreAJourUI() {
    // Mode select
    const modeSelect = document.getElementById("modeSelect");
    if (modeSelect) modeSelect.value = ETAT.mode === 3 ? "" : String(ETAT.mode);

    // Bouton situation
    const btnSituation = document.getElementById("btnSituation");
    if (btnSituation) btnSituation.classList.toggle("actif", ETAT.mode === 3);

    // Panneaux
    const zoneIA = document.getElementById("zoneIA");
    if (zoneIA) zoneIA.style.display = (ETAT.mode === 0 || ETAT.mode === 1) ? "block" : "none";

    const zoneSituation = document.getElementById("zoneSituation");
    if (zoneSituation) zoneSituation.style.display = ETAT.mode === 3 ? "block" : "none";

    // Profondeurs
    const profRouge = document.getElementById("profondeurRouge");
    const profJaune = document.getElementById("profondeurJaune");
    if (profRouge) profRouge.value = String(ETAT.profondeur_rouge);
    if (profJaune) profJaune.value = String(ETAT.profondeur_jaune);

    // Départ
    const departSelect = document.getElementById("departSelect");
    if (departSelect) departSelect.value = String(ETAT.couleur_depart);

    // Pion éditeur
    mettreAJourBoutonsPion(ETAT.pion_editeur);

    // Plateau
    if (ETAT.mode === 3) {
        afficherPlateauEditeur(ETAT.plateau);
    } else {
        afficherPlateau(ETAT.plateau);
    }

    // Info
    const info = document.getElementById("info");
    if (info) {
        if (ETAT.resultat) {
            const emoji = ETAT.resultat === "rouge" ? "🔴" : ETAT.resultat === "jaune" ? "🟡" : "🤝";
            const texte = ETAT.resultat === "nul" ? "Match nul !" : `${emoji} ${ETAT.resultat.toUpperCase()} gagne !`;
            info.innerHTML = "🏆 " + texte;
            info.className = "info fin";
        } else if (ETAT.mode === 3) {
            info.innerHTML = "🧠 Mode Situation — placez vos pions librement";
            info.className = "info";
        } else {
            const emoji = ETAT.joueur_courant === 1 ? "🔴" : "🟡";
            const nom   = ETAT.joueur_courant === 1 ? "Rouge" : "Jaune";
            info.innerHTML = `${emoji} Tour de ${nom}`;
            info.className = "info";
        }
    }

    // Bouton prédiction (CORRIGÉ — ligne dupliquée supprimée)
    const btnPred = document.getElementById("btnPrediction");
    if (btnPred) {
        btnPred.style.display = (ETAT.mode === 1 && !ETAT.resultat && ETAT.joueur_courant === ETAT.joueur_humain) ? "inline-block" : "none";
    }

    // Timer IA vs IA
    if (ETAT.mode === 0 && !ETAT.resultat) {
        demarrerTimerIA();
    } else {
        stopperTimerIA();
        ETAT.en_train = false;
    }

    // Sauvegarder si partie finie
    if (ETAT.resultat && !ETAT.partie_sauvegardee) {
        sauvegarderPartie();
    }
}

/* ================================================
   AFFICHER PLATEAU NORMAL
================================================ */

function afficherPlateau(plateau) {
    if (!plateau) return;
    const plateauDiv = document.getElementById("plateau");
    plateauDiv.innerHTML = "";

    const nbCol = plateau[0].length;
    plateauDiv.style.gridTemplateColumns = `repeat(${nbCol}, 50px)`;

    const cliquable = ETAT.mode !== 0 && !ETAT.resultat && ETAT.mode !== 3;

    plateau.forEach((ligne, rowIndex) => {
        ligne.forEach((cell, colIndex) => {
            const div = document.createElement("div");
            div.className = "case";
            if (cell === 1) div.classList.add("rouge");
            if (cell === 2) div.classList.add("jaune");

            if (cliquable) {
                div.onclick = () => jouer(colIndex);
                div.style.cursor = "pointer";
            }
            plateauDiv.appendChild(div);
        });
    });
}

/* ================================================
   AFFICHER PLATEAU ÉDITEUR
================================================ */

function afficherPlateauEditeur(plateau) {
    if (!plateau) return;
    const plateauDiv = document.getElementById("plateau");
    plateauDiv.innerHTML = "";

    const nbCol = plateau[0].length;
    plateauDiv.style.gridTemplateColumns = `repeat(${nbCol}, 50px)`;

    plateau.forEach((ligne, rowIndex) => {
        ligne.forEach((cell, colIndex) => {
            const div = document.createElement("div");
            div.className = "case editeur";
            if (cell === 1) div.classList.add("rouge");
            if (cell === 2) div.classList.add("jaune");
            div.style.cursor = "pointer";
            div.onclick = () => situationPlacer(rowIndex, colIndex);
            plateauDiv.appendChild(div);
        });
    });
}

/* ================================================
   JOUER COUP HUMAIN
================================================ */

async function jouer(col) {
    if (ETAT.en_train || ETAT.resultat || ETAT.mode === 0 || ETAT.mode === 3) return;

    ETAT.en_train = true;
    desactiverPlateau();
    cacherConseil();

    const res  = await fetch("/api/jouer", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ ...getEtatServeur(), col })
    });
    const data = await res.json();

    if (data.status === "col_invalide" || data.status === "fin") {
        ETAT.en_train = false;
        activerPlateau();
        return;
    }

    ETAT.plateau        = data.plateau;
    ETAT.joueur_courant = data.joueur_courant;
    ETAT.historique     = data.historique;
    ETAT.resultat       = data.resultat;

    mettreAJourUI();

    if (!ETAT.resultat && ETAT.mode === 1) {
        const info = document.getElementById("info");
        if (info) { info.innerHTML = "🧠 IA réfléchit..."; info.className = "info ia-thinking"; }

        await pause(300);
        await jouerIA();
    }

    ETAT.en_train = false;
    activerPlateau();
}

/* ================================================
   COUP IA
================================================ */

async function jouerIA() {
    if (ETAT.resultat) return;

    const joueur    = ETAT.joueur_courant;
    const ia_type   = joueur === 1 ? ETAT.ia_rouge : ETAT.ia_jaune;
    const profondeur = joueur === 1 ? ETAT.profondeur_rouge : ETAT.profondeur_jaune;

    const res  = await fetch("/api/ia_step", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ ...getEtatServeur(), ia_type, profondeur })
    });
    const data = await res.json();

    if (data.status === "fin" || data.status === "nul") return;

    ETAT.plateau        = data.plateau;
    ETAT.joueur_courant = data.joueur_courant;
    ETAT.historique     = data.historique;
    ETAT.resultat       = data.resultat;

    mettreAJourUI();
}

/* ================================================
   TIMER IA VS IA
================================================ */

function demarrerTimerIA() {
    if (ETAT.timer_ia !== null) return;

    ETAT.timer_ia = setInterval(async () => {
        if (ETAT.en_train || ETAT.resultat) return;
        ETAT.en_train = true;

        const info = document.getElementById("info");
        if (info) info.innerHTML = "🤖 IA joue...";

        await jouerIA();

        ETAT.en_train = false;
        if (ETAT.resultat) stopperTimerIA();
    }, ETAT.delai_ia);
}

function stopperTimerIA() {
    if (ETAT.timer_ia !== null) {
        clearInterval(ETAT.timer_ia);
        ETAT.timer_ia = null;
    }
}

/* ================================================
   ANNULER COUP
================================================ */

async function annulerCoup() {
    if (ETAT.en_train) return;
    stopperTimerIA();
    ETAT.en_train = false;
    cacherConseil();

    const res  = await fetch("/api/annuler", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(getEtatServeur())
    });
    const data = await res.json();

    ETAT.plateau        = data.plateau;
    ETAT.joueur_courant = data.joueur_courant;
    ETAT.historique     = data.historique;
    ETAT.resultat       = data.resultat;

    mettreAJourUI();
}

/* ================================================
   CHANGER MODE
================================================ */

async function changerMode() {
    const modeStr = document.getElementById("modeSelect").value;
    const mode    = parseInt(modeStr);
    if (isNaN(mode)) return;

    stopperTimerIA();
    ETAT.en_train = false;
    ETAT.mode     = mode;
    cacherConseil();

    mettreAJourUI();
}

async function activerSituation() {
    stopperTimerIA();
    ETAT.en_train = false;
    cacherConseil();

    ETAT.mode = ETAT.mode === 3 ? 2 : 3;

    const modeSelect = document.getElementById("modeSelect");
    if (modeSelect) modeSelect.value = ETAT.mode === 3 ? "" : String(ETAT.mode);

    mettreAJourUI();
}

/* ================================================
   CHANGER DÉPART
================================================ */

async function changerDepart() {
    const couleur = parseInt(document.getElementById("departSelect").value);
    ETAT.couleur_depart = couleur;
    ETAT.joueur_humain = couleur;
    await nouvellePartie();
}

/* ================================================
   CHANGER PROFONDEUR
================================================ */

async function changerProfondeur(joueur) {
    const id   = joueur === "rouge" ? "profondeurRouge" : "profondeurJaune";
    const prof = parseInt(document.getElementById(id).value);
    if (joueur === "rouge") ETAT.profondeur_rouge = prof;
    else ETAT.profondeur_jaune = prof;
}

async function changerStrategie() {
    ETAT.ia_rouge = document.getElementById("strategieRouge").value;
    ETAT.ia_jaune = document.getElementById("strategieJaune").value;
}

function appliquerDelaiIA() {
    ETAT.delai_ia = parseInt(document.getElementById("delaiIA").value) || 600;
    stopperTimerIA();
    if (ETAT.mode === 0 && !ETAT.resultat) demarrerTimerIA();
}

/* ================================================
   MODE SITUATION
================================================ */

/* ── Importer séquence depuis fichier .txt ── */
async function importerSequence() {
    const input = document.getElementById("importFichier");
    const infoDiv = document.getElementById("importInfo");

    if (!input.files || input.files.length === 0) return;

    const fichier = input.files[0];

    // La séquence est dans le NOM du fichier (ex: 554433221.txt)
    const nomFichier = fichier.name.replace(/\.[^.]+$/, ""); // enlever l'extension
    const coups = nomFichier.replace(/[^0-9]/g, "");

    if (coups.length === 0) {
        if (infoDiv) infoDiv.innerHTML = "❌ Pas de chiffres dans le nom du fichier";
        return;
    }

    // Reconstruire le plateau coup par coup
    const lignes = ETAT.lignes;
    const colonnes = ETAT.colonnes;
    let plateau = Array.from({ length: lignes }, () => new Array(colonnes).fill(0));
    let joueur = ETAT.couleur_depart || 1;
    let nbCoups = 0;

    for (const ch of coups) {
        const col = parseInt(ch) - 1;  // fichier = 1-indexé, plateau = 0-indexé
        if (col < 0 || col >= colonnes) continue;

        let placed = false;
        for (let row = lignes - 1; row >= 0; row--) {
            if (plateau[row][col] === 0) {
                plateau[row][col] = joueur;
                placed = true;
                break;
            }
        }

        if (placed) {
            nbCoups++;
            joueur = joueur === 1 ? 2 : 1;
        }
    }

    ETAT.plateau = plateau;
    ETAT.joueur_courant = joueur;
    ETAT.resultat = null;

    afficherPlateauEditeur(ETAT.plateau);

    const joueurSelect = document.getElementById("joueurAnalyse");
    if (joueurSelect) joueurSelect.value = String(joueur);

    const nomJoueur = joueur === 1 ? "Rouge" : "Jaune";
    const emoji = joueur === 1 ? "🔴" : "🟡";
    if (infoDiv) {
        infoDiv.innerHTML = `✅ ${nbCoups} coups chargés depuis "${fichier.name}" — ${emoji} ${nomJoueur} joue`;
    }

    const info = document.getElementById("info");
    if (info) {
        info.innerHTML = `📂 Séquence "${nomFichier}" (${nbCoups} coups) — ${emoji} ${nomJoueur} joue`;
        info.className = "info";
    }

    input.value = "";
}

async function situationPlacer(lig, col) {
    let couleur = ETAT.pion_editeur;
    if (ETAT.plateau[lig][col] === couleur) couleur = 0;

    const res  = await fetch("/api/situation/placer", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ ...getEtatServeur(), lig, col, couleur })
    });
    const data = await res.json();

    ETAT.plateau = data.plateau;
    afficherPlateauEditeur(ETAT.plateau);

    const info = document.getElementById("info");
    if (data.victoire_rouge) {
        info.innerHTML = "🔴 Rouge est déjà gagnant !";
        info.className = "info fin";
    } else if (data.victoire_jaune) {
        info.innerHTML = "🟡 Jaune est déjà gagnant !";
        info.className = "info fin";
    } else {
        info.innerHTML = "🧠 Mode Situation — placez vos pions librement";
        info.className = "info";
    }
}

async function changerPionEditeur(pion) {
    ETAT.pion_editeur = pion;
    mettreAJourBoutonsPion(pion);
}

function mettreAJourBoutonsPion(pion) {
    const btnRouge   = document.getElementById("btnPionRouge");
    const btnJaune   = document.getElementById("btnPionJaune");
    const btnEffacer = document.getElementById("btnPionEffacer");
    if (btnRouge)   btnRouge.classList.toggle("actif", pion === 1);
    if (btnJaune)   btnJaune.classList.toggle("actif", pion === 2);
    if (btnEffacer) btnEffacer.classList.toggle("actif", pion === 0);
}

/* ── Continuer la partie depuis la position actuelle ── */
async function continuerPartie(mode) {
    // Récupérer qui joue depuis le sélecteur d'analyse
    const joueurSelect = document.getElementById("joueurAnalyse");
    const joueur = joueurSelect ? parseInt(joueurSelect.value) : ETAT.joueur_courant;

    // Garder le plateau actuel, changer le mode
    ETAT.joueur_courant = joueur;
    ETAT.mode = mode;
    ETAT.resultat = null;
    ETAT.en_train = false;
    ETAT.partie_sauvegardee = false;

    // Reconstruire l'historique depuis le plateau actuel
    // (on ne peut pas le reconstituer exactement, mais on vide pour repartir propre)
    ETAT.historique = [];

    // En mode Humain vs IA, le joueur humain est celui qui joue en premier
    if (mode === 1) {
        ETAT.joueur_humain = joueur;
    }

    // Mettre à jour le sélecteur de mode
    const modeSelect = document.getElementById("modeSelect");
    if (modeSelect) modeSelect.value = String(mode);

    cacherConseil();
    mettreAJourUI();

    const nomMode = mode === 0 ? "IA vs IA" : mode === 1 ? "Humain vs IA" : "2 Joueurs";
    const emoji = joueur === 1 ? "🔴" : "🟡";
    const nomJoueur = joueur === 1 ? "Rouge" : "Jaune";

    const info = document.getElementById("info");
    if (info) {
        info.innerHTML = `▶ Partie lancée en ${nomMode} — ${emoji} ${nomJoueur} commence`;
        info.className = "info";
    }
}

async function situationEffacer() {
    ETAT.plateau = Array.from({ length: ETAT.lignes }, () => new Array(ETAT.colonnes).fill(0));
    afficherPlateauEditeur(ETAT.plateau);

    const info = document.getElementById("info");
    info.innerHTML = "🧠 Mode Situation — plateau effacé";
    info.className = "info";

    const zoneResultat = document.getElementById("resultatAnalyse");
    const zoneContainer = document.getElementById("zoneAnalyseResultat");
    if (zoneResultat) zoneResultat.innerHTML = "";
    if (zoneContainer) zoneContainer.style.display = "none";

    // Reset le file input
    const fi = document.getElementById("importFichier");
    if (fi) fi.value = "";
    const ii = document.getElementById("importInfo");
    if (ii) ii.innerHTML = "";
}

async function situationAnalyser() {
    const joueurSelect = document.getElementById("joueurAnalyse");
    const joueur_analyse = joueurSelect ? parseInt(joueurSelect.value) : 1;

    const profSelect = document.getElementById("profondeurAnalyse");
    const profondeur = profSelect ? parseInt(profSelect.value) : 6;

    const info = document.getElementById("info");
    info.innerHTML = "🔍 Analyse en cours...";
    info.className = "info ia-thinking";

    const res  = await fetch("/api/situation/analyser", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ ...getEtatServeur(), joueur_analyse, profondeur })
    });
    const data = await res.json();

    info.innerHTML = "🧠 Mode Situation — placez vos pions librement";
    info.className = "info";

    const zoneResultat  = document.getElementById("resultatAnalyse");
    const zoneContainer = document.getElementById("zoneAnalyseResultat");

    if (zoneResultat) {
        let couleurResultat = "#facc15";
        if (data.gagnant === "rouge")     couleurResultat = "#ef4444";
        if (data.gagnant === "jaune")     couleurResultat = "#facc15";
        if (data.gagnant === "equilibre") couleurResultat = "#60a5fa";

        zoneResultat.innerHTML = `
            <div class="analyse-result" style="border-color: ${couleurResultat}">
                <p style="font-size:18px; font-weight:bold;">${data.message}</p>
                ${data.meilleur_col !== undefined
                    ? `<p class="meilleur-coup">🎯 Meilleur coup : colonne <strong>${data.meilleur_col + 1}</strong></p>`
                    : ""}
                ${data.nb_coups !== undefined && data.nb_coups !== null
                    ? `<p>📊 Victoire forcée en <strong>${data.nb_coups} coup(s)</strong></p>`
                    : ""}
            </div>
        `;
        if (zoneContainer) zoneContainer.style.display = "block";
    }

    if (data.meilleur_col !== undefined) surlignerColonne(data.meilleur_col);
}

async function changerProfondeurAnalyse() {
    // Rien à faire côté serveur, juste côté client
}

/* ================================================
   CONSEIL IA (SEUILS CORRIGÉS)
================================================ */

async function afficherConseil() {
    const res  = await fetch("/api/conseil", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ ...getEtatServeur(), profondeur: 4 })
    });
    const data = await res.json();

    if (data.status !== "ok") return;
    afficherScoresColonnes(data.scores, data.meilleur_col);
}

function afficherScoresColonnes(scores, meilleurCol) {
    cacherConseil();

    const plateauDiv = document.getElementById("plateau");
    if (!plateauDiv) return;

    const nbCol = ETAT.colonnes;
    const cases = plateauDiv.querySelectorAll(".case");
    if (cases.length === 0) return;

    plateauDiv.style.position = "relative";

    for (let col = 0; col < nbCol; col++) {
        const caseTarget = cases[col];
        if (!caseTarget) continue;

        const rect        = caseTarget.getBoundingClientRect();
        const plateauRect = plateauDiv.getBoundingClientRect();
        const scoreCol    = scores[col];
        const isMeilleur  = col === meilleurCol;

        // SEUILS CORRIGÉS pour SCORE_VICTOIRE = 1_000_000
        let couleur = "#60a5fa";
        if (scoreCol === undefined)              couleur = "#475569";
        else if (scoreCol > SEUIL_VICTOIRE)      couleur = "#22c55e";
        else if (scoreCol < -SEUIL_VICTOIRE)     couleur = "#ef4444";
        else if (scoreCol > 500)                 couleur = "#86efac";
        else if (scoreCol < -500)                couleur = "#fca5a5";

        let texteScore;
        if (scoreCol === undefined) {
            texteScore = "X";
        } else if (scoreCol > SEUIL_VICTOIRE) {
            const demi = 1000000 - scoreCol;
            const coups = Math.ceil((demi + 1) / 2);
            texteScore = `WIN ${coups}`;
        } else if (scoreCol < -SEUIL_VICTOIRE) {
            const demi = 1000000 + scoreCol;
            const coups = Math.ceil((demi + 1) / 2);
            texteScore = `LOSE ${coups}`;
        } else {
            texteScore = (scoreCol > 0 ? "+" : "") + scoreCol;
        }

        const div = document.createElement("div");
        div.className = "conseil-score-col";

        div.innerHTML = `
            <div style="text-align:center; color:${couleur}; font-size:${isMeilleur ? "13px" : "11px"}; font-weight:${isMeilleur ? "bold" : "normal"}; opacity:${isMeilleur ? "1" : "0.75"};">
                ${isMeilleur ? `<div style="font-size:22px; animation: bounceDown 0.8s infinite;">▼</div>` : ""}
                <div>${texteScore}</div>
            </div>
        `;

        div.style.position    = "absolute";
        div.style.left        = (rect.left - plateauRect.left + rect.width/2 - 20) + "px";
        div.style.top         = isMeilleur ? "-70px" : "-35px";
        div.style.width       = "40px";
        div.style.zIndex      = "100";
        div.style.pointerEvents = "none";

        plateauDiv.appendChild(div);
    }
}

function cacherConseil() {
    document.querySelectorAll(".conseil-score-col").forEach(e => e.remove());
    const fleche = document.getElementById("conseilFleche");
    if (fleche) fleche.remove();
}

/* ================================================
   SURLIGNER COLONNE
================================================ */

function surlignerColonne(col) {
    const cases = document.querySelectorAll(".case");
    const nbCol = ETAT.colonnes;

    cases.forEach((c, index) => {
        c.classList.remove("surligne");
        if (index % nbCol === col) c.classList.add("surligne");
    });

    setTimeout(() => {
        document.querySelectorAll(".case.surligne").forEach(c => c.classList.remove("surligne"));
    }, 3000);
}

/* ================================================
   SAUVEGARDER PARTIE
================================================ */

async function sauvegarderPartie() {
    if (ETAT.partie_sauvegardee) return;

    await fetch("/api/sauvegarder", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ ...getEtatServeur(), mode: ETAT.mode })
    });

    ETAT.partie_sauvegardee = true;
}

/* ================================================
   HISTORIQUE
================================================ */

async function ouvrirHistorique() {
    document.getElementById("modalHistorique").style.display = "block";
    const res  = await fetch("/api/historique");
    const data = await res.json();

    const liste = document.getElementById("listeParties");
    liste.innerHTML = "";

    data.forEach(partie => {
        const tr = document.createElement("tr");
        const couleur = partie.resultat === "rouge"
            ? "style='color:#ef4444;font-weight:bold'"
            : "style='color:#facc15;font-weight:bold'";

        tr.innerHTML = `
            <td>${partie.id}</td>
            <td>${partie.date}</td>
            <td style="font-family:monospace">${partie.coups}</td>
            <td ${couleur}>${partie.resultat}</td>
            <td>${partie.statut}</td>
            <td><button onclick="chargerPartie(${partie.id},'${partie.coups}')">▶ Replay</button></td>
        `;
        liste.appendChild(tr);
    });
}

function fermerHistorique() {
    document.getElementById("modalHistorique").style.display = "none";
}

/* ================================================
   CHARGER PARTIE
================================================ */

async function chargerPartie(id, coups) {
    fermerHistorique();

    const res  = await fetch(`/api/charger/${id}`);
    const data = await res.json();

    if (data.status !== "ok") return;

    ETAT.plateau        = data.plateau;
    ETAT.joueur_courant = data.joueur_courant;
    ETAT.couleur_depart = data.couleur_depart;
    ETAT.historique     = data.historique;
    ETAT.resultat       = data.resultat;
    ETAT.lignes         = data.lignes;
    ETAT.colonnes       = data.colonnes;
    ETAT.partie_sauvegardee = true;

    ETAT.replay_actif  = true;
    ETAT.replay_coups  = coups.split("").map(Number);
    ETAT.replay_index  = ETAT.replay_coups.length;

    afficherReplay();
    afficherControlesReplay();
}

/* ================================================
   REPLAY
================================================ */

function afficherReplay() {
    const lignes   = ETAT.lignes;
    const colonnes = ETAT.colonnes;
    let plateau = Array.from({ length: lignes }, () => new Array(colonnes).fill(0));
    let joueur  = ETAT.couleur_depart || 1;

    for (let i = 0; i < ETAT.replay_index; i++) {
        const col = ETAT.replay_coups[i] - 1;
        for (let row = lignes - 1; row >= 0; row--) {
            if (plateau[row][col] === 0) {
                plateau[row][col] = joueur;
                break;
            }
        }
        joueur = joueur === 1 ? 2 : 1;
    }

    afficherPlateau(plateau);

    const info = document.getElementById("info");
    if (info) info.innerHTML = `🎬 Replay — coup ${ETAT.replay_index} / ${ETAT.replay_coups.length}`;
}

function afficherControlesReplay() {
    let div = document.getElementById("replayControls");
    if (!div) {
        div = document.createElement("div");
        div.id = "replayControls";
        div.innerHTML = `
            <button onclick="replayPrecedent()">◀ Précédent</button>
            <button onclick="replaySuivant()">Suivant ▶</button>
            <button onclick="quitterReplay()">✕ Quitter</button>
        `;
        document.getElementById("plateau").after(div);
    }
}

function replaySuivant() {
    if (ETAT.replay_index < ETAT.replay_coups.length) { ETAT.replay_index++; afficherReplay(); }
}

function replayPrecedent() {
    if (ETAT.replay_index > 0) { ETAT.replay_index--; afficherReplay(); }
}

function quitterReplay() {
    ETAT.replay_actif = false;
    const ctrl = document.getElementById("replayControls");
    if (ctrl) ctrl.remove();
    mettreAJourUI();
}

/* ================================================
   HELPER : état à envoyer au serveur
================================================ */

function getEtatServeur() {
    return {
        plateau:        ETAT.plateau,
        joueur_courant: ETAT.joueur_courant,
        couleur_depart: ETAT.couleur_depart,
        historique:     ETAT.historique,
        resultat:       ETAT.resultat,
        lignes:         ETAT.lignes,
        colonnes:       ETAT.colonnes,
    };
}

/* ================================================
   UTILITAIRES
================================================ */

function pause(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function desactiverPlateau() {
    document.querySelectorAll(".case").forEach(c => {
        c.style.pointerEvents = "none";
        c.style.opacity = "0.6";
    });
}

function activerPlateau() {
    document.querySelectorAll(".case").forEach(c => {
        c.style.pointerEvents = "auto";
        c.style.opacity = "1";
    });
}

window.onclick = function(event) {
    const modal = document.getElementById("modalHistorique");
    if (event.target === modal) modal.style.display = "none";
}