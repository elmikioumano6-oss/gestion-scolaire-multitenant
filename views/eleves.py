from datetime import datetime
import urllib.parse
import string
import random
import streamlit as st
from werkzeug.security import generate_password_hash
from database.audit import log_action_erp
from database.db_config import SessionLocal
from database.models import Classe, Eleve, Paiement, User


def generer_lien_whatsapp(telephone, nom_parent, nom_eleve, username, password_clair):
    """Prépare le lien WhatsApp avec le texte pré-formaté pour l'envoi des identifiants."""
    telephone_propre = str(telephone).replace(" ", "").replace("+", "")
    message = (
        f"Bonjour {nom_parent}, 👋\n\n"
        f"Nous vous confirmons l'inscription de *{nom_eleve}* au sein de notre établissement.\n\n"
        f"Afin de suivre sa scolarité en temps réel (notes, versements, reliquat), voici vos identifiants sécurisés pour accéder à l'Espace Famille :\n\n"
        f"🌐 *Lien* : https://app.gestionscolairepro.com\n"
        f"👤 *Utilisateur* : {username}\n"
        f"🔑 *Mot de passe* : {password_clair}\n\n"
        f"Veuillez modifier ce mot de passe lors de votre première connexion.\n\n"
        f"Cordialement,\n*La Direction*"
    )
    texte_encode = urllib.parse.quote(message)
    return f"https://wa.me/{telephone_propre}?text={texte_encode}"


def afficher_eleves(niveau_actif="Collège"):
    st.subheader("🎓 Inscription et Gestion des Élèves")
    st.markdown(
        "Enregistrement des effectifs avec création automatique des comptes parents, "
        "génération de liens WhatsApp et encaissement initial de la 1ère tranche."
    )
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    username = st.session_state.get("username", "")

    # 🔒 Confinement strict de l'admin Rahmat
    if username and "rahmat" in username.lower():
        is_super_admin = False

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        tab_liste, tab_ajout = st.tabs(
            ["📋 Liste des Élèves", "➕ Inscrire un Élève"]
        )

        # --- REQUÊTE COMMUNE AVEC ISOLATION MULTI-TENANT ---
        query = (
            db.query(Eleve)
            .join(Classe)
            .filter(Classe.cycle == niveau_actif, Eleve.deleted_at.is_(None))
        )

        if not is_super_admin and school_id:
            query = query.filter(Eleve.school_id == school_id)

        eleves = query.order_by(Eleve.nom).all()

        with tab_liste:
            st.markdown(f"### Effectifs Enregistrés — Établissement ({niveau_actif})")

            if eleves:
                total_eleves = len(eleves)
                garcons = sum(1 for e in eleves if getattr(e, "sexe", "").lower() in ["masculin", "m", "garçon"])
                filles = sum(1 for e in eleves if getattr(e, "sexe", "").lower() in ["féminin", "f", "fille"])

                kpi1, kpi2, kpi3 = st.columns(3)
                with kpi1:
                    st.metric("Total Élèves Inscrits", total_eleves)
                with kpi2:
                    st.metric("Garçons", garcons)
                with kpi3:
                    st.metric("Filles", filles)

                st.markdown("---")

            if not eleves:
                st.info(f"Aucun élève inscrit pour le cycle **{niveau_actif}**.")
            else:
                cols = st.columns([1.3, 1.8, 1.8, 1.1, 1.8, 1.6, 1.4, 2])
                cols[0].markdown("**Matricule**")
                cols[1].markdown("**Nom**")
                cols[2].markdown("**Prénom**")
                cols[3].markdown("**Sexe**")
                cols[4].markdown("**Classe**")
                cols[5].markdown("**Tél Parent**")
                cols[6].markdown("**Réduction**")
                cols[7].markdown("**Actions**")
                st.markdown("---")

                for e in eleves:
                    montant_red = getattr(e, "montant_reduction", 0.0) or 0.0
                    red_str = f"{montant_red:,.0f}".replace(",", " ") if montant_red > 0 else "0"

                    c = st.columns([1.3, 1.8, 1.8, 1.1, 1.8, 1.6, 1.4, 2])
                    c[0].write(e.matricule or "N/D")
                    c[1].write(e.nom)
                    c[2].write(e.prenom)
                    c[3].write(e.sexe or "N/D")
                    c[4].write(e.classe.libelle if e.classe else "N/D")
                    c[5].write(e.tuteur or "Non renseigné")
                    c[6].write(f"{red_str} FCFA")

                    btn_col1, btn_col2 = c[7].columns(2)
                    with btn_col1:
                        if st.button("✏️", key=f"edit_eleve_{e.id}", help="Modifier cet élève"):
                            st.session_state[f"editing_eleve_{e.id}"] = True
                    with btn_col2:
                        if st.button("🗑️", key=f"del_eleve_{e.id}", help="Archiver (Soft Delete) cet élève"):
                            st.session_state[f"deleting_eleve_{e.id}"] = True

                    # Gestion du Soft Delete
                    if st.session_state.get(f"deleting_eleve_{e.id}", False):
                        st.warning(f"Voulez-vous vraiment archiver l'élève **{e.nom} {e.prenom}** ?")
                        c_del1, c_del2 = st.columns(2)
                        with c_del1:
                            if st.button("Confirmer l'archivage", key=f"conf_del_el_{e.id}", type="primary"):
                                e.deleted_at = datetime.now()
                                db.commit()

                                log_action_erp(
                                    module="Inscription Élèves",
                                    action=f"Archivage (Soft Delete) de l'élève {e.nom} {e.prenom} (Mat: {e.matricule})",
                                    statut="Critique",
                                    valeur_avant="Actif",
                                    valeur_apres="Archivé / Supprimé logiquement",
                                )
                                st.success("Élève archivé avec succès !")
                                st.session_state[f"deleting_eleve_{e.id}"] = False
                                st.rerun()
                        with c_del2:
                            if st.button("Annuler", key=f"canc_del_el_{e.id}"):
                                st.session_state[f"deleting_eleve_{e.id}"] = False
                                st.rerun()

                    # Gestion de la modification
                    if st.session_state.get(f"editing_eleve_{e.id}", False):
                        with st.form(key=f"form_edit_eleve_{e.id}"):
                            st.markdown(f"**Modifier l'élève : {e.nom} {e.prenom}**")

                            classes_dispo = (
                                db.query(Classe)
                                .filter(
                                    Classe.school_id == school_id,
                                    Classe.cycle == niveau_actif,
                                    Classe.deleted_at.is_(None),
                                )
                                .all()
                            )
                            options_classes = {cl.libelle: cl.id for cl in classes_dispo}
                            current_classe_name = (
                                e.classe.libelle if e.classe and e.classe.libelle in options_classes
                                else list(options_classes.keys())[0] if options_classes else ""
                            )

                            new_matricule = st.text_input("Matricule", value=e.matricule or "")
                            new_nom = st.text_input("Nom", value=e.nom or "")
                            new_prenom = st.text_input("Prénom", value=e.prenom or "")
                            new_tuteur = st.text_input("Téléphone Parent / Tuteur (WhatsApp)", value=e.tuteur or "")

                            sexes = ["Masculin", "Féminin"]
                            idx_sexe = sexes.index(e.sexe) if e.sexe in sexes else 0
                            new_sexe = st.selectbox("Sexe", sexes, index=idx_sexe)

                            class_names = list(options_classes.keys())
                            idx_cls = class_names.index(current_classe_name) if current_classe_name in class_names else 0
                            new_classe_nom = st.selectbox("Classe", class_names, index=idx_cls)

                            types_red = ["Aucune", "Bourse scolaire", "Cas social", "Enfant d'enseignant", "Autre"]
                            idx_red = types_red.index(e.type_reduction) if e.type_reduction in types_red else 0
                            new_type_red = st.selectbox("Type de réduction", types_red, index=idx_red)

                            new_montant_red = st.number_input(
                                "Montant de la réduction (FCFA)", value=float(e.montant_reduction or 0.0), step=5000.0
                            )

                            sub_edit = st.form_submit_button("Enregistrer les modifications", type="primary")
                            canc_edit = st.form_submit_button("Annuler")

                            if sub_edit:
                                if not new_nom or not new_prenom or not new_matricule:
                                    st.error("Le nom, le prénom et le matricule sont obligatoires.")
                                else:
                                    ancienne_valeurs = f"Nom: {e.nom}, Prénom: {e.prenom}, Mat: {e.matricule}"

                                    e.matricule = new_matricule.strip()
                                    e.nom = new_nom.upper().strip()
                                    e.prenom = new_prenom.strip()
                                    e.tuteur = new_tuteur.strip() if new_tuteur else None
                                    e.sexe = new_sexe
                                    e.classe_id = options_classes[new_classe_nom]
                                    e.type_reduction = new_type_red
                                    e.montant_reduction = new_montant_red
                                    db.commit()

                                    nouvelles_valeurs = f"Nom: {e.nom}, Prénom: {e.prenom}, Mat: {e.matricule}"
                                    log_action_erp(
                                        module="Inscription Élèves",
                                        action=f"Modification des informations de l'élève ID {e.id}",
                                        statut="Critique",
                                        valeur_avant=ancienne_valeurs,
                                        valeur_apres=nouvelles_valeurs,
                                    )

                                    st.success("Informations de l'élève modifiées et tracées avec succès !")
                                    st.session_state[f"editing_eleve_{e.id}"] = False
                                    st.rerun()
                            if canc_edit:
                                st.session_state[f"editing_eleve_{e.id}"] = False
                                st.rerun()
                    st.markdown("<hr style='margin: 0.2rem 0; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)

        # ==========================================
        # ONGLET 2 : INSCRIPTION, ACOMPTE & WHATSAPP
        # ==========================================
        with tab_ajout:
            st.markdown("### Formulaire d'Inscription")

            classes_dispo = (
                db.query(Classe)
                .filter(
                    Classe.school_id == school_id,
                    Classe.cycle == niveau_actif,
                    Classe.deleted_at.is_(None),
                )
                .all()
            )

            if not classes_dispo:
                st.warning(f"⚠️ Veuillez d'abord créer des classes pour le cycle **{niveau_actif}**.")
                return

            dict_classes = {c.libelle: c for c in classes_dispo}
            options_classes = list(dict_classes.keys())

            with st.form("form_inscription_eleve"):
                st.markdown("#### 1. Informations de l'élève")
                col1, col2 = st.columns(2)
                with col1:
                    nom_e = st.text_input("Nom de l'élève *")
                    prenom_e = st.text_input("Prénom de l'élève *")
                    classe_choisie_nom = st.selectbox("Sélectionner la classe *", options_classes)
                with col2:
                    sexe_e = st.selectbox("Sexe", ["Masculin", "Féminin"])
                    matricule_e = st.text_input("Matricule de l'élève *")
                    tuteur_e = st.text_input("Téléphone Parent (Format avec indicatif, ex: 22790000000) *")

                # --- RAPPEL VISUEL DE LA GRILLE TARIFAIRE ---
                classe_obj_selectionnee = dict_classes.get(classe_choisie_nom)
                if classe_obj_selectionnee:
                    scol_ref = f"{classe_obj_selectionnee.frais_scolarite:,.0f}".replace(",", " ")
                    insc_ref = f"{classe_obj_selectionnee.frais_inscription:,.0f}".replace(",", " ")
                    coges_ref = f"{getattr(classe_obj_selectionnee, 'frais_coges', 0.0):,.0f}".replace(",", " ")
                    trans_ref = f"{classe_obj_selectionnee.frais_transport:,.0f}".replace(",", " ")
                    cant_ref = f"{classe_obj_selectionnee.frais_cantine:,.0f}".replace(",", " ")

                    st.info(
                        f"📌 **Grille tarifaire officielle ({classe_choisie_nom})** :\n"
                        f"- Scolarité : **{scol_ref} F** | Inscription : **{insc_ref} F** | COGES : **{coges_ref} F**\n"
                        f"- Transport : **{trans_ref} F** | Cantine : **{cant_ref} F**"
                    )

                st.markdown("#### 2. Encaissement Initial (Acompte / 1ère tranche)")
                st.caption("ℹ️ *Saisissez uniquement le montant payé AUJOURD'HUI. Le reliquat sera calculé automatiquement et pourra être payé plus tard dans le module **Encaissements**.*")
                
                col_v1, col_v2, col_v3 = st.columns(3)
                with col_v1:
                    versement_inscription = st.number_input(
                        "Frais d'Inscription (Fixe)", min_value=0.0,
                        value=float(classe_obj_selectionnee.frais_inscription or 0.0) if classe_obj_selectionnee else 0.0, step=1000.0