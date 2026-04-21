"""
Aldar Conversational Analytics — Slick Minimalist BI Dashboard
-------------------------------------------------------------
LLM Interpreted • Python Verified • Bilingual (EN/AR)
"""

import json
import os
import urllib.error
import urllib.request
from datetime import datetime

import matplotlib.pyplot as plt
import streamlit as st

st.set_page_config(
    page_title="Aldar Conversational Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

API_BASE = "http://127.0.0.1:9000"

# ── Session State ──────────────────────────────────────────────────────────────
if "lang" not in st.session_state:
    st.session_state.lang = "en"
if "question" not in st.session_state:
    st.session_state.question = ""
if "response" not in st.session_state:
    st.session_state.response = None
if "api_status" not in st.session_state:
    st.session_state.api_status = None
if "stats" not in st.session_state:
    st.session_state.stats = None

# ── Bilingual Dictionary ───────────────────────────────────────────────────────
T = {
    "en": {
        "title": "Aldar Conversational Analytics",
        "subtitle": "AI-powered smart grid insights with deterministic verification.",
        "verified": "✓ Python Verified",
        "dataset": "Dataset Workspace",
        "upload_label": "Upload CSV",
        "upload_note": "Backend upload coming next. Reading from data/.",
        "quick_insights": "Quick Insights",
        "ask_label": "Chat / Query",
        "ask_placeholder": "e.g. What was the average load for North_District from 2026-03-08 to 2026-03-14?",
        "ask_btn": "Ask",
        "clear_btn": "Clear",
        "hint": "Try: \"show me the average consumption this month and plot it\"",
        "metrics_title": "Network Overview",
        "m_total_rows": "Total Records",
        "m_avg_load": "Avg Load (kWh)",
        "m_avg_gen": "Avg Gen (kWh)",
        "m_top_asset": "Top Maint. Asset",
        "chart_title_default": "Network Load vs Generation",
        "verif_trace": "Verification Trace",
        "raw_json": "Raw JSON",
        "no_data": "No data found.",
        "error": "Error:",
        "api_offline": "API is offline.",
        "enter_q": "Please enter a question.",
        "analyzing": "Analyzing…",
        "p_llm": "Groq LLM",
        "p_regex": "Regex",
    },
    "ar": {
        "title": "تحليلات الدار الحوارية",
        "subtitle": "رؤى الشبكة الذكية المدعومة بالذكاء الاصطناعي مع تحقق حتمي.",
        "verified": "✓ تحقق عبر بايثون",
        "dataset": "مساحة عمل البيانات",
        "upload_label": "تحميل ملف CSV",
        "upload_note": "دعم التحميل قادم. يقرأ من data/.",
        "quick_insights": "رؤى سريعة",
        "ask_label": "الدردشة / الاستعلام",
        "ask_placeholder": "مثال: ما هو متوسط الحمل في المنطقة الشمالية من 2026-03-08 إلى 2026-03-14؟",
        "ask_btn": "اسأل",
        "clear_btn": "مسح",
        "hint": "جرب: \"أظهر لي متوسط الاستهلاك هذا الشهر وارسمه بيانيًا\"",
        "metrics_title": "نظرة عامة على الشبكة",
        "m_total_rows": "إجمالي السجلات",
        "m_avg_load": "متوسط الحمل",
        "m_avg_gen": "متوسط التوليد",
        "m_top_asset": "أكثر الأصول صيانة",
        "chart_title_default": "حمل الشبكة مقابل التوليد",
        "verif_trace": "مسار التحقق",
        "raw_json": "البيانات الخام",
        "no_data": "لا توجد بيانات.",
        "error": "خطأ:",
        "api_offline": "الخادم غير متصل.",
        "enter_q": "الرجاء كتابة سؤال.",
        "analyzing": "جاري التحليل…",
        "p_llm": "Groq LLM",
        "p_regex": "Regex",
    }
}

# ── CSS (Slick Minimalist) ─────────────────────────────────────────────────────
def inject_css(lang):
    direction = "rtl" if lang == "ar" else "ltr"
    align = "right" if lang == "ar" else "left"
    
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Tajawal:wght@300;400;500;700&display=swap');

    html, body, [class*="css"] {{ 
        font-family: { "'Tajawal', sans-serif" if lang == 'ar' else "'Inter', sans-serif" };
        background-color: #FAFAFA;
        color: #111827;
        direction: {direction};
        text-align: {align};
    }}
    
    /* Hide Streamlit elements */
    #MainMenu {{visibility: hidden;}}
    header {{visibility: hidden;}}
    footer {{visibility: hidden;}}

    .stApp {{ background-color: #FAFAFA; }}

    /* ── Minimalist Cards ── */
    .min-card {{
        background-color: #FFFFFF;
        border: 1px solid #EEEEEE;
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: none;
    }}
    
    /* Logo Card specifically */
    .logo-card {{
        background-color: #FFFFFF;
        border: 1px solid #EEEEEE;
        border-radius: 8px;
        padding: 1.2rem;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 1.5rem;
        max-width: 180px;
    }}
    .logo-card img {{
        max-height: 40px;
        object-fit: contain;
    }}

    /* ── Typography ── */
    .h-title {{ font-size: 1.8rem; font-weight: 600; color: #111827; margin: 0 0 0.3rem 0; letter-spacing: -0.5px; }}
    .h-sub {{ font-size: 0.95rem; color: #6B7280; margin: 0 0 1rem 0; font-weight: 400; }}
    .sec-label {{ font-size: 0.8rem; font-weight: 600; color: #4B5563; text-transform: uppercase; letter-spacing: 1px; margin: 1.5rem 0 0.8rem 0; }}
    
    /* ── Metric Grid ── */
    .metric-box {{
        background-color: #FFFFFF;
        border: 1px solid #EEEEEE;
        border-radius: 8px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        text-align: {align};
    }}
    .metric-lbl {{ font-size: 0.75rem; color: #6B7280; text-transform: uppercase; margin-bottom: 0.4rem; font-weight: 500; }}
    .metric-val {{ font-size: 1.8rem; font-weight: 600; color: #111827; line-height: 1.1; }}
    .metric-sub {{ font-size: 0.75rem; color: #9CA3AF; margin-top: 0.4rem; }}

    /* ── Chat Bubble ── */
    .chat-bubble {{
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        font-size: 0.95rem;
        line-height: 1.6;
        color: #374151;
    }}
    .chat-hint {{
        background-color: #F9FAFB;
        border: 1px solid #F3F4F6;
        border-radius: 6px;
        padding: 0.8rem 1rem;
        font-size: 0.85rem;
        color: #6B7280;
        margin-top: 1rem;
    }}

    /* ── Chips ── */
    .stButton > button {{
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 6px;
        color: #4B5563;
        font-size: 0.8rem;
        padding: 0.4rem 0.8rem;
        transition: all 0.2s;
        box-shadow: none;
    }}
    .stButton > button:hover {{
        background-color: #F9FAFB;
        border-color: #D1D5DB;
        color: #111827;
    }}
    .btn-primary > button {{
        background-color: #111827;
        color: #FFFFFF;
        border: none;
    }}
    .btn-primary > button:hover {{
        background-color: #374151;
        color: #FFFFFF;
    }}
    </style>
    """, unsafe_allow_html=True)

# ── API Calls ──────────────────────────────────────────────────────────────────
def call_ask(question: str):
    payload = json.dumps({"question": question}).encode()
    req = urllib.request.Request(
        f"{API_BASE}/ask", data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())
    except Exception as ex:
        return 0, {"detail": str(ex)}

def check_api():
    try:
        with urllib.request.urlopen(f"{API_BASE}/health", timeout=3) as r:
            return r.status == 200, json.loads(r.read())
    except Exception:
        return False, {}

def get_stats():
    try:
        with urllib.request.urlopen(f"{API_BASE}/stats", timeout=5) as r:
            if r.status == 200: return json.loads(r.read())
    except Exception: pass
    return None

# ── Helpers ────────────────────────────────────────────────────────────────────
def _mpl_fig(h=4.5):
    fig, ax = plt.subplots(figsize=(8, h))
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")
    ax.tick_params(colors="#6B7280", labelsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#E5E7EB')
    ax.spines['bottom'].set_color('#E5E7EB')
    ax.grid(axis="y", color="#F3F4F6", linestyle="-", linewidth=1)
    return fig, ax

def render_logo():
    logo_path = os.path.join(os.path.dirname(__file__), "assets", "aldar_logo.png")
    if os.path.exists(logo_path):
        import base64
        with open(logo_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        st.markdown(f'<div class="logo-card"><img src="data:image/png;base64,{b64}"></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="logo-card"><h3 style="margin:0; letter-spacing:2px; font-weight:700;">ALDAR</h3></div>', unsafe_allow_html=True)

# ── State Initialization ───────────────────────────────────────────────────────
if st.session_state.api_status is None:
    st.session_state.api_status = check_api()
if st.session_state.stats is None:
    st.session_state.stats = get_stats()

api_ok, api_health = st.session_state.api_status
t = T[st.session_state.lang]
inject_css(st.session_state.lang)

# ── Header Toggle ──────────────────────────────────────────────────────────────
st.markdown("<div style='display:flex; justify-content:flex-end; gap:8px;'>", unsafe_allow_html=True)
c_sp, c_en, c_ar = st.columns([10, 1, 1])
with c_en:
    if st.button("EN", use_container_width=True):
        st.session_state.lang = "en"
        st.rerun()
with c_ar:
    if st.button("عربي", use_container_width=True):
        st.session_state.lang = "ar"
        st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

# ── Layout: 50/50 Split ────────────────────────────────────────────────────────
# In RTL mode, CSS `direction: rtl` naturally flips flex items. 
# We maintain Python's [1, 1] order regardless of language.
col_act, col_ins = st.columns([1, 1], gap="large")

# ══════════════════════════════════════════════════════════════════════
# ACTION ZONE (Left Column)
# ══════════════════════════════════════════════════════════════════════
with col_act:
    render_logo()
    st.markdown(f"""
        <h1 class="h-title">{t['title']}</h1>
        <p class="h-sub">{t['subtitle']} <span style="color:#10B981; font-weight:500; font-size:0.8rem; margin-left:8px;">{t['verified']}</span></p>
    """, unsafe_allow_html=True)
    
    # Dataset uploader (Clean)
    st.markdown(f'<div class="sec-label">{t["dataset"]}</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader(t["upload_label"], type=["csv"], label_visibility="collapsed")
    if uploaded:
        st.markdown(f'<div style="font-size:0.8rem; color:#6B7280;">📄 {uploaded.name} — {t["upload_note"]}</div>', unsafe_allow_html=True)

    # Quick Insights Chips
    st.markdown(f'<div class="sec-label">{t["quick_insights"]}</div>', unsafe_allow_html=True)
    
    if st.session_state.lang == "en":
        CHIPS = [
            ("Network Average Load", "What was the average load for North_District from 2026-03-08 to 2026-03-14?"),
            ("Analyze March Peaks", "Identify the hour on 2026-03-12 where generation peaked"),
            ("Maintenance Ranking", "Which assets had the highest number of maintenance hours from 2026-03-01 to 2026-03-31?"),
            ("Peak vs Off-Peak", "Compare generation in Central_Hub between peak hours and off-peak from 2026-03-01 to 2026-03-31")
        ]
    else:
        CHIPS = [
            ("متوسط حمل الشبكة", "ما هو متوسط الحمل في المنطقة الشمالية من 2026-03-08 إلى 2026-03-14؟"),
            ("تحليل ذروة مارس", "حدد الساعة التي بلغت فيها التوليد ذروتها يوم 2026-03-12"),
            ("ترتيب الصيانة", "ما الأصول التي سجلت أعلى عدد من ساعات الصيانة من 2026-03-01 إلى 2026-03-31؟"),
            ("الذروة مقابل غير الذروة", "قارن التوليد في المركز الرئيسي بين ساعات الذروة وغير الذروة في مارس")
        ]
    
    chip_cols = st.columns(len(CHIPS))
    for i, (lbl, q) in enumerate(CHIPS):
        with chip_cols[i]:
            if st.button(lbl, key=f"chip_{i}", use_container_width=True):
                st.session_state.question = q
                st.rerun()

    # Chat Interface
    st.markdown(f'<div class="sec-label" style="margin-top:2rem;">{t["ask_label"]}</div>', unsafe_allow_html=True)
    
    question = st.text_area(
        "Q", value=st.session_state.question, height=100, 
        placeholder=t["ask_placeholder"], label_visibility="collapsed"
    )

    btn_c1, btn_c2, _ = st.columns([2, 2, 4])
    if st.session_state.lang == "ar": btn_c1, btn_c2 = btn_c2, btn_c1
    
    with btn_c1:
        st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
        ask_clicked = st.button(t["ask_btn"], use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with btn_c2:
        if st.button(t["clear_btn"], use_container_width=True):
            st.session_state.question = ""
            st.session_state.response = None
            st.rerun()

    st.markdown(f'<div style="font-size:0.75rem; color:#9CA3AF; margin-top:0.6rem;">{t["hint"]}</div>', unsafe_allow_html=True)

    # API Request Execution
    if ask_clicked:
        if not question.strip():
            st.warning(t["enter_q"])
        elif not api_ok:
            st.error(t["api_offline"])
        else:
            with st.spinner(t["analyzing"]):
                status, data = call_ask(question.strip())
            st.session_state.response = (status, data)
            st.session_state.question = question.strip()

    # Render Chat Bubble Answer
    if st.session_state.response:
        status, data = st.session_state.response
        if status in (200, 201):
            intent = data.get("interpreted_query", {}).get("intent", "")
            ans = data.get("answer", {})
            iq = data.get("interpreted_query", {})
            
            human_text = ""
            chart_hint = ""
            
            if intent == "average_load":
                avg = ans.get("average_load_kwh", 0)
                reg_lbl = ans.get("region") or iq.get("region") or "All Regions"
                if st.session_state.lang == "en":
                    human_text = f"During the selected period ({iq.get('start_date')} to {iq.get('end_date')}), the network average load for **{reg_lbl}** reached **{avg} kWh**."
                    chart_hint = "The chart on the right visualizes the exact value, with detailed tracking if timeseries data was requested."
                else:
                    human_text = f"خلال الفترة المحددة ({iq.get('start_date')} إلى {iq.get('end_date')})، بلغ متوسط حمل الشبكة في **{reg_lbl}** **{avg} كيلوواط/ساعة**."
                    chart_hint = "يوضح الرسم البياني على اليسار القيمة الدقيقة للمتوسط المطلوب."
                    
            elif intent == "peak_generation":
                ts = ans.get("timestamp", "").replace("T", " ")
                gen = ans.get("generation_kwh", 0)
                if st.session_state.lang == "en":
                    human_text = f"The highest generation was observed on **{ts}**, peaking at **{gen} kWh**. This was recorded by asset **{ans.get('asset_id')}**."
                    chart_hint = "The bar chart compares this peak generation hour against the system load recorded at the exact same time."
                else:
                    human_text = f"أعلى توليد تم رصده كان يوم **{ts}**، حيث بلغ الذروة بـ **{gen} كيلوواط/ساعة** بواسطة الأصل **{ans.get('asset_id')}**."
                    chart_hint = "يقارن الرسم البياني ساعة ذروة التوليد هذه مع حمل النظام المسجل في نفس الوقت."
                    
            elif intent == "maintenance_ranking":
                ranked = ans.get("ranked_assets", [])
                if ranked:
                    if st.session_state.lang == "en":
                        human_text = f"The asset with the most maintenance activity was **{ranked[0]['asset_id']}**, accumulating **{ranked[0]['maintenance_hours']} hours** of scheduled downtime."
                        chart_hint = "The adjacent horizontal chart displays the distribution of maintenance hours across the most affected assets."
                    else:
                        human_text = f"الأصل الأكثر خضوعًا للصيانة كان **{ranked[0]['asset_id']}**، بإجمالي **{ranked[0]['maintenance_hours']} ساعة**."
                        chart_hint = "يعرض الرسم البياني الأفقي المجاور توزيع ساعات الصيانة عبر الأصول."
                        
            elif intent == "peak_vs_offpeak":
                diff = ans.get("difference_kwh", 0)
                if st.session_state.lang == "en":
                    human_text = f"Generation during peak hours was higher by **{diff} kWh** compared to off-peak periods in **{ans.get('region')}**."
                    chart_hint = "The side-by-side comparison chart illustrates the exact averages for peak and off-peak generation."
                else:
                    human_text = f"كان التوليد خلال ساعات الذروة أعلى بـ **{diff} كيلوواط/ساعة** مقارنة بأوقات غير الذروة."
                    chart_hint = "يوضح الرسم البياني المقارن المتوسطات الدقيقة."

            # Output Chat Bubble
            st.markdown(f"""
            <div class="chat-bubble">
                <div style="font-weight:600; margin-bottom:0.8rem; color:#111827;">Analysis Result</div>
                {human_text}
                <div class="chat-hint">🔍 <strong>Context:</strong> {chart_hint}</div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander(t["verif_trace"]):
                st.markdown(f"<div style='font-size:0.85rem;color:#6B7280;'>{data.get('explanation', '')}</div>", unsafe_allow_html=True)
            with st.expander(t["raw_json"]):
                st.json(data)

# ══════════════════════════════════════════════════════════════════════
# INSIGHT ZONE (Right Column)
# ══════════════════════════════════════════════════════════════════════
with col_ins:
    st.markdown(f'<div class="sec-label" style="margin-top:0;">{t["metrics_title"]}</div>', unsafe_allow_html=True)
    
    if st.session_state.stats:
        s = st.session_state.stats
        
        # 2x2 Metric Grid
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            st.markdown(f'<div class="metric-box"><div class="metric-lbl">{t["m_total_rows"]}</div><div class="metric-val">{s["total_rows"]:,}</div><div class="metric-sub">Active Records</div></div>', unsafe_allow_html=True)
        with r1c2:
            st.markdown(f'<div class="metric-box"><div class="metric-lbl">{t["m_avg_load"]}</div><div class="metric-val" style="color:#2563EB;">{s["avg_load_kwh"]:,}</div><div class="metric-sub">Network Baseline</div></div>', unsafe_allow_html=True)
            
        r2c1, r2c2 = st.columns(2)
        with r2c1:
            st.markdown(f'<div class="metric-box"><div class="metric-lbl">{t["m_avg_gen"]}</div><div class="metric-val" style="color:#059669;">{s["avg_generation_kwh"]:,}</div><div class="metric-sub">Generation Avg</div></div>', unsafe_allow_html=True)
        with r2c2:
            ma = s["top_maintenance_asset"] or "None"
            st.markdown(f'<div class="metric-box"><div class="metric-lbl">{t["m_top_asset"]}</div><div class="metric-val" style="color:#D97706;">{ma}</div><div class="metric-sub">{s["top_maintenance_hours"]} hours logged</div></div>', unsafe_allow_html=True)

        # Main Chart Area
        st.markdown(f'<div class="sec-label" style="margin-top:2rem;">Visualization</div>', unsafe_allow_html=True)
        
        if st.session_state.response and st.session_state.response[0] in (200, 201):
            # Dynamic Chart based on Query
            data = st.session_state.response[1]
            intent = data.get("interpreted_query", {}).get("intent", "")
            ans = data.get("answer", {})
            
            st.markdown('<div class="min-card" style="padding:1rem;">', unsafe_allow_html=True)
            
            if intent == "average_load":
                avg = ans.get("average_load_kwh", 0)
                ts = data.get("timeseries", [])
                fig, ax = _mpl_fig(4)
                if data.get("chart_requested", False) and ts:
                    import matplotlib.dates as mdates
                    from datetime import datetime
                    times = [datetime.fromisoformat(p["timestamp"]) for p in ts]
                    loads = [p["load_kwh"] for p in ts]
                    ax.plot(times, loads, color="#2563EB", linewidth=1.5)
                    ax.fill_between(times, loads, alpha=0.05, color="#2563EB")
                    ax.axhline(avg, color="#D97706", linewidth=1, linestyle="--")
                    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
                    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
                    plt.xticks(rotation=0, ha="center")
                    ax.set_title("Load Timeseries", color="#111827", fontsize=10, pad=12, loc="left", fontweight="bold")
                else:
                    ax.bar(["Average Load"], [avg], color="#2563EB", width=0.3)
                    ax.set_xlim(-0.5, 0.5)
                    ax.set_title("Average Load", color="#111827", fontsize=10, pad=12, loc="left", fontweight="bold")
                st.pyplot(fig); plt.close(fig)
                
            elif intent == "peak_generation":
                gen = ans.get("generation_kwh", 0)
                load = ans.get("load_kwh", 0)
                fig, ax = _mpl_fig(4)
                ax.bar(["Generation", "Load"], [gen, load], color=["#059669", "#2563EB"], width=0.4)
                ax.set_title("Peak Generation vs Load", color="#111827", fontsize=10, pad=12, loc="left", fontweight="bold")
                st.pyplot(fig); plt.close(fig)
                
            elif intent == "maintenance_ranking":
                ranked = ans.get("ranked_assets", [])
                fig, ax = _mpl_fig(4)
                if ranked:
                    assets = [r["asset_id"] for r in ranked[:5]]
                    hours = [r["maintenance_hours"] for r in ranked[:5]]
                    ax.barh(assets[::-1], hours[::-1], color="#6B7280", height=0.5)
                    ax.set_title("Top 5 Maintenance Assets", color="#111827", fontsize=10, pad=12, loc="left", fontweight="bold")
                st.pyplot(fig); plt.close(fig)
                
            elif intent == "peak_vs_offpeak":
                fig, ax = _mpl_fig(4)
                ax.bar(["Peak Avg", "Off-Peak Avg"], [ans.get('peak_avg_generation_kwh',0), ans.get('offpeak_avg_generation_kwh',0)], color=["#7C3AED", "#2563EB"], width=0.4)
                ax.set_title("Generation Comparison", color="#111827", fontsize=10, pad=12, loc="left", fontweight="bold")
                st.pyplot(fig); plt.close(fig)

            st.markdown('</div>', unsafe_allow_html=True)
            
        else:
            # Default Empty State Chart
            st.markdown('<div class="min-card" style="padding:1rem;">', unsafe_allow_html=True)
            fig, ax = _mpl_fig(4)
            ax.bar(["Avg Load", "Avg Gen"], [s["avg_load_kwh"], s["avg_generation_kwh"]], color=["#2563EB", "#059669"], width=0.4)
            ax.set_title(t["chart_title_default"], color="#111827", fontsize=10, pad=12, loc="left", fontweight="bold")
            st.pyplot(fig); plt.close(fig)
            st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.warning("Stats endpoint unavailable. Ensure backend is running.")
