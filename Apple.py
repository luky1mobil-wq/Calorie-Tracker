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
st.set_page_config(page_title="NutriApp Ultimate", page_icon="🔥", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #121212; }
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding-top: 1rem; padding-bottom: 3rem;}
    .stButton>button { border-radius: 12px; background-color: #2E2E2E; color: white; border: 1px solid #444; font-weight: bold; width: 100%; }
    .stButton>button:hover { border-color: #4CAF50; color: #4CAF50; }
    .stProgress > div > div > div > div { background-color: #4CAF50; }
    .streak-box { background-color: #FF9800; color: #121212; padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 14px; display: inline-block; }
    .stDataFrame { font-size: 14px; }
    </style>
""", unsafe_allow_html=True)

# Nastavení přesného českého času (UTC + 1 hodina)
now_cz = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
today = now_cz.strftime("%Y-%m-%d")
current_time_str = now_cz.strftime("%H:%M")

def draw_donut(val, total, color, label, unit=""):
    if total <= 0: total = 1
    pct = min(int((val / total) * 100), 100)
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

def get_meal_category():
    hour = now_cz.hour
    if 5 <= hour < 10: return "Snídaně"
    elif 10 <= hour < 14: return "Oběd"
    elif 14 <= hour < 18: return "Svačina"
    else: return "Večeře"

# --- API KLÍČ A MODEL ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel("gemini-flash-latest", generation_config={"response_mime_type": "application/json"})
    text_model = genai.GenerativeModel("gemini-flash-latest")
except Exception as e:
    st.error(f"CHYBÍ API KLÍČ V SECRETS! Chyba: {e}")
    st.stop()

# ==============================================================================
# 2. FILE MANAGEMENT
# ==============================================================================
USERS_FILE = "users_list.json"

def get_filenames(user):
    c = str(user).strip().replace(" ", "_")
    return {"food": f"data_{c}_food.csv", "weight": f"data_{c}_weight.csv", "profile": f"data_{c}_profile.json", "water": f"data_{c}_water.csv"}

def load_csv(f): 
    try: 
        df = pd.read_csv(f)
        if "Kategorie" not in df.columns and not df.empty: df["Kategorie"] = "Ostatní"
        return df
    except: return pd.DataFrame()

def save_csv(df, f): 
    df.to_csv(f, index=False)

def load_profile(f):
    if os.path.exists(f):
        try:
            with open(f, "r", encoding="utf-8") as file: return json.load(file)
        except: pass
    return {"weight": 80.0, "goal_weight": 80.0, "height": 184, "age": 14, "gender": "Muž", "goal": "Body Recomp", "activity": 1.55}

def save_profile(data, f):
    with open(f, "w", encoding="utf-8") as file: json.dump(data, file)

def clean_json(text):
    start, end = text.find('{'), text.rfind('}')
    if start != -1 and end != -1: return json.loads(text[start:end+1])
    raise ValueError("JSON nenalezen.")

def calc_streak(df_f):
    if df_f.empty: return 0
    dates = sorted(df_f['Datum'].unique(), reverse=True)
    today_str = today
    yesterday_str = (now_cz - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    
    streak = 0
    current_check = today_str
    
    if dates and dates[0] != today_str:
        if dates[0] == yesterday_str: current_check = yesterday_str
        else: return 0

    for d in dates:
        if d == current_check:
            streak += 1
            current_check = (datetime.datetime.strptime(d, "%Y-%m-%d") - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        else: break
    return streak

# ==============================================================================
# 3. AUTO-LOGIN & SETUP
# ==============================================================================
qp = st.query_params
if 'user' not in st.session_state: st.session_state.user = qp.get("user", None)

if not st.session_state.user:
    st.title("Login")
    users = ["Lukáš"] if not os.path.exists(USERS_FILE) else json.load(open(USERS_FILE, "r", encoding="utf-8"))
    u = st.selectbox("Kdo jsi?", users)
    if st.button("Vstoupit"):
        st.session_state.user = u
        if "user" not in st.query_params or st.query_params["user"] != u:
            st.query_params["user"] = u
        st.rerun()
    st.stop()

user = st.session_state.user
files = get_filenames(user)
profile = load_profile(files["profile"])

with st.sidebar:
    st.title(f"{user}")
    if st.button("Odhlásit"): st.session_state.user = None; st.query_params.clear(); st.rerun()
    st.divider()
    with st.expander("Nastavení & Cíle"):
        w = st.number_input("Aktuální váha (kg)", 0.0, 200.0, float(profile.get("weight", 80.0)))
        gw = st.number_input("Cílová váha (kg)", 0.0, 200.0, float(profile.get("goal_weight", w)))
        g_opts = ["Body Recomp", "Objem", "Hubnutí"]
        g_idx = g_opts.index(profile.get("goal", "Body Recomp")) if profile.get("goal") in g_opts else 0
        goal = st.selectbox("Směr", g_opts, index=g_idx)
        if st.button("Uložit profil"):
            profile.update({"weight": w, "goal_weight": gw, "goal": goal})
            save_profile(profile, files["profile"])
            st.rerun()

    # VÝPOČTY
    bmr = (10 * profile["weight"]) + (6.25 * profile.get("height", 184)) - (5 * profile.get("age", 14)) + 5
    tdee = bmr * profile.get("activity", 1.55)
    
    if "Recomp" in profile["goal"]: t_cal = int(tdee + 100); t_prot = int(profile["weight"] * 2.2)
    elif "Objem" in profile["goal"]: t_cal = int(tdee + 300); t_prot = int(profile["weight"] * 2.0)
    else: t_cal = int(tdee - 400); t_prot = int(profile["weight"] * 2.2)

    t_fat = int(profile["weight"] * 1.0) 
    t_carb = int(max((t_cal - (t_prot * 4) - (t_fat * 9)) / 4, 0))
    t_water = int(profile["weight"] * 30)
    t_burn = 500 

df_food = load_csv(files["food"])
df_water = load_csv(files["water"])
df_weight = load_csv(files["weight"])

streak_count = calc_streak(df_food)
df_t = df_food[df_food["Datum"]==today] if not df_food.empty else pd.DataFrame()
c_cal = df_t["Kalorie"].sum() if not df_t.empty else 0
c_prot = df_t['Bílkoviny'].sum() if not df_t.empty else 0
c_carb = df_t['Sacharidy'].sum() if not df_t.empty else 0
c_fat = df_t['Tuky'].sum() if not df_t.empty else 0
c_water = df_water[df_water["Datum"]==today]["Objem"].sum() if not df_water.empty else 0
last_weight = df_weight.iloc[-1]["Vaha"] if not df_weight.empty else profile["weight"]

if 'burned' not in st.session_state: st.session_state.burned = 0

# ==============================================================================
# 4. TABS: DNEŠEK | TRENDY | HISTORIE
# ==============================================================================
tab_dnes, tab_trendy, tab_hist = st.tabs(["🏠 Dnešek", "📈 Trendy", "📜 Historie"])

# ----------------- TAB 1: DNEŠEK -----------------
with tab_dnes:
    c_hlavicka1, c_hlavicka2 = st.columns([1, 1])
    c_hlavicka1.markdown(f"### 📅 {today}")
    c_hlavicka2.markdown(f"<div style='text-align: right;'><span class='streak-box'>🔥 Jedeš {streak_count} dní!</span></div>", unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(draw_donut(c_cal, t_cal, "#4CAF50", "PŘÍJEM", "kcal"), unsafe_allow_html=True)
    with c2:
        st.markdown(draw_donut(st.session_state.burned, t_burn, "#FF9800", "POHYB", "kcal"), unsafe_allow_html=True)
        if st.button("🔥 +50", key="b1"): st.session_state.burned += 50; st.rerun()
    with c3:
        st.markdown(draw_donut(c_water, t_water, "#2196F3", "VODA", "ml"), unsafe_allow_html=True)
        if st.button("💧 +250", key="w1"):
            df_water = pd.concat([df_water, pd.DataFrame([{"Datum": today, "Objem": 250}])], ignore_index=True)
            save_csv(df_water, files["water"]); st.rerun()
    with c4:
        st.markdown(draw_donut(last_weight, profile.get("goal_weight", last_weight), "#9C27B0", "VÁHA", "kg"), unsafe_allow_html=True)
        w_in = st.number_input("Váha", 0.0, 150.0, float(last_weight), label_visibility="collapsed")
        if st.button("💾", key="w_s"):
            if not df_weight.empty: df_weight = df_weight[df_weight["Datum"] != today]
            df_weight = pd.concat([df_weight, pd.DataFrame([{"Datum": today, "Vaha": w_in}])], ignore_index=True)
            save_csv(df_weight, files["weight"]); profile["weight"] = w_in; save_profile(profile, files["profile"]); st.rerun()

    st.divider()
    
    # ZADÁVÁNÍ FOTEK
    st.subheader("📸 Přidat jídlo")
    st.caption("💡 TIP: Pro lepší ostrost a zoom vyfoť věci normálně foťákem v mobilu a sem je rovnou nahraj.")
    
    tab_galerie, tab_kamera = st.tabs(["📂 Nahrát z Galerie", "📷 Vyfotit rovnou"])
    
    with tab_galerie:
        uploaded_files = st.file_uploader("Vyber fotky (jídlo + tabulka s hodnotami)", accept_multiple_files=True, type=['jpg','png','jpeg','webp','heic','heif'], key="file_up_galerie")
        if uploaded_files:
            images = []
            c_imgs = st.columns(len(uploaded_files[:2])) 
            for i, f in enumerate(uploaded_files[:2]):
                img = Image.open(f)
                c_imgs[i].image(img, width=150)
                images.append(img)
                
            e_info1 = st.text_input("Doplňující info k fotkám:", key="e_cam1")
            if st.button("🚀 Analyzovat FOTO z Galerie", type="primary", key="btn_galerie"):
                with st.spinner("AI analyzuje..."):
                    try:
                        prompt = f"Analyzuj jídlo na fotkách. Pokud je jedna z fotek nutriční tabulka, řiď se primárně podle ní! Zohledni info od uživatele: '{e_info1}'. Vrať striktně čistý JSON: {{\"nazev\": \"Nazev\", \"kalorie\": 0, \"bilkoviny\": 0, \"sacharidy\": 0, \"tuky\": 0}}"
                        res = model.generate_content([prompt] + images)
                        d = clean_json(res.text)
                        
                        rec = pd.DataFrame([{"Datum": today, "Čas": current_time_str, "Kategorie": get_meal_category(), "Jídlo": d['nazev'], "Kalorie": d['kalorie'], "Bílkoviny": d['bilkoviny'], "Sacharidy": d['sacharidy'], "Tuky": d['tuky']}])
                        df_food = pd.concat([df_food, rec], ignore_index=True); save_csv(df_food, files["food"]); st.rerun()
                    except Exception as e: st.error(f"CHYBA: {e}")

    with tab_kamera:
        cam_in = st.camera_input("Rychlá fotka", key="cam_direct")
        if cam_in:
            st.image(cam_in, width=150)
            e_info2 = st.text_input("Doplňující info:", key="e_cam2")
            if st.button("🚀 Analyzovat FOTO", type="primary", key="btn_kamera"):
                with st.spinner("AI analyzuje..."):
                    try:
                        prompt = f"Analyzuj jídlo. Info: '{e_info2}'. Čistý JSON: {{\"nazev\": \"N\", \"kalorie\": 0, \"bilkoviny\": 0, \"sacharidy\": 0, \"tuky\": 0}}"
                        res = model.generate_content([prompt, Image.open(cam_in)])
                        d = clean_json(res.text)
                        
                        rec = pd.DataFrame([{"Datum": today, "Čas": current_time_str, "Kategorie": get_meal_category(), "Jídlo": d['nazev'], "Kalorie": d['kalorie'], "Bílkoviny": d['bilkoviny'], "Sacharidy": d['sacharidy'], "Tuky": d['tuky']}])
                        df_food = pd.concat([df_food, rec], ignore_index=True); save_csv(df_food, files["food"]); st.rerun()
                    except Exception as e: st.error(f"CHYBA: {e}")

    with st.expander("✍️ Zapsat pouze textem"):
        txt = st.text_input("Co jsi jedl?")
        if st.button("Zapsat text", key="btn_text"):
            with st.spinner("AI počítá..."):
                try:
                    d = clean_json(model.generate_content(f"Analyzuj: '{txt}'. Čistý JSON: {{\"nazev\": \"N\", \"kalorie\": 0, \"bilkoviny\": 0, \"sacharidy\": 0, \"tuky\": 0}}").text)
                    rec = pd.DataFrame([{"Datum": today, "Čas": current_time_str, "Kategorie": get_meal_category(), "Jídlo": d['nazev'], "Kalorie": d['kalorie'], "Bílkoviny": d['bilkoviny'], "Sacharidy": d['sacharidy'], "Tuky": d['tuky']}])
                    df_food = pd.concat([df_food, rec], ignore_index=True); save_csv(df_food, files["food"]); st.rerun()
                except Exception as e: st.error(f"CHYBA: {e}")

    # MAKRA A KATEGORIE
    st.divider()
    m1, m2, m3 = st.columns(3)
    with m1: st.markdown(draw_donut(c_prot, t_prot, "#2196F3", "BÍLKOVINY", "g"), unsafe_allow_html=True) 
    with m2: st.markdown(draw_donut(c_carb, t_carb, "#FFC107", "SACHARIDY", "g"), unsafe_allow_html=True) 
    with m3: st.markdown(draw_donut(c_fat, t_fat, "#F44336", "TUKY", "g"), unsafe_allow_html=True) 
    
    if not df_t.empty:
        st.write("### Dnešní jídla")
        for kat in ["Snídaně", "Oběd", "Svačina", "Večeře", "Ostatní"]:
            df_k = df_t[df_t.get("Kategorie", "Ostatní") == kat]
            if not df_k.empty:
                st.markdown(f"**{kat}** ({df_k['Kalorie'].sum()} kcal)")
                st.dataframe(df_k[["Čas", "Jídlo", "Kalorie", "Bílkoviny", "Sacharidy", "Tuky"]], use_container_width=True, hide_index=True)
        
        if st.button("🗑️ Smazat poslední záznam z dneška", key="del_last_safe"):
            todays_indices = df_food[df_food['Datum'] == today].index
            if len(todays_indices) > 0:
                df_food = df_food.drop(todays_indices[-1])
                save_csv(df_food, files["food"])
                st.rerun()

    # VYLEPŠENÝ AI TRENÉR S ČASEM
    st.divider()
    if st.button("🤖 AI Trenér - Zhodnotit makra a poradit jídlo", type="primary"):
        with st.spinner("Trenér píše..."):
            meal_cat = get_meal_category()
            prompt = f"Jsem uživatel, cíl: {profile['goal']}. Aktuálně mám snězeno {c_cal}/{t_cal} kcal a bílkoviny {c_prot}/{t_prot}g. Právě teď je {current_time_str} hodin ({meal_cat}). Napiš mi stručné, úderné zhodnocení (max 2 věty). Vzhledem k tomu, že je {current_time_str}, dej mi JEDEN konkrétní tip na to, co si mám teď dát za jídlo, abych se vešel do maker. Odpovídej česky, stručně, narovinu a jako trenér, nepoučuj mě."
            odpoved = text_model.generate_content(prompt).text
            st.info(odpoved)

# ----------------- TAB 2: TRENDY -----------------
with tab_trendy:
    st.subheader("Vývoj váhy")
    if not df_weight.empty and len(df_weight) > 1:
        c_w = alt.Chart(df_weight).mark_line(point=True, color="#9C27B0").encode(x='Datum', y=alt.Y('Vaha', scale=alt.Scale(zero=False)))
        st.altair_chart(c_w, use_container_width=True)
    else: st.write("Zatím málo dat o váze.")
    
    st.subheader("Příjem Kalorií (poslední dny)")
    if not df_food.empty:
        df_cal_trend = df_food.groupby('Datum')['Kalorie'].sum().reset_index()
        c_c = alt.Chart(df_cal_trend.tail(14)).mark_bar(color="#4CAF50").encode(x='Datum', y='Kalorie')
        st.altair_chart(c_c, use_container_width=True)

# ----------------- TAB 3: HISTORIE -----------------
with tab_hist:
    st.subheader("Kompletní záznamy")
    if not df_food.empty: st.dataframe(df_food.iloc[::-1], use_container_width=True, hide_index=True)
    else: st.write("Zatím žádná data.")
