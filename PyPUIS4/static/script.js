let timerIA = null;
let delaiIAActuel = 600;

/* ================================
   CHARGER PLATEAU
================================ */

async function chargerPlateau() {
    const res = await fetch("/api/plateau");
    const data = await res.json();

    // remettre le select sur le mode courant (utile si refresh)
    const modeSelect = document.getElementById("modeSelect");
    if (modeSelect) modeSelect.value = String(data.mode);

    // afficher/masquer la zone réglages IA
    const zoneIA = document.getElementById("zoneIA");
    if (zoneIA) {
        if (data.mode === 0 || data.mode === 1) {
            zoneIA.style.display = "block";
        } else {
            zoneIA.style.display = "none";
        }
    }

    // remplir les réglages IA depuis le backend
    if (data.ia_config) {
        const cfg = data.ia_config;

        // rouge
        const stratR = document.getElementById("strategieRouge");
        const profR = document.getElementById("profRouge");
        if (stratR) stratR.value = cfg.rouge.strategie;
        if (profR) profR.value = String(cfg.rouge.profondeur);

        // jaune
        const stratJ = document.getElementById("strategieJaune");
        const profJ = document.getElementById("profJaune");
        if (stratJ) stratJ.value = cfg.jaune.strategie;
        if (profJ) profJ.value = String(cfg.jaune.profondeur);

        // delai
        const delaiInput = document.getElementById("delaiIA");
        if (delaiInput) delaiInput.value = String(cfg.delai);

        delaiIAActuel = parseInt(cfg.delai) || 600;
    }

    const plateauDiv = document.getElementById("plateau");
    plateauDiv.innerHTML = "";

    const nbColonnes = data.plateau[0].length;

    // Plateau compact
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

            // clic autorisé seulement si partie pas finie ET pas IA vs IA
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
    } else {
        info.innerHTML = "Joueur : " + (data.joueur === 1 ? "Rouge" : "Jaune");
    }

    afficherScoresSousColonnes(data.scores);

    // IA vs IA animation
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
        headers: { "Content-Type": "application/json" },
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
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: mode })
    });

    chargerPlateau();
}

/* ================================
   APPLIQUER CONFIG IA (Tkinter-like)
================================ */

async function appliquerConfigIA() {
    await fetch("/api/config_ia", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            strategieRouge: document.getElementById("strategieRouge").value,
            profRouge: document.getElementById("profRouge").value,
            strategieJaune: document.getElementById("strategieJaune").value,
            profJaune: document.getElementById("profJaune").value,
            delai: document.getElementById("delaiIA").value
        })
    });

    // important : si on est en IA vs IA et qu’on change le délai,
    // on redémarre le timer avec le nouveau délai
    stopperIA();
    chargerPlateau();
}

/* ================================
   IA vs IA
================================ */

function demarrerIA() {
    if (timerIA !== null) return;

    // utilise le délai configuré
    const d = parseInt(delaiIAActuel) || 600;

    timerIA = setInterval(async () => {
        await fetch("/api/ia_step", { method: "POST" });
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
   AFFICHAGE SCORES MINIMAX
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
   HISTORIQUE BD
================================ */

async function ouvrirHistorique() {
    const zone = document.getElementById("historique");

    if (zone.style.display === "none") {
        zone.style.display = "block";
        chargerHistorique();
    } else {
        zone.style.display = "none";
    }
}

async function chargerHistorique() {
    const res = await fetch("/api/historique");
    const data = await res.json();

    const liste = document.getElementById("listeParties");
    liste.innerHTML = "";

    data.forEach(partie => {
        const div = document.createElement("div");

        div.innerHTML = `
            <strong>ID ${partie.id}</strong> |
            résultat : ${partie.resultat} |
            confiance : ${partie.confiance}
            <button onclick="chargerPartie(${partie.id})">
                Charger
            </button>
        `;

        liste.appendChild(div);
    });
}

async function chargerPartie(id) {
    await fetch("/api/charger/" + id);
    chargerPlateau();
}

/* ================================
   INITIALISATION
================================ */

chargerPlateau();