import streamlit as st
import google.generativeai as genai
from PIL import Image

st.set_page_config(page_title="Nutri Tracker")
st.title("🥗 Kalorický Tracker")

# Nastavení klíče
genai.configure(api_key="AIzaSyBVO_JlXa0oJ4PzR-3QrEF_eJxh9vqIk3I")

# Použijeme model 1.5-flash, který je nejmíň náchylný na chyby s kvótou
model = genai.GenerativeModel('gemini-1.5-flash')

foto = st.camera_input("Vyfoť jídlo")

if foto:
    img = Image.open(foto)
    st.image(img, use_container_width=True)
    
    with st.spinner('Počítám...'):
        prompt = "Analyzuj fotku a vytvoř tabulku v češtině: Potravina, Hmotnost, Energie (kcal), Bílkoviny, Sacharidy, Cukry, Tuky, Sůl, Vláknina. Na konci dej součet."
        try:
            # Přímé odeslání obrázku
            response = model.generate_content([prompt, img])
            st.markdown(response.text)
        except Exception as e:
            st.error(f"Chyba: {e}")
