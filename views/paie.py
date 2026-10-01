from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components
from database.db_config import SessionLocal
from database.models import CahierTexte, Enseignant, School, User


def format_fcfa(montant):
    """Formate un montant en FCFA avec un espace comme séparateur de milliers."""
    return f"{int(round(montant)):,}".replace(",", " ")


def afficher_etat_paie_administration(mois, date_paie):
    school_id = st.session_state.get("school_id")
    db = SessionLocal()
    try:
        ecole = (
            db.query(School).filter(School.id == school_id).first()
            if school_id
            else db.query(School).first()
        )
        nom_ecole = (
            ecole.nom.upper()
            if ecole
            else "COMPLEXE SCOLAIRE PRIVE RAHMAT-FH"
        )
        adresse_ecole = (
            getattr(ecole, "adresse", "QUARTIER AEROPORT NIAMEY-NIGER").upper()
            if ecole
            else "QUARTIER AEROPORT NIAMEY-NIGER"
        )
        contacts_ecole = (
            getattr(ecole, "contacts", "TEL : 99 79 71 63")
            if ecole
            else "TEL : 99 79 71 63"
        )

        utilisateurs_query = db.query(User)
        if school_id:
            utilisateurs_query = utilisateurs_query.filter(
                User.school_id == school_id
            )

        tous_utilisateurs = utilisateurs_query.all()
        
        postes_administratifs = [
            "proviseur", "directeur", "censeur", "surveillant", 
            "comptable", "econome", "gardien", "secretaire", 
            "informaticien", "planton", "admin"
        ]
        
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
            lignes_html = '<tr><td colspan="8" style="text-align: center; color: gray;">Aucun personnel administratif enregistré en base de données.</td></tr>'
        else:
            for i, p in enumerate(personnels, 1):
                salaire_base = float(getattr(p, "salaire_base", 0.0) or 0.0)
                primes = float(getattr(p, "primes_fixes", 0.0) or 0.0)
                acompte = float(getattr(p, "acompte", 0.0) or 0.0)
                poste = getattr(p, "role", "Administratif")
                nom_complet = getattr(p, "username", f"Agent {i}")

                net_a_payer = salaire_base + primes - acompte
                total_net_global += net_a_payer

                lignes_html += f"""
                <tr>
                    <td style="text-align: center;">{i}</td>
                    <td><b>{nom_complet}</b></td>
                    <td>{str(poste).capitalize()}</td>
                    <td style="text-align: right;">{format_fcfa(salaire_base)}</td>
                    <td style="text-align: right;">{format_fcfa(primes)}</td>
                    <td style="text-align: right;">{format_fcfa(acompte)}</td>
                    <td style="text-align: right; background-color: #f8fafc;"><b>{format_fcfa(net_a_payer)}</b></td>
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
                .page {{
                    width: 277mm; min-height: 180mm; margin: 0 auto; background: #FFFFFF; padding: 12mm;
                    border: 2px solid #000080; box-sizing: border-box; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }}
                table {{ width: 100%; border-collapse: collapse; font-size: 0.75rem; margin-top: 10px; }}
                th, td {{ border: 1px solid #000080; padding: 6px 8px; }}
                th {{ background-color: #800020; color: #FFFFFF; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="print-container no-print">
                <button class="print-btn" onclick="window.print()">🖨️ Imprimer l'État de Paie Administration (Paysage)</button>
            </div>
            <div class="page">
                <table style="border: none; margin-bottom: 10px;">
                    <tr>
                        <td style="border: none; font-size: 0.8rem; font-weight: bold;">
                            {nom_ecole}<br><span style="font-size: 0.7rem; font-weight: normal;">{adresse_ecole}</span>
                        </td>
                        <td style="border: none; text-align: right; font-size: 0.8rem;">
                            <b>ÉTAT DE PAIE GLOBAL — ADMINISTRATIF</b><br>
                            Mois de référence : <b>{mois}</b><br>
                            Date de versement : <b>{date_paie.strftime('%d/%m/%Y')}</b>
                        </td>
                    </tr>
                </table>
                
                <table>
                    <thead>
                        <tr>
                            <th>N°</th>
                            <th>Nom & Prénom</th>
                            <th>Poste / Fonction</th>
                            <th>Salaire de Base (FCFA)</th>
                            <th>Primes / Avantages</th>
                            <th>Acomptes Versés</th>
                            <th>Net à Payer (FCFA)</th>
                            <th>Émargement (Signature)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {lignes_html}
                    </tbody>
                    <tfoot>
                        <tr style="background-color: #000080; color: #FFFFFF; font-weight: bold;">
                            <td colspan="6" style="text-align: right; padding: 8px;">TOTAL GÉNÉRAL NET :</td>
                            <td style="text-align: right; padding: 8px;">{format_fcfa(total_net_global)} FCFA</td>
                            <td></td>
                        </tr>
                    </tfoot>
                </table>

                <div style="display: flex; justify-content: space-between; margin-top: 30px; font-size: 0.8rem;">
                    <div style="text-align: center; width: 30%;">
                        <b>Le Comptable / Économat</b><br><br><br>___________________________
                    </div>
                    <div style="text-align: center; width: 30%;">
                        <b>Le Directeur / Proviseur</b><br><br><br>___________________________
                    </div>
                    <div style="text-align: center; width: 30%;">
                        <b>Contrôle Financier</b><br><br><br>___________________________
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 25px; font-size: 0.65rem; border-top: 1px solid #000080; padding-top: 4px; font-weight: bold; color: #000080;">
                    {contacts_ecole} — Document comptable officiel pour classement physique.
                </div>
            </div>
        </body>
        </html>
        """
        components.html(html_content, height=620, scrolling=True)
    finally:
        db.close()


def afficher_etat_paie_vacataires(mois, date_paie):
    school_id = st.session_state.get("school_id")
    db = SessionLocal()
    try:
        ecole = (
            db.query(School).filter(School.id == school_id).first()
            if school_id
            else db.query(School).first()
        )
        nom_ecole = (
            ecole.nom.upper()
            if ecole
            else "COMPLEXE SCOLAIRE PRIVE RAHMAT-FH"
        )
        adresse_ecole = (
            getattr(ecole, "adresse", "QUARTIER AEROPORT NIAMEY-NIGER").upper()
            if ecole
            else "QUARTIER AEROPORT NIAMEY-NIGER"
        )
        contacts_ecole = (
            getattr(ecole, "contacts", "TEL : 99 79 71 63")
            if ecole
            else "TEL : 99 79 71 63"
        )

        enseignants_query = db.query(Enseignant)
        if school_id:
            enseignants_query = enseignants_query.filter(
                Enseignant.school_id == school_id
            )

        enseignants = enseignants_query.all()
        lignes_html = ""
        total_heures_global = 0
        total_net_global = 0

        if not enseignants:
            lignes_html = '<tr><td colspan="9" style="text-align: center; color: gray;">Aucun enseignant enregistré en base de données.</td></tr>'
        else:
            for i, ens in enumerate(enseignants, 1):
                nom_ens = f"{getattr(ens, 'nom', '')} {getattr(ens, 'prenom', '')}".strip()
                if not nom_ens:
                    nom_ens = getattr(ens, "name", f"Enseignant {i}")

                taux_horaire = float(
                    getattr(ens, "taux_horaire", 1500.0) or 1500.0
                )

                heures_realisees = 0.0
                matieres_set = set()

                mat_attr_str = (
                    getattr(ens, "matieres_attribuees", None)
                    or getattr(ens, "matieres", None)
                    or getattr(ens, "matiere", None)
                )
                if mat_attr_str and str(mat_attr_str).strip() and str(mat_attr_str).lower() != "aucune":
                    for m in str(mat_attr_str).split(","):
                        if m.strip():
                            matieres_set.add(m.strip().title())

                try:
                    cahier_query = db.query(CahierTexte).filter(
                        (CahierTexte.user_id == ens.id)
                        | (CahierTexte.auteur_saisie == nom_ens)
                    )
                    entrees_cours = cahier_query.all()
                    for cours in entrees_cours:
                        duree_str = str(getattr(cours, "duree_seance", "1 heure"))
                        try:
                            chiffre = float("".join(filter(str.isdigit, duree_str)) or 1)
                        except Exception:
                            chiffre = 1.0
                        heures_realisees += chiffre
                except Exception:
                    heures_realisees = float(
                        getattr(ens, "volume_horaire_mois", 0.0) or 0.0
                    )

                if not matieres_set:
                    matiere_ens = "Matière non spécifiée"
                else:
                    matiere_ens = ", ".join(matieres_set)

                retenue = float(getattr(ens, "retenue", 0.0) or 0.0)
                brut = heures_realisees * taux_horaire
                net_a_payer = brut - retenue
                total_heures_global += heures_realisees
                total_net_global += net_a_payer

                lignes_html += f"""
                <tr>
                    <td style="text-align: center;">{i}</td>
                    <td><b>{nom_ens}</b></td>
                    <td>{matiere_ens}</td>
                    <td style="text-align: center;">{heures_realisees} h</td>
                    <td style="text-align: right;">{format_fcfa(taux_horaire)}</td>
                    <td style="text-align: right;">{format_fcfa(brut)}</td>
                    <td style="text-align: right;">{format_fcfa(retenue)}</td>
                    <td style="text-align: right; background-color: #f8fafc;"><b>{format_fcfa(net_a_payer)}</b></td>
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
                .page {{
                    width: 277mm; min-height: 180mm; margin: 0 auto; background: #FFFFFF; padding: 12mm;
                    border: 2px solid #000080; box-sizing: border-box; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }}
                table {{ width: 100%; border-collapse: collapse; font-size: 0.75rem; margin-top: 10px; }}
                th, td {{ border: 1px solid #000080; padding: 6px 8px; }}
                th {{ background-color: #800020; color: #FFFFFF; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="print-container no-print">
                <button class="print-btn" onclick="window.print()">🖨️ Imprimer l'État de Paie Vacataires (Paysage)</button>
            </div>
            <div class="page">
                <table style="border: none; margin-bottom: 10px;">
                    <tr>
                        <td style="border: none; font-size: 0.8rem; font-weight: bold;">
                            {nom_ecole}<br><span style="font-size: 0.7rem; font-weight: normal;">{adresse_ecole}</span>
                        </td>
                        <td style="border: none; text-align: right; font-size: 0.8rem;">
                            <b>ÉTAT DE PAIE MENSUEL — ENSEIGNANTS VACATAIRES (HEURES RÉALISÉES)</b><br>
                            Mois de référence : <b>{mois}</b><br>
                            Date de versement : <b>{date_paie.strftime('%d/%m/%Y')}</b>
                        </td>
                    </tr>
                </table>
                
                <table>
                    <thead>
                        <tr>
                            <th>N°</th>
                            <th>Nom & Prénom</th>
                            <th>Matière(s)</th>
                            <th>Heures Réalisées</th>
                            <th>Taux (FCFA)</th>
                            <th>Montant Brut (FCFA)</th>
                            <th>Retenues / Abs.</th>
                            <th>Net à Payer (FCFA)</th>
                            <th>Émargement (Signature)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {lignes_html}
                    </tbody>
                    <tfoot>
                        <tr style="background-color: #000080; color: #FFFFFF; font-weight: bold;">
                            <td colspan="3" style="text-align: right; padding: 8px;">TOTAUX :</td>
                            <td style="text-align: center; padding: 8px;">{total_heures_global} h</td>
                            <td colspan="3" style="text-align: right; padding: 8px;">TOTAL GÉNÉRAL NET :</td>
                            <td style="text-align: right; padding: 8px;">{format_fcfa(total_net_global)} FCFA</td>
                            <td></td>
                        </tr>
                    </tfoot>
                </table>

                <div style="display: flex; justify-content: space-between; margin-top: 30px; font-size: 0.8rem;">
                    <div style="text-align: center; width: 30%;">
                        <b>Le Responsable des Études</b><br><br><br>___________________________
                    </div>
                    <div style="text-align: center; width: 30%;">
                        <b>Le Comptable</b><br><br><br>___________________________
                    </div>
                    <div style="text-align: center; width: 30%;">
                        <b>Le Directeur / Proviseur</b><br><br><br>___________________________
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 25px; font-size: 0.65rem; border-top: 1px solid #000080; padding-top: 4px; font-weight: bold; color: #000080;">
                    {contacts_ecole} — Document de contrôle et de décaissement basé sur les heures effectives de cours.
                </div>
            </div>
        </body>
        </html>
        """
        components.html(html_content, height=620, scrolling=True)
    finally:
        db.close()


def afficher_paie():
    st.subheader("📋 Édition des États de Paie Mensuels")
    st.markdown(
        "Générez et imprimez les états récapitulatifs globaux directement connectés aux données de l'établissement pour l'émargement et l'archivage physique."
    )
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        type_etat = st.radio(
            "🎯 Sélectionnez la catégorie :",
            ["Personnel Administratif", "Enseignants Vacataires"],
            horizontal=True,
        )
    with col2:
        mois_selectionne = st.selectbox(
            "📅 Mois de référence :",
            [
                "Septembre 2026",
                "Octobre 2026",
                "Novembre 2026",
                "Décembre 2026",
                "Janvier 2027",
                "Février 2027",
                "Mars 2027",
                "Avril 2027",
                "Mai 2027",
                "Juin 2027",
                "Juillet 2027",
                "Août 2027",
            ],
        )
    with col3:
        date_versement = st.date_input(
            "📅 Date de versement / paie :", value=datetime.today()
        )

    st.markdown("---")

    if type_etat == "Personnel Administratif":
        afficher_etat_paie_administration(
            mois=mois_selectionne, date_paie=date_versement
        )
    else:
        afficher_etat_paie_vacataires(
            mois=mois_selectionne, date_paie=date_versement
        )


afficher_gestion_paie = afficher_paie