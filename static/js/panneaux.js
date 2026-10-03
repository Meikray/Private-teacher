// Panneaux : onglets, tableau de bord, mémoire, documents, réglages.

import {
  couleurEtat, element, emettre, ecouter, envoyer, lire, requete, supprimer,
} from "./api.js";
import { lireReglages, modifierReglage } from "./reglages.js";
import * as voix from "./voix.js";

const panneaux = {
  carte: document.getElementById("panneau-carte"),
  tableau: document.getElementById("panneau-tableau"),
  memoire: document.getElementById("panneau-memoire"),
  documents: document.getElementById("panneau-documents"),
  reglages: document.getElementById("panneau-reglages"),
};

// Chaque panneau a une fonction d'affichage (appelée à l'ouverture).
const afficheurs = {
  tableau: afficherTableau,
  memoire: afficherMemoire,
  documents: afficherDocuments,
  reglages: afficherReglages,
};

let ouvert = "carte";

function ouvrir(nom) {
  ouvert = nom;
  for (const [cle, panneau] of Object.entries(panneaux)) {
    panneau.hidden = cle !== nom;
    panneau.classList.toggle("actif", cle === nom);
  }
  document.querySelectorAll(".onglet").forEach((onglet) => {
    onglet.setAttribute("aria-selected", String(onglet.dataset.panneau === nom));
  });
  afficheurs[nom]?.().catch((erreur) => {
    panneaux[nom].replaceChildren(element("p", erreur.message, "note"));
  });
}

// "2026-10-03T22:34:50" -> "03/10/2026 à 22:34"
function dateLisible(iso) {
  const [jour, heure] = iso.split("T");
  return jour.split("-").reverse().join("/") + (heure ? " à " + heure.slice(0, 5) : "");
}

// Petite fonction pour créer une tuile du tableau de bord.
function tuile(valeur, libelle) {
  const t = element("div", "", "tuile");
  t.append(element("div", String(valeur), "valeur"), element("div", libelle, "libelle"));
  return t;
}

// Liste simple de concepts avec un bouton d'action.
function listeConcepts(concepts, texteBouton, message, mode) {
  if (!concepts.length) return element("p", "Rien pour l'instant.", "note");
  const liste = element("ul", "", "liste");
  for (const concept of concepts) {
    const li = element("li");
    const infos = element("div", "", "infos");
    infos.append(element("div", concept.nom), element("div", concept.nom_etat, "petit"));
    li.appendChild(infos);
    if (texteBouton) {
      const bouton = element("button", texteBouton, "secondaire");
      bouton.addEventListener("click", () =>
        emettre("demander", { texte: message(concept), mode })
      );
      li.appendChild(bouton);
    }
    liste.appendChild(li);
  }
  return liste;
}

// ---------------------------------------------------------------------------
// Tableau de bord (section 31) : pas seulement un pourcentage.
// ---------------------------------------------------------------------------

async function afficherTableau() {
  const t = await lire("/api/tableau-de-bord");
  const p = panneaux.tableau;
  p.replaceChildren(element("h2", "Tableau de bord"));

  const tuiles = element("div", "", "tuiles");
  tuiles.append(
    tuile(t.nb_messages, "questions posées"),
    tuile(t.nb_exercices, "exercices travaillés"),
    tuile(t.nb_reussis_seul, "réussis sans aide"),
    tuile(t.jours_actifs, "jours d'étude")
  );
  p.appendChild(tuiles);

  // Niveau d'assistance (section 23 : détection de dépendance à l'IA).
  p.appendChild(element("h3", "Ton autonomie"));
  const encadre = element("div", "", "encadre");
  encadre.append(
    element("strong", `Palier actuel : ${t.assistance.nom}`),
    element("div", `Le professeur te propose : ${t.assistance.explication}.`)
  );
  if (t.assistance.palier < 3) {
    encadre.appendChild(element(
      "div",
      "Réussis des exercices avec moins d'indices pour passer au palier suivant."
    ));
  }
  if (t.assistance.part_demandes_solution >= 0.5) {
    encadre.appendChild(element(
      "div",
      "Tu demandes souvent la solution directement : essaie d'abord, même si c'est faux. " +
        "Une erreur est une information !"
    ));
  }
  p.appendChild(encadre);

  // Répartition des concepts par état (barre empilée + légende chiffrée).
  p.appendChild(element("h3", "Tes connaissances"));
  const total = Object.values(t.repartition).reduce((a, b) => a + b, 0);
  const barre = element("div", "", "barre-etats");
  barre.setAttribute("role", "img");
  barre.setAttribute(
    "aria-label",
    Object.entries(t.repartition).map(([nom, n]) => `${nom} : ${n}`).join(", ")
  );
  const legende = element("div", "", "legende-etats");
  Object.entries(t.repartition).forEach(([nom, nombre], etat) => {
    if (nombre) {
      const segment = element("span");
      segment.style.width = (nombre / total) * 100 + "%";
      segment.style.background = couleurEtat(etat);
      segment.title = `${nom} : ${nombre}`;
      barre.appendChild(segment);
    }
    const item = element("span");
    const pastille = element("span", "", "pastille");
    pastille.style.background = couleurEtat(etat);
    item.append(pastille, `${nom} : ${nombre}`);
    legende.appendChild(item);
  });
  p.append(barre, legende);

  p.appendChild(element("h3", "Révisions à faire"));
  p.appendChild(listeConcepts(
    t.revisions, "Réviser",
    (c) => `Fais-moi réviser : ${c.nom}, avec un petit exercice de 3 minutes.`, "revision"
  ));

  p.appendChild(element("h3", "Concepts fragiles"));
  p.appendChild(listeConcepts(
    t.fragiles, "Consolider",
    (c) => `Je veux consolider : ${c.nom}. Vérifie ce que j'ai compris.`, "socratique"
  ));

  p.appendChild(element("h3", "Concepts maîtrisés"));
  p.appendChild(listeConcepts(t.maitrises));

  p.appendChild(element("h3", "Erreurs récentes"));
  if (t.erreurs_recentes.length) {
    const liste = element("ul", "", "liste");
    for (const e of t.erreurs_recentes) {
      const li = element("li");
      const infos = element("div", "", "infos");
      infos.append(element("div", e.description), element("div", e.nom_concept, "petit"));
      li.appendChild(infos);
      liste.appendChild(li);
    }
    p.appendChild(liste);
  } else {
    p.appendChild(element("p", "Aucune erreur enregistrée.", "note"));
  }
}

// ---------------------------------------------------------------------------
// Ma mémoire (section 20) : voir, corriger, supprimer, réinitialiser.
// ---------------------------------------------------------------------------

async function afficherMemoire() {
  const [profil, parcours, { erreurs }] = await Promise.all([
    lire("/api/profil"), lire("/api/parcours"), lire("/api/erreurs"),
  ]);
  const p = panneaux.memoire;
  p.replaceChildren(
    element("h2", "Ma mémoire"),
    element(
      "p",
      "Tout ce que le professeur sait de toi est ici, stocké uniquement sur ton " +
        "ordinateur (fichier data/professeur.db). Tu peux tout corriger ou effacer.",
      "note"
    )
  );

  // Profil.
  p.appendChild(element("h3", "Mon profil"));
  const formulaire = element("form", "", "formulaire-grille");
  const champs = {
    objectifs: "Mes objectifs",
    langage_etudie: "Langage étudié en ce moment",
    niveau_estime: "Mon niveau (selon moi)",
    cours_actuels: "Mes cours actuels",
  };
  for (const [cle, libelle] of Object.entries(champs)) {
    const label = element("label", libelle);
    const champ = element("input");
    champ.type = "text";
    champ.name = cle;
    champ.value = profil[cle] || "";
    label.appendChild(champ);
    formulaire.appendChild(label);
  }
  const statut = element("span", "", "statut");
  const ligne = element("div", "", "ligne");
  ligne.append(element("button", "Enregistrer le profil"), statut);
  formulaire.appendChild(ligne);
  formulaire.addEventListener("submit", async (evenement) => {
    evenement.preventDefault();
    const valeurs = Object.fromEntries(new FormData(formulaire));
    await envoyer("/api/profil", valeurs, "PUT");
    statut.textContent = "Profil enregistré.";
  });
  p.appendChild(formulaire);

  // Concepts : seulement ceux déjà rencontrés (ou tous, sur demande).
  p.appendChild(element("h3", "Mes concepts"));
  const toutAfficher = element("label", "", "note");
  const caseTout = element("input");
  caseTout.type = "checkbox";
  toutAfficher.append(caseTout, " Afficher aussi les concepts non rencontrés");
  p.appendChild(toutAfficher);
  const listeConceptsEl = element("ul", "", "liste");
  p.appendChild(listeConceptsEl);

  const dessinerConcepts = () => {
    listeConceptsEl.replaceChildren();
    const concepts = parcours.concepts.filter((c) => caseTout.checked || c.etat > 0);
    if (!concepts.length) {
      listeConceptsEl.appendChild(element("p", "Aucun concept enregistré pour l'instant.", "note"));
    }
    for (const concept of concepts) {
      const li = element("li");
      const infos = element("div", "", "infos");
      infos.append(element("div", concept.nom), element("div", concept.remarque, "petit"));
      const choix = element("select");
      choix.setAttribute("aria-label", "État de " + concept.nom);
      parcours.etats.forEach((nom, etat) => {
        const option = element("option", nom);
        option.value = etat;
        option.selected = etat === concept.etat;
        choix.appendChild(option);
      });
      choix.addEventListener("change", async () => {
        await envoyer(
          `/api/concepts/${concept.id}`,
          { etat: Number(choix.value), remarque: concept.remarque },
          "PUT"
        );
        concept.etat = Number(choix.value);
        emettre("memoire-modifiee", [concept.id]);
      });
      const oublier = element("button", "Oublier", "secondaire");
      oublier.addEventListener("click", async () => {
        await supprimer(`/api/concepts/${concept.id}`);
        concept.etat = 0;
        concept.remarque = "";
        emettre("memoire-modifiee", [concept.id]);
        dessinerConcepts();
      });
      li.append(infos, choix, oublier);
      listeConceptsEl.appendChild(li);
    }
  };
  caseTout.addEventListener("change", dessinerConcepts);
  dessinerConcepts();

  // Erreurs fréquentes.
  p.appendChild(element("h3", "Mes erreurs enregistrées"));
  const listeErreurs = element("ul", "", "liste");
  if (!erreurs.length) p.appendChild(element("p", "Aucune erreur enregistrée.", "note"));
  for (const e of erreurs) {
    const li = element("li");
    const infos = element("div", "", "infos");
    infos.append(element("div", e.description), element("div", `${e.nom_concept} · ${dateLisible(e.date)}`, "petit"));
    const bouton = element("button", "Supprimer", "secondaire");
    bouton.addEventListener("click", async () => {
      await supprimer(`/api/erreurs/${e.id}`);
      li.remove();
    });
    li.append(infos, bouton);
    listeErreurs.appendChild(li);
  }
  p.appendChild(listeErreurs);

  // Réinitialisation complète.
  p.appendChild(element("h3", "Tout recommencer"));
  const reinit = element("button", "Réinitialiser ma mémoire", "danger");
  reinit.addEventListener("click", async () => {
    if (!confirm("Effacer tout ton profil pédagogique ? Cette action est définitive.")) return;
    await requete("/api/memoire/reinitialiser", { method: "POST" });
    emettre("memoire-modifiee", []);
    afficherMemoire();
  });
  p.appendChild(reinit);
}

// ---------------------------------------------------------------------------
// Documents de cours (section 16)
// ---------------------------------------------------------------------------

async function afficherDocuments(messageStatut = "") {
  const { documents, extensions } = await lire("/api/documents");
  const p = panneaux.documents;
  p.replaceChildren(
    element("h2", "Mes documents de cours"),
    element(
      "p",
      "Importe tes cours, notes ou exercices (PDF, texte, Markdown, code). Ils restent " +
        "sur ton ordinateur (dossier data/documents).",
      "note"
    )
  );
  const avertissement = element("div", "", "encadre");
  avertissement.textContent =
    "À savoir : quand tu poses une question, les passages de tes documents qui " +
    "s'y rapportent sont envoyés à Claude (Anthropic) avec ta question, pour que " +
    "le professeur s'appuie sur ton cours. N'importe pas de documents confidentiels.";
  p.appendChild(avertissement);

  const ligne = element("div", "", "ligne");
  ligne.style.marginTop = "12px";
  const champ = element("input");
  champ.type = "file";
  champ.accept = extensions.join(",");
  const statut = element("span", messageStatut, "statut");
  ligne.append(champ, statut);
  p.appendChild(ligne);

  champ.addEventListener("change", async () => {
    const fichier = champ.files[0];
    if (!fichier) return;
    const formulaire = new FormData();
    formulaire.append("fichier", fichier);
    statut.textContent = "Import en cours…";
    try {
      const info = await requete("/api/documents", { method: "POST", body: formulaire });
      afficherDocuments(`« ${info.nom} » importé (${info.nb_caracteres} caractères).`);
    } catch (erreur) {
      statut.textContent = erreur.message;
    }
  });

  p.appendChild(element("h3", "Documents importés"));
  if (!documents.length) {
    p.appendChild(element("p", "Aucun document pour l'instant.", "note"));
    return;
  }
  const liste = element("ul", "", "liste");
  for (const d of documents) {
    const li = element("li");
    const infos = element("div", "", "infos");
    infos.append(element("div", d.nom), element("div", `${d.nb_caracteres} caractères · ${dateLisible(d.date)}`, "petit"));
    const fiche = element("button", "Fiche de révision", "secondaire");
    fiche.addEventListener("click", () => emettre("demander", {
      texte: `À partir de mon document « ${d.nom} », fais-moi une fiche de révision : ` +
        "concepts importants, vocabulaire, exemples, et un petit quiz.",
      mode: "professeur",
    }));
    const bouton = element("button", "Supprimer", "secondaire");
    bouton.addEventListener("click", async () => {
      await supprimer(`/api/documents/${d.id}`);
      afficherDocuments();
    });
    li.append(infos, fiche, bouton);
    liste.appendChild(li);
  }
  p.appendChild(liste);
}

// ---------------------------------------------------------------------------
// Réglages : détail, recherche web, voix.
// ---------------------------------------------------------------------------

function caseACocher(nom, libelle, note) {
  const label = element("label", "", "case");
  const champ = element("input");
  champ.type = "checkbox";
  champ.checked = Boolean(lireReglages()[nom]);
  champ.addEventListener("change", () => modifierReglage(nom, champ.checked));
  label.append(champ, " " + libelle);
  const bloc = element("div");
  bloc.append(label);
  if (note) bloc.appendChild(element("div", note, "note"));
  return bloc;
}

async function afficherReglages() {
  const reglages = lireReglages();
  const p = panneaux.reglages;
  p.replaceChildren(
    element("h2", "Réglages"),
    element("p", "Ces réglages restent dans ton navigateur.", "note")
  );
  const grille = element("div", "", "formulaire-grille");

  // Niveau de détail des réponses.
  const labelDetail = element("label", "Niveau de détail des réponses");
  const detail = element("select");
  for (const [valeur, nom] of [["court", "Court"], ["normal", "Normal"], ["detaille", "Détaillé"]]) {
    const option = element("option", nom);
    option.value = valeur;
    option.selected = reglages.detail === valeur;
    detail.appendChild(option);
  }
  detail.addEventListener("change", () => modifierReglage("detail", detail.value));
  labelDetail.appendChild(detail);
  grille.appendChild(labelDetail);

  grille.appendChild(caseACocher(
    "rechercheWeb",
    "Autoriser le professeur à chercher sur Internet",
    "Utile pour les technologies récentes ou la documentation officielle. " +
      "Chaque recherche est facturée en plus par Anthropic (3 au maximum par question)."
  ));

  p.appendChild(grille);
  p.appendChild(element("h3", "Voix"));
  const grilleVoix = element("div", "", "formulaire-grille");

  if (voix.lectureDisponible) {
    grilleVoix.appendChild(caseACocher("lectureVocale", "Lire les réponses à voix haute"));

    const labelVoix = element("label", "Voix");
    const choixVoix = element("select");
    const remplirVoix = () => {
      choixVoix.replaceChildren(element("option", "Voix par défaut"));
      choixVoix.firstChild.value = "";
      for (const v of voix.voixDisponibles()) {
        const option = element("option", `${v.name} (${v.lang})`);
        option.value = v.name;
        option.selected = v.name === lireReglages().voix;
        choixVoix.appendChild(option);
      }
    };
    remplirVoix();
    // Les voix se chargent parfois après la page.
    speechSynthesis.addEventListener("voiceschanged", remplirVoix);
    choixVoix.addEventListener("change", () => modifierReglage("voix", choixVoix.value));
    labelVoix.appendChild(choixVoix);
    grilleVoix.appendChild(labelVoix);

    const labelVitesse = element("label", "Vitesse de lecture");
    const vitesse = element("input");
    vitesse.type = "range";
    vitesse.min = "0.6";
    vitesse.max = "1.4";
    vitesse.step = "0.05";
    vitesse.value = reglages.vitesse;
    vitesse.addEventListener("change", () => modifierReglage("vitesse", Number(vitesse.value)));
    labelVitesse.appendChild(vitesse);
    grilleVoix.appendChild(labelVitesse);

    const essai = element("button", "Tester la voix", "secondaire");
    essai.type = "button";
    essai.addEventListener("click", () =>
      voix.lire("Bonjour ! Voici comment je parle. Est-ce que la vitesse te convient ?")
    );
    grilleVoix.appendChild(essai);
  } else {
    grilleVoix.appendChild(element("p", "La lecture vocale n'est pas disponible dans ce navigateur.", "note"));
  }

  const labelLangue = element("label", "Langue de la voix");
  const langue = element("select");
  for (const [valeur, nom] of [["fr-FR", "Français"], ["en-US", "Anglais"]]) {
    const option = element("option", nom);
    option.value = valeur;
    option.selected = reglages.langue === valeur;
    langue.appendChild(option);
  }
  langue.addEventListener("change", () => {
    modifierReglage("langue", langue.value);
    afficherReglages();
  });
  labelLangue.appendChild(langue);
  grilleVoix.appendChild(labelLangue);

  if (voix.dicteeDisponible) {
    grilleVoix.appendChild(caseACocher(
      "dictee",
      "Autoriser la dictée au micro (bouton 🎤)",
      "Attention : dans Chrome et Edge, ta voix est envoyée au service de " +
        "reconnaissance vocale du navigateur (Google ou Microsoft) pour être transcrite."
    ));
  } else {
    grilleVoix.appendChild(element("p", "La dictée n'est pas disponible dans ce navigateur (essaie Chrome ou Edge).", "note"));
  }
  p.appendChild(grilleVoix);
}

export function initialiserPanneaux() {
  document.querySelectorAll(".onglet").forEach((onglet) => {
    onglet.addEventListener("click", () => ouvrir(onglet.dataset.panneau));
  });
  // Quand la mémoire change, on rafraîchit le tableau de bord s'il est ouvert.
  ecouter("memoire-modifiee", () => {
    if (ouvert === "tableau") afficherTableau().catch(() => {});
  });
  // Un bouton « Réviser » ou « Apprendre » : on revient à la carte pour
  // voir la progression s'animer.
  ecouter("demander", () => {
    if (ouvert !== "carte" && ouvert !== "tableau") ouvrir("carte");
  });
}
