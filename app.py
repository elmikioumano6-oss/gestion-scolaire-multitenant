from contextlib import contextmanager
from datetime import datetime, timezone
import importlib
import inspect
import json
import logging
import os
import re
import time

from dotenv import load_dotenv
import streamlit as st
from streamlit_option_menu import option_menu

# --- 1. CONFIGURATION LOGGING PROFESSIONNEL ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv(override=True)

from database.db_config import SessionLocal, init_db
from database.models import AnneeScolaire, School, User


@contextmanager
def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@st.cache_data(ttl=600)
def get_libelle_annee_courante():
    with get_db_session() as db_sidebar:
        try:
            annee_courante = (
                db_sidebar.query(AnneeScolaire)
                .filter(AnneeScolaire.active == True)
                .first()
            )
            return annee_courante.libelle if annee_courante else "2026-2027"
        except Exception as e:
            logger.error(f"Erreur DB (Année courante) : {e}")
            return "2026-2027"


def init_tenant_context():
    if st.session_state.get("authenticated") and st.session_state.get(
        "school_id"
    ):
        return

    if (
        "school_id" in st.session_state
        and st.session_state["school_id"]
        and not st.session_state.get("is_super_admin")
    ):
        return

    with get_db_session() as db:
        subdomain = "default"
        try:
            host = (
                st.context.headers.get("Host", "")
                or st.context.headers.get("X-Forwarded-Host", "")
            )
            if host:
                host_clean = host.split(":")[0].lower()
                if (
                    "localhost" not in host_clean
                    and "127.0.0.1" not in host_clean
                ):
                    parts = host_clean.split(".")
                    if len(parts) > 2 and parts[0] not in [
                        "www",
                        "app",
                        "gestion",
                    ]:
                        subdomain = parts[0]
        except Exception:
            pass

        school = None
        try:
            if subdomain != "default":
                school = (
                    db.query(School)
                    .filter(School.subdomain == subdomain)
                    .first()
                )
        except Exception:
            school = None

        if school:
            st.session_state["school_id"] = school.id
            st.session_state["school_name"] = school.nom
            st.session_state["school_code"] = school.code
        else:
            if "school_id" not in st.session_state:
                st.session_state["school_id"] = None
                st.session_state["school_name"] = "Gestion Scolaire Pro"


def main():
    start_total = time.time()

    st.set_page_config(
        page_title="Gestion Scolaire Pro - SaaS",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # --- DÉTECTION AUTOMATIQUE ET DYNAMIQUE DU LOGO DE L'ÉCOLE POUR LA PWA MOBILE ---
    school_code = str(st.session_state.get("school_code", "")).strip().upper()
    school_name = str(st.session_state.get("school_name", "")).strip().lower()
    school_name_actuel = st.session_state.get("school_name", "ERP Scolaire")

    logo_filename = None
    try:
        fichiers_racine = os.listdir(".")
        mots_cles = [school_code, school_name]
        mots_cles_propres = [re.sub(r"[^a-z0-9]", "", m.lower()) for m in mots_cles if m]

        for fichier in fichiers_racine:
            if fichier.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                nom_fichier_clean = re.sub(r"[^a-z0-9]", "", fichier.lower())
                if any(mot in nom_fichier_clean for mot in mots_cles_propres if len(mot) > 2):
                    logo_filename = fichier
                    break
    except Exception:
        pass

    if not logo_filename or not os.path.exists(logo_filename):
        logo_filename = "Logo CSP-RAHMAT-FH.png" if os.path.exists("Logo CSP-RAHMAT-FH.png") else "Logo Gestion Scolaire Pro.png"

    # Création dynamique du manifeste JSON pour l'installation sur l'écran d'accueil du mobile
    manifest_data = {
        "name": school_name_actuel,
        "short_name": "ERP Scolaire",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0b131d",
        "theme_color": "#111827",
        "icons": [
            {
                "src": f"/{logo_filename}" if os.path.exists(logo_filename) else "/favicon.png",
                "sizes": "192x192 512x512",
                "type": "image/png"
            }
        ]
    }
    
    try:
        with open("manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest_data, f)
    except Exception:
        pass

    st.markdown(
        f"""
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="apple-mobile-web-app-title" content="{school_name_actuel}">
        <link rel="apple-touch-icon" href="{logo_filename}">
        <link rel="manifest" href="/manifest.json">
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="theme-color" content="#111827">
    """,
        unsafe_allow_html=True,
    )

    # --- STYLE CSS AVANCÉ POUR UNE BARRE DE DÉFILEMENT ULTRA-VISIBLE ET LARGE ---
    st.markdown(
        """
        <style>
            /* Forcer le conteneur de la sidebar à afficher une barre de défilement large et contrastée */
            section[data-testid="stSidebar"] {
                overflow: hidden !important;
            }
            section[data-testid="stSidebar"] > div:first-child {
                overflow-y: scroll !important;
                height: 100vh !important;
                padding-right: 5px !important;
            }
            
            /* Largeur de la piste de défilement */
            section[data-testid="stSidebar"] ::-webkit-scrollbar {
                width: 16px !important;
                display: block !important;
                visibility: visible !important;
            }
            
            /* Fond de la piste de défilement */
            section[data-testid="stSidebar"] ::-webkit-scrollbar-track {
                background: #0b131d !important;
                border-radius: 8px !important;
                border: 1px solid rgba(212, 175, 55, 0.3) !important;
            }
            
            /* Le curseur (pouce) de défilement bien visible en couleur Or/Doré */
            section[data-testid="stSidebar"] ::-webkit-scrollbar-thumb {
                background: #D4AF37 !important;
                border-radius: 8px !important;
                border: 3px solid #0b131d !important;
                min-height: 40px !important;
            }
            
            /* Changement de couleur au survol du curseur */
            section[data-testid="stSidebar"] ::-webkit-scrollbar-thumb:hover {
                background: #ff8800 !important;
            }

            /* Personnalisation globale des barres de défilement de la page principale */
            ::-webkit-scrollbar {
                width: 12px;
                height: 12px;
            }
            ::-webkit-scrollbar-track {
                background: #0e1117;
                border-radius: 6px;
            }
            ::-webkit-scrollbar-thumb {
                background: #3b82f6;
                border-radius: 6px;
                border: 2px solid #0e1117;
            }
            ::-webkit-scrollbar-thumb:hover {
                background: #60a5fa;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if not st.session_state.get("db_initialized", False):
        t0 = time.time()
        try:
            init_db()
            logger.info(f"DB Initialisée en {time.time() - t0:.2f} s")
        except Exception as e:
            logger.error(f"Erreur critique lors de l'initialisation de la DB : {e}")
        st.session_state["db_initialized"] = True

    t0 = time.time()
    init_tenant_context()
    logger.info(f"Contexte Tenant initialisé en {time.time() - t0:.2f} s")

    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("role", "login")
    st.session_state.setdefault("username", "")
    st.session_state.setdefault("school_id", None)
    st.session_state.setdefault("school_name", "")
    st.session_state.setdefault("is_super_admin", False)

    if not st.session_state.get("authenticated") or not st.session_state.get(
        "username"
    ):
        st.query_params.clear()
        st.markdown(
            '<style>[data-testid="stSidebar"] { display: none !important; }</style>',
            unsafe_allow_html=True,
        )
        try:
            module = importlib.import_module("views.login")
            getattr(module, "afficher_login")()
        except Exception as e:
            logger.error(f"Erreur Login: {e}")
            st.error("Erreur de chargement. Veuillez rafraîchir la page.")
        return

    nom_utilisateur = st.session_state.get("username")
    role_utilisateur = str(st.session_state.get("role", "")).lower()
    is_super_admin = st.session_state.get("is_super_admin", False)

    if nom_utilisateur and "rahmat" in nom_utilisateur.lower():
        is_super_admin = False
        st.session_state["is_super_admin"] = False

    # --- SÉCURISATION TRANSACTIONNELLE DE LA BASE DE DONNÉES ---
    db_sec = SessionLocal()
    try:
        current_user = None
        try:
            current_user = (
                db_sec.query(User)
                .filter(User.username == nom_utilisateur)
                .first()
                if nom_utilisateur
                else None
            )
        except Exception as db_query_error:
            logger.error(f"Erreur de requête utilisateur en DB : {db_query_error}")

        if not current_user:
            st.warning("Session expirée ou utilisateur introuvable.")
            st.session_state.clear()
            st.rerun()

        if current_user.school_id and not st.session_state.get("school_id"):
            st.session_state["school_id"] = current_user.school_id
            school_obj = (
                db_sec.query(School)
                .filter(School.id == current_user.school_id)
                .first()
            )
            if school_obj:
                st.session_state["school_name"] = school_obj.nom
                st.session_state["school_code"] = school_obj.code

        if current_user.school_id and not is_super_admin:
            ecole_verif = (
                db_sec.query(School)
                .filter(School.id == current_user.school_id)
                .first()
            )
            if ecole_verif and not getattr(ecole_verif, "actif", True):
                st.session_state.clear()
                st.error(
                    f"L'établissement '{ecole_verif.nom}' a été suspendu."
                )
                st.stop()

        if not is_super_admin and getattr(
            current_user, "changer_mdp_requis", False
        ):
            st.markdown(
                '<style>[data-testid="stSidebar"] { display: none !important; }</style>',
                unsafe_allow_html=True,
            )
            st.markdown(
                "<br><h2 style='text-align: center; color: #C5A059;'>Sécurité"
                " Obligatoire</h2>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<p style='text-align: center;'>Veuillez définir votre nouveau"
                " mot de passe personnel.</p>",
                unsafe_allow_html=True,
            )

            col_c1, col_c2, col_c3 = st.columns([1, 2, 1])
            with col_c2:
                with st.form("form_securite_mdp_force"):
                    nouveau_p = st.text_input(
                        "Nouveau mot de passe", type="password"
                    )
                    confirme_p = st.text_input(
                        "Confirmer le nouveau mot de passe", type="password"
                    )
                    submit_btn = st.form_submit_button(
                        "Enregistrer", use_container_width=True, type="primary"
                    )

                    if submit_btn:
                        if not re.match(
                            r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d@$!%*?&]{8,}$",
                            nouveau_p,
                        ):
                            st.error(
                                "Le mot de passe doit contenir au moins 8"
                                " caractères, une majuscule et un chiffre."
                            )
                        elif nouveau_p != confirme_p:
                            st.error("Les mots de passe ne correspondent pas.")
                        else:
                            try:
                                salt = bcrypt.gensalt()
                                hashed = bcrypt.hashpw(
                                    nouveau_p.encode("utf-8"), salt
                                )
                                current_user.password = hashed.decode("utf-8")
                                current_user.changer_mdp_requis = False
                                db_sec.commit()
                                st.success("Succès ! Chargement...")
                                st.rerun()
                            except Exception as ex:
                                db_sec.rollback()
                                st.error(f"Erreur : {ex}")
            return

        current_user.derniere_activite = datetime.now(timezone.utc)
        db_sec.commit()

    except Exception as e:
        db_sec.rollback()
        logger.error(f"Erreur critique dans le gardien de sécurité : {e}")
        st.error(
            "Une erreur critique est survenue lors de la vérification de la"
            " session. Veuillez rafraîchir."
        )
        return
    finally:
        db_sec.close()

    with st.sidebar:
        try:
            school_id = st.session_state.get("school_id")
            school_code = (
                str(st.session_state.get("school_code", "")).strip().upper()
            )
            school_name = (
                str(st.session_state.get("school_name", "")).strip().lower()
            )

            logo_file = None
            fichiers_racine = os.listdir(".")

            mots_cles = [school_code, school_name]
            mots_cles_propres = [
                re.sub(r"[^a-z0-9]", "", m.lower()) for m in mots_cles if m
            ]

            for fichier in fichiers_racine:
                if fichier.lower().endswith(
                    (".png", ".jpg", ".jpeg", ".webp")
                ):
                    nom_fichier_clean = re.sub(
                        r"[^a-z0-9]", "", fichier.lower()
                    )
                    if any(
                        mot in nom_fichier_clean
                        for mot in mots_cles_propres
                        if len(mot) > 2
                    ):
                        logo_file = fichier
                        break

            if not logo_file and school_id:
                candidate = f"logo_{school_id}.png"
                if os.path.exists(candidate):
                    logo_file = candidate

            if not logo_file and os.path.exists(
                "Logo Gestion Scolaire Pro.png"
            ):
                logo_file = "Logo Gestion Scolaire Pro.png"

            col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
            with col_logo2:
                if logo_file and os.path.exists(logo_file):
                    st.image(logo_file, width=100)
                else:
                    st.markdown(
                        "<div style='text-align: center;'><h3>🏫</h3></div>",
                        unsafe_allow_html=True,
                    )
        except Exception:
            pass

        nom_affiche_ecole = st.session_state.get(
            "school_name", "Gestion Scolaire Pro"
        )
        st.markdown(
            """
                <div style="text-align: left; margin-top: -5px;">
                    <h3 style="color: #C5A059; font-size: 1.1rem; font-weight: 700; margin-bottom: 0px;">{}</h3>
                    <p style='color: #D4AF37; font-size: 0.8rem; font-style: italic; margin-top: 2px;'>Gestion Scolaire Pro</p>
                </div>
            """.format(
                nom_affiche_ecole
            ),
            unsafe_allow_html=True,
        )

        st.markdown(
            "<hr style='margin: 0.5rem 0 0.8rem 0; border-color: rgba(197,"
            " 160, 89, 0.3);'>",
            unsafe_allow_html=True,
        )

        cycles_disponibles = ["Maternelle", "Primaire", "Collège", "Lycée"]
        cycle_courant_session = st.session_state.get("cycle_actif", "Collège")
        index_actuel = (
            cycles_disponibles.index(cycle_courant_session)
            if cycle_courant_session in cycles_disponibles
            else 2
        )

        if is_super_admin:
            st.markdown("#### 🏛️ Gouvernance ERP")
            st.info(f"Connecté : **{nom_utilisateur}**")
            options_menu = [
                "📊 Pilotage & BI",
                "🏢 Gestion des Tenants",
                "👥 IAM & Sécurité",
                "📜 Piste d'Audit",
                "💾 Infrastructure & Backup",
                "🩺 Santé & Diagnostic",
                "⚙️ Paramètres Système",
            ]
            icons_menu = [
                "speedometer2",
                "globe",
                "shield-lock",
                "clock-history",
                "database",
                "heart-pulse",
                "gear",
            ]
            menu_key_val = "menu_super_admin_erp"

        elif role_utilisateur == "inspecteur":
            st.markdown("#### 🔍 Portail Inspecteur")
            st.info(f"Connecté : **{nom_utilisateur}**")
            options_menu = [
                "Espace Inspection",
                "Suivi des Programmes",
                "Supervision cahier",
            ]
            icons_menu = ["clipboard-check", "graph-up", "eye"]
            menu_key_val = "menu_inspecteur"

        elif role_utilisateur == "censeur":
            st.markdown("#### 📐 Portail Censeur")
            st.info(f"Connecté : **{nom_utilisateur}**")
            niveau_actif = st.selectbox(
                "Cycle actif",
                cycles_disponibles,
                index=index_actuel,
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
                "Communication Groupée",
                "Notifications",
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
                "megaphone",
                "bell",
            ]
            menu_key_val = "menu_censeur"

        elif role_utilisateur == "enseignant":
            st.markdown("#### 👨‍🏫 Portail Enseignant")
            st.info(f"Connecté : **{nom_utilisateur}**")
            options_menu = ["Espace Enseignants"]
            icons_menu = ["person-video3"]
            menu_key_val = "menu_enseignant"

        elif role_utilisateur == "parent":
            st.markdown("#### 👨‍👩‍👧 Portail Famille")
            st.info(f"Connecté : **{nom_utilisateur}**")
            options_menu = ["Espace Parent", "Messages"]
            icons_menu = ["house-heart", "chat-dots"]
            menu_key_val = "menu_parent"

        else:
            st.markdown("#### 🏫 Pilotage Administratif")
            niveau_actif = st.selectbox(
                "Cycle actif",
                cycles_disponibles,
                index=index_actuel,
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
                "Clôture d'Année",
                "Matières & Coeffs",
                "Classes & Tarifs",
                "Inscription Élèves",
                "Import Massif Élèves",
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
                "Fiches de Paie",
                "Rapports",
                "Paramètres",
                "Journal d'activité",
                "Messages",
                "Communication Groupée",
                "Notifications",
                "Espace Parent",
                "Backup",
                "🩺 Santé & Diagnostic",
            ]
            icons_menu = [
                "house",
                "speedometer2",
                "calendar",
                "calendar-x",
                "book",
                "grid",
                "person-plus",
                "file-excel",
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
                "file-earmark-text",
                "file-earmark-bar-graph",
                "file-earmark-bar-graph",
                "gear",
                "clock-history",
                "chat-dots",
                "megaphone",
                "bell",
                "house-heart",
                "database",
                "heart-pulse",
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

        st.query_params["user"] = nom_utilisateur
        st.query_params["role"] = role_utilisateur
        st.query_params["page"] = menu_option

        st.markdown("---")
        libelle_annee = get_libelle_annee_courante()
        st.markdown(
            f"<div style='text-align: center; color: #C5A059; font-size:"
            f" 0.75rem;'>Année Scolaire : <b>{libelle_annee}</b><br>Niamey,"
            " Niger</div>",
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

    ROUTES = {
        "📊 Pilotage & BI": ("views.accueil", "afficher_accueil"),
        "🏢 Gestion des Tenants": ("views.super_admin", "afficher_super_admin"),
        "👥 IAM & Sécurité": (
            "views.gestion_utilisateurs",
            "afficher_gestion_utilisateurs",
        ),
        "📜 Piste d'Audit": ("views.journal_activite", "afficher_journal_activite"),
        "💾 Infrastructure & Backup": ("views.backup", "backup"),
        "🩺 Santé & Diagnostic": ("views.health_check", "health_check"),
        "⚙️ Paramètres Système": ("views.parametres", "afficher_parametres"),
        "Administration Globale": ("views.super_admin", "afficher_super_admin"),
        "Accueil": ("views.accueil", "afficher_accueil"),
        "Tableau de Bord": ("views.tableau_de_bord", "afficher_tableau_de_bord"),
        "Année Scolaire": ("views.annee_scolaire", "afficher_annee_scolaire"),
        "Clôture d'Année": ("views.cloture_annee", "afficher_cloture_annee"),
        "Matières & Coeffs": ("views.matieres", "afficher_matieres"),
        "Classes & Tarifs": ("views.classes", "afficher_classes"),
        "Inscription Élèves": ("views.eleves", "afficher_eleves"),
        "Import Massif Élèves": ("views.import_masse", "afficher_import_masse"),
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
        "Tableau Finances": ("views.tableau_finances", "afficher_tableau_finances"),
        "Soldes & Impayés": ("views.soldes_impayes", "afficher_soldes_impayes"),
        "Dépenses": ("views.depenses", "afficher_depenses"),
        "Fiches de Paie": ("views.paie", "afficher_paie"),
        "Rapports": ("views.rapports", "afficher_rapports"),
        "Paramètres": ("views.parametres", "afficher_parametres"),
        "Journal d'activité": (
            "views.journal_activite",
            "afficher_journal_activite",
        ),
        "Messages": ("views.messages", "afficher_messages"),
        "Communication Groupée": ("views.communication", "afficher_communication"),
        "Notifications": (
            "views.centre_notifications",
            "afficher_centre_notifications",
        ),
        "Espace Parent": ("views.parent_space", "afficher_espace_parent"),
        "Backup": ("views.backup", "backup"),
    }

    if menu_option not in options_menu:
        st.warning("⛔ Accès non autorisé à cette section.")
        st.stop()

    t0 = time.time()
    if menu_option in ROUTES:
        module_path, nom_fonction = ROUTES[menu_option]
        try:
            module = importlib.import_module(module_path)
            fonction = getattr(module, nom_fonction)
            sig = inspect.signature(fonction)

            if (
                "niveau_actif" in sig.parameters
                and role_utilisateur
                not in ["inspecteur", "enseignant", "parent"]
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
            logger.error(f"Erreur de routage pour {menu_option}: {e}")

    logger.info(
        f"Page '{menu_option}' chargée en {time.time() - t0:.2f} s. (Temps"
        f" total: {time.time() - start_total:.2f} s)"
    )


if __name__ == "__main__":
    main()