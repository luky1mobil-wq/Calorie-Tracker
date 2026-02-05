import streamlit as st
import google.generativeai as genai
from PIL import Image

st.set_page_config(page_title="Nutri Tracker", page_icon="🥗")
st.title("🥗 Nutriční Tracker (Gemini 2.0)")

# --- BEZPEČNOSTNÍ POJISTKA ---
# Klíč se načte z Trezoru, takže v kódu není vidět a Google ho nezablokuje.
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception:
    st.error("Chybí klíč v Secrets! Nastav ho v Manage app -> Settings -> Secrets.")

# Používáme model 2.0 Flash, který ti fungoval v diagnostice
model = genai.GenerativeModel('gemini-2.0-flash')

foto = st.camera_input("Vyfoť jídlo")

if foto:
    img = Image.open(foto)
    st.image(img, caption="Analyzuji...", use_container_width=True)
    
    with st.spinner('Počítám kalorie...'):
        prompt = """
        Jsi nutriční expert. Analyzuj fotku a vytvoř Markdown tabulku:
        Potravina | Hmotnost | Energie (kcal) | Bílkoviny | Tuky | Sacharidy | Cukry | Sůl
        Na konci dej řádek CELKEM.
        Odpovídej česky. Buď maximálně přesný v odhadu soli.
        """
        try:
            response = model.generate_content([prompt, img])
            st.markdown("### 📊 Výsledky")
            st.markdown(response.text)
        except Exception as e:
            st.error(f"Chyba: {e}")
            st.error(f"Chyba: {e}")
