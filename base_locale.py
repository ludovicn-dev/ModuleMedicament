# Base des noms commerciaux → DCI
NOMS_COMMERCIAUX = {
    "topalgic": "tramadol",
    "doliprane": "paracetamol",
    "efferalgan": "paracetamol",
    "dafalgan": "paracetamol",
    "coumadine": "warfarine",
    "augmentin": "amoxicilline + acide clavulanique",
    "clamoxyl": "amoxicilline",
    "voltarene": "diclofenac",
    "spasfon": "phloroglucinol",
    "smecta": "diosmectite",
    "tardyferon": "sulfate ferreux",
    "lamaline": "paracetamol + opium + cafeine",
    "contramal": "tramadol",
    "zumalgic": "tramadol",
    "kardegic": "acide acetylsalicylique",
    "plavix": "clopidogrel",
    "tahor": "atorvastatine",
    "inexium": "esomeprazole",
    "mopral": "omeprazole",
    "aerius": "desloratadine",
    "xyzall": "levocetirizine",
    "solupred": "prednisolone",
    "celestene": "betamethasone",
    "zithromax": "azithromycine",
    "orelox": "cefpodoxime",
    "ciflox": "ciprofloxacine",
    "advil": "ibuprofene",
    "nurofen": "ibuprofene",
    "brufen": "ibuprofene",
}

# Spécificités calédoniennes par DCI
BASE_NC = {
    "paracetamol": {
        "disponible_nc": True,
        "equivalents_nc": ["Doliprane", "Efferalgan", "Dafalgan"],
        "remarque": "Disponible en grande quantité en NC"
    },
    "tramadol": {
        "disponible_nc": True,
        "equivalents_nc": ["Topalgic", "Contramal", "Zumalgic"],
        "remarque": "Disponible en grande quantité en NC"
    },
    "amoxicilline": {
        "disponible_nc": True,
        "equivalents_nc": ["Clamoxyl", "Amoxil"],
        "remarque": "Disponible en grande quantité en NC"
    },
    "warfarine": {
        "disponible_nc": True,
        "usage_hospitalier": False,
        "equivalents_nc": ["Coumadine"],
        "remarque": "Disponible en ville — surveillance INR obligatoire"
    },
    "diclofenac": {
        "disponible_nc": True,
        "equivalents_nc": ["Voltarène"],
        "remarque": "Disponible en NC — prudence chez insuffisant rénal"
    },
}