from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components
from database.db_config import SessionLocal
from database.models import CahierTexte, Enseignant, School, User, Classe, Matiere, Depense, HeureVacataireMois

def format_fcfa(montant):
    """Formate un montant en FCFA avec un espace comme séparateur de milliers."""
    return f"{int(round(montant)):,}".replace(",", " ")

def format_taux(montant):
    """Formate un taux horaire sans espace pour tenir sur une seule ligne."""
    return str(int(round(montant)))

def afficher_etat_paie_administration(mois, date_paie):
    school_id = st.session_state.get("school_id")
    db = SessionLocal()
    try:
        ecole = db.query(School).filter(School.id == school_id).first() if school_id else db.query(School).first()
        nom_ecole = ecole.nom.upper() if ecole else "COMPLEXE SCOLAIRE PRIVE RAHMAT-FH"
        adresse_ecole = getattr(ecole, "adresse", "QUARTIER AEROPORT NIAMEY-NIGER").upper() if ecole else "QUARTIER AEROPORT NIAMEY-NIGER"

        utilisateurs_query = db.query(User)
        if school_id:
            utilisateurs_query = utilisateurs_query.filter(User.school_id == school_id)

        tous_utilisateurs = utilisateurs_query.all()
        postes_administratifs = ["proviseur", "directeur", "censeur", "surveillant", "comptable", "econome", "gardien", "secretaire", "informaticien", "planton", "admin"]
        
        personnels = []
        for u in tous_utilisateurs:
            role_lower = str(getattr(u, "role", "")).lower()
            if any(p in role_lower for p in postes_administratifs) and "enseignant" not in role_lower and "professeur" not in role_lower:
                personnels.append(u)

        if not personnels and tous_utilisateurs:
            for u in tous_utilisateurs:
                role_lower = str(getattr(u, "role", "")).lower()
                if role_lower not in ["enseignant", "professeur", "vacataire"]:
                    personnels.append(u)

        lignes_html = ""
        total_net_global = 0

        if not personnels:
            lignes_html = '<tr><td colspan="8" style="text-align: center; color: gray;">Aucun personnel administratif enregistré.</td></tr>'
        else:
            for i, p in enumerate(personnels, 1):
                salaire_base = float(getattr(p, "salaire_base", 0.0) or 0.0)
                primes = float(getattr(p, "primes_fixes", 0.0) or 0.0)
                nom_complet = getattr(p, "username", f"Agent {i}")
                
                acompte_depenses = 0.0
                try:
                    depenses_query = db.query(Depense).filter(Depense.school_id == school_id) if school_id else db.query(Depense)
                    for dep in depenses_query.all():
                        libelle_dep = str(getattr(dep, "libelle", "") or getattr(dep, "motif", "") or "").lower()
                        beneficiaire_dep = str(getattr(dep, "beneficiaire", "") or "").lower()
                        if nom_complet.lower() in libelle_dep or nom_complet.lower() in beneficiaire_dep:
                            if any(k in libelle_dep for k in ["acompte", "avance", "paie"]):
                                acompte_depenses += float(getattr(dep, "montant", 0.0) or 0.0)
                except Exception:
                    db.rollback()

                acompte = float(getattr(p, "acompte", 0.0) or 0.0) + acompte_depenses
                poste = getattr(p, "role", "Administratif")
                net_a_payer = salaire_base + primes - acompte
                total_net_global += net_a_payer

                lignes_html += f"""
                <tr>
                    <td style="text-align: center;">{i}</td>
                    <td><b>{nom_complet}</b></td>
                    <td>{str(poste).capitalize()}</td>
                    <td style="text-align: right; white-space: nowrap;">{format_fcfa(salaire_base)}</td>
                    <td style="text-align: right; white-space: nowrap;">{format_fcfa(primes)}</td>
                    <td style="text-align: right; white-space: nowrap;">{format_fcfa(acompte)}</td>
                    <td style="text-align: right; white-space: nowrap; background-color: #f8fafc;"><b>{format_fcfa(net_a_payer)}</b></td>
                    <td style="height: 35px;"></td>
                </tr>
                """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                @page {{ size: A4 landscape; margin: 10mm; }}
                @media print {{
                    body {{ background: #FFFFFF; margin: 0; }}
                    .no-print {{ display: none !important; }}
                    .page {{ border: none !important; box-shadow: none !important; width: 100% !important; padding: 0 !important; }}
                }}
                body {{ background: #f0f2f5; font-family: Arial, sans-serif; padding: 10px 0; }}
                .print-container {{ text-align: center; margin-bottom: 15px; }}
                .print-btn {{ background-color: #ff8800; color: white; padding: 10px 24px; font-size: 14px; font-weight: bold; border: none; border-radius: 6px; cursor: pointer; }}
                .page {{ width: 277mm; min-height: 180mm; margin: 0 auto; background: #FFFFFF; padding: 12mm; border: 2px solid #000080; box-sizing: border-box; }}
                table {{ width: 100%; border-collapse: collapse; font-size: 0.75rem; margin-top: 10px; }}
                th, td {{ border: 1px solid #000080; padding: 6px 8px; }}
                th {{ background-color: #800020; color: #FFFFFF; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="print-container no-print"><button class="print-btn" onclick="window.print()">🖨️ Imprimer l'État de Paie Administration</button></div>
            <div class="page">
                <table>
                    <tr>
                        <td style="border: none; font-size: 0.8rem; font-weight: bold;">{nom_ecole}<br>{adresse_ecole}</td>
                        <td style="border: none; text-align: right; font-size: 0.8rem;"><b>ÉTAT DE PAIE — ADMINISTRATIF</b><br>Mois : <b>{mois}</b><br>Date : <b>{date_paie.strftime('%d/%m/%Y')}</b></td>
                    </tr>
                </table>
                <table>
                    <thead><tr><th>N°</th><th>Nom & Prénom</th><th>Poste</th><th>Salaire de Base</th><th>Primes</th><th>Acomptes</th><th>Net à Payer</th><th>Signature</th></tr></thead>
                    <tbody>{lignes_html}</tbody>
                    <tfoot><tr style="background-color: #000080; color: #FFFFFF; font-weight: bold;"><td colspan="6" style="text-align: right;">TOTAL GÉNÉRAL :</td><td style="text-align: right; white-space: nowrap;">{format_fcfa(total_net_global)} FCFA</td><td></td></tr></tfoot>
                </table>
            </div>
        </body>
        </html>
        """
        components.html(html_content, height=620, scrolling=True)
    except Exception as e:
        db.rollback()
        st.error(f"Erreur technique : {e}")
    finally:
        db.close()

def afficher_etat_paie_vacataires(mois, date_paie, cycle_filtre="Tous les cycles"):
    school_id = st.session_state.get("school_id")
    db = SessionLocal()
    try:
        ecole = db.query(School).filter(School.id == school_id).first() if school_id else db.query(School).first()
        nom_ecole = ecole.nom.upper() if ecole else "COMPLEXE SCOLAIRE PRIVE RAHMAT-FH"
        adresse_ecole = getattr(ecole, "adresse", "QUARTIER AEROPORT NIAMEY-NIGER").upper() if ecole else "QUARTIER AEROPORT NIAMEY-NIGER"

        enseignants_query = db.query(Enseignant)
        if school_id:
            enseignants_query = enseignants_query.filter(Enseignant.school_id == school_id)

        tous_enseignants = enseignants_query.all()
        
        classes_db = []
        try:
            classes_q = db.query(Classe)
            if school_id:
                classes_q = classes_q.filter(Classe.school_id == school_id)
            classes_db = classes_q.all()
        except Exception:
            db.rollback()

        enseignants = []
        for ens in tous_enseignants:
            classes_attribuees_str = str(getattr(ens, "classes_attribuees", "") or getattr(ens, "classes", "")).lower()
            est_lycee = False
            est_college = False
            
            for c in classes_db:
                lib_c = str(getattr(c, "libelle", "")).lower()
                cyc_c = str(getattr(c, "cycle", "")).lower()
                if lib_c and lib_c in classes_attribuees_str:
                    if "lycée" in cyc_c or "lycee" in cyc_c or any(n in lib_c for n in ["2de", "premiere", "terminale", "1ere", "tle"]):
                        est_lycee = True
                    else:
                        est_college = True

            if not est_lycee and not est_college:
                if any(n in classes_attribuees_str for n in ["2de", "premiere", "terminale", "1ere", "tle", "lycée", "lycee"]):
                    est_lycee = True
                else:
                    est_college = True

            if cycle_filtre == "Lycée Uniquement" and not est_lycee:
                continue
            if cycle_filtre == "Collège Uniquement" and not est_college:
                continue
                
            enseignants.append(ens)

        if not enseignants:
            st.warning(f"Aucun enseignant trouvé pour le filtre : {cycle_filtre}")
            return

        # --- SYNCHRONISATION AUTOMATIQUE UNIVERSELLE ---
        parties_mois = mois.split()
        nom_mois = parties_mois[0].lower() if len(parties_mois) > 0 else "octobre"
        annee_mois = int(parties_mois[1]) if len(parties_mois) > 1 else 2026
        
        mapping_mois = {
            "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12,
            "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4,
            "mai": 5, "juin": 6, "juillet": 7, "aout": 8
        }
        num_mois = mapping_mois.get(nom_mois, 10)

        for ens in enseignants:
            enreg_mois = db.query(HeureVacataireMois).filter(
                HeureVacataireMois.enseignant_id == ens.id,
                HeureVacataireMois.mois == mois
            ).first()

            if not enreg_mois:
                heures_calculees = 0.0
                try:
                    mat_attr_str = str(getattr(ens, "matieres_attribuees", "") or getattr(ens, "matieres", "") or "").lower()
                    
                    cahier_entries = db.query(CahierTexte).filter(
                        CahierTexte.school_id == school_id if school_id else True
                    ).all()

                    for entry in cahier_entries:
                        if entry.date_cours and entry.date_cours.month == num_mois and entry.date_cours.year == annee_mois:
                            mat_obj = db.query(Matiere).filter(Matiere.id == entry.matiere_id).first() if entry.matiere_id else None
                            nom_mat_entry = str(getattr(mat_obj, "libelle", "") or getattr(mat_obj, "nom", "")).lower()
                            
                            auteur = str(getattr(entry, "auteur_saisie", "")).lower()
                            nom_ens_complet = f"{getattr(ens, 'nom', '')} {getattr(ens, 'prenom', '')}".strip().lower()

                            match_matiere = nom_mat_entry and any(m.strip() in mat_attr_str for m in nom_mat_entry.split(","))
                            match_auteur = nom_ens_complet in auteur or (ens.email and ens.email.lower() in auteur)

                            if match_matiere or match_auteur:
                                duree_str = str(getattr(entry, "duree_seance", "1"))
                                chiffres = "".join([c for c in duree_str if c.isdigit() or c == '.'])
                                heures_calculees += float(chiffres) if chiffres else 1.0
                except Exception:
                    heures_calculees = 0.0

                if heures_calculees <= 0:
                    heures_calculees = float(getattr(ens, "heures_defaut", 0.0) or 0.0)

                nouvel_enreg = HeureVacataireMois(
                    school_id=school_id if school_id else 1,
                    enseignant_id=ens.id,
                    mois=mois,
                    heures=heures_calculees
                )
                db.add(nouvel_enreg)
                db.commit()

        st.markdown(f"### Gestion des heures — {cycle_filtre} ({mois})")
        st.info(f"Les heures ci-dessous sont synchronisées automatiquement avec le **Cahier de Texte** (peu importe l'auteur de la saisie). Vous pouvez les ajuster manuellement si besoin.")

        heures_saisies = {}
        
        with st.form(key=f"form_saisie_heures_{mois}"):
            for ens in enseignants:
                nom_ens = f"{getattr(ens, 'nom', '')} {getattr(ens, 'prenom', '')}".strip() or getattr(ens, "name", "Enseignant")
                mat_attr_str = getattr(ens, "matieres_attribuees", None) or getattr(ens, "matieres", None) or getattr(ens, "matiere", None)
                matiere_ens = str(mat_attr_str).strip() if mat_attr_str else "Matière non spécifiée"
                
                enreg_mois = db.query(HeureVacataireMois).filter(
                    HeureVacataireMois.enseignant_id == ens.id,
                    HeureVacataireMois.mois == mois
                ).first()
                valeur_actuelle = enreg_mois.heures if enreg_mois else 0.0

                c1, c2, c3 = st.columns([3, 2, 2])
                with c1:
                    st.text(f"Agent: {nom_ens}")
                with c2:
                    st.text(f"Matière: {matiere_ens}")
                with c3:
                    heures_saisies[ens.id] = st.number_input(
                        f"Heures {nom_ens}", 
                        min_value=0.0, 
                        max_value=300.0, 
                        value=float(valeur_actuelle),
                        step=1.0,
                        label_visibility="collapsed"
                    )
            
            submitted = st.form_submit_button("💾 Enregistrer / Mettre à jour les heures", type="primary")
            if submitted:
                for ens_id, h_val in heures_saisies.items():
                    enreg = db.query(HeureVacataireMois).filter(
                        HeureVacataireMois.enseignant_id == ens_id,
                        HeureVacataireMois.mois == mois
                    ).first()
                    
                    if enreg:
                        enreg.heures = h_val
                    else:
                        nouvel_enreg = HeureVacataireMois(
                            school_id=school_id if school_id else 1,
                            enseignant_id=ens_id,
                            mois=mois,
                            heures=h_val
                        )
                        db.add(nouvel_enreg)
                db.commit()
                st.success(f"✅ Heures mises à jour pour le mois de **{mois}** avec succès !")
                st.rerun()

        lignes_html = ""
        total_heures_global = 0
        total_net_global = 0
        lignes_paie_data = []

        for ens in enseignants:
            nom_ens = f"{getattr(ens, 'nom', '')} {getattr(ens, 'prenom', '')}".strip() or getattr(ens, "name", "Enseignant")
            
            enreg_mois = db.query(HeureVacataireMois).filter(
                HeureVacataireMois.enseignant_id == ens.id,
                HeureVacataireMois.mois == mois
            ).first()
            heures_realisees = enreg_mois.heures if enreg_mois else 0.0
            
            if heures_realisees <= 0:
                continue

            matieres_set = set()
            mat_attr_str = getattr(ens, "matieres_attribuees", None) or getattr(ens, "matieres", None) or getattr(ens, "matiere", None)
            if mat_attr_str and str(mat_attr_str).strip() and str(mat_attr_str).lower() != "aucune":
                for m in str(mat_attr_str).split(","):
                    if m.strip():
                        matieres_set.add(m.strip().title())

            matiere_ens = ", ".join(matieres_set) if matieres_set else "Matière non spécifiée"
            retenue = float(getattr(ens, "retenue", 0.0) or 0.0)
            acompte_base = float(getattr(ens, "acompte", 0.0) or 0.0)
            
            taux_base_defaut = float(getattr(ens, "taux_horaire", 0.0) or 0.0)
            if taux_base_defaut > 0:
                taux_horaire = taux_base_defaut
            else:
                taux_horaire = 2000.0 if cycle_filtre == "Lycée Uniquement" else 1500.0

            brut = heures_realisees * taux_horaire
            net_a_payer = max(0.0, brut - retenue - acompte_base)

            lignes_paie_data.append({
                "nom": nom_ens,
                "matiere": matiere_ens,
                "heures": heures_realisees,
                "taux": taux_horaire,
                "brut": brut,
                "retenue": retenue,
                "acompte": acompte_base,
                "net": net_a_payer
            })

        if not lignes_paie_data:
            lignes_html = '<tr><td colspan="10" style="text-align: center; color: gray;">Aucune heure enregistrée ou validée pour ce mois.</td></tr>'
        else:
            for i, row in enumerate(lignes_paie_data, 1):
                total_heures_global += row["heures"]
                total_net_global += row["net"]
                lignes_html += f"""
                <tr>
                    <td style="text-align: center;">{i}</td>
                    <td><b>{row["nom"]}</b></td>
                    <td>{row["matiere"]}</td>
                    <td style="text-align: center;">{row["heures"]:g} h</td>
                    <td style="text-align: right; white-space: nowrap;">{format_taux(row["taux"])}</td>
                    <td style="text-align: right; white-space: nowrap;">{format_fcfa(row["brut"])}</td>
                    <td style="text-align: right; white-space: nowrap;">{format_fcfa(row["retenue"])}</td>
                    <td style="text-align: right; white-space: nowrap;">{format_fcfa(row["acompte"])}</td>
                    <td style="text-align: right; white-space: nowrap; background-color: #f8fafc;"><b>{format_fcfa(row["net"])}</b></td>
                    <td style="height: 35px;"></td>
                </tr>
                """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                @page {{ size: A4 landscape; margin: 10mm; }}
                @media print {{
                    body {{ background: #FFFFFF; margin: 0; }}
                    .no-print {{ display: none !important; }}
                    .page {{ border: none !important; box-shadow: none !important; width: 100% !important; padding: 0 !important; }}
                }}
                body {{ background: #f0f2f5; font-family: Arial, sans-serif; padding: 10px 0; }}
                .print-container {{ text-align: center; margin-bottom: 15px; }}
                .print-btn {{ background-color: #ff8800; color: white; padding: 10px 24px; font-size: 14px; font-weight: bold; border: none; border-radius: 6px; cursor: pointer; }}
                .page {{ width: 277mm; min-height: 180mm; margin: 0 auto; background: #FFFFFF; padding: 12mm; border: 2px solid #000080; box-sizing: border-box; }}
                table {{ width: 100%; border-collapse: collapse; font-size: 0.75rem; margin-top: 10px; }}
                th, td {{ border: 1px solid #000080; padding: 6px 8px; }}
                th {{ background-color: #800020; color: #FFFFFF; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="print-container no-print"><button class="print-btn" onclick="window.print()">🖨️ Imprimer l'État de Paie Vacataires</button></div>
            <div class="page">
                <table>
                    <tr>
                        <td style="border: none; font-size: 0.8rem; font-weight: bold;">{nom_ecole}<br>{adresse_ecole}</td>
                        <td style="border: none; text-align: right; font-size: 0.8rem;"><b>ÉTAT DE PAIE — VACATAIRES ({cycle_filtre.upper()})</b><br>Mois : <b>{mois}</b><br>Date : <b>{date_paie.strftime('%d/%m/%Y')}</b></td>
                    </tr>
                </table>
                <table>
                    <thead><tr><th>N°</th><th>Nom & Prénom</th><th>Matières</th><th>Heures</th><th>Taux</th><th>Montant Brut</th><th>Retenues</th><th>Acomptes</th><th>Net à Payer</th><th>Signature</th></tr></thead>
                    <tbody>{lignes_html}</tbody>
                    <tfoot><tr style="background-color: #000080; color: #FFFFFF; font-weight: bold;"><td colspan="3" style="text-align: right;">TOTAUX :</td><td style="text-align: center;">{total_heures_global:g} h</td><td colspan="4" style="text-align: right;">TOTAL GÉNÉRAL NET :</td><td style="text-align: right; white-space: nowrap;">{format_fcfa(total_net_global)} FCFA</td><td></td></tr></tfoot>
                </table>
            </div>
        </body>
        </html>
        """
        components.html(html_content, height=620, scrolling=True)
    except Exception as e:
        db.rollback()
        st.error(f"Erreur : {e}")
    finally:
        db.close()

def afficher_paie():
    st.subheader("Édition des États de Paie Mensuels")
    st.markdown("Générez et imprimez les états récapitulatifs globaux directement connectés aux données de l'établissement.")
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        type_etat = st.radio("Catégorie :", ["Personnel Administratif", "Enseignants Vacataires"], horizontal=True)
    with col2:
        mois_selectionne = st.selectbox("Mois :", ["Septembre 2026", "Octobre 2026", "Novembre 2026", "Décembre 2026", "Janvier 2027", "Février 2027", "Mars 2027", "Avril 2027", "Mai 2027", "Juin 2027", "Juillet 2027", "Août 2027"], index=1)
    with col3:
        date_versement = st.date_input("Date de versement :", value=datetime.today())
    with col4:
        cycle_selectionne = st.selectbox("Filtrer par cycle :", ["Tous les cycles", "Collège Uniquement", "Lycée Uniquement"])

    st.markdown("---")

    if type_etat == "Personnel Administratif":
        afficher_etat_paie_administration(mois=mois_selectionne, date_paie=date_versement)
    else:
        afficher_etat_paie_vacataires(mois=mois_selectionne, date_paie=date_versement, cycle_filtre=cycle_selectionne)

afficher_gestion_paie = afficher_paie