from datetime import datetime
from io import BytesIO
import unicodedata
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from database.db_config import SessionLocal
from database.models import (
    ActivityLog,
    AnneeScolaire,
    CahierTexte,
    Classe,
    Matiere,
    Programme,
    School,
)

SYNONYMES_MATIERES = {
    "sciences physiques": "physique chimie",
    "physique chimie": "physique chimie",
    "svt": "science de la vie et de la terre",
    "science de la vie et de la terre": "science de la vie et de la terre",
    "eps": "education physique et sportive",
    "education physique et sportive": "education physique et sportive",
    "economie familiale": "economie familiale et sociale",
    "economie familiale et sociale": "economie familiale et sociale",
    "histoire geographie": "histoire geographie",
    "histoire-geographie": "histoire geographie",
}


def normaliser_chaine(texte):
    if not texte or pd.isna(texte):
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texte))
    sans_accent = "".join([c for c in nfkd if not unicodedata.combining(c)])
    nettoye = " ".join(
        sans_accent.lower().replace("-", " ").replace("_", " ").split()
    )
    return SYNONYMES_MATIERES.get(nettoye, nettoye)


def afficher_supervision_cahier():
    st.markdown(
        """
    <style>
        @media print {
            body { background-color: white !important; color: black !important; }
            .stButton, .stSelectbox, sidebar, header, footer, [data-testid="stSidebar"] { display: none !important; }
            .printable-area { width: 100% !important; padding: 10px !important; margin: 0 !important; }
            .print-footer { position: fixed; bottom: 0; left: 0; right: 0; text-align: center; font-size: 8pt; border-top: 1px solid #ccc; padding-top: 8px; color: #333; background-color: white; }
        }
    </style>
    """,
        unsafe_allow_html=True,
    )

    st.subheader(
        "📋 Contrôle d'Inspection Pédagogique, Archivage & Registre Officiel"
    )
    st.markdown(
        "Portail officiel d'audit aux normes internationales (SIA) pour la"
        " direction, le censeur et les inspecteurs."
    )
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    username = st.session_state.get("username", "admin")
    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        target_school_id = school_id
        if is_super_admin and not target_school_id:
            ecole_defaut = db.query(School).first()
            target_school_id = ecole_defaut.id if ecole_defaut else 1

        resolved_school_id = school_id if school_id else target_school_id

        ecole_courante = (
            db.query(School).filter(School.id == resolved_school_id).first()
        )
        school_name = (
            ecole_courante.nom
            if ecole_courante
            else st.session_state.get("school_name", "Établissement")
        )
        school_devise = (
            ecole_courante.devise
            if ecole_courante
            else "Excellence - Persévérance - Réussite"
        )
        school_adresse = (
            ecole_courante.adresse
            if ecole_courante and ecole_courante.adresse
            else "Niamey - Niger"
        )
        school_contacts = (
            ecole_courante.contacts
            if ecole_courante and ecole_courante.contacts
            else "N/D"
        )

        annee_active = (
            db.query(AnneeScolaire)
            .filter(
                AnneeScolaire.school_id == resolved_school_id,
                AnneeScolaire.active == True,
            )
            .first()
        )
        libelle_annee = annee_active.libelle if annee_active else "2026"

        st.markdown('<div class="printable-area">', unsafe_allow_html=True)
        st.markdown(
            f"### 🏫 **{school_name}** — Cycle : **{cycle_en_cours}**"
        )
        st.caption(
            f"Devise : {school_devise} | Année Scolaire : **{libelle_annee}** |"
            f" {school_adresse}"
        )

        classes_cycle = (
            db.query(Classe)
            .filter(
                Classe.cycle == cycle_en_cours,
                Classe.school_id == resolved_school_id,
            )
            .all()
        )

        if not classes_cycle:
            st.warning(
                f"⚠️ Aucune classe enregistrée pour le cycle **{cycle_en_cours}**."
            )
            st.markdown("</div>", unsafe_allow_html=True)
            return

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            noms_classes = [
                c.libelle or getattr(c, "nom", f"Classe {c.id}")
                for c in classes_cycle
            ]
            classe_suivie = st.selectbox(
                "Sélectionner la classe à inspecter",
                noms_classes,
                key="sup_classe_select",
            )
        with col_f2:
            periode_inspection = st.selectbox(
                "Période d'évaluation / Semestre",
                [
                    "Année complète",
                    "Semestre 1",
                    "Semestre 2",
                ],
                key="sup_periode_select",
            )

        classe_obj = next(
            (
                c
                for c in classes_cycle
                if (c.libelle or getattr(c, "nom", f"Classe {c.id}"))
                == classe_suivie
            ),
            None,
        )
        st.info(
            f"🔍 Registre d'inspection actif pour la classe de **{classe_suivie}**"
            f" ({periode_inspection})."
        )

        col_p1, _ = st.columns([1, 4])
        with col_p1:
            components.html(
                """
                <div style="display: flex; align-items: center; height: 38px;">
                    <button onclick="parent.window.print()" style="background-color: #2563eb; color: white; border: none; padding: 0.4rem 1rem; font-size: 0.85rem; font-weight: 600; border-radius: 6px; cursor: pointer; font-family: sans-serif; white-space: nowrap;">🖨️ Imprimer le Rapport</button>
                </div>
                """,
                height=45,
            )

        if not classe_obj:
            st.warning("⚠️ Classe sélectionnée invalide.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        # --- RÉCUPÉRATION STRICTE DES MATIÈRES DE LA CLASSE SÉLECTIONNÉE ---
        matieres_query = db.query(Matiere).filter(
            Matiere.classe_id == classe_obj.id,
            Matiere.school_id == resolved_school_id,
        )
        if hasattr(Matiere, "deleted_at"):
            matieres_query = matieres_query.filter(Matiere.deleted_at.is_(None))
        
        matieres_classe = matieres_query.all()

        all_programmes = db.query(Programme).filter(
            Programme.school_id == resolved_school_id
        ).all()

        if not matieres_classe:
            st.info(
                f"Aucune matière configurée pour la classe de **{classe_suivie}**."
            )
            st.markdown("</div>", unsafe_allow_html=True)
            return

        libelle_classe_norm = normaliser_chaine(classe_suivie)
        niveau_cible = ""
        for mot, lib_long in [("6", "6ème"), ("5", "5ème"), ("4", "4ème"), ("3", "3ème")]:
            if mot in libelle_classe_norm or mot + "e" in libelle_classe_norm or mot + "è" in libelle_classe_norm:
                niveau_cible = lib_long
                break

        data_suivi = []
        is_college = cycle_en_cours.lower() in ["collège", "college"]

        for mat in matieres_classe:
            mat_lib = mat.libelle if hasattr(mat, "libelle") and mat.libelle else getattr(mat, "nom", "Matière")
            norm_key = normaliser_chaine(mat_lib)

            heures_prevues = 0.0
            
            # Application de la même logique croisée stricte par classe pour récupérer le vrai volume du programme
            if not is_college:
                prog_obj = None
                for p in all_programmes:
                    p_nom = normaliser_chaine(getattr(p, 'nom_matiere', getattr(p, 'matiere', '')))
                    texte_ligne = normaliser_chaine(f"{getattr(p, 'classe', '')} {getattr(p, 'code_matiere', '')} {getattr(p, 'matiere', '')} {getattr(p, 'nom_matiere', '')}")
                    if p_nom == norm_key and (libelle_classe_norm in texte_ligne):
                        prog_obj = p
                        break
                
                if not prog_obj:
                    for p in all_programmes:
                        p_nom = normaliser_chaine(getattr(p, 'nom_matiere', getattr(p, 'matiere', '')))
                        if p_nom == norm_key:
                            prog_obj = p
                            break

                heures_prevues = float(prog_obj.volume_horaire) if prog_obj and prog_obj.volume_horaire else float(getattr(mat, "volume_horaire", 0) or 0)
            else:
                prog_classe = next(
                    (p for p in all_programmes 
                     if normaliser_chaine(getattr(p, 'nom_matiere', '')) == norm_key 
                     and (not niveau_cible or normaliser_chaine(niveau_cible) in normaliser_chaine(getattr(p, 'code_matiere', '')))),
                    None
                )

                if prog_classe and prog_classe.volume_horaire and prog_classe.volume_horaire > 0:
                    heures_prevues = prog_classe.volume_horaire
                else:
                    BAREME_COLLEGE = {
                        "6ème": {"francais": 205, "anglais": 140, "histoire geographie": 70, "mathematiques": 240, "physique chimie": 35, "science de la vie et de la terre": 70, "economie familiale et sociale": 35, "education physique et sportive": 70, "education civique": 35},
                        "5ème": {"francais": 140, "anglais": 140, "histoire geographie": 70, "mathematiques": 175, "physique chimie": 35, "science de la vie et de la terre": 70, "economie familiale et sociale": 35, "education physique et sportive": 70, "education civique": 35},
                        "4ème": {"francais": 140, "anglais": 140, "histoire geographie": 70, "mathematiques": 175, "physique chimie": 105, "science de la vie et de la terre": 70, "economie familiale et sociale": 35, "education physique et sportive": 70, "education civique": 35},
                        "3ème": {"francais": 140, "anglais": 140, "histoire geographie": 70, "mathematiques": 175, "physique chimie": 105, "science de la vie et de la terre": 105, "economie familiale et sociale": 35, "education physique et sportive": 70, "education civique": 35},
                    }
                    if niveau_cible in BAREME_COLLEGE and norm_key in BAREME_COLLEGE[niveau_cible]:
                        heures_prevues = float(BAREME_COLLEGE[niveau_cible][norm_key])
                    elif mat.volume_horaire and mat.volume_horaire > 0:
                        heures_prevues = mat.volume_horaire
                    else:
                        heures_prevues = 0.0

            if periode_inspection in ["Semestre 1", "Semestre 2"]:
                heures_prevues_periode = round(heures_prevues / 2.0, 1)
            else:
                heures_prevues_periode = heures_prevues

            # --- FILTRE DES SÉANCES STRICTEMENT POUR CETTE CLASSE ET CETTE MATIÈRE ---
            entrees_query = db.query(CahierTexte).filter(
                CahierTexte.school_id == resolved_school_id,
                CahierTexte.classe_id == classe_obj.id,
                CahierTexte.matiere_id == mat.id,
            )

            entrees_cahier = entrees_query.all()

            entrees_filtrees = []
            for e in entrees_cahier:
                date_seance = getattr(e, "date_seance", None) or getattr(e, "date", None)
                if date_seance:
                    if isinstance(date_seance, str):
                        try:
                            date_obj = datetime.strptime(date_seance[:10], "%Y-%m-%d")
                        except Exception:
                            date_obj = None
                    else:
                        date_obj = date_seance

                    if date_obj and periode_inspection != "Année complète":
                        mois = date_obj.month
                        is_s1 = mois in [9, 10, 11, 12, 1, 2]
                        if periode_inspection == "Semestre 1" and is_s1:
                            entrees_filtrees.append(e)
                        elif periode_inspection == "Semestre 2" and not is_s1:
                            entrees_filtrees.append(e)
                    else:
                        entrees_filtrees.append(e)
                else:
                    entrees_filtrees.append(e)

            heures_realisees = 0.0
            for e in entrees_filtrees:
                duree_str = getattr(e, "duree_seance", "1 heure")
                try:
                    val_duree = float(duree_str.split()[0])
                except Exception:
                    val_duree = 1.0
                heures_realisees += val_duree

            progression_pct = (
                round((heures_realisees / heures_prevues_periode) * 100, 1)
                if heures_prevues_periode > 0
                else 0.0
            )
            if progression_pct > 100.0:
                progression_pct = 100.0

            if entrees_filtrees:
                dernier_cours = entrees_filtrees[-1]
                contenu_cours = getattr(dernier_cours, "contenu", "") or ""
                dernier_chapitre = (
                    contenu_cours[:60] + "..."
                    if len(contenu_cours) > 60
                    else (contenu_cours if contenu_cours else "N/D")
                )
                enseignant_ref = (
                    getattr(
                        getattr(dernier_cours, "enseignant_user", None),
                        "username",
                        getattr(dernier_cours, "auteur_saisie", "Corps professoral"),
                    )
                    or "Corps professoral"
                )
            else:
                dernier_chapitre = "Aucun cours enregistré"
                enseignant_ref = "Non assigné"

            if heures_prevues_periode == 0.0:
                appreciation = "⚠️ Volume horaire non défini (Programme manquant)"
            elif progression_pct >= 75:
                appreciation = "🟢 Rythme excellent et conforme"
            elif progression_pct >= 40:
                appreciation = "🟡 Rythme satisfaisant"
            elif progression_pct > 0:
                appreciation = "🟠 Rythme insuffisant - Retard à rattraper"
            else:
                appreciation = "🔴 En attente de première saisie"

            data_suivi.append({
                "Matière": mat_lib.title(),
                "Enseignant(e)": enseignant_ref,
                "Heures Prévues": f"{heures_prevues_periode}h",
                "Heures Réalisées": f"{heures_realisees}h",
                "Progression (%)": f"{progression_pct}%",
                "Dernier Chapitre / Notions": dernier_chapitre,
                "Appréciation Inspection": appreciation,
            })

        df_suivi = pd.DataFrame(data_suivi)
        st.dataframe(df_suivi, use_container_width=True)

        st.download_button(
            label="📥 Télécharger le rapport officiel d'inspection (CSV)",
            data=df_suivi.to_csv(index=False).encode("utf-8"),
            file_name=(
                f"rapport_inspection_{classe_suivie}_"
                f"{datetime.now().strftime('%Y%m%d')}.csv"
            ),
            mime="text/csv",
        )

        st.markdown("</div>", unsafe_allow_html=True)
    finally:
        db.close()


afficher_supervision_cahier = afficher_supervision_cahier