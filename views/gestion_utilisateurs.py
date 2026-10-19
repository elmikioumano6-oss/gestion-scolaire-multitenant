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
    telephone_propre = str(telephone).replace(" ", "").replace("+", "").replace("-", "")
    url_connexion = "https://www.gestionscolairepro.com"
    
    if role.lower() == "parent":
        message = (
            "🌟 *Chère Famille, Chers Parents*, 👋\n\n"
            "Nous avons le plaisir de vous rappeler que votre *Espace Famille* est entièrement actif et sécurisé au sein de notre établissement.\n\n"
            "Restez connectés au parcours scolaire de votre enfant en temps réel : suivez ses notes, son assiduité, son cahier de textes ainsi que l'évolution de ses versements et de sa scolarité.\n\n"
            "🚀 *Connectez-vous dès maintenant pour découvrir votre espace dédié :*\n"
            f"🌐 *Portail* : {url_connexion}\n\n"
            "🔑 *Vos identifiants d'accès sécurisés :*\n"
            f"👤 *Nom d'utilisateur* : `{username}`\n"
            f"🔒 *Mot de passe provisoire* : `{password_clair}`\n\n"
            "_Par mesure de sécurité, veuillez modifier votre mot de passe dès votre première connexion._\n\n"
            "En cas de besoin, l'administration reste à votre entière disposition.\n\n"
            "Cordialement,\n*La Direction du CSP RAHMAT-FH*"
        )
    else:
        message = (
            "Bonjour 👋\n\n"
            f"Voici vos accès professionnels pour l'ERP Scolaire (Rôle : {role}).\n\n"
            f"🔗 *Lien de connexion* : {url_connexion}\n"
            f"👤 *Utilisateur* : {username}\n"
            f"🔑 *Mot de passe provisoire* : `{password_clair}`\n\n"
            "Veuillez modifier ce mot de passe lors de votre première connexion.\n\n"
            "Cordialement,\n*La Direction du CSP RAHMAT-FH*"
        )
        
    texte_encode = urllib.parse.quote(message)
    return f"https://api.whatsapp.com/send?phone={telephone_propre}&text={texte_encode}"


def generer_mdp_personnalise(nom, telephone):
    nom_nettoye = str(nom).strip()
    tel_nettoye = str(telephone).replace(" ", "").replace("+", "")
    
    if tel_nettoye.startswith("227") and len(tel_nettoye) > 3:
        tel_nettoye = tel_nettoye[3:]
        
    lettres = nom_nettoye[:2].lower() if len(nom_nettoye) >= 2 else (nom_nettoye.lower() + "x")
    chiffres = tel_nettoye[:3] if len(tel_nettoye) >= 3 else "123"
    
    return f"{lettres}{chiffres}"


def afficher_gestion_utilisateurs():
    st.subheader("Gestion des Comptes Utilisateurs & Roles")
    st.markdown(
        "Administration securisee des acces, des comptes et des roles du "
        "personnel avec isolation multi-tenant stricte et suivi des statuts en "
        "temps reel."
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
            school_name = ecole_courante.nom if ecole_courante else st.session_state.get("school_name", "Etablissement")
        else:
            school_name = st.session_state.get("school_name", "Etablissement")
    finally:
        db.close()

    if not school_id and not is_super_admin:
        st.warning("Veuillez vous connecter pour acceder a cette section.")
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
            "Liste des Utilisateurs",
            "Nouvel Utilisateur",
        ])

        with tab_liste:
            st.markdown(f"### Utilisateurs Actifs — **{school_name}**")

            if is_school_admin or is_super_admin:
                with st.expander("Outil de maintenance : Uniformiser & Raccourcir les identifiants parents"):
                    st.caption("Cliquez sur ce bouton pour convertir automatiquement tous les identifiants parents au format court (ex: famille.nom_prenom) base sur le premier mot du nom et du prenom.")
                    if st.button("Raccourcir et nettoyer tous les identifiants parents", type="secondary"):
                        try:
                            comptes_parents = db.query(User).filter(User.role == "parent").all()
                            nb_modifies = 0
                            for cp in comptes_parents:
                                eleve_lie = None
                                if cp.eleve_id:
                                    eleve_lie = db.query(Eleve).filter(Eleve.id == cp.eleve_id).first()
                                if not eleve_lie:
                                    eleve_lie = db.query(Eleve).filter(Eleve.parent_id == cp.id).first()

                                if eleve_lie:
                                    nom_brut = "".join([c for c in eleve_lie.nom.lower() if c.isalnum() or c == ' ']).strip()
                                    prenom_brut = "".join([c for c in eleve_lie.prenom.lower() if c.isalnum() or c == ' ']).strip()
                                    
                                    nom_court = nom_brut.split()[0] if nom_brut else "famille"
                                    prenom_court = prenom_brut.split()[0] if prenom_brut else "eleve"
                                    
                                    nouveau_pseudo = f"famille.{nom_court}_{prenom_court}"

                                    existe = db.query(User).filter(User.username == nouveau_pseudo, User.id != cp.id).first()
                                    if existe:
                                        suffixe = "".join(random.choices(string.digits, k=3))
                                        nouveau_pseudo = f"famille.{nom_court}_{prenom_court}_{suffixe}"

                                    cp.username = nouveau_pseudo
                                    nb_modifies += 1
                            db.commit()
                            st.success(f"{nb_modifies} compte(s) parent(s) raccourcis et mis a jour avec succes !")
                            st.rerun()
                        except Exception as err:
                            db.rollback()
                            st.error(f"Erreur lors de la mise a jour : {err}")

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
                st.info("Aucun utilisateur enregistre dans cet etablissement.")
            else:
                data_u = []
                noms_vus = set()
                maintenant = datetime.now()

                for u in utilisateurs_db:
                    if u.username not in noms_vus:
                        noms_vus.add(u.username)

                        statut_connexion = "Hors ligne"
                        if hasattr(u, "derniere_activite") and u.derniere_activite:
                            diff = maintenant - u.derniere_activite
                            if diff < timedelta(minutes=5):
                                statut_connexion = "En ligne"

                        data_u.append({
                            "Nom d'utilisateur": u.username,
                            "Role / Fonction": getattr(u, "role", "N/D"),
                            "Statut Actuel": statut_connexion,
                            "Mot de passe a changer": (
                                "Oui" if getattr(u, "changer_mdp_requis", False) else "Non"
                            ),
                        })

                df_users = pd.DataFrame(data_u)
                st.dataframe(df_users, use_container_width=True)

                st.markdown("---")
                st.markdown("### Reinitialiser & Envoyer les acces par WhatsApp (Compte par compte)")
                st.caption("Selectionnez un utilisateur existant. Le numero WhatsApp se remplit automatiquement s'il s'agit d'un compte parent lie a un eleve.")
                
                col_ex1, col_ex2 = st.columns(2)
                with col_ex1:
                    user_select_wa = st.selectbox("Choisir l'utilisateur", [u.username for u in utilisateurs_db], key="sel_user_wa_existant")
                    
                    el_telephone_auto = ""
                    nom_eleve_associe = ""
                    u_selectionne_obj = db.query(User).filter(User.username == user_select_wa).first()
                    if u_selectionne_obj:
                        eleve_associe = None
                        if u_selectionne_obj.eleve_id:
                            eleve_associe = db.query(Eleve).filter(Eleve.id == u_selectionne_obj.eleve_id).first()
                        if not eleve_associe:
                            eleve_associe = db.query(Eleve).filter(Eleve.parent_id == u_selectionne_obj.id).first()

                        if eleve_associe:
                            if eleve_associe.tuteur:
                                el_telephone_auto = eleve_associe.tuteur
                            if eleve_associe.nom:
                                nom_eleve_associe = eleve_associe.nom

                    tel_existant = st.text_input("Numero WhatsApp (ex: +227...)", value=el_telephone_auto, key="tel_user_wa_existant")
                with col_ex2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    if nom_eleve_associe and tel_existant:
                        nouveau_mdp_temp = generer_mdp_personnalise(nom_eleve_associe, tel_existant)
                    else:
                        nouveau_mdp_temp = "".join(
                            random.choice(string.ascii_letters + string.digits)
                            for _ in range(8)
                        )

                    if st.button("Generer un nouveau MDP & Lien WhatsApp", type="primary"):
                        try:
                            u_cible = db.query(User).filter(User.username == user_select_wa).first()
                            if u_cible:
                                u_cible.password = bcrypt.hashpw(nouveau_mdp_temp.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                                u_cible.changer_mdp_requis = True
                                db.commit()
                                
                                if tel_existant:
                                    lien_wa_ex = generer_lien_whatsapp_compte(tel_existant, u_cible.username, nouveau_mdp_temp, u_cible.role)
                                    st.success(f"Mot de passe reinitialise pour **{u_cible.username}** !")
                                    st.info(f"Nouveau MDP provisoire : `{nouveau_mdp_temp}`")
                                    st.markdown(
                                        '<a href="' + lien_wa_ex + '" target="_blank"><button style="background-color:#25D366; color:white; padding:10px 20px; border:none; border-radius:5px; font-weight:bold; cursor:pointer;">📲 Cliquer pour envoyer sur WhatsApp</button></a>',
                                        unsafe_allow_html=True
                                    )
                                else:
                                    st.warning("Veuillez saisir un numero de telephone WhatsApp valide.")
                        except Exception as ex:
                            db.rollback()
                            st.error(f"Erreur lors de la reinitialisation : {ex}")

                if is_school_admin or is_super_admin:
                    st.markdown("---")
                    with st.expander("🚀 Envoi groupé des accès WhatsApp à tous les parents"):
                        st.caption("Cet outil liste tous les comptes parents, met à jour leurs mots de passe provisoires (règle automatique) et génère un tableau avec leurs liens d'envoi WhatsApp en un clic.")
                        
                        if st.button("🔄 Préparer la liste de tous les parents", type="secondary"):
                            parents_tous = db.query(User).filter(User.role == "parent").all()
                            liste_apercu = []
                            for p in parents_tous:
                                el = None
                                if p.eleve_id:
                                    el = db.query(Eleve).filter(Eleve.id == p.eleve_id).first()
                                if not el:
                                    el = db.query(Eleve).filter(Eleve.parent_id == p.id).first()
                                
                                tel_p = el.tuteur if (el and el.tuteur) else ""
                                nom_p = el.nom if (el and el.nom) else p.username
                                
                                if tel_p:
                                    mdp_gen = generer_mdp_personnalise(nom_p, tel_p)
                                    p.password = bcrypt.hashpw(mdp_gen.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                                    p.changer_mdp_requis = True
                                    db.commit()
                                    
                                    lien_w = generer_lien_whatsapp_compte(tel_p, p.username, mdp_gen, p.role)
                                    liste_apercu.append({
                                        "Utilisateur": p.username,
                                        "Élève / Nom": nom_p,
                                        "Téléphone": tel_p,
                                        "Mot de passe": mdp_gen,
                                        "Lien": lien_w
                                    })
                            
                            st.session_state["cache_parents_groupe"] = liste_apercu

                        if "cache_parents_groupe" in st.session_state and st.session_state["cache_parents_groupe"]:
                            st.success(f"✅ {len(st.session_state['cache_parents_groupe'])} parents prêts pour l'envoi !")
                            for idx, item in enumerate(st.session_state["cache_parents_groupe"]):
                                c_g1, c_g2, c_g3 = st.columns([2, 2, 2])
                                c_g1.write(f"👤 **{item['Utilisateur']}**")
                                c_g2.write(f"📞 {item['Téléphone']}")
                                with c_g3:
                                    st.markdown(
                                        '<a href="' + item["Lien"] + '" target="_blank"><button style="background-color:#25D366; color:white; padding:6px 12px; border:none; border-radius:4px; font-weight:bold; cursor:pointer;">📲 Envoyer</button></a>',
                                        unsafe_allow_html=True
                                    )

                if is_school_admin or is_super_admin:
                    st.markdown("---")
                    st.markdown("### Supprimer un utilisateur")
                    
                    usernames_disponibles = [u.username for u in utilisateurs_db if u.username != username_connecte]
                    
                    if usernames_disponibles:
                        user_a_supprimer = st.selectbox("Selectionner l'utilisateur a supprimer", usernames_disponibles, key="select_suppr_user_multitenant")
                        if st.button("Supprimer definitivement", type="primary"):
                            try:
                                user_obj_del = db.query(User).filter(User.username == user_a_supprimer).first()
                                if user_obj_del:
                                    db.query(Eleve).filter(Eleve.parent_id == user_obj_del.id).update({Eleve.parent_id: None})
                                    db.delete(user_obj_del)
                                    db.commit()
                                    st.success(f"L'utilisateur {user_a_supprimer} a ete supprime avec succes !")
                                    st.rerun()
                            except Exception as ex:
                                db.rollback()
                                st.error(f"Erreur lors de la suppression : {ex}")
                    else:
                        st.info("Aucun autre utilisateur disponible a la suppression.")

        with tab_ajout:
            st.markdown(f"### Creation d'un Nouveau Compte Utilisateur — **{school_name}**")

            if st.session_state.get("dernier_compte_cree"):
                compte = st.session_state["dernier_compte_cree"]
                st.success(f"Le compte de **{compte['username']}** ({compte['role']}) a ete cree avec succes !")
                st.info(f"**Identifiant** : `{compte['username']}`\n\n**Mot de passe** : `{compte['password']}`")
                
                if compte['telephone']:
                    lien_wa = generer_lien_whatsapp_compte(compte['telephone'], compte['username'], compte['password'], compte['role'])
                    st.markdown(
                        '<a href="' + lien_wa + '" target="_blank"><button style="background-color:#25D366; color:white; padding:10px 20px; border:none; border-radius:5px; font-weight:bold; cursor:pointer;">📲 Envoyer immédiatement les accès par WhatsApp</button></a>',
                        unsafe_allow_html=True
                    )
                else:
                    st.warning("Aucun numero de telephone n'a ete renseigne pour ce compte.")
                
                if st.button("Creer un autre compte"):
                    del st.session_state["dernier_compte_cree"]
                    st.rerun()
            else:
                if "temp_gen_pwd" not in st.session_state:
                    st.session_state["temp_gen_pwd"] = ""

                with st.form("form_creation_utilisateur_admin"):
                    col1, col2 = st.columns(2)
                    with col1:
                        nouveau_user = st.text_input("Nom d'utilisateur (Identifiant)")
                        nom_personne = st.text_input("Nom complet ou Nom de famille (pour regle MDP auto)")
                        telephone_compte = st.text_input("Telephone (WhatsApp pour l'envoi des acces)")
                        
                        if st.form_submit_button("Appliquer la regle MDP automatique"):
                            if nom_personne and telephone_compte:
                                st.session_state["temp_gen_pwd"] = generer_mdp_personnalise(nom_personne, telephone_compte)
                            else:
                                st.warning("Veuillez d'abord remplir le nom et le telephone.")

                        mot_de_passe = st.text_input(
                            "Mot de passe provisoire",
                            value=st.session_state.get("temp_gen_pwd", ""),
                            type="password",
                        )
                    with col2:
                        role_options = {
                            "fondateur": "Fondateur / Proprietaire",
                            "directeur": "Directeur / Administrateur",
                            "proviseur": "Proviseur / Direction Secondaire",
                            "censeur": "Censeur des Etudes",
                            "enseignant": "Enseignant / Professeur",
                            "econome": "Econome / Finances",
                            "surveillant": "Surveillant General",
                            "inspecteur": "Inspecteur",
                            "parent": "Parent d'eleve",
                        }
                        role_attribue = st.selectbox(
                            "Role / Fonction", options=list(role_options.keys())
                        )
                        cycle_associe = st.selectbox(
                            "Cycle d'affectation",
                            ["College / Lycee", "Maternelle", "Primaire", "College", "Lycee"],
                            index=0
                        )

                    role_descriptions = {
                        "fondateur": "Supervision strategique globale, acces illimite a l'administration et aux finances de l'etablissement.",
                        "directeur": "Acces complet a la gestion administrative, financiere et aux parametres de l'ecole.",
                        "proviseur": "Supervision globale du cycle secondaire, pilotage pedagogique et validation des decisions.",
                        "censeur": "Gestion des emplois du temps, des notes, des cahiers de textes et de la discipline.",
                        "enseignant": "Saisie des notes, emargement du cahier de texte et suivi de classe.",
                        "econome": "Gestion de la tresorerie, encaissements de scolarite et suivi des depenses.",
                        "surveillant": "Gestion des absences, retours de discipline et cahier de correspondance.",
                        "inspecteur": "Supervision pedagogique, apposition de visas et audit des notes.",
                        "parent": "Acces restreint au portail famille pour le suivi exclusif de l'enfant.",
                    }
                    st.markdown(
                        f"<div style='background-color: rgba(217, 119, 6, 0.1); padding: 8px 12px; border-radius: 6px; border-left: 3px solid #D97706; font-size: 0.85rem; color: #E2E8F0; margin-bottom: 10px;'>ℹ <b>Permission :</b> {role_descriptions.get(role_attribue, 'Acces standard')}</div>",
                        unsafe_allow_html=True,
                    )

                    enseignant_lie_id = None
                    if role_attribue == "enseignant":
                        st.markdown("#### Liaison avec un enseignant existant")
                        tous_ens = db.query(Enseignant).filter(Enseignant.school_id == (school_id or 1)).all()
                        ens_sans_compte = [e for e in tous_ens if not db.query(User).filter(User.enseignant_id == e.id).first()]
                        
                        dict_ens = {f"{e.nom} {e.prenom}": e.id for e in ens_sans_compte}
                        if dict_ens:
                            nom_choisi = st.selectbox("Selectionner l'Enseignant a lier", options=list(dict_ens.keys()))
                            if nom_choisi:
                                enseignant_lie_id = dict_ens[nom_choisi]
                        else:
                            st.info("Tous les enseignants ont deja un compte utilisateur associe.")

                    eleves_associes_ids = []
                    if role_attribue == "parent":
                        st.markdown("#### Association des enfants")
                        eleves_query = db.query(Eleve).filter(
                            Eleve.school_id == (school_id or 1),
                            Eleve.deleted_at.is_(None)
                        )
                        if cycle_associe == "College / Lycee":
                            eleves_query = eleves_query.filter(Eleve.cycle.in_(["College", "Lycee"]))
                        elif cycle_associe != "College / Lycee":
                            eleves_query = eleves_query.filter(Eleve.cycle == cycle_associe)
                        
                        tous_les_eleves = eleves_query.all()
                        options_eleves_form = {f"{e.nom} {e.prenom} (Matricule: {e.matricule})": e.id for e in tous_les_eleves}
                        if options_eleves_form:
                            choix_eleves_form = st.multiselect("Selectionner le ou les enfants concernes", list(options_eleves_form.keys()))
                            eleves_associes_ids = [options_eleves_form[nom] for nom in choix_eleves_form]
                        else:
                            st.info("Aucun eleve trouve pour ce cycle.")

                    submitted_user = st.form_submit_button("Enregistrer le compte", type="primary")

                    if submitted_user:
                        if not nouveau_user.strip() or not mot_de_passe.strip():
                            st.error("Le nom d'utilisateur et le mot de passe sont obligatoires.")
                        else:
                            existing_user = db.query(User).filter(User.username == nouveau_user.strip()).first()
                            if existing_user:
                                st.error(f"Un utilisateur avec le nom '{nouveau_user.strip()}' existe deja.")
                            else:
                                try:
                                    hashed_pwd = bcrypt.hashpw(mot_de_passe.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
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
                                        action=f"Creation du compte {nouveau_user.strip()} ({role_attribue})",
                                        statut="Succes",
                                        valeur_avant="Inexistant",
                                        valeur_apres=f"Role: {role_attribue}",
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
                                    st.error(f"Erreur lors de la creation du compte : {ex}")

    except Exception as e:
        db.rollback()
        st.error(f"Une erreur est survenue lors du chargement de la gestion des utilisateurs : {e}")
    finally:
        db.close()