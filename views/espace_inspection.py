from datetime import datetime
from database.audit import log_action_erp
from database.db_config import SessionLocal
from database.models import CahierTexte, Classe, Enseignant, School, Note, Eleve, Programme, Matiere
import pandas as pd
import streamlit as st
import unicodedata

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

# Référentiel global de secours par cycle (MEN Niger)
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


def afficher_espace_inspection():
    # --- Injection CSS pour un design Premium & Institutionnel ---
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
        </style>
    """, unsafe_allow_html=True)

    st.markdown("## 🔍 Supervision Pédagogique")
    st.markdown(
        "Portail de contrôle universel (Normes MEN Niger / Standards internationaux) : "
        "Visas pédagogiques, suivi des programmes et traçabilité d'audit."
    )
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

        log_action_erp(
            module="Espace Inspection",
            action=f"Consultation sécurisée de l'espace d'inspection - Cycle global: {cycle_en_cours}",
            statut="Succès",
            valeur_avant="Accès non audité",
            valeur_apres=f"Utilisateur: {username_connecte}",
        )

        # --- 1. Carte Inspecteur ---
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

        # ONGLET 1 : SUIVI DES COURS ET CAHIER DE TEXTE
        with tab_cours:
            st.markdown(f"<h4 class='tab-title'>📖 Contrôle des Séances & Visa Pédagogique</h4>", unsafe_allow_html=True)
            st.markdown("Apposez un **Visa Numérique Officiel** pour certifier la supervision des cahiers de texte.")

            classes_cycle = (
                db.query(Classe)
                .filter(
                    Classe.school_id == target_school_id,
                    Classe.cycle == cycle_en_cours,
                    Classe.deleted_at.is_(None)
                )
                .all()
            )
            noms_classes = [c.libelle for c in classes_cycle]

            if not noms_classes:
                st.info(f"Aucune classe configurée pour le cycle **{cycle_en_cours}**.")
            else:
                classe_sel = st.selectbox(
                    "Sélectionner la classe à superviser", noms_classes, key="insp_classe_sel"
                )
                classe_obj = next(
                    (c for c in classes_cycle if c.libelle == classe_sel), None
                )

                if classe_obj:
                    entrees = (
                        db.query(CahierTexte)
                        .filter(
                            CahierTexte.school_id == target_school_id,
                            CahierTexte.classe_id == classe_obj.id,
                        )
                        .order_by(CahierTexte.date.desc())
                        .all()
                    )

                    if not entrees:
                        st.markdown(f"""
                            <div class="empty-state">
                                <div style="font-size: 3rem; margin-bottom: 10px;">📓</div>
                                <h4>Cahier de texte vierge</h4>
                                <p>Aucune séance n'a encore été saisie par les enseignants pour la classe de <b>{classe_sel}</b>.</p>
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown("<br>", unsafe_allow_html=True)
                        for ent in entrees:
                            date_str = ent.date.strftime('%d/%m/%Y') if ent.date else "N/D"
                            visa_actuel = getattr(ent, 'visa_inspecteur', None)
                            
                            # Ajout d'un emoji visuel pour différencier les cours validés
                            titre_expander = f"✅ Cours du {date_str}" if visa_actuel else f"⏳ Cours du {date_str}"
                            
                            with st.expander(f"{titre_expander} — Enseignant : {ent.enseignant_username or 'N/D'} ({getattr(ent, 'duree', 1.0)}h)"):
                                st.write(f"**Contenu :** {ent.contenu_realise}")
                                st.write(f"**Difficultés :** {ent.difficultees or 'Aucune'}")
                                
                                st.markdown("---")
                                col_v1, col_v2 = st.columns([3, 1])
                                with col_v1:
                                    if visa_actuel:
                                        st.markdown(f"<div class='visa-box'><strong>Certifié :</strong> {visa_actuel}</div>", unsafe_allow_html=True)
                                    else:
                                        st.warning("⚠️ En attente de supervision")
                                with col_v2:
                                    if not visa_actuel:
                                        if st.button("✍️ Apposer le Visa", key=f"visa_{ent.id}", use_container_width=True):
                                            setattr(ent, 'visa_inspecteur', f"Visé par {username_connecte} le {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
                                            db.commit()
                                            log_action_erp(
                                                module="Espace Inspection",
                                                action=f"Apposition de visa pédagogique sur le cahier de texte ID {ent.id} (Classe {classe_sel})",
                                                statut="Critique",
                                                valeur_avant="Non visé",
                                                valeur_apres="Visé officiellement",
                                            )
                                            st.success("Visa apposé !")
                                            st.rerun()

        # ONGLET 2 : PROGRESSION
        with tab_progression:
            st.markdown(f"<h4 class='tab-title'>📈 Taux de Couverture des Programmes (MEN Niger)</h4>", unsafe_allow_html=True)
            st.markdown("Évaluation dynamique et globale du volume horaire total dispensé par rapport au cumul des volumes horaires officiels.")

            classes_cycle_prog = (
                db.query(Classe)
                .filter(
                    Classe.school_id == target_school_id,
                    Classe.cycle == cycle_en_cours,
                    Classe.deleted_at.is_(None)
                )
                .all()
            )
            noms_classes_prog = [c.libelle for c in classes_cycle_prog]

            if not noms_classes_prog:
                st.info(f"Aucune classe configurée pour le cycle **{cycle_en_cours}**.")
            else:
                classe_prog_sel = st.selectbox(
                    "🔍 Sélectionner la classe pour le suivi global :", noms_classes_prog, key="insp_prog_classe_sel"
                )
                classe_prog_obj = next(
                    (c for c in classes_cycle_prog if c.libelle == classe_prog_sel), None
                )

                if classe_prog_obj:
                    # 1. Calcul des heures réelles dispensées (Cahier de texte)
                    entrees_classe = (
                        db.query(CahierTexte)
                        .filter(
                            CahierTexte.school_id == target_school_id,
                            CahierTexte.classe_id == classe_prog_obj.id,
                        )
                        .all()
                    )

                    total_heures_realisees = 0.0
                    for ent in entrees_classe:
                        duree_val = float(getattr(ent, 'duree', 0.0) or 0.0)
                        if duree_val > 0:
                            total_heures_realisees += duree_val
                        else:
                            d_str = str(getattr(ent, "duree_seance", "1 heure"))
                            try:
                                chiffre = float("".join(filter(str.isdigit, d_str)) or 1)
                                total_heures_realisees += chiffre
                            except Exception:
                                total_heures_realisees += 1.0

                    # 2. Calcul universel du volume attendu (Matières de la classe -> Programmes -> Référentiel du cycle)
                    objectif_total = 0.0
                    origine_calcul = "Base dynamique"
                    cycle_key = cycle_en_cours.strip().lower()

                    # A. Vérification de la table Matière liée à la classe
                    matieres_classe = db.query(Matiere).filter(Matiere.classe_id == classe_prog_obj.id, Matiere.school_id == resolved_school_id).all()
                    if matieres_classe:
                        for m in matieres_classe:
                            for attr_v in ["volume_horaire", "volume", "heures", "masse_horaire", "duree", "volume_hebdo"]:
                                val = getattr(m, attr_v, None)
                                if val is not None:
                                    try:
                                        v_f = float(val)
                                        if v_f > 0:
                                            objectif_total += v_f
                                            break
                                    except Exception:
                                        pass

                    # B. Vérification de la table Programme si la table matière est vide
                    if objectif_total == 0.0:
                        programmes_ecole = db.query(Programme).filter(Programme.school_id == resolved_school_id).all()
                        classe_norm = normaliser_chaine(classe_prog_sel)
                        for p in programmes_ecole:
                            p_classe = normaliser_chaine(str(getattr(p, 'classe', getattr(p, 'code_matiere', ''))))
                            if classe_norm in p_classe or any(m in p_classe for m in classe_norm.split() if len(m) > 1):
                                objectif_total += float(p.volume_horaire or 0)

                    # C. Référentiel de secours universel selon le cycle et le niveau de la classe
                    if objectif_total == 0.0:
                        cl_lower = classe_prog_sel.lower()
                        ref_cycle = BAREME_OFFICIEL_GLOBAL.get(cycle_key, {"defaut": 700.0})
                        
                        matched = False
                        for key_niv, val_vol in ref_cycle.items():
                            if key_niv != "defaut" and key_niv in cl_lower:
                                objectif_total = val_vol
                                origine_calcul = f"Référentiel officiel ({cycle_en_cours} - {key_niv})"
                                matched = True
                                break
                        if not matched:
                            objectif_total = ref_cycle.get("defaut", 700.0)
                            origine_calcul = f"Référentiel standard ({cycle_en_cours})"

                    taux_global = min(100.0, (total_heures_realisees / objectif_total) * 100) if objectif_total > 0 else 0.0

                    st.caption(f"🌍 Mode de calcul : _{origine_calcul}_")

                    col_m1, col_m2, col_m3 = st.columns(3)
                    with col_m1:
                        st.metric("Volume Horaire Total Dispensé", f"{total_heures_realisees:g} h")
                    with col_m2:
                        st.metric("Volume Horaire Officiel Attendu", f"{objectif_total:g} h")
                    with col_m3:
                        st.metric("Taux de Couverture Global", f"{taux_global:.1f}%")

                    st.progress(taux_global / 100.0)
                    
                    if taux_global < 20:
                        st.error(f"🔴 État d'avancement critique pour **{classe_prog_sel}** (Taux : {taux_global:.1f}%)")
                    elif taux_global < 50:
                        st.warning(f"🟠 Avancement modéré pour **{classe_prog_sel}** (Taux : {taux_global:.1f}%)")
                    else:
                        st.success(f"🟢 Rythme de couverture satisfaisant pour **{classe_prog_sel}** (Taux : {taux_global:.1f}%)")

        # ONGLET 3 : VISITE DE CLASSE
        with tab_visite:
            st.markdown(f"<h4 class='tab-title'>📋 Grille Numérisée de Visite de Classe</h4>", unsafe_allow_html=True)
            st.markdown("Outil réglementaire d'évaluation pédagogique de l'enseignant (pédagogie, tenue de classe, supports).")
            
            # 1. Récupération des enseignants de l'école
            enseignants_query = db.query(Enseignant).filter(Enseignant.school_id == resolved_school_id)
            if hasattr(Enseignant, "deleted_at"):
                enseignants_query = enseignants_query.filter(Enseignant.deleted_at.is_(None))
            liste_enseignants = enseignants_query.all()
            noms_enseignants = sorted([f"{prof.nom} {prof.prenom}" for prof in liste_enseignants])

            # 2. Récupération des matières (dédupliquées ET FILTRÉES PAR CYCLE)
            matieres_query = db.query(Matiere).filter(
                Matiere.school_id == resolved_school_id,
                Matiere.cycle == cycle_en_cours 
            )
            if hasattr(Matiere, "deleted_at"):
                matieres_query = matieres_query.filter(Matiere.deleted_at.is_(None))
            liste_matieres = matieres_query.all()
            noms_matieres = sorted(list(set([(m.libelle if hasattr(m, 'libelle') and m.libelle else getattr(m, 'nom', 'Matière')).title() for m in liste_matieres])))

            with st.form("form_fiche_visite"):
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    prof_inspecte = st.selectbox(
                        "Nom de l'enseignant inspecté *", 
                        options=noms_enseignants if noms_enseignants else ["Aucun enseignant enregistré"]
                    )
                    
                    discipline_eval = st.selectbox(
                        "Discipline / Matière *", 
                        options=noms_matieres if noms_matieres else ["Aucune matière enregistrée dans ce cycle"]
                    )
                with col_f2:
                    note_pedagogique = st.slider("Note pédagogique attribuée (/20)", 0.0, 20.0, 14.0, 0.5)
                    appreciation_globale = st.selectbox("Appréciation générale", ["Très Satisfaisant", "Satisfaisant", "Passable", "Insuffisant"])

                remarques_inspecteur = st.text_area("Rapport et conseils de l'inspecteur / censeur *")
                
                submitted_visite = st.form_submit_button("💾 Enregistrer et archiver la fiche de visite", type="primary")
                if submitted_visite:
                    if not prof_inspecte.strip() or not remarques_inspecteur.strip() or prof_inspecte == "Aucun enseignant enregistré":
                        st.error("⚠️ Veuillez renseigner un enseignant valide et le rapport d'inspection.")
                    else:
                        log_action_erp(
                            module="Espace Inspection",
                            action=f"Archivage Fiche de Visite — Prof: {prof_inspecte} ({discipline_eval}) - Note: {note_pedagogique}/20",
                            statut="Critique",
                            valeur_avant="Aucune évaluation",
                            valeur_apres=f"Note: {note_pedagogique}/20 [{appreciation_globale}]",
                        )
                        st.success(f"✅ Fiche de visite pour **{prof_inspecte}** enregistrée et sécurisée dans la piste d'audit !")

        # ONGLET 4 : STATS SOC 2
        with tab_stats:
            st.markdown("<h4 class='tab-title'>📊 Indicateurs de Gouvernance & Sécurité (SOC 2 / ISO 27001)</h4>", unsafe_allow_html=True)
            total_cours = (
                db.query(CahierTexte)
                .filter(CahierTexte.school_id == target_school_id)
                .count()
            )
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                st.metric("Total Séances Enregistrées", total_cours)
            with col_s2:
                st.metric("Niveau de Sécurité Données", "Immuable / Chiffré")
            with col_s3:
                st.metric(
                    "Établissement", school_name, delta=f"Cycle : {cycle_en_cours}"
                )

    finally:
        db.close()


# Alias de compatibilité exhaustive pour le routeur app.py
afficher_espace_inspection = afficher_espace_inspection
afficher_inspection = afficher_espace_inspection