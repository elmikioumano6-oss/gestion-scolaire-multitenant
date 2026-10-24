from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components
from database.db_config import SessionLocal
from database.models import CahierTexte, Enseignant, School, User, Classe, Matiere, Depense

def format_fcfa(montant):
    """Formate un montant en FCFA avec un espace comme séparateur de milliers."""
    return f"{int(round(montant)):,}".replace(",", " ")

def format_taux(montant):
    """Formate un taux horaire sans espace pour tenir sur une seule ligne."""
    return str(int(round(montant)))

def est_prof_lycee(ens_obj, classes_attribuees_ens):
    """Détermine rigoureusement si un enseignant appartient au Lycée."""
    txt_ens = f"{getattr(ens_obj, 'classes_attribuees', '')} {getattr(ens_obj, 'classes', '')} {getattr(ens_obj, 'matieres_attribuees', '')} {classes_attribuees_ens}".lower()
    mots_cles_lycee = ["lycée", "lycee", "2de", "2nd", "seconde", "1ere", "1ère", "premiere", "terminale", "tle"]
    mots_cles_college = ["collège", "college", "6eme", "6ème", "5eme", "5ème", "4eme", "4ème", "3eme", "3ème"]
    
    is_lycee = any(kw in txt_ens for kw in mots_cles_lycee)
    is_college = any(kw in txt_ens for kw in mots_cles_college)
    
    if is_lycee and not is_college:
        return True
    return is_lycee

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

                lignes_html += """
                <tr>
                    <td style="text-align: center;">{}</td>
                    <td><b>{}</b></td>
                    <td>{}</td>
                    <td style="text-align: right; white-space: nowrap;">{}</td>
                    <td style="text-align: right; white-space: nowrap;">{}</td>
                    <td style="text-align: right; white-space: nowrap;">{}</td>
                    <td style="text-align: right; white-space: nowrap; background-color: #f8fafc;"><b>{}</b></td>
                    <td style="height: 35px;"></td>
                </tr>
                """.format(i, nom_complet, str(poste).capitalize(), format_fcfa(salaire_base), format_fcfa(primes), format_fcfa(acompte), format_fcfa(net_a_payer))

        html_template = """
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
                .print-btn {{ background-color: #000080; color: white; padding: 10px 24px; font-size: 14px; font-weight: bold; border: none; border-radius: 6px; cursor: pointer; }}
                .page {{ width: 277mm; min-height: 180mm; margin: 0 auto; background: #FFFFFF; padding: 12mm; border: 1.5px solid #000080; box-sizing: border-box; }}
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
                        <td style="border: none; font-size: 0.8rem; font-weight: bold;">{ecole}<br>{adresse}</td>
                        <td style="border: none; text-align: right; font-size: 0.8rem;"><b>ÉTAT DE PAIE — ADMINISTRATIF</b><br>Mois : <b>{mois}</b><br>Date : <b>{date_format}</b></td>
                    </tr>
                </table>
                <table>
                    <thead><tr><th>N°</th><th>Nom & Prénom</th><th>Poste</th><th>Salaire de Base</th><th>Primes</th><th>Acomptes</th><th>Net à Payer</th><th>Signature</th></tr></thead>
                    <tbody>{lignes}</tbody>
                    <tfoot><tr style="background-color: #000080; color: #FFFFFF; font-weight: bold;"><td colspan="6" style="text-align: right;">TOTAL GÉNÉRAL :</td><td style="text-align: right; white-space: nowrap;">{total_net} FCFA</td><td></td></tr></tfoot>
                </table>
            </div>
        </body>
        </html>
        """
        html_content = html_template.format(
            ecole=nom_ecole, adresse=adresse_ecole, mois=mois,
            date_format=date_paie.strftime('%d/%m/%Y'), lignes=lignes_html,
            total_net=format_fcfa(total_net_global)
        )
        components.html(html_content, height=620, scrolling=True)
    except Exception as e:
        db.rollback()
        st.error(f"Erreur technique (Administration) : {e}")
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

        if not tous_enseignants:
            st.warning("Aucun enseignant enregistré.")
            return

        dict_enseignants = {e.id: e for e in tous_enseignants}
        classes_db = db.query(Classe).filter(Classe.school_id == school_id).all() if school_id else db.query(Classe).all()
        dict_classes_id = {c.id: c for c in classes_db}

        matieres_db = db.query(Matiere).filter(Matiere.school_id == school_id).all() if school_id else db.query(Matiere).all()
        dict_matieres_id = {m.id: m for m in matieres_db}

        mapping_mois = {
            "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12,
            "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4,
            "mai": 5, "juin": 6, "juillet": 7, "aout": 8
        }
        parties_mois = mois.split()
        nom_mois = parties_mois[0].lower() if len(parties_mois) > 0 else "octobre"
        annee_mois = int(parties_mois[1]) if len(parties_mois) > 1 else 2026
        num_mois = mapping_mois.get(nom_mois, 10)

        cahier_query = db.query(CahierTexte)
        if school_id:
            cahier_query = cahier_query.filter(CahierTexte.school_id == school_id)
        cahier_entries = cahier_query.all()

        heures_par_cycle = {ens.id: {"Collège": 0.0, "Lycée": 0.0} for ens in tous_enseignants}
        cycles_actifs_ens = {ens.id: set() for ens in tous_enseignants}

        for entry in cahier_entries:
            date_c = getattr(entry, "date_cours", None)
            if not date_c:
                continue
            
            if isinstance(date_c, str):
                parsed_date = None
                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
                    try:
                        parsed_date = datetime.strptime(date_c, fmt)
                        break
                    except ValueError:
                        continue
                date_c = parsed_date

            if not date_c or not hasattr(date_c, "month") or not hasattr(date_c, "year"):
                continue

            if date_c.month != num_mois or date_c.year != annee_mois:
                continue

            classe_entry = dict_classes_id.get(getattr(entry, "classe_id", None))
            
            matched_ens_id = getattr(entry, "enseignant_id", None)
            
            if not matched_ens_id or str(getattr(entry, "auteur_saisie", "")).lower() in ["admin", "admin_rahmat", "directeur", "censeur"]:
                matiere_entree_id = getattr(entry, "matiere_id", None)
                classe_entree_id = getattr(entry, "classe_id", None)
                
                if matiere_entree_id and classe_entree_id:
                    matiere_obj_db = dict_matieres_id.get(matiere_entree_id)
                    nom_mat_db = str(getattr(matiere_obj_db, "libelle", "") or getattr(matiere_obj_db, "nom", "")).lower() if matiere_obj_db else ""
                    
                    for ens in tous_enseignants:
                        mat_attr = str(getattr(ens, "matieres_attribuees", "") or getattr(ens, "matieres", "")).lower()
                        cls_attr = str(getattr(ens, "classes_attribuees", "") or getattr(ens, "classes", "")).lower()
                        
                        if classe_entry and (classe_entry.libelle.lower() in cls_attr) and (nom_mat_db and nom_mat_db in mat_attr):
                            matched_ens_id = ens.id
                            break
            
            if not matched_ens_id:
                texte_entree = f"{getattr(entry, 'auteur_saisie', '')} {getattr(entry, 'cours', '')} {getattr(entry, 'contenu', '')}".lower()
                for ens in tous_enseignants:
                    nom = str(getattr(ens, "nom", "") or "").strip().lower()
                    prenom = str(getattr(ens, "prenom", "") or "").strip().lower()
                    if (nom and nom in texte_entree) or (prenom and prenom in texte_entree):
                        matched_ens_id = ens.id
                        break

            if not matched_ens_id:
                continue

            ens_obj = dict_enseignants.get(matched_ens_id)
            nom_classe_str = str(getattr(classe_entry, "cycle", "") or getattr(classe_entry, "libelle", "")).lower() if classe_entry else ""
            mots_lycee = ["lycée", "lycee", "2de", "2nd", "seconde", "1ere", "1ère", "premiere", "terminale", "tle"]
            
            is_lycee_cours = any(kw in nom_classe_str for kw in mots_lycee) or (classe_entry and str(getattr(classe_entry, "cycle", "")).lower() == "lycée")
            cycle_nom = "Lycée" if is_lycee_cours else "Collège"

            duree_str = str(getattr(entry, "duree_seance", "1"))
            chiffres = "".join([c for c in duree_str if c.isdigit() or c == '.'])
            duree_val = float(chiffres) if chiffres else 1.0

            if matched_ens_id not in heures_par_cycle:
                heures_par_cycle[matched_ens_id] = {"Collège": 0.0, "Lycée": 0.0}
            heures_par_cycle[matched_ens_id][cycle_nom] += duree_val
            cycles_actifs_ens[matched_ens_id].add(cycle_nom)

        lignes_paie_data = []
        for ens_id, cycles_dict in heures_par_cycle.items():
            ens = dict_enseignants.get(ens_id)
            if not ens:
                continue
            nom_ens = f"{getattr(ens, 'nom', '')} {getattr(ens, 'prenom', '')}".strip() or "Enseignant"
            mat_attr = getattr(ens, "matieres_attribuees", None) or getattr(ens, "matieres", None) or "Matière non spécifiée"
            retenue = float(getattr(ens, "retenue", 0.0) or 0.0)
            acompte_base = float(getattr(ens, "acompte", 0.0) or 0.0)

            classes_attr_ens = str(getattr(ens, "classes_attribuees", "") or getattr(ens, "classes", ""))
            is_prof_lyc = est_prof_lycee(ens, classes_attr_ens)
            cycle_principal = "Lycée" if is_prof_lyc else "Collège"

            has_college = cycles_dict["Collège"] > 0
            has_lycee = cycles_dict["Lycée"] > 0

            if not has_college and not has_lycee:
                if cycle_filtre == "Collège Uniquement" and cycle_principal != "Collège":
                    continue
                if cycle_filtre == "Lycée Uniquement" and cycle_principal != "Lycée":
                    continue

                taux_horaire = 2000.0 if cycle_principal == "Lycée" else 1500.0
                net_a_payer = max(0.0, 0.0 - retenue - acompte_base)
                lignes_paie_data.append({
                    'nom': f"{nom_ens} ({cycle_principal})",
                    'matiere': f"{mat_attr} — {cycle_principal}",
                    'heures': 0.0,
                    'taux': taux_horaire,
                    'brut': 0.0,
                    'retenue': retenue if cycle_principal == "Collège" else 0.0,
                    'acompte': acompte_base if cycle_principal == "Collège" else 0.0,
                    'net': net_a_payer
                })
            else:
                for cycle_nom in ["Collège", "Lycée"]:
                    if cycle_filtre == "Lycée Uniquement" and cycle_nom != "Lycée":
                        continue
                    if cycle_filtre == "Collège Uniquement" and cycle_nom != "Collège":
                        continue

                    heures = cycles_dict[cycle_nom]
                    
                    if heures > 0 or (cycle_nom == cycle_principal and sum(cycles_dict.values()) == 0):
                        taux_horaire = 2000.0 if cycle_nom == "Lycée" else 1500.0
                        brut = heures * taux_horaire
                        net_a_payer = max(0.0, brut - retenue - acompte_base if cycle_nom == "Collège" else brut)

                        lignes_paie_data.append({
                            'nom': f"{nom_ens} ({cycle_nom})",
                            'matiere': f"{mat_attr} — {cycle_nom}",
                            'heures': heures,
                            'taux': taux_horaire,
                            'brut': brut,
                            'retenue': retenue if cycle_nom == "Collège" else 0.0,
                            'acompte': acompte_base if cycle_nom == "Collège" else 0.0,
                            'net': net_a_payer
                        })

        st.markdown(f"### 🎓 Gestion des Heures & Paie — Vacataires ({cycle_filtre} - {mois})")
        
        if not lignes_paie_data:
            st.info(f"ℹ️ Aucun enseignant trouvé pour le filtre : **{cycle_filtre}**.")
            return

        st.info("💡 **État Officiel de Paie :** Filtrage rigoureux par cycle (Collège / Lycée).")

        lignes_html = ""
        total_heures_global = 0
        total_net_global = 0

        for i, row in enumerate(lignes_paie_data, 1):
            total_heures_global += row['heures']
            total_net_global += row['net']

            lignes_html += """
            <tr>
                <td style="text-align: center;">{}</td>
                <td><b>{}</b></td>
                <td>{}</td>
                <td style="text-align: center;">{:g} h</td>
                <td style="text-align: right; white-space: nowrap;">{}</td>
                <td style="text-align: right; white-space: nowrap;">{}</td>
                <td style="text-align: right; white-space: nowrap;">{}</td>
                <td style="text-align: right; white-space: nowrap;">{}</td>
                <td style="text-align: right; white-space: nowrap; background-color: #f8fafc;"><b>{}</b></td>
                <td style="height: 35px;"></td>
            </tr>
            """.format(
                i, row['nom'], row['matiere'], row['heures'],
                format_taux(row['taux']), format_fcfa(row['brut']),
                format_fcfa(row['retenue']), format_fcfa(row['acompte']),
                format_fcfa(row['net'])
            )

        html_template = """
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
                .print-btn {{ background-color: #000080; color: white; padding: 10px 24px; font-size: 14px; font-weight: bold; border: none; border-radius: 6px; cursor: pointer; }}
                .page {{ width: 277mm; min-height: 180mm; margin: 0 auto; background: #FFFFFF; padding: 12mm; border: 1.5px solid #000080; box-sizing: border-box; }}
                table {{ width: 100%; border-collapse: collapse; font-size: 0.75rem; margin-top: 10px; }}
                th, td {{ border: 1px solid #000080; padding: 6px 8px; }}
                th {{ background-color: #800020; color: #FFFFFF; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="print-container no-print"><button class="print-btn" onclick="window.print()">🖨️ Imprimer l'État Officiel de Paie — Vacataires ({cycle})</button></div>
            <div class="page">
                <table>
                    <tr>
                        <td style="border: none; font-size: 0.8rem; font-weight: bold;">{ecole}<br>{adresse}</td>
                        <td style="border: none; text-align: right; font-size: 0.8rem;"><b>ÉTAT RÉCAPITULATIF DE PAIE — VACATAIRES ({cycle_upper})</b><br>Période : <b>{mois}</b><br>Date d'édition : <b>{date_format}</b></td>
                    </tr>
                </table>
                <table>
                    <thead><tr><th>N°</th><th>Nom & Prénom</th><th>Matières Enseignées</th><th>Volume Horaire</th><th>Taux Horaire</th><th>Montant Brut</th><th>Retenues</th><th>Acomptes</th><th>Net à Payer (FCFA)</th><th>Visa & Signature</th></tr></thead>
                    <tbody>{lignes}</tbody>
                    <tfoot><tr style="background-color: #000080; color: #FFFFFF; font-weight: bold;"><td colspan="3" style="text-align: right;">TOTAUX GLOBAUX :</td><td style="text-align: center;">{total_h:g} h</td><td colspan="4" style="text-align: right;">TOTAL GÉNÉRAL NET :</td><td style="text-align: right; white-space: nowrap;">{total_net_str} FCFA</td><td></td></tr></tfoot>
                </table>
            </div>
        </body>
        </html>
        """
        
        html_content = html_template.format(
            cycle=cycle_filtre,
            cycle_upper=cycle_filtre.upper(),
            ecole=nom_ecole,
            adresse=adresse_ecole,
            mois=mois,
            date_format=date_paie.strftime('%d/%m/%Y'),
            lignes=lignes_html,
            total_h=total_heures_global,
            total_net_str=format_fcfa(total_net_global)
        )

        components.html(html_content, height=620, scrolling=True)
    except Exception as e:
        db.rollback()
        st.error(f"Erreur technique (Vacataires) : {e}")
    finally:
        db.close()

def afficher_paie():
    st.subheader("Édition des États de Paie Mensuels")
    st.markdown("Générez et imprimez les états récapitulatifs globaux directement connectés aux données de l'établissement.")
    st.markdown("---")

    try:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            # Utilisation d'un sélecteur à boutons clairs et explicites
            type_etat = st.radio("Catégorie :", ["Personnel Administratif", "Enseignants Vacataires"], horizontal=True, key="radio_type_etat_paie")
        with col2:
            mois_selectionne = st.selectbox("Mois :", ["Septembre 2026", "Octobre 2026", "Novembre 2026", "Décembre 2026", "Janvier 2027", "Février 2027", "Mars 2027", "Avril 2027", "Mai 2027", "Juin 2027", "Juillet 2027", "Août 2027"], index=1, key="select_mois_paie")
        with col3:
            date_versement = st.date_input("Date de versement :", value=datetime.today(), key="date_versement_paie")
        with col4:
            cycle_selectionne = st.selectbox("Filtrer par cycle :", ["Tous les cycles", "Collège Uniquement", "Lycée Uniquement"], key="select_cycle_paie")
    except Exception as e:
        st.error(f"Erreur lors du rendu des filtres : {e}")
        return

    st.markdown("---")

    try:
        # Utilisation d'une condition robuste basée sur la présence du mot clé dans le choix
        if "Administratif" in str(type_etat):
            afficher_etat_paie_administration(mois=mois_selectionne, date_paie=date_versement)
        else:
            afficher_etat_paie_vacataires(mois=mois_selectionne, date_paie=date_versement, cycle_filtre=cycle_selectionne)
    except Exception as e:
        st.error(f"Erreur lors de l'exécution de l'état de paie : {e}")

afficher_gestion_paie = afficher_paie