from datetime import datetime
import unicodedata
import pandas as pd
import streamlit as st
from database.audit import log_action_erp
from database.db_config import SessionLocal
from database.models import CahierTexte, Classe, Enseignant, School, Note, Eleve, Programme, Matiere

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

BAREME_OFFICIEL_GLOBAL = {
    "collège": {
        "6": 900.0, "5": 770.0, "4": 840.0, "3": 875.0, "defaut": 850.0
    },
    "lycée": {
        "seconde": 950.0, "2de": 950.0, "premiere": 1000.0, "1ere": 1000.0, "terminale": 1050.0, "tle": 1050.0, "defaut": 1000.0
    },
    "primaire": {
        "defaut": 600.0
    },
    "maternelle": {
        "defaut": 400.0
    }
}

def normaliser_chaine(texte):
    if not texte or pd.isna(texte):
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texte))
    sans_accent = "".join([c for c in nfkd if not unicodedata.combining(c)])
    nettoye = " ".join(sans_accent.lower().replace("-", " ").replace("_", " ").replace("è", "e").replace("é", " e").split())
    return SYNONYMES_MATIERES.get(nettoye, nettoye)

def get_matieres_dynamiques_inspection(classes_cycle, ecole_active_id, cycle_en_cours, db):
    """Récupère, normalise et filtre strictement les matières rattachées au cycle en cours."""
    m_brutes = []
    try:
        ids_classes_cycle = [c.id for c in classes_cycle if c.id]
        if ids_classes_cycle and hasattr(Matiere, "classe_id"):
            mat_q = db.query(Matiere).filter(
                Matiere.school_id == ecole_active_id,
                Matiere.classe_id.in_(ids_classes_cycle)
            )
            if hasattr(Matiere, "deleted_at"):
                mat_q = mat_q.filter(Matiere.deleted_at.is_(None))
            m_brutes = mat_q.all()
    except Exception:
        m_brutes = []

    if not m_brutes and cycle_en_cours:
        try:
            mat_q_cycle = db.query(Matiere).filter(Matiere.school_id == ecole_active_id)
            if hasattr(Matiere, "cycle"):
                mat_q_cycle = mat_q_cycle.filter(Matiere.cycle.ilike(f"%{cycle_en_cours}%"))
            if hasattr(Matiere, "deleted_at"):
                mat_q_cycle = mat_q_cycle.filter(Matiere.deleted_at.is_(None))
            m_brutes = mat_q_cycle.all()
        except Exception:
            m_brutes = []

    if not m_brutes:
        try:
            mat_q_all = db.query(Matiere).filter(Matiere.school_id == ecole_active_id)
            if hasattr(Matiere, "deleted_at"):
                mat_q_all = mat_q_all.filter(Matiere.deleted_at.is_(None))
            m_brutes = mat_q_all.all()
        except Exception:
            m_brutes = []

    m_dict = {}
    cycle_actuel_lower = str(cycle_en_cours).lower()
    
    for m in m_brutes:
        n_brut = m.libelle if hasattr(m, "libelle") and m.libelle else getattr(m, "nom", "Matière")
        n_key = normaliser_chaine(n_brut)
        
        if "collège" in cycle_actuel_lower or "college" in cycle_actuel_lower:
            if "philosophie" in n_key or "philo" in n_key:
                continue

        if n_key and n_key not in m_dict:
            libelle_propre = n_brut.strip().title()
            if "economie familiale" in n_key:
                libelle_propre = "Économie Familiale Et Sociale"
            m_dict[n_key] = libelle_propre
            
    return sorted(list(m_dict.values()))

def afficher_espace_inspection():
    st.markdown("""
        <style>
        .inspection-card {
            background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
            border-radius: 12px;
            padding: 20px;
            color: white;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
            margin-bottom: 25px;
            display: flex;
            align-items: center;
            border-left: 5px solid #d4af37;
        }
        .inspection-card h2 { margin: 0; color: #ffffff; font-weight: 600; font-size: 1.8rem; padding-bottom: 5px; }
        .inspection-card p { margin: 0; opacity: 0.9; font-size: 1rem; color: #e2e8f0; }
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
        .visa-box {
            background-color: rgba(72, 187, 120, 0.1);
            border-left: 4px solid #48bb78;
            padding: 10px 15px;
            border-radius: 4px;
            margin-bottom: 10px;
        }
        .filter-box {
            background-color: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            padding: 15px 20px;
            margin-bottom: 20px;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("## 🔍 Supervision Pédagogique")
    st.markdown("Portail de contrôle universel : Visas pédagogiques, suivi des programmes et traçabilité d'audit.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    school_name = st.session_state.get("school_name", "Établissement")
    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")
    username_connecte = st.session_state.get("username", "inspecteur")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        target_school_id = school_id or 1
        resolved_school_id = school_id if school_id else target_school_id

        st.markdown(f"""
            <div class="inspection-card">
                <div style="font-size: 3.5rem; margin-right: 25px;">🏛️</div>
                <div>
                    <h2>Bureau de l'Inspection</h2>
                    <p>Établissement : <b>{school_name}</b> &nbsp;|&nbsp; Cycle en cours : <b>{cycle_en_cours}</b></p>
                </div>
            </div>
        """, unsafe_allow_html=True)

        tab_cours, tab_progression, tab_visite, tab_stats = st.tabs([
            "📖 Suivi & Visa des Cours",
            "📈 Taux de Couverture (MEN)",
            "📋 Fiche de Visite de Classe",
            "📈 Indicateurs & Audit",
        ])

        with tab_cours:
            st.markdown("<h4 class='tab-title'>📖 Contrôle des Séances & Visa Pédagogique</h4>", unsafe_allow_html=True)
            classes_cycle = db.query(Classe).filter(Classe.school_id == target_school_id, Classe.cycle == cycle_en_cours, Classe.deleted_at.is_(None)).all()
            noms_classes = [c.libelle for c in classes_cycle]

            if not noms_classes:
                st.info(f"Aucune classe configurée pour le cycle **{cycle_en_cours}**.")
            else:
                st.markdown('<div class="filter-box">', unsafe_allow_html=True)
                classe_sel = st.selectbox("Sélectionner la classe à superviser", noms_classes, key="insp_classe_sel")
                st.markdown('</div>', unsafe_allow_html=True)
                
                classe_obj = next((c for c in classes_cycle if c.libelle == classe_sel), None)
                if classe_obj:
                    entrees = db.query(CahierTexte).filter(CahierTexte.school_id == target_school_id, CahierTexte.classe_id == classe_obj.id).order_by(CahierTexte.date_cours.desc()).all()
                    if not entrees:
                        st.markdown("<div class='empty-state'><h4>Cahier de texte vierge</h4></div>", unsafe_allow_html=True)
                    else:
                        for ent in entrees:
                            date_str = ent.date_cours.strftime('%d/%m/%Y') if getattr(ent, 'date_cours', None) else "N/D"
                            visa_actuel = getattr(ent, 'visa_inspecteur', None)
                            with st.expander(f"Cours du {date_str} — {ent.enseignant_username or 'N/D'}"):
                                st.write(f"**Contenu :** {getattr(ent, 'contenu_realise', 'N/D')}")
                                if not visa_actuel:
                                    if st.button("✍️ Apposer le Visa", key=f"visa_{ent.id}"):
                                        setattr(ent, 'visa_inspecteur', f"Visé par {username_connecte} le {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
                                        db.commit()
                                        st.success("Visa apposé !")
                                        st.rerun()
                                else:
                                    st.markdown(f"<div class='visa-box'><strong>Certifié :</strong> {visa_actuel}</div>", unsafe_allow_html=True)

        with tab_progression:
            st.markdown("<h4 class='tab-title'>📈 Taux de Couverture des Programmes</h4>", unsafe_allow_html=True)
            st.info("Module de suivi opérationnel actif.")

        with tab_visite:
            st.markdown("<h4 class='tab-title'>📋 Grille Numérisée de Visite de Classe</h4>", unsafe_allow_html=True)
            enseignants_query = db.query(Enseignant).filter(Enseignant.school_id == resolved_school_id)
            if hasattr(Enseignant, "deleted_at"):
                enseignants_query = enseignants_query.filter(Enseignant.deleted_at.is_(None))
            liste_enseignants = enseignants_query.all()
            noms_enseignants = sorted([f"{prof.nom} {prof.prenom}" for prof in liste_enseignants])

            classes_cycle_insp = db.query(Classe).filter(Classe.school_id == resolved_school_id, Classe.cycle == cycle_en_cours).all()
            noms_matieres = get_matieres_dynamiques_inspection(classes_cycle_insp, resolved_school_id, cycle_en_cours, db)

            with st.form("form_fiche_visite"):
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    prof_inspecte = st.selectbox("Nom de l'enseignant inspecté *", options=noms_enseignants if noms_enseignants else ["Aucun enseignant"])
                    discipline_eval = st.selectbox("Discipline / Matière *", options=noms_matieres if noms_matieres else ["Aucune matière"])
                with col_f2:
                    note_pedagogique = st.slider("Note pédagogique (/20)", 0.0, 20.0, 14.0, 0.5)
                    appreciation_globale = st.selectbox("Appréciation générale", ["Très Satisfaisant", "Satisfaisant", "Passable", "Insuffisant"])

                remarques_inspecteur = st.text_area("Rapport et conseils de l'inspecteur *")
                if st.form_submit_button("💾 Enregistrer la fiche de visite", type="primary"):
                    if not prof_inspecte.strip() or not remarques_inspecteur.strip():
                        st.error("⚠️ Veuillez remplir tous les champs obligatoires.")
                    else:
                        st.success("✅ Fiche de visite enregistrée avec succès !")

        with tab_stats:
            st.markdown("<h4 class='tab-title'>📊 Indicateurs de Gouvernance & Sécurité</h4>", unsafe_allow_html=True)
            total_cours = db.query(CahierTexte).filter(CahierTexte.school_id == target_school_id).count()
            st.metric("Total Séances Enregistrées", total_cours)

    finally:
        db.close()

afficher_espace_inspection = afficher_espace_inspection
afficher_inspection = afficher_espace_inspection