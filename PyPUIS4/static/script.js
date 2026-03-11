let timerIA = null;
let delaiIAActuel = 600;

/* ================================
   CHARGER PLATEAU
================================ */

async function chargerPlateau() {

    const res = await fetch("/api/plateau");
    const data = await res.json();

    const plateauDiv = document.getElementById("plateau");
    plateauDiv.innerHTML = "";

    const nbColonnes = data.plateau[0].length;

    plateauDiv.style.display = "grid";
    plateauDiv.style.gridTemplateColumns = `repeat(${nbColonnes}, 38px)`;
    plateauDiv.style.gap = "4px";
    plateauDiv.style.justifyContent = "center";

    data.plateau.forEach((ligne) => {

        ligne.forEach((cell, colIndex) => {

            const div = document.createElement("div");
            div.className = "case";

            div.style.width = "38px";
            div.style.height = "38px";

            if (cell === 1) {
                div.innerHTML = "●";
                div.classList.add("rouge");
            }

            if (cell === 2) {
                div.innerHTML = "●";
                div.classList.add("jaune");
            }

            div.onclick = () => {
                if (!data.resultat) {
                    jouer(colIndex);
                }
            };

            plateauDiv.appendChild(div);

        });

    });

    const info = document.getElementById("info");

    if (data.resultat) {
        info.innerHTML = "Partie terminée : " + data.resultat;
    }
    else {
        info.innerHTML = "Joueur : " + (data.joueur === 1 ? "Rouge" : "Jaune");
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
   HISTORIQUE
================================ */

async function chargerHistorique() {

    const res = await fetch("/api/historique");
    const data = await res.json();

    const liste = document.getElementById("listeParties");

    if (!liste) return;

    liste.innerHTML = "";

    data.forEach(partie => {

        let resultatTexte = "Match nul";

        if (partie.resultat === "rouge")
            resultatTexte = "🔴 Rouge gagne";

        if (partie.resultat === "jaune")
            resultatTexte = "🟡 Jaune gagne";

        const ligne = document.createElement("tr");

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
/* ================================
   FONCTIONS UTILISÉES PAR HTML
   (pour éviter les erreurs console)
================================ */

function replayPrecedent(){
    console.log("Replay précédent (désactivé)");
}

function replaySuivant(){
    console.log("Replay suivant (désactivé)");
}

function replayAuto(){
    console.log("Replay auto (désactivé)");
}

async function changerMode(){

    const modeSelect = document.getElementById("modeSelect");

    if(!modeSelect) return;

    const mode = parseInt(modeSelect.value);

    await fetch("/api/mode",{
        method:"POST",
        headers:{
            "Content-Type":"application/json"
        },
        body:JSON.stringify({mode:mode})
    });

    chargerPlateau();
}