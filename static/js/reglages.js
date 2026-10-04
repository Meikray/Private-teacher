// Réglages de l'utilisateur (voix, vitesse, détail, recherche web...).
// Ils sont gardés uniquement dans le navigateur (localStorage) : ils ne
// quittent jamais ton ordinateur.

const CLE = "professeur-reglages";

const PAR_DEFAUT = {
  detail: "normal", // "court", "normal" ou "detaille"
  rechercheWeb: true, // accès à Internet (gratuit avec l'IA locale, payant avec Claude)
  lectureVocale: false, // le professeur lit ses réponses à voix haute
  dictee: false, // dictée au micro autorisée
  voix: "", // nom de la voix choisie ("" = voix par défaut)
  vitesse: 0.95, // vitesse de lecture (1 = normale)
  langue: "fr-FR",
};

let reglages = { ...PAR_DEFAUT };

// try/catch : le stockage peut être bloqué (navigation privée...). Dans ce
// cas, l'application fonctionne quand même avec les réglages par défaut.
try {
  const sauvegarde = JSON.parse(localStorage.getItem(CLE) || "{}");
  reglages = { ...PAR_DEFAUT, ...sauvegarde };
} catch {
  reglages = { ...PAR_DEFAUT };
}

export function lireReglages() {
  return { ...reglages };
}

export function modifierReglage(nom, valeur) {
  reglages[nom] = valeur;
  try {
    localStorage.setItem(CLE, JSON.stringify(reglages));
  } catch {
    // Stockage indisponible : le réglage vaut seulement pour cette session.
  }
}
