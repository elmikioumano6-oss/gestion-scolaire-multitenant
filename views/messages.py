from datetime import datetime
import urllib.parse
from database.audit import log_action_erp
from database.db_config import SessionLocal
from database.models import Eleve, School, User
from database.queries import get_classes_cached, get_matieres_cached
import streamlit as st


def afficher_messages():
  st.subheader("💬 Messagerie WhatsApp Intégrée")
  st.markdown(
      "Centre de communication WhatsApp automatisé : réception des messages et"
      " envoi direct sécurisé et audité aux parents."
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
    tab1, tab2 = st.tabs([
        "📥 Boîte de Réception WhatsApp",
        "📤 Envoi Direct WhatsApp aux Parents (Audité)",
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
              " adresse cette note d'information importante concernant le"
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

            # --- TRACABILITÉ DANS LE JOURNAL D'ACTIVITE (NORMES SOC 2 / ISO 27001) ---
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

  finally:
    db.close()


# Alias de compatibilité
afficher_messagerie = afficher_messages
afficher_gestion_messages = afficher_messages