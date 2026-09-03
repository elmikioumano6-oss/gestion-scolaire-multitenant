import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse
import bcrypt
from database.db_config import SessionLocal
from database.models import School, User

def afficher_super_admin():
    st.subheader("🌐 Administration Globale de la Plateforme")
    st.markdown("Pilotage centralisé des établissements partenaires, gestion des abonnements, des essais et des statuts d'accès.")
    st.markdown("---")

    if not st.session_state.get("is_super_admin", False):
        st.warning("⚠️ Accès strictement réservé au Super Administrateur.")
        return

    # --- SECTION DE SÉCURITÉ GLOBALE (FIXÉE EN HAUT POUR NE PLUS DISPARAÎTRE) ---
    with st.expander("🔒 Sécurité et Mises à jour globales des comptes", expanded=True):
        st.markdown("Si vous avez des comptes administrateurs ou censeurs créés avant la mise en place de la sécurité, forcez ici l'exigence d'un changement de mot de passe à leur prochaine connexion.")
        if st.button("🔑 Forcer le changement de mot de passe pour TOUS les administrateurs existants", type="primary"):
            db_sec_all = SessionLocal()
            try:
                nb_maj = db_sec_all.query(User).filter(User.role != "super_admin").update(
                    {User.changer_mdp_requis: True}, synchronize_session=False
                )
                db_sec_all.commit()
                st.success(f"✅ Succès ! {nb_maj} compte(s) configuré(s) pour exiger un changement de mot de passe.")
            except Exception as ex:
                db_sec_all.rollback()
                st.error(f"Erreur lors de la mise à jour globale : {ex}")
            finally:
                db_sec_all.close()

    st.markdown("---")

    # --- AFFICHAGE DES DERNIERS ACCÈS CRÉÉS (POUR ENVOI RAPIDE WHATSAPP) ---
    if "last_created_credentials" in st.session_state:
        cred = st.session_state["last_created_credentials"]
        st.success(f"✅ Compte généré avec succès pour **{cred['school_name']}** !")
        
        lien_plateforme = "https://gestion-scolaire-multitenant-fcdbzcspet6krxvurgmfny.streamlit.app"
        
        msg = (
            f"Bonjour, votre espace de gestion pour l'établissement {cred['school_name']} "
            f"est actif sur la plateforme Gestion Scolaire Pro.\n\n"
            f"🔗 Lien d'accès : {lien_plateforme}\n"
            f"👤 Identifiant : {cred['username']}\n"
            f"🔑 Mot de passe provisoire : {cred['password']}\n\n"
            f"⚠️ Un changement de mot de passe vous sera demandé à la première connexion."
        )
        encoded_msg = urllib.parse.quote(msg)
        
        raw_contacts = str(cred.get('contacts', ''))
        liste_brute = [p.strip() for p in raw_contacts.replace(',', '/').replace('-', '/').split('/') if p.strip()]
        
        numeros_valides = []
        for num in liste_brute:
            clean_num = "".join(filter(str.isdigit, num))
            if len(clean_num) == 8:
                clean_num = "227" + clean_num
            if len(clean_num) >= 8:
                numeros_valides.append((num, clean_num))

        col_wa1, col_wa2 = st.columns([2, 1])
        with col_wa1:
            if numeros_valides:
                if len(numeros_valides) > 1:
                    choix_label = st.selectbox(
                        "📱 Cet établissement a plusieurs numéros. Lequel voulez-vous utiliser pour WhatsApp ?",
                        options=[n[0] for n in numeros_valides],
                        key="select_whatsapp_number"
                    )
                    selected_clean = next(n[1] for n in numeros_valides if n[0] == choix_label)
                else:
                    choix_label, selected_clean = numeros_valides[0]
                
                wa_url = f"https://wa.me/{selected_clean}?text={encoded_msg}"
                st.markdown(
                    f"""
                    <a href="{wa_url}" target="_blank" style="display:inline-block;background-color:#25D366;color:white;padding:10px 20px;border-radius:5px;text-decoration:none;font-weight:bold;margin-bottom:10px;">
                        📲 Envoyer les accès par WhatsApp au {choix_label}
                    </a>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.warning("⚠️ Aucun numéro de téléphone valide n'a été renseigné pour ce contact.")
                
        with col_wa2:
            if st.button("Fermer cet encadré"):
                del st.session_state["last_created_credentials"]
                st.rerun()

        st.text_area("Copier le message d'accès (si besoin) :", value=msg, height=140)
        st.markdown("---")

    db = SessionLocal()
    try:
        tab1, tab2 = st.tabs(["🏫 Gestion des Établissements & Abonnements", "➕ Enregistrer un Nouvel Établissement"])

        with tab1:
            st.markdown("### Liste des Établissements Partenaires")
            
            ecoles = db.query(School).all()
            if not ecoles:
                st.info("Aucun établissement enregistré pour le moment sur la plateforme.")
            else:
                for ecole in ecoles:
                    statut_texte = "✅ Actif" if getattr(ecole, 'actif', True) else "⛔ Suspendu"
                    
                    with st.expander(f"🏫 {ecole.nom} (ID: {ecole.id}) [Code: {ecole.code}] — Statut : {statut_texte}"):
                        with st.form(key=f"form_update_{ecole.id}"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.write(f"**Code :** {getattr(ecole, 'code', 'N/D')}")
                                st.write(f"**Devise :** {getattr(ecole, 'devise', 'N/D')}")
                                st.write(f"**Adresse :** {getattr(ecole, 'adresse', 'N/D')}")
                                st.write(f"**Contacts :** {getattr(ecole, 'contacts', 'N/D')}")
                                
                            with col2:
                                date_exp_actuelle = getattr(ecole, 'date_expiration', None)
                                if not date_exp_actuelle:
                                    date_exp_actuelle = datetime.utcnow() + timedelta(days=30)
                                
                                nouveau_statut_actif = st.checkbox("Établissement Actif", value=getattr(ecole, 'actif', True), key=f"actif_{ecole.id}")
                                
                                if isinstance(date_exp_actuelle, datetime):
                                    d_val = date_exp_actuelle.date()
                                else:
                                    d_val = datetime.utcnow().date() + timedelta(days=30)
                                    
                                nouvelle_date_exp = st.date_input("Date limite d'accès / Fin d'essai", value=d_val, key=f"exp_{ecole.id}")
                                
                                submitted_update = st.form_submit_button("💾 Mettre à jour l'établissement")
                                if submitted_update:
                                    ecole_maj = db.query(School).filter(School.id == ecole.id).first()
                                    if ecole_maj:
                                        ecole_maj.actif = nouveau_statut_actif
                                        ecole_maj.date_expiration = datetime.combine(nouvelle_date_exp, datetime.min.time())
                                        
                                        utilisateurs_ecole = db.query(User).filter(User.school_id == ecole.id).all()
                                        for u in utilisateurs_ecole:
                                            if hasattr(u, 'actif'):
                                                u.actif = nouveau_statut_actif
                                                
                                        db.commit()
                                        st.success(f"✅ Paramètres mis à jour pour {ecole_maj.nom} !")
                                        st.rerun()

                        st.markdown("---")
                        st.markdown("#### 👤 Gestion des Comptes Administrateurs / Censeurs")
                        
                        utilisateurs_ecole = db.query(User).filter(User.school_id == ecole.id).all()
                        if utilisateurs_ecole:
                            for u in utilisateurs_ecole:
                                st.markdown(f"- **Utilisateur :** `{u.username}` | **Rôle :** `{u.role}` | **Mot de passe à changer :** `{'Oui' if u.changer_mdp_requis else 'Non'}`")
                        else:
                            st.warning("⚠️ Aucun compte utilisateur n'est encore associé à cet établissement.")

                        with st.form(key=f"form_admin_existant_{ecole.id}"):
                            st.write("Créer ou réinitialiser un accès administrateur pour cette école :")
                            adm_username = st.text_input("Identifiant de connexion", key=f"adm_user_{ecole.id}")
                            adm_password = st.text_input("Mot de passe provisoire", type="password", key=f"adm_pass_{ecole.id}")
                            btn_save_adm = st.form_submit_button("Créer / Réinitialiser le compte Admin")
                            
                            if btn_save_adm:
                                if not adm_username.strip() or not adm_password.strip():
                                    st.error("Veuillez renseigner l'identifiant et le mot de passe.")
                                elif len(adm_password) < 6:
                                    st.error("Le mot de passe provisoire doit contenir au moins 6 caractères.")
                                else:
                                    existing_usr = db.query(User).filter(User.username == adm_username.strip()).first()
                                    if existing_usr:
                                        if existing_usr.school_id == ecole.id:
                                            existing_usr.password = bcrypt.hashpw(adm_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                                            existing_usr.role = "admin"
                                            existing_usr.changer_mdp_requis = True
                                            db.commit()
                                            
                                            st.session_state["last_created_credentials"] = {
                                                "school_name": ecole.nom,
                                                "username": adm_username.strip(),
                                                "password": adm_password.strip(),
                                                "contacts": ecole.contacts or ""
                                            }
                                            st.success(f"✅ Compte {adm_username.strip()} mis à jour avec succès !")
                                            st.rerun()
                                        else:
                                            st.error("⛔ Cet identifiant est déjà utilisé par un autre utilisateur dans une autre école.")
                                    else:
                                        hashed_p = bcrypt.hashpw(adm_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                                        nouveau_compte = User(
                                            school_id=ecole.id,
                                            username=adm_username.strip(),
                                            password=hashed_p,
                                            role="admin",
                                            changer_mdp_requis=True
                                        )
                                        db.add(nouveau_compte)
                                        db.commit()
                                        
                                        st.session_state["last_created_credentials"] = {
                                            "school_name": ecole.nom,
                                            "username": adm_username.strip(),
                                            "password": adm_password.strip(),
                                            "contacts": ecole.contacts or ""
                                        }
                                        st.success(f"✅ Compte administrateur `{adm_username.strip()}` créé avec succès pour {ecole.nom} !")
                                        st.rerun()

        with tab2:
            st.markdown("### Enregistrer un Nouvel Établissement et son Administrateur")
            with st.form("form_create_school"):
                st.markdown("#### 1. Informations de l'établissement")
                code_ecole = st.text_input("Code unique de l'établissement (ex: RAHMAT, CHALLENGE)")
                nom_ecole = st.text_input("Nom de l'établissement")
                devise_ecole = st.text_input("Devise", value="Discipline - Qualité - Réussite")
                adresse_ecole = st.text_input("Adresse / Quartier, Ville", value="Niamey, Niger")
                contacts_ecole = st.text_input("Numéros de téléphone (séparés par /)")
                periode_essai_mois = st.number_input("Période d'essai (en mois)", min_value=1, max_value=12, value=1)

                st.markdown("#### 2. Compte Administrateur / Censeur initial")
                admin_username = st.text_input("Identifiant de connexion (ex: admin_rahmat)")
                admin_password = st.text_input("Mot de passe provisoire", type="password")

                submitted_school = st.form_submit_button("Créer l'établissement et générer le compte")
                if submitted_school:
                    if not nom_ecole.strip() or not code_ecole.strip():
                        st.error("⚠️ Le nom et le code unique de l'établissement sont obligatoires.")
                    elif not admin_username.strip() or not admin_password.strip():
                        st.error("⚠️ L'identifiant et le mot de passe administrateur sont obligatoires.")
                    elif len(admin_password) < 6:
                        st.error("⚠️ Le mot de passe provisoire doit contenir au moins 6 caractères.")
                    else:
                        code_nettoye = code_ecole.strip().upper()
                        code_existant = db.query(School).filter(School.code == code_nettoye).first()
                        if code_existant:
                            st.error(f"⚠️ Un établissement avec le code '{code_nettoye}' existe déjà.")
                        else:
                            user_existant = db.query(User).filter(User.username == admin_username.strip()).first()
                            if user_existant:
                                st.error(f"⚠️ L'identifiant '{admin_username.strip()}' est déjà utilisé.")
                            else:
                                date_expiration_val = datetime.utcnow() + timedelta(days=30 * periode_essai_mois)
                                nouvelle_ecole = School(
                                    code=code_nettoye,
                                    nom=nom_ecole.strip(),
                                    devise=devise_ecole.strip(),
                                    adresse=adresse_ecole.strip(),
                                    contacts=contacts_ecole.strip(),
                                    actif=True,
                                    date_expiration=date_expiration_val
                                )
                                db.add(nouvelle_ecole)
                                db.commit()
                                db.refresh(nouvelle_ecole)

                                hashed_pwd = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                                nouvel_admin = User(
                                    school_id=nouvelle_ecole.id,
                                    username=admin_username.strip(),
                                    password=hashed_pwd,
                                    role="admin",
                                    changer_mdp_requis=True
                                )
                                db.add(nouvel_admin)
                                db.commit()

                                st.session_state["last_created_credentials"] = {
                                    "school_name": nom_ecole.strip(),
                                    "username": admin_username.strip(),
                                    "password": admin_password.strip(),
                                    "contacts": contacts_ecole.strip()
                                }

                                st.success(f"✅ L'établissement **{nom_ecole}** et son compte administrateur ont été créés avec succès !")
                                st.rerun()

    finally:
        db.close()

afficher_super_admin_global = afficher_super_admin