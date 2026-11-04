from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components
from database.db_config import SessionLocal
from database.models import CahierTexte, Enseignant, School, User, Classe, Matiere, Depense
from database.audit import log_action_erp

def format_fcfa(montant):
    return f"{int(round(montant)):,}".replace(",", " ")

def format_taux(montant):
    return str(int(round(montant)))

def parse_date_securisee(date_c):
    if not date_c:
        return None
    if isinstance(date_c, datetime):
        return date_c
    if hasattr(date_c, "year") and hasattr(date_c, "month"):
        try:
            return datetime(date_c.year, date_c.month, getattr(date_c, "day", 1))
        except Exception:
            pass
    if not isinstance(date_c, str):
        try:
            return datetime.combine(date_c, datetime.min.time())
        except Exception:
            return None
    date_str = str(date_c).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            pass
    return None

def is_cours_lycee(classe_entry, mots_lycee_kw):
    if not classe_entry:
        return False
    cycle_str = f"{getattr(classe_entry, 'cycle', '')} {getattr(classe_entry, 'libelle', '')}".lower()
    cycle_db = str(getattr(classe_entry, 'cycle', '')).lower()
    cond_kw = any(kw in cycle_str for kw in mots_lycee_kw)
    cond_tag = any(k in cycle_str for k in ["tle", "2de", "2nd", "seconde", "1ere", "1ère", "premiere", "terminale"])
    cond_db = cycle_db in ["lycee", "lycée"]
    return cond_kw or cond_tag or cond_db

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
                depenses_query = db.query(Depense).filter(Depense.school_id == school_id) if school_id else db.query(Depense)
                for dep in depenses_query.all():
                    libelle_dep = str(getattr(dep, "libelle", "") or getattr(dep, "motif", "") or "").lower()
                    beneficiaire_dep = str(getattr(dep, "beneficiaire", "") or "").lower()
                    if nom_complet.lower() in libelle_dep or nom_complet.lower() in beneficiaire_dep:
                        if any(k in libelle_dep for k in ["acompte", "avance", "paie"]):
                            acompte_depenses += float(getattr(dep, "montant", 0.0) or 0.0)
                acompte = float(getattr(p, "acompte", 0.0) or 0.0) + acompte_depenses
                poste = getattr(p, "role", "Administratif")
                net_a_payer = salaire_base + primes - acompte
                total_net_global += net_a_payer
                lignes_html += f"<tr><td style='text-align: center;'>{i}</td><td><b>{nom_complet}</b></td><td>{str(poste).capitalize()}</td><td style='text-align: right;'>{format_fcfa(salaire_base)}</td><td style='text-align: right;'>{format_fcfa(primes)}</td><td style='text-align: right;'>{format_fcfa(acompte)}</td><td style='text-align: right; background-color: #f8fafc;'><b>{format_fcfa(net_a_payer)}</b></td><td></td></tr>"
        html_content = f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>@page {{ size: A4 landscape; margin: 10mm; }} body {{ font-family: Arial, sans-serif; }} table {{ width: 100%; border-collapse: collapse; font-size: 0.75rem; margin-top: 10px; }} th, td {{ border: 1px solid #000080; padding: 6px 8px; }} th {{ background-color: #800020; color: #FFFFFF; text-align: center; }}</style></head><body><div style='text-align:center; margin-bottom:15px;'><button onclick='window.print()' style='background:#000080; color:white; padding:10px 24px; font-weight:bold; border:none; border-radius:6px; cursor:pointer;'>🖨️ Imprimer</button></div><div style='width:277mm; margin:0 auto; background:#FFF; padding:12mm; border:1.5px solid #000080;'><table><tr><td style='border:none; font-weight:bold;'>{nom_ecole}<br>{adresse_ecole}</td><td style='border:none; text-align:right;'><b>ETAT DE PAIE — ADMINISTRATIF</b><br>Mois : <b>{mois}</b><br>Date : <b>{date_paie.strftime('%d/%m/%Y')}</b></td></tr></table><table><thead><tr><th>N°</th><th>Nom & Prénom</th><th>Poste</th><th>Salaire de Base</th><th>Primes</th><th>Acomptes</th><th>Net à Payer</th><th>Signature</th></tr></thead><tbody>{lignes_html}</tbody><tfoot><tr style='background:#000080; color:#FFF; font-weight:bold;'><td colspan='6' style='text-align:right;'>TOTAL GENERAL :</td><td style='text-align:right;'>{format_fcfa(total_net_global)} FCFA</td><td></td></tr></tfoot></table></div></body></html>"
        components.html(html_content, height=620, scrolling=True)
    except Exception as e:
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
        mapping_mois = {"septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12, "décembre": 12, "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7, "aout": 8, "août": 8}
        parties_mois = mois.split()
        nom_mois = parties_mois[0].lower() if len(parties_mois) > 0 else "octobre"
        annee_mois = int(parties_mois[1]) if len(parties_mois) > 1 else 2026
        num_mois = mapping_mois.get(nom_mois, 10)
        cahier_query = db.query(CahierTexte)
        if school_id:
            cahier_query = cahier_query.filter(CahierTexte.school_id == school_id)
        cahier_entries = cahier_query.all()
        heures_par_cycle = {ens.id: {"Collège": 0.0, "Lycée": 0.0} for ens in tous_enseignants}
        matieres_par_cycle = {ens.id: {"Collège": set(), "Lycée": set()} for ens in tous_enseignants}
        cycles_detectes = {ens.id: set() for ens in tous_enseignants}
        mots_lycee_kw = ["lycée", "lycee", "2de", "2nd", "seconde", "1ere", "1ère", "premiere", "terminale", "tle"]
        mots_college_kw = ["collège", "college", "6eme", "6ème", "5eme", "5ème", "4eme", "4ème", "3eme", "3ème", "6è", "5è", "4è", "3è"]
        for entry in cahier_entries:
            try:
                date_c = parse_date_securisee(getattr(entry, "date_cours", None))
                if date_c and (date_c.month != num_mois or date_c.year != annee_mois):
                    continue
                classe_entry = dict_classes_id.get(getattr(entry, "classe_id", None))
                matched_ens_id = getattr(entry, "enseignant_id", None)
                nom_mat_entry = ""
                if getattr(entry, "matiere_id", None):
                    mat_obj = dict_matieres_id.get(entry.matiere_id)
                    if mat_obj:
                        nom_mat_entry = getattr(mat_obj, "libelle", "") or getattr(mat_obj, "nom", "")
                if not matched_ens_id and classe_entry and getattr(entry, "matiere_id", None):
                    matiere_obj_db = dict_matieres_id.get(entry.matiere_id)
                    nom_mat_db = str(getattr(matiere_obj_db, "libelle", "") or getattr(matiere_obj_db, "nom", "")).lower() if matiere_obj_db else ""
                    for ens in tous_enseignants:
                        mat_attr = str(getattr(ens, "matieres_attribuees", "") or getattr(ens, "matieres", "")).lower()
                        cls_attr = str(getattr(ens, "classes_attribuees", "") or getattr(ens, "classes", "")).lower()
                        if (classe_entry.libelle.lower() in cls_attr) and (nom_mat_db and nom_mat_db in mat_attr):
                            matched_ens_id = ens.id
                            break
                if not matched_ens_id:
                    texte_entree = f"{getattr(entry, 'auteur_saisie', '')} {getattr(entry, 'contenu', '')} {getattr(entry, 'titre', '')}".lower()
                    for ens in tous_enseignants:
                        nom = str(getattr(ens, "nom", "") or "").strip().lower()
                        prenom = str(getattr(ens, "prenom", "") or "").strip().lower()
                        if (nom and nom in texte_entree) or (prenom and prenom in texte_entree):
                            matched_ens_id = ens.id
                            break
                if not matched_ens_id:
                    continue
                is_lycee_cours = is_cours_lycee(classe_entry, mots_lycee_kw)
                cycle_nom = "Lycée" if is_lycee_cours else "Collège"
                duree_str = str(getattr(entry, "duree_seance", "1"))
                chiffres = "".join([c for c in duree_str if c.isdigit() or c == '.'])
                try:
                    duree_val = float(chiffres) if chiffres else 1.0
                except ValueError:
                    duree_val = 1.0
                if matched_ens_id not in heures_par_cycle:
                    heures_par_cycle[matched_ens_id] = {"Collège": 0.0, "Lycée": 0.0}
                heures_par_cycle[matched_ens_id][cycle_nom] += duree_val
                cycles_detectes[matched_ens_id].add(cycle_nom)
                if nom_mat_entry:
                    matieres_par_cycle[matched_ens_id][cycle_nom].add(nom_mat_entry)
            except Exception:
                continue
        for ens in tous_enseignants:
            try:
                txt_prof = f"{getattr(ens, 'classes_attribuees', '')} {getattr(ens, 'classes', '')} {getattr(ens, 'matieres_attribuees', '')}".lower()
                is_lycee = any(kw in txt_prof for kw in mots_lycee_kw) or any(k in txt_prof for k in ["tle", "2de", "2nd", "seconde", "1ere", "1ère", "1re", "premiere", "terminale"])
                is_college = any(kw in txt_prof for kw in mots_college_kw) or any(k in txt_prof for k in ["6eme", "6ème", "6è", "5eme", "5ème", "5è", "4eme", "4ème", "4è", "3eme", "3ème", "3è"])
                mat_base = getattr(ens, 'matieres_attribuees', '') or getattr(ens, 'matieres', '')
                if is_lycee:
                    cycles_detectes[ens.id].add("Lycée")
                    if mat_base and not matieres_par_cycle[ens.id]["Lycée"]:
                        matieres_par_cycle[ens.id]["Lycée"].add(mat_base)
                if is_college:
                    cycles_detectes[ens.id].add("Collège")
                    if mat_base and not matieres_par_cycle[ens.id]["Collège"]:
                        matieres_par_cycle[ens.id]["Collège"].add(mat_base)
            except Exception:
                pass
        for ens_id, cycles_dict in heures_par_cycle.items():
            if cycles_dict["Lycée"] > 0:
                cycles_detectes[ens_id].add("Lycée")
            if cycles_dict["Collège"] > 0:
                cycles_detectes[ens_id].add("Collège")
        acomptes_depenses_dict = {}
        depenses_query = db.query(Depense).filter(Depense.school_id == school_id) if school_id else db.query(Depense)
        depenses_list = depenses_query.all() if depenses_query else []
        for dep in depenses_list:
            libelle_dep = str(getattr(dep, "libelle", "") or getattr(dep, "motif", "") or "").lower()
            beneficiaire_dep = str(getattr(dep, "beneficiaire", "") or "").lower()
            if any(k in libelle_dep for k in ["acompte", "avance", "paie"]):
                montant_dep = float(getattr(dep, "montant", 0.0) or 0.0)
                for ens in tous_enseignants:
                    nom_p = str(getattr(ens, "nom", "")).strip().lower()
                    prenom_p = str(getattr(ens, "prenom", "")).strip().lower()
                    nom_complet_ens = f"{nom_p} {prenom_p}".strip()
                    if (nom_p and (nom_p in libelle_dep or nom_p in beneficiaire_dep)) or (prenom_p and (prenom_p in libelle_dep or prenom_p in beneficiaire_dep)) or (nom_complet_ens and nom_complet_ens in libelle_dep):
                        acomptes_depenses_dict[ens.id] = acomptes_depenses_dict.get(ens.id, 0.0) + montant_dep
        lignes_paie_data = []
        for ens_id, cycles_dict in heures_par_cycle.items():
            ens = dict_enseignants.get(ens_id)
            if not ens:
                continue
            nom_ens = f"{getattr(ens, 'nom', '')} {getattr(ens, 'prenom', '')}".strip() or "Enseignant"
            retenue = float(getattr(ens, "retenue", 0.0) or 0.0)
            acompte_base = float(getattr(ens, "acompte", 0.0) or 0.0)
            acompte_total = acompte_base + acomptes_depenses_dict.get(ens.id, 0.0)
            cycles_valides = cycles_detectes.get(ens_id, set())
            if not cycles_valides:
                cycles_valides = {"Collège"}
            list_cycles_ordre = list(cycles_valides)
            for cycle_nom in ["Collège", "Lycée"]:
                heures = cycles_dict[cycle_nom]
                if cycle_nom not in cycles_valides and heures == 0:
                    continue
                mats_cycle = list(matieres_par_cycle.get(ens_id, {}).get(cycle_nom, set()))
                if not mats_cycle:
                    mat_attr = getattr(ens, "matieres_attribuees", None) or getattr(ens, "matieres", None) or ""
                    if mat_attr:
                        mats_cycle = [m.strip() for m in mat_attr.split(",")]
                matiere_str = ", ".join(mats_cycle) if mats_cycle else "Matière non spécifiée"
                taux_horaire = 2000.0 if cycle_nom == "Lycée" else 1500.0
                brut = heures * taux_horaire
                is_first_cycle = (cycle_nom == list_cycles_ordre[0]) if list_cycles_ordre else True
                net_a_payer = max(0.0, brut - (retenue if cycle_nom == "Collège" else 0.0) - (acompte_total if is_first_cycle else 0.0))
                lignes_paie_data.append({
                    'cycle_ligne': cycle_nom,
                    'nom': f"{nom_ens} ({cycle_nom})",
                    'matiere': f"{matiere_str} — {cycle_nom}",
                    'heures': heures,
                    'taux': taux_horaire,
                    'brut': brut,
                    'retenue': retenue if cycle_nom == "Collège" else 0.0,
                    'acompte': acompte_total if is_first_cycle else 0.0,
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
            lignes_html += f"<tr><td style='text-align: center;'>{i}</td><td><b>{row['nom']}</b></td><td>{row['matiere']}</td><td style='text-align: center;'>{row['heures']:g} h</td><td style='text-align: right;'>{format_taux(row['taux'])}</td><td style='text-align: right;'>{format_fcfa(row['brut'])}</td><td style='text-align: right;'>{format_fcfa(row['retenue'])}</td><td style='text-align: right;'>{format_fcfa(row['acompte'])}</td><td style='text-align: right; background-color: #f8fafc;'><b>{format_fcfa(row['net'])}</b></td><td></td></tr>"
        cycle_upper_str = cycle_filtre.upper()
        titre_bouton_imprimer = f"🖨️ Imprimer l'État Officiel de Paie — Vacataires ({cycle_filtre})"
        html_content = f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>@page {{ size: A4 landscape; margin: 10mm; }} body {{ font-family: Arial, sans-serif; }} table {{ width: 100%; border-collapse: collapse; font-size: 0.75rem; margin-top: 10px; }} th, td {{ border: 1px solid #000080; padding: 6px 8px; }} th {{ background-color: #800020; color: #FFFFFF; text-align: center; }}</style></head><body><div style='text-align:center; margin-bottom:15px;'><button onclick='window.print()' style='background:#000080; color:white; padding:10px 24px; font-weight:bold; border:none; border-radius:6px; cursor:pointer;'>{titre_bouton_imprimer}</button></div><div style='width:277mm; margin:0 auto; background:#FFF; padding:12mm; border:1.5px solid #000080;'><table><tr><td style='border:none; font-weight:bold;'>{nom_ecole}<br>{adresse_ecole}</td><td style='border:none; text-align:right;'><b>ÉTAT RÉCAPITULATIF DE PAIE — VACATAIRES ({cycle_upper_str})</b><br>Période : <b>{mois}</b><br>Date d'édition : <b>{date_paie.strftime('%d/%m/%Y')}</b></td></tr></table><table><thead><tr><th>N°</th><th>Nom & Prénom</th><th>Matières Enseignées</th><th>Volume Horaire</th><th>Taux Horaire</th><th>Montant Brut</th><th>Retenues</th><th>Acomptes</th><th>Net à Payer (FCFA)</th><th>Visa & Signature</th></tr></thead><tbody>{lignes_html}</tbody><tfoot><tr style='background:#000080; color:#FFF; font-weight:bold;'><td colspan='3' style='text-align:right;'>TOTAUX GLOBAUX :</td><td style='text-align:center;'>{total_heures_global:g} h</td><td colspan='4' style='text-align:right;'>TOTAL GÉNÉRAL NET :</td><td style='text-align:right;'>{format_fcfa(total_net_global)} FCFA</td><td></td></tr></tfoot></table></div></body></html>"
        components.html(html_content, height=620, scrolling=True)
    except Exception as e:
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
            type_etat = st.radio("Catégorie :", ["Personnel Administratif", "Enseignants Vacataires"], horizontal=True, key="radio_type_etat_paie_v7")
        with col2:
            mois_selectionne = st.selectbox("Mois :", ["Septembre 2026", "Octobre 2026", "Novembre 2026", "Décembre 2026", "Janvier 2027", "Février 2027", "Mars 2027", "Avril 2027", "Mai 2027", "Juin 2027", "Juillet 2027", "Août 2027"], index=1, key="select_mois_paie_v7")
        with col3:
            date_versement = st.date_input("Date de versement :", value=datetime.today(), key="date_versement_paie_v7")
        with col4:
            cycle_filtre = st.selectbox("Filtrer par cycle :", ["Tous les cycles", "Collège Uniquement", "Lycée Uniquement"], index=0, key="select_cycle_paie_v7")
        st.markdown("---")
        if type_etat == "Personnel Administratif":
            afficher_etat_paie_administration(mois_selectionne, date_versement)
        else:
            afficher_etat_paie_vacataires(mois_selectionne, date_versement, cycle_filtre)
    except Exception as e:
        st.error(f"Une erreur est survenue dans le module de paie : {e}")

afficher_fiches_de_paie = afficher_paie
afficher_paie = afficher_paie