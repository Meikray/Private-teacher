// Point d'entrée JavaScript : démarre chaque partie de l'interface.
//
// FAIRE ÉVOLUER : chaque partie est un module indépendant.
//   chat.js      -> discussion avec le professeur
//   carte.js     -> carte des connaissances (+ carte3d.js pour la 3D)
//   panneaux.js  -> tableau de bord, mémoire, documents, réglages
//   voix.js      -> dictée et lecture vocale
// Ils communiquent par des événements (voir emettre/ecouter dans api.js).

import { initialiserCarte } from "./carte.js";
import { initialiserChat } from "./chat.js";
import { initialiserPanneaux } from "./panneaux.js";

initialiserPanneaux();
initialiserChat();
initialiserCarte().catch((erreur) => console.error("Carte indisponible :", erreur));
