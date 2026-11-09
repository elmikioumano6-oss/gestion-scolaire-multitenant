from datetime import datetime
import unicodedata
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from database.db_config import SessionLocal
from database.models import (
    Classe,
    Eleve,
    Parent,
    Evaluation,
    School,
    User,
    Note,
    Presence,
    EmploiDuTemps,
    Paiement
)

def afficher_espace_parents():
    st.markdown("""
        <style>
        .parent-card {
            background: linear-gradient(135deg, #0f766e 0%, #14b8a6 100%);
            border-radius: 12px;
            padding: 20px;
            color: white;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
            margin-bottom: 25px;
            display: flex;
            align-items: center;
        }
        .parent-card h2 { margin: 0; color: #ffffff; font-weight: 600; font-size: 1.8rem; padding-bottom: 5px; }
        .parent-card p { margin: 0; opacity: 0.9; font-size: 1rem; color: #ccfbf1; }
        .context-box {
            background-color: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            padding: 15px 20px 5px 20px;
            margin-bottom: 25px;
        }
        .tab-title {
            color: #2dd4bf;
            font-weight: 600;
            margin-bottom: 15px;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("## 👨‍👩‍👧‍👦 Espace Suivi Parents")
    st.markdown("Suivez en temps réel la scolarité, les notes, les présences, l'emploi du temps et le planning des évaluations de vos enfants.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    username = st.session_state.get("username", "parent")
    role_actuel = str(st.session_state.get("role", "")).lower()

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

        user_obj = db.query(User).filter(User.username == username).first()
        user_id = user_obj.id if user_obj else None

        if role_actuel in ["directeur", "admin", "censeur"] or is_super_admin:
            enfants_list = db.query(Eleve).filter(Eleve.school_id == ecole_active_id).all()
        else:
            enfants_list = db.query(Eleve).filter(
                Eleve.school_id == ecole_active_id,
                (Eleve.parent_id == user_id) | (Eleve.tuteur.ilike(f"%{username}%"))
            ).all()

        if not enfants_list:
            if role_actuel in ["directeur", "admin", "censeur"] or is_super_admin:
                st.warning("⚠️ Aucun élève n'est enregistré dans cet établissement.")
            else:
                st.warning("⚠️ Aucun enfant n'est actuellement rattaché à votre compte parent.")
            return

        noms_enfants = [f"{e.nom} {e.prenom} (Classe: {e.classe.libelle if hasattr(e, 'classe') and e.classe else 'N/C'})" for e in enfants_list]

        card_html = (
            '<div class="parent-card">'
            '<div style="font-size: 3.5rem; margin-right: 25px;">👨‍👩‍👧‍👦</div>'
            '<div>'
            f'<h2>Bienvenue, {username.capitalize()} ({role_actuel.capitalize()})</h2>'
            f'<p>Établissement : <b>{school_name}</b> &nbsp;|&nbsp; Enfants accessibles : <b>{len(enfants_list)}</b></p>'
            '</div>'
            '</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)

        st.markdown('<div class="context-box">', unsafe_allow_html=True)
        st.markdown("#### 🎯 Sélection de l'enfant et de la période")
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            enfant_selectionne_str = st.selectbox("Sélectionner l'enfant", noms_enfants, key="parent_enfant_select")
        with col_p2:
            semestre_selectionne = st.selectbox("Sélectionner le Semestre / Période", ["Semestre 1", "Semestre 2", "Trimestre 1", "Trimestre 2", "Trimestre 3"], key="parent_semestre_select")
            
        st.markdown('</div>', unsafe_allow_html=True)

        index_enfant = noms_enfants.index(enfant_selectionne_str)
        enfant_actif = enfants_list[index_enfant]
        classe_enfant = getattr(enfant_actif, 'classe', None)

        tab_eval_parent, tab_notes_parent, tab_presence_parent, tab_edt_parent, tab_scol_parent = st.tabs([
            "📅 Planning des Évaluations",
            "📝 Notes & Résultats",
            "📋 Assiduité & Absences",
            "🕒 Emploi du Temps",
            "💰 Scolarité & Paiements"
        ])

        with tab_eval_parent:
            classe_nom_affichage = classe_enfant.libelle if classe_enfant and hasattr(classe_enfant, 'libelle') else "Classe non assignée"
            st.markdown(f'<h4 class="tab-title">📅 Planning Officiel des Évaluations — Classe : {classe_nom_affichage} ({semestre_selectionne})</h4>', unsafe_allow_html=True)
            st.markdown(f"Retrouvez ci-dessous le calendrier complet des devoirs et compositions pour la classe de votre enfant **{enfant_actif.nom} {enfant_actif.prenom}**.")

            if classe_enfant:
                data_evals = []
                seen_creneaux_horaires = set()

                evals_sql = db.query(Evaluation).filter(
                    Evaluation.school_id == ecole_active_id,
                    Evaluation.classe_id == classe_enfant.id
                ).order_by(Evaluation.date_evaluation, Evaluation.heure_debut).all()

                for ev in evals_sql:
                    ev_sem = getattr(ev, 'semestre', semestre_selectionne)
                    mat_nom = ev.matiere.libelle if (hasattr(ev, 'matiere') and ev.matiere and hasattr(ev.matiere, 'libelle')) else getattr(ev, 'intitule', 'Matière générale')
                    
                    date_val = ev.date_evaluation.strftime("%d/%m/%Y") if hasattr(ev, 'date_evaluation') and ev.date_evaluation else "23/11/2026"
                    horaire_val = f"{ev.heure_debut} - {ev.heure_fin}" if hasattr(ev, 'heure_debut') and ev.heure_debut else "08h00 - 10h00"
                    
                    mat_low = str(mat_nom).lower()
                    if not mat_nom or "générale" in mat_low or "generale" in mat_low or "matiere" in mat_low or mat_nom == classe_nom_affichage:
                        continue

                    cle_creneau = (date_val, horaire_val)
                    if cle_creneau not in seen_creneaux_horaires:
                        seen_creneaux_horaires.add(cle_creneau)
                        data_evals.append({
                            "Semestre": ev_sem,
                            "Type d'Examen": getattr(ev, 'type_evaluation', 'Devoir Surveillé'),
                            "Date": date_val,
                            "Horaire": horaire_val,
                            "Matière(s)": mat_nom.strip().title(),
                            "Salle": getattr(ev, 'salle', 'Salle Principale')
                        })

                if not data_evals and "grille_enregistree_cache" in st.session_state:
                    grille_cache = st.session_state["grille_enregistree_cache"]
                    df_cache = grille_cache.get("df")
                    semestre_cache = grille_cache.get("semestre", semestre_selectionne)
                    
                    if df_cache is not None and classe_nom_affichage in df_cache.columns:
                        for _, row in df_cache.iterrows():
                            col_temps = str(row.iloc[0])
                            cellule_texte = str(row.get(classe_nom_affichage, ""))
                            
                            if cellule_texte.strip() and cellule_texte.strip() != "-" and cellule_texte.strip() != "nan":
                                date_str = col_temps.split("(")[0].strip() if "(" in col_temps else col_temps.strip()
                                horaire_str = col_temps.split("(")[1].replace(")", "").strip() if "(" in col_temps else "08h00 - 10h00"
                                
                                matieres_cellule = [m.replace("-", "").strip() for m in cellule_texte.split("\n") if m.strip()]
                                
                                for m_item in matieres_cellule:
                                    m_low = str(m_item).lower()
                                    if not m_item or "générale" in m_low or "generale" in m_low or "matiere" in m_low or m_item == classe_nom_affichage:
                                        continue

                                    cle_creneau = (date_str, horaire_str)
                                    if cle_creneau not in seen_creneaux_horaires:
                                        seen_creneaux_horaires.add(cle_creneau)
                                        data_evals.append({
                                            "Semestre": semestre_cache,
                                            "Type d'Examen": "Devoir Surveillé",
                                            "Date": date_str,
                                            "Horaire": horaire_str,
                                            "Matière(s)": m_item.strip().title(),
                                            "Salle": "Salle Principale"
                                        })

                if data_evals:
                    df_final = pd.DataFrame(data_evals)
                    df_final = df_final.sort_values(by=["Date", "Horaire"]).reset_index(drop=True)
                    st.dataframe(df_final, use_container_width=True)
                else:
                    st.info(f"ℹ️ Aucun planning d'évaluation n'a encore été publié pour la classe de **{classe_nom_affichage}** au titre du **{semestre_selectionne}**.")
            else:
                st.warning("⚠️ L'enfant sélectionné n'est rattaché à aucune classe valide.")

        with tab_notes_parent:
            st.markdown(f'<h4 class="tab-title">📝 Notes et Résultats — {enfant_actif.nom} {enfant_actif.prenom}</h4>', unsafe_allow_html=True)
            notes_enfant = db.query(Note).filter(Note.eleve_id == enfant_actif.id).all()
            
            if notes_enfant:
                data_notes = []
                for n in notes_enfant:
                    mat_lib = n.matiere.libelle if (hasattr(n, 'matiere') and n.matiere and hasattr(n.matiere, 'libelle')) else "Matière"
                    data_notes.append({
                        "Matière": mat_lib,
                        "Type": getattr(n, 'type_evaluation', 'Devoir'),
                        "Note /20": f"{n.valeur:g} / 20" if hasattr(n, 'valeur') else "N/C",
                        "Semestre": getattr(n, 'semestre', semestre_selectionne)
                    })
                st.dataframe(pd.DataFrame(data_notes), use_container_width=True)
            else:
                st.info(f"ℹ️ Aucune note enregistrée pour l'instant pour **{enfant_actif.nom} {enfant_actif.prenom}**.")

        with tab_presence_parent:
            st.markdown(f'<h4 class="tab-title">📋 Suivi des Absences et Retards — {enfant_actif.nom} {enfant_actif.prenom}</h4>', unsafe_allow_html=True)
            presences_enfant = db.query(Presence).filter(Presence.eleve_id == enfant_actif.id).order_by(Presence.date.desc()).all()
            
            if presences_enfant:
                data_pres = []
                for p in presences_enfant:
                    data_pres.append({
                        "Date": p.date.strftime("%d/%m/%Y") if hasattr(p, 'date') and p.date else "N/C",
                        "Statut": getattr(p, 'statut', 'Présent'),
                        "Motif / Précisions": getattr(p, 'motif', '—')
                    })
                st.dataframe(pd.DataFrame(data_pres), use_container_width=True)
            else:
                st.success(f"✅ Aucune absence ni retard signalé pour **{enfant_actif.nom} {enfant_actif.prenom}**. Exemplaire !")

        with tab_edt_parent:
            classe_nom_affichage = classe_enfant.libelle if classe_enfant and hasattr(classe_enfant, 'libelle') else ""
            st.markdown(f'<h4 class="tab-title">🕒 Emploi du Temps de la Classe — {classe_nom_affichage}</h4>', unsafe_allow_html=True)
            
            if classe_enfant:
                edt_list = db.query(EmploiDuTemps).filter(
                    EmploiDuTemps.school_id == ecole_active_id,
                    (EmploiDuTemps.classe_id == classe_enfant.id) | (EmploiDuTemps.classe == classe_nom_affichage)
                ).all()

                if edt_list:
                    data_edt = []
                    for e in edt_list:
                        data_edt.append({
                            "Jour": getattr(e, 'jour', '—'),
                            "Heure": getattr(e, 'heure', '—'),
                            "Matière": getattr(e, 'matiere', '—'),
                            "Enseignant": getattr(e, 'enseignant', '—'),
                            "Contact": getattr(e, 'contact', '—')
                        })
                    st.dataframe(pd.DataFrame(data_edt), use_container_width=True)
                else:
                    st.info(f"ℹ️ L'emploi du temps de la classe **{classe_nom_affichage}** n'a pas encore été configuré.")
            else:
                st.warning("⚠️ L'enfant n'est rattaché à aucune classe.")

        with tab_scol_parent:
            st.markdown(f'<h4 class="tab-title">💰 Suivi de la Scolarité — {enfant_actif.nom} {enfant_actif.prenom}</h4>', unsafe_allow_html=True)
            
            if classe_enfant:
                frais_total = getattr(classe_enfant, 'frais_scolarite', 0.0) or 0.0
                frais_insc = getattr(classe_enfant, 'frais_inscription', 0.0) or 0.0
                
                reduction_eleve = float(getattr(enfant_actif, 'reduction', 5000.0) or 0.0)
                frais_net_a_payer = max(0.0, frais_total - reduction_eleve)
                
                col_s1, col_s2, col_s3 = st.columns(3)
                with col_s1:
                    st.metric("Scolarité Initiale", f"{frais_total:,.2f} FCFA")
                with col_s2:
                    st.metric("Réduction Accordée", f"{reduction_eleve:,.2f} FCFA")
                with col_s3:
                    st.metric("Net à Payer", f"{frais_net_a_payer:,.2f} FCFA")
                
                st.markdown("##### Historique des Paiements Effectués")
                paiements_list = db.query(Paiement).filter(Paiement.eleve_id == enfant_actif.id).all()
                
                if paiements_list:
                    data_paiements = []
                    montant_paye_total = 0.0
                    for p in paiements_list:
                        mt = getattr(p, 'montant', 0.0) or 0.0
                        montant_paye_total += mt
                        data_paiements.append({
                            "Référence Reçu": getattr(p, 'reference_recu', '—'),
                            "Date": p.date_paiement.strftime("%d/%m/%Y") if hasattr(p, 'date_paiement') and p.date_paiement else "—",
                            "Montant Payé": f"{mt:,.2f} FCFA",
                            "Mode": getattr(p, 'mode_reglement', 'Espèces'),
                            "Motif": getattr(p, 'motif', 'Scolarité'),
                            "Caissier(e)": getattr(p, 'agent_caisse', 'Administration')
                        })
                    st.dataframe(pd.DataFrame(data_paiements), use_container_width=True)
                    
                    reste_a_payer = max(0.0, frais_net_a_payer - montant_paye_total)
                    if reste_a_payer == 0.0:
                        st.success(f"✅ **Compte Soldé :** Total payé : **{montant_paye_total:,.2f} FCFA** (Bénéficiant d'une réduction de {reduction_eleve:,.2f} FCFA). Aucun solde restant !")
                    else:
                        st.info(f"💡 **Bilan Financier :** Total payé : **{montant_paye_total:,.2f} FCFA** | Reste à solder : **{reste_a_payer:,.2f} FCFA**")
                else:
                    st.info(f"ℹ️ Aucun paiement enregistré. Le net à payer après réduction est de **{frais_net_a_payer:,.2f} FCFA**.")
            else:
                st.warning("⚠️ L'enfant n'est rattaché à aucune classe pour calculer la scolarité.")

    except Exception as e:
        st.error(f"⚠️ Une erreur est survenue lors du chargement de l'espace parent : {e}")
    finally:
        db.close()

afficher_parents = afficher_espace_parents
afficher_espace_parent = afficher_espace_parents
run = afficher_espace_parents