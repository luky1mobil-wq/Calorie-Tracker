import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import datetime
import pandas as pd
import altair as alt
import os
import re

# ==============================================================================
# 1. DESIGN A KONFIGURACE
# ==============================================================================
st.set_page_config(page_title="NutriApp Pro", page_icon="💪", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #121212; }
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding-top: 1rem; padding-bottom: 3rem;}
    .stButton>button { border-radius: 15px; background-color: #2E2E2E; color: white; border: 1px solid #444; font-weight: bold; width: 100%; }
    .stButton>button:hover { border-color: #4CAF50; color: #4CAF50; }
    .stProgress > div > div > div > div { background-color: #4CAF50; }
    </style>
""", unsafe_allow_html=True)

# VYLEPŠENÁ FUNKCE NA KOLEČKA (Přesně jako KT)
def draw_donut(val, total, color, label, unit=""):
    if total <= 0: total = 1
    pct = min(int((val / total) * 100), 100)
    
    # Varování: Překročení kalorií zbarví kolečko do červena
    if label == "PŘÍJEM" and val > total:
        color = "#F44336"
        pct = 100
        
    return f"""
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; margin-bottom: 10px;">
        <div style="width: 110px; height: 110px; border-radius: 50%; background: conic-gradient({color} {pct}%, #333 {pct}%); position: relative; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">
            <div style="position: absolute; width: 90px; height: 90px; background-color: #1E1E1E; border-radius: 50%; display: flex; flex-direction: column; align-items: center; justify-content: center;">
                <span style="font-size: 18px; font-weight: bold; color: white; line-height: 1.2;">{int(val)}</span>
                <span style="color: #AAAAAA; font-size: 11px;">z {int(total)} {unit}</span>
            </div>
        </div>
        <span style="color: #FFFFFF; font-size: 13px; font-weight: bold; margin-top: 12px; text-transform: uppercase; letter-spacing: 1px;">{label}</span>
    </div>
    """

# --- API KLÍČ A MODEL ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel("gemini-flash-latest", generation_config={"response_mime_type": "application/json"})
except Exception as e:
    st.error(f"CHYBÍ API KLÍČ V SECRETS! Chyba: {e}")
    st.stop()

# ==============================================================================
# 2. FILE MANAGEMENT
# ==============================================================================
USERS_FILE = "users_list.json"

def get_filenames(username):
    clean = str(username).strip().replace(" ", "_")
    return {
        "food": f"data_{clean}_food.csv",
        "weight": f"data_{clean}_weight.csv",
        "profile": f"data_{clean}_profile.json",
        "water": f"data_{clean}_water.csv"
    }

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return ["Lukáš"]
    return ["Lukáš"]

def add_user(name):
    users = load_users()
    if name and name not in users:
        users.append(name)
        with open(USERS_FILE, "w", encoding="utf-8") as f: json.dump(users, f)
        return True
    return False

def load_csv(filename): 
    try:
        return pd.read_csv(filename) if os.path.exists(filename) else pd.DataFrame()
    except:
        return pd.DataFrame()

def save_csv(df, filename): 
    if not df.empty:
        df.to_csv(filename, index=False)

def load_profile(filename):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return {"weight": 80.0, "goal_weight": 80.0, "height": 184, "age": 14, "gender": "Muž", "goal": "Body Recomp", "activity": 1.55}

def save_profile(data, filename):
    with open(filename, "w", encoding="utf-8") as f: json.dump(data, f)

def clean_json_response(raw_text):
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(json)?", "", text)
        text = re.sub(r"```$", "", text).strip()
    return json.loads(text)

# ==============================================================================
# 3. AUTO-LOGIN
# ==============================================================================
qp = st.query_params
if 'user' not in st.session_state: 
    st.session_state.user = qp.get("user", None)

if not st.session_state.user:
    st.title("Login")
    u = st.selectbox("Kdo jsi?", load_users())
    if st.button("Vstoupit", type="primary"):
        st.session_state.user = u
        st.query_params["user"] = u
        st.rerun()
    st.stop()

# ==============================================================================
# 4. HLAVNÍ LOGIKA A VÝPOČTY
# ==============================================================================
user = st.session_state.user
files = get_filenames(user)
profile = load_profile(files["profile"])
today = datetime.date.today().strftime("%Y-%m-%d")

with st.sidebar:
    st.title(f"{user}")
    if st.button("Odhlásit"): 
        st.session_state.user = None
        st.query_params.clear()
        st.rerun()
    
    st.divider()
    with st.expander("Nastavení & Cíle"):
        w = st.number_input("Aktuální váha (kg)", 0.0, 200.0, float(profile.get("weight", 80.0)))
        gw = st.number_input("Cílová váha (kg)", 0.0, 200.0, float(profile.get("goal_weight", w)))
        
        goal_options = ["Body Recomp", "Objem", "Hubnutí"]
        current_goal = profile.get("goal", "Body Recomp")
        goal_index = goal_options.index(current_goal) if current_goal in goal_options else 0
        goal = st.selectbox("Směr", goal_options, index=goal_index)
        
        if st.button("Uložit profil"):
            profile.update({"weight": w, "goal_weight": gw, "goal": goal})
            save_profile(profile, files["profile"])
            st.rerun()

    # VÝPOČTY CÍLŮ
    bmr = (10 * profile["weight"]) + (6.25 * profile.get("height", 184)) - (5 * profile.get("age", 14)) + 5
    tdee = bmr * profile.get("activity", 1.55)
    
    if "Recomp" in profile["goal"]: t_cal = int(tdee + 100); t_prot = int(profile["weight"] * 2.2)
    elif "Objem" in profile["goal"]: t_cal = int(tdee + 300); t_prot = int(profile["weight"] * 2.0)
    else: t_cal = int(tdee - 400); t_prot = int(profile["weight"] * 2.2)

    t_fat = int(profile["weight"] * 1.0) 
    t_carb = int(max((t_cal - (t_prot * 4) - (t_fat * 9)) / 4, 0))
    
    # Cíl vody: 30 ml na 1 kg váhy
    t_water = int(profile["weight"] * 30)
    # Cíl pohybu (pro zobrazení v kolečku - zatím pevně 500)
    t_burn = 500 

df_food = load_csv(files["food"])
df_water = load_csv(files["water"])
df_weight = load_csv(files["weight"])

c_cal = df_food[df_food["Datum"]==today]["Kalorie"].sum() if not df_food.empty else 0
c_water = df_water[df_water["Datum"]==today]["Objem"].sum() if not df_water.empty else 0
last_weight = df_weight.iloc[-1]["Vaha"] if not df_weight.empty else profile["weight"]

if 'burned' not in st.session_state: st.session_state.burned = 0

# ==============================================================================
# 5. DASHBOARD (KOLEČKA VŠUDE)
# ==============================================================================
st.markdown(f"### 📅 {today}")

# 4 sloupce pro hlavní metriky
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(draw_donut(c_cal, t_cal, "#4CAF50", "PŘÍJEM", "kcal"), unsafe_allow_html=True)
    
with c2:
    st.markdown(draw_donut(st.session_state.burned, t_burn, "#FF9800", "POHYB", "kcal"), unsafe_allow_html=True)
    if st.button("🔥 +50 kcal"):
        st.session_state.burned += 50
        st.rerun()

with c3:
    st.markdown(draw_donut(c_water, t_water, "#2196F3", "VODA", "ml"), unsafe_allow_html=True)
    w1, w2 = st.columns(2)
    if w1.button("💧 250"):
        new_w = pd.DataFrame([{"Datum": today, "Objem": 250}])
        df_water = pd.concat([df_water, new_w], ignore_index=True) if not df_water.empty else new_w
        save_csv(df_water, files["water"])
        st.rerun()
    if w2.button("💧 500"):
        new_w = pd.DataFrame([{"Datum": today, "Objem": 500}])
        df_water = pd.concat([df_water, new_w], ignore_index=True) if not df_water.empty else new_w
        save_csv(df_water, files["water"])
        st.rerun()

with c4:
    st.markdown(draw_donut(last_weight, profile.get("goal_weight", last_weight), "#9C27B0", "VÁHA", "kg"), unsafe_allow_html=True)
    w_input = st.number_input("Zapsat váhu:", 0.0, 150.0, float(last_weight), label_visibility="collapsed")
    if w_input != last_weight:
        new_row = pd.DataFrame([{"Datum": today, "Vaha": w_input}])
        if not df_weight.empty: df_weight = df_weight[df_weight["Datum"] != today]
        df_weight = pd.concat([df_weight, new_row], ignore_index=True) if not df_weight.empty else new_row
        save_csv(df_weight, files["weight"])
        profile["weight"] = w_input
        save_profile(profile, files["profile"])
        st.rerun()

st.divider()

# ==============================================================================
# 6. PŘIDÁVÁNÍ JÍDLA
# ==============================================================================
st.subheader("📸 Přidat jídlo")

cam = st.camera_input("Vyfoť jídlo", label_visibility="collapsed")
if cam:
    st.image(cam, width=150)
    if st.button("Analyzovat FOTO", type="primary", key="ana_cam"):
        with st.spinner("AI analyzuje..."):
            try:
                prompt = "Analyzuj jídlo na fotce. Vrať striktně čistý JSON: {\"nazev\": \"Nazev\", \"kalorie\": 0, \"bilkoviny\": 0, \"sacharidy\": 0, \"tuky\": 0}"
                res = model.generate_content([prompt, Image.open(cam)])
                d = clean_json_response(res.text)
                
                rec = pd.DataFrame([{"Datum": today, "Čas": datetime.datetime.now().strftime("%H:%M"), "Jídlo": d['nazev'], "Kalorie": d['kalorie'], "Bílkoviny": d['bilkoviny'], "Sacharidy": d['sacharidy'], "Tuky": d['tuky']}])
                df_food = pd.concat([df_food, rec], ignore_index=True) if not df_food.empty else rec
                save_csv(df_food, files["food"])
                st.success(f"Přidáno: {d['nazev']}")
                st.rerun()
            except Exception as e: 
                st.error(f"PŘESNÁ CHYBA: {e}")

with st.expander("✍️ Zapsat textem"):
    txt = st.text_input("Co jsi jedl?")
    if st.button("Zapsat"):
        with st.spinner("AI analyzuje..."):
            try:
                res = model.generate_content(f"Analyzuj: '{txt}'. Vrať čistý JSON: {{\"nazev\": \"Nazev\", \"kalorie\": 0, \"bilkoviny\": 0, \"sacharidy\": 0, \"tuky\": 0}}")
                d = clean_json_response(res.text)
                
                rec = pd.DataFrame([{"Datum": today, "Čas": datetime.datetime.now().strftime("%H:%M"), "Jídlo": d['nazev'], "Kalorie": d['kalorie'], "Bílkoviny": d['bilkoviny'], "Sacharidy": d['sacharidy'], "Tuky": d['tuky']}])
                df_food = pd.concat([df_food, rec], ignore_index=True) if not df_food.empty else rec
                save_csv(df_food, files["food"])
                st.success(f"Přidáno: {d['nazev']}")
                st.rerun()
            except Exception as e: 
                st.error(f"PŘESNÁ CHYBA: {e}")

# ==============================================================================
# 7. MAKRÁ A HISTORIE 
# ==============================================================================
st.subheader("📊 Denní Makra")
df_t = df_food[df_food["Datum"]==today] if not df_food.empty else pd.DataFrame()

c_prot = df_t['Bílkoviny'].sum() if not df_t.empty else 0
c_carb = df_t['Sacharidy'].sum() if not df_t.empty else 0
c_fat = df_t['Tuky'].sum() if not df_t.empty else 0

m1, m2, m3 = st.columns(3)
with m1: st.markdown(draw_donut(c_prot, t_prot, "#2196F3", "BÍLKOVINY", "g"), unsafe_allow_html=True) 
with m2: st.markdown(draw_donut(c_carb, t_carb, "#FFC107", "SACHARIDY", "g"), unsafe_allow_html=True) 
with m3: st.markdown(draw_donut(c_fat, t_fat, "#F44336", "TUKY", "g"), unsafe_allow_html=True) 

if not df_t.empty:
    st.dataframe(df_t[["Čas", "Jídlo", "Kalorie"]].iloc[::-1], use_container_width=True, hide_index=True)
    if st.button("🗑️ Smazat poslední jídlo z dneška"):
        df_food = df_food.drop(df_food[df_food['Datum'] == today].index[-1])
        save_csv(df_food, files["food"])
        st.rerun()
