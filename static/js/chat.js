// Discussion avec le professeur.
// Rôle : garder l'historique, l'envoyer au serveur, afficher les réponses.

import { element, emettre, ecouter, envoyer, lire as lireApi } from "./api.js";
import { markdownVersHtml } from "./markdown.js";
import { lireReglages, modifierReglage } from "./reglages.js";
import * as voix from "./voix.js";

const conversation = document.getElementById("conversation");
const formulaire = document.getElementById("formulaire");
const champMessage = document.getElementById("message");
const boutonEnvoyer = document.getElementById("bouton-envoyer");
const boutonMicro = document.getElementById("bouton-micro");
const choixMode = document.getElementById("choix-mode");
const boutonNouvelle = document.getElementById("nouvelle-conversation");
const choixInternet = document.getElementById("choix-internet");

// L'API Claude ne retient rien entre deux messages : c'est la page qui garde
// toute la conversation et l'envoie en entier à chaque fois.
// Chaque élément ressemble à : { role: "user" ou "assistant", content: "..." }
let historique = [];
let enCours = false;

// Ajoute une bulle dans la conversation et la renvoie.
// auteur : "eleve", "professeur", "erreur" ou "attente".
function afficherMessage(texte, auteur) {
  const bulle = element("div", "", "message " + auteur);
  if (auteur === "professeur") {
    // Le Markdown est converti de façon sûre (voir markdown.js).
    bulle.innerHTML = markdownVersHtml(texte);
  } else {
    // textContent : le texte est affiché tel quel (protection XSS).
    bulle.textContent = texte;
  }
  conversation.appendChild(bulle);
  conversation.scrollTop = conversation.scrollHeight;
  return bulle;
}

// Message d'accueil (affiché seulement, pas envoyé au professeur).
async function afficherAccueil() {
  const bulle = afficherMessage(
    "Bonjour ! Je suis ton professeur d'informatique. Je ne vais pas faire " +
      "tes exercices à ta place : je vais t'aider à devenir **autonome**.\n\n" +
      "Pose-moi une question, colle ton code, ou choisis un mode en haut.",
    "professeur"
  );
  // Première utilisation (section 38) : proposer l'évaluation diagnostique.
  try {
    const tableau = await lireApi("/api/tableau-de-bord");
    const dejaRencontres = Object.entries(tableau.repartition)
      .filter(([nom]) => nom !== "Non rencontré")
      .reduce((total, [, nombre]) => total + nombre, 0);
    if (tableau.nb_messages === 0 && dejaRencontres === 0) {
      const p = element(
        "p",
        "Première visite ? Je te propose une courte évaluation (15 à 20 questions) " +
          "pour repérer tes points forts et tes lacunes."
      );
      const actions = element("div", "", "actions");
      const bouton = element("button", "Commencer l'évaluation diagnostique");
      bouton.addEventListener("click", () => {
        actions.remove();
        demander("Je voudrais commencer l'évaluation diagnostique.", "diagnostic");
      });
      actions.appendChild(bouton);
      bulle.append(p, actions);
    }
  } catch {
    // Le tableau de bord est indisponible : on garde l'accueil simple.
  }
}

// Envoie un message au professeur et affiche sa réponse.
async function envoyerMessage(texte) {
  if (enCours) return;
  enCours = true;
  boutonEnvoyer.disabled = true;
  voix.arreterLecture();

  afficherMessage(texte, "eleve");
  historique.push({ role: "user", content: texte });
  const attente = afficherMessage("Le professeur réfléchit…", "attente");
  const reglages = lireReglages();

  try {
    const donnees = await envoyer("/chat", {
      historique,
      mode: choixMode.value,
      detail: reglages.detail,
      recherche_web: reglages.rechercheWeb,
    });
    attente.remove();
    afficherMessage(donnees.reponse, "professeur");
    historique.push({ role: "assistant", content: donnees.reponse });
    if (reglages.lectureVocale) voix.lire(donnees.reponse);
    // Prévient la carte 3D et les panneaux que la mémoire a pu changer.
    emettre("memoire-modifiee", donnees.concepts_mis_a_jour);
  } catch (erreur) {
    attente.remove();
    // On retire ton dernier message de l'historique : tu pourras le renvoyer
    // sans créer de doublon.
    historique.pop();
    afficherMessage(erreur.message, "erreur");
  } finally {
    enCours = false;
    boutonEnvoyer.disabled = false;
    champMessage.focus();
  }
}

// Utilisé par les autres panneaux (carte 3D, tableau de bord) :
// change de mode si besoin, puis envoie le message.
function demander(texte, mode) {
  if (mode) choixMode.value = mode;
  envoyerMessage(texte);
}

export async function initialiserChat() {
  // Remplit la liste des modes à partir du serveur (registre app/modes.py).
  try {
    const { modes, par_defaut } = await lireApi("/api/modes");
    for (const mode of modes) {
      const option = element("option", mode.nom);
      option.value = mode.id;
      option.title = mode.description;
      choixMode.appendChild(option);
    }
    choixMode.value = par_defaut;
  } catch (erreur) {
    afficherMessage(erreur.message, "erreur");
  }

  // Interrupteur « Internet » : le même réglage que dans l'onglet Réglages.
  choixInternet.checked = lireReglages().rechercheWeb;
  choixInternet.addEventListener("change", () =>
    modifierReglage("rechercheWeb", choixInternet.checked)
  );
  // Si le réglage change dans l'onglet Réglages, on met la case à jour.
  ecouter("reglage-modifie", () => (choixInternet.checked = lireReglages().rechercheWeb));

  formulaire.addEventListener("submit", (evenement) => {
    // Empêche le comportement par défaut du formulaire (recharger la page).
    evenement.preventDefault();
    const texte = champMessage.value.trim();
    if (texte === "") return;
    champMessage.value = "";
    envoyerMessage(texte);
  });

  // Entrée envoie le message, Maj+Entrée va à la ligne.
  champMessage.addEventListener("keydown", (evenement) => {
    if (evenement.key === "Enter" && !evenement.shiftKey) {
      evenement.preventDefault();
      formulaire.requestSubmit();
    }
  });

  boutonNouvelle.addEventListener("click", () => {
    historique = [];
    conversation.replaceChildren();
    voix.arreterLecture();
    afficherAccueil();
  });

  // Dictée au micro (seulement si autorisée dans les réglages).
  boutonMicro.hidden = !voix.dicteeDisponible;
  boutonMicro.addEventListener("click", () => {
    if (boutonMicro.getAttribute("aria-pressed") === "true") {
      voix.arreterDictee();
      return;
    }
    if (!lireReglages().dictee) {
      afficherMessage(
        "La dictée est désactivée. Active-la dans l'onglet Réglages " +
          "(l'audio est alors transcrit par le service vocal de ton navigateur).",
        "erreur"
      );
      return;
    }
    boutonMicro.setAttribute("aria-pressed", "true");
    voix.demarrerDictee(
      (texte) => {
        champMessage.value = (champMessage.value + " " + texte).trim();
      },
      () => boutonMicro.setAttribute("aria-pressed", "false")
    );
  });

  ecouter("demander", ({ texte, mode }) => demander(texte, mode));
  afficherAccueil();
}
