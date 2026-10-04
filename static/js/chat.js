// Discussion avec le professeur.
// Rôle : garder l'historique, l'envoyer au serveur, afficher les réponses.

import { element, emettre, ecouter, lire as lireApi } from "./api.js";
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

// Lit la réponse « diffusée » par le serveur (/chat/flux) : une ligne JSON
// par événement. Appelle surEvenement(evenement) pour chacun.
async function lireFlux(reponse, surEvenement) {
  const lecteur = reponse.body.getReader();
  const decodeur = new TextDecoder();
  let reste = ""; // morceau de ligne pas encore complet
  for (;;) {
    const { value, done } = await lecteur.read();
    if (done) break;
    reste += decodeur.decode(value, { stream: true });
    const lignes = reste.split("\n");
    reste = lignes.pop();
    for (const ligne of lignes) {
      if (ligne.trim()) surEvenement(JSON.parse(ligne));
    }
  }
  if (reste.trim()) surEvenement(JSON.parse(reste));
}

// Envoie un message au professeur et affiche sa réponse AU FUR ET À MESURE.
async function envoyerMessage(texte) {
  if (enCours) return;
  enCours = true;
  boutonEnvoyer.disabled = true;
  voix.arreterLecture();

  afficherMessage(texte, "eleve");
  historique.push({ role: "user", content: texte });
  const reglages = lireReglages();

  // Bulle d'attente avec un compteur de secondes : on voit que ça avance.
  const attente = afficherMessage("Le professeur réfléchit… 0 s", "attente");
  const debut = Date.now();
  let statut = "Le professeur réfléchit…";
  const minuteur = setInterval(() => {
    attente.textContent = `${statut} ${Math.round((Date.now() - debut) / 1000)} s`;
  }, 1000);

  let bulle = null; // bulle de la réponse, créée au premier morceau de texte
  let reponseTexte = "";
  let fin = null;
  let erreurFlux = null;

  try {
    const reponse = await fetch("/chat/flux", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        historique,
        mode: choixMode.value,
        detail: reglages.detail,
        recherche_web: reglages.rechercheWeb,
      }),
    });
    if (!reponse.ok) {
      const erreur = await reponse.json().catch(() => ({}));
      throw new Error(typeof erreur.detail === "string" ? erreur.detail : "Erreur du serveur.");
    }

    await lireFlux(reponse, (evenement) => {
      if (evenement.type === "texte") {
        if (!bulle) {
          bulle = afficherMessage("", "professeur");
          // On garde la bulle d'attente sous la réponse pour le statut.
          attente.hidden = true;
        }
        reponseTexte += evenement.contenu;
        // On réaffiche le Markdown à chaque morceau (conversion sûre).
        bulle.innerHTML = markdownVersHtml(reponseTexte);
        conversation.scrollTop = conversation.scrollHeight;
      } else if (evenement.type === "statut") {
        statut = evenement.contenu;
        attente.hidden = false;
        conversation.appendChild(attente); // le statut passe en bas
      } else if (evenement.type === "erreur") {
        erreurFlux = evenement.contenu;
      } else if (evenement.type === "fin") {
        fin = evenement;
      }
    });

    if (erreurFlux || !fin) {
      throw new Error(erreurFlux || "La réponse a été interrompue. Réessaie.");
    }
    historique.push({ role: "assistant", content: reponseTexte });
    if (reglages.lectureVocale) voix.lire(reponseTexte);
    // Prévient la carte 3D et les panneaux que la mémoire a pu changer.
    emettre("memoire-modifiee", fin.concepts_mis_a_jour);
  } catch (erreur) {
    // Réponse incomplète : on la retire, ainsi que ton dernier message de
    // l'historique (tu pourras le renvoyer sans créer de doublon).
    if (bulle) bulle.remove();
    historique.pop();
    afficherMessage(erreur.message, "erreur");
  } finally {
    clearInterval(minuteur);
    attente.remove();
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
