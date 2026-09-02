import importlib
import inspect
from datetime import datetime
import os
from database.db_config import SessionLocal
from database.models import AnneeScolaire, User, School
import streamlit as st
from streamlit_option_menu import option_menu


def main():
    st.set_page_config(
        page_title="Gestion Scolaire Pro - Plateforme Multi-Tenant",
        page_icon="🏫",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    query_params = st.query_params

    # --- 1. RESTAURATION SÉCURISÉE & VÉRIFICATION STRICTE DE L'ÉCOLE ---
    url_user = query_params.get("user", "")
    url_role = query_params.get("role", "")

    # Si une session est active OU qu'on essaie de se restaurer via l'URL
    target_user = st.session_state.get("username") or url_user

    if target_user:
        db_sec = SessionLocal()
        try:
            user_verif = db_sec.query(User).filter(User.username == target_user).first()
            if user_verif:
                role_db = str(user_verif.role or "").strip().lower()
                is_super = (role_db == "super_admin")

                # VÉRIFICATION DE L'ÉCOLE ASSOCIÉE (Si l'utilisateur appartient à une école et n'est pas super admin)
                if user_verif.school_id and not is_super:
                    ecole_verif = db_sec.query(School).filter(School.id == user_verif.school_id).first()
                    if ecole_verif:
                        is_active = getattr(ecole_verif, 'actif', True)
                        date_exp = getattr(ecole_verif, 'date_expiration', None)
                        now = datetime.utcnow()
                        
                        # Si l'école est suspendue ou expirée, on bloque tout net
                        if not is_active or (date_exp and date_exp < now):
                            st.session_state.clear()
                            st.session_state["authenticated"] = False
                            st.session_state["role"] = "login"
                            st.query_params.clear()
                            st.error(f"⛔ L'établissement '{ecole_verif.nom}' a été suspendu ou la période d'essai a expiré.")
                            st.stop()

                # Si l'école est active ou si c'est le super admin, on valide la session
                st.session_state["authenticated"] = True
                st.session_state["username"] = user_verif.username
                st.session_state["role"] = role_db
                st.session_state["school_id"] = user_verif.school_id
                st.session_state["is_super_admin"] = is_super
                
                if user_verif.school_id:
                    ecole = db_sec.query(School).filter(School.id == user_verif.school_id).first()
                    st.session_state["school_name"] = ecole.nom if ecole else "École Inconnue"
                else:
                    st.session_state["school_name"] = "Plateforme Globale"
            else:
                st.query_params.clear()
                st.session_state.clear()
                st.session_state["authenticated"] = False
                st.session_state["role"] = "login"
        except Exception:
            st.session_state.clear()
            st.session_state["authenticated"] = False
            st.session_state["role"] = "login"
        finally:
            db_sec.close()

    # Initialisation par défaut si toujours vide
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

    role_utilisateur = str(st.session_state.get("role", "login")).lower()
    nom_utilisateur = st.session_state.get("username", "Utilisateur")

    # --- MISE À JOUR DU STATUT "DERNIÈRE ACTIVITÉ" EN TEMPS RÉEL & DOUBLE CHECK SÉCURITÉ ---
    if st.session_state.get("authenticated") and nom_utilisateur:
        db_act = SessionLocal()
        try:
            usr_to_update = db_act.query(User).filter(User.username == nom_utilisateur).first()
            if usr_to_update:
                # Double vérification anti-contournement en temps réel pour les non super-admin
                if usr_to_update.school_id and not st.session_state.get("is_super_admin", False):
                    ecole_live = db_act.query(School).filter(School.id == usr_to_update.school_id).first()
                    if ecole_live and not getattr(ecole_live, 'actif', True):
                        st.session_state.clear()
                        st.session_state["authenticated"] = False
                        st.session_state["role"] = "login"
                        st.query_params.clear()
                        st.error(f"⛔ L'établissement '{ecole_live.nom}' a été suspendu.")
                        st.stop()

                usr_to_update.derniere_activite = datetime.utcnow()
                db_act.commit()
        except Exception:
            db_act.rollback()
        finally:
            db_act.close()

    # --- 2. SI NON CONNECTÉ OU SI LA PAGE DEMANDÉE EST LOGIN : AFFICHAGE DU LOGIN ---
    page_demandee_urt = query_params.get("page", "")
    if not st.session_state.get("authenticated") or not st.session_state.get("username") or role_utilisateur == "login" or page_demandee_urt == "Login":
        st.markdown(
            """
            <style>
                [data-testid="stSidebar"] {
                    display: none !important;
                }
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
        return

    # --- 3. BARRE LATÉRALE - MENU SANS LOGIN ---
    with st.sidebar:
        try:
            school_name_lower = st.session_state.get('school_name', '').lower()
            if "etoile" in school_name_lower:
                logo_file = "Logo L'ETOILE DU SUCCES.png"
            else:
                logo_file = "Logo CSP-RAHMAT-FH.png"

            col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
            with col_logo2:
                if os.path.exists(logo_file):
                    st.image(logo_file, width=100)
                else:
                    st.image("Logo CSP-RAHMAT-FH.png", width=100)
        except Exception:
            st.markdown(
                "<div style='text-align: center;'><h3>🏫</h3></div>",
                unsafe_allow_html=True,
            )

        nom_affiche_ecole = st.session_state.get('school_name', 'Plateforme Scolaire')
        st.markdown(
            f"""
            <div style="text-align: left; margin-top: -5px; margin-bottom: 0px;">
                <h3 style="color: #C5A059; font-family: 'Georgia', serif; font-size: 1.1rem; font-weight: 700; margin-bottom: 0px; letter-spacing: 0.5px;">{nom_affiche_ecole}</h3>
                <p style='color: #D4AF37; font-size: 0.8rem; font-style: italic; font-weight: 500; margin-top: 2px; margin-bottom: 0px;'>Plateforme Multi-Écoles</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            "<hr style='margin: 0.5rem 0 0.8rem 0; border-color: rgba(197, 160, 89, 0.3);'>",
            unsafe_allow_html=True,
        )

        niveau_actif = "Collège"

        if st.session_state.get("is_super_admin", False):
            st.markdown("#### 🌐 Super Administrateur")
            st.info(f"Connecté : **{nom_utilisateur}**")

            options_menu = ["Administration Globale", "Accueil", "Paramètres", "Journal d'activité", "Backup"]
            icons_menu = ["globe", "house", "gear", "clock-history", "database"]
            menu_key_val = "menu_super_admin"

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
                "Messages"
            ]
            icons_menu = [
                "house",
                "speedometer2",
                "clipboard-check",
                "graph-up",
                "eye",
                "clock-history",
                "chat-dots"
            ]
            menu_key_val = "menu_inspecteur"

        elif role_utilisateur == "censeur":
            st.markdown("#### 📐 Portail Censeur")
            st.info(f"Connecté : **{nom_utilisateur}**")

            niveau_actif = st.selectbox(
                "Cycle d'enseignement actif",
                options=["Primaire", "Collège", "Lycée"],
                index=1,
                key="global_niveau_actif_censeur",
            )
            st.session_state["cycle_actif"] = niveau_actif

            st.markdown(
                "<hr style='margin: 0.5rem 0 0.5rem 0; border-color: rgba(255,255,255,0.1);'>",
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
                "Messages"
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
                "chat-dots"
            ]
            menu_key_val = "menu_censeur"

        elif role_utilisateur == "enseignant":
            st.markdown("#### 👨‍🏫 Portail Enseignant")
            st.info(f"Connecté : **{nom_utilisateur}**")

            options_menu = [
                "Espace Enseignants",
                "Cahier de Texte",
                "Saisie des notes",
            ]
            icons_menu = [
                "person-video3",
                "journal-text",
                "pencil-square",
            ]
            menu_key_val = "menu_enseignant"

        elif role_utilisateur == "parent":
            st.markdown("#### 👨‍👩‍👧 Portail Famille")
            st.info(f"Connecté : **{nom_utilisateur}**")

            options_menu = ["Espace Parent", "Messages"]
            icons_menu = ["house-heart", "chat-dots"]
            menu_key_val = "menu_parent"

        else:
            st.markdown("#### 🏫 Pilotage par Cycle")
            niveau_actif = st.selectbox(
                "Cycle d'enseignement actif",
                options=["Primaire", "Collège", "Lycée"],
                index=1,
                key="global_niveau_actif",
            )
            st.session_state["cycle_actif"] = niveau_actif

            st.markdown(
                "<hr style='margin: 0.5rem 0 0.5rem 0; border-color: rgba(255,255,255,0.1);'>",
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

        # Récupération de la page dans l'URL pour garder le bon index au F5
        page_demandee = query_params.get("page", options_menu[0])
        default_idx = 0
        if page_demandee in options_menu:
            default_idx = options_menu.index(page_demandee)
        elif role_utilisateur in ["admin", "administrateur"]:
            default_idx = 1 if "Tableau de Bord" in options_menu else 0

        menu_option = option_menu(
            menu_title=None,
            options=options_menu,
            icons=icons_menu,
            menu_icon="cast",
            default_index=default_idx,
            key=menu_key_val,
            styles={
                "container": {
                    "padding": "0!important",
                    "background-color": "#0d1b2a",
                },
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

        # Mise à jour transparente de l'URL pour la persistance
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
            libelle_annee = (
                annee_courante.libelle if annee_courante else "2026-2027"
            )
        except Exception:
            libelle_annee = "2026-2027"
        finally:
            db_sidebar.close()

        st.markdown(
            f"<div style='text-align: center; color: #C5A059; font-size: 0.75rem;'>Année Scolaire : <b>{libelle_annee}</b><br>Niamey, Niger</div>",
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button(
            "🚪 Se déconnecter", use_container_width=True, type="secondary"
        ):
            st.session_state.clear()
            st.session_state["authenticated"] = False
            st.session_state["role"] = "login"
            st.query_params.clear()
            st.success("Déconnexion réussie !")
            st.rerun()

    # --- 4. DICTIONNAIRE DE ROUTAGE ---
    ROUTES = {
        "Administration Globale": ("views.super_admin", "afficher_super_admin"),
        "Accueil": ("views.accueil", "afficher_accueil"),
        "Tableau de Bord": (
            "views.tableau_de_bord",
            "afficher_tableau_de_bord",
        ),
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
        "Personnels et rôles": (
            "views.personnels_roles",
            "afficher_personnels",
        ),
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
        "Backup": ("views.backup", "afficher_backup"),
    }

    # --- 5. SÉCURITÉ DES RÔLES ---
    if st.session_state.get("is_super_admin", False):
        if menu_option not in ["Administration Globale", "Accueil", "Paramètres", "Journal d'activité", "Backup"]:
            st.warning("⛔ Accès restreint pour le Super Administrateur.")
            return
    elif role_utilisateur not in ["admin", "administrateur", "censeur"] and menu_option not in ["Messages"]:
        if role_utilisateur == "inspecteur" and menu_option not in ["Accueil", "Tableau de Bord", "Espace Inspection", "Suivi des Programmes", "Supervision cahier", "Journal d'activité", "Messages"]:
            st.warning("⛔ Accès non autorisé à cette section.")
            return
        elif role_utilisateur == "censeur" and menu_option not in [
            "Accueil", "Tableau de Bord", "Matières & Coeffs", "Classes & Tarifs",  
            "Emploi du temps", "Planification des évaluations", "Cahier de Texte",  
            "Supervision cahier", "Présence", "Conseil de classe", "Bulletins",  
            "Alerte Performance", "Suivi des Programmes", "Enseignants", "Paramètres", "Messages"
        ]:
            st.warning("⛔ Accès non autorisé à cette section.")
            return
        elif role_utilisateur == "enseignant" and menu_option not in ["Espace Enseignants", "Cahier de Texte", "Saisie des notes"]:
            st.warning("⛔ Accès non autorisé à cette section.")
            return
        elif role_utilisateur == "parent" and menu_option not in ["Espace Parent", "Messages"]:
            st.warning("⛔ Accès non autorisé à cette section.")
            return

    # --- 6. EXÉCUTION DE LA VUE ---
    if menu_option in ROUTES:
        module_path, nom_fonction = ROUTES[menu_option]
        try:
            module = importlib.import_module(module_path)
            fonction = getattr(module, nom_fonction)
            sig = inspect.signature(fonction)
            if "niveau_actif" in sig.parameters and role_utilisateur not in [
                "inspecteur",
                "enseignant",
                "parent",
            ] and not st.session_state.get("is_super_admin", False):
                fonction(niveau_actif=niveau_actif)
            else:
                fonction()
        except (ImportError, AttributeError) as e:
            st.error(
                f"Erreur de chargement pour la vue **{menu_option}** : {e}"
            )


if __name__ == "__main__":
    main()