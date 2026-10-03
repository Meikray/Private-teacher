// Carte des connaissances : fiche d'un concept, légende, et solution de
// secours sans 3D. La scène 3D elle-même est dans carte3d.js, chargée
// « dynamiquement » : si Three.js ne se charge pas (pas d'Internet, carte
// graphique trop ancienne...), on affiche une liste à la place.

import { couleurEtat, element, emettre, ecouter, lire } from "./api.js";

const conteneur = document.getElementById("scene-3d");
const legende = document.getElementById("legende");
const secours = document.getElementById("secours-3d");
const fiche = document.getElementById("fiche-concept");
const panneau = document.getElementById("panneau-carte");

let donnees = null; // { domaines, etats, concepts }
let scene = null; // objet renvoyé par creerScene3D (ou null sans 3D)
let conceptAffiche = null;

const info = element("div", "", "info-survol");
info.hidden = true;
panneau.appendChild(info);

function nomDomaine(id) {
  return donnees.domaines.find((d) => d.id === id)?.nom || id;
}

function afficherLegende() {
  legende.replaceChildren(element("strong", "États de maîtrise"));
  donnees.etats.forEach((nom, etat) => {
    const ligne = element("span");
    const pastille = element("span", "", "pastille");
    pastille.style.background = couleurEtat(etat);
    ligne.append(pastille, nom);
    legende.appendChild(ligne);
  });
}

function afficherFiche(concept) {
  conceptAffiche = concept;
  if (!concept) {
    fiche.hidden = true;
    return;
  }
  const parId = new Map(donnees.concepts.map((c) => [c.id, c]));
  document.getElementById("fiche-nom").textContent = concept.nom;
  document.getElementById("fiche-domaine").textContent = nomDomaine(concept.domaine);
  document.getElementById("fiche-etat").textContent = concept.nom_etat;
  document.getElementById("fiche-remarque").textContent = concept.remarque || "";
  const prerequis = concept.prerequis.map((id) => {
    const p = parId.get(id);
    return `${p.nom} (${p.nom_etat})`;
  });
  document.getElementById("fiche-prerequis").textContent = prerequis.length
    ? "Prérequis : " + prerequis.join(", ")
    : "Aucun prérequis : c'est un point de départ.";
  fiche.hidden = false;
}

function survol(concept, evenement) {
  if (!concept) {
    info.hidden = true;
    return;
  }
  const cadre = panneau.getBoundingClientRect();
  info.textContent = `${concept.nom} — ${concept.nom_etat}`;
  info.style.left = evenement.clientX - cadre.left + "px";
  info.style.top = evenement.clientY - cadre.top + "px";
  info.hidden = false;
}

// Solution de secours : la carte sous forme de liste, domaine par domaine.
function afficherSecours(raison) {
  secours.replaceChildren(
    element("h2", "Carte des connaissances"),
    element("p", raison, "note")
  );
  for (const domaine of donnees.domaines) {
    secours.appendChild(element("h3", domaine.nom));
    const liste = element("ul", "", "liste");
    for (const concept of donnees.concepts.filter((c) => c.domaine === domaine.id)) {
      const li = element("li");
      const infos = element("div", "", "infos");
      const pastille = element("span", "", "pastille");
      pastille.style.background = couleurEtat(concept.etat);
      infos.append(pastille, " " + concept.nom);
      const bouton = element("button", "Voir", "secondaire");
      bouton.addEventListener("click", () => afficherFiche(concept));
      li.append(infos, element("span", concept.nom_etat, "petit"), bouton);
      liste.appendChild(li);
    }
    secours.appendChild(liste);
  }
  secours.hidden = false;
  legende.hidden = true;
}

async function rafraichir(idsModifies = []) {
  donnees = await lire("/api/parcours");
  if (scene) {
    scene.mettreAJour(donnees.concepts, idsModifies);
  } else if (!secours.hidden) {
    afficherSecours(secours.querySelector(".note")?.textContent || "");
  }
  if (conceptAffiche) {
    afficherFiche(donnees.concepts.find((c) => c.id === conceptAffiche.id));
  }
}

export async function initialiserCarte() {
  donnees = await lire("/api/parcours");
  afficherLegende();

  document.getElementById("fermer-fiche").addEventListener("click", () => {
    afficherFiche(null);
    scene?.selectionner(null);
  });
  document.getElementById("fiche-apprendre").addEventListener("click", () => {
    emettre("demander", {
      texte: `Fais-moi un cours sur : ${conceptAffiche.nom} (${nomDomaine(conceptAffiche.domaine)}).`,
      mode: "professeur",
    });
  });
  document.getElementById("fiche-reviser").addEventListener("click", () => {
    emettre("demander", {
      texte: `Fais-moi réviser : ${conceptAffiche.nom}, avec un petit exercice.`,
      mode: "revision",
    });
  });

  // La mémoire a changé (réponse du professeur, modification manuelle...).
  ecouter("memoire-modifiee", (ids) => rafraichir(ids || []).catch(() => {}));

  // WebGL disponible ? (WebGL = la 3D dans le navigateur.)
  const testWebgl = document.createElement("canvas");
  if (!(testWebgl.getContext("webgl2") || testWebgl.getContext("webgl"))) {
    afficherSecours("Ton navigateur ne permet pas l'affichage 3D (WebGL) : voici la carte en liste.");
    return;
  }

  try {
    const { creerScene3D } = await import("./carte3d.js");
    scene = creerScene3D(conteneur, donnees, {
      surSelection: afficherFiche,
      surSurvol: survol,
    });
  } catch (erreur) {
    console.error(erreur);
    afficherSecours(
      "La bibliothèque 3D n'a pas pu être chargée (connexion Internet nécessaire " +
        "la première fois) : voici la carte en liste."
    );
  }
}
