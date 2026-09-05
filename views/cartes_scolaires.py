import streamlit as st
import streamlit.components.v1 as components
import base64
import os
import urllib.parse
from datetime import datetime
from sqlalchemy import text
from database.db_config import SessionLocal
from database.models import Classe, Eleve, School, JournalActivite, AnneeScolaire

def obtenir_logo_et_palette(school_name):
    """
    Détecte l'école active et associe son logo depuis la racine ainsi que sa palette officielle.
    """
    school_name_lower = (school_name or "").lower()
    
    if "etoile" in school_name_lower:
        logo_file = "Logo L'ETOILE DU SUCCES.png"
        couleur_principale = "#0a192f"
        couleur_secondaire = "#b8860b"
    elif "rahmat" in school_name_lower or "csp" in school_name_lower:
        logo_file = "Logo CSP-RAHMAT-FH.png" if os.path.exists("Logo CSP-RAHMAT-FH.png") else "Logo Gestion Scolaire Pro.png"
        couleur_principale = "#1b365d"  # Bleu marine (Haut)
        couleur_secondaire = "#8b0000"  # Rouge bordeaux (Bande bas)
    else:
        logo_file = "Logo Gestion Scolaire Pro.png" if os.path.exists("Logo Gestion Scolaire Pro.png") else "Logo CSP-RAHMAT-FH.png"
        couleur_principale = "#1b365d"
        couleur_secondaire = "#8b0000"

    logo_data_uri = ""
    if os.path.exists(logo_file):
        try:
            with open(logo_file, "rb") as image_file:
                encoded = base64.b64encode(image_file.read()).decode()
                logo_data_uri = f"data:image/png;base64,{encoded}"
        except Exception:
            pass

    return logo_data_uri, couleur_principale, couleur_secondaire

def obtenir_photo_eleve_base64(eleve_obj):
    """
    Récupère la photo de l'élève depuis la base de données et la convertit en URI Base64.
    """
    photo_path = getattr(eleve_obj, 'photo', None) or getattr(eleve_obj, 'image', None) or getattr(eleve_obj, 'avatar', None)
    
    if photo_path and isinstance(photo_path, str):
        if photo_path.startswith("data:image") or photo_path.startswith("http"):
            return photo_path
        if os.path.exists(photo_path):
            try:
                with open(photo_path, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode()
                    return f"data:image/png;base64,{encoded}"
            except Exception:
                pass
    return ""

def afficher_cartes_scolaires():
    st.subheader("🪪 Génération des Cartes Scolaires")
    st.markdown("Édition et impression directe des cartes d'identité des élèves aux normes officielles.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    username = st.session_state.get("username", "")

    if not school_id:
        st.warning("⚠️ Veuillez vous connecter en tant qu'établissement pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        # SÉCURITÉ AUTOMATIQUE : Ajoute la colonne photo si elle n'existe pas encore dans la base SQL
        try:
            db.execute(text("ALTER TABLE eleves ADD COLUMN IF NOT EXISTS photo TEXT;"))
            db.commit()
        except Exception:
            db.rollback()

        ecole_obj = db.query(School).filter(School.id == school_id).first()
        school_name = getattr(ecole_obj, 'nom', None) or st.session_state.get("school_name", "CSP Rahmat-FH")
        
        adresse_ecole = getattr(ecole_obj, 'adresse', None) or getattr(ecole_obj, 'quartier', None) or "Quartier Aéroport"
        tel_ecole_brut = getattr(ecole_obj, 'telephone', None) or getattr(ecole_obj, 'tel', None) or getattr(ecole_obj, 'contacts', None) or "90 90 85 23 / 97 32 77 52"
        
        bas_page_adresse = f"Adresse de l'Établissement : {adresse_ecole} | Tél : {tel_ecole_brut}"

        # Récupération dynamique du logo et des couleurs de l'école active
        logo_data_uri, coul_principale, coul_secondaire = obtenir_logo_et_palette(school_name)

        annee_active_obj = db.query(AnneeScolaire).filter(AnneeScolaire.school_id == school_id, AnneeScolaire.active == True).first()
        if not annee_active_obj:
            annee_active_obj = db.query(AnneeScolaire).filter(AnneeScolaire.active == True).first()
        
        libelle_annee = getattr(annee_active_obj, 'libelle', None) or getattr(annee_active_obj, 'annee', '2026-2027')
        cycle_en_cours = st.session_state.get("cycle_actif", "Collège")

        classes_query = db.query(Classe).filter(
            Classe.school_id == school_id,
            Classe.cycle == cycle_en_cours,
            Classe.deleted_at.is_(None)
        )
        classes_cycle = classes_query.all()

        if not classes_cycle:
            st.info(f"📌 **{school_name}** — Aucune classe disponible pour le cycle **{cycle_en_cours}**.")
            return

        classes_dict = {c.id: c.libelle for c in classes_cycle}
        classes_ids = list(classes_dict.keys())

        eleves_query = db.query(Eleve).filter(
            Eleve.school_id == school_id,
            Eleve.classe_id.in_(classes_ids),
            Eleve.deleted_at.is_(None)
        )
        eleves = eleves_query.order_by(Eleve.nom).all()

        st.markdown(f"### Cartes Scolaires — **{school_name} ({cycle_en_cours})**")

        if not eleves:
            st.info("Aucun élève enregistré pour générer les cartes scolaires dans ce cycle.")
        else:
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                noms_eleves = [f"{e.nom} {e.prenom} (Mat: {getattr(e, 'matricule', 'N/D')} — {classes_dict.get(e.classe_id, 'N/D')})" for e in eleves]
                choix_eleve = st.selectbox("Sélectionner un élève", noms_eleves)
            
            with col_f2:
                st.markdown("<br>", unsafe_allow_html=True)
                tracer_audit = st.checkbox("Enregistrer l'impression dans le journal d'audit", value=False)

            eleve_obj = next((e for e in eleves if f"{e.nom} {e.prenom} (Mat: {getattr(e, 'matricule', 'N/D')} — {classes_dict.get(e.classe_id, 'N/D')})" == choix_eleve), None)

            if eleve_obj:
                st.markdown("---")
                st.markdown("#### 🎫 Aperçu et Impression Directe")
                
                prenom_eleve = getattr(eleve_obj, 'prenom', '')
                nom_eleve = getattr(eleve_obj, 'nom', '')
                date_naissance = getattr(eleve_obj, 'date_naissance', '01/01/2008')
                lieu_naissance = getattr(eleve_obj, 'lieu_naissance', 'Niamey')
                classe_libelle = classes_dict.get(eleve_obj.classe_id, 'N/D')
                matricule_val = getattr(eleve_obj, 'matricule', 'N/D')
                contact_eleve = getattr(eleve_obj, 'contact', 'N/D')
                
                tuteur_nom = getattr(eleve_obj, 'tuteur_nom', None) or getattr(eleve_obj, 'nom_parent', None) or 'NIAMEY AEROPORT AHNAT'
                tuteur_tel = getattr(eleve_obj, 'tuteur_tel', None) or getattr(eleve_obj, 'tel_parent', None) or '+227 80 25 51 08'
                
                id_carte = f"0000{eleve_obj.id}" if eleve_obj.id < 10000 else str(eleve_obj.id)
                
                banniere_contenu = f'<span>{school_name.upper()}</span>'

                # Gestion de la photo de l'élève
                photo_eleve_uri = obtenir_photo_eleve_base64(eleve_obj)
                if photo_eleve_uri:
                    photo_html = f'<img src="{photo_eleve_uri}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 3px;" alt="Photo Élève" />'
                else:
                    photo_html = 'PHOTO ÉLÈVE'

                # Génération du QR Code WhatsApp pointant vers le premier numéro de l'école
                premier_num = "".join(filter(str.isdigit, tel_ecole_brut.split('/')[0]))
                if not premier_num.startswith("227"):
                    premier_num = "227" + premier_num

                texte_msg = f"Bonjour, est-ce que la carte numéro {id_carte} appartenant à l'élève {prenom_eleve} {nom_eleve} (Classe: {classe_libelle}) est authentique ?"
                whatsapp_url = f"https://wa.me/{premier_num}?text={urllib.parse.quote(texte_msg)}"
                qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=120x120&data={urllib.parse.quote(whatsapp_url)}"

                # Logo de l'établissement sous l'ID N°
                if logo_data_uri:
                    logo_sous_id_html = f'<img src="{logo_data_uri}" style="height: 26px; max-width: 70px; object-fit: contain; display: block; margin-top: 2px;" alt="Logo" />'
                else:
                    logo_sous_id_html = f'<span style="font-size: 8px; font-weight: bold; color: {coul_principale};">{school_name.upper()}</span>'

                badge_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                <meta charset="utf-8">
                <style>
                body {{
                    background-color: #f8f9fa;
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 5px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                }}
                .official-id-card {{
                    width: 100%;
                    max-width: 680px;
                    background: #ffffff;
                    border: 3px solid {coul_principale};
                    border-radius: 8px;
                    padding: 10px 15px 0px 15px;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.15);
                    color: #000000;
                    box-sizing: border-box;
                    position: relative;
                    overflow: hidden;
                }}
                .card-top-header {{
                    text-align: center;
                    border-bottom: 2px solid {coul_principale};
                    padding-bottom: 2px;
                    margin-bottom: 4px;
                }}
                .card-top-header .rep {{
                    font-size: 10.5px;
                    font-weight: bold;
                    letter-spacing: 0.5px;
                    margin: 0;
                    color: {coul_principale};
                }}
                .card-top-header .min {{
                    font-size: 9.5px;
                    margin: 1px 0;
                    color: #333;
                }}
                .card-top-header .dren {{
                    font-size: 9.5px;
                    font-weight: bold;
                    margin: 0;
                    color: {coul_principale};
                }}
                .school-title-banner {{
                    background-color: {coul_principale};
                    color: #ffffff;
                    text-align: center;
                    padding: 5px;
                    font-weight: bold;
                    font-size: 13.5px;
                    letter-spacing: 1px;
                    margin: 4px 0;
                    border-radius: 3px;
                }}
                .card-sub-info {{
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    font-size: 9.5px;
                    font-weight: bold;
                    background: #f4f6f9;
                    padding: 3px 6px;
                    border-left: 4px solid {coul_secondaire};
                    margin-bottom: 5px;
                }}
                .card-content-grid {{
                    display: flex;
                    gap: 12px;
                    align-items: flex-start;
                    width: 100%;
                }}
                .photo-column {{
                    flex: 1;
                    text-align: center;
                }}
                .student-photo {{
                    width: 95px;
                    height: 118px;
                    border: 2px solid {coul_principale};
                    border-radius: 4px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 9.5px;
                    color: #555;
                    background: #eaeaea;
                    margin: 0 auto 3px auto;
                    overflow: hidden;
                }}
                .qr-container {{
                    width: 55px;
                    height: 55px;
                    margin: 0 auto;
                }}
                .qr-container img {{
                    width: 55px;
                    height: 55px;
                    object-fit: contain;
                }}
                .details-column {{
                    flex: 2.4;
                    font-size: 11px;
                    line-height: 1.3;
                }}
                .details-column table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                .details-column td {{
                    padding: 1px 0;
                    vertical-align: top;
                }}
                .label-field {{
                    font-weight: bold;
                    color: {coul_principale};
                    width: 95px;
                }}
                .tuteur-section {{
                    margin-top: 3px;
                    border-top: 1px dashed {coul_secondaire};
                    padding-top: 2px;
                }}
                .tuteur-title {{
                    font-weight: bold;
                    font-size: 9.5px;
                    color: {coul_secondaire};
                    margin-bottom: 1px;
                }}
                .card-bottom-footer {{
                    margin-top: 8px;
                    margin-left: -15px;
                    margin-right: -15px;
                    background-color: {coul_secondaire};
                    color: #ffffff;
                    padding: 5px 12px;
                    font-size: 8.5px;
                    text-align: center;
                    font-weight: bold;
                    letter-spacing: 0.3px;
                }}
                .print-btn-container {{
                    margin-top: 10px;
                    text-align: center;
                }}
                .btn-print {{
                    background-color: {coul_principale};
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: bold;
                    border-radius: 5px;
                    cursor: pointer;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                }}
                .btn-print:hover {{
                    opacity: 0.9;
                }}
                @media print {{
                    body {{
                        background: white;
                        padding: 0;
                    }}
                    .print-btn-container {{
                        display: none;
                    }}
                    .official-id-card {{
                        box-shadow: none;
                        border: 2px solid #000;
                    }}
                }}
                </style>
                </head>
                <body>
                <div class="official-id-card">
                    <div class="card-top-header">
                        <div class="rep">REPUBLIQUE DU NIGER</div>
                        <div class="min">Ministère de l'Éducation Nationale</div>
                        <div class="dren">D.R.E.N / NIAMEY</div>
                    </div>

                    <div class="school-title-banner">
                        {banniere_contenu}
                    </div>

                    <div class="card-sub-info">
                        <span>ANNÉE SCOLAIRE : {libelle_annee}</span>
                        <span>CARTE SCOLAIRE</span>
                        <div style="text-align: right; display: flex; flex-direction: column; align-items: flex-end;">
                            <div><b>ID N° : {id_carte}</b></div>
                            <div style="margin-top: 1px;">{logo_sous_id_html}</div>
                        </div>
                    </div>

                    <div class="card-content-grid">
                        <div class="photo-column">
                            <div class="student-photo">
                                {photo_html}
                            </div>
                            <div class="qr-container">
                                <img src="{qr_code_url}" alt="QR WhatsApp" />
                            </div>
                        </div>
                        <div class="details-column">
                            <table>
                                <tr>
                                    <td class="label-field">Prénom :</td>
                                    <td><b>{prenom_eleve}</b></td>
                                </tr>
                                <tr>
                                    <td class="label-field">Nom :</td>
                                    <td><b>{nom_eleve}</b></td>
                                </tr>
                                <tr>
                                    <td class="label-field">Né(e) le :</td>
                                    <td>{date_naissance} à {lieu_naissance}</td>
                                </tr>
                                <tr>
                                    <td class="label-field">Classe :</td>
                                    <td><b>{classe_libelle}</b></td>
                                </tr>
                                <tr>
                                    <td class="label-field">Matricule :</td>
                                    <td><b>{matricule_val}</b></td>
                                </tr>
                                <tr>
                                    <td class="label-field">Contact :</td>
                                    <td>{contact_eleve}</td>
                                </tr>
                            </table>

                            <div class="tuteur-section">
                                <div class="tuteur-title">Adresse Parent ou Tuteur</div>
                                <table>
                                    <tr>
                                        <td class="label-field" style="width: 50px;">Nom :</td>
                                        <td>{tuteur_nom}</td>
                                    </tr>
                                    <tr>
                                        <td class="label-field" style="width: 50px;">Tél :</td>
                                        <td><b>{tuteur_tel}</b></td>
                                    </tr>
                                </table>
                            </div>
                        </div>
                    </div>

                    <div class="card-bottom-footer">
                        {bas_page_adresse}
                    </div>
                </div>

                <div class="print-btn-container">
                    <button class="btn-print" onclick="window.print()">🖨️ Lancer l'impression directe de la carte</button>
                </div>
                </body>
                </html>
                """

                components.html(badge_html, height=410, scrolling=False)

                if tracer_audit:
                    nouveau_log = JournalActivite(
                        school_id=school_id,
                        timestamp=datetime.utcnow(),
                        username=username or "admin",
                        action=f"Édition carte scolaire - {nom_eleve} {prenom_eleve} (Mat: {matricule_val})",
                        module="Cartes Scolaires",
                        statut="Succès",
                        valeur_apres=f"Carte émise par {school_name} - Classe {classe_libelle}"
                    )
                    db.add(nouveau_log)
                    db.commit()

    finally:
        db.close()

afficher_cartes_scolaires = afficher_cartes_scolaires