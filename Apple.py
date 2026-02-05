import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# Nastavení vzhledu aplikace
st.set_page_config(page_title="AI Calorie Tracker", page_icon="🥗")

st.title("🥗 Můj Nutriční Tracker")
st.write("Vyfoť jídlo a AI spočítá zbytek.")

# API Klíč - už ho tam máš, tak ho jen nech v uvozovkách
API_KEY = "AIzaSyBVO_JlXa0oJ4PzR-3QrEF_eJxh9vqIk3I"
genai.configure(api_key=API_KEY)

# Dynamický výběr modelu pro eliminaci chyby 404
try:
    # Gemini 2.0 Flash je nejnovější a nejrychlejší
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
except:
    # Záložní plán pro starší verze knihovny
    model = genai.GenerativeModel('gemini-1.5-flash-latest')

# Foťák přímo v aplikaci
foto = st.camera_input("Vyfotit jídlo")

if foto:
    img = Image.open(foto)
    st.image(img, caption='Analyzuji...', use_container_width=True)
    
    with st.spinner('Počítám makra a sůl...'):
        prompt = """
        Jsi špičkový nutriční specialista. Analyzuj tuto fotku jídla.
        Vytvoř tabulku: Potravina | Hmotnost | Energie (kcal) | Bílkoviny | Sacharidy | Cukry | Tuky | Sůl | Vláknina.
        Na konci přidej tučný řádek CELKEM.
        Důležité: Buď velmi přesný v odhadu soli. Odpovídej česky.
        """
        
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG')
        img_data = img_byte_arr.getvalue()
        
        try:
            # Odeslání dat do modelu
            response = model.generate_content([
                prompt,
                {'mime_type': 'image/jpeg', 'data': img_data}
            ])
            st.markdown("### 📊 Výsledek analýzy")
            st.markdown(response.text)
        except Exception as e:
            st.error(f"Chyba při analýze: {e}")

st.divider()
st.caption("Běží na Gemini 2.0/1.5 | Minimalistický & Výkonný design")
