import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import datetime
import pandas as pd
import altair as alt

# ---------------------------------------------------------
# 1. KONFIGURACE APLIKACE
# ---------------------------------------------------------
st.set_page_config(
    page_title="Smart Nutri Pro",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Načtení klíče
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception:
    st.error("⚠️ Chybí API klíč v Secrets!")
    st.stop()

# Model s JSON konfigurací
generation_config = {
    "temperature": 0.4,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 2048,
    "response_mime_type": "application/json",
}

try:
    model = genai.GenerativeModel("gemini-1.5-flash", generation_config=generation_config)
except:
    model = genai.GenerativeModel("gemini-flash-latest")

if 'food_history' not in st.session_state:
    st.session_state.food_history = []

# ---------------------------------------------------------
# 2. PROFIL & CÍLE (Sidebar)
# ---------------------------------------------------------
with st.sidebar:
    st.header("👤 Nastavení těla")
    gender = st.radio("Pohlaví", ["Muž", "Žena"], horizontal=True)
    weight = st.number_input("Váha (kg)", 40, 200, 80)
    height = st.number_input("Výška (cm)", 100, 230, 180)
    age = st.number_input("Věk", 10, 100, 25)
    
    activity_map = {"Sedadavá": 1.2, "Lehká": 1.375, "Střední": 1.55, "Vysoká": 1.725}
    activity = st.selectbox("Aktivita", list(activity_map.keys()))
    
    goal_map = {"Hubnout": -500, "Udržovat": 0, "Nabírat": 300}
    goal = st.selectbox("Cíl", list(goal_map.keys()))

    # Výpočet BMR
    if gender == "Muž":
        bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
    else:
        bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
    
    target_kcal = (bmr * activity_map[activity]) + goal_map[goal]
    
    # Cíle maker
    t_prot = (target_kcal * 0.30) / 4
    t_carbs = (target_kcal * 0.35) / 4
    t_fats = (target_kcal * 0.35) / 9

# ---------------------------------------------------------
# 3. DASHBOARD (GRAFY A ČÍSLA)
# ---------------------------------------------------------
st.title("🔥 Smart Nutri Pro")

# Součty
if st.session_state.food_history:
    df = pd.DataFrame(st.session_state.food_history)
    c_cal = df['Kalorie'].sum()
    c_prot = df['Bílkoviny'].sum()
    c_carbs = df['Sacharidy'].sum()
    c_fats = df['Tuky'].sum()
else:
    c_cal = c_prot = c_carbs = c_fats = 0

# Hlavní metriky
k1, k2, k3, k4 = st.columns(4)
k1.metric("🔥 Kalorie", f"{int(c_cal)}", f"Cíl: {int(target_kcal)}")
k2.metric("🥩 Bílkoviny", f"{int(c_prot)} g", f"Cíl: {int(t_prot)}")
k3.metric("🍚 Sacharidy", f"{int(c_carbs)} g", f"Cíl: {int(t_carbs)}")
k4.metric("🥑 Tuky", f"{int(c_fats)} g", f"Cíl: {int(t_fats)}")

# Progress Bar
prog = min(c_cal / target_kcal, 1.0) if target_kcal > 0 else 0
st.progress(prog)

# --- GRAF: Donut Chart (Poměr živin) ---
if c_cal > 0:
    source = pd.DataFrame({
        "Kategorie": ["Bílkoviny", "Sacharidy", "Tuky"],
        "Hodnota": [c_prot, c_carbs, c_fats]
    })
    
    base = alt.Chart(source).encode(
        theta=alt.Theta("Hodnota", stack=True)
    )
    
    pie = base.mark_arc(outerRadius=120, innerRadius=80).encode(
        color=alt.Color("Kategorie"),
        tooltip=["Kategorie", "Hodnota"]
    )
    
    text = base.mark_text(radius=140).encode(
        text="Hodnota",
        order=alt.Order("Hodnota", sort="descending"),
        color=alt.value("white")  
    )
    
    st.altair_chart(pie + text, use_container_width=True)

st.divider()

# ---------------------------------------------------------
# 4. SKENER A AI TRENÉR
# ---------------------------------------------------------
c_left, c_right = st.columns([1, 1.5])

with c_left:
    st.subheader("📸 Nové jídlo")
    foto = st.camera_input("Vyfoť talíř")

with c_right:
    if foto:
        img = Image.open(foto)
        st.image(img, width=200)
        
        with st.spinner('🔍 AI zkoumá složení a hledá rady...'):
            prompt = """
            Analyzuj jídlo. Vrať JSON:
            {
                "nazev": "Jídlo (česky)",
                "kalorie": int (kcal),
                "bilkoviny": int (g),
                "sacharidy": int (g),
                "tuky": int (g),
                "sul": float (g),
                "tip": "Krátká, úderná rada nutričního trenéra k tomuto jídlu (max 1 věta)."
            }
            Pokud nevíš, dej 0.
            """
            try:
                response = model.generate_content([prompt, img])
                data = json.loads(response.text)
                
                st.success(f"**{data['nazev']}**")
                st.info(f"💡 **AI Tip:** {data['tip']}")
                
                c_d1, c_d2, c_d3, c_d4 = st.columns(4)
                c_d1.write(f"🔥 {data['kalorie']}")
                c_d2.write(f"🥩 {data['bilkoviny']}")
                c_d3.write(f"🍚 {data['sacharidy']}")
                c_d4.write(f"🧂 {data['sul']}g sůl")
                
                if st.button("✅ Snědl jsem to", type="primary"):
                    rec = {
                        "Čas": datetime.datetime.now().strftime("%H:%M"),
                        "Jídlo": data['nazev'],
                        "Kalorie": data['kalorie'],
                        "Bílkoviny": data['bilkoviny'],
                        "Sacharidy": data['sacharidy'],
                        "Tuky": data['tuky'],
                        "Sůl": data['sul'],
                        "Tip AI": data['tip']
                    }
                    st.session_state.food_history.append(rec)
                    st.rerun()
                    
            except:
                st.error("Chyba. Zkus vyfotit lépe.")

# ---------------------------------------------------------
# 5. DENNÍ REPORT & EXPORT
# ---------------------------------------------------------
st.divider()
st.subheader("📝 Dnešní přehled")

if st.session_state.food_history:
    df_export = pd.DataFrame(st.session_state.food_history)
    st.dataframe(df_export, use_container_width=True)
    
    # Tlačítko pro stažení dat (aby se neztratila)
    csv = df_export.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="💾 Stáhnout jídelníček (CSV)",
        data=csv,
        file_name='mujjidelnicek.csv',
        mime='text/csv',
    )
