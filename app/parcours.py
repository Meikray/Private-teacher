"""Parcours pédagogique : les domaines, les concepts et leurs prérequis.

C'est la « carte des connaissances » de l'application (sections 11 à 14,
39, 57 et 62 du cahier des charges). Elle sert :
- à la mémoire pédagogique (chaque concept a un état de maîtrise) ;
- à la carte 3D (chaque concept est une sphère, chaque prérequis un lien) ;
- au professeur (il connaît les prérequis à vérifier).

FAIRE ÉVOLUER LE PARCOURS : il suffit d'ajouter un domaine dans DOMAINES ou
un concept dans CONCEPTS. Aucun autre fichier n'a besoin d'être modifié.
Les tests (tests/test_parcours.py) vérifient que tout reste cohérent.
"""

# Les 7 états de maîtrise (section 21). L'indice sert de valeur numérique :
# 0 = Non rencontré ... 6 = Autonome.
ETATS = [
    "Non rencontré",
    "Découverte",
    "Compréhension fragile",
    "Compréhension correcte",
    "Maîtrisé",
    "Maîtrisé en pratique",
    "Autonome",
]

# Les domaines, dans l'ordre conseillé de la progression (section 39 :
# d'abord ce qui sert aux cours d'IoT, puis l'informatique générale).
DOMAINES = [
    {"id": "bases", "nom": "Bases numériques"},
    {"id": "logique", "nom": "Logique informatique"},
    {"id": "c", "nom": "Programmation C"},
    {"id": "microcontroleurs", "nom": "Microcontrôleurs"},
    {"id": "iot", "nom": "IoT"},
    {"id": "reseaux", "nom": "Réseaux"},
    {"id": "cpp", "nom": "C++"},
    {"id": "assembleur", "nom": "Assembleur"},
    {"id": "outils", "nom": "Outils et méthodes"},
]


def _concept(id, nom, domaine, prerequis=()):
    """Petit raccourci pour écrire un concept sur une seule ligne."""
    return {"id": id, "nom": nom, "domaine": domaine, "prerequis": list(prerequis)}


CONCEPTS = [
    # --- Niveau 0 : bases numériques ---
    _concept("ordinateur", "Ordinateur", "bases"),
    _concept("processeur", "Processeur", "bases", ["ordinateur"]),
    _concept("memoire", "Mémoire", "bases", ["ordinateur"]),
    _concept("stockage", "Stockage", "bases", ["memoire"]),
    _concept("fichiers", "Fichiers", "bases", ["stockage"]),
    _concept("systeme_exploitation", "Système d'exploitation", "bases", ["processeur", "memoire"]),
    _concept("programme", "Programme", "bases", ["processeur"]),
    _concept("binaire", "Binaire", "bases"),
    _concept("bits_octets", "Bits et octets", "bases", ["binaire"]),
    _concept("compilateur_interpreteur", "Compilateur et interpréteur", "bases", ["programme"]),
    # --- Niveau 1 : logique informatique ---
    _concept("algorithme", "Algorithme", "logique"),
    _concept("variable", "Variable", "logique", ["memoire"]),
    _concept("type", "Type", "logique", ["variable", "bits_octets"]),
    _concept("condition", "Condition", "logique", ["variable"]),
    _concept("boucle", "Boucle", "logique", ["condition"]),
    _concept("fonction", "Fonction", "logique", ["variable"]),
    _concept("entree_sortie", "Entrée / sortie", "logique", ["programme"]),
    _concept("erreur", "Erreur", "logique", ["programme"]),
    _concept("debogage", "Débogage", "logique", ["erreur"]),
    _concept("pseudocode", "Pseudocode", "logique", ["algorithme"]),
    # --- Niveau 2 : programmation C ---
    _concept("c_syntaxe", "Syntaxe du C", "c", ["compilateur_interpreteur", "variable"]),
    _concept("operateurs", "Opérateurs", "c", ["c_syntaxe", "type"]),
    _concept("c_conditions_boucles", "Conditions et boucles en C", "c", ["c_syntaxe", "boucle"]),
    _concept("c_fonctions", "Fonctions en C", "c", ["c_syntaxe", "fonction"]),
    _concept("tableaux", "Tableaux", "c", ["c_conditions_boucles"]),
    _concept("chaines", "Chaînes de caractères", "c", ["tableaux"]),
    _concept("adresse_memoire", "Adresse mémoire", "c", ["memoire", "variable"]),
    _concept("pointeurs", "Pointeurs", "c", ["adresse_memoire", "type"]),
    _concept("structures", "Structures", "c", ["type"]),
    _concept("memoire_dynamique", "Mémoire dynamique", "c", ["pointeurs"]),
    _concept("fichiers_c", "Fichiers en C", "c", ["pointeurs", "fichiers"]),
    _concept("compilation", "Compilation", "c", ["compilateur_interpreteur", "c_syntaxe"]),
    # --- Microcontrôleurs ---
    _concept("microcontroleur", "Microcontrôleur", "microcontroleurs", ["processeur", "memoire"]),
    _concept("registres", "Registres", "microcontroleurs", ["microcontroleur", "bits_octets"]),
    _concept("gpio", "GPIO", "microcontroleurs", ["microcontroleur"]),
    _concept("entrees_numeriques", "Entrées / sorties numériques", "microcontroleurs", ["gpio"]),
    _concept("adc", "Entrées analogiques (ADC)", "microcontroleurs", ["gpio", "binaire"]),
    _concept("pwm", "PWM", "microcontroleurs", ["entrees_numeriques"]),
    _concept("interruptions", "Interruptions", "microcontroleurs", ["microcontroleur", "c_fonctions"]),
    _concept("timers", "Timers", "microcontroleurs", ["registres"]),
    _concept("uart", "UART", "microcontroleurs", ["entrees_numeriques", "bits_octets"]),
    _concept("i2c", "I2C", "microcontroleurs", ["uart"]),
    _concept("spi", "SPI", "microcontroleurs", ["uart"]),
    # --- IoT ---
    _concept("capteurs", "Capteurs", "iot", ["entrees_numeriques", "adc"]),
    _concept("actionneurs", "Actionneurs", "iot", ["entrees_numeriques", "pwm"]),
    _concept("arduino", "Arduino", "iot", ["microcontroleur", "c_fonctions"]),
    _concept("esp32", "ESP32", "iot", ["arduino"]),
    _concept("raspberry_pi", "Raspberry Pi", "iot", ["systeme_exploitation"]),
    _concept("wifi", "Wi-Fi", "iot", ["adresse_ip"]),
    _concept("bluetooth_ble", "Bluetooth / BLE", "iot", ["microcontroleur"]),
    _concept("mqtt", "MQTT", "iot", ["tcp_udp", "wifi"]),
    _concept("http_api", "HTTP et API", "iot", ["tcp_udp"]),
    _concept("bases_de_donnees", "Bases de données", "iot", ["fichiers"]),
    _concept("dashboards", "Dashboards", "iot", ["mqtt", "bases_de_donnees"]),
    _concept("node_red", "Node-RED", "iot", ["mqtt"]),
    _concept("securite_iot", "Sécurité IoT", "iot", ["tls", "mqtt"]),
    # --- Réseaux ---
    _concept("adresse_ip", "Adresse IP", "reseaux", ["binaire"]),
    _concept("masque_sous_reseau", "Masque et sous-réseaux", "reseaux", ["adresse_ip"]),
    _concept("ports", "Ports", "reseaux", ["adresse_ip"]),
    _concept("tcp_udp", "TCP et UDP", "reseaux", ["ports"]),
    _concept("dns", "DNS", "reseaux", ["adresse_ip"]),
    _concept("dhcp", "DHCP", "reseaux", ["adresse_ip"]),
    _concept("routage", "Routage", "reseaux", ["masque_sous_reseau"]),
    _concept("tls", "TLS / HTTPS", "reseaux", ["tcp_udp"]),
    # --- C++ ---
    _concept("cpp_vs_c", "Différences C / C++", "cpp", ["c_fonctions"]),
    _concept("classes_objets", "Classes et objets", "cpp", ["cpp_vs_c", "structures"]),
    _concept("constructeurs", "Constructeurs", "cpp", ["classes_objets"]),
    _concept("encapsulation", "Encapsulation", "cpp", ["classes_objets"]),
    _concept("references", "Références", "cpp", ["pointeurs", "cpp_vs_c"]),
    _concept("stl", "STL", "cpp", ["classes_objets", "tableaux"]),
    _concept("exceptions", "Exceptions", "cpp", ["erreur", "classes_objets"]),
    # --- Assembleur ---
    _concept("instruction_opcode", "Instruction et opcode", "assembleur", ["registres", "bits_octets"]),
    _concept("compteur_ordinal", "Compteur ordinal", "assembleur", ["instruction_opcode"]),
    _concept("pile", "Pile", "assembleur", ["memoire", "instruction_opcode"]),
    _concept("branchements", "Comparaisons et branchements", "assembleur", ["compteur_ordinal", "condition"]),
    _concept("chaine_compilation", "Du C au code machine", "assembleur", ["compilation", "instruction_opcode"]),
    # --- Outils et méthodes ---
    _concept("terminal_linux", "Terminal et Linux", "outils", ["systeme_exploitation"]),
    _concept("git", "Git", "outils", ["fichiers"]),
    _concept("documentation_officielle", "Lire la documentation", "outils"),
    _concept("tests", "Tests", "outils", ["fonction", "debogage"]),
    _concept("utiliser_ia", "Utiliser l'IA comme outil", "outils", ["documentation_officielle"]),
]

# Accès rapide à un concept par son identifiant.
CONCEPTS_PAR_ID = {concept["id"]: concept for concept in CONCEPTS}


def nom_etat(etat):
    """Renvoie le nom lisible d'un état (ex. 3 -> "Compréhension correcte")."""
    return ETATS[etat]
