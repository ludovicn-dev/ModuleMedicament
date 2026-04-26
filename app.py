import streamlit as st
import anthropic
import requests
import os
import json
from dotenv import load_dotenv
from base_locale import NOMS_COMMERCIAUX, BASE_NC
import unicodedata

def normaliser(texte):
    # Supprime les accents et met en minuscules
    return ''.join(
        c for c in unicodedata.normalize('NFD', texte.lower())
        if unicodedata.category(c) != 'Mn'
    )

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Icônes par forme galénique
FORMES_ICONES = {
    "comprimé": "⚪",
    "gélule": "💊",
    "solution injectable": "💉",
    "solution buvable": "🧴",
    "patch": "🩹",
    "suppositoire": "🔵",
    "pommade": "🫙",
    "collyre": "👁️",
    "spray": "💨",
    "sachet": "📦",
    # Nouvelles variantes
    "solution ophtalmique": "👁️",
    "pommade ophtalmique": "👁️",
    "gel ophtalmique": "👁️",
    "solution auriculaire": "👂",
    "solution nasale": "👃",
    "spray nasal": "👃",
    "inhalation": "🫁",
    "poudre pour inhalation": "🫁",
    "sirop": "🧴",
    "suspension buvable": "🧴",
    "granules": "📦",
    "lyophilisat": "💉",
    "solution pour perfusion": "💉",
    "poudre injectable": "💉",
    "implant": "🩹",
    "dispositif": "🩹",
    "crème": "🫙",
    "gel": "🫙",
    "mousse": "🫙",
}

def get_icone_forme(forme):
    for key, icone in FORMES_ICONES.items():
        if key in forme.lower():
            return icone
    return "💊"

def chercher_bdpm(nom_medicament):
    try:
        # Essai 1 — recherche directe
        url = f"https://medicaments-api.giygas.dev/v1/medicament?denomination={nom_medicament.upper()}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return data[0]
        
        # Essai 2 — recherche en minuscules
        url = f"https://medicaments-api.giygas.dev/v1/medicament?denomination={nom_medicament.lower()}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return data[0]
        return None
    except:
        return None

def extraire_dci_bdpm(donnees_bdpm):
    try:
        if "compositions" in donnees_bdpm:
            for compo in donnees_bdpm["compositions"]:
                if "denominationSubstance" in compo:
                    return compo["denominationSubstance"]
        if "denomination" in donnees_bdpm:
            return donnees_bdpm["denomination"]
        return None
    except:
        return None

def analyser_medicament(nom):
    nom_normalise = normaliser(nom)
    dci_locale = None
    
    # Recherche floue dans la base locale
    for cle, dci in NOMS_COMMERCIAUX.items():
        if normaliser(cle) == nom_normalise:
            dci_locale = dci
            break
        
    # Vérifier dans la base locale des noms commerciaux
    dci_locale = NOMS_COMMERCIAUX.get(nom.lower(), None)

    # Chercher dans la BDPM
    donnees_bdpm = chercher_bdpm(dci_locale if dci_locale else nom)
    dci_officielle = dci_locale

    if not dci_officielle and donnees_bdpm:
        dci_officielle = extraire_dci_bdpm(donnees_bdpm)

    if dci_officielle:
        contexte_bdpm = f"""DONNÉES VÉRIFIÉES :
- Nom recherché : {nom}
- DCI confirmée : {dci_officielle}
RÈGLE ABSOLUE : Utilise exactement "{dci_officielle}" comme DCI sans la modifier."""
    else:
        contexte_bdpm = f"Utilise tes connaissances sur '{nom}' en étant rigoureux sur la DCI."

    prompt = f"""Tu es un pharmacien expert. Donne-moi une fiche complète sur le médicament "{nom}".

{contexte_bdpm}

Réponds UNIQUEMENT en JSON avec cette structure exacte, sans texte avant ou après :
{{
    "nom": "nom commercial",
    "dci": "dénomination commune internationale",
    "forme": "forme galénique (comprimé/gélule/solution injectable/etc)",
    "secable": true,
    "indication": "indication principale en 1-2 phrases",
    "posologie_standard": "posologie standard adulte + dose max journalière",
    "posologie_insuf_renale": "adaptation posologique en cas d'insuffisance rénale",
    "administration": "mode d'administration",
    "conservation": "conditions de conservation",
    "contre_indications": "principales contre-indications",
    "effets_indesirables": "effets indésirables fréquents",
    "compatibilite_iv": "compatibilités IV principales ou null si non injectable",
    "ecrasable": "oui/non/non applicable - avec explication courte",
    "ouvrable": "oui/non/non applicable - pour les gélules",
    "classe_therapeutique": "classe thérapeutique du médicament",
    "usage_hospitalier": false,
    "stupefiants": false,
    "marge_etroite": false,
    "surveillance_bio": "surveillance biologique recommandée ou null",
    "delai_action": "délai d'action et durée d'effet",
    "administration_sng": "administration par sonde nasogastrique - oui/non/avec précautions",
    "photosensible": false,
    "grossesse": "catégorie de risque grossesse et allaitement",
    "alternatives": "principales alternatives thérapeutiques",
    "surveillance_clinique": "surveillance clinique recommandée"
}}"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    texte = message.content[0].text
    debut = texte.find("{")
    fin = texte.rfind("}") + 1
    resultat = json.loads(texte[debut:fin])

    # Forcer la DCI officielle si disponible
    if dci_officielle:
        resultat["dci"] = dci_officielle

    return resultat

def analyser_interactions(medicaments):
    prompt = f"""Tu es un pharmacien expert. Analyse toutes les interactions médicamenteuses entre ces médicaments : {', '.join(medicaments)}.

Réponds UNIQUEMENT en JSON sans texte avant ou après :
{{
    "interactions": [
        {{
            "medicament1": "nom",
            "medicament2": "nom",
            "gravite": "modérée/sévère/contre-indiquée",
            "description": "explication courte",
            "conduite": "que faire"
        }}
    ],
    "conclusion": "résumé global en 1-2 phrases"
}}

IMPORTANT : N'inclus PAS les interactions mineures, uniquement modérées, sévères et contre-indiquées."""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    texte = message.content[0].text
    debut = texte.find("{")
    fin = texte.rfind("}") + 1
    return json.loads(texte[debut:fin])

def trouver_equivalents(medicament):
    prompt = f"""Tu es un pharmacien expert. Pour le médicament "{medicament}", donne-moi les équivalents thérapeutiques.

Réponds UNIQUEMENT en JSON sans texte avant ou après :
{{
    "medicament": "nom du médicament recherché",
    "dci": "DCI du médicament",
    "classe": "classe thérapeutique",
    "generiques": [
        {{
            "nom": "nom du générique",
            "laboratoire": "laboratoire fabricant",
            "dosage": "dosage disponible"
        }}
    ],
    "equivalents_therapeutiques": [
        {{
            "nom": "nom du médicament équivalent",
            "dci": "DCI",
            "remarque": "différence ou précaution par rapport à l'original"
        }}
    ],
    "conseil": "conseil pharmacien sur la substitution en 1-2 phrases"
}}"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    texte = message.content[0].text
    debut = texte.find("{")
    fin = texte.rfind("}") + 1
    return json.loads(texte[debut:fin])

def chat_pharmacie(message, service, historique):
    
    contextes_services = {
        "🚨 Urgences": "Tu réponds à un soignant des urgences. Privilégie les réponses rapides, pratiques et adaptées aux situations aiguës et à la prise en charge immédiate.",
        "🫀 USC (Unité de Soins Continus)": "Tu réponds à un soignant d'USC. Sois rigoureux sur les médicaments de surveillance rapprochée, les perfusions continues, les antidotes et la gestion hémodynamique.",
        "🔪 Chirurgie Ambulatoire": "Tu réponds à un soignant de chirurgie ambulatoire. Mets l'accent sur la gestion péri-opératoire, les antalgiques, les antiémétiques, et le retour rapide à domicile.",
        "💊 Oncologie Ambulatoire": "Tu réponds à un soignant d'oncologie ambulatoire. Sois précis sur les protocoles de chimiothérapie, les antiémétiques, les G-CSF, et la gestion des effets indésirables.",
        "🍼 Maternité": "Tu réponds à un soignant de maternité. Sois particulièrement rigoureux sur les médicaments autorisés pendant la grossesse et l'allaitement, les tocolytiques et les ocytociques.",
        "🏥 BOB (Bloc Obstétrical)": "Tu réponds à un soignant du bloc obstétrical. Mets l'accent sur l'analgésie péridurale, l'ocytocine, la gestion des urgences obstétricales et les médicaments en salle de naissance.",
        "🦴 Chirurgie Orthopédique": "Tu réponds à un soignant de chirurgie orthopédique. Sois précis sur les antalgiques post-op, les anticoagulants préventifs, les antibioprophylaxies et la rééducation médicamenteuse.",
        "🫁 Chirurgie Viscérale / Urologique": "Tu réponds à un soignant de chirurgie viscérale ou urologique. Mets l'accent sur l'antibioprophylaxie, la gestion de la douleur post-op, les antiémétiques et la reprise du transit.",
        "♿ SMR (Soins Médicaux et Réadaptation)": "Tu réponds à un soignant de SMR. Privilégie les questions sur la polymédication, les interactions médicamenteuses chez les patients chroniques, et l'adaptation des traitements au long cours.",
        "🎗️ Oncologie Hospitalisation": "Tu réponds à un soignant d'oncologie en hospitalisation. Sois précis sur les chimiothérapies, les soins de support, la gestion de la douleur oncologique et les urgences hématologiques.",
        "🩸 Néphrologie": "Tu réponds à un soignant de néphrologie. Sois rigoureux sur les adaptations posologiques en insuffisance rénale, la dialyse, les immunosuppresseurs et les néphrotoxiques à éviter.",
        "💬 HDJ Polyvalent": "Tu réponds à un soignant d'HDJ polyvalent. Donne des réponses adaptées à une grande variété de pathologies et de traitements en ambulatoire.",
    }
    
    contexte = contextes_services.get(service, contextes_services["💬 HDJ Polyvalent"])
    
    # Construction de l'historique pour Claude
    messages = []
    for msg in historique:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": message})
    
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        system=f"""Tu es un assistant pharmacien hospitalier expert.
{contexte}
Réponds toujours en français, de façon claire et structurée.
Termine toujours par un rappel court si nécessaire de vérifier les informations sur le RCP officiel.
Ne pose jamais plus d'une question à la fois.""",
        messages=messages
    )
    return response.content[0].text

import datetime

FICHIER_MESSAGES = "messages.json"

def charger_messages():
    try:
        with open(FICHIER_MESSAGES, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def sauvegarder_messages(messages):
    with open(FICHIER_MESSAGES, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

# Interface principale
st.set_page_config(page_title="Assistant Pharmacie", page_icon="💊", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap');

p, h1, h2, h3, h4, input, button, label {
    font-family: 'Nunito', sans-serif !important;
}

h1, h2, h3 {
    font-family: 'Nunito', sans-serif !important;
    font-weight: 800;
    color: #00695C;
}

/* Boutons */
div.stButton > button {
    background-color: #00897B;
    color: white;
    border-radius: 12px;
    border: none;
    padding: 10px 28px;
    font-family: 'Nunito', sans-serif;
    font-weight: 700;
    font-size: 16px;
    transition: all 0.3s ease;
    box-shadow: 0 2px 8px rgba(0,137,123,0.2);
}

div.stButton > button:hover {
    background-color: #00695C;
    transform: translateY(-3px);
    box-shadow: 0 6px 16px rgba(0,137,123,0.35);
}

div.stButton > button:active {
    transform: translateY(0px);
    box-shadow: 0 2px 8px rgba(0,137,123,0.2);
}

/* Carte principale médicament */
div[data-testid="stMarkdownContainer"] h2 {
    background: linear-gradient(135deg, #00897B 0%, #00695C 100%);
    color: white !important;
    padding: 16px 20px;
    border-radius: 14px;
    margin-bottom: 16px;
    box-shadow: 0 4px 15px rgba(0,137,123,0.3);
    animation: fadeInDown 0.5s ease;
}

/* Animation d'apparition des encarts */
div[data-testid="stAlert"] {
    animation: fadeInUp 0.4s ease;
    border-radius: 12px !important;
    border: none !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

/* Formulaire de recherche */
div[data-testid="stForm"] {
    background: white;
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 4px 20px rgba(0,137,123,0.1);
    border: 1px solid #B2DFDB;
}

/* Onglets */
div[data-testid="stTabs"] button {
    font-family: 'Nunito', sans-serif !important;
    font-weight: 700 !important;
    font-size: 15px !important;
}

/* Expander */
div[data-testid="stExpander"] {
    border-radius: 12px !important;
    border: 1px solid #B2DFDB !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

/* Input */
div[data-testid="stTextInput"] input {
    border-radius: 10px !important;
    border: 1.5px solid #B2DFDB !important;
    font-family: 'Nunito', sans-serif !important;
    font-size: 15px !important;
    transition: border 0.2s ease;
}

div[data-testid="stTextInput"] input:focus {
    border-color: #00897B !important;
    box-shadow: 0 0 0 3px rgba(0,137,123,0.15) !important;
}

/* Animations */
@keyframes fadeInDown {
    from { opacity: 0; transform: translateY(-20px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(15px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(0,137,123,0.4); }
    70% { box-shadow: 0 0 0 10px rgba(0,137,123,0); }
    100% { box-shadow: 0 0 0 0 rgba(0,137,123,0); }
}

/* Spinner personnalisé */
div[data-testid="stSpinner"] {
    color: #00897B !important;
}

/* Caption disclaimer */
div[data-testid="stCaptionContainer"] {
    background: #FFF8E1;
    border-radius: 8px;
    padding: 8px 12px;
    border-left: 3px solid #FFB300;
}

/* Divider */
hr {
    border-color: #B2DFDB !important;
    margin: 20px 0 !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
    <div style='text-align: center; padding: 10px 0 20px 0;'>
        <h1 style='color: #00695C; font-size: 2.2rem;'>💊 Assistant Pharmacie</h1>
    </div>
""", unsafe_allow_html=True)

onglet1, onglet2, onglet3, onglet4, onglet5 = st.tabs([
    "📋 Fiche Médicament", 
    "⚠️ Interactions", 
    "🔄 Équivalents", 
    "💬 Chat IA Pharmacie",
    "📨 Messagerie Interne"
])

# ========== ONGLET 1 — FICHE MÉDICAMENT ==========
with onglet1:
    st.write("Recherchez un médicament pour obtenir sa fiche complète.")

    with st.form(key="recherche_form"):
        medicament = st.text_input("Nom du médicament (commercial ou DCI)",
                                   placeholder="Ex: Paracétamol, Topalgic... puis Entrée")
        st.form_submit_button("🔍 Rechercher")

    if medicament:
        bdpm = chercher_bdpm(medicament)
        dci_connue = NOMS_COMMERCIAUX.get(medicament.lower(), None)

        if not bdpm and not dci_connue:
            st.warning("⚠️ Médicament non trouvé dans la base officielle BDPM. Les informations sont générées par IA — à vérifier avant tout usage clinique.")

        with st.spinner("Génération de la fiche..."):
            try:
                fiche = analyser_medicament(medicament)
                info_locale = BASE_NC.get(fiche["dci"].lower(), None)

                icone = get_icone_forme(fiche["forme"])
                st.markdown(f"## {icone} {fiche['nom']} — {fiche['dci']}")

                forme_texte = fiche["forme"].capitalize()
                st.info(f"**Forme :** {forme_texte}")

                col1, col2 = st.columns(2)
                with col1:
                    st.success(f"**📋 Indication**\n\n{fiche['indication']}")
                    st.warning(f"**⚖️ Posologie standard**\n\n{fiche['posologie_standard']}")
                    st.warning(f"**🫘 Insuffisance rénale**\n\n{fiche['posologie_insuf_renale']}")
                    st.info(f"**👩🏻‍⚕️ Administration**\n\n{fiche['administration']}")
                with col2:
                    st.info(f"**❄️☀️ Conservation**\n\n{fiche['conservation']}")
                    st.error(f"**⛔ Contre-indications**\n\n{fiche['contre_indications']}")
                    st.warning(f"**⚠️ Effets indésirables**\n\n{fiche['effets_indesirables']}")

                if fiche.get("compatibilite_iv"):
                    st.info(f"**💉 Compatibilité IV**\n\n{fiche['compatibilite_iv']}")

                with st.expander("➕ Plus de détails"):
                    if fiche.get("secable") == True:
                        st.write("✂️ Sécable : oui")
                    elif fiche.get("secable") == False:
                        st.write("🚫 Sécable : non")
                    if fiche.get("ecrasable"):
                        st.write(f"🔨 Écrasable : {fiche['ecrasable']}")
                    if fiche.get("ouvrable"):
                        st.write(f"💊 Ouvrable : {fiche['ouvrable']}")
                    if fiche.get("administration_sng"):
                        st.write(f"🧪 Sonde nasogastrique : {fiche['administration_sng']}")
                    if fiche.get("delai_action"):
                        st.write(f"⏱️ Délai d'action : {fiche['delai_action']}")
                    if fiche.get("photosensible"):
                        st.warning("☀️ Photosensible — protéger de la lumière")
                    if fiche.get("classe_therapeutique"):
                        st.write(f"🏷️ Classe : {fiche['classe_therapeutique']}")
                    if fiche.get("usage_hospitalier"):
                        st.error("🏥 Réservé à l'usage hospitalier")
                    if fiche.get("stupefiants"):
                        st.error("🔒 Stupéfiant — ordonnance sécurisée obligatoire")
                    if fiche.get("marge_etroite"):
                        st.warning("⚠️ Marge thérapeutique étroite — surveillance renforcée")
                    if fiche.get("surveillance_bio"):
                        st.write(f"🔬 Surveillance bio : {fiche['surveillance_bio']}")
                    if fiche.get("surveillance_clinique"):
                        st.write(f"🩺 Surveillance clinique : {fiche['surveillance_clinique']}")
                    if fiche.get("grossesse"):
                        st.write(f"🤰 Grossesse/Allaitement : {fiche['grossesse']}")
                    if fiche.get("alternatives"):
                        st.write(f"💡 Alternatives : {fiche['alternatives']}")

                if info_locale:
                    st.divider()
                    st.markdown("### 🌺 Spécificités Nouvelle-Calédonie")
                    if info_locale["disponible_nc"]:
                        st.success("✅ Disponible en NC")
                    else:
                        st.error("❌ Non disponible en NC")
                    if info_locale.get("equivalents_nc"):
                        st.info(f"**Équivalents disponibles :** {', '.join(info_locale['equivalents_nc'])}")
                    if info_locale.get("remarque"):
                        st.warning(f"**Remarque :** {info_locale['remarque']}")

            except Exception as e:
                st.error(f"Erreur : {e}")

    st.divider()
    st.caption("⚠️ Cet outil est une aide à la décision. Les informations doivent toujours être vérifiées sur le RCP officiel avant tout usage clinique.")

# ========== ONGLET 2 — INTERACTIONS ==========
with onglet2:
    st.write("Analysez les interactions entre plusieurs médicaments simultanément.")

    with st.form(key="interactions_form"):
        medicaments_liste = st.text_input(
            "Entrez les médicaments séparés par des virgules",
            placeholder="Ex: Warfarine, Ibuprofène, Aspirine, Metformine"
        )
        st.form_submit_button("⚠️ Analyser les interactions")

    if medicaments_liste:
        medicaments = [m.strip() for m in medicaments_liste.split(",") if m.strip()]
        if len(medicaments) < 2:
            st.warning("Entrez au moins 2 médicaments")
        else:
            with st.spinner("Analyse des interactions en cours..."):
                try:
                    resultat = analyser_interactions(medicaments)

                    if not resultat["interactions"]:
                        st.success("✅ Aucune interaction significative détectée entre ces médicaments.")
                    else:
                        for interaction in resultat["interactions"]:
                            gravite = interaction["gravite"].lower()
                            titre = f"**{interaction['medicament1']} + {interaction['medicament2']}** — {interaction['gravite'].upper()}"
                            detail = f"\n\n{interaction['description']}\n\n**À faire :** {interaction['conduite']}"
                            if "sévère" in gravite or "contre" in gravite:
                                st.error(f"🚨 {titre}{detail}")
                            else:
                                st.warning(f"⚠️ {titre}{detail}")

                    st.divider()
                    st.success(f"**Conclusion :** {resultat['conclusion']}")

                except Exception as e:
                    st.error(f"Erreur : {e}")

    st.divider()
    st.caption("⚠️ Cet outil est une aide à la décision. Les informations doivent toujours être vérifiées avant tout usage clinique.")

    # ========== ONGLET 3 — ÉQUIVALENTS ==========
with onglet3:
    st.write("Trouvez les génériques et équivalents thérapeutiques d'un médicament.")

    with st.form(key="equivalents_form"):
        medicament_eq = st.text_input(
            "Nom du médicament",
            placeholder="Ex: Doliprane, Augmentin... puis Entrée"
        )
        st.form_submit_button("🔄 Trouver les équivalents")

    if medicament_eq:
        with st.spinner("Recherche des équivalents..."):
            try:
                resultat = trouver_equivalents(medicament_eq)

                st.markdown(f"## 🔄 {resultat['medicament']} — {resultat['dci']}")
                st.info(f"**🏷️ Classe thérapeutique :** {resultat['classe']}")

                # Génériques
                if resultat.get("generiques"):
                    st.markdown("### 💊 Génériques disponibles")
                    for gen in resultat["generiques"]:
                        st.success(f"**{gen['nom']}** — {gen['laboratoire']} — {gen['dosage']}")

                # Équivalents thérapeutiques
                if resultat.get("equivalents_therapeutiques"):
                    st.markdown("### 🔁 Équivalents thérapeutiques")
                    for eq in resultat["equivalents_therapeutiques"]:
                        st.warning(f"**{eq['nom']}** ({eq['dci']})\n\n{eq['remarque']}")

                # Conseil pharmacien
                if resultat.get("conseil"):
                    st.divider()
                    st.info(f"💡 **Conseil pharmacien :** {resultat['conseil']}")

            except Exception as e:
                st.error(f"Erreur : {e}")

    st.divider()
    st.caption("⚠️ Les équivalents proposés sont générés par IA. Toujours vérifier avant substitution.")

    # ========== ONGLET 4 — CHAT PHARMACIE ==========
with onglet4:
    st.write("Posez vos questions pharmaceutiques selon votre service.")

    # Sélection du service
    service = st.selectbox("🏥 Votre service", [
        "🚨 Urgences",
        "🫀 USC (Unité de Soins Continus)",
        "🔪 Chirurgie Ambulatoire",
        "💊 Oncologie Ambulatoire",
        "🍼 Maternité",
        "🏥 BOB (Bloc Obstétrical)",
        "🦴 Chirurgie Orthopédique",
        "🫁 Chirurgie Viscérale / Urologique",
        "♿ SMR (Soins Médicaux et Réadaptation)",
        "🎗️ Oncologie Hospitalisation",
        "🩸 Néphrologie",
        "🏨 HDJ Polyvalent",
    ])

    # Initialisation de l'historique par service
    cle_historique = f"chat_{service}"
    if cle_historique not in st.session_state:
        st.session_state[cle_historique] = []

    # Affichage de l'historique
    for msg in st.session_state[cle_historique]:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        else:
            st.chat_message("assistant").write(msg["content"])

    # Zone de saisie
    question = st.chat_input("Posez votre question pharmaceutique...")

    if question:
        # Ajouter la question à l'historique
        st.session_state[cle_historique].append({
            "role": "user",
            "content": question
        })
        st.chat_message("user").write(question)

        # Obtenir la réponse
        with st.spinner("💬 Réflexion en cours..."):
            reponse = chat_pharmacie(
                question,
                service,
                st.session_state[cle_historique][:-1]
            )

        # Ajouter la réponse à l'historique
        st.session_state[cle_historique].append({
            "role": "assistant",
            "content": reponse
        })
        st.chat_message("assistant").write(reponse)

    # Bouton pour effacer l'historique
    if st.session_state[cle_historique]:
        if st.button("🗑️ Effacer la conversation"):
            st.session_state[cle_historique] = []
            st.rerun()

    st.divider()
    st.caption("⚠️ Cet assistant est une aide à la décision. Toujours vérifier les informations avant tout acte clinique.")

    # ========== ONGLET 5 — MESSAGERIE INTERNE ==========
with onglet5:
    
    messages = charger_messages()
    
    # Choix du profil
    profil = st.radio("👤 Vous êtes :", 
                      ["🏥 Un service", "💊 La Pharmacie"],
                      horizontal=True)
    
    st.divider()

    # ===== VUE SERVICE =====
    if profil == "🏥 Un service":
        
        service_msg = st.selectbox("🏥 Votre service", [
            "🚨 Urgences",
            "🫀 USC",
            "🔪 Chirurgie Ambulatoire",
            "💊 Oncologie Ambulatoire",
            "🍼 Maternité",
            "🏥 BOB",
            "🦴 Chirurgie Orthopédique",
            "🫁 Chirurgie Viscérale / Urologique",
            "♿ SMR",
            "🎗️ Oncologie Hospitalisation",
            "🩸 Néphrologie",
            "🏨 HDJ Polyvalent",
        ])

        st.markdown("### 📤 Envoyer un message à la Pharmacie")

        with st.form(key="form_message"):
            sujet = st.selectbox("Sujet", [
                "❓ Question médicament",
                "📦 Demande de stock",
                "⚠️ Urgence / Besoin immédiat",
                "🔄 Substitution / Équivalent",
                "💊 Préparation spéciale",
                "📋 Autre"
            ])
            contenu = st.text_area("Votre message", 
                                   placeholder="Ex: Avez-vous du Noradrénaline en stock ? Patient en choc septique...")
            envoyer = st.form_submit_button("📤 Envoyer")

            if envoyer and contenu:
                nouveau_message = {
                    "id": len(messages) + 1,
                    "service": service_msg,
                    "sujet": sujet,
                    "contenu": contenu,
                    "date": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "statut": "non lu",
                    "reponse": None,
                    "date_reponse": None
                }
                messages.append(nouveau_message)
                sauvegarder_messages(messages)
                st.success("✅ Message envoyé à la pharmacie !")

        # Afficher les réponses reçues pour ce service
        mes_messages = [m for m in messages if m["service"] == service_msg]
        if mes_messages:
            st.divider()
            st.markdown("### 📬 Vos messages et réponses")
            for msg in reversed(mes_messages):
                with st.expander(f"{msg['sujet']} — {msg['date']} — {'✅ Répondu' if msg['reponse'] else '⏳ En attente'}"):
                    st.write(f"**Votre message :** {msg['contenu']}")
                    if msg["reponse"]:
                        st.success(f"**💊 Réponse pharmacie ({msg['date_reponse']}) :** {msg['reponse']}")
                    else:
                        st.warning("⏳ En attente de réponse de la pharmacie")

    # ===== VUE PHARMACIE =====
    else:
        st.markdown("### 📥 Messages reçus des services")
        
        messages_non_lus = [m for m in messages if m["statut"] == "non lu"]
        messages_lus = [m for m in messages if m["statut"] == "lu"]
        
        if not messages:
            st.info("📭 Aucun message pour le moment")
        else:
            if messages_non_lus:
                st.error(f"📬 {len(messages_non_lus)} message(s) non lu(s)")
            
            for msg in reversed(messages):
                statut_icon = "🔴" if msg["statut"] == "non lu" else "✅"
                with st.expander(f"{statut_icon} {msg['service']} — {msg['sujet']} — {msg['date']}"):
                    st.write(f"**Message :** {msg['contenu']}")
                    
                    if msg["reponse"]:
                        st.success(f"**Votre réponse ({msg['date_reponse']}) :** {msg['reponse']}")
                    else:
                        with st.form(key=f"reponse_{msg['id']}"):
                            reponse = st.text_area("Votre réponse")
                            envoyer_rep = st.form_submit_button("📤 Répondre")
                            
                            if envoyer_rep and reponse:
                                for m in messages:
                                    if m["id"] == msg["id"]:
                                        m["reponse"] = reponse
                                        m["statut"] = "lu"
                                        m["date_reponse"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                                sauvegarder_messages(messages)
                                st.success("✅ Réponse envoyée !")
                                st.rerun()

    st.divider()
    st.caption("📨 Messagerie interne — Assistant Pharmacie")