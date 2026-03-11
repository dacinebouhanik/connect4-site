let timerIA = null;
let delaiIAActuel = 600;

/* ================================
   REPLAY HISTORIQUE
================================ */

let replayCoups = [];
let replayIndex = 0;
let replayActif = false;


/* ================================
   CHARGER PLATEAU NORMAL
================================ */

async function chargerPlateau() {

    if (replayActif) return;

    const res = await fetch("/api/plateau");
    const data = await res.json();

    const modeSelect = document.getElementById("modeSelect");
    if (modeSelect) modeSelect.value = String(data.mode);

    const zoneIA = document.getElementById("zoneIA");
    if (zoneIA) {
        zoneIA.style.display = (data.mode === 0 || data.mode === 1) ? "block" : "none";
    }

    afficherPlateau(data.plateau, data);

    const info = document.getElementById("info");

    if (data.resultat) {
        info.innerHTML = "🏆 Partie terminée : " + data.resultat;
    } else {
        info.innerHTML = "Tour : " + (data.joueur === 1 ? "🔴 Rouge" : "🟡 Jaune");
    }

    afficherScoresSousColonnes(data.scores);

    if (data.mode === 0 && !data.resultat) demarrerIA();
    else stopperIA();
}


/* ================================
   AFFICHER PLATEAU
================================ */

function afficherPlateau(plateau, data = null){

    const plateauDiv = document.getElementById("plateau");
    plateauDiv.innerHTML = "";

    const nbColonnes = plateau[0].length;

    plateauDiv.style.display = "grid";
    plateauDiv.style.gridTemplateColumns = `repeat(${nbColonnes}, 50px)`;
    plateauDiv.style.gap = "6px";
    plateauDiv.style.justifyContent = "center";

    plateau.forEach((ligne,rowIndex) => {

        ligne.forEach((cell,colIndex) => {

            const div = document.createElement("div");
            div.className = "case";

            if(cell === 1) div.classList.add("rouge");
            if(cell === 2) div.classList.add("jaune");

            if(data && !data.resultat && data.mode !== 0){
                div.onclick = () => jouer(colIndex);
            }

            plateauDiv.appendChild(div);

        });

    });

}


/* ================================
   JOUER
================================ */

async function jouer(col){

    await fetch("/api/jouer",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({col:col})
    });

    chargerPlateau();

}


/* ================================
   NOUVELLE PARTIE
================================ */

async function nouvellePartie(){

    replayActif = false;

    const ctrl = document.getElementById("replayControls");
    if(ctrl) ctrl.remove();

    await fetch("/api/nouvelle");

    chargerPlateau();

}


/* ================================
   ANNULER COUP
================================ */

async function annulerCoup(){

    await fetch("/api/annuler");

    chargerPlateau();

}


/* ================================
   CHANGER MODE
================================ */

async function changerMode(){

    const mode = parseInt(document.getElementById("modeSelect").value);

    await fetch("/api/mode",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({mode:mode})
    });

    chargerPlateau();
}


/* ================================
   IA VS IA
================================ */

function demarrerIA(){

    if(timerIA !== null) return;

    const d = parseInt(delaiIAActuel) || 600;

    timerIA = setInterval(async ()=>{

        await fetch("/api/ia_step",{method:"POST"});
        await chargerPlateau();

    },d);

}

function stopperIA(){

    if(timerIA !== null){

        clearInterval(timerIA);
        timerIA = null;

    }

}


/* ================================
   HISTORIQUE
================================ */

async function ouvrirHistorique(){

    document.getElementById("modalHistorique").style.display="block";
    chargerHistorique();

}


async function chargerHistorique(){

    const res = await fetch("/api/historique");
    const data = await res.json();

    const liste = document.getElementById("listeParties");
    liste.innerHTML="";

    data.forEach(partie=>{

        const tr=document.createElement("tr");

        const couleur = partie.resultat === "rouge"
            ? "style='color:#ef4444;font-weight:bold'"
            : "style='color:#facc15;font-weight:bold'";

        tr.innerHTML=`

        <td>${partie.id}</td>
        <td>${partie.date}</td>
        <td style="font-family:monospace">${partie.coups}</td>
        <td ${couleur}>${partie.resultat}</td>
        <td>${partie.statut}</td>
        <td>
        <button onclick="chargerPartie(${partie.id},'${partie.coups}')">
        Charger
        </button>
        </td>
        `;

        liste.appendChild(tr);

    });

}


function fermerHistorique(){
    document.getElementById("modalHistorique").style.display="none";
}


/* ================================
   REPLAY HISTORIQUE
================================ */

function chargerPartie(id,coups){

    fermerHistorique();

    replayActif = true;
    replayCoups = coups.split("").map(Number);
    replayIndex = 0;

    afficherReplay();
    afficherControlesReplay();

}


function afficherReplay(){

    const lignes = 6;
    const colonnes = 9;

    let plateau = [];

    for(let i=0;i<lignes;i++){
        plateau.push(new Array(colonnes).fill(0));
    }

    let joueur = 1;

    for(let i=0;i<replayIndex;i++){

        let col = replayCoups[i]-1;

        for(let row=lignes-1;row>=0;row--){

            if(plateau[row][col]===0){

                plateau[row][col]=joueur;
                break;

            }

        }

        joueur = joueur===1 ? 2 : 1;

    }

    afficherPlateau(plateau);

}


/* ================================
   CONTROLES REPLAY
================================ */

function afficherControlesReplay(){

    let div=document.getElementById("replayControls");

    if(!div){

        div=document.createElement("div");

        div.id="replayControls";
        div.style.marginTop="20px";

        div.innerHTML=`

        <button onclick="replayPrecedent()">◀ Précédent</button>
        <button onclick="replaySuivant()">Suivant ▶</button>
        <button onclick="quitterReplay()">Quitter replay</button>

        `;

        document.getElementById("plateau").after(div);

    }

}


function replaySuivant(){

    if(replayIndex < replayCoups.length){
        replayIndex++;
        afficherReplay();
    }

}


function replayPrecedent(){

    if(replayIndex>0){
        replayIndex--;
        afficherReplay();
    }

}


function quitterReplay(){

    replayActif=false;

    const ctrl = document.getElementById("replayControls");
    if(ctrl) ctrl.remove();

    chargerPlateau();

}


/* ================================
   SCORES MINIMAX
================================ */

function afficherScoresSousColonnes(scores){

    const ancien=document.getElementById("scoresMinimax");
    if(ancien) ancien.remove();

    if(!scores) return;

    const nbColonnes=Object.keys(scores).length;

    const div=document.createElement("div");

    div.id="scoresMinimax";
    div.style.display="grid";
    div.style.gridTemplateColumns=`repeat(${nbColonnes},50px)`;
    div.style.gap="6px";
    div.style.marginTop="8px";
    div.style.justifyContent="center";

    for(let i=0;i<nbColonnes;i++){

        const cell=document.createElement("div");

        cell.style.textAlign="center";
        cell.style.fontSize="14px";
        cell.style.color="#22c55e";
        cell.style.fontWeight="bold";

        cell.innerText=scores[i]!==undefined?scores[i]:"";

        div.appendChild(cell);

    }

    document.getElementById("plateau").after(div);

}


/* ================================
   INITIALISATION
================================ */

chargerPlateau();