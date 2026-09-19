from datetime import datetime, timedelta
import re
import unicodedata
import time
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

    # --- INITIALISATION ROBUSTE DU SUPER ADMIN GLOBAL ---
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

        tab_login, tab_trial = st.tabs(
            ["🔐 Connexion", "🚀 Créer un Essai Démo"]
        )

        with tab_login:
            # --- CONTRÔLE RATE LIMITING (ANTI-BRUTE FORCE) ---
            if "login_attempts" not in st.session_state:
                st.session_state["login_attempts"] = 0
            if "lockout_time" not in st.session_state:
                st.session_state["lockout_time"] = 0

            if st.session_state["lockout_time"] > time.time():
                temps_restant = int(st.session_state["lockout_time"] - time.time())
                st.error(f"🔒 Trop de tentatives infructueuses. Veuillez patienter {temps_restant} secondes.")
                st.stop()

            # --- INTERCEPTION DU CHANGEMENT DE MOT DE PASSE OBLIGATOIRE ---
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
                        if len(nouveau_p.strip()) < 6:
                            st.error(
                                "⚠️ Le mot de passe doit contenir au moins 6 caractères."
                            )
                        elif nouveau_p != confirme_p:
                            st.error("⚠️ Les mots de passe ne correspondent pas.")
                        else:
                            db = SessionLocal()
                            try:
                                username_cible = st.session_state.get("pending_username")
                                user_obj = (
                                    db.query(User)
                                    .filter(User.username == username_cible)
                                    .first()
                                )
                                if user_obj:
                                    salt = bcrypt.gensalt()
                                    user_obj.password = bcrypt.hashpw(
                                        nouveau_p.strip().encode("utf-8"), salt
                                    ).decode("utf-8")
                                    user_obj.changer_mdp_requis = False
                                    db.commit()

                                    st.session_state["authenticated"] = True
                                    st.session_state["username"] = user_obj.username
                                    role_db = str(user_obj.role or "").strip().lower()
                                    if role_db == "admin":
                                        role_db = "administrateur"
                                    st.session_state["role"] = role_db
                                    st.session_state["school_id"] = user_obj.school_id
                                    st.session_state["is_super_admin"] = (role_db == "super_admin")

                                    if user_obj.school_id:
                                        ecole = (
                                            db.query(School)
                                            .filter(School.id == user_obj.school_id)
                                            .first()
                                        )
                                        st.session_state["school_name"] = (
                                            ecole.nom if ecole else "Gestion Scolaire Pro"
                                        )
                                    else:
                                        st.session_state["school_name"] = "Plateforme Globale"

                                    del st.session_state["pending_password_change"]
                                    del st.session_state["pending_username"]

                                    st.success("✅ Mot de passe mis à jour avec succès !")
                                    st.rerun()
                            except Exception as e:
                                db.rollback()
                                st.error(f"Erreur lors de la mise à jour : {e}")
                            finally:
                                db.close()
                return

            # --- FORMULAIRE DE CONNEXION CLASSIQUE ---
            with st.form("form_connexion_pro"):
                st.markdown("### Connexion à votre espace")
                username_input = st.text_input("Identifiant")
                password_input = st.text_input("Mot de passe", type="password")

                submitted = st.form_submit_button(
                    "Se connecter", use_container_width=True
                )

                if submitted:
                    clean_username = username_input.strip()
                    clean_password = password_input.strip()

                    if not clean_username or not clean_password:
                        st.error("⚠️ Veuillez renseigner l'identifiant et le mot de passe.")
                    else:
                        db = SessionLocal()
                        try:
                            user = (
                                db.query(User)
                                .filter(User.username == clean_username)
                                .first()
                            )

                            password_valid = False
                            if user and user.password:
                                try:
                                    stored_hash = user.password
                                    if isinstance(stored_hash, str):
                                        stored_hash = stored_hash.encode("utf-8")
                                        
                                    password_valid = bcrypt.checkpw(
                                        clean_password.encode("utf-8"),
                                        stored_hash,
                                    )
                                except Exception:
                                    password_valid = False

                            if user and password_valid:
                                # Réinitialisation du compteur d'échecs en cas de succès
                                st.session_state["login_attempts"] = 0
                                st.session_state["lockout_time"] = 0

                                role_db = str(user.role or "").strip().lower()
                                if role_db == "admin":
                                    role_db = "administrateur"

                                is_super = role_db == "super_admin"

                                # --- CONTRÔLE D'ABONNEMENT ET D'ESSAI SÉCURISÉ ---
                                if user.school_id and not is_super:
                                    ecole = (
                                        db.query(School)
                                        .filter(School.id == user.school_id)
                                        .first()
                                    )
                                    if ecole:
                                        if not getattr(ecole, "actif", True):
                                            st.error(f"⛔ L'établissement '{ecole.nom}' a été suspendu.")
                                            db.close()
                                            return

                                        if getattr(ecole, "is_trial", False) and ecole.trial_expires_at:
                                            trial_exp = ecole.trial_expires_at
                                            if hasattr(trial_exp, "tzinfo") and trial_exp.tzinfo is not None:
                                                trial_exp = trial_exp.replace(tzinfo=None)
                                            if datetime.now() > trial_exp:
                                                st.error(f"🔒 Période d'essai expirée pour '{ecole.nom}'.")
                                                db.close()
                                                return

                                if getattr(user, "changer_mdp_requis", False):
                                    st.session_state["pending_password_change"] = True
                                    st.session_state["pending_username"] = user.username
                                    db.close()
                                    st.rerun()

                                # --- HYDRATATION ATOMIQUE DE LA SESSION ---
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
                                        ecole.nom if ecole else "Gestion Scolaire Pro"
                                    )
                                else:
                                    st.session_state["school_name"] = "Plateforme Globale"

                                st.success("✅ Connexion réussie ! Chargement...")
                                st.rerun()
                            else:
                                # Incrémentation des échecs pour le Rate Limiting
                                st.session_state["login_attempts"] += 1
                                if st.session_state["login_attempts"] >= 5:
                                    st.session_state["lockout_time"] = time.time() + 30
                                    st.session_state["login_attempts"] = 0
                                    st.warning("⚠️ Trop d'échecs consécutifs. Compte temporairement verrouillé pour 30 secondes.")
                                else:
                                    st.error("⛔ Identifiant ou mot de passe incorrect.")
                        finally:
                            db.close()

        with tab_trial:
            st.markdown("### 🚀 Créer un compte d'essai (14 jours)")
            st.markdown("Testez instantanément la plateforme avec votre propre établissement.")

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
                    clean_nom_ecole = nom_ecole_trial.strip()
                    clean_code_ecole = code_ecole_trial.strip().upper()
                    clean_admin_user = admin_username_trial.strip()
                    clean_admin_pass = admin_password_trial.strip()

                    if not clean_nom_ecole or not clean_code_ecole or not clean_admin_user or not clean_admin_pass:
                        st.error("⚠️ Veuillez remplir tous les champs.")
                    elif len(clean_admin_pass) < 6:
                        st.error("⚠️ Le mot de passe doit contenir au moins 6 caractères.")
                    else:
                        db_trial = SessionLocal()
                        try:
                            existing_school = (
                                db_trial.query(School)
                                .filter(
                                    (School.nom == clean_nom_ecole)
                                    | (School.code == clean_code_ecole)
                                )
                                .first()
                            )
                            existing_user = (
                                db_trial.query(User)
                                .filter(User.username == clean_admin_user)
                                .first()
                            )

                            if existing_school:
                                st.error("⛔ Un établissement avec ce nom ou ce code existe déjà.")
                            elif existing_user:
                                st.error("⛔ Ce nom d'utilisateur est déjà pris.")
                            else:
                                sub = generate_subdomain(clean_nom_ecole)
                                new_school = School(
                                    nom=clean_nom_ecole,
                                    code=clean_code_ecole,
                                    subdomain=sub,
                                    actif=True,
                                    is_trial=True,
                                    trial_expires_at=datetime.now() + timedelta(days=14),
                                )
                                db_trial.add(new_school)
                                db_trial.commit()
                                db_trial.refresh(new_school)

                                hashed_pwd = bcrypt.hashpw(
                                    clean_admin_pass.encode("utf-8"),
                                    bcrypt.gensalt(),
                                ).decode("utf-8")

                                new_admin = User(
                                    username=clean_admin_user,
                                    password=hashed_pwd,
                                    role="administrateur",
                                    school_id=new_school.id,
                                    changer_mdp_requis=False,
                                )
                                db_trial.add(new_admin)
                                db_trial.commit()

                                st.success(
                                    "🎉 Établissement créé avec succès !"
                                    f" Sous-domaine attribué : `{sub}.gestionscolairepro.com`"
                                )
                                st.info("Vous pouvez maintenant vous connecter dans l'onglet **Connexion**.")
                        except Exception as ex:
                            db_trial.rollback()
                            st.error(f"Erreur lors de la création de l'essai : {ex}")
                        finally:
                            db_trial.close()