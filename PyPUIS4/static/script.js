let timerIA = null;
let delaiIAActuel = 600;

/* =========================
   VARIABLES REPLAY
========================= */

let replayCoups = [];
let replayIndex = 0;


/* =========================
   CHARGER PLATEAU
========================= */

async function chargerPlateau() {

    const res = await fetch("/api/plateau");
    const data = await res.json();

    const plateauDiv = document.getElementById("plateau");
    plateauDiv.innerHTML = "";

    const nbColonnes = data.plateau[0].length;

    plateauDiv.style.display = "grid";
    plateauDiv.style.gridTemplateColumns = `repeat(${nbColonnes},38px)`;
    plateauDiv.style.gap = "4px";

    data.plateau.forEach(ligne => {

        ligne.forEach((cell,colIndex)=>{

            const div=document.createElement("div");
            div.className="case";

            div.style.width="38px";
            div.style.height="38px";

            if(cell===1){
                div.innerHTML="●";
                div.classList.add("rouge");
            }

            if(cell===2){
                div.innerHTML="●";
                div.classList.add("jaune");
            }

            div.onclick=()=>{
                jouer(colIndex);
            }

            plateauDiv.appendChild(div);

        });

    });

}


/* =========================
   JOUER
========================= */

async function jouer(col){

    await fetch("/api/jouer",{
        method:"POST",
        headers:{
            "Content-Type":"application/json"
        },
        body:JSON.stringify({col:col})
    });

    chargerPlateau();

}


/* =========================
   NOUVELLE PARTIE
========================= */

async function nouvellePartie(){

    await fetch("/api/nouvelle");

    chargerPlateau();

}


/* =========================
   HISTORIQUE
========================= */

async function chargerHistorique(){

    const res=await fetch("/api/historique");
    const data=await res.json();

    const liste=document.getElementById("listeParties");

    liste.innerHTML="";

    data.forEach(partie=>{

        const ligne=document.createElement("tr");

        ligne.innerHTML=`
        <td>${partie.id}</td>
        <td>${partie.date}</td>
        <td>${partie.coups ? partie.coups.length : 0}</td>
        <td>${partie.resultat}</td>
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

function ouvrirHistorique(){

    const zone=document.getElementById("historique");

    if(zone.style.display==="none" || zone.style.display===""){
        zone.style.display="block";
        chargerHistorique();
    }else{
        zone.style.display="none";
    }

}


/* =========================
   CHARGER PARTIE POUR REPLAY
========================= */

async function chargerPartie(id){

    const res=await fetch("/api/charger/"+id);
    const data=await res.json();

    replayCoups=data.coups.split("").map(Number);

    replayIndex=0;

    await nouvellePartie();

}


/* =========================
   REPLAY SUIVANT
========================= */

async function replaySuivant(){

    if(replayIndex>=replayCoups.length) return;

    await jouer(replayCoups[replayIndex]);

    replayIndex++;

}


/* =========================
   REPLAY PRECEDENT
========================= */

async function replayPrecedent(){

    if(replayIndex<=0) return;

    replayIndex--;

    await nouvellePartie();

    for(let i=0;i<replayIndex;i++){
        await jouer(replayCoups[i]);
    }

}


/* =========================
   INITIALISATION
========================= */

chargerPlateau();