import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import datetime
import pandas as pd
import altair as alt
import time

st.set_page_config(
    page_title="Lukášův Nutri Deník",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- KONFIGURACE ---
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("Chybí API klíč v Secrets.")
        st.stop()
except Exception:
    st.error("Chyba konfigurace API.")
    st.stop()

# Výběr modelu
generation_config = {
    "temperature": 0.35,
    "top_p": 0.95,
    "max_output_tokens": 1024,
    "response_mime_type": "application/json",
}

try:
    model = genai.GenerativeModel("gemini-1.5-flash", generation_config=generation_config)
except:
    model = genai.GenerativeModel("gemini-flash-latest", generation_config=generation_config)

if 'food_history' not in st.session_state:
    st.session_state.food_history = []

# --- PROFIL (Hardcoded: 80kg, 184cm, 14 let) ---
with st.sidebar:
    st.header("Nastavení")
    gender = st.radio("Pohlaví", ["Muž", "Žena"], horizontal=True)
    weight = st.number_input("Váha", 40.0, 150.0, 80.0)
    height = st.number_input("Výška", 100, 230, 184)
    age = st.number_input("Věk", 10, 100, 14)
    
    activity_level = st.selectbox("Aktivita", ["Sedadavá", "Lehká", "Střední", "Vysoká", "Extrémní"], index=2)
    goal = st.selectbox("Cíl", ["Hubnout (-500)", "Udržovat", "Nabírat (+500)"], index=2)
    
    act_map = {"Sedadavá": 1.2, "Lehká": 1.375, "Střední": 1.55, "Vysoká": 1.725, "Extrémní": 1.9}
    goal_map = {"Hubnout (-500)": -500, "Udržovat": 0, "Nabírat (+500)": 500}

    # Mifflin-St Jeor
    if gender == "Muž":
        bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
    else:
        bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
    
    target_kcal = int((bmr * act_map[activity_level]) + goal_map[goal])
    t_prot = int((target_kcal * 0.25) / 4)
    t_carbs = int((target_kcal * 0.50) / 4)
    t_fats = int((target_kcal * 0.25) / 9)
    
    if st.button("🗑️ Smazat data"):
        st.session_state.food_history = []
        st.rerun()

# --- DASHBOARD ---
st.title("🧬 Lukášův Nutri Deník")

if st.session_state.food_history:
    df = pd.DataFrame(st.session_state.food_history)
    c_cal = df['Kalorie'].sum()
    c_prot = df['Bílkoviny'].sum()
    c_carbs = df['Sacharidy'].sum()
    c_fats = df['Tuky'].sum()
else:
    c_cal = c_prot = c_carbs = c_fats = 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("🔥 Kalorie", f"{int(c_cal)}", f"{int(target_kcal - c_cal)} zbývá")
col2.metric("🥩 Bílkoviny", f"{int(c_prot)} g", f"{int(t_prot - c_prot)} g")
col3.metric("🍚 Sacharidy", f"{int(c_carbs)} g", f"{int(t_carbs - c_carbs)} g")
col4.metric("🥑 Tuky", f"{int(c_fats)} g", f"{int(t_fats - c_fats)} g")

prog = min(c_cal / target_kcal, 1.0) if target_kcal > 0 else 0
st.progress(prog)

st.divider()

# --- SKENER ---
c_cam, c_res = st.columns([1, 1.5])
with c_cam:
    foto = st.camera_input("Vyfoť jídlo", label_visibility="collapsed")

with c_res:
    if foto:
        img = Image.open(foto)
        st.image(img, width=200)
        
        with st.spinner('Analyzuji...'):
            prompt = """
            Analyzuj jídlo. Vrať JSON:
            {
                "nazev": "string", "kalorie": int, "bilkoviny": int, 
                "sacharidy": int, "tuky": int, "sul": float, 
                "tip": "string (max 1 věta, trenérský tip)"
            }
            Pokud nevíš, dej 0.
            """
            try:
                res = model.generate_content([prompt, img])
                data = json.loads(res.text)
                
                st.markdown(f"### {data['nazev']}")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Kcal", data['kalorie'])
                c2.metric("B", data['bilkoviny'])
                c3.metric("S", data['sacharidy'])
                c4.metric("T", data['tuky'])
                st.info(f"💡 {data['tip']}")
                
                if st.button("✅ Uložit", type="primary"):
                    rec = {
                        "Čas": datetime.datetime.now().strftime("%H:%M"),
                        "Jídlo": data['nazev'],
                        "Kalorie": data['kalorie'],
                        "Bílkoviny": data['bilkoviny'],
                        "Sacharidy": data['sacharidy'],
                        "Tuky": data['tuky'],
                        "Sůl": data.get('sul', 0)
                    }
                    st.session_state.food_history.append(rec)
                    st.rerun()
            except:
                st.error("Chyba analýzy.")

# --- HISTORIE & GRAF ---
st.divider()
if st.session_state.food_history:
    df_h = pd.DataFrame(st.session_state.food_history)
    
    c_g, c_t = st.columns([1, 2])
    with c_g:
        if c_cal > 0:
            src = pd.DataFrame({
                "Kat": ["Bílkoviny", "Sacharidy", "Tuky"],
                "Val": [c_prot*4, c_carbs*4, c_fats*9]
            })
            chart = alt.Chart(src).mark_arc(innerRadius=50).encode(
                theta="Val", color="Kat", tooltip=["Kat", "Val"]
            )
            st.altair_chart(chart, use_container_width=True)
            
    with c_t:
        st.dataframe(df_h[["Čas", "Jídlo", "Kalorie", "Bílkoviny", "Sacharidy", "Tuky"]], use_container_width=True, hide_index=True)
        
        csv = df_h.to_csv(index=False).encode('utf-8')
        st.download_button("💾 Stáhnout CSV", csv, "denik.csv", "text/csv")
