import urllib.parse
import pandas as pd
import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from database.db_config import SessionLocal
from database.models import Eleve, Classe, School

def afficher_communication():
    # --- Injection CSS ---
    st.markdown("""
        <style>
        .comm-card {
            background: linear-gradient(135deg, #00b4db 0%, #0083b0 100%);
            border-radius: 12px;
            padding: 20px;
            color: white;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
            margin-bottom: 25px;
            display: flex;
            align-items: center;
        }
        .comm-card h2 { margin: 0; color: #ffffff; font-weight: 600; font-size: 1.8rem; padding-bottom: 5px; }
        .comm-card p { margin: 0; opacity: 0.9; font-size: 1rem; color: #e2e8f0; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("## 📢 Communication & Diffusion Groupée")
    st.markdown("Envoyez des annonces, rappels de paiement et invitations à tous les parents en quelques clics.")
    st.markdown("---")

    school_id = st.session_state.get("school_id")
    is_super_admin = st.session_state.get("is_super_admin", False)

    if not school_id and not is_super_admin:
        st.warning("⚠️ Veuillez vous connecter pour accéder à cette section.")
        return

    db = SessionLocal()
    try:
        # En-tête
        st.markdown(f"""
            <div class="comm-card">
                <div style="font-size: 3.5rem; margin-right: 25px;">📣</div>
                <div>
                    <h2>Centre de Diffusion</h2>
                    <p>Campagnes WhatsApp et Emailing pour les parents d'élèves.</p>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Récupération des classes de l'école
        classes_ecole = db.query(Classe).filter(Classe.school_id == school_id, Classe.deleted_at.is_(None)).all()
        noms_classes = ["Toute l'école"] + sorted([c.libelle for c in classes_ecole])

        st.markdown("#### 🎯 1. Ciblage de l'audience")
        audience_choisie = st.selectbox("À qui souhaitez-vous envoyer ce message ?", noms_classes)

        # Récupération des élèves/parents ciblés
        query_eleves = db.query(Eleve).filter(Eleve.school_id == school_id, Eleve.deleted_at.is_(None))
        
        if audience_choisie != "Toute l'école":
            classe_obj = next((c for c in classes_ecole if c.libelle == audience_choisie), None)
            if classe_obj:
                query_eleves = query_eleves.filter(Eleve.classe_id == classe_obj.id)
        
        eleves_cibles = query_eleves.all()

        # Extraction et nettoyage des numéros de téléphone
        contacts_valides = []
        for e in eleves_cibles:
            if e.tuteur:
                num = str(e.tuteur).replace(" ", "").replace("+", "")
                if len(num) >= 8:  # Vérification basique de la longueur d'un numéro
                    contacts_valides.append({
                        "Élève": f"{e.nom} {e.prenom}",
                        "Classe": e.classe.libelle if e.classe else "N/D",
                        "Téléphone Parent": num
                    })

        df_contacts = pd.DataFrame(contacts_valides)

        st.info(f"📊 **Audience estimée :** {len(df_contacts)} numéros de téléphone valides trouvés pour '{audience_choisie}'.")

        if len(df_contacts) == 0:
            st.warning("Aucun contact valide trouvé pour cette sélection.")
            return

        st.markdown("#### ✍️ 2. Rédaction du message")
        message_texte = st.text_area(
            "Contenu de votre message", 
            placeholder="Ex: Chers parents, n'oubliez pas la réunion parents-professeurs de ce samedi à 09h00...",
            height=150
        )

        tab_wa, tab_email = st.tabs(["📱 Diffusion WhatsApp", "📧 Diffusion Email"])

        # ==========================================
        # ONGLET WHATSAPP
        # ==========================================
        with tab_wa:
            st.markdown("##### Méthode WhatsApp")
            st.markdown("WhatsApp bloque l'ouverture automatique de centaines d'onglets pour éviter le spam. Vous avez donc **deux options** :")
            
            col_w1, col_w2 = st.columns(2)
            
            with col_w1:
                st.markdown("**Option 1 : Logiciel d'envoi de masse (Recommandé)**")
                st.caption("Si vous utilisez une extension Chrome (ex: WA Sender) ou un logiciel, téléchargez la liste des numéros.")
                if st.download_button(
                    label="📥 Télécharger les numéros (CSV)",
                    data=df_contacts.to_csv(index=False).encode("utf-8"),
                    file_name=f"contacts_whatsapp_{audience_choisie.replace(' ', '_')}.csv",
                    mime="text/csv",
                    type="primary"
                ):
                    st.success("Fichier CSV téléchargé avec succès !")

            with col_w2:
                st.markdown("**Option 2 : Envoi manuel semi-automatisé**")
                st.caption("Cliquez sur chaque lien ci-dessous pour ouvrir WhatsApp Web pré-rempli avec votre message.")
                
                if message_texte.strip():
                    msg_encode = urllib.parse.quote(message_texte)
                    
                    # On affiche les 50 premiers pour ne pas faire planter le navigateur
                    for idx, row in df_contacts.head(50).iterrows():
                        wa_link = f"https://wa.me/{row['Téléphone Parent']}?text={msg_encode}"
                        st.markdown(
                            f"➡️ <a href='{wa_link}' target='_blank'>Envoyer à la famille de {row['Élève']} ({row['Téléphone Parent']})</a>", 
                            unsafe_allow_html=True
                        )
                    if len(df_contacts) > 50:
                        st.caption(f"... et {len(df_contacts) - 50} autres contacts (Utilisez le CSV pour les envois massifs).")
                else:
                    st.warning("Veuillez rédiger un message pour générer les liens.")

        # ==========================================
        # ONGLET EMAIL
        # ==========================================
        with tab_email:
            st.markdown("##### Envoi par Serveur Email (SMTP)")
            st.caption("Cette fonction envoie le message directement dans la boîte mail des parents (si vous avez collecté leurs emails).")
            
            with st.form("form_mass_email"):
                sujet_email = st.text_input("Objet de l'email", value="Information Importante - Direction")
                st.info("ℹ️ Les emails seront envoyés en Copie Cachée (BCC) pour protéger la vie privée des parents.")
                
                submit_email = st.form_submit_button("🚀 Lancer la campagne d'Emailing")
                
                if submit_email:
                    if not message_texte.strip():
                        st.error("Le message est vide !")
                    else:
                        st.warning("Configuration SMTP requise. (Contactez votre administrateur pour lier le compte Gmail de l'école au code python `smtplib`).")
                        # Exemple de logique (désactivée par sécurité tant que SMTP_PASSWORD n'est pas fourni) :
                        # try:
                        #     server = smtplib.SMTP("smtp.gmail.com", 587)
                        #     server.starttls()
                        #     server.login("email_ecole@gmail.com", "MOT_DE_PASSE_APP")
                        #     # ... boucle d'envoi ...
                        #     st.success("Emails envoyés avec succès !")
                        # except Exception as e:
                        #     st.error(f"Erreur d'envoi : {e}")

    finally:
        db.close()

# Alias
afficher_communication_diffusion = afficher_communication