// Communication avec le serveur (toutes les requêtes passent par ici).

// Envoie une requête et renvoie la réponse JSON.
// En cas d'erreur, lève une Error avec le message précis du serveur
// (champ "detail"), ou un message générique.
export async function requete(adresse, options = {}) {
  const reponse = await fetch(adresse, options);

  if (!reponse.ok) {
    let explication = "Erreur du serveur (code " + reponse.status + ").";
    try {
      const erreur = await reponse.json();
      if (typeof erreur.detail === "string") {
        explication = erreur.detail;
      }
    } catch {
      // La réponse n'était pas du JSON : on garde le message générique.
    }
    throw new Error(explication);
  }
  return reponse.json();
}

// Raccourcis pour les méthodes HTTP courantes.
export const lire = (adresse) => requete(adresse);

export const envoyer = (adresse, donnees, methode = "POST") =>
  requete(adresse, {
    method: methode,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(donnees),
  });

export const supprimer = (adresse) => requete(adresse, { method: "DELETE" });

// Petit « bus d'événements » : les modules communiquent sans se connaître.
// Exemple : la carte 3D émet "demander" et la discussion l'écoute.
export function emettre(nom, detail) {
  window.dispatchEvent(new CustomEvent(nom, { detail }));
}

export function ecouter(nom, fonction) {
  window.addEventListener(nom, (evenement) => fonction(evenement.detail));
}

// Couleur CSS d'un état de maîtrise (variables --etat-0 à --etat-6).
export function couleurEtat(etat) {
  return getComputedStyle(document.documentElement)
    .getPropertyValue("--etat-" + etat)
    .trim();
}

// Crée un élément HTML avec du texte (jamais interprété comme du HTML).
export function element(balise, texte = "", classe = "") {
  const el = document.createElement(balise);
  if (texte) el.textContent = texte;
  if (classe) el.className = classe;
  return el;
}
