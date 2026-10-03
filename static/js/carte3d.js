// Scène 3D de la carte des connaissances (bibliothèque Three.js).
//
// Disposition :
// - chaque DOMAINE (bases, logique, C, IoT...) est un « îlot » placé en cercle ;
// - chaque CONCEPT est une sphère au-dessus de son îlot ;
// - la HAUTEUR d'une sphère = la longueur de sa chaîne de prérequis :
//   plus une notion est avancée, plus elle est haute ;
// - la COULEUR et la TAILLE = l'état de maîtrise (gris = non rencontré,
//   doré = autonome) ;
// - un ANNEAU signale une révision à faire ;
// - les LIGNES relient un concept à ses prérequis.
//
// Ce module ne connaît que la scène : la fiche, la légende et la solution
// de secours (sans 3D) sont gérées par carte.js.

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { couleurEtat } from "./api.js";

const RAYON_DOMAINES = 17; // distance des îlots au centre
const RAYON_ILOT = 2.6; // étalement des sphères autour d'un îlot
const HAUTEUR_NIVEAU = 2.4; // écart vertical entre deux niveaux de prérequis

const mouvementReduit = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// Profondeur d'un concept = longueur de la plus longue chaîne de prérequis.
function calculerProfondeurs(concepts) {
  const parId = new Map(concepts.map((c) => [c.id, c]));
  const profondeurs = new Map();
  const profondeur = (id) => {
    if (profondeurs.has(id)) return profondeurs.get(id);
    const concept = parId.get(id);
    const valeur = concept && concept.prerequis.length
      ? 1 + Math.max(...concept.prerequis.map(profondeur))
      : 0;
    profondeurs.set(id, valeur);
    return valeur;
  };
  concepts.forEach((c) => profondeur(c.id));
  return profondeurs;
}

// Position 3D de chaque concept.
function calculerPositions(domaines, concepts) {
  const profondeurs = calculerProfondeurs(concepts);
  const positions = new Map();
  const centres = new Map();

  domaines.forEach((domaine, i) => {
    const angle = (i / domaines.length) * Math.PI * 2;
    const centre = new THREE.Vector3(
      Math.cos(angle) * RAYON_DOMAINES, 0, Math.sin(angle) * RAYON_DOMAINES
    );
    centres.set(domaine.id, centre);

    // Regroupe les concepts du domaine par profondeur, puis les répartit
    // en cercle autour du centre de l'îlot.
    const parNiveau = new Map();
    concepts
      .filter((c) => c.domaine === domaine.id)
      .forEach((c) => {
        const niveau = profondeurs.get(c.id);
        if (!parNiveau.has(niveau)) parNiveau.set(niveau, []);
        parNiveau.get(niveau).push(c);
      });

    for (const [niveau, groupe] of parNiveau) {
      groupe.forEach((concept, k) => {
        const a = (k / groupe.length) * Math.PI * 2 + niveau * 0.7;
        const r = groupe.length === 1 ? 0 : RAYON_ILOT * (0.6 + 0.15 * groupe.length / 3);
        positions.set(concept.id, new THREE.Vector3(
          centre.x + Math.cos(a) * r,
          1.2 + niveau * HAUTEUR_NIVEAU,
          centre.z + Math.sin(a) * r
        ));
      });
    }
  });
  return { positions, centres };
}

// Crée une étiquette texte (image dessinée sur un canvas, toujours face caméra).
function creerEtiquette(texte, couleur) {
  const canvas = document.createElement("canvas");
  const contexte = canvas.getContext("2d");
  const taillePolice = 48;
  contexte.font = `600 ${taillePolice}px system-ui, sans-serif`;
  canvas.width = Math.ceil(contexte.measureText(texte).width) + 32;
  canvas.height = taillePolice + 24;
  contexte.font = `600 ${taillePolice}px system-ui, sans-serif`;
  contexte.fillStyle = couleur;
  contexte.textBaseline = "middle";
  contexte.fillText(texte, 16, canvas.height / 2);

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const sprite = new THREE.Sprite(
    // depthTest: false : l'étiquette reste visible devant les îlots.
    new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false })
  );
  sprite.renderOrder = 10;
  const echelle = 0.022;
  sprite.scale.set(canvas.width * echelle, canvas.height * echelle, 1);
  return sprite;
}

const lireVariable = (nom) =>
  getComputedStyle(document.documentElement).getPropertyValue(nom).trim();

// Construit la scène. Renvoie un objet pour la piloter depuis carte.js.
export function creerScene3D(conteneur, { domaines, concepts }, { surSelection, surSurvol }) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(lireVariable("--scene-fond"));
  scene.fog = new THREE.Fog(scene.background, 45, 95);

  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 300);
  camera.position.set(0, 30, 52);

  const rendu = new THREE.WebGLRenderer({ antialias: true });
  rendu.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  conteneur.appendChild(rendu.domElement);

  // Contrôles à la souris / au doigt : tourner, zoomer, déplacer.
  const controles = new OrbitControls(camera, rendu.domElement);
  controles.target.set(0, 7, 0);
  controles.enableDamping = true;
  controles.autoRotate = !mouvementReduit;
  controles.autoRotateSpeed = 0.4;
  controles.minDistance = 8;
  controles.maxDistance = 80;
  controles.addEventListener("start", () => (controles.autoRotate = false));

  // Lumières.
  scene.add(new THREE.AmbientLight(0xffffff, 0.55));
  const soleil = new THREE.DirectionalLight(0xffffff, 1.1);
  soleil.position.set(10, 30, 20);
  scene.add(soleil);

  // Champ d'étoiles en arrière-plan.
  const etoiles = new THREE.BufferGeometry();
  const points = [];
  for (let i = 0; i < 600; i++) {
    const v = new THREE.Vector3().randomDirection().multiplyScalar(70 + Math.random() * 40);
    points.push(v.x, Math.abs(v.y) * 0.8 - 10, v.z);
  }
  etoiles.setAttribute("position", new THREE.Float32BufferAttribute(points, 3));
  scene.add(new THREE.Points(etoiles, new THREE.PointsMaterial({
    color: lireVariable("--texte-doux"), size: 0.25, transparent: true, opacity: 0.6,
  })));

  const { positions, centres } = calculerPositions(domaines, concepts);

  // Îlots des domaines (disques) + nom du domaine.
  const couleurTexte = lireVariable("--texte");
  for (const domaine of domaines) {
    const centre = centres.get(domaine.id);
    const disque = new THREE.Mesh(
      new THREE.CylinderGeometry(RAYON_ILOT + 1, RAYON_ILOT + 1.2, 0.25, 48),
      new THREE.MeshStandardMaterial({
        color: lireVariable("--bordure"), roughness: 0.9, transparent: true, opacity: 0.55,
      })
    );
    disque.position.copy(centre).setY(-0.2);
    scene.add(disque);

    const etiquette = creerEtiquette(domaine.nom, couleurTexte);
    etiquette.position.copy(centre).setY(-1.2);
    scene.add(etiquette);
  }

  // Sphères des concepts.
  const geometrie = new THREE.SphereGeometry(1, 32, 16);
  const geometrieAnneau = new THREE.TorusGeometry(1.6, 0.07, 8, 48);
  const spheres = new Map(); // id -> { mesh, anneau, concept, pulsation }
  for (const concept of concepts) {
    const mesh = new THREE.Mesh(geometrie, new THREE.MeshStandardMaterial({ roughness: 0.35 }));
    mesh.position.copy(positions.get(concept.id));
    mesh.userData.id = concept.id;
    const anneau = new THREE.Mesh(
      geometrieAnneau, new THREE.MeshBasicMaterial({ color: lireVariable("--etat-2") })
    );
    anneau.rotation.x = Math.PI / 2;
    mesh.add(anneau);
    scene.add(mesh);
    spheres.set(concept.id, { mesh, anneau, concept, pulsation: 0 });
  }

  // Lignes de prérequis (toutes, discrètes) + lignes du concept sélectionné.
  const toutesLignes = [];
  for (const concept of concepts) {
    for (const prerequis of concept.prerequis) {
      toutesLignes.push(positions.get(concept.id), positions.get(prerequis));
    }
  }
  scene.add(new THREE.LineSegments(
    new THREE.BufferGeometry().setFromPoints(toutesLignes),
    new THREE.LineBasicMaterial({ color: lireVariable("--bordure"), transparent: true, opacity: 0.5 })
  ));
  const lignesSelection = new THREE.LineSegments(
    new THREE.BufferGeometry(),
    new THREE.LineBasicMaterial({ color: lireVariable("--principal") })
  );
  scene.add(lignesSelection);

  // Applique l'état d'un concept à sa sphère (couleur, taille, anneau).
  const aujourdHui = new Date().toISOString().slice(0, 10);
  function appliquerEtat(entree) {
    const { mesh, anneau, concept } = entree;
    const couleur = new THREE.Color(couleurEtat(concept.etat));
    mesh.material.color.copy(couleur);
    mesh.material.emissive.copy(couleur);
    mesh.material.emissiveIntensity = 0.08 + concept.etat * 0.07;
    mesh.material.transparent = concept.etat === 0;
    mesh.material.opacity = concept.etat === 0 ? 0.55 : 1;
    entree.taille = 0.45 + concept.etat * 0.07;
    anneau.visible = Boolean(
      concept.prochaine_revision && concept.prochaine_revision <= aujourdHui
    );
  }
  spheres.forEach(appliquerEtat);

  // ----- Survol et clic (« raycasting » : quel objet est sous la souris ?) -----
  const rayon = new THREE.Raycaster();
  const souris = new THREE.Vector2();
  const meshes = [...spheres.values()].map((s) => s.mesh);
  let selection = null;

  function objetSous(evenement) {
    const cadre = rendu.domElement.getBoundingClientRect();
    souris.x = ((evenement.clientX - cadre.left) / cadre.width) * 2 - 1;
    souris.y = -((evenement.clientY - cadre.top) / cadre.height) * 2 + 1;
    rayon.setFromCamera(souris, camera);
    const touche = rayon.intersectObjects(meshes, false)[0];
    return touche ? spheres.get(touche.object.userData.id) : null;
  }

  rendu.domElement.addEventListener("pointermove", (evenement) => {
    const entree = objetSous(evenement);
    rendu.domElement.style.cursor = entree ? "pointer" : "grab";
    surSurvol(entree ? entree.concept : null, evenement);
  });

  // On distingue un clic d'un glisser (rotation) : peu de mouvement = clic.
  let depart = null;
  rendu.domElement.addEventListener("pointerdown", (e) => (depart = [e.clientX, e.clientY]));
  rendu.domElement.addEventListener("pointerup", (evenement) => {
    if (!depart) return;
    const deplacement = Math.hypot(evenement.clientX - depart[0], evenement.clientY - depart[1]);
    depart = null;
    if (deplacement > 5) return;
    const entree = objetSous(evenement);
    selectionner(entree ? entree.concept.id : null);
    surSelection(entree ? entree.concept : null);
  });

  function selectionner(id) {
    selection = id ? spheres.get(id) : null;
    const segments = [];
    if (selection) {
      for (const prerequis of selection.concept.prerequis) {
        segments.push(positions.get(selection.concept.id), positions.get(prerequis));
      }
      controles.autoRotate = false;
    }
    lignesSelection.geometry.dispose();
    lignesSelection.geometry = new THREE.BufferGeometry().setFromPoints(segments);
  }

  // ----- Taille du rendu (suit la taille du panneau) -----
  function redimensionner() {
    const { clientWidth: l, clientHeight: h } = conteneur;
    if (!l || !h) return;
    rendu.setSize(l, h);
    camera.aspect = l / h;
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(redimensionner).observe(conteneur);
  redimensionner();

  // ----- Boucle d'animation (environ 60 images par seconde) -----
  const horloge = new THREE.Clock();
  function animer() {
    requestAnimationFrame(animer);
    if (!conteneur.clientWidth) return; // panneau caché : on ne dessine pas
    // getDelta() : temps écoulé depuis l'image précédente ; elapsedTime :
    // temps total (mis à jour par getDelta).
    const dt = horloge.getDelta();
    const t = horloge.elapsedTime;
    for (const entree of spheres.values()) {
      let echelle = entree.taille;
      if (entree.pulsation > 0) {
        // Petite « respiration » quand un concept vient d'être mis à jour.
        entree.pulsation = Math.max(0, entree.pulsation - dt);
        echelle *= 1 + 0.5 * Math.sin(entree.pulsation * Math.PI * 2) * entree.pulsation;
      }
      if (entree === selection) echelle *= 1.35;
      entree.mesh.scale.setScalar(echelle);
      if (entree.anneau.visible && !mouvementReduit) {
        entree.anneau.scale.setScalar(1 + 0.12 * Math.sin(t * 3));
      }
    }
    controles.update();
    rendu.render(scene, camera);
  }
  animer();

  return {
    // Met à jour les états (après une réponse du professeur ou une
    // modification dans « Ma mémoire »). idsModifies : concepts à faire pulser.
    mettreAJour(nouveauxConcepts, idsModifies = []) {
      for (const concept of nouveauxConcepts) {
        const entree = spheres.get(concept.id);
        if (!entree) continue;
        entree.concept = concept;
        appliquerEtat(entree);
        if (idsModifies.includes(concept.id) && !mouvementReduit) entree.pulsation = 1.2;
      }
    },
    selectionner,
  };
}
