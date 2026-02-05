import streamlit as st
import google.generativeai as genai
from PIL import Image

# Nastavení stránky
st.set_page_config(page_title="Nutri Tracker", page_icon="🥗")
st.title("🥗 Nutriční Tracker (Gemini 2.0)")

# Tvůj API klíč
API_KEY = "AIzaSyBVO_JlXa0oJ4PzR-3QrEF_eJxh9vqIk3I"
genai.configure(api_key=API_KEY)

# VÍTĚZNÝ MODEL Z DIAGNOSTIKY
# Tohle je ten přesný název ze screenshotu, který bude fungovat
model = genai.GenerativeModel('gemini-2.0-flash')

# Foťák
foto = st.camera_input("Vyfoť jídlo")

if foto:
    img = Image.open(foto)
    st.image(img, caption="Analyzuji...", use_container_width=True)
    
    with st.spinner('Gemini 2.0 počítá kalorie a sůl...'):
        prompt = """
        Jsi nutriční expert. Analyzuj fotku a vytvoř Markdown tabulku:
        Potravina | Hmotnost | Energie (kcal) | Bílkoviny | Tuky | Sacharidy | Cukry | Sůl
        Na konci dej řádek CELKEM.
        Odpovídej česky. Buď maximálně přesný v odhadu soli.
        """
        
        try:
