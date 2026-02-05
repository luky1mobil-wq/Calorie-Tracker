import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# Nastavení vzhledu aplikace
st.set_page_config(page_title="AI Calorie Tracker", page_icon="🥗")

st.title("🥗 Můj Nutriční Tracker")
st.write("Vyfoť jídlo a Gemini 3 Pro spočítá zbytek.")

# API Klíč
API_KEY = "AIzaSyBVO_JlXa0oJ4PzR-3QrEF_eJxh9vqIk3I"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-3-pro-preview')

# Foťák přímo v aplikaci
foto = st.camera_input("Vyfotit jídlo")

if foto:
    img = Image.open(foto)
    st.image(img, caption='Analyzuji...', use_container_width=True)
    
    with st.spinner('Počítám makra a sůl...'):
        prompt = """
        Jsi expert na výživu. Analyzuj fotku a vytvoř Markdown tabulku:
        Potravina | Hmotnost | Energie (kcal) | Bílkoviny | Sacharidy | Cukry | Tuky | Sůl | Vláknina
        Na konci přidej tučný řádek CELKEM.
        Odpovídej česky.
        """
        
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG')
        img_data = img_byte_arr.getvalue()
        
        try:
            response = model.generate_content([
                prompt,
                {'mime_type': 'image/jpeg', 'data': img_data}
            ])
            st.markdown("### 📊 Výsledek analýzy")
            st.markdown(response.text)
        except Exception as e:
            st.error(f"Chyba: {e}")
