from datetime import datetime
from database.audit import log_action_erp
from database.db_config import SessionLocal
from database.models import Depense, School
import pandas as pd
import streamlit as st


def afficher_depenses():
  st.subheader("📉 Gestion des Dépenses")
  st.markdown(
      "Suivi des charges opérationnelles, pièces justificatives et"
      " contre-passation comptable par établissement et par cycle."
  )
  st.markdown("---")

  school_id = st.session_state.get("school_id")
  is_super_admin = st.session_state.get("is_super_admin", False)
  school_name = st.session_state.get("school_name", "Établissement")
  cycle_en_cours = st.session_state.get("cycle_actif", "Collège")
  username_connecte = st.session_state.get("username", "admin")
  user_role = str(st.session_state.get("role", "")).lower()

  # Gouvernance RBAC pour l'annulation/contre-passation
  profil_autorise_annulation = (
      is_super_admin
      or ("directeur" in user_role)
      or ("comptable" in user_role)
      or ("admin" in user_role)
  )

  if not school_id and not is_super_admin:
    st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
    return

  db = SessionLocal()
  try:
    target_school_id = school_id or 1

    tab_saisie, tab_historique = st.tabs([
        "➕ Enregistrer une Dépense",
        "📋 Historique & Contre-Passation",
    ])

    with tab_saisie:
      st.markdown(
          f"### Enregistrement des Dépenses — **{school_name} ({cycle_en_cours})**"
      )

      with st.form("form_add_depense"):
        col1, col2 = st.columns(2)
        with col1:
          libelle_depense = st.text_input(
              "Libellé / Motif de la dépense *",
              placeholder="Ex: Achat de fournitures pédagogiques",
          )
          montant = st.number_input(
              "Montant (FCFA) *", min_value=0.0, step=1000.0, value=0.0
          )
          categorie = st.selectbox("Catégorie", [
              "Fournitures scolaires",
              "Maintenance & Réparations",
              "Charges administratives",
              "Énergie & Eau",
              "Divers",
          ])
        with col2:
          # Saisie libre obligatoire de la pièce justificative (Facture / Bon de caisse)
          ref_piece = st.text_input(
              "N° de Pièce Justificative / Facture (Saisie libre) *",
              value="",
              placeholder="Ex: BC-2026-001 ou Facture N°...",
              help="Saisissez la référence de la pièce justificative physique.",
          )
          mode_paiement = st.selectbox(
              "Mode de décaissement",
              [
                  "Espèces",
                  "Chèque",
                  "Virement Bancaire",
                  "Mobile Money (Orange/Moov)",
              ],
          )
          date_depense = st.date_input(
              "Date de la dépense", value=datetime.now()
          )

        submitted = st.form_submit_button(
            "💾 Enregistrer la dépense", type="primary"
        )
        if submitted:
          libelle_clean = libelle_depense.strip()
          ref_clean = ref_piece.strip()

          if not libelle_clean or montant <= 0:
            st.error(
                "⚠️ Veuillez renseigner un libellé valide et un montant"
                " supérieur à zéro."
            )
          elif not ref_clean:
            st.error(
                "⚠️ Le numéro de pièce justificative / facture est obligatoire."
            )
          else:
            # Vérification de l'unicité de la pièce justificative
            doublon_piece = (
                db.query(Depense)
                .filter(
                    Depense.school_id == target_school_id,
                    Depense.reference_piece == ref_clean,
                )
                .first()
            )

            if doublon_piece:
              st.error(
                  f"⚠️ La référence de pièce '{ref_clean}' existe déjà dans le"
                  " système."
              )
            else:
              # Enregistrement en base de données avec la pièce justificative
              nouvelle_depense = Depense(
                  school_id=target_school_id,
                  cycle=cycle_en_cours,
                  libelle=libelle_clean,
                  montant=montant,
                  categorie=categorie,
                  reference_piece=ref_clean,
                  mode_paiement=mode_paiement,
                  date_depense=datetime.combine(
                      date_depense, datetime.now().time()
                  ),
                  auteur=username_connecte,
              )
              db.add(nouvelle_depense)

              log_action_erp(
                  module="Gestion des Dépenses",
                  action=(
                      f"Enregistrement dépense [{categorie}] :"
                      f" {libelle_clean} ({montant:,.0f} FCFA) - Pièce:"
                      f" {ref_clean}"
                  ),
                  statut="Critique",
                  valeur_avant="0 FCFA",
                  valeur_apres=f"{montant:,.0f} FCFA",
              )

              db.commit()
              st.success(
                  f"✅ Dépense de {montant:,.0f} FCFA ('{libelle_clean}')"
                  f" enregistrée sous la pièce **{ref_clean}** avec succès !"
              )
              st.rerun()

    with tab_historique:
      st.markdown(
          f"### Historique & Contre-Passation — **{school_name}"
          f" ({cycle_en_cours})**"
      )

      query_depenses = db.query(Depense).filter(Depense.cycle == cycle_en_cours)
      if not is_super_admin and school_id:
        query_depenses = query_depenses.filter(
            Depense.school_id == school_id
        )

      depenses_list = (
          query_depenses.order_by(Depense.date_depense.desc()).all()
      )

      if not depenses_list:
        st.info(
            f"📌 Aucune dépense enregistrée pour le cycle **{cycle_en_cours}**"
            " dans cet établissement."
        )
      else:
        total_depenses = sum(d.montant for d in depenses_list)
        st.metric("💵 Total des Dépenses du Cycle", f"{total_depenses:,.0f} FCFA")

        st.markdown("---")
        st.markdown("#### 🔍 Liste détaillée et gestion des contre-passations")

        for d in depenses_list:
          ref_p = (
              d.reference_piece
              if hasattr(d, "reference_piece") and d.reference_piece
              else "Sans référence"
          )
          col_d1, col_d2, col_d3, col_d4 = st.columns([2, 1.5, 2.5, 1])
          col_d1.write(f"**Pièce :** `{ref_p}`")
          col_d2.write(f"**Montant :** {d.montant:,.0f} F")
          col_d3.write(f"**Motif :** {d.libelle} *({d.categorie})*")

          with col_d4:
            # Empêche de contre-passer un Avoir existant
            if not ref_p.startswith("AVOIR-"):
              if st.button(
                  "🔄 Contre-passer",
                  key=f"contrepasser_depense_{d.id}",
                  help="Émettre une écriture de régularisation (Avoir)",
              ):
                if not profil_autorise_annulation:
                  st.error(
                      "🔒 Accès restreint : Réservé aux Directeurs et"
                      " Comptables."
                  )
                else:
                  montant_d = float(d.montant)
                  ref_orig = ref_p

                  depense_avoir = Depense(
                      school_id=target_school_id,
                      cycle=cycle_en_cours,
                      libelle=f"CONTRE-PASSATION (Avoir) - Réf: {ref_orig} ({d.libelle})",
                      montant=-montant_d,
                      categorie=d.categorie,
                      reference_piece=f"AVOIR-{ref_orig}",
                      mode_paiement="Régularisation Comptable",
                      date_depense=datetime.utcnow(),
                      auteur=username_connecte,
                  )
                  db.add(depense_avoir)

                  log_action_erp(
                      module="Gestion des Dépenses",
                      action=(
                          f"Contre-passation de dépense de {montant_d:,.0f} F"
                          f" (Pièce d'avoir: AVOIR-{ref_orig})"
                      ),
                      statut="Critique",
                      valeur_avant=f"{montant_d:,.0f} FCFA",
                      valeur_apres=f"-{montant_d:,.0f} FCFA",
                  )
                  db.commit()
                  st.success(
                      f"✅ Écriture de contre-passation (AVOIR-{ref_orig})"
                      " générée avec succès !"
                  )
                  st.rerun()

          st.markdown(
              "<hr style='margin: 0.2rem 0;"
              " border-color: rgba(255,255,255,0.05);'>",
              unsafe_allow_html=True,
          )

  finally:
    db.close()


# Alias de compatibilité exhaustive pour le routeur app.py
afficher_depenses = afficher_depenses
afficher_gestion_depenses = afficher_depenses