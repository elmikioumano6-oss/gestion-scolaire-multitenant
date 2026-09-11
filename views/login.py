from datetime import datetime, timedelta
import re
import unicodedata
import bcrypt
import streamlit as st
from database.db_config import SessionLocal
from database.models import School, User


def generate_subdomain(school_name):
    nfkd_form = unicodedata.normalize("NFKD", school_name)
    only_ascii = nfkd_form.encode("ASCII", "ignore").decode("utf-8")
    slug = re.sub(r"[^a-z0-9]+", "-", only_ascii.lower()).strip("-")
    return slug


def afficher_login():
    # Style épuré pour la page de connexion
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"] { display: none !important; }
            .login-container {
                max-width: 450px;
                margin: 0 auto;
                padding: 2rem;
                background-color: #ffffff;
                border-radius: 10px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # --- INITIALISATION UNIQUEMENT DU SUPER ADMIN GLOBAL ---
    db_init = SessionLocal()
    try:
        admin_verif = db_init.query(User).filter(User.username == "admin").first()
        new_h = bcrypt.hashpw(
            "admin2026".encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        if not admin_verif:
            ecole_d = db_init.query(School).first()
            s_id = ecole_d.id if ecole_d else None
            db_init.add(
                User(
                    username="admin",
                    password=new_h,
                    role="super_admin",
                    school_id=s_id,
                    changer_mdp_requis=False,
                )
            )
            db_init.commit()
        else:
            admin_verif.password = new_h
            admin_verif.role = "super_admin"
            admin_verif.changer_mdp_requis = False
            db_init.commit()
    except Exception:
        db_init.rollback()
    finally:
        db_init.close()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            "<br><h1 style='text-align: center; color: #C5A059;'>🏫 Gestion"
            " Scolaire Pro</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align: center; color: #6c757d; margin-bottom:"
            " 2rem;'>Plateforme Multi-Tenant de Gestion Scolaire</p>",
            unsafe_allow_html=True,
        )

        # Gestion des onglets : Connexion vs Inscription Démo / Essai (Self-Service)
        tab_login, tab_trial = st.tabs(
            ["🔐 Connexion", "🚀 Créer un Essai Démo"]
        )

        with tab_login:
            # --- ÉTAPE 1 : INTERCEPTION DU CHANGEMENT DE MOT DE PASSE OBLIGATOIRE ---
            if st.session_state.get("pending_password_change", False):
                st.warning("🔒 Sécurité Obligatoire de Première Connexion")
                st.markdown(
                    "Vous êtes connecté avec un mot de passe provisoire. Veuillez"
                    " définir votre nouveau mot de passe personnel."
                )

                with st.form("form_change_mdp_provisoire"):
                    nouveau_p = st.text_input(
                        "Nouveau mot de passe (6 caractères min.)",
                        type="password",
                    )
                    confirme_p = st.text_input(
                        "Confirmer le nouveau mot de passe", type="password"
                    )
                    submit_chg = st.form_submit_button(
                        "Enregistrer mon nouveau mot de passe",
                        use_container_width=True,
                    )

                    if submit_chg:
                        if len(nouveau_p) < 6:
                            st.error(
                                "⚠️ Le mot de passe doit contenir au moins 6"
                                " caractères."
                            )
                        elif nouveau_p != confirme_p:
                            st.error(
                                "⚠️ Les mots de passe ne correspondent pas."
                            )
                        else:
                            db = SessionLocal()
                            try:
                                username_cible = st.session_state.get(
                                    "pending_username"
                                )
                                user_obj = (
                                    db.query(User)
                                    .filter(
                                        User.username == username_cible
                                    )
                                    .first()
                                )
                                if user_obj:
                                    salt = bcrypt.gensalt()
                                    user_obj.password = bcrypt.hashpw(
                                        nouveau_p.encode("utf-8"), salt
                                    ).decode("utf-8")
                                    user_obj.changer_mdp_requis = False
                                    db.commit()

                                    # Nettoyage de l'état temporaire et connexion définitive
                                    st.session_state["authenticated"] = True
                                    st.session_state["username"] = (
                                        user_obj.username
                                    )
                                    role_db = str(
                                        user_obj.role or ""
                                    ).strip().lower()
                                    st.session_state["role"] = role_db
                                    st.session_state["school_id"] = (
                                        user_obj.school_id
                                    )
                                    st.session_state["is_super_admin"] = (
                                        role_db == "super_admin"
                                    )

                                    if user_obj.school_id:
                                        ecole = (
                                            db.query(School)
                                            .filter(
                                                School.id == user_obj.school_id
                                            )
                                            .first()
                                        )
                                        st.session_state["school_name"] = (
                                            ecole.nom
                                            if ecole
                                            else "Gestion Scolaire Pro"
                                        )
                                    else:
                                        st.session_state["school_name"] = (
                                            "Plateforme Globale"
                                        )

                                    del st.session_state[
                                        "pending_password_change"
                                    ]
                                    del st.session_state["pending_username"]

                                    st.success(
                                        "✅ Mot de passe mis à jour avec succès !"
                                        " Accès à la plateforme..."
                                    )
                                    st.rerun()
                            except Exception as e:
                                db.rollback()
                                st.error(
                                    f"Erreur lors de la mise à jour : {e}"
                                )
                            finally:
                                db.close()
                return

            # --- ÉTAPE 2 : FORMULAIRE DE CONNEXION CLASSIQUE ---
            with st.form("form_connexion_pro"):
                st.markdown("### Connexion à votre espace")
                username_input = st.text_input("Identifiant")
                password_input = st.text_input("Mot de passe", type="password")

                submitted = st.form_submit_button(
                    "Se connecter", use_container_width=True
                )

                if submitted:
                    if not username_input.strip() or not password_input.strip():
                        st.error(
                            "⚠️ Veuillez renseigner l'identifiant et le mot de"
                            " passe."
                        )
                    else:
                        db = SessionLocal()
                        try:
                            user = (
                                db.query(User)
                                .filter(
                                    User.username == username_input.strip()
                                )
                                .first()
                            )

                            password_valid = False
                            if user and user.password:
                                try:
                                    password_valid = bcrypt.checkpw(
                                        password_input.encode("utf-8"),
                                        user.password.encode("utf-8"),
                                    )
                                except Exception:
                                    password_valid = False

                            if user and password_valid:
                                role_db = str(
                                    user.role or ""
                                ).strip().lower()
                                is_super = role_db == "super_admin"

                                # --- CONTRÔLE D'ABONNEMENT ET D'ESSAI ---
                                if user.school_id and not is_super:
                                    ecole = (
                                        db.query(School)
                                        .filter(School.id == user.school_id)
                                        .first()
                                    )
                                    if ecole:
                                        # 1. Vérification de la suspension manuelle
                                        if not getattr(ecole, "actif", True):
                                            st.error(
                                                f"⛔ L'établissement '{ecole.nom}' a"
                                                " été suspendu par l'administration."
                                            )
                                            db.close()
                                            return

                                        # 2. Vérification de l'expiration de la période d'essai (is_trial)
                                        if getattr(ecole, "is_trial", False) and ecole.trial_expires_at:
                                            if datetime.now() > ecole.trial_expires_at:
                                                st.error(
                                                    f"🔒 Période d'essai expirée : La période d'essai de 14 jours pour l'établissement '{ecole.nom}' est arrivée à terme. Veuillez contacter le support pour activer votre abonnement."
                                                )
                                                db.close()
                                                return

                                if getattr(
                                    user, "changer_mdp_requis", False
                                ):
                                    st.session_state[
                                        "pending_password_change"
                                    ] = True
                                    st.session_state["pending_username"] = (
                                        user.username
                                    )
                                    db.close()
                                    st.rerun()

                                st.session_state["authenticated"] = True
                                st.session_state["username"] = user.username
                                st.session_state["role"] = role_db
                                st.session_state["school_id"] = user.school_id
                                st.session_state["is_super_admin"] = is_super

                                if user.school_id:
                                    ecole = (
                                        db.query(School)
                                        .filter(School.id == user.school_id)
                                        .first()
                                    )
                                    st.session_state["school_name"] = (
                                        ecole.nom
                                        if ecole
                                        else "Gestion Scolaire Pro"
                                    )
                                else:
                                    st.session_state["school_name"] = (
                                        "Plateforme Globale"
                                    )

                                st.success("✅ Connexion réussie ! Chargement...")
                                st.rerun()
                            else:
                                st.error(
                                    "⛔ Identifiant ou mot de passe incorrect."
                                )
                        finally:
                            db.close()

        with tab_trial:
            st.markdown("### 🚀 Créer un compte d'essai (14 jours)")
            st.markdown(
                "Testez instantanément la plateforme avec votre propre"
                " établissement."
            )

            with st.form("form_trial_signup"):
                nom_ecole_trial = st.text_input(
                    "Nom de l'établissement",
                    placeholder="ex: Complexe Scolaire Horizon",
                )
                code_ecole_trial = st.text_input(
                    "Code unique de l'école", placeholder="ex: CS-HORIZON"
                )
                admin_username_trial = st.text_input(
                    "Nom d'utilisateur Administrateur",
                    placeholder="ex: admin_horizon",
                )
                admin_password_trial = st.text_input(
                    "Mot de passe", type="password"
                )

                submit_trial = st.form_submit_button(
                    "Lancer mon essai gratuit", use_container_width=True
                )

                if submit_trial:
                    if (
                        not nom_ecole_trial.strip()
                        or not code_ecole_trial.strip()
                        or not admin_username_trial.strip()
                        or not admin_password_trial.strip()
                    ):
                        st.error("⚠️ Veuillez remplir tous les champs.")
                    elif len(admin_password_trial) < 6:
                        st.error(
                            "⚠️ Le mot de passe doit contenir au moins 6"
                            " caractères."
                        )
                    else:
                        db_trial = SessionLocal()
                        try:
                            # Vérifier unicité
                            existing_school = (
                                db_trial.query(School)
                                .filter(
                                    (School.nom == nom_ecole_trial.strip())
                                    | (
                                        School.code
                                        == code_ecole_trial.strip().upper()
                                    )
                                )
                                .first()
                            )
                            existing_user = (
                                db_trial.query(User)
                                .filter(
                                    User.username
                                    == admin_username_trial.strip()
                                )
                                .first()
                            )

                            if existing_school:
                                st.error(
                                    "⛔ Un établissement avec ce nom ou ce code"
                                    " existe déjà."
                                )
                            elif existing_user:
                                st.error(
                                    "⛔ Ce nom d'utilisateur est déjà pris."
                                )
                            else:
                                sub = generate_subdomain(nom_ecole_trial)
                                new_school = School(
                                    nom=nom_ecole_trial.strip(),
                                    code=code_ecole_trial.strip().upper(),
                                    subdomain=sub,
                                    actif=True,
                                    is_trial=True,
                                    trial_expires_at=datetime.now()
                                    + timedelta(days=14),
                                )
                                db_trial.add(new_school)
                                db_trial.commit()
                                db_trial.refresh(new_school)

                                hashed_pwd = bcrypt.hashpw(
                                    admin_password_trial.encode("utf-8"),
                                    bcrypt.gensalt(),
                                ).decode("utf-8")
                                new_admin = User(
                                    username=admin_username_trial.strip(),
                                    password=hashed_pwd,
                                    role="administrateur",  # Mis à jour à "administrateur" pour correspondre au routage de app.py
                                    school_id=new_school.id,
                                    changer_mdp_requis=False,
                                )
                                db_trial.add(new_admin)
                                db_trial.commit()

                                st.success(
                                    "🎉 Établissement créé avec succès !"
                                    f" Sous-domaine attribué : `{sub}.gestionscolairepro.com`"
                                )
                                st.info(
                                    "Vous pouvez maintenant vous connecter avec"
                                    " vos identifiants dans l'onglet"
                                    " **Connexion**."
                                )
                        except Exception as ex:
                            db_trial.rollback()
                            st.error(
                                f"Erreur lors de la création de l'essai : {ex}"
                            )
                        finally:
                            db_trial.close()