/* ================================================
   ÉTAT GLOBAL
================================================ */

let timerIA      = null;
let delaiIA      = 600;
let enTrain      = false;
let replayActif  = false;
let replayCoups  = [];
let replayIndex  = 0;
let etatActuel   = null;


/* ================================================
   INITIALISATION
================================================ */

document.addEventListener("DOMContentLoaded", () => {
    chargerPlateau();
});


/* ================================================
   CHARGER PLATEAU
================================================ */

async function chargerPlateau() {
    if (replayActif) return;

    const res  = await fetch("/api/plateau");
    const data = await res.json();
    etatActuel = data;

    mettreAJourUI(data);
}


/* ================================================
   METTRE À JOUR TOUTE L'UI
================================================ */

function mettreAJourUI(data) {

    const modeSelect = document.getElementById("modeSelect");
    if (modeSelect) modeSelect.value = data.mode === 3 ? "" : String(data.mode);

    // Bouton situation actif ou non
    const btnSituation = document.getElementById("btnSituation");
    if (btnSituation) btnSituation.classList.toggle("actif", data.mode === 3);

    const zoneIA = document.getElementById("zoneIA");
    if (zoneIA) zoneIA.style.display = (data.mode === 0 || data.mode === 1) ? "block" : "none";

    const zoneSituation = document.getElementById("zoneSituation");
    if (zoneSituation) zoneSituation.style.display = data.mode === 3 ? "block" : "none";

    const profRouge = document.getElementById("profondeurRouge");
    const profJaune = document.getElementById("profondeurJaune");
    if (profRouge) profRouge.value = String(data.profondeur_rouge);
    if (profJaune) profJaune.value = String(data.profondeur_jaune);

    const departSelect = document.getElementById("departSelect");
    if (departSelect) departSelect.value = String(data.couleur_depart);

    if (data.pion_editeur !== undefined) {
        mettreAJourBoutonsPion(data.pion_editeur);
    }

    if (data.mode === 3) {
        afficherPlateauEditeur(data.plateau);
    } else {
        afficherPlateau(data.plateau, data);
    }

    const info = document.getElementById("info");
    if (info) {
        if (data.resultat) {
            const emoji = data.resultat === "rouge" ? "🔴" : data.resultat === "jaune" ? "🟡" : "🤝";
            const texte = data.resultat === "nul" ? "Match nul !" : `${emoji} ${data.resultat.toUpperCase()} gagne !`;
            info.innerHTML = "🏆 " + texte;
            info.className = "info fin";
        } else if (data.mode === 3) {
            info.innerHTML = "🧠 Mode Situation — placez vos pions librement";
            info.className = "info";
        } else {
            const emoji = data.joueur === 1 ? "🔴" : "🟡";
            const nom   = data.joueur === 1 ? "Rouge" : "Jaune";
            info.innerHTML = `${emoji} Tour de ${nom}`;
            info.className = "info";
        }
    }

    const zoneResultat = document.getElementById("resultатAnalyse");
    const zoneContainer = document.getElementById("zoneAnalyseResultat");
    if (zoneResultat && data.mode !== 3) {
        zoneResultat.innerHTML = "";
        if (zoneContainer) zoneContainer.style.display = "none";
    }

    if (data.mode === 0 && !data.resultat) {
        demarrerTimerIA();
    } else {
        stopperTimerIA();
        enTrain = false;
    }

    // Afficher conseil si mode HvIA et c'est le tour de l'humain
    if (data.mode === 1 && !data.resultat) {
        afficherConseil();
    } else if (data.mode !== 1) {
        cacherConseil();
    }
}


/* ================================================
   AFFICHER PLATEAU NORMAL
================================================ */

function afficherPlateau(plateau, data = null) {
    const plateauDiv = document.getElementById("plateau");
    plateauDiv.innerHTML = "";

    const nbCol = plateau[0].length;
    plateauDiv.style.gridTemplateColumns = `repeat(${nbCol}, 50px)`;

    const cliquable = data && data.mode !== 0 && !data.resultat;

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
   AFFICHER PLATEAU ÉDITEUR (mode situation)
================================================ */

function afficherPlateauEditeur(plateau) {
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
            div.title = `Ligne ${rowIndex}, Colonne ${colIndex}`;
            div.onclick = () => situationPlacer(rowIndex, colIndex);

            plateauDiv.appendChild(div);
        });
    });
}


/* ================================================
   MODE SITUATION — ACTIVER / DÉSACTIVER
================================================ */

async function activerSituation() {
    stopperTimerIA();
    enTrain = false;

    const nouveauMode = (etatActuel && etatActuel.mode === 3) ? 2 : 3;

    document.getElementById("modeSelect").value = nouveauMode === 3 ? "" : String(nouveauMode);
    document.getElementById("btnSituation").classList.toggle("actif", nouveauMode === 3);

    const joueurSelect = document.getElementById("joueurAnalyse");
    const joueur = joueurSelect ? parseInt(joueurSelect.value) : 1;

    await fetch("/api/mode", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ mode: nouveauMode, joueur_courant: joueur })
    });

    await chargerPlateau();
}


/* ================================================
   MODE SITUATION — PLACER UN PION
================================================ */

async function situationPlacer(lig, col) {
    const plateau = etatActuel ? etatActuel.plateau : null;
    let couleur = etatActuel ? etatActuel.pion_editeur : 1;

    if (plateau && plateau[lig][col] === couleur) {
        couleur = 0;
    }

    const res  = await fetch("/api/situation/placer", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ lig, col, couleur })
    });
    const data = await res.json();

    etatActuel = { ...etatActuel, plateau: data.plateau };
    afficherPlateauEditeur(data.plateau);

    const info = document.getElementById("info");
    if (data.victoire_rouge) {
        info.innerHTML = "🔴 Rouge est déjà en position gagnante sur ce plateau !";
        info.className = "info fin";
    } else if (data.victoire_jaune) {
        info.innerHTML = "🟡 Jaune est déjà en position gagnante sur ce plateau !";
        info.className = "info fin";
    } else {
        info.innerHTML = "🧠 Mode Situation — placez vos pions librement";
        info.className = "info";
    }
}


/* ================================================
   MODE SITUATION — CHANGER PION ACTIF
================================================ */

async function changerPionEditeur(pion) {
    etatActuel = { ...etatActuel, pion_editeur: pion };
    mettreAJourBoutonsPion(pion);

    await fetch("/api/situation/pion", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ pion })
    });
}

function mettreAJourBoutonsPion(pion) {
    const btnRouge   = document.getElementById("btnPionRouge");
    const btnJaune   = document.getElementById("btnPionJaune");
    const btnEffacer = document.getElementById("btnPionEffacer");

    if (btnRouge)   btnRouge.classList.toggle("actif", pion === 1);
    if (btnJaune)   btnJaune.classList.toggle("actif", pion === 2);
    if (btnEffacer) btnEffacer.classList.toggle("actif", pion === 0);
}


/* ================================================
   MODE SITUATION — EFFACER PLATEAU
================================================ */

async function situationEffacer() {
    const res  = await fetch("/api/situation/effacer", { method: "POST" });
    const data = await res.json();

    etatActuel = { ...etatActuel, plateau: data.plateau };
    afficherPlateauEditeur(data.plateau);

    const info = document.getElementById("info");
    info.innerHTML = "🧠 Mode Situation — plateau effacé";
    info.className = "info";

    const zoneResultat = document.getElementById("resultатAnalyse");
    if (zoneResultat) zoneResultat.innerHTML = "";
}


/* ================================================
   MODE SITUATION — ANALYSER LA POSITION
================================================ */

async function situationAnalyser() {
    const joueurSelect = document.getElementById("joueurAnalyse");
    const joueur = joueurSelect ? parseInt(joueurSelect.value) : 1;

    const info = document.getElementById("info");
    info.innerHTML = "🔍 Analyse en cours...";
    info.className = "info ia-thinking";

    const res  = await fetch("/api/situation/analyser", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ joueur })
    });
    const data = await res.json();

    // Remettre le message normal dans #info
    info.innerHTML = "🧠 Mode Situation — placez vos pions librement";
    info.className = "info";

    const zoneResultat = document.getElementById("resultатAnalyse");
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
            </div>
        `;
        if (zoneContainer) zoneContainer.style.display = "block";
    }

    if (data.meilleur_col !== undefined) {
        surlignerColonne(data.meilleur_col);
    }
}




/* ================================================
   CONSEIL HUMAIN — MEILLEUR COUP EN TEMPS RÉEL
================================================ */

async function afficherConseil() {
    const res  = await fetch("/api/conseil");
    const data = await res.json();

    if (data.status !== "ok") return;

    // Afficher la flèche au-dessus de la colonne conseillée
    afficherFleche(data.meilleur_col, data.verdict, data.score);
}

function afficherFleche(col, verdict, score) {
    // Supprimer l'ancienne flèche
    cacherConseil();

    const plateauDiv = document.getElementById("plateau");
    if (!plateauDiv) return;

    const nbCol = etatActuel ? etatActuel.plateau[0].length : 9;

    // Calculer la position de la colonne
    const cases = plateauDiv.querySelectorAll(".case");
    if (cases.length === 0) return;

    // Trouver la case de la première ligne de la colonne conseillée
    const caseTarget = cases[col];
    if (!caseTarget) return;

    let couleur = "#60a5fa";
    let texteVerdict = "Équilibre";
    if (verdict === "victoire")     { couleur = "#22c55e"; texteVerdict = "Gagne !"; }
    else if (verdict === "defaite") { couleur = "#ef4444"; texteVerdict = "Danger"; }
    else if (verdict === "avantage"){ couleur = "#86efac"; texteVerdict = "Avantage"; }
    else if (verdict === "desavantage") { couleur = "#fca5a5"; texteVerdict = "Risqué"; }

    // Créer la flèche
    const fleche = document.createElement("div");
    fleche.id = "conseilFleche";
    fleche.innerHTML = `
        <div style="text-align:center; line-height:1.2;">
            <div style="font-size:11px; color:${couleur}; font-weight:bold;">${texteVerdict}</div>
            <div style="font-size:28px; color:${couleur}; animation: bounceDown 0.8s infinite;">▼</div>
        </div>
    `;

    // Positionner la flèche au-dessus de la bonne case
    const rect = caseTarget.getBoundingClientRect();
    const plateauRect = plateauDiv.getBoundingClientRect();

    fleche.style.position = "absolute";
    fleche.style.left = (rect.left - plateauRect.left + rect.width/2 - 20) + "px";
    fleche.style.top = "-55px";
    fleche.style.width = "40px";
    fleche.style.zIndex = "100";
    fleche.style.pointerEvents = "none";

    // Mettre le plateau en position relative
    plateauDiv.style.position = "relative";
    plateauDiv.appendChild(fleche);
}

function cacherConseil() {
    const fleche = document.getElementById("conseilFleche");
    if (fleche) fleche.remove();
}

/* ================================================
   SURLIGNER UNE COLONNE
================================================ */

function surlignerColonne(col) {
    const cases = document.querySelectorAll(".case");
    const nbCol = etatActuel ? etatActuel.plateau[0].length : 9;

    cases.forEach((c, index) => {
        c.classList.remove("surligne");
        if (index % nbCol === col) {
            c.classList.add("surligne");
        }
    });

    setTimeout(() => {
        document.querySelectorAll(".case.surligne").forEach(c => c.classList.remove("surligne"));
    }, 3000);
}


/* ================================================
   JOUER COUP HUMAIN (mode normal)
================================================ */

async function jouer(col) {
    if (enTrain) return;
    if (etatActuel && etatActuel.resultat) return;
    if (etatActuel && etatActuel.mode === 0) return;
    if (etatActuel && etatActuel.mode === 3) return;

    enTrain = true;
    desactiverPlateau();

    const res  = await fetch("/api/jouer", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ col })
    });
    const data = await res.json();

    if (data.status === "col_invalide" || data.status === "fin") {
        enTrain = false;
        activerPlateau();
        return;
    }

    etatActuel = { ...etatActuel, ...data };
    mettreAJourUI(etatActuel);

    if (etatActuel.resultat) {
        enTrain = false;
        return;
    }

    if (etatActuel.mode === 1) {
        const info = document.getElementById("info");
        if (info) {
            info.innerHTML = "🧠 IA réfléchit...";
            info.className = "info ia-thinking";
        }

        await pause(300);

        const resIA  = await fetch("/api/ia_step", { method: "POST" });
        const dataIA = await resIA.json();

        etatActuel = { ...etatActuel, ...dataIA };
        mettreAJourUI(etatActuel);
    }

    enTrain = false;
    activerPlateau();
}


/* ================================================
   TIMER IA VS IA
================================================ */

function demarrerTimerIA() {
    if (timerIA !== null) return;

    timerIA = setInterval(async () => {
        if (enTrain) return;
        enTrain = true;

        const info = document.getElementById("info");
        if (info) info.innerHTML = "🤖 IA joue...";

        const res  = await fetch("/api/ia_step", { method: "POST" });
        const data = await res.json();

        etatActuel = { ...etatActuel, ...data };
        mettreAJourUI(etatActuel);

        if (etatActuel.resultat) stopperTimerIA();

        enTrain = false;
    }, delaiIA);
}

function stopperTimerIA() {
    if (timerIA !== null) {
        clearInterval(timerIA);
        timerIA = null;
    }
}


/* ================================================
   CHANGER MODE
================================================ */

async function changerMode() {
    const modeStr = document.getElementById("modeSelect").value;
    const mode = parseInt(modeStr);

    // Si le select est vide → ignorer
    if (isNaN(mode)) return;

    stopperTimerIA();
    enTrain = false;

    const btnSituation = document.getElementById("btnSituation");
    if (btnSituation) btnSituation.classList.toggle("actif", false);

    // Récupérer le joueur sélectionné dans mode situation
    const joueurSelect = document.getElementById("joueurAnalyse");
    const joueur = joueurSelect ? parseInt(joueurSelect.value) : 1;

    await fetch("/api/mode", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ mode, joueur_courant: joueur })
    });

    await chargerPlateau();
}


/* ================================================
   CHANGER PROFONDEUR
================================================ */

async function changerProfondeur(joueur) {
    const id   = joueur === "rouge" ? "profondeurRouge" : "profondeurJaune";
    const prof = parseInt(document.getElementById(id).value);

    await fetch("/api/profondeur", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ joueur, profondeur: prof })
    });
}


/* ================================================
   CHOISIR QUI COMMENCE
================================================ */

async function changerDepart() {
    const couleur = parseInt(document.getElementById("departSelect").value);

    stopperTimerIA();
    enTrain = false;

    const res  = await fetch("/api/couleur_depart", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ couleur })
    });
    const data = await res.json();

    etatActuel = { ...etatActuel, ...data };
    await chargerPlateau();
}


/* ================================================
   NOUVELLE PARTIE
================================================ */

async function nouvellePartie() {
    stopperTimerIA();
    enTrain = false;
    replayActif = false;

    const ctrl = document.getElementById("replayControls");
    if (ctrl) ctrl.remove();

    const res  = await fetch("/api/nouvelle", { method: "POST" });
    const data = await res.json();

    etatActuel = { ...etatActuel, ...data };
    await chargerPlateau();
}


/* ================================================
   ANNULER COUP
================================================ */

async function annulerCoup() {
    if (enTrain) return;
    stopperTimerIA();
    enTrain = false;
    await fetch("/api/annuler");
    await chargerPlateau();
}


/* ================================================
   DÉLAI IA VS IA
================================================ */

function appliquerDelaiIA() {
    delaiIA = parseInt(document.getElementById("delaiIA").value) || 600;
    stopperTimerIA();
    if (etatActuel && etatActuel.mode === 0 && !etatActuel.resultat) {
        demarrerTimerIA();
    }
}


/* ================================================
   CHANGER STRATÉGIE IA
================================================ */

async function changerStrategie() {
    const rouge = document.getElementById("strategieRouge").value;
    const jaune = document.getElementById("strategieJaune").value;

    await fetch("/api/ia_type", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ rouge, jaune })
    });
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
   REPLAY
================================================ */

function chargerPartie(id, coups) {
    fermerHistorique();
    replayActif = true;
    replayCoups = coups.split("").map(Number);
    replayIndex = 0;
    afficherReplay();
    afficherControlesReplay();
}

function afficherReplay() {
    const lignes   = 9;
    const colonnes = 9;
    let plateau = Array.from({ length: lignes }, () => new Array(colonnes).fill(0));
    let joueur  = 1;

    for (let i = 0; i < replayIndex; i++) {
        const col = replayCoups[i] - 1;
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
    if (info) info.innerHTML = `🎬 Replay — coup ${replayIndex} / ${replayCoups.length}`;
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
    if (replayIndex < replayCoups.length) { replayIndex++; afficherReplay(); }
}

function replayPrecedent() {
    if (replayIndex > 0) { replayIndex--; afficherReplay(); }
}

function quitterReplay() {
    replayActif = false;
    const ctrl = document.getElementById("replayControls");
    if (ctrl) ctrl.remove();
    chargerPlateau();
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


/* ================================================
   CHANGER PROFONDEUR ANALYSE (mode situation)
================================================ */

async function changerProfondeurAnalyse() {
    const prof = parseInt(document.getElementById("profondeurAnalyse").value);

    await fetch("/api/profondeur", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ joueur: "rouge", profondeur: prof })
    });
    await fetch("/api/profondeur", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ joueur: "jaune", profondeur: prof })
    });
}