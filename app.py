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

onglet1, onglet2 = st.tabs(["📋 Fiche Médicament", "⚠️ Interactions"])

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