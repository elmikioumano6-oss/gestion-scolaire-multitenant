import importlib
import inspect
from datetime import datetime
import os
from database.db_config import SessionLocal, init_db
from database.models import AnneeScolaire, User, School
import streamlit as st
import bcrypt
from streamlit_option_menu import option_menu


def init_tenant_context():
    """Détecte le tenant par sous-domaine ou initialise l'école par défaut en session."""
    if "school_id" in st.session_state and st.session_state["school_id"]:
        return

    db = SessionLocal()
    try:
        subdomain = "default"
        try:
            host = st.context.headers.get("Host", "") or st.context.headers.get("X-Forwarded-Host", "")
            if host and "localhost" not in host and "127.0.0.1" not in host:
                parts = host.split(".")
                if len(parts) > 2:
                    subdomain = parts[0].lower()
        except Exception:
            pass

        school = None
        if subdomain != "default":
            school = db.query(School).filter(School.subdomain == subdomain).first()
        
        # Fallback sur la première école si aucun sous-domaine ne correspond
        if not school:
            school = db.query(School).first()

        if school:
            st.session_state["school_id"] = school.id
            st.session_state["school_name"] = school.nom
            st.session_state["school_code"] = school.code
        else:
            st.session_state["school_id"] = 1
            st.session_state["school_name"] = "Default School"
    finally:
        db.close()


def main():
    st.set_page_config(
        page_title="Gestion Scolaire Pro - Plateforme Multi-Tenant",
        page_icon="🏫",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # --- INITIALISATION ET MIGRATIONS AUTOMATIQUES ---
    init_db()
    
    # --- INITIALISATION DU CONTEXTE MULTI-TENANT ---
    init_tenant_context()

    # --- INITIALISATION DE L'ÉTAT DE SESSION ---
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "role" not in st.session_state:
        st.session_state["role"] = "login"
    if "username" not in st.session_state:
        st.session_state["username"] = ""
    if "school_id" not in st.session_state:
        st.session_state["school_id"] = None
    if "school_name" not in st.session_state:
        st.session_state["school_name"] = ""
    if "is_super_admin" not in st.session_state:
        st.session_state["is_super_admin"] = False

    # --- 1. GESTION DE LA DÉCONNEXION OU DE L'ÉTAT NON AUTHENTIFIÉ ---
    if not st.session_state.get("authenticated") or not st.session_state.get(
        "username"
    ):
        st.query_params.clear()
        st.markdown(
            """
                <style>
                    [data-testid="stSidebar"] { display: none !important; }
                </style>
                """,
            unsafe_allow_html=True,
        )
        try:
            module = importlib.import_module("views.login")
            fonction = getattr(module, "afficher_login")
            fonction()
        except Exception as e:
            st.error(f"Erreur lors du chargement de la page de connexion : {e}")
            if "Invalid salt" in str(e):
                st.warning(
                    "⚠️ L'ancien mot de passe en base utilise un format incompatible."
                    " Veuillez réinitialiser le mot de passe administrateur."
                )
        return

    # --- 2. GARDIEN DE SÉCURITÉ (GATEKEEPER) & INTERCEPTION DU MOT DE PASSE ---
    nom_utilisateur = st.session_state.get("username")
    role_utilisateur = str(st.session_state.get("role", "")).lower()
    is_super_admin = st.session_state.get("is_super_admin", False)

    # 🔒 CONFINEMENT MULTI-TENANT STRICT : admin_rahmat ne doit jamais être super admin global
    if nom_utilisateur and "rahmat" in nom_utilisateur.lower():
        is_super_admin = False
        st.session_state["is_super_admin"] = False

    db_sec = SessionLocal()
    try:
        current_user = (
            db_sec.query(User).filter(User.username == nom_utilisateur).first()
        )
        if not current_user:
            db_sec.close()
            st.session_state.clear()
            st.rerun()

        # Vérification si l'établissement a été suspendu par le Super Admin
        if current_user.school_id and not is_super_admin:
            ecole_verif = (
                db_sec.query(School)
                .filter(School.id == current_user.school_id)
                .first()
            )
            if ecole_verif and not getattr(ecole_verif, "actif", True):
                db_sec.close()
                st.session_state.clear()
                st.error(
                    f"⛔ L'établissement '{ecole_verif.nom}' a été suspendu. Veuillez"
                    " contacter l'administrateur de la plateforme."
                )
                st.stop()

        # 🔒 INTERCEPTION OBLIGATOIRE SI CHANGEMENT DE MOT DE PASSE REQUIS
        if not is_super_admin and getattr(
            current_user, "changer_mdp_requis", False
        ):
            st.markdown(
                """
                    <style>
                        [data-testid="stSidebar"] { display: none !important; }
                    </style>
                    """,
                unsafe_allow_html=True,
            )

            st.markdown(
                "<br><h2 style='text-align: center; color: #C5A059;'>🔒 Sécurité"
                " Obligatoire de Première Connexion</h2>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<p style='text-align: center; color: #6c757d;'>Vous êtes connecté"
                " avec un mot de passe provisoire. Veuillez définir votre nouveau"
                " mot de passe personnel pour accéder à la plateforme.</p>",
                unsafe_allow_html=True,
            )

            col_c1, col_c2, col_c3 = st.columns([1, 2, 1])
            with col_c2:
                with st.form("form_securite_mdp_force"):
                    nouveau_p = st.text_input(
                        "Nouveau mot de passe (6 caractères min.)", type="password"
                    )
                    confirme_p = st.text_input(
                        "Confirmer le nouveau mot de passe", type="password"
                    )
                    submit_btn = st.form_submit_button(
                        "Enregistrer mon nouveau mot de passe",
                        use_container_width=True,
                        type="primary",
                    )

                    if submit_btn:
                        if len(nouveau_p) < 6:
                            st.error(
                                "⚠️ Le mot de passe doit contenir au moins 6 caractères."
                            )
                        elif nouveau_p != confirme_p:
                            st.error("⚠️ Les mots de passe ne correspondent pas.")
                        else:
                            try:
                                salt = bcrypt.gensalt()
                                hashed = bcrypt.hashpw(nouveau_p.encode("utf-8"), salt)
                                current_user.password = hashed.decode("utf-8")
                                current_user.changer_mdp_requis = False
                                db_sec.commit()
                                st.success(
                                    "✅ Mot de passe mis à jour avec succès ! Chargement de"
                                    " l'application..."
                                )
                                st.rerun()
                            except Exception as ex:
                                db_sec.rollback()
                                st.error(
                                    f"Erreur lors de la mise à jour du mot de passe : {ex}"
                                )
            db_sec.close()
            return  # Bloque totalement l'accès au reste tant que le MDP n'est pas changé

        # Mise à jour de la dernière activité (pour l'audit)
        current_user.derniere_activite = datetime.now()
        db_sec.commit()
    except Exception:
        db_sec.rollback()
    finally:
        db_sec.close()

    # --- 3. BARRE LATÉRALE & NAVIGATION ---
    with st.sidebar:
        try:
            school_name_lower = st.session_state.get("school_name", "").lower()
            if "etoile" in school_name_lower:
                logo_file = "Logo L'ETOILE DU SUCCES.png"
            else:
                logo_file = (
                    "Logo Gestion Scolaire Pro.png"
                    if os.path.exists("Logo Gestion Scolaire Pro.png")
                    else "Logo CSP-RAHMAT-FH.png"
                )

            col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
            with col_logo2:
                if os.path.exists(logo_file):
                    st.image(logo_file, width=100)
                else:
                    st.markdown(
                        "<div style='text-align: center;'><h3>🏫</h3></div>",
                        unsafe_allow_html=True,
                    )
        except Exception:
            st.markdown(
                "<div style='text-align: center;'><h3>🏫</h3></div>",
                unsafe_allow_html=True,
            )

        nom_affiche_ecole = st.session_state.get(
            "school_name", "Gestion Scolaire Pro"
        )
        st.markdown(
            f"""
                <div style="text-align: left; margin-top: -5px; margin-bottom: 0px;">
                    <h3 style="color: #C5A059; font-family: 'Georgia', serif; font-size: 1.1rem; font-weight: 700; margin-bottom: 0px; letter-spacing: 0.5px;">{nom_affiche_ecole}</h3>
                    <p style='color: #D4AF37; font-size: 0.8rem; font-style: italic; font-weight: 500; margin-top: 2px; margin-bottom: 0px;'>Gestion Scolaire Pro</p>
                </div>
                """,
            unsafe_allow_html=True,
        )

        st.markdown(
            "<hr style='margin: 0.5rem 0 0.8rem 0; border-color: rgba(197, 160, 89,"
            " 0.3);'>",
            unsafe_allow_html=True,
        )

        niveau_actif = "Collège"

        # --- DÉFINITION DES MENUS SELON LE RÔLE ---
        if is_super_admin:
            st.markdown("#### 🏛️ Gouvernance ERP")
            st.info(f"Connecté : **{nom_utilisateur}**")
            options_menu = [
                "📊 Pilotage & BI",
                "🏢 Gestion des Tenants",
                "👥 IAM & Sécurité",
                "📜 Piste d'Audit",
                "💾 Infrastructure & Backup",
                "⚙️ Paramètres Système",
            ]
            icons_menu = [
                "speedometer2",
                "globe",
                "shield-lock",
                "clock-history",
                "database",
                "gear",
            ]
            menu_key_val = "menu_super_admin_erp"

        elif role_utilisateur == "inspecteur":
            st.markdown("#### 🔍 Portail Inspecteur")
            st.info(f"Connecté : **{nom_utilisateur}**")
            options_menu = [
                "Accueil",
                "Tableau de Bord",
                "Espace Inspection",
                "Suivi des Programmes",
                "Supervision cahier",
                "Journal d'activité",
                "Messages",
            ]
            icons_menu = [
                "house",
                "speedometer2",
                "clipboard-check",
                "graph-up",
                "eye",
                "clock-history",
                "chat-dots",
            ]
            menu_key_val = "menu_inspecteur"

        elif role_utilisateur == "censeur":
            st.markdown("#### 📐 Portail Censeur")
            st.info(f"Connecté : **{nom_utilisateur}**")
            niveau_actif = st.selectbox(
                "Cycle actif",
                ["Primaire", "Collège", "Lycée"],
                index=1,
                key="global_niveau_actif_censeur",
            )
            st.session_state["cycle_actif"] = niveau_actif
            st.markdown(
                "<hr style='margin: 0.5rem 0 0.5rem 0; border-color:"
                " rgba(255,255,255,0.1);'>",
                unsafe_allow_html=True,
            )
            options_menu = [
                "Accueil",
                "Tableau de Bord",
                "Matières & Coeffs",
                "Classes & Tarifs",
                "Emploi du temps",
                "Planification des évaluations",
                "Cahier de Texte",
                "Supervision cahier",
                "Présence",
                "Conseil de classe",
                "Bulletins",
                "Alerte Performance",
                "Suivi des Programmes",
                "Enseignants",
                "Paramètres",
                "Messages",
            ]
            icons_menu = [
                "house",
                "speedometer2",
                "book",
                "grid",
                "calendar-week",
                "clock",
                "journal-text",
                "eye",
                "check-circle",
                "award",
                "journal-richtext",
                "exclamation-triangle",
                "graph-up",
                "person-badge",
                "gear",
                "chat-dots",
            ]
            menu_key_val = "menu_censeur"

        elif role_utilisateur == "enseignant":
            st.markdown("#### 👨‍🏫 Portail Enseignant")
            st.info(f"Connecté : **{nom_utilisateur}**")
            options_menu = ["Espace Enseignants", "Cahier de Texte", "Saisie des notes"]
            icons_menu = ["person-video3", "journal-text", "pencil-square"]
            menu_key_val = "menu_enseignant"

        elif role_utilisateur == "parent":
            st.markdown("#### 👨‍👩‍👧 Portail Famille")
            st.info(f"Connecté : **{nom_utilisateur}**")
            options_menu = ["Espace Parent", "Messages"]
            icons_menu = ["house-heart", "chat-dots"]
            menu_key_val = "menu_parent"

        else:  # Administrateur de l'école (Tenant Admin)
            st.markdown("#### 🏫 Pilotage Administratif")
            niveau_actif = st.selectbox(
                "Cycle d'enseignement actif",
                ["Primaire", "Collège", "Lycée"],
                index=1,
                key="global_niveau_actif",
            )
            st.session_state["cycle_actif"] = niveau_actif
            st.markdown(
                "<hr style='margin: 0.5rem 0 0.5rem 0; border-color:"
                " rgba(255,255,255,0.1);'>",
                unsafe_allow_html=True,
            )
            options_menu = [
                "Accueil",
                "Tableau de Bord",
                "Année Scolaire",
                "Matières & Coeffs",
                "Classes & Tarifs",
                "Inscription Élèves",
                "Cartes Scolaires",
                "Emploi du temps",
                "Planification des évaluations",
                "Cahier de Texte",
                "Supervision cahier",
                "Présence",
                "Saisie des notes",
                "Consultations des notes",
                "Espace Inspection",
                "Conseil de classe",
                "Bulletins",
                "Alerte Performance",
                "Espace Enseignants",
                "Suivi des Programmes",
                "Enseignants",
                "Personnels et rôles",
                "Gestion Comptes",
                "Import Programmes PDF",
                "Encaissement",
                "Stats Encaissements",
                "Tableau Finances",
                "Soldes & Impayés",
                "Dépenses",
                "Rapports",
                "Paramètres",
                "Journal d'activité",
                "Messages",
                "Espace Parent",
                "Backup",
            ]
            icons_menu = [
                "house",
                "speedometer2",
                "calendar",
                "book",
                "grid",
                "person-plus",
                "card-text",
                "calendar-week",
                "clock",
                "journal-text",
                "eye",
                "check-circle",
                "pencil-square",
                "search",
                "clipboard-check",
                "award",
                "journal-richtext",
                "exclamation-triangle",
                "person-video3",
                "graph-up",
                "person-badge",
                "shield-lock",
                "people",
                "file-pdf",
                "cash-coin",
                "bar-chart-fill",
                "wallet2",
                "receipt",
                "file-earmark-bar-graph",
                "file-earmark-bar-graph",
                "gear",
                "clock-history",
                "chat-dots",
                "house-heart",
                "database",
            ]
            menu_key_val = "menu_principal_admin"

        page_demandee = st.query_params.get("page", options_menu[0])
        default_idx = (
            options_menu.index(page_demandee)
            if page_demandee in options_menu
            else 0
        )

        menu_option = option_menu(
            menu_title=None,
            options=options_menu,
            icons=icons_menu,
            menu_icon="cast",
            default_index=default_idx,
            key=menu_key_val,
            styles={
                "container": {"padding": "0!important", "background-color": "#0d1b2a"},
                "icon": {"color": "#ff8800", "font-size": "14px"},
                "nav-link": {
                    "font-size": "13px",
                    "text-align": "left",
                    "margin": "1px 0px",
                    "color": "#e0e1dd",
                    "--hover-color": "#1b263b",
                },
                "nav-link-selected": {
                    "background-color": "#ff8800",
                    "color": "#ffffff",
                },
            },
        )

        st.query_params["user"] = nom_utilisateur
        st.query_params["role"] = role_utilisateur
        st.query_params["page"] = menu_option

        st.markdown("---")

        db_sidebar = SessionLocal()
        try:
            annee_courante = (
                db_sidebar.query(AnneeScolaire)
                .filter(AnneeScolaire.active == True)
                .first()
            )
            libelle_annee = annee_courante.libelle if annee_courante else "2026-2027"
        except Exception:
            libelle_annee = "2026-2027"
        finally:
            db_sidebar.close()

        st.markdown(
            f"<div style='text-align: center; color: #C5A059; font-size: 0.75rem;'>Année"
            f" Scolaire : <b>{libelle_annee}</b><br>Niamey, Niger</div>",
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)

        if st.button(
            "🚪 Se déconnecter", use_container_width=True, type="secondary"
        ):
            st.session_state.clear()
            st.query_params.clear()
            st.success("Déconnexion réussie !")
            st.rerun()

    # --- 4. DICTIONNAIRE DE ROUTAGE (ERP STANDARD) ---
    ROUTES = {
        # Piliers Super Admin ERP
        "📊 Pilotage & BI": ("views.accueil", "afficher_accueil"),
        "🏢 Gestion des Tenants": ("views.super_admin", "afficher_super_admin"),
        "👥 IAM & Sécurité": (
            "views.gestion_utilisateurs",
            "afficher_gestion_utilisateurs",
        ),
        "📜 Piste d'Audit": ("views.journal_activite", "afficher_journal_activite"),
        "💾 Infrastructure & Backup": ("views.backup", "afficher_backup"),
        "⚙️ Paramètres Système": ("views.parametres", "afficher_parametres"),
        # Modules standards administration et autres rôles
        "Administration Globale": (
            "views.super_admin",
            "afficher_super_admin",
        ),
        "Accueil": ("views.accueil", "afficher_accueil"),
        "Tableau de Bord": ("views.accueil", "afficher_accueil"),
        "Année Scolaire": ("views.annee_scolaire", "afficher_annee_scolaire"),
        "Matières & Coeffs": ("views.matieres", "afficher_matieres"),
        "Classes & Tarifs": ("views.classes", "afficher_classes"),
        "Inscription Élèves": ("views.eleves", "afficher_eleves"),
        "Cartes Scolaires": ("views.cartes_scolaires", "afficher_cartes_scolaires"),
        "Emploi du temps": ("views.emploi_du_temps", "afficher_emploi_temps"),
        "Planification des évaluations": (
            "views.planification",
            "afficher_planification_evaluations",
        ),
        "Cahier de Texte": ("views.cahier_texte", "afficher_cahier_texte"),
        "Supervision cahier": (
            "views.supervision_cahier",
            "afficher_supervision_cahier",
        ),
        "Présence": ("views.presence", "afficher_presence"),
        "Saisie des notes": ("views.notes", "afficher_notes"),
        "Consultations des notes": (
            "views.consultation_notes",
            "afficher_consultation_notes",
        ),
        "Espace Inspection": (
            "views.espace_inspection",
            "afficher_espace_inspection",
        ),
        "Conseil de classe": ("views.conseil_classe", "afficher_conseil_classe"),
        "Bulletins": ("views.bulletins", "afficher_bulletins"),
        "Alerte Performance": (
            "views.alerte_performance",
            "afficher_alerte_performance",
        ),
        "Espace Enseignants": (
            "views.espace_enseignants",
            "afficher_espace_enseignants",
        ),
        "Suivi des Programmes": (
            "views.supervision_progression",
            "afficher_supervision_progression",
        ),
        "Enseignants": ("views.enseignants", "afficher_enseignants"),
        "Personnels et rôles": ("views.personnels_roles", "afficher_personnels"),
        "Gestion Comptes": (
            "views.gestion_utilisateurs",
            "afficher_gestion_utilisateurs",
        ),
        "Import Programmes PDF": (
            "views.upload_programmes",
            "afficher_upload_programmes",
        ),
        "Encaissement": ("views.scolarite", "afficher_encaissement"),
        "Stats Encaissements": (
            "views.stats_encaissements",
            "afficher_stats_encaissements",
        ),
        "Tableau Finances": (
            "views.tableau_finances",
            "afficher_tableau_finances",
        ),
        "Soldes & Impayés": ("views.soldes_impayes", "afficher_soldes_impayes"),
        "Dépenses": ("views.depenses", "afficher_depenses"),
        "Rapports": ("views.rapports", "afficher_rapports"),
        "Paramètres": ("views.parametres", "afficher_parametres"),
        "Journal d'activité": (
            "views.journal_activite",
            "afficher_journal_activite",
        ),
        "Messages": ("views.messages", "afficher_messages"),
        "Espace Parent": ("views.parent_space", "afficher_espace_parent"),
        "Backup": ("views.backup", "backup"),
    }

    # --- 5. SÉCURITÉ DES RÔLES (RBAC STRICT) ---
    if menu_option not in options_menu:
        st.warning("⛔ Accès non autorisé à cette section.")
        st.stop()

    # --- 6. EXÉCUTION DE LA VUE DYNAMIQUE ---
    if menu_option in ROUTES:
        module_path, nom_fonction = ROUTES[menu_option]
        try:
            module = importlib.import_module(module_path)
            fonction = getattr(module, nom_fonction)
            sig = inspect.signature(fonction)

            if (
                "niveau_actif" in sig.parameters
                and role_utilisateur not in ["inspecteur", "enseignant", "parent"]
                and not is_super_admin
            ):
                fonction(niveau_actif=niveau_actif)
            else:
                fonction()
        except (ImportError, AttributeError) as e:
            st.error(
                f"⚠️ Le module pour la vue **{menu_option}** est en cours de"
                f" développement ou n'a pas été trouvé. ({e})"
            )


if __name__ == "__main__":
    main()