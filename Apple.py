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
st.set_page_config(page_title="Body Architect Pro", page_icon="💪", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #121212; }
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding-top: 1rem; padding-bottom: 3rem;}
    .dashboard-card {
        background-color: #1E1E1E; border-radius: 15px; padding: 15px;
        margin-bottom: 10px; border: 1px solid #333; text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .card-title { color: #AAAAAA; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }
    .card-value { color: #FFFFFF; font-size: 28px; font-weight: bold; }
    .card-sub { color: #4CAF50; font-size: 14px; }
    .stButton>button { border-radius: 20px; background-color: #2E2E2E; color: white; border: 1px solid #444; font-weight: bold; }
    .stButton>button:hover { border-color: #4CAF50; color: #4CAF50; }
    .stProgress > div > div > div > div { background-color: #4CAF50; }
    </style>
""", unsafe_allow_html=True)

# --- API KLÍČ A MODEL ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
    # Nový model podle e-mailu od Googlu
    model = genai.GenerativeModel("gemini-3.1-pro-preview", generation_config={"response_mime_type": "application/json"})
except Exception as e:
    st.error(f"⚠️ CHYBÍ API KLÍČ V SECRETS! Ujisti se, že máš soubor .streamlit/secrets.toml. Chyba: {e}")
    st.stop()

# ==============================================================================
# 2. FILE MANAGEMENT (Bezpečnější zápis)
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
    return {"weight": 80.0, "height": 184, "age": 14, "gender": "Muž", "goal": "Body Recomp", "activity": 1.55}

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
    st.title("🔐 Login")
    u = st.selectbox("Kdo jsi?", load_users())
    if st.button("Vstoupit", type="primary"):
        st.session_state.user = u
        st.query_params["user"] = u
        st.rerun()
    
    st.divider()
    new = st.text_input("Nový uživatel")
    if st.button("Vytvořit") and add_user(new):
        st.success("OK")
        st.rerun()
    st.stop()

# ==============================================================================
# 4. HLAVNÍ LOGIKA
# ==============================================================================
user = st.session_state.user
files = get_filenames(user)
profile = load_profile(files["profile"])
today = datetime.date.today().strftime("%Y-%m-%d")

with st.sidebar:
    st.title(f"👤 {user}")
    st.caption("Tvůj odkaz: " + f"?user={user}")
    if st.button("Odhlásit"): 
        st.session_state.user = None
        st.query_params.clear()
        st.rerun()
    
    st.divider()
    with st.expander("⚙️ Nastavení"):
        w = st.number_input("Váha", 0.0, 200.0, float(profile.get("weight", 80.0)))
        
        goal_options = ["Body Recomp", "Objem", "Hubnutí"]
        current_goal = profile.get("goal", "Body Recomp")
        goal_index = goal_options.index(current_goal) if current_goal in goal_options else 0
        goal = st.selectbox("Cíl", goal_options, index=goal_index)
        
        if st.button("Uložit"):
            profile.update({"weight": w, "goal": goal})
            save_profile(profile, files["profile"])
            st.rerun()

    bmr = (10 * profile["weight"]) + (6.25 * profile.get("height", 184)) - (5 * profile.get("age", 14)) + 5
    tdee = bmr * profile.get("activity", 1.55)
    if "Recomp" in profile["goal"]: t_cal = int(tdee+100)
    elif "Objem" in profile["goal"]: t_cal = int(tdee+300)
    else: t_cal = int(tdee-400)

df_food = load_csv(files["food"])
df_water = load_csv(files["water"])
df_weight = load_csv(files["weight"])

c_cal = df_food[df_food["Datum"]==today]["Kalorie"].sum() if not df_food.empty else 0
c_water = df_water[df_water["Datum"]==today]["Objem"].sum() if not df_water.empty else 0
last_weight = df_weight.iloc[-1]["Vaha"] if not df_weight.empty else profile["weight"]

if 'burned' not in st.session_state: st.session_state.burned = 0

# ==============================================================================
# 5. DASHBOARD 
# ==============================================================================
c_date, c_prog = st.columns([1, 2])
c_date.markdown(f"**📅 {today}**")
prog_val = min(c_cal / t_cal, 1.0) if t_cal > 0 else 0
c_prog.progress(prog_val)

col1, col2 = st.columns(2)

with col1:
    st.markdown(f"""
    <div class="dashboard-card">
        <div class="card-title">🍽️ PŘÍJEM</div>
        <div class="card-value">{int(c_cal)}</div>
        <div class="card-sub">z {t_cal} kcal</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    with st.container():
        st.markdown(f"""
        <div class="dashboard-card" style="padding-bottom: 5px;">
            <div class="card-title">🔥 POHYB</div>
            <div class="card-value">{st.session_state.burned}</div>
            <div class="card-sub">kcal spáleno</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("➕ Aktivita (+50)", key="btn_burn"):
            st.session_state.burned += 50
            st.rerun()

with col1:
    st.markdown(f"""
    <div class="dashboard-card">
        <div class="card-title">💧 VODA</div>
        <div class="card-value">{float(c_water)/1000:.1f}</div>
        <div class="card-sub">litrů</div>
    </div>
    """, unsafe_allow_html=True)
    cw1, cw2 = st.columns(2)
    if cw1.button("+0.25l", key="w250"):
        new_w = pd.DataFrame([{"Datum": today, "Objem": 250}])
        df_water = pd.concat([df_water, new_w], ignore_index=True) if not df_water.empty else new_w
        save_csv(df_water, files["water"])
        st.rerun()
    if cw2.button("+0.5l", key="w500"):
        new_w = pd.DataFrame([{"Datum": today, "Objem": 500}])
        df_water = pd.concat([df_water, new_w], ignore_index=True) if not df_water.empty else new_w
        save_csv(df_water, files["water"])
        st.rerun()

with col2:
    st.markdown(f"""
    <div class="dashboard-card">
        <div class="card-title">⚖️ VÁHA</div>
        <div class="card-value">{last_weight}</div>
        <div class="card-sub">kg</div>
    </div>
    """, unsafe_allow_html=True)
        
    w_input = st.number_input("Nová váha:", 0.0, 150.0, float(last_weight), label_visibility="collapsed", key="w_inp_dash")
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
    if st.button("🚀 Analyzovat FOTO", type="primary", key="ana_cam"):
        with st.spinner("Gemini 3.1 analyzuje..."):
            try:
                prompt = "Analyzuj jídlo na fotce. Vrať striktně čistý JSON bez markdownu a formátování: {\"nazev\": \"Nazev\", \"kalorie\": 0, \"bilkoviny\": 0, \"sacharidy\": 0, \"tuky\": 0}"
                res = model.generate_content([prompt, Image.open(cam)])
                d = clean_json_response(res.text)
                
                rec = pd.DataFrame([{"Datum": today, "Čas": datetime.datetime.now().strftime("%H:%M"), "Jídlo": d['nazev'], "Kalorie": d['kalorie'], "Bílkoviny": d['bilkoviny'], "Sacharidy": d['sacharidy'], "Tuky": d['tuky']}])
                df_food = pd.concat([df_food, rec], ignore_index=True) if not df_food.empty else rec
                save_csv(df_food, files["food"])
                st.success(f"Přidáno: {d['nazev']}")
                st.rerun()
            except Exception as e: 
                st.error(f"Chyba při čtení dat z AI: {e}")

with st.expander("✍️ Nebo zapsat textem"):
    txt = st.text_input("Co jsi jedl?")
    if st.button("Zapsat"):
         with st.spinner("Gemini 3.1 analyzuje..."):
            try:
                res = model.generate_content(f"Analyzuj toto jídlo: '{txt}'. Vrať striktně čistý JSON bez formátování: {{\"nazev\": \"Nazev\", \"kalorie\": 0, \"bilkoviny\": 0, \"sacharidy\": 0, \"tuky\": 0}}")
                d = clean_json_response(res.text)
                
                rec = pd.DataFrame([{"Datum": today, "Čas": datetime.datetime.now().strftime("%H:%M"), "Jídlo": d['nazev'], "Kalorie": d['kalorie'], "Bílkoviny": d['bilkoviny'], "Sacharidy": d['sacharidy'], "Tuky": d['tuky']}])
                df_food = pd.concat([df_food, rec], ignore_index=True) if not df_food.empty else rec
                save_csv(df_food, files["food"])
                st.success(f"Přidáno: {d['nazev']}")
                st.rerun()
            except Exception as e: 
                st.error(f"Chyba při čtení dat z AI: {e}")

# ==============================================================================
# 7. HISTORIE & MAKRA
# ==============================================================================
st.subheader("📊 Denní Makra")
if not df_food.empty:
    df_t = df_food[df_food["Datum"]==today]
    if not df_t.empty:
        m1, m2, m3 = st.columns(3)
        m1.metric("Bílkoviny", f"{int(df_t['Bílkoviny'].sum())}g")
        m2.metric("Sacharidy", f"{int(df_t['Sacharidy'].sum())}g")
        m3.metric("Tuky", f"{int(df_t['Tuky'].sum())}g")
        
        st.dataframe(df_t[["Čas", "Jídlo", "Kalorie"]].iloc[::-1], use_container_width=True, hide_index=True)
        
        if st.button("🗑️ Smazat poslední jídlo z dneška"):
            df_food = df_food.drop(df_food[df_food['Datum'] == today].index[-1])
            save_csv(df_food, files["food"])
            st.rerun()
