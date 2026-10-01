import streamlit as st

def get_header_html():
    """Retourne le HTML de l'en-tête."""
    return """
    <div style="text-align: center; border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 20px; font-family: Arial, sans-serif;">
        <h1 style="margin: 0; font-size: 24px;">COMPLEXE SCOLAIRE PRIVÉ RAHMAT-FH</h1>
        <p style="font-style: italic; font-weight: bold; margin: 5px 0;">"Excellence, Discipline et Travail"</p>
    </div>
    """

def afficher_en_tete_impression():
    st.markdown(get_header_html(), unsafe_allow_html=True)