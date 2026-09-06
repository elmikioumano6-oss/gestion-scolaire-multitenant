import base64
from datetime import datetime
from io import BytesIO
import os
import streamlit as st
import streamlit.components.v1 as components
from database.db_config import SessionLocal
from database.models import ActivityLog, Classe, Eleve, Matiere, Note, School


def get_image_base64(path):
  if os.path.exists(path):
    with open(path, "rb") as image_file:
      return base64.b64encode(image_file.read()).decode()
  return ""


def afficher_bulletins(niveau_actif="Collège"):
  school_id = st.session_state.get("school_id")
  is_super_admin = st.session_state.get("is_super_admin", False)
  username = st.session_state.get("username", "admin")

  db = SessionLocal()
  try:
    # 1. Résolution stricte multi-tenant de l'école active (Nom, Adresse, Contacts changeant dynamiquement)
    target_school_id = school_id
    if is_super_admin and not target_school_id:
      ecole_defaut = db.query(School).first()
      target_school_id = ecole_defaut.id if ecole_defaut else 1

    ecole_active_id = school_id if school_id else target_school_id

    nom_ecole = "COMPLEXE SCOLAIRE PRIVE RAHMAT-FH"
    devise_ecole = "Excellence - Persévérance - Réussite"
    adresse_ecole = "QUARTIER AEROPORT NIAMEY-NIGER"
    contacts_ecole = "TEL : 99 79 71 63 / 97 32 77 52 / 92 53 27 10"

    if ecole_active_id:
      ecole = db.query(School).filter(School.id == ecole_active_id).first()
      if ecole:
        nom_ecole = ecole.nom.upper()
        devise_ecole = getattr(ecole, "devise", devise_ecole)
        adresse_ecole = getattr(ecole, "adresse", adresse_ecole).upper()
        contacts_ecole = getattr(ecole, "contacts", contacts_ecole)

    st.subheader("📄 Édition des Bulletins Scolaires Officiels")
    st.markdown(
        f"Générez, imprimez et vérifiez l'authenticité des bulletins conformes"
        f" au modèle institutionnel de **{nom_ecole}** pour le cycle : **{niveau_actif}**."
    )
    st.markdown("---")

    # 2. Récupération sécurisée et filtrée des classes de l'établissement actif
    classes_query = db.query(Classe).filter(Classe.cycle == niveau_actif)
    if hasattr(Classe, "deleted_at"):
      classes_query = classes_query.filter(Classe.deleted_at.is_(None))

    if school_id:
      classes_query = classes_query.filter(Classe.school_id == school_id)
    else:
      classes_query = classes_query.filter(Classe.school_id == target_school_id)

    classes = classes_query.all()

    if not classes:
      st.warning(
          f"Aucune classe active disponible pour le cycle {niveau_actif} dans cet"
          " établissement."
      )
      return

    def get_label(obj):
      for attr in ["libelle", "nom", "name", "titre"]:
        if hasattr(obj, attr):
          return getattr(obj, attr)
      return f"ID {obj.id}"

    # --- PANNEAU DE CONTRÔLE ET SÉLECTEURS PROFESSIONNELS ---
    with st.container():
      st.markdown("### ⚙️ Paramètres d'Édition & Filtres")
      col_f1, col_f2, col_f3 = st.columns(3)

      with col_f1:
        classe_noms = {get_label(c): c.id for c in classes}
        classe_choisie = st.selectbox(
            "🏫 Sélectionnez la Classe :", options=list(classe_noms.keys())
        )
        classe_id = classe_noms[classe_choisie]

      with col_f2:
        # Restriction stricte aux Semestres demandés
        semestre = st.selectbox(
            "📅 Période Académique :", options=["Semestre 1", "Semestre 2"]
        )

      with col_f3:
        portee = st.radio(
            "🎯 Portée de l'édition :",
            options=["Élève unique", "Toute la classe"],
            horizontal=True,
        )

    # 3. Récupération isolée des élèves de l'école
    eleves_query = db.query(Eleve).filter(Eleve.classe_id == classe_id)
    if hasattr(Eleve, "deleted_at"):
      eleves_query = eleves_query.filter(Eleve.deleted_at.is_(None))

    if school_id:
      eleves_query = eleves_query.filter(Eleve.school_id == school_id)
    else:
      eleves_query = eleves_query.filter(Eleve.school_id == target_school_id)

    eleves = eleves_query.all()

    if not eleves:
      st.info(f"Aucun élève actif inscrit dans la classe de {classe_choisie}.")
      return

    eleve_id_selectionne = None
    if portee == "Élève unique":
      st.markdown("")
      eleve_dict = {
          f"{getattr(e, 'matricule', 'N/A')} - {e.nom} {e.prenom}": e.id
          for e in eleves
      }
      eleve_choisi_str = st.selectbox(
          "👨‍🎓 Sélectionnez l'Élève :", options=list(eleve_dict.keys())
      )
      eleve_id_selectionne = eleve_dict[eleve_choisi_str]

    st.markdown("---")

    # Traçabilité dans l'ERP liée à l'établissement en cours
    nouveau_log = ActivityLog(
        school_id=ecole_active_id,
        timestamp=datetime.utcnow(),
        username=username,
        action=(
            f"Édition des bulletins ({semestre}) pour la classe de"
            f" {classe_choisie} ({nom_ecole})"
        ),
        module="Bulletins",
        statut="Succès",
    )
    db.add(nouveau_log)
    db.commit()

    # 4. Récupération des matières de l'école
    matieres_query = db.query(Matiere).filter(Matiere.cycle == niveau_actif)
    if hasattr(Matiere, "deleted_at"):
      matieres_query = matieres_query.filter(Matiere.deleted_at.is_(None))

    if school_id:
      matieres_query = matieres_query.filter(Matiere.school_id == school_id)
    else:
      matieres_query = matieres_query.filter(
          Matiere.school_id == target_school_id
      )

    matieres_brutes = matieres_query.all()
    matieres_dict_unique = {}
    for m in matieres_brutes:
      nom_m = get_label(m)
      if nom_m not in matieres_dict_unique:
        matieres_dict_unique[nom_m] = m

    matieres_toutes = list(matieres_dict_unique.values())

    is_troisieme = (
        "3" in classe_choisie.upper() or "TROISIEME" in classe_choisie.upper()
    )
    matieres = []
    for m in matieres_toutes:
      nom_m_lower = get_label(m).lower()
      if is_troisieme and (
          "economie familiale" in nom_m_lower
          or "familiale et sociale" in nom_m_lower
      ):
        continue
      matieres.append(m)

    # 5. Récupération des Notes Réelles
    toutes_notes_classe = (
        db.query(Note).join(Eleve).filter(Eleve.classe_id == classe_id).all()
    )
    notes_periode = [
        n
        for n in toutes_notes_classe
        if str(getattr(n, "semestre", "")) == str(semestre)
    ]
    notes_s1 = [
        n
        for n in toutes_notes_classe
        if str(getattr(n, "semestre", "")) in ["Semestre 1"]
    ]

    def calculer_moyennes_notes(notes_subset):
      matrice = {}
      for n in notes_subset:
        e_id = n.eleve_id
        m_id = getattr(n, "matiere_id", None)
        val = float(getattr(n, "valeur", 0.0))
        if e_id not in matrice:
          matrice[e_id] = {}
        if m_id not in matrice[e_id]:
          matrice[e_id][m_id] = []
        matrice[e_id][m_id].append(val)

      moy_dict = {}
      for e in eleves:
        notes_e = matrice.get(e.id, {})
        if notes_e:
          mots_moy = [
              sum(notes_e.get(m.id, [0])) / len(notes_e.get(m.id, [1]))
              for m in matieres
              if notes_e.get(m.id)
          ]
          moy_dict[e.id] = (
              round(sum(mots_moy) / len(mots_moy), 2) if mots_moy else 0.0
          )
        else:
          moy_dict[e.id] = 0.0
      return matrice, moy_dict

    matrice_notes, moyennes_generales = calculer_moyennes_notes(notes_periode)
    _, moyennes_s1 = calculer_moyennes_notes(notes_s1)

    moyennes_annuelles = {}
    for e in eleves:
      m_s1 = moyennes_s1.get(e.id, 0.0)
      m_s2 = moyennes_generales.get(e.id, 0.0)
      if ("2" in semestre) and (m_s1 > 0 or m_s2 > 0):
        moyennes_annuelles[e.id] = round((m_s1 + m_s2) / 2.0, 2)
      else:
        moyennes_annuelles[e.id] = m_s2 if ("2" in semestre) else m_s1

    classement_trie = sorted(
        moyennes_generales.items(), key=lambda x: x[1], reverse=True
    )
    classement_annuel_trie = sorted(
        moyennes_annuelles.items(), key=lambda x: x[1], reverse=True
    )

    effectif = len(eleves)
    garcons = sum(
        1
        for el in eleves
        if str(getattr(el, "sexe", "G")).upper() in ["M", "GARÇON", "G"]
    )
    filles = sum(
        1 for el in eleves if str(getattr(el, "sexe", "G")).upper() in ["F", "FILLE"]
    )

    logo_b64 = get_image_base64("Logo CSP-RAHMAT-FH.png")
    logo_img_tag = (
        f'<img src="data:image/png;base64,{logo_b64}" style="max-height: 55px;'
        ' max-width: 55px; object-fit: contain;" />'
        if logo_b64
        else "<b>LOGO</b>"
    )

    vals_moyennes = [v for v in moyennes_generales.values() if v > 0]
    moy_classe_val = (
        round(sum(vals_moyennes) / len(vals_moyennes), 2)
        if vals_moyennes
        else 0.0
    )
    max_moy_val = round(max(vals_moyennes), 2) if vals_moyennes else 0.0
    min_moy_val = round(min(vals_moyennes), 2) if vals_moyennes else 0.0

    def rendre_bulletin(eleve_obj):
      moy_eleve = moyennes_generales.get(eleve_obj.id, 0.0)
      moy_s1_eleve = moyennes_s1.get(eleve_obj.id, 0.0)
      moy_annuelle_eleve = moyennes_annuelles.get(eleve_obj.id, 0.0)

      position_idx = 1
      for idx, (id_el, _) in enumerate(classement_trie, start=1):
        if id_el == eleve_obj.id:
          position_idx = idx
          break

      position_annuelle_idx = 1
      for idx, (id_el, _) in enumerate(classement_annuel_trie, start=1):
        if id_el == eleve_obj.id:
          position_annuelle_idx = idx
          break

      sexe_eleve = str(getattr(eleve_obj, "sexe", "G")).upper()
      is_fille = sexe_eleve in ["F", "FILLE"]
      rang_eleve = (
          "1ère"
          if (position_idx == 1 and is_fille)
          else ("1er" if position_idx == 1 else f"{position_idx} ème")
      )
      rang_annuel = (
          "1ère"
          if (position_annuelle_idx == 1 and is_fille)
          else ("1er" if position_annuelle_idx == 1 else f"{position_annuelle_idx} ème")
      )

      lignes_html = ""
      total_coef = 0
      total_moyen_coef = 0
      notes_eleve = matrice_notes.get(eleve_obj.id, {})

      for m in matieres:
        m_nom = get_label(m)
        notes_m = notes_eleve.get(m.id, [])
        note_classe = round(sum(notes_m) / len(notes_m), 2) if notes_m else 0.0
        note_compo = note_classe
        coef = int(getattr(m, "coefficient", 2) or 2)
        moyen_coef = note_classe * coef

        total_coef += coef
        total_moyen_coef += moyen_coef

        appreciation = (
            "Très Bien"
            if note_classe >= 16
            else (
                "Bien"
                if note_classe >= 14
                else (
                    "Assez Bien"
                    if note_classe >= 12
                    else ("Passable" if note_classe >= 10 else "Faible")
                )
            )
        )

        if note_classe == 0.0 and not notes_m:
          note_classe_str = note_compo_str = moyen_coef_str = ""
          appreciation = "Non noté"
        else:
          note_classe_str = f"{note_classe:.2f}"
          note_compo_str = f"{note_compo:.2f}"
          moyen_coef_str = f"{round(moyen_coef, 2):.2f}"

        lignes_html += f"""
                    <tr>
                        <td style="border: 1px solid #000; padding: 4px 6px; text-align: left; font-size: 0.85rem;">{m_nom}</td>
                        <td style="border: 1px solid #000; padding: 4px 6px; text-align: center; font-size: 0.85rem;">{note_classe_str}</td>
                        <td style="border: 1px solid #000; padding: 4px 6px; text-align: center; font-size: 0.85rem;">{note_compo_str}</td>
                        <td style="border: 1px solid #000; padding: 4px 6px; text-align: center; font-size: 0.85rem;">{coef}</td>
                        <td style="border: 1px solid #000; padding: 4px 6px; text-align: center; font-size: 0.85rem;">{moyen_coef_str}</td>
                        <td style="border: 1px solid #000; padding: 4px 6px; text-align: center; font-size: 0.85rem;">{rang_eleve if note_classe_str else ''}</td>
                        <td style="border: 1px solid #000; padding: 4px 6px; text-align: center; font-size: 0.85rem;">{appreciation}</td>
                        <td style="border: 1px solid #000; padding: 4px 6px; text-align: center; font-size: 0.85rem;"></td>
                    </tr>
                """

      lignes_html += f"""
                <tr>
                    <td style="border: 1px solid #000; padding: 4px 6px; text-align: left; font-size: 0.85rem; font-weight: bold;">Conduite</td>
                    <td style="border: 1px solid #000; padding: 4px 6px; text-align: center; font-size: 0.85rem;">18.00</td>
                    <td style="border: 1px solid #000; padding: 4px 6px; text-align: center; font-size: 0.85rem;">18.00</td>
                    <td style="border: 1px solid #000; padding: 4px 6px; text-align: center; font-size: 0.85rem;">1</td>
                    <td style="border: 1px solid #000; padding: 4px 6px; text-align: center; font-size: 0.85rem;">18.00</td>
                    <td style="border: 1px solid #000; padding: 4px 6px; text-align: center; font-size: 0.85rem;">{rang_eleve}</td>
                    <td style="border: 1px solid #000; padding: 4px 6px; text-align: center; font-size: 0.85rem;">Bien</td>
                    <td style="border: 1px solid #000; padding: 4px 6px; text-align: center; font-size: 0.85rem;"></td>
                </tr>
            """
      total_coef += 1
      total_moyen_coef += 18.0

      recap_annuel_html = ""
      if "2" in semestre:
        recap_annuel_html = f"""
                <div style="border: 1px solid #000; background-color: #1E293B; color: #FFFFFF; padding: 6px; text-align: center; font-size: 0.85rem; margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-around; font-weight: bold;">
                        <span>Moyenne S1 : <b>{moy_s1_eleve:.2f} / 20</b></span>
                        <span>Moyenne Actuelle : <b>{moy_eleve:.2f} / 20</b></span>
                        <span style="color: #38BDF8;">Moyenne Annuelle : <b>{moy_annuelle_eleve:.2f} / 20</b> (Rang : {rang_annuel})</span>
                    </div>
                </div>
                """

      verification_url = f"https://api.whatsapp.com/send?phone=22799797163&text=Bonjour,%20je%20souhaite%20verifier%20l'authenticite%20du%20bulletin%20de%20l'eleve%20{getattr(eleve_obj, 'nom', '')}%20{getattr(eleve_obj, 'prenom', '')}%20(Matricule:%20{getattr(eleve_obj, 'matricule', 'N/A')})."
      qr_code_api = f"https://api.qrserver.com/v1/create-qr-code/?size=100x100&data={verification_url}"

      bulletin_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    @media print {{
                        .no-print {{ display: none !important; }}
                        body {{ background: #FFFFFF; margin: 0; }}
                        .bulletin-container {{ border: none !important; margin: 0 !important; width: 100% !important; }}
                        .bulletin-page {{ page-break-after: always; }} 
                    }}
                    body {{ background: #f0f2f5; font-family: Arial, sans-serif; }}
                    .bulletin-container {{ border: 2px solid #000; padding: 15px; background-color: #FFFFFF; color: #000000; max-width: 820px; margin: 0 auto 20px auto; box-sizing: border-box; }}
                </style>
            </head>
            <body>
                <div class="no-print" style="max-width: 820px; margin: 0 auto 15px auto; text-align: right;">
                    <button onclick="window.print();" style="background-color: #D97706; color: white; border: none; padding: 10px 20px; font-weight: bold; font-size: 0.95rem; border-radius: 6px; cursor: pointer; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">🖨️ Imprimer / PDF</button>
                </div>

                <div class="bulletin-container bulletin-page">
                    <div style="border: 1px solid #000; padding: 8px; margin-bottom: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div style="text-align: left; width: 38%; font-size: 0.7rem; font-weight: bold; line-height: 1.2;">
                                REPUBLIQUE DU NIGER<br>
                                MINISTERE DE L'EDUCATION NATIONALE<br>
                                {nom_ecole}<br>
                                <span style="font-size: 0.65rem; font-weight: normal; font-style: italic;">{devise_ecole}</span>
                            </div>
                            <div style="text-align: center; width: 24%;">
                                <img src="{qr_code_api}" style="width: 65px; height: 65px; display: block; margin: 0 auto;" alt="QR Code" />
                            </div>
                            <div style="text-align: right; width: 38%;">
                                {logo_img_tag}
                            </div>
                        </div>
                    </div>

                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #000; padding-bottom: 5px; margin-bottom: 8px; font-size: 0.85rem;">
                        <div style="font-weight: bold;">{nom_ecole}</div>
                        <div style="text-align: center;">
                            <b>BULLETIN : {semestre.upper()}</b><br>
                            <span style="font-size: 0.80rem;">Année Scolaire : 2026-2027</span>
                        </div>
                        <div></div>
                    </div>

                    <div style="display: flex; justify-content: space-between; border: 1px solid #000; padding: 6px 10px; margin-bottom: 8px; font-size: 0.85rem; background: #FAFAFA;">
                        <div style="line-height: 1.4;">
                            <b>Nom et Prénom :</b> {getattr(eleve_obj, 'nom', '')} {getattr(eleve_obj, 'prenom', '')}<br>
                            <b>Matricule :</b> {getattr(eleve_obj, 'matricule', 'N/A')}<br>
                            <b>Moyenne :</b> {moy_eleve:.2f}<br>
                            <b>Rang :</b> {rang_eleve}
                        </div>
                        <div style="line-height: 1.4;">
                            <b>Classe :</b> {classe_choisie}<br>
                            <b>Effectif :</b> {effectif}<br>
                            <b>Garçons :</b> {garcons}<br>
                            <b>Filles :</b> {filles}
                        </div>
                    </div>

                    <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-bottom: 8px;">
                        <thead>
                            <tr style="background-color: #7F1D1D; color: #FFFFFF; text-align: center;">
                                <th style="border: 1px solid #000; padding: 5px;">Matières</th>
                                <th style="border: 1px solid #000; padding: 5px;">NoteClasse/20</th>
                                <th style="border: 1px solid #000; padding: 5px;">NoteCompo/20</th>
                                <th style="border: 1px solid #000; padding: 5px;">Coef</th>
                                <th style="border: 1px solid #000; padding: 5px;">MoyenCoef</th>
                                <th style="border: 1px solid #000; padding: 5px;">Rang</th>
                                <th style="border: 1px solid #000; padding: 5px;">Appréciation</th>
                                <th style="border: 1px solid #000; padding: 5px;">Signature</th>
                            </tr>
                        </thead>
                        <tbody>
                            {lignes_html}
                        </tbody>
                    </table>

                    <div style="border: 1px solid #000; background-color: #0F172A; color: #FFFFFF; padding: 6px; text-align: center; font-size: 0.85rem; margin-bottom: 8px;">
                        <div style="display: flex; justify-content: space-around; font-weight: bold;">
                            <span>Total de la période</span>
                            <span>{total_coef}</span>
                            <span>{total_moyen_coef:.2f} sur {total_coef * 20}</span>
                        </div>
                        <div style="display: flex; justify-content: space-around; margin-top: 3px; font-weight: bold; border-top: 1px solid #334155; padding-top: 3px;">
                            <span>Moyenne Périodique</span>
                            <span style="color: #FBBF24;">{moy_eleve:.2f} sur 20</span>
                        </div>
                    </div>

                    {recap_annuel_html}

                    <div style="display: grid; grid-template-columns: 1.4fr 1.2fr 1.3fr 1fr; border: 1px solid #000; font-size: 0.75rem; margin-bottom: 10px; background: #FFFFFF;">
                        <div style="border-right: 1px solid #000; padding: 6px; line-height: 1.4;">
                            <b style="text-decoration: underline; display: block; text-align: center; margin-bottom: 4px;">Travail de la Classe</b>
                            Conduite de la classe : 18.00<br>
                            Moyenne de la classe : {moy_classe_val:.2f}<br>
                            Plus Forte Moyenne : {max_moy_val:.2f}<br>
                            Plus Faible Moyenne : {min_moy_val:.2f}<br>
                            Nombre de Moyenne : {sum(1 for v in vals_moyennes if v >= 10)}
                        </div>
                        <div style="border-right: 1px solid #000; padding: 6px; line-height: 1.4;">
                            <b style="text-decoration: underline; display: block; text-align: center; margin-bottom: 4px;">Conduite</b>
                            ☒ Bien<br>☐ Passable<br>☐ Mal<br>☐ Avertissement<br>☐ Blame
                        </div>
                        <div style="border-right: 1px solid #000; padding: 6px; line-height: 1.4;">
                            <b style="text-decoration: underline; display: block; text-align: center; margin-bottom: 4px;">Tableau d'honneur</b>
                            ☒ Inscrit(e)<br>☐ Félicitations<br>☐ Encouragement<br>☐ Non Inscrit(e)
                        </div>
                        <div style="padding: 6px; text-align: center; line-height: 1.4;">
                            <b style="text-decoration: underline; display: block; margin-bottom: 4px;">Assiduité-Retard</b>
                            <br><br>
                            <span style="color: red; font-weight: bold; font-size: 0.9rem;">R - A - S</span>
                        </div>
                    </div>

                    <div style="display: flex; justify-content: space-between; margin-top: 15px; font-size: 0.85rem;">
                        <div style="text-align: center; width: 40%;">
                            <b>Le Directeur / Censeur</b><br><br><br><br>
                            _________________________________
                        </div>
                        <div style="text-align: center; width: 40%;">
                            <b>Appréciation des Parents</b><br><br><br><br>
                            _________________________________
                        </div>
                    </div>

                    <div style="text-align: center; margin-top: 15px; font-size: 0.7rem; border-top: 1px solid #000; padding-top: 4px; font-weight: bold;">
                        {adresse_ecole}<br>
                        {contacts_ecole} — Service de Vérification & Authentification
                    </div>
                </div>
            </body>
            </html>
            """
      return bulletin_html

    if portee == "Élève unique" and eleve_id_selectionne:
      eleve_s = db.query(Eleve).filter(Eleve.id == eleve_id_selectionne).first()
      if eleve_s:
        html_rendu = rendre_bulletin(eleve_s)
        st.markdown(
            f"📞 *Contacts de vérification :*"
            f" `{contacts_ecole.replace('TEL : ', '')}`"
        )
        components.html(html_rendu, height=1050, scrolling=True)
    elif portee == "Toute la classe":
      st.markdown("<br>", unsafe_allow_html=True)
      st.info(
          "💡 **Impression de classe entière** : Faites défiler vers le bas."
          " Les sauts de page sont automatiquement configurés pour l'impression"
          " (Ctrl+P)."
      )
      for eleve_item in eleves:
        html_rendu = rendre_bulletin(eleve_item)
        components.html(html_rendu, height=1050, scrolling=True)

  finally:
    db.close()


# Alias de compatibilité
afficher_bulletin = afficher_bulletins
afficher_generation_bulletins = afficher_bulletins