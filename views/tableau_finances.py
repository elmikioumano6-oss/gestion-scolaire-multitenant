from datetime import datetime
import io
from database.audit import log_action_erp
from database.db_config import SessionLocal
from database.models import ActivityLog, Classe, Depense, Eleve, Paiement, School
from database.queries import get_classes_cached, get_matieres_cached
import pandas as pd
import streamlit as st


def afficher_tableau_finances():
  st.subheader("📈 Tableau de Bord Financier Global")
  st.markdown(
      "Vue macroscopique incluant la ventilation des cotisations par classe,"
      " cycle et établissement avec prise en compte stricte des frais de"
      " scolarité, des frais COGES, des réductions nominatives, des salaires et des charges opérationnelles."
  )
  st.markdown("---")

  school_id = st.session_state.get("school_id")
  is_super_admin = st.session_state.get("is_super_admin", False)
  school_name = st.session_state.get("school_name", "Établissement")
  cycle_en_cours = st.session_state.get("cycle_actif", "Collège")
  username_connecte = st.session_state.get("username", "admin")

  if not school_id and not is_super_admin:
    st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
    return

  db = SessionLocal()
  try:
    target_school_id = school_id
    if is_super_admin and not target_school_id:
      ecole_defaut = db.query(School).first()
      target_school_id = ecole_defaut.id if ecole_defaut else 1

    ecole_active_id = school_id if school_id else target_school_id

    # Récupération sécurisée des classes du cycle avec isolation multi-tenant
    classes_query = db.query(Classe).filter(
        Classe.cycle == cycle_en_cours, Classe.school_id == ecole_active_id
    )
    if hasattr(Classe, "deleted_at"):
      classes_query = classes_query.filter(Classe.deleted_at.is_(None))
    classes_cycle = classes_query.all()

    def get_classe_libelle(c):
        for attr in ['libelle', 'nom', 'name', 'titre']:
            if hasattr(c, attr) and getattr(c, attr):
                return getattr(c, attr)
        return f"Classe {c.id}"

    classes_dict = {c.id: c for c in classes_cycle}
    classes_ids = list(classes_dict.keys())

    # Récupération sécurisée des élèves strictement rattachés aux classes du cycle actif
    eleves_query = db.query(Eleve).filter(Eleve.school_id == ecole_active_id)
    if hasattr(Eleve, "deleted_at"):
      eleves_query = eleves_query.filter(Eleve.deleted_at.is_(None))
      
    if classes_ids:
      eleves_query = eleves_query.filter(Eleve.classe_id.in_(classes_ids))
    else:
      # Isolation stricte : si aucune classe n'existe pour ce cycle, on renvoie une liste vide
      eleves_query = eleves_query.filter(Eleve.classe_id == -1)
      
    eleves = eleves_query.all()

    total_classes = len(classes_cycle)
    total_eleves = len(eleves)

    budget_attendu = 0.0
    total_encaisse = 0.0

    # Calcul précis : Scolarité (65000) + COGES (2000) - Réduction (5000) = 62000 net par défaut
    for eleve in eleves:
      classe = classes_dict.get(eleve.classe_id) if eleve.classe_id else None
      frais_scol = float(
          getattr(classe, "frais_scolarite", 65000.0) or 65000.0
      )
      frais_inscr = float(getattr(classe, "frais_inscription", 0.0) or 0.0)
      frais_coges = float(getattr(classe, "frais_coges", 2000.0) or 2000.0)

      frais_brut_total = frais_scol + frais_inscr + frais_coges
      reduction = float(getattr(eleve, "montant_reduction", 5000.0) or 5000.0)
      net_eleve = max(0.0, frais_brut_total - reduction)

      budget_attendu += net_eleve

      paiements_eleve = (
          db.query(Paiement)
          .filter(
              Paiement.eleve_id == eleve.id,
              Paiement.school_id == ecole_active_id,
          )
          .all()
      )
      montant_paye = (
          sum(
              float(getattr(p, "montant_total", None) or getattr(p, "montant", 0.0))
              for p in paiements_eleve
          )
          if paiements_eleve
          else 0.0
      )
      total_encaisse += montant_paye

    # Récupération et calcul des dépenses et salaires pour le cycle/école active
    depenses_query = db.query(Depense).filter(
        Depense.school_id == ecole_active_id,
        Depense.cycle == cycle_en_cours
    )
    depenses_list = depenses_query.all()
    total_depenses = sum(float(d.montant or 0.0) for d in depenses_list)
    solde_net_caisse = total_encaisse - total_depenses

    taux = (
        (total_encaisse / budget_attendu * 100) if budget_attendu > 0 else 0.0
    )
    reste_a_recouvrer = max(0.0, budget_attendu - total_encaisse)

    st.markdown(
        f"### Tableau Financier Global — **{school_name} ({cycle_en_cours})**"
    )

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
      st.metric("Classes Actives", total_classes)
    with col2:
      st.metric("Élèves Inscrits", total_eleves)
    with col3:
      st.metric("Budget Attendu (Net)", f"{budget_attendu:,.0f} FCFA")
    with col4:
      st.metric(
          "Total Encaissé",
          f"{total_encaisse:,.0f} FCFA",
          delta=f"{taux:.1f}% réalisé",
      )
    with col5:
      st.metric(
          "Solde Net en Caisse",
          f"{solde_net_caisse:,.0f} FCFA",
          delta="Disponible" if solde_net_caisse >= 0 else "Déficit",
          delta_color="normal" if solde_net_caisse >= 0 else "inverse",
      )

    st.markdown("---")
    st.markdown(
        f"### Répartition Financière par Classe — **{cycle_en_cours}**"
    )

    if not classes_cycle:
      st.info(
          f"📌 Aucune classe configurée pour le cycle **{cycle_en_cours}**."
          " Veuillez en créer pour afficher la ventilation détaillée."
      )
    else:
      repartition_data = []
      for classe in classes_cycle:
        eleves_classe = [e for e in eleves if e.classe_id == classe.id]
        nb_eleves = len(eleves_classe)

        attendu_classe = 0.0
        encaisse_classe = 0.0

        for e in eleves_classe:
          f_scol = float(
              getattr(classe, "frais_scolarite", 65000.0) or 65000.0
          )
          f_inscr = float(getattr(classe, "frais_inscription", 0.0) or 0.0)
          f_coges = float(getattr(classe, "frais_coges", 2000.0) or 2000.0)
          brut_e = f_scol + f_inscr + f_coges
          red_e = float(getattr(e, "montant_reduction", 5000.0) or 5000.0)
          attendu_classe += max(0.0, brut_e - red_e)

          p_eleve = (
              db.query(Paiement)
              .filter(
                  Paiement.eleve_id == e.id,
                  Paiement.school_id == ecole_active_id,
              )
              .all()
          )
          encaisse_classe += (
              sum(
                  float(
                      getattr(p, "montant_total", None)
                      or getattr(p, "montant", 0.0)
                  )
                  for p in p_eleve
              )
              if p_eleve
              else 0.0
          )

        classe_lib = get_classe_libelle(classe)
        repartition_data.append({
            "Classe": classe_lib,
            "Niveau": getattr(classe, "niveau", "N/D"),
            "Effectif": nb_eleves,
            "Attendu (Net)": attendu_classe,
            "Encaissé": encaisse_classe,
            "Reste à Recouvrer": max(0.0, attendu_classe - encaisse_classe),
        })

      df_rep = pd.DataFrame(repartition_data)
      st.dataframe(df_rep, use_container_width=True, hide_index=True)

      # Section d'exportation professionnelle
      st.markdown("##### 📥 Exportation des Bilans Macroscopiques")
      col_e1, col_e2 = st.columns(2)

      with col_e1:
        csv_rep = df_rep.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📊 Télécharger le bilan CSV",
            data=csv_rep,
            file_name=(
                f"Bilan_Financier_Global_{school_name}_{cycle_en_cours}.csv"
            ),
            mime="text/csv",
        )

      with col_e2:
        output_excel = io.BytesIO()
        with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
          df_rep.to_excel(writer, index=False, sheet_name="BilanGlobal")
        excel_bytes = output_excel.getvalue()
        st.download_button(
            label="📈 Télécharger le bilan Excel (.xlsx)",
            data=excel_bytes,
            file_name=(
                f"Bilan_Financier_Global_{school_name}_{cycle_en_cours}.xlsx"
            ),
            mime=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )

    # Journalisation d'audit de l'action
    db.add(
        ActivityLog(
            school_id=ecole_active_id,
            timestamp=datetime.utcnow(),
            username=username_connecte,
            action=f"Consultation du tableau financier global ({cycle_en_cours})",
            module="Tableau Finances",
            statut="Succès",
        )
    )
    db.commit()

  finally:
    db.close()


# Alias de compatibilité exhaustive pour le routeur app.py
afficher_tableau_finances = afficher_tableau_finances
afficher_finances = afficher_tableau_finances