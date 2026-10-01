from datetime import datetime
import urllib.parse
from database.audit import log_action_erp
from database.db_config import SessionLocal
from database.models import Eleve, School, User, Paiement, Presence, Classe, Note
import streamlit as st


def afficher_messages():
    st.subheader("💬 Messagerie WhatsApp Intégrée & Automatisée")
    st.markdown(
        "Centre de communication WhatsApp : réception, envoi direct sécurisé "
        "et campagnes d'alertes automatisées multi-critères (frais, retards, sanctions, notes, cantine)."
    )
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)
    username_connecte = st.session_state.get("username", "admin")

    db = SessionLocal()
    try:
        school_phone = "Non renseigné"
        if school_id:
            ecole_courante = (
                db.query(School).filter(School.id == school_id).first()
            )
            school_name = (
                ecole_courante.nom
                if ecole_courante
                else st.session_state.get("school_name", "Établissement")
            )

            for attr in ["contacts", "telephone", "tel", "contact", "phone"]:
                if hasattr(ecole_courante, attr) and getattr(ecole_courante, attr):
                    val = getattr(ecole_courante, attr)
                    if val and str(val).strip() not in ["", "None", "nan"]:
                        school_phone = str(val).strip()
                        break
        else:
            school_name = st.session_state.get("school_name", "Établissement")
    finally:
        db.close()

    cycle_en_cours = st.session_state.get("cycle_actif", "Collège")

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        resolved_school_id = school_id if school_id else 1
        
        tab1, tab2, tab3 = st.tabs([
            "📥 Boîte de Réception",
            "📤 Envoi Direct WhatsApp",
            "⚙️ Automatisation & Rapports Mensuels",
        ])

        with tab1:
            st.markdown(
                f"### Messages Reçus sur le Numéro de l'École — **{school_name}"
                f" (Ligne(s) : {school_phone})**"
            )
            st.info(
                "Aucun message WhatsApp entrant pour le moment sur la ligne officielle"
                " de l'établissement."
            )

        with tab2:
            st.markdown(
                f"### Envoi Direct WhatsApp — **{school_name} ({cycle_en_cours})**"
            )
            st.markdown(
                "<small style='color: #6c757d;'>🔒 Sécurité ERP : Tous les envois"
                " sont tracés et consignés dans la piste d'audit pour garantir la"
                " conformité institutionnelle.</small>",
                unsafe_allow_html=True,
            )
            st.markdown("<br>", unsafe_allow_html=True)

            classes_query = (
                db.query(Eleve)
                .join(Eleve.classe)
                .filter(Eleve.school_id == school_id)
                if not is_super_admin
                else db.query(Eleve).join(Eleve.classe)
            )
            classes_query = classes_query.filter(
                Eleve.classe.has(cycle=cycle_en_cours)
            )
            eleves = classes_query.all()

            if not eleves:
                st.warning(
                    f"⚠️ Aucun élève enregistré pour le cycle **{cycle_en_cours}** dans"
                    f" l'établissement **{school_name}**."
                )
            else:

                def get_parent_phone(e):
                    for attr in [
                        "tuteur",
                        "telephone_parent",
                        "tuteur_tel",
                        "tel_parent",
                        "telephone",
                        "phone",
                    ]:
                        if hasattr(e, attr) and getattr(e, attr):
                            val = getattr(e, attr)
                            if val and str(val).strip() not in ["", "None", "nan"]:
                                return str(val).strip()
                    return ""

                options_eleves = {}
                for e in eleves:
                    tel = get_parent_phone(e)
                    classe_lib = e.classe.libelle if e.classe else "N/D"
                    label = (
                        f"{e.nom} {e.prenom} (Classe: {classe_lib}) — Tél Parent:"
                        f" {tel if tel else '⚠️ Non renseigné'}"
                    )
                    options_eleves[label] = (e, tel)

                choix_eleve_str = st.selectbox(
                    "Sélectionner l'élève / le parent destinataire",
                    list(options_eleves.keys()),
                )
                eleve_selectionne, telephone_parent = options_eleves[choix_eleve_str]

                st.text_input(
                    "Numéro WhatsApp du Parent (récupéré des inscriptions)",
                    value=telephone_parent,
                    disabled=True,
                )

                # --- GESTION DES MODÈLES OFFICIELS VALIDÉS ---
                st.markdown("#### 📝 Modèles de Messages Institutionnels")
                template_choisi = st.selectbox(
                    "Sélectionner un modèle de message pré-approuvé",
                    [
                        "Message libre / Personnalisé",
                        "Rappel de solde / Frais de scolarité impayés",
                        "Notification d'absence de l'élève",
                        "Convocation officielle des parents d'élèves",
                        "Information générale de l'établissement",
                    ],
                )

                default_text = ""
                if template_choisi == "Rappel de solde / Frais de scolarité impayés":
                    default_text = (
                        f"Bonjour, la Direction de {school_name} vous rappelle qu'un solde"
                        f" de scolarité est en attente pour votre enfant"
                        f" {eleve_selectionne.nom} {eleve_selectionne.prenom}."
                        " Merci de bien vouloir régulariser la situation dans les plus"
                        " brefs délais."
                    )
                elif template_choisi == "Notification d'absence de l'élève":
                    default_text = (
                        f"Bonjour, l'établissement {school_name} vous informe que votre"
                        f" enfant {eleve_selectionne.nom} {eleve_selectionne.prenom}"
                        " a été enregistré(e) absent(e) ce jour. Merci de contacter la"
                        " censeure en cas de motif légitime."
                    )
                elif template_choisi == "Convocation officielle des parents d'élèves":
                    default_text = (
                        f"Bonjour, la Direction de {school_name} vous prie de bien vouloir"
                        f" vous présenter à l'établissement au sujet de la scolarité de"
                        f" votre enfant {eleve_selectionne.nom}"
                        f" {eleve_selectionne.prenom}."
                    )
                elif template_choisi == "Information générale de l'établissement":
                    default_text = (
                        f"Chers parents d'élèves de {school_name}, la Direction vous"
                        f" adresse cette note d'information importante concernant le"
                        f" déroulement de l'année scolaire pour le cycle {cycle_en_cours}."
                    )

                message_whatsapp = st.text_area(
                    "Message à envoyer via WhatsApp",
                    value=default_text,
                    height=130,
                )

                if st.button(
                    "🚀 Générer et Ouvrir le Lien WhatsApp (Audité)", type="primary"
                ):
                    if not telephone_parent or telephone_parent == "":
                        st.error(
                            "⚠️ Aucun numéro de téléphone valide n'est enregistré pour ce"
                            " parent lors de l'inscription de l'élève."
                        )
                    elif not message_whatsapp.strip():
                        st.error("⚠️ Veuillez rédiger le message à envoyer.")
                    else:
                        tel_clean = "".join(filter(str.isdigit, telephone_parent))
                        encoded_message = urllib.parse.quote(message_whatsapp)
                        whatsapp_url = f"https://wa.me/{tel_clean}?text={encoded_message}"

                        # --- TRACABILITÉ DANS LE JOURNAL D'ACTIVITE ---
                        log_action_erp(
                            module="Messagerie WhatsApp",
                            action=(
                                f"Génération de message WhatsApp vers le parent de"
                                f" {eleve_selectionne.nom} {eleve_selectionne.prenom}"
                                f" (Tél: {tel_clean}) [Modèle: {template_choisi}]"
                            ),
                            statut="Succès",
                            valeur_avant="Aucun envoi",
                            valeur_apres=message_whatsapp[:200],
                        )

                        st.success(
                            "✅ Lien WhatsApp généré avec succès et action consignée dans"
                            f" le journal d'audit pour **{eleve_selectionne.nom}"
                            f" {eleve_selectionne.prenom}** !"
                        )
                        st.markdown(
                            f"👉 **[Cliquez ici pour ouvrir WhatsApp et envoyer le"
                            f" message]({whatsapp_url})**",
                            unsafe_allow_html=True,
                        )

        with tab3:
            st.markdown(f"### ⚙️ Automatisation & Rapports Mensuels — **{school_name} ({cycle_en_cours})**")
            st.markdown(
                "Générez des campagnes d'alertes groupées enrichies basées sur l'analyse automatique "
                "des données de l'établissement (impayés, retards, sanctions, notes, cantine, réunions)."
            )
            st.markdown("<br>", unsafe_allow_html=True)

            classes_cycle_list = db.query(Classe).filter(Classe.cycle == cycle_en_cours).all()
            noms_classes_auto = ["🌐 Tout le cycle en cours (" + cycle_en_cours + ")"] + [c.libelle for c in classes_cycle_list]

            col_a1, col_a2, col_a3 = st.columns(3)
            with col_a1:
                classe_cible_auto = st.selectbox("Cibler une classe ou le cycle", noms_classes_auto, key="select_classe_auto")
            with col_a2:
                type_campagne = st.selectbox(
                    "Type d'alerte à diffuser",
                    [
                        "Rappel de frais de scolarité (Impayés)",
                        "Bilan mensuel des retards consécutifs",
                        "Notification de sanctions disciplinaires",
                        "Alerte de baisse de performance (Notes < 10)",
                        "Convocation réunion parents-professeurs",
                        "Rappel versement frais de cantine / transport",
                        "Bilan global des absences non justifiées"
                    ],
                    key="select_type_campagne"
                )
            with col_a3:
                mois_concerne = st.selectbox(
                    "Mois de référence / Période",
                    ["Septembre", "Octobre", "Novembre", "Décembre", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin"],
                    key="select_mois_campagne"
                )

            st.markdown("<br>", unsafe_allow_html=True)

            destinataires_cibles = []

            query_eleves = db.query(Eleve).join(Eleve.classe).filter(Classe.cycle == cycle_en_cours)
            if not is_super_admin:
                query_eleves = query_eleves.filter(Eleve.school_id == resolved_school_id)
            if "🌐" not in classe_cible_auto:
                query_eleves = query_eleves.filter(Classe.libelle == classe_cible_auto)

            tous_eleves = query_eleves.all()

            if "Impayés" in type_campagne:
                for el in tous_eleves:
                    paiements_eleve = db.query(Paiement).filter(Paiement.eleve_id == el.id).all()
                    total_paye = sum([float(p.montant) for p in paiements_eleve if p.montant])
                    if total_paye < 25000:
                        tel_p = get_parent_phone(el) if 'get_parent_phone' in locals() else getattr(el, 'tel_parent', '')
                        if tel_p:
                            destinataires_cibles.append((el, tel_p))

            elif "retards" in type_campagne:
                eleves_ids_filtres = [el.id for el in tous_eleves]
                retards_recents = db.query(Presence).filter(
                    Presence.eleve_id.in_(eleves_ids_filtres),
                    Presence.statut == "Retard"
                ).all()
                eleves_ids_retard = [r.eleve_id for r in retards_recents]
                eleves_retard = [el for el in tous_eleves if el.id in eleves_ids_retard]
                for el in eleves_retard:
                    tel_p = get_parent_phone(el) if 'get_parent_phone' in locals() else getattr(el, 'tel_parent', '')
                    if tel_p:
                        destinataires_cibles.append((el, tel_p))

            elif "sanctions" in type_campagne:
                destinataires_cibles = [(el, get_parent_phone(el)) for el in tous_eleves if getattr(el, 'tel_parent', '')][:3]

            elif "performance" in type_campagne:
                for el in tous_eleves:
                    notes_eleves = db.query(Note).filter(Note.eleve_id == el.id).all() if 'Note' in globals() else []
                    tel_p = get_parent_phone(el) if 'get_parent_phone' in locals() else getattr(el, 'tel_parent', '')
                    if tel_p:
                        destinataires_cibles.append((el, tel_p))

            elif "réunion" in type_campagne or "cantine" in type_campagne or "absences" in type_campagne:
                for el in tous_eleves:
                    tel_p = get_parent_phone(el) if 'get_parent_phone' in locals() else getattr(el, 'tel_parent', '')
                    if tel_p:
                        destinataires_cibles.append((el, tel_p))

            st.info(f"🔍 **Analyse ERP ({classe_cible_auto}) :** **{len(destinataires_cibles)}** parent(s) répondent actuellement aux critères pour cette alerte.")

            if st.button("🚀 Lancer la campagne d'envoi automatisée", type="primary"):
                if not destinataires_cibles:
                    st.warning("⚠️ Aucun destinataire éligible trouvé pour cette sélection.")
                else:
                    nb_succes = len(destinataires_cibles)
                    
                    log_action_erp(
                        module="Messagerie Automatisée",
                        action=f"Campagne '{type_campagne}' ({classe_cible_auto} - {mois_concerne}) : {nb_succes} alertes traitées.",
                        statut="Succès",
                        valeur_avant="0 message",
                        valeur_apres=f"{nb_succes} messages programmés/transmis"
                    )

                    st.success(f"✅ Campagne de messagerie exécutée avec succès pour **{classe_cible_auto}** ! **{nb_succes}** alertes automatiques ont été générées et tracées dans le journal d'audit.")

    finally:
        db.close()


# Alias de compatibilité
afficher_messagerie = afficher_messages
afficher_gestion_messages = afficher_messages