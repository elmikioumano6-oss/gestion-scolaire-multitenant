from datetime import datetime
import unicodedata
import pandas as pd
import streamlit as st
from database.db_config import SessionLocal
from database.models import (
    ActivityLog,
    CahierTexte,
    Classe,
    Eleve,
    Enseignant,
    Matiere,
    Note,
    Programme,
    Presence,
    School,
    User,
)

SYNONYMES_MATIERES = {
    "sciences physiques": "physique chimie",
    "physique chimie": "physique chimie",
    "svt": "science de la vie et de la terre",
    "science de la vie et de la terre": "science de la vie et de la terre",
    "eps": "eps",
    "education physique": "eps",
    "education physique et sportive": "eps",
    "economie familiale": "economie familiale et sociale",
    "economie familiale et sociale": "economie familiale et sociale",
    "economie familiale sociale": "economie familiale et sociale",
    "histoire geographie": "histoire geographie",
    "histoire-geographie": "histoire geographie",
    "education civique": "education civique et morale",
    "education civique et morale": "education civique et morale",
    "education civique morale": "education civique et morale",
    "conduite": "conduite",
}


def normaliser_chaine(texte):
    if not texte or pd.isna(texte):
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texte))
    sans_accent = "".join([c for c in nfkd if not unicodedata.combining(c)])
    nettoye = " ".join(sans_accent.lower().replace("-", " ").replace("_", " ").replace("è", "e").replace("é", " e").split())
    return SYNONYMES_MATIERES.get(nettoye, nettoye)


def get_matieres_classe_strict(classe_obj, ecole_active_id, db, enseignant_obj=None):
    if not classe_obj:
        return []
    try:
        matieres_autorisees = []
        if enseignant_obj and hasattr(enseignant_obj, "matieres_attribuees") and enseignant_obj.matieres_attribuees:
            matieres_autorisees = [m.strip().title() for m in enseignant_obj.matieres_attribuees.split(",") if m.strip()]

        mat_q = db.query(Matiere).filter(
            Matiere.school_id == ecole_active_id,
            Matiere.classe_id == classe_obj.id
        )
        if hasattr(Matiere, "deleted_at"):
            mat_q = mat_q.filter(Matiere.deleted_at.is_(None))
        matieres_brutes = mat_q.all()
        
        if not matieres_brutes:
            mat_all_q = db.query(Matiere).filter(Matiere.school_id == ecole_active_id)
            if hasattr(Matiere, "deleted_at"):
                mat_all_q = mat_all_q.filter(Matiere.deleted_at.is_(None))
            matieres_brutes = mat_all_q.all()

        noms = []
        for m in matieres_brutes:
            nom_m = m.libelle if hasattr(m, "libelle") and m.libelle else getattr(m, "nom", "Matière")
            if nom_m:
                titre_m = nom_m.title()
                if not matieres_autorisees or any(m_auth.lower() in titre_m.lower() or titre_m.lower() in m_auth.lower() for m_auth in matieres_autorisees):
                    noms.append(titre_m)

        if not noms and matieres_autorisees:
            noms = matieres_autorisees

        return sorted(list(set(noms))) if noms else ["Matière Générale"]
    except Exception:
        return ["Matière Générale"]


def afficher_espace_enseignants():
    st.markdown("""
        <style>
        .teacher-card {
            background: linear-gradient(135deg, #2b5876 0%, #4e4376 100%);
            border-radius: 12px;
            padding: 20px;
            color: white;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
            margin-bottom: 25px;
            display: flex;
            align-items: center;
        }
        .teacher-card h2 { margin: 0; color: #ffffff; font-weight: 600; font-size: 1.8rem; padding-bottom: 5px; }
        .teacher-card p { margin: 0; opacity: 0.9; font-size: 1rem; color: #e2e8f0; }
        .context-box {
            background-color: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            padding: 15px 20px 5px 20px;
            margin-bottom: 25px;
        }
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            background-color: rgba(255,255,255,0.03);
            border-radius: 12px;
            color: #a0aec0;
            border: 1px dashed rgba(255,255,255,0.2);
            margin-top: 15px;
        }
        .empty-state h4 { color: #e2e8f0; margin-top: 10px; }
        .tab-title {
            color: #4da6ff;
            font-weight: 600;
            margin-bottom: 15px;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("## 👨‍🏫 Espace Pédagogique Enseignant")
    st.markdown("Plateforme unifiée pour l'appel, la saisie des notes, le cahier de texte et le suivi des charges horaires.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    user_role = str(st.session_state.get("role", "enseignant")).lower()
    username = st.session_state.get("username", "enseignant")
    cycle_en_cours = st.session_state.get("cycle_actif", "Collège / Lycée")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        target_school_id = school_id
        if is_super_admin and not target_school_id:
            ecole_defaut = db.query(School).first()
            target_school_id = ecole_defaut.id if ecole_defaut else 1

        ecole_active_id = school_id if school_id else target_school_id
        ecole_courante = db.query(School).filter(School.id == ecole_active_id).first()
        school_name = ecole_courante.nom if ecole_courante else st.session_state.get("school_name", "Établissement")

        user_obj = db.query(User).filter(User.username == username).first() if username else None
        enseignant_obj = None
        if user_obj and hasattr(user_obj, "enseignant_id") and user_obj.enseignant_id:
            enseignant_obj = db.query(Enseignant).filter(Enseignant.id == user_obj.enseignant_id).first()

        classes_query = db.query(Classe).filter(Classe.school_id == ecole_active_id)
        if hasattr(Classe, "deleted_at"):
            classes_query = classes_query.filter(Classe.deleted_at.is_(None))
        toutes_classes_ecole = classes_query.all()

        if not toutes_classes_ecole:
            st.warning(f"⚠️ Veuillez vous assurer que des classes sont configurées dans l'établissement **{school_name}**.")
            return

        if user_role in ["directeur", "admin", "administrateur", "super_admin", "censeur"] or not enseignant_obj:
            classes_disponibles = toutes_classes_ecole
        else:
            classes_str = getattr(enseignant_obj, "classes_attribuees", "") or getattr(enseignant_obj, "classes", "") or ""
            classes_prof = [c.strip().lower() for c in classes_str.split(",") if c.strip()]
            if classes_prof:
                classes_disponibles = [c for c in toutes_classes_ecole if c.libelle and c.libelle.strip().lower() in classes_prof]
            else:
                classes_disponibles = []

            if not classes_disponibles:
                st.warning("⚠️ Aucune classe ne vous est actuellement attribuée. Veuillez contacter l'administration.")
                return

        noms_classes = sorted(list(set(c.libelle for c in classes_disponibles if c.libelle)))

        st.markdown(f"""
            <div class="teacher-card">
                <div style="font-size: 3.5rem; margin-right: 25px;">👨‍🏫</div>
                <div>
                    <h2>Bienvenue, Prof. {username.capitalize()}</h2>
                    <p>Établissement : <b>{school_name}</b> &nbsp;|&nbsp; Accès : <b>Collège / Lycée (Multi-cycles)</b></p>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="context-box">', unsafe_allow_html=True)
        st.markdown("#### 🎯 Paramètres de la séance (Basculement dynamique Collège / Lycée)")
        col1, col2 = st.columns(2)
        with col1:
            classe_enseignant = st.selectbox("Vos classes assignées (Collège & Lycée)", noms_classes, key="ens_classe_select")

        classe_obj = next((c for c in classes_disponibles if c.libelle == classe_enseignant), None)
        noms_matieres = get_matieres_classe_strict(classe_obj, ecole_active_id, db, enseignant_obj)

        with col2:
            matiere_enseignant = st.selectbox("Vos matières dispensées", noms_matieres if noms_matieres else ["Aucune matière trouvée"], key="ens_matiere_select")
        st.markdown('</div>', unsafe_allow_html=True)

        matieres_brutes_db = db.query(Matiere).filter(Matiere.school_id == ecole_active_id).all()
        matiere_obj = next(
            (m for m in matieres_brutes_db if (m.libelle if hasattr(m, 'libelle') and m.libelle else getattr(m, 'nom', '')).title() == matiere_enseignant),
            None,
        )

        eleves = []
        if classe_obj:
            eleves_query = db.query(Eleve).filter(Eleve.classe_id == classe_obj.id, Eleve.school_id == ecole_active_id)
            if hasattr(Eleve, "deleted_at"):
                eleves_query = eleves_query.filter(Eleve.deleted_at.is_(None))
            eleves = eleves_query.order_by(Eleve.nom).all()

        tab_cahier, tab_notes, tab_appel, tab_charge = st.tabs([
            "📖 Cahier de Texte",
            "📝 Saisie des Notes",
            "📋 Feuille d'Appel",
            "📊 Horaires & Reste à faire",
        ])

        with tab_cahier:
            st.markdown(f"<h4 class='tab-title'>📖 Remplir le Cahier de Texte — {classe_enseignant} ({matiere_enseignant})</h4>", unsafe_allow_html=True)
            with st.form("form_ens_cahier_texte_avance"):
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    date_seance = st.date_input("Date de la séance", value=datetime.now().date(), key="ens_date_cours")
                with col_c2:
                    duree_seance = st.selectbox("Durée de la séance", ["1 heure", "2 heures", "3 heures", "4 heures"], key="ens_duree_seance")

                titre_seance = st.text_input("Titre du cours ou du chapitre *", placeholder="Ex: Chapitre 3 - Les équations du premier degré", key="ens_titre_cours")
                contenu_seance = st.text_area("Contenu réalisé / Résumé de la leçon *", placeholder="Détaillez les notions et le contenu dispensé...", key="ens_contenu_cours")
                
                with st.expander("➕ Ajouter des remarques ou exercices (Optionnel)"):
                    difficultees = st.text_area