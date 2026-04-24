import streamlit as st
import anthropic
import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Vérification mot de passe
MOT_DE_PASSE = os.environ.get("PASSWORD", "")

if "authentifie" not in st.session_state:
    st.session_state.authentifie = False

if not st.session_state.authentifie:
    st.title("🔒 Accès restreint")
    mdp = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        if mdp == MOT_DE_PASSE:
            st.session_state.authentifie = True
            st.rerun()
        else:
            st.error("Mot de passe incorrect")
    st.stop()

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
}

# Base locale calédonienne
BASE_LOCALE = {
    "paracetamol": {
        "disponible_nc": True,
        "equivalents_nc": ["Doliprane", "Efferalgan", "Dafalgan"],
        "remarque": "Disponible en grande quantité en NC"
    },
    "amoxicilline": {
        "disponible_nc": True,
        "equivalents_nc": ["Clamoxyl"],
        "remarque": "Disponible en grande quantité en NC"
    },
    "warfarine": {
        "disponible_nc": True,
        "usage_hospitalier": False,
        "equivalents_nc": ["Coumadine"],
        "remarque": "Disponible en ville — surveillance INR obligatoire"
    },
}

def get_icone_forme(forme):
    for key, icone in FORMES_ICONES.items():
        if key in forme.lower():
            return icone
    return "💊"

def chercher_bdpm(nom_medicament):
    try:
        url = f"https://base-donnees-publique.medicaments.gouv.fr/api/v1/medicament?denomination={nom_medicament}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return data[0]
        return None
    except:
        return None

def analyser_medicament(nom):
    donnees_bdpm = chercher_bdpm(nom)
    if donnees_bdpm:
        contexte_bdpm = f"Voici les données officielles BDPM : {donnees_bdpm}"
    else:
        contexte_bdpm = "Aucune donnée BDPM trouvée, utilise tes connaissances générales."

    prompt = f"""Tu es un pharmacien expert. Donne-moi une fiche complète sur le médicament "{nom}".

{contexte_bdpm}

Réponds UNIQUEMENT en JSON avec cette structure exacte, sans texte avant ou après :
{{
    "nom": "nom commercial",
    "dci": "dénomination commune internationale",
    "forme": "forme galénique (comprimé/gélule/solution injectable/etc)",
    "secable": true,
    "indication": "indication principale en 1-2 phrases",
    "posologie_standard": "posologie standard adulte",
    "posologie_insuf_renale": "adaptation posologique en cas d'insuffisance rénale",
    "dose_max_journaliere": "dose maximale journalière",
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
    return json.loads(texte[debut:fin])

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

# Interface principale
st.set_page_config(page_title="Assistant Pharmacie", page_icon="💊", layout="centered")

# Style personnalisé
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700&display=swap');

html, body, p, div, span, h1, h2, h3, h4, input, button, label {
    font-family: 'Nunito', sans-serif !important;
}

div.stButton > button {
    background-color: #00897B;
    color: white;
    border-radius: 12px;
    border: none;
    padding: 10px 24px;
    font-family: 'Nunito', sans-serif;
    font-weight: 600;
    font-size: 16px;
    transition: 0.3s;
}

div.stButton > button:hover {
    background-color: #00695C;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,137,123,0.3);
}

div.stForm > div {
    border-radius: 16px;
    border: 1px solid #B2DFDB;
    padding: 20px;
}

h1, h2, h3 {
    font-family: 'Nunito', sans-serif !important;
    font-weight: 700;
    color: #00695C;
}
</style>
""", unsafe_allow_html=True)

st.title("💊 Assistant Pharmacie")

onglet1, onglet2 = st.tabs(["📋 Fiche Médicament", "⚠️ Interactions"])

# ========== ONGLET 1 — FICHE MÉDICAMENT ==========
with onglet1:
    st.write("Recherchez un médicament pour obtenir sa fiche complète.")

    with st.form(key="recherche_form"):
        medicament = st.text_input("Nom du médicament (commercial ou DCI)",
                                   placeholder="Ex: Paracétamol, Amoxicilline... puis Entrée")
        st.form_submit_button("🔍 Rechercher")

    if medicament:
        with st.spinner("Génération de la fiche..."):
            try:
                fiche = analyser_medicament(medicament)
                info_locale = BASE_LOCALE.get(fiche["dci"].lower(), None)

                icone = get_icone_forme(fiche["forme"])
                st.markdown(f"## {icone} {fiche['nom']} — {fiche['dci']}")

                forme_texte = fiche["forme"].capitalize()
                
                st.info(f"**Forme :** {forme_texte}")

                col1, col2 = st.columns(2)
                with col1:
                    st.success(f"**📋 Indication**\n\n{fiche['indication']}")
                    st.warning(f"**⚖️ Posologie standard**\n\n{fiche['posologie_standard']}\n\n**Dose max journalière :** {fiche['dose_max_journaliere']}")
                    st.warning(f"**🫘 Insuffisance rénale**\n\n{fiche['posologie_insuf_renale']}")
                    st.info(f"**👩🏻‍⚕️ Administration**\n\n{fiche['administration']}")
                with col2:
                    st.info(f"**❄️☀️ Conservation**\n\n{fiche['conservation']}")
                    st.error(f"**⛔ Contre-indications**\n\n{fiche['contre_indications']}")
                    st.warning(f"**⚠️ Effets indésirables**\n\n{fiche['effets_indesirables']}")

                if fiche.get("compatibilite_iv"):
                    st.info(f"**💉 Compatibilité IV**\n\n{fiche['compatibilite_iv']}")

                with st.expander("➕ Plus de détails"):
                    if fiche.get("ecrasable"):
                        st.write(f"🔨 Écrasable : {fiche['ecrasable']}")
                    if fiche.get("ouvrable"):
                        st.write(f"💊 Ouvrable : {fiche['ouvrable']}")
                    if fiche.get("secable") == True:
                        st.write("✂️ Sécable : oui")
                    elif fiche.get("secable") == False:
                        st.write("🚫 Sécable : non")
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