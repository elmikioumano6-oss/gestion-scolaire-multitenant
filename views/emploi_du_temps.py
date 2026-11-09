from datetime import datetime
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from database.db_config import SessionLocal
from database.models import (
    Classe,
    EmploiDuTemps,
    School
)

def afficher_emploi_du_temps():
    st.markdown("""
        <style>
        .edt-card {
            background: linear-gradient(135deg, #1e3a8a 100%, #3b82f6 0%);
            border-radius: 12px;
            padding: 20px;
            color: white;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
            margin-bottom: 25px;
            display: flex;
            align-items: center;
        }
        .edt-card h2 { margin: 0; color: #ffffff; font-weight: 600; font-size: 1.8rem; padding-bottom: 5px; }
        .edt-card p { margin: 0; opacity: 0.9; font-size: 1.0rem; color: #93c5fd; }
        .context-box {
            background-color: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            padding: 15px 20px 5px 20px;
            margin-bottom: 25px;
        }
        .tab-title {
            color: #3b82f6;
            font-weight: 600;
            margin-bottom: 15px;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("## 🕒 Gestion et Grille Matricielle des Emplois du Temps")
    st.markdown("Saisissez et consultez les emplois du temps de manière fluide et rapide sous forme de grille interactive.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)

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

        classes_query = db.query(Classe).filter(Classe.school_id == ecole_active_id).all()
        if not classes_query:
            st.warning(f"⚠️ Aucune classe n'est configurée dans l'établissement **{school_name}**.")
            return

        noms_classes = [c.libelle for c in classes_query if c.libelle]

        card_html = (
            '<div class="edt-card">'
            '<div style="font-size: 3.5rem; margin-right: 25px;">🕒</div>'
            '<div>'
            f'<h2>Emploi du Temps — {school_name}</h2>'
            '<p>Édition rapide par grille matricielle et consultation officielle</p>'
            '</div>'
            '</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)

        st.markdown('<div class="context-box">', unsafe_allow_html=True)
        st.markdown("#### 🎯 Sélection de la classe")
        classe_selectionnee = st.selectbox("Choisir une classe", noms_classes, key="edt_admin_classe_select")
        st.markdown('</div>', unsafe_allow_html=True)

        classe_obj = next((c for c in classes_query if c.libelle == classe_selectionnee), None)

        if classe_obj:
            jours_ordre = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]
            creneaux_horaires = [
                "08h00 - 09h00", "09h00 - 10h00", "10h00 - 11h00",
                "11h30 - 12h30", "12h30 - 13h30", "13h30 - 14h30"
            ]

            tab_saisie_grille, tab_consultation = st.tabs([
                "✏️ Grille de Saisie Interactive",
                "📊 Consultation & Exportation"
            ])

            with tab_saisie_grille:
                st.markdown(f'<h4 class="tab-title">✏️ Édition directe de l’Emploi du Temps — Classe : {classe_selectionnee}</h4>', unsafe_allow_html=True)
                st.markdown("Remplissez directement les cellules avec les matières (ex: *Mathématiques*, *S.V.T*, *Français*). Laissez `-` si pas de cours.")

                # Récupération des données existantes en base pour pré-remplir la grille
                edt_existants = db.query(EmploiDuTemps).filter(
                    EmploiDuTemps.school_id == ecole_active_id,
                    (EmploiDuTemps.classe_id == classe_obj.id) | (EmploiDuTemps.classe == classe_selectionnee)
                ).all()

                dict_existant = {(e.heure, e.jour): e.matiere for e in edt_existants}

                # Construction du DataFrame pour l'éditeur interactif
                data_grille_edit = []
                for h in creneaux_horaires:
                    ligne = {"Heure / Créneau": h}
                    for j in jours_ordre:
                        ligne[j] = dict_existant.get((h, j), "-")
                    data_grille_edit.append(ligne)

                df_editable = pd.DataFrame(data_grille_edit)

                # Utilisation de st.data_editor pour une saisie rapide et fluide en mode grille
                edited_df = st.data_editor(
                    df_editable,
                    use_container_width=True,
                    num_rows="fixed",
                    key=f"editor_edt_{classe_selectionnee}"
                )

                if st.button("💾 Enregistrer toute la grille", type="primary", use_container_width=True):
                    # Suppression des anciens enregistrements de la classe pour les remplacer proprement par la nouvelle grille
                    db.query(EmploiDuTemps).filter(
                        EmploiDuTemps.school_id == ecole_active_id,
                        (EmploiDuTemps.classe_id == classe_obj.id) | (EmploiDuTemps.classe == classe_selectionnee)
                    ).delete(synchronize_session=False)

                    # Sauvegarde des nouvelles valeurs de la grille
                    for _, row in edited_df.iterrows():
                        heure_creneau = row["Heure / Créneau"]
                        for jour in jours_ordre:
                            val_matiere = str(row.get(jour, "")).strip()
                            if val_matiere and val_matiere != "-" and val_matiere != "nan":
                                nouveau_cours = EmploiDuTemps(
                                    school_id=ecole_active_id,
                                    classe_id=classe_obj.id,
                                    classe=classe_selectionnee,
                                    jour=jour,
                                    heure=heure_creneau,
                                    matiere=val_matiere,
                                    enseignant="Administration",
                                    contact="—"
                                )
                                db.add(nouveau_cours)

                    db.commit()
                    st.success(f"✅ Emploi du temps de la classe **{classe_selectionnee}** mis à jour avec succès !")
                    st.rerun()

            with tab_consultation:
                st.markdown(f'<h4 class="tab-title">📊 Consultation & Exportation — Classe : {classe_selectionnee}</h4>', unsafe_allow_html=True)
                
                edt_list = db.query(EmploiDuTemps).filter(
                    EmploiDuTemps.school_id == ecole_active_id,
                    (EmploiDuTemps.classe_id == classe_obj.id) | (EmploiDuTemps.classe == classe_selectionnee)
                ).all()

                if edt_list:
                    data_brute = []
                    for e in edt_list:
                        data_brute.append({
                            "Jour": getattr(e, 'jour', '—'),
                            "Heure": getattr(e, 'heure', '—'),
                            "Matière": getattr(e, 'matiere', '—'),
                            "Enseignant": getattr(e, 'enseignant', '—'),
                            "Contact": getattr(e, 'contact', '—')
                        })
                    df_brut = pd.DataFrame(data_brute)

                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        csv_data = df_brut.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Exporter en CSV",
                            data=csv_data,
                            file_name=f"emploi_du_temps_{classe_selectionnee}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    with col_e2:
                        if st.button("🖨️ Imprimer / PDF", use_container_width=True):
                            st.info("💡 Utilisez le raccourci **Ctrl + P** de votre navigateur pour imprimer ou enregistrer en PDF.")

                    st.markdown("---")
                    st.markdown("##### 📅 Grille Matricielle Officielle")

                    heures_presents = sorted(list(set(e.heure for e in edt_list if e.heure)))
                    jours_presents = set(e.jour for e in edt_list if e.jour)
                    jours_actifs = [j for j in jours_ordre if j in jours_presents]

                    edt_dict = {(e.jour, e.heure): e for e in edt_list}

                    grille_data = []
                    for h in heures_presents:
                        ligne = {"Heure / Créneau": h}
                        for j in jours_actifs:
                            match_cours = edt_dict.get((j, h))
                            if match_cours:
                                mat = getattr(match_cours, 'matiere', '—')
                                prof = getattr(match_cours, 'enseignant', '')
                                ligne[j] = f"📖 {mat}" + (f"<br><span style='font-size:0.75rem; color:#94a3b8;'>👨‍🏫 {prof}</span>" if prof else "")
                            else:
                                ligne[j] = "—"
                        grille_data.append(ligne)

                    if grille_data:
                        df_grille = pd.DataFrame(grille_data)
                        headers_html = "".join([f"<th>{col}</th>" for col in df_grille.columns])
                        lignes_html = ""
                        for _, row in df_grille.iterrows():
                            ligne_tr = "<tr>"
                            for col in df_grille.columns:
                                val = row[col]
                                if col == "Heure / Créneau":
                                    ligne_tr += f"<td style='font-weight: 600; background-color: #1e293b; color: #60a5fa;'>{val}</td>"
                                else:
                                    ligne_tr += f"<td style='text-align: center; vertical-align: middle;'>{val}</td>"
                            ligne_tr += "</tr>"
                            lignes_html += ligne_tr

                        html_grille = f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>body {{ background-color: #0e1117; color: #f3f4f6; font-family: sans-serif; margin: 0; padding: 0; }} .grid-table {{ width: 100%; border-collapse: collapse; border-radius: 8px; overflow: hidden; border: 1px solid #334155; }} .grid-table th {{ background-color: #1e293b; color: #e2e8f0; text-align: center; padding: 12px 8px; font-size: 0.85rem; border-bottom: 2px solid #475569; }} .grid-table td {{ background-color: #0f172a; color: #cbd5e0; padding: 12px 8px; font-size: 0.80rem; border-bottom: 1px solid #1e293b; border-right: 1px solid #1e293b; height: 60px; }}</style></head><body><table class='grid-table'><thead><tr>{headers_html}</tr></thead><tbody>{lignes_html}</tbody></table></body></html>"
                        components.html(html_grille, height=350, scrolling=True)

                    st.markdown("---")
                    st.markdown("##### 📋 Liste Détaillée")
                    st.dataframe(df_brut, use_container_width=True)
                else:
                    st.info(f"ℹ️ Aucun emploi du temps n'a encore été enregistré pour la classe de **{classe_selectionnee}**. Utilisez l'onglet **Grille de Saisie Interactive** pour le remplir en un clin d'œil !")
        else:
            st.warning("⚠️ Veuillez sélectionner une classe valide.")

    except Exception as e:
        st.error(f"⚠️ Une erreur est survenue lors du chargement de l'emploi du temps : {e}")
    finally:
        db.close()

afficher_emploi_temps = afficher_emploi_du_temps
run = afficher_emploi_du_temps