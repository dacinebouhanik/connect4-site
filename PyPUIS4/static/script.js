let timerIA = null;
let delaiIAActuel = 600;

/* ================================
   CHARGER PLATEAU
================================ */

async function chargerPlateau() {

    const res = await fetch("/api/plateau");
    const data = await res.json();

    const modeSelect = document.getElementById("modeSelect");
    if (modeSelect) modeSelect.value = String(data.mode);

    const zoneIA = document.getElementById("zoneIA");
    if (zoneIA) {
        if (data.mode === 0 || data.mode === 1) {
            zoneIA.style.display = "block";
        } else {
            zoneIA.style.display = "none";
        }
    }

    const plateauDiv = document.getElementById("plateau");
    plateauDiv.innerHTML = "";

    const nbColonnes = data.plateau[0].length;

    plateauDiv.style.display = "grid";
    plateauDiv.style.gridTemplateColumns = `repeat(${nbColonnes}, 42px)`;
    plateauDiv.style.gap = "4px";
    plateauDiv.style.justifyContent = "center";

    data.plateau.forEach((ligne) => {
        ligne.forEach((cell, colIndex) => {

            const div = document.createElement("div");
            div.className = "case";
            div.style.width = "42px";
            div.style.height = "42px";

            if (cell === 1) {
                div.innerHTML = "●";
                div.classList.add("rouge");
            } else if (cell === 2) {
                div.innerHTML = "●";
                div.classList.add("jaune");
            }

            div.onclick = () => {
                if (!data.resultat && data.mode !== 0) {
                    jouer(colIndex);
                }
            };

            plateauDiv.appendChild(div);

        });
    });

    const info = document.getElementById("info");

    if (data.resultat) {

        info.innerHTML = "Partie terminée : " + data.resultat;

        const zone = document.getElementById("historique");
        if (zone && zone.style.display !== "none") {
            chargerHistorique();
        }

    } else {

        info.innerHTML = "Joueur : " + (data.joueur === 1 ? "Rouge" : "Jaune");

    }

    afficherScoresSousColonnes(data.scores);

    if (data.mode === 0 && !data.resultat) {
        demarrerIA();
    } else {
        stopperIA();
    }
}


/* ================================
   JOUER
================================ */

async function jouer(col) {

    await fetch("/api/jouer", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ col: col })
    });

    chargerPlateau();
}


/* ================================
   NOUVELLE PARTIE
================================ */

async function nouvellePartie() {

    await fetch("/api/nouvelle");
    chargerPlateau();

}


/* ================================
   ANNULER
================================ */

async function annulerCoup() {

    await fetch("/api/annuler");
    chargerPlateau();

}


/* ================================
   CHANGER MODE
================================ */

async function changerMode() {

    const modeSelect = document.getElementById("modeSelect");
    const mode = parseInt(modeSelect.value);

    await fetch("/api/mode", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ mode: mode })
    });

    chargerPlateau();

}


/* ================================
   IA vs IA
================================ */

function demarrerIA() {

    if (timerIA !== null) return;

    const d = parseInt(delaiIAActuel) || 600;

    timerIA = setInterval(async () => {

        await fetch("/api/ia_step", {
            method: "POST"
        });

        await chargerPlateau();

    }, d);

}

function stopperIA() {

    if (timerIA !== null) {
        clearInterval(timerIA);
        timerIA = null;
    }

}


/* ================================
   SCORES MINIMAX
================================ */

function afficherScoresSousColonnes(scores) {

    const ancien = document.getElementById("scoresMinimax");
    if (ancien) ancien.remove();

    if (!scores) return;

    const nbColonnes = Object.keys(scores).length;

    const div = document.createElement("div");

    div.id = "scoresMinimax";
    div.style.display = "grid";
    div.style.gridTemplateColumns = `repeat(${nbColonnes}, 42px)`;
    div.style.gap = "4px";
    div.style.marginTop = "8px";
    div.style.justifyContent = "center";

    for (let i = 0; i < nbColonnes; i++) {

        const cell = document.createElement("div");

        cell.style.textAlign = "center";
        cell.style.fontSize = "14px";
        cell.style.color = "green";
        cell.style.fontWeight = "bold";

        cell.innerText = scores[i] !== undefined ? scores[i] : "";

        div.appendChild(cell);
    }

    const plateauDiv = document.getElementById("plateau");
    plateauDiv.after(div);
}


/* ================================
   HISTORIQUE (MODIFIÉ)
================================ */

async function chargerHistorique() {

    const res = await fetch("/api/historique");
    const data = await res.json();

    const liste = document.getElementById("listeParties");
    if (!liste) return;

    liste.innerHTML = "";

    data.forEach(partie => {

        const ligne = document.createElement("tr");

        let resultatTexte = "Match nul";

        if (partie.resultat === "rouge")
            resultatTexte = "🔴 Rouge gagne";

        if (partie.resultat === "jaune")
            resultatTexte = "🟡 Jaune gagne";

        ligne.innerHTML = `
            <td>${partie.id}</td>
            <td>${partie.date}</td>
           <td>${partie.coups ? partie.coups.length : 0}</td>
            <td>${resultatTexte}</td>
            <td>${partie.statut}</td>
            <td>
                <button onclick="chargerPartie(${partie.id})">
                    Voir
                </button>
            </td>
        `;

        liste.appendChild(ligne);

    });

}
function ouvrirHistorique() {

    const zone = document.getElementById("historique");

    if (!zone) return;

    if (zone.style.display === "none" || zone.style.display === "") {
        zone.style.display = "block";
        chargerHistorique();
    } else {
        zone.style.display = "none";
    }

}


/* ================================
   CHARGER PARTIE
================================ */

async function chargerPartie(id) {

    await fetch("/api/charger/" + id);

    chargerPlateau();

}


/* ================================
   INITIALISATION
================================ */

chargerPlateau();