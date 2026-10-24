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
        cycles_detectes = {ens.id: set() for ens in tous_enseignants}

        mots_lycee_kw = ["lycée", "lycee", "2de", "2nd", "seconde", "1ere", "1ère", "premiere", "terminale", "tle"]
        mots_college_kw = ["collège", "college", "6eme", "6ème", "5eme", "5ème", "4eme", "4ème", "3eme", "3ème"]

        # ÉTAPE 1 : Détermination rigoureuse et exclusive des cycles par enseignant via ses classes réelles
        for ens in tous_enseignants:
            txt_prof = f"{getattr(ens, 'classes_attribuees', '')} {getattr(ens, 'classes', '')} {getattr(ens, 'matieres_attribuees', '')}".lower()
            
            is_lycee = any(kw in txt_prof for kw in mots_lycee_kw) or any(k in txt_prof for k in ["tle", "2de", "2nd", "seconde", "1ere", "1ère", "premiere", "terminale"])
            is_college = any(kw in txt_prof for kw in mots_college_kw) or any(k in txt_prof for k in ["6eme", "6ème", "5eme", "5ème", "4eme", "4ème", "3eme", "3ème"])

            # Si l'enseignant n'a explicitement que des classes de lycée (ex: Tle D), on force uniquement le Lycée
            if is_lycee and not is_college:
                cycles_detectes[ens.id].add("Lycée")
            elif is_college and not is_lycee:
                cycles_detectes[ens.id].add("Collège")
            else:
                if is_lycee:
                    cycles_detectes[ens.id].add("Lycée")
                if is_college:
                    cycles_detectes[ens.id].add("Collège")

        # ÉTAPE 2 : Analyse des entrées réelles du cahier de texte pour ventiler les heures
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

            classe_str = f"{getattr(classe_entry, 'cycle', '')} {getattr(classe_entry, 'libelle', '')}".lower() if classe_entry else ""
            is_lycee_cours = any(kw in classe_str for kw in mots_lycee_kw) or any(k in classe_str for k in ["tle", "2de", "2nd", "seconde", "1ere", "1ère", "premiere", "terminale"]) or (classe_entry and str(getattr(classe_entry, "cycle", "")).lower() == "lycée")
            cycle_nom = "Lycée" if is_lycee_cours else "Collège"

            duree_str = str(getattr(entry, "duree_seance", "1"))
            chiffres = "".join([c for c in duree_str if c.isdigit() or c == '.'])
            duree_val = float(chiffres) if chiffres else 1.0

            if matched_ens_id not in heures_par_cycle:
                heures_par_cycle[matched_ens_id] = {"Collège": 0.0, "Lycée": 0.0}
            
            # S'assure que l'heure va dans le cycle détecté pour cet enseignant
            if cycle_nom in cycles_detectes.get(matched_ens_id, {cycle_nom}):
                heures_par_cycle[matched_ens_id][cycle_nom] += duree_val
            else:
                # Fallback sur le cycle unique de l'enseignant si la classe saisie diffère
                primary_cycle = list(cycles_detectes[matched_ens_id])[0] if cycles_detectes[matched_ens_id] else cycle_nom
                heures_par_cycle[matched_ens_id][primary_cycle] += duree_val

        # ÉTAPE 3 : Récupération globale des acomptes depuis les dépenses
        acomptes_depenses_dict = {}
        try:
            depenses_query = db.query(Depense).filter(Depense.school_id == school_id) if school_id else db.query(Depense)
            for dep in depenses_query.all():
                libelle_dep = str(getattr(dep, "libelle", "") or getattr(dep, "motif", "") or "").lower()
                beneficiaire_dep = str(getattr(dep, "beneficiaire", "") or "").lower()
                if any(k in libelle_dep for k in ["acompte", "avance", "paie"]):
                    montant_dep = float(getattr(dep, "montant", 0.0) or 0.0)
                    for ens in tous_enseignants:
                        nom_p = str(getattr(ens, "nom", "")).strip().lower()
                        prenom_p = str(getattr(ens, "prenom", "")).strip().lower()
                        nom_complet_ens = f"{nom_p} {prenom_p}".strip()
                        if (nom_p and nom_p in libelle_dep) or (nom_p and nom_p in beneficiaire_dep) or \
                           (prenom_p and prenom_p in libelle_dep) or (prenom_p and prenom_p in beneficiaire_dep) or \
                           (nom_complet_ens and nom_complet_ens in libelle_dep):
                            acomptes_depenses_dict[ens.id] = acomptes_depenses_dict.get(ens.id, 0.0) + montant_dep
        except Exception:
            db.rollback()

        lignes_paie_data = []
        for ens_id, cycles_dict in heures_par_cycle.items():
            ens = dict_enseignants.get(ens_id)
            if not ens:
                continue
            nom_ens = f"{getattr(ens, 'nom', '')} {getattr(ens, 'prenom', '')}".strip() or "Enseignant"
            mat_attr = getattr(ens, "matieres_attribuees", None) or getattr(ens, "matieres", None) or "Matière non spécifiée"
            retenue = float(getattr(ens, "retenue", 0.0) or 0.0)
            acompte_base = float(getattr(ens, "acompte", 0.0) or 0.0)
            acompte_total = acompte_base + acomptes_depenses_dict.get(ens.id, 0.0)

            # Restreint strictement aux cycles réellement détectés pour l'enseignant
            cycles_valides = cycles_detectes.get(ens_id, {"Collège"})
            if not cycles_valides:
                cycles_valides = {"Collège"}

            for cycle_nom in ["Collège", "Lycée"]:
                if cycle_nom not in cycles_valides:
                    continue

                heures = cycles_dict[cycle_nom]
                
                # On affiche la ligne si l'enseignant a des heures ou s'il est rattaché à ce cycle
                doit_afficher = (heures > 0) or (len(cycles_valides) == 1)

                if doit_afficher:
                    taux_horaire = 2000.0 if cycle_nom == "Lycée" else 1500.0
                    brut = heures * taux_horaire
                    net_a_payer = max(0.0, brut - retenue - (acompte_total if cycle_nom == list(cycles_valides)[0] else 0.0))

                    lignes_paie_data.append({
                        'cycle_ligne': cycle_nom,
                        'nom': f"{nom_ens} ({cycle_nom})",
                        'matiere': f"{mat_attr} — {cycle_nom}",
                        'heures': heures,
                        'taux': taux_horaire,
                        'brut': brut,
                        'retenue': retenue if cycle_nom == "Collège" else 0.0,
                        'acompte': acompte_total if cycle_nom == list(cycles_valides)[0] else 0.0,
                        'net': net_a_payer
                    })

        lignes_filtrees = []
        for row in lignes_paie_data:
            if cycle_filtre == "Lycée Uniquement" and row['cycle_ligne'] != "Lycée":
                continue
            if cycle_filtre == "Collège Uniquement" and row['cycle_ligne'] != "Collège":
                continue
            lignes_filtrees.append(row)

        st.markdown(f"### 🎓 Gestion des Heures & Paie — Vacataires ({cycle_filtre} - {mois})")
        
        if not lignes_filtrees:
            st.info(f"ℹ️ Aucun enseignant trouvé pour le filtre : **{cycle_filtre}**.")
            return

        lignes_html = ""
        total_heures_global = 0
        total_net_global = 0

        for i, row in enumerate(lignes_filtrees, 1):
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
            type_etat = st.radio("Catégorie :", ["Personnel Administratif", "Enseignants Vacataires"], horizontal=True, key="radio_type_etat_paie_v6")
        with col2:
            mois_selectionne = st.selectbox("Mois :", ["Septembre 2026", "Octobre 2026", "Novembre 2026", "Décembre 2026", "Janvier 2027", "Février 2027", "Mars 2027", "Avril 2027", "Mai 2027", "Juin 2027", "Juillet 2027", "Août 2027"], index=1, key="select_mois_paie_v6")
        with col3:
            date_versement = st.date_input("Date de versement :", value=datetime.today(), key="date_versement_paie_v6")
        with col4:
            cycle_selectionne = st.selectbox("Filtrer par cycle :", ["Tous les cycles", "Collège Uniquement", "Lycée Uniquement"], key="select_cycle_paie_v6")
    except Exception as e:
        st.error(f"Erreur lors du rendu des filtres : {e}")
        return

    st.markdown("---")

    try:
        if type_etat == "Personnel Administratif":
            afficher_etat_paie_administration(mois=mois_selectionne, date_paie=date_versement)
        else:
            afficher_etat_paie_vacataires(mois=mois_selectionne, date_paie=date_versement, cycle_filtre=cycle_selectionne)
    except Exception as e:
        st.error(f"Erreur lors de l'exécution de l'état de paie : {e}")

afficher_gestion_paie = afficher_paie