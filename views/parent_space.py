from datetime import datetime
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from database.audit import log_action_erp
from database.db_config import SessionLocal
from database.models import (
    Classe,
    Eleve,
    EmploiDuTemps,
    Matiere,
    Note,
    Paiement,
    Presence,
    School,
    User,
    Message,
)


def afficher_espace_parent():
    st.markdown("""
        <style>
        .student-card {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            border-radius: 12px;
            padding: 20px;
            color: white;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
            margin-bottom: 20px;
            display: flex;
            align-items: center;
        }
        .student-card h2 { margin: 0; color: #ffffff; font-weight: 600; font-size: 1.8rem; padding-bottom: 5px; }
        .student-card p { margin: 0; opacity: 0.9; font-size: 1rem; color: #e2e8f0; }
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
        </style>
    """, unsafe_allow_html=True)

    st.markdown("## 👋 Bienvenue dans votre Espace Famille (Portail International)")
    st.markdown("Suivi académique, assiduité certifiée et situation financière consolidée en temps réel.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")
    username = st.session_state.get("username")
    user_role = st.session_state.get("role", "")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        user_obj = db.query(User).filter(User.username == username).first() if username else None

        eleves_query = db.query(Eleve).filter(Eleve.deleted_at.is_(None))

        if user_role and user_role.lower() == "parent" and user_obj:
            eleves_query = eleves_query.filter(
                (Eleve.parent_id == user_obj.id) | (Eleve.id == user_obj.eleve_id)
            )
        else:
            classes_query = db.query(Classe).filter(Classe.cycle == cycle_en_cours)
            if not is_super_admin and school_id:
                classes_query = classes_query.filter(Classe.school_id == school_id)
            classes_cycle = classes_query.all()
            classes_ids = [c.id for c in classes_cycle]

            if not is_super_admin and school_id:
                eleves_query = eleves_query.filter(Eleve.school_id == school_id)
            if classes_ids:
                eleves_query = eleves_query.filter(Eleve.classe_id.in_(classes_ids))
            else:
                eleves_query = eleves_query.filter(Eleve.classe_id == -1)

        eleves = eleves_query.all()

        if not eleves:
            if user_role and user_role.lower() == "parent":
                st.warning("⚠️ Aucun profil d'élève n'est actuellement rattaché à votre compte parent.")
            else:
                st.info(f"📌 Aucun élève enregistré pour le cycle **{cycle_en_cours}**.")
        else:
            noms_names = [f"{e.nom} {e.prenom} (Matricule: {e.matricule})" for e in eleves]
            eleve_choisi = st.selectbox("👨‍👩‍👧‍👦 Sélectionner l'enfant à consulter", noms_names)

            eleve_obj = next(
                (e for e in eleves if f"{e.nom} {e.prenom} (Matricule: {e.matricule})" == eleve_choisi),
                None,
            )

            if eleve_obj:
                classe = db.query(Classe).filter(Classe.id == eleve_obj.classe_id).first() if eleve_obj.classe_id else None
                classe_nom = classe.libelle if (classe and hasattr(classe, "libelle") and classe.libelle) else getattr(classe, "nom", "Non assignée")

                notes_list = db.query(Note).filter(Note.eleve_id == eleve_obj.id).all()
                moy_str = "N/A"
                if notes_list:
                    moy_calc = sum(float(n.valeur) for n in notes_list) / len(notes_list)
                    moy_str = f"{moy_calc:.2f} / 20"

                presences_list = db.query(Presence).filter(Presence.eleve_id == eleve_obj.id).all()
                nb_absences = sum(1 for p in presences_list if "Absent" in str(p.statut))
                nb_retards = sum(1 for p in presences_list if "Retard" in str(p.statut))

                frais_scol = float(getattr(classe, "frais_scolarite", 0.0) or 0.0) if classe else 0.0
                frais_inscr = float(getattr(classe, "frais_inscription", 0.0) or 0.0) if classe else 0.0
                frais_coges = float(getattr(classe, "frais_coges", 0.0) or 0.0) if classe else 0.0
                montant_brut = (frais_scol + frais_inscr + frais_coges) if (frais_scol + frais_inscr + frais_coges) > 0 else 65000.0
                reduction = float(getattr(eleve_obj, "montant_reduction", 0.0) or 0.0)
                montant_du_net = max(0.0, montant_brut - reduction)
                paiements_eleve = db.query(Paiement).filter(Paiement.eleve_id == eleve_obj.id).all()
                montant_paye = sum(float(p.montant) for p in paiements_eleve) if paiements_eleve else 0.0
                solde_restant = montant_du_net - montant_paye
                statut_finance = "À jour ✅" if solde_restant <= 0 else "Impayé ⚠️"

                st.markdown(f"""
                    <div class="student-card">
                        <div style="font-size: 3.5rem; margin-right: 25px;">🎓</div>
                        <div>
                            <h2>{eleve_obj.nom} {eleve_obj.prenom}</h2>
                            <p>Classe : <b>{classe_nom}</b> &nbsp;|&nbsp; Cycle : {cycle_en_cours} &nbsp;|&nbsp; Matricule : {eleve_obj.matricule}</p>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                col_k1, col_k2, col_k3, col_k4 = st.columns(4)
                with col_k1:
                    st.metric("Moyenne (Est.)", moy_str)
                with col_k2:
                    st.metric("Absences", f"{nb_absences}")
                with col_k3:
                    st.metric("Retards", f"{nb_retards}")
                with col_k4:
                    st.metric("Situation Financière", statut_finance)

                st.markdown("<br>", unsafe_allow_html=True)

                tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                    "📚 Notes & Évaluations",
                    "📋 Bulletins",
                    "🕒 Emploi du Temps",
                    "📌 Assiduité",
                    "💳 Situation Financière",
                    "✉️ Message & Support",
                ])

                with tab1:
                    st.markdown("#### Notes des Évaluations Récentes")
                    if not notes_list:
                        st.info("Aucune note enregistrée.")
                    else:
                        data_notes = []
                        for n in notes_list:
                            mat = db.query(Matiere).filter(Matiere.id == n.matiere_id).first()
                            mat_lib = mat.libelle if (mat and hasattr(mat, "libelle") and mat.libelle) else getattr(mat, "nom", "N/D")
                            data_notes.append({
                                "Matière": mat_lib,
                                "Type": n.type_evaluation,
                                "Note /20": float(n.valeur),
                            })
                        st.dataframe(pd.DataFrame(data_notes), use_container_width=True, hide_index=True)

                with tab2:
                    st.markdown("#### Synthèse du Bulletin de Notes")
                    if not notes_list:
                        st.info("Bulletin non disponible.")
                    else:
                        matieres_classe = db.query(Matiere).filter(Matiere.classe_id == eleve_obj.classe_id).all() if eleve_obj.classe_id else []
                        dict_coeffs_par_nom = {}
                        for m in matieres_classe:
                            nom_m = (m.libelle or getattr(m, "nom", "")).strip().lower()
                            if nom_m:
                                dict_coeffs_par_nom[nom_m] = float(getattr(m, 'coefficient', 1.0) or 1.0)

                        matieres_dict = {}
                        for n in notes_list:
                            mat = db.query(Matiere).filter(Matiere.id == n.matiere_id).first()
                            nom_mat = (mat.libelle if (mat and hasattr(mat, "libelle") and mat.libelle) else getattr(mat, "nom", "Autre")) if mat else "Autre"
                            nom_mat_lower = nom_mat.strip().lower()

                            coef = dict_coeffs_par_nom.get(nom_mat_lower, float(getattr(mat, "coefficient", 1.0) or 1.0) if mat else 1.0)

                            if nom_mat not in matieres_dict:
                                matieres_dict[nom_mat] = {"notes": [], "coef": coef}
                            matieres_dict[nom_mat]["notes"].append(float(n.valeur))

                        bulletin_data = []
                        total_points = 0.0
                        total_coef = 0.0
                        for mat_nom, info in matieres_dict.items():
                            notes = info["notes"]
                            coef = info["coef"]
                            moy_mat = sum(notes) / len(notes)
                            total_points += moy_mat * coef
                            total_coef += coef
                            bulletin_data.append({
                                "Matière": mat_nom,
                                "Coefficient": coef,
                                "Moyenne Matière": round(moy_mat, 2),
                            })

                        st.dataframe(pd.DataFrame(bulletin_data), use_container_width=True, hide_index=True)
                        if total_coef > 0:
                            st.metric("Moyenne Générale Estimée", f"{total_points / total_coef:.2f} / 20")

                with tab3:
                    st.markdown(f"#### Emploi du Temps — Classe : **{classe_nom}**")
                    
                    edt_list = db.query(EmploiDuTemps).filter(
                        (EmploiDuTemps.classe_id == eleve_obj.classe_id) | (EmploiDuTemps.classe == classe_nom)
                    ).all()

                    if not edt_list:
                        st.info("Aucun emploi du temps configuré pour cette classe.")
                    else:
                        edt_dict = {}
                        for item in edt_list:
                            edt_dict[(item.jour, item.heure)] = {
                                "matiere": item.matiere,
                                "prof": item.enseignant,
                                "contact": getattr(item, "contact", "N/D") or "N/D"
                            }

                        jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]
                        creneaux_horaires = [
                            "08h00 - 09h00",
                            "09h00 - 10h00",
                            "10h00 - 11h00",
                            "11h00 - 11h30",
                            "11h30 - 12h30",
                            "12h30 - 13h30",
                            "13h30 - 14h30",
                        ]

                        lignes_tbody = ""
                        for jour in jours:
                            lignes_tbody += f"<tr><td>{jour}</td>"
                            skip_slots = 0
                            for i, horaire in enumerate(creneaux_horaires):
                                if skip_slots > 0:
                                    skip_slots -= 1
                                    continue

                                if horaire == "11h00 - 11h30":
                                    lignes_tbody += '<td class="pause-col">☕ Pause</td>'
                                    continue

                                val_creneau = edt_dict.get((jour, horaire), None)
                                if val_creneau:
                                    span = 1
                                    for next_h in creneaux_horaires[i+1:]:
                                        if next_h == "11h00 - 11h30":
                                            break
                                        next_val = edt_dict.get((jour, next_h), None)
                                        if next_val == val_creneau:
                                            span += 1
                                        else:
                                            break
                                    
                                    skip_slots = span - 1
                                    colspan_attr = f' colspan="{span}"' if span > 1 else ''

                                    lignes_tbody += f"""
                                    <td{colspan_attr}>
                                        <div style="color: #34d399; font-weight: 700; font-size: 0.85rem; margin-bottom: 3px;">📖 {val_creneau['matiere']}</div>
                                        <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 2px;">👨‍🏫 {val_creneau['prof']}</div>
                                        <div style="font-size: 0.7rem; color: #60a5fa;">📞 {val_creneau['contact']}</div>
                                    </td>
                                    """
                                else:
                                    lignes_tbody += "<td></td>"
                            lignes_tbody += "</tr>"

                        html_table_parent = f"""
                        <!DOCTYPE html>
                        <html>
                        <head>
                        <meta charset="utf-8">
                        <style>
                            body {{
                                background-color: #0e1117;
                                color: #f3f4f6;
                                font-family: sans-serif;
                                margin: 0;
                                padding: 0;
                            }}
                            .edt-container {{
                                background-color: #0e1117;
                                padding: 0.5rem;
                                border-radius: 12px;
                                border: 1px solid rgba(255, 255, 255, 0.1);
                            }}
                            .edt-header {{
                                display: flex;
                                justify-content: space-between;
                                align-items: center;
                                margin-bottom: 1.2rem;
                                border-bottom: 2px solid #1f2937;
                                padding-bottom: 0.8rem;
                            }}
                            .edt-title {{
                                font-size: 1.1rem;
                                font-weight: 600;
                                color: #f3f4f6;
                            }}
                            .edt-badge-repot {{
                                background: #3b82f6;
                                color: white;
                                padding: 0.4rem 0.8rem;
                                border-radius: 20px;
                                font-size: 0.8rem;
                                font-weight: 500;
                            }}
                            .styled-table {{
                                width: 100%;
                                border-collapse: collapse;
                                border-radius: 8px;
                                overflow: hidden;
                                border: 1px solid #2d3748;
                            }}
                            .styled-table th {{
                                background-color: #1a202c;
                                color: #e2e8f0;
                                text-align: center;
                                padding: 12px 8px;
                                font-size: 0.85rem;
                                border-bottom: 2px solid #4a5568;
                            }}
                            .styled-table td {{
                                background-color: #111827;
                                color: #cbd5e0;
                                text-align: center;
                                padding: 12px 8px;
                                font-size: 0.8rem;
                                border-bottom: 1px solid #1f2937;
                                border-right: 1px solid #1f2937;
                                vertical-align: middle;
                                height: 65px;
                                word-break: break-word;
                            }}
                            .styled-table td:first-child {{
                                font-weight: 600;
                                color: #60a5fa;
                                background-color: #161e2e;
                                width: 90px;
                            }}
                            .pause-col {{
                                background-color: #18212f !important;
                                color: #9ca3af !important;
                                font-style: italic;
                            }}
                        </style>
                        </head>
                        <body>
                        <div class="edt-container">
                            <div class="edt-header">
                                <div class="edt-title">📌 Emploi du temps officiel : <span style="color: #60a5fa;">{classe_nom}</span></div>
                                <div class="edt-badge-repot">☕ Pause récréative : 11h00 - 11h30</div>
                            </div>
                            <table class="styled-table">
                               <thead>
                                    <tr>
                                        <th>Jour</th>
                                        <th>08h00 - 09h00</th>
                                        <th>09h00 - 10h00</th>
                                        <th>10h00 - 11h00</th>
                                        <th class="pause-col">11h00 - 11h30<br><span style="font-size:0.65rem;">(Récréation)</span></th>
                                        <th>11h30 - 12h30</th>
                                        <th>12h30 - 13h30</th>
                                        <th>13h30 - 14h30</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {lignes_tbody}
                                </tbody>
                            </table>
                        </div>
                        </body>
                        </html>
                        """
                        components.html(html_table_parent, height=520, scrolling=True)

                with tab4:
                    if not presences_list:
                        st.success("Assiduité exemplaire !")
                    else:
                        pres_data = [{"Date": p.date.strftime("%d/%m/%Y"), "Statut": p.statut} for p in presences_list]
                        st.dataframe(pd.DataFrame(pres_data), use_container_width=True, hide_index=True)

                with tab5:
                    st.markdown("#### État de Compte & Règlements")
                    st.metric("Solde Restant Dû", f"{solde_restant:,.0f} FCFA")
                    if paiements_eleve:
                        data_pay = [{"Date": p.date_paiement.strftime("%d/%m/%Y") if hasattr(p, 'date_paiement') and p.date_paiement else "N/D", "Montant": f"{float(p.montant):,.0f} FCFA", "Motif": getattr(p, 'motif', 'Scolarité')} for p in paiements_eleve]
                        st.dataframe(pd.DataFrame(data_pay), use_container_width=True, hide_index=True)
                    else:
                        st.info("Aucun historique de versement enregistré pour le moment.")

                with tab6:
                    st.markdown("#### Canaux de communication sécurisés")
                    with st.form("form_contact"):
                        obj = st.text_input("Objet du message")
                        msg = st.text_area("Contenu de votre message")
                        if st.form_submit_button("Envoyer à l'administration", type="primary"):
                            if obj and msg:
                                db.add(Message(school_id=school_id, expediteur=username, destinataire="Administration", objet=obj, contenu=msg, date_envoi=datetime.now()))
                                db.commit()
                                st.success("Message transmis avec succès à l'administration !")
    finally:
        db.close()


afficher_espace_parent = afficher_espace_parent
afficher_portail_parent = afficher_espace_parent