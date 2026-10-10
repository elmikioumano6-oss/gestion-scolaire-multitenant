from datetime import datetime, timedelta
import urllib.parse
import random
import string
import bcrypt
from database.audit import log_action_erp
from database.db_config import SessionLocal
from database.models import Enseignant, Eleve, School, User
import pandas as pd
import streamlit as st


def generer_lien_whatsapp_compte(telephone, username, password_clair, role):
    telephone_propre = str(telephone).replace(" ", "").replace("+", "")
    url_connexion = "https://www.gestionscolairepro.com"
    message = (
        f"Bonjour 👋\n\n"
        f"Voici vos accès pour l'ERP Scolaire (Rôle : {role}).\n\n"
        f"🔗 *Lien de connexion* : {url_connexion}\n"
        f"👤 *Utilisateur* : {username}\n"
        f"🔑 *Mot de passe provisoire* : {password_clair}\n\n"
        f"Cordialement,\n*L'Administration*"
    )
    texte_encode = urllib.parse.quote(message)
    return f"https://wa.me/{telephone_propre}?text={texte_encode}"


def generer_mdp_personnalise(nom, telephone):
    nom_nettoye = str(nom).strip()
    tel_nettoye = str(telephone).replace(" ", "").replace("+", "")
    
    if tel_nettoye.startswith("227") and len(tel_nettoye) > 3:
        tel_nettoye = tel_nettoye[3:]
        
    lettres = (nom_nettoye[0] + nom_nettoye[-1]) if len(nom_nettoye) >= 2 else (nom_nettoye + "X")
    chiffres = tel_nettoye[:3] if len(tel_nettoye) >= 3 else "123"
    
    return f"{lettres}{chiffres}"


def afficher_gestion_utilisateurs():
    st.subheader("👥 Gestion des Comptes Utilisateurs & Rôles")
    st.markdown(
        "Administration sécurisée des accès, des comptes et des rôles du "
        "personnel avec isolation multi-tenant stricte et suivi des statuts en "
        "temps réel."
    )
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    username_connecte = st.session_state.get("username", "")

    db = SessionLocal()
    try:
        if username_connecte:
            try:
                user_actif_session = db.query(User).filter(User.username == username_connecte).first()
                if user_actif_session and hasattr(user_actif_session, "derniere_activite"):
                    user_actif_session.derniere_activite = datetime.now()
                    db.commit()
            except Exception:
                db.rollback()

        if school_id:
            ecole_courante = db.query(School).filter(School.id == school_id).first()
            school_name = ecole_courante.nom if ecole_courante else st.session_state.get("school_name", "Établissement")
        else:
            school_name = st.session_state.get("school_name", "Établissement")
    finally:
        db.close()

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        user_obj_connecte = db.query(User).filter(User.username == username_connecte).first()
        user_role_connecte = getattr(user_obj_connecte, "role", "").lower() if user_obj_connecte else ""
        
        is_school_admin = user_role_connecte in [
            "admin",
            "directeur",
            "fondateur",
            "proviseur",
        ] or "admin" in username_connecte.lower()

        tab_liste, tab_ajout = st.tabs([
            "📋 Liste des Utilisateurs",
            "➕ Nouvel Utilisateur",
        ])

        with tab_liste:
            st.markdown(f"### Utilisateurs Actifs — **{school_name}**")

            users_query = db.query(User)
            if is_super_admin:
                pass
            elif school_id:
                users_query = users_query.filter(
                    User.school_id == school_id,
                    User.role != "super_admin"
                )

            utilisateurs_db = users_query.all()
            if not utilisateurs_db:
                st.info("Aucun utilisateur enregistré dans cet établissement.")
            else:
                data_u = []
                noms_vus = set()
                maintenant = datetime.now()

                for u in utilisateurs_db:
                    if u.username not in noms_vus:
                        noms_vus.add(u.username)

                        statut_connexion = "🔴 Hors ligne"
                        if hasattr(u, "derniere_activite") and u.derniere_activite:
                            diff = maintenant - u.derniere_activite
                            if diff < timedelta(minutes=5):
                                statut_connexion = "🟢 En ligne"

                        data_u.append({
                            "Nom d'utilisateur": u.username,
                            "Rôle / Fonction": getattr(u, "role", "N/D"),
                            "Statut Actuel": statut_connexion,
                            "Mot de passe à changer": (
                                "Oui" if getattr(u, "changer_mdp_requis", False) else "Non"
                            ),
                        })

                df_users = pd.DataFrame(data_u)
                st.dataframe(df_users, use_container_width=True)

                st.markdown("---")
                st.markdown("### 📲 Réinitialiser & Envoyer les accès par WhatsApp (Comptes existants)")
                col_ex1, col_ex2 = st.columns(2)
                with col_ex1:
                    user_select_wa = st.selectbox("Choisir l'utilisateur", [u.username for u in utilisateurs_db], key="sel_user_wa_existant")
                    tel_existant = st.text_input("Numéro WhatsApp (ex: +227...)", key="tel_user_wa_existant")
                with col_ex2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    nouveau_mdp_temp = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(8))
                    if st.button("🔄 Générer un nouveau MDP & Lien WhatsApp", type="primary"):
                        try:
                            u_cible = db.query(User).filter(User.username == user_select_wa).first()
                            if u_cible:
                                u_cible.password = bcrypt.hashpw(nouveau_mdp_temp.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                                u_cible.changer_mdp_requis = True
                                db.commit()
                                
                                if tel_existant:
                                    lien_wa_ex = generer_lien_whatsapp_compte(tel_existant, u_cible.username, nouveau_mdp_temp, u_cible.role)
                                    st.success(f"Mot de passe réinitialisé pour **{u_cible.username}** !")
                                    st.info(f"🔑 Nouveau MDP provisoire : `{nouveau_mdp_temp}`")
                                    st.link_button("📲 Cliquer pour envoyer sur WhatsApp", lien_wa_ex, type="primary")
                                else:
                                    st.warning("Veuillez saisir un numéro de téléphone WhatsApp valide.")
                        except Exception as ex:
                            db.rollback()
                            st.error(f"Erreur lors de la réinitialisation : {ex}")

                if is_school_admin or is_super_admin:
                    st.markdown("---")
                    st.markdown("### 🗑 Supprimer un utilisateur")
                    
                    usernames_disponibles = [u.username for u in utilisateurs_db if u.username != username_connecte]
                    
                    if usernames_disponibles:
                        user_a_supprimer = st.selectbox("Sélectionner l'utilisateur à supprimer", usernames_disponibles, key="select_suppr_user_multitenant")
                        if st.button("❌ Supprimer définitivement", type="primary"):
                            try:
                                user_obj_del = db.query(User).filter(User.username == user_a_supprimer).first()
                                if user_obj_del:
                                    db.query(Eleve).filter(Eleve.parent_id == user_obj_del.id).update({Eleve.parent_id: None})
                                    db.delete(user_obj_del)
                                    db.commit()
                                    st.success(f"L'utilisateur {user_a_supprimer} a été supprimé avec succès !")
                                    st.rerun()
                            except Exception as ex:
                                db.rollback()
                                st.error(f"Erreur lors de la suppression : {ex}")
                    else:
                        st.info("Aucun autre utilisateur disponible à la suppression.")

        with tab_ajout:
            st.markdown(f"### Création d'un Nouveau Compte Utilisateur — **{school_name}**")

            if st.session_state.get("dernier_compte_cree"):
                compte = st.session_state["dernier_compte_cree"]
                st.success(f"✅ Le compte de **{compte['username']}** ({compte['role']}) a été créé avec succès !")
                st.info(f"👤 **Identifiant** : `{compte['username']}`\n\n🔑 **Mot de passe** : `{compte['password']}`")
                
                if compte['telephone']:
                    lien_wa = generer_lien_whatsapp_compte(compte['telephone'], compte['username'], compte['password'], compte['role'])
                    st.link_button("📲 Envoyer immédiatement les accès par WhatsApp", lien_wa, type="primary")
                else:
                    st.warning("⚠️ Aucun numéro de téléphone n'a été renseigné pour ce compte.")
                
                if st.button("➕ Créer un autre compte"):
                    del st.session_state["dernier_compte_cree"]
                    st.rerun()
            else:
                if "temp_gen_pwd" not in st.session_state:
                    st.session_state["temp_gen_pwd"] = ""

                with st.form("form_creation_utilisateur_admin"):
                    col1, col2 = st.columns(2)
                    with col1:
                        nouveau_user = st.text_input("Nom d'utilisateur (Identifiant)")
                        nom_personne = st.text_input("Nom complet ou Nom de famille (pour règle MDP auto)")
                        telephone_compte = st.text_input("Téléphone (WhatsApp pour l'envoi des accès)")
                        
                        if st.form_submit_button("⚡ Appliquer la règle MDP automatique"):
                            if nom_personne and telephone_compte:
                                st.session_state["temp_gen_pwd"] = generer_mdp_personnalise(nom_personne, telephone_compte)
                            else:
                                st.warning("Veuillez d'abord remplir le nom et le téléphone.")

                        mot_de_passe = st.text_input(
                            "Mot de passe provisoire",
                            value=st.session_state.get("temp_gen_pwd", ""),
                            type="password",
                        )
                    with col2:
                        role_options = {
                            "fondateur": "Fondateur / Propriétaire",
                            "directeur": "Directeur / Administrateur",
                            "proviseur": "Proviseur / Direction Secondaire",
                            "censeur": "Censeur des Études",
                            "enseignant": "Enseignant / Professeur",
                            "econome": "Économe / Finances",
                            "surveillant": "Surveillant Général",
                            "inspecteur": "Inspecteur",
                            "parent": "Parent d'élève",
                        }
                        role_attribue = st.selectbox(
                            "Rôle / Fonction", options=list(role_options.keys())
                        )
                        cycle_associe = st.selectbox(
                            "Cycle d'affectation",
                            ["Collège / Lycée", "Maternelle", "Primaire", "Collège", "Lycée"],
                            index=0
                        )

                    role_descriptions = {
                        "fondateur": "Supervision stratégique globale, accès illimité à l'administration et aux finances de l'établissement.",
                        "directeur": "Accès complet à la gestion administrative, financière et aux paramètres de l'école.",
                        "proviseur": "Supervision globale du cycle secondaire, pilotage pédagogique et validation des décisions.",
                        "censeur": "Gestion des emplois du temps, des notes, des cahiers de textes et de la discipline.",
                        "enseignant": "Saisie des notes, émargement du cahier de texte et suivi de classe.",
                        "econome": "Gestion de la trésorerie, encaissements de scolarité et suivi des dépenses.",
                        "surveillant": "Gestion des absences, retours de discipline et cahier de correspondance.",
                        "inspecteur": "Supervision pédagogique, apposition de visas et audit des notes.",
                        "parent": "Accès restreint au portail famille pour le suivi exclusif de l'enfant.",
                    }
                    st.markdown(
                        f"<div style='background-color: rgba(217, 119, 6, 0.1); padding: 8px 12px; border-radius: 6px; border-left: 3px solid #D97706; font-size: 0.85rem; color: #E2E8F0; margin-bottom: 10px;'>ℹ <b>Permission :</b> {role_descriptions.get(role_attribue, 'Accès standard')}</div>",
                        unsafe_allow_html=True,
                    )

                    enseignant_lie_id = None
                    if role_attribue == "enseignant":
                        st.markdown("#### 🔗 Liaison avec un enseignant existant")
                        tous_ens = db.query(Enseignant).filter(Enseignant.school_id == (school_id or 1)).all()
                        ens_sans_compte = [e for e in tous_ens if not db.query(User).filter(User.enseignant_id == e.id).first()]
                        
                        dict_ens = {f"{e.nom} {e.prenom}": e.id for e in ens_sans_compte}
                        if dict_ens:
                            nom_choisi = st.selectbox("Sélectionner l'Enseignant à lier", options=list(dict_ens.keys()))
                            if nom_choisi:
                                enseignant_lie_id = dict_ens[nom_choisi]
                        else:
                            st.info("Tous les enseignants ont déjà un compte utilisateur associé.")

                    eleves_associes_ids = []
                    if role_attribue == "parent":
                        st.markdown("#### 🔗 Association des enfants")
                        eleves_query = db.query(Eleve).filter(
                            Eleve.school_id == (school_id or 1),
                            Eleve.deleted_at.is_(None)
                        )
                        if cycle_associe == "Collège / Lycée":
                            eleves_query = eleves_query.filter(Eleve.cycle.in_(["Collège", "Lycée"]))
                        elif cycle_associe != "Collège / Lycée":
                            eleves_query = eleves_query.filter(Eleve.cycle == cycle_associe)
                        
                        tous_les_eleves = eleves_query.all()
                        options_eleves_form = {f"{e.nom} {e.prenom} (Matricule: {e.matricule})": e.id for e in tous_les_eleves}
                        if options_eleves_form:
                            choix_eleves_form = st.multiselect("Sélectionner le ou les enfants concernés *", list(options_eleves_form.keys()))
                            eleves_associes_ids = [options_eleves_form[nom] for nom in choix_eleves_form]
                        else:
                            st.info("Aucun élève trouvé pour ce cycle.")

                    submitted_user = st.form_submit_button("💾 Enregistrer le compte", type="primary")

                    if submitted_user:
                        if not nouveau_user.strip() or not mot_de_passe.strip():
                            st.error("⚠️ Le nom d'utilisateur et le mot de passe sont obligatoires.")
                        else:
                            existing_user = db.query(User).filter(User.username == nouveau_user.strip()).first()
                            if existing_user:
                                st.error(f"⚠️ Un utilisateur avec le nom '{nouveau_user.strip()}' existe déjà.")
                            else:
                                try:
                                    hashed_pwd = bcrypt.hashpw(mot_de_passe.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                                    nouvel_u = User(
                                        username=nouveau_user.strip(),
                                        password=hashed_pwd,
                                        role=role_attribue,
                                        school_id=school_id or 1,
                                        enseignant_id=enseignant_lie_id,
                                        changer_mdp_requis=True
                                    )
                                    db.add(nouvel_u)
                                    db.flush()

                                    if role_attribue == "parent" and eleves_associes_ids:
                                        db.query(Eleve).filter(Eleve.id.in_(eleves_associes_ids)).update(
                                            {Eleve.parent_id: nouvel_u.id}, synchronize_session=False
                                        )

                                    db.commit()

                                    log_action_erp(
                                        module="Gestion Comptes",
                                        action=f"Création du compte {nouveau_user.strip()} ({role_attribue})",
                                        statut="Succès",
                                        valeur_avant="Inexistant",
                                        valeur_apres=f"Rôle: {role_attribue}",
                                    )

                                    st.session_state["dernier_compte_cree"] = {
                                        "username": nouveau_user.strip(),
                                        "password": mot_de_passe.strip(),
                                        "role": role_attribue,
                                        "telephone": telephone_compte.strip() if telephone_compte else None
                                    }
                                    if "temp_gen_pwd" in st.session_state:
                                        st.session_state["temp_gen_pwd"] = ""
                                    st.rerun()
                                except Exception as ex:
                                    db.rollback()
                                    st.error(f"Erreur lors de la création du compte : {ex}")

    except Exception as e:
        db.rollback()
        st.error(f"Une erreur est survenue lors du chargement de la gestion des utilisateurs : {e}")
    finally:
        db.close()