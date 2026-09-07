from datetime import datetime
import io
from database.audit import log_action_erp
from database.db_config import SessionLocal
from database.models import ActivityLog, Classe, Eleve, Paiement, School
import pandas as pd
import streamlit as st


def afficher_soldes_impayes(niveau_actif="Collège"):
  st.subheader("📊 Soldes & Suivi des Impayés")
  st.markdown(
      "Suivi des encaissements, des réductions et des soldes restants par élève"
      " avec prise en compte des quittances saisies par la comptabilité,"
      " conformité comptable (contre-passation) et gouvernance RBAC stricte."
  )
  st.markdown("---")

  school_id = st.session_state.get("school_id")
  if not school_id:
    st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
    return

  is_super_admin = st.session_state.get("is_super_admin", False)
  user_role = str(st.session_state.get("role", "")).lower()
  username_connecte = st.session_state.get("username", "admin")

  profil_autorise_annulation = (
      is_super_admin
      or ("directeur" in user_role)
      or ("comptable" in user_role)
      or ("admin" in user_role)
  )

  db = SessionLocal()
  try:
    classes = (
        db.query(Classe)
        .filter(Classe.school_id == school_id, Classe.cycle == niveau_actif)
        .all()
    )

    if not classes:
      st.warning(f"Aucune classe trouvée pour le cycle {niveau_actif}.")
      return

    options_classes = {c.libelle: c.id for c in classes}
    choix_classe = st.selectbox(
        "Filtrer par classe",
        list(options_classes.keys()),
        key="select_classe_solde",
    )

    classe_id_sel = options_classes[choix_classe]
    classe_obj = db.query(Classe).filter(Classe.id == classe_id_sel).first()

    eleves = (
        db.query(Eleve)
        .filter(Eleve.school_id == school_id, Eleve.classe_id == classe_id_sel)
        .all()
    )

    if not eleves:
      st.info("Aucun élève dans cette classe.")
      return

    frais_scolarite_base = float(classe_obj.frais_scolarite or 0.0)
    frais_coges = float(getattr(classe_obj, "frais_coges", 0.0) or 0.0)
    total_brut_classe = frais_scolarite_base + frais_coges

    col_f1, col_f2 = st.columns([2, 2])
    with col_f1:
      filtre_statut_solde = st.selectbox(
          "🔍 Filtrer par état de paiement",
          ["Tous les élèves", "Uniquement les impayés", "Soldés / Trop-perçu"],
      )

    cols = st.columns([2, 1.5, 1.5, 1.5, 1.5, 2])
    cols[0].markdown("**Élève**")
    cols[1].markdown("**Montant Brut**")
    cols[2].markdown("**Réduction**")
    cols[3].markdown("**Net à Payer**")
    cols[4].markdown("**Total Versé**")
    cols[5].markdown("**Solde Restant**")
    for i in range(6):
      cols[i].markdown("---")

    data_export = []
    eleves_a_afficher = []

    for e in eleves:
      reduction = float(e.montant_reduction or 0.0)
      net_a_payer = max(0.0, total_brut_classe - reduction)

      paiements_eleve = (
          db.query(Paiement)
          .filter(Paiement.school_id == school_id, Paiement.eleve_id == e.id)
          .all()
      )
      total_verse = sum([float(p.montant) for p in paiements_eleve])
      solde_restant = net_a_payer - total_verse

      if filtre_statut_solde == "Uniquement les impayés" and solde_restant <= 0:
        continue
      elif (
          filtre_statut_solde == "Soldés / Trop-perçu" and solde_restant > 0
      ):
        continue

      eleves_a_afficher.append(
          (e, net_a_payer, total_verse, solde_restant, reduction)
      )

      statut_export = (
          f"Impayé ({solde_restant:,.0f} F)"
          if solde_restant > 0
          else (
              f"Trop-perçu ({abs(solde_restant):,.0f} F)"
              if solde_restant < 0
              else "Soldé (0 F)"
          )
      )
      data_export.append({
          "Matricule": e.matricule,
          "Élève": f"{e.nom} {e.prenom}",
          "Montant Brut (F)": f"{total_brut_classe:,.0f}",
          "Réduction (F)": f"-{reduction:,.0f}",
          "Net à Payer (F)": f"{net_a_payer:,.0f}",
          "Total Versé (F)": f"{total_verse:,.0f}",
          "Statut": statut_export,
      })

    for (
        e,
        net_a_payer,
        total_verse,
        solde_restant,
        reduction,
    ) in eleves_a_afficher:
      c = st.columns([2, 1.5, 1.5, 1.5, 1.5, 2])
      c[0].write(f"{e.nom} {e.prenom} ({e.matricule})")
      c[1].write(f"{total_brut_classe:,.0f} F")
      c[2].write(f"-{reduction:,.0f} F" if reduction > 0 else "0 F")
      c[3].write(f"{net_a_payer:,.0f} F")
      c[4].write(f"{total_verse:,.0f} F")

      if solde_restant > 0:
        c[5].markdown(
            f"<span style='color: red; font-weight: bold;'>{solde_restant:,.0f}"
            " F (Impayé)</span>",
            unsafe_allow_html=True,
        )
      elif solde_restant < 0:
        c[5].markdown(
            f"<span style='color: orange; font-weight: bold;'>{abs(solde_restant):,.0f}"
            " F (Trop-perçu)</span>",
            unsafe_allow_html=True,
        )
      else:
        c[5].markdown(
            "<span style='color: green; font-weight: bold;'>Soldé (0 F)</span>",
            unsafe_allow_html=True,
        )

    if data_export:
      st.markdown("---")
      st.markdown("##### 📥 Exportation des Rapports de Recouvrement")
      df_exp = pd.DataFrame(data_export)

      col_ex1, col_ex2 = st.columns(2)

      with col_ex1:
        st.download_button(
            "📊 Télécharger en CSV",
            df_exp.to_csv(index=False).encode("utf-8"),
            f"Suivi_Impayes_{choix_classe}.csv",
            "text/csv",
        )
      with col_ex2:
        output_io = io.BytesIO()
        with pd.ExcelWriter(output_io, engine="openpyxl") as writer:
          df_exp.to_excel(writer, index=False, sheet_name="Impayes")
        st.download_button(
            "📈 Télécharger en Excel (.xlsx)",
            output_io.getvalue(),
            f"Suivi_Impayes_{choix_classe}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    st.markdown("---")
    st.markdown("### 🛠️ Gestion & Contre-Passation des Versements Erronés")
    st.markdown(
        "Conformément aux normes comptables internationales, la suppression"
        " physique est remplacée par une écriture de contre-passation (Avoir /"
        " Régularisation) pour garantir l'immutabilité du grand livre."
    )

    if not profil_autorise_annulation:
      st.warning(
          "🔒 Accès restreint : Seuls les profils Directeur ou Comptable"
          " Principal sont habilités à effectuer des contre-passations de"
          " quittances."
      )
    else:
      options_eleves_tous = {
          f"{elev.nom} {elev.prenom} ({elev.matricule})": elev.id
          for elev in eleves
      }
      eleve_a_gerer_str = st.selectbox(
          "Sélectionner un élève pour auditer ou contre-passer ses reçus",
          list(options_eleves_tous.keys()),
      )
      eleve_gerer_id = options_eleves_tous[eleve_a_gerer_str]

      historique_paiements = (
          db.query(Paiement)
          .filter(
              Paiement.school_id == school_id, Paiement.eleve_id == eleve_gerer_id
          )
          .all()
      )

      if not historique_paiements:
        st.info("Aucun versement enregistré pour cet élève.")
      else:
        for p in historique_paiements:
          col_p1, col_p2, col_p3, col_p4 = st.columns([2, 2, 2, 1])
          col_p1.write(f"**Reçu :** {p.reference_recu}")
          col_p2.write(f"**Montant :** {p.montant:,.0f} F")
          col_p3.write(f"**Motif :** {p.motif}")

          with col_p4:
            if st.button(
                "🔄 Contre-passer",
                key=f"contrepasser_paiement_{p.id}",
                help="Émettre une écriture de régularisation (Avoir)",
            ):
              montant_annule = float(p.montant)
              ref_orig = p.reference_recu
              motif_orig = p.motif

              paiement_avoir = Paiement(
                  school_id=school_id,
                  eleve_id=eleve_gerer_id,
                  montant=-montant_annule,
                  motif=(
                      f"CONTRE-PASSATION (Avoir) - Réf: {ref_orig}"
                      f" ({motif_orig})"
                  ),
                  mode_reglement="Régularisation Comptable",
                  reference_recu=f"AVOIR-{ref_orig}",
                  agent_caisse=username_connecte,
                  date_paiement=datetime.utcnow(),
              )
              db.add(paiement_avoir)

              db.add(
                  ActivityLog(
                      school_id=school_id,
                      timestamp=datetime.utcnow(),
                      username=username_connecte,
                      action=(
                          f"Contre-passation de {montant_annule:,.0f} F sur la"
                          f" quittance {ref_orig} (Élève ID: {eleve_gerer_id})"
                      ),
                      module="Soldes & Impayés",
                      statut="Succès",
                  )
              )
              db.commit()
              st.success(
                  f"✅ Écriture de contre-passation (Avoir) générée avec succès"
                  f" pour le reçu {ref_orig} !"
              )
              st.rerun()
          st.markdown(
              "<hr style='margin: 0.1rem 0;"
              " border-color: rgba(255,255,255,0.05);'>",
              unsafe_allow_html=True,
          )

    db.add(
        ActivityLog(
            school_id=school_id,
            timestamp=datetime.utcnow(),
            username=username_connecte,
            action=f"Consultation du module Soldes & Impayés ({niveau_actif})",
            module="Soldes & Impayés",
            statut="Succès",
        )
    )
    db.commit()

  finally:
    db.close()


# Alias de compatibilité indispensable pour le routeur
afficher_soldes_impayes = afficher_soldes_impayes
afficher_soldes_et_impayes = afficher_soldes_impayes