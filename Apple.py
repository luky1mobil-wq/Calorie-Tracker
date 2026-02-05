import streamlit as st
import google.generativeai as genai

st.title("🕵️ Diagnostika Modelů")

# Tvůj klíč
API_KEY = "AIzaSyBVO_JlXa0oJ4PzR-3QrEF_eJxh9vqIk3I"
genai.configure(api_key=API_KEY)

st.write("Zjišťuji dostupné modely pro tvůj API klíč...")

try:
    # Získáme seznam všech modelů, které tvůj klíč vidí
    models = list(genai.list_models())
    
    found_any = False
    for m in models:
        # Hledáme jen ty, co umí generovat obsah (ne embeddingy)
        if 'generateContent' in m.supported_generation_methods:
            st.success(f"✅ NALEZEN: **{m.name}**")
            found_any = True
            
    if not found_any:
        st.error("Žádné použitelné modely nenalezeny. Problém s klíčem?")
        
except Exception as e:
    st.error(f"Kritická chyba: {e}")
    st.info("Tip: Pokud vidíš chybu 'module not found', Streamlit ignoruje tvůj requirements.txt")

st.write("---")
st.caption("Pošli screenshot tohoto seznamu a vybereme ten, který svítí zeleně.")
