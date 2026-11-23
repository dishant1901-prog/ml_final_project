"""HimaRoad + flood-copilot: one app. Run with: streamlit run app.py"""

import streamlit as st

st.set_page_config(
    page_title="HimaRoad Flood Copilot",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="auto",
)

NAVY, TEAL, SAFFRON, ICE, INK, LINE = (
    "#082433",
    "#087F8C",
    "#E47F24",
    "#EAF5F6",
    "#17252D",
    "#D8E2E6",
)
st.markdown(
    f"""<style>
    :root {{ --hr-navy:{NAVY}; --hr-teal:{TEAL}; --hr-orange:{SAFFRON}; --hr-ice:{ICE}; --hr-line:{LINE}; }}
    .stApp {{ background:#F4F7F8; color:{INK}; }}
    .block-container {{ max-width: 1540px; padding-top: 1.25rem; padding-bottom: 3rem; }}
    h1, h2, h3 {{ color:{NAVY}; letter-spacing:-0.025em; }}
    h1 {{ font-size:clamp(1.8rem,3vw,2.45rem) !important; padding-top:.1rem !important; }}
    p, label, [data-testid="stCaptionContainer"] {{ line-height:1.55; }}
    .kicker {{ color:{TEAL}; font-size:.7rem; font-weight:800; letter-spacing:.14em; text-transform:uppercase; margin-bottom:-.45rem; }}
    .band {{ background:{NAVY}; color:#fff; border-radius:14px; padding:15px 20px; margin:0 0 18px;
             display:flex; justify-content:space-between; align-items:center; gap:16px; flex-wrap:wrap;
             box-shadow:0 8px 24px rgba(8,36,51,.12); }}
    .band-main {{ display:flex; align-items:center; gap:12px; }}
    .band-logo {{ width:38px; height:38px; display:grid; place-items:center; border-radius:11px; background:{TEAL}; font-size:1.1rem; }}
    .band b {{ font-size:1.14rem; letter-spacing:-.01em; }}
    .band span {{ display:block; color:#BFD6DD; font-size:.78rem; margin-top:1px; }}
    .band .pill {{ background:rgba(255,255,255,.1); border:1px solid rgba(255,255,255,.18); color:#fff;
                  border-radius:999px; padding:6px 11px; font-size:.68rem; font-weight:800; letter-spacing:.05em; }}
    [data-testid="stMetric"] {{ min-height:108px; background:#fff; border:1px solid {LINE}; border-left:4px solid {TEAL};
                                border-radius:12px; padding:13px 15px; box-shadow:0 1px 2px rgba(8,36,51,.03); }}
    [data-testid="stMetricLabel"] p {{ color:#5D707A; font-size:.75rem; font-weight:700; }}
    [data-testid="stMetricValue"] {{ color:{NAVY}; font-size:1.8rem; font-weight:750; letter-spacing:-.04em; }}
    [data-testid="stExpander"] details {{ background:#fff; border:1px solid {LINE}; border-radius:11px; overflow:hidden; }}
    [data-testid="stExpander"] summary {{ min-height:44px; font-weight:700; color:{NAVY}; }}
    [data-testid="stSidebar"] {{ background:#fff; border-right:1px solid {LINE}; }}
    [data-testid="stSidebar"] [data-testid="stForm"] {{ background:#F7FAFB; border:1px solid {LINE}; border-radius:12px; padding:13px; }}
    [data-testid="stSidebar"] h2 {{ font-size:1.05rem; }}
    [data-testid="stSidebarNav"] {{ background:#fff; border-bottom:1px solid {LINE}; }}
    [data-testid="stSidebarNavLink"] {{ min-height:44px; border-radius:8px; }}
    [data-testid="stSidebarNavLink"][aria-current="page"] {{ background:{ICE}; color:{TEAL}; }}
    .stButton button, .stFormSubmitButton button, .stDownloadButton button {{ min-height:42px; border-radius:9px;
      border:1px solid #9DBFC4; color:{NAVY}; background:#fff; font-weight:700; transition:.15s ease; }}
    .stButton button:hover, .stFormSubmitButton button:hover, .stDownloadButton button:hover {{ background:{TEAL}; border-color:{TEAL}; color:#fff; transform:translateY(-1px); }}
    .stTextInput input, .stNumberInput input, [data-baseweb="select"] > div {{ min-height:42px; border-radius:8px; }}
    [data-testid="stAlert"] {{ border-radius:10px; border-width:1px; }}
    [data-testid="stDataFrame"] {{ background:#fff; border:1px solid {LINE}; border-radius:11px; overflow:hidden; }}
    [data-testid="stPlotlyChart"] {{ background:#fff; border:1px solid {LINE}; border-radius:12px; overflow:hidden; padding:4px; }}
    .card {{ background:#fff; border:1px solid {LINE}; border-left:4px solid {TEAL}; border-radius:11px; padding:13px 16px; margin-bottom:10px; }}
    .card.warn {{ border-left-color:{SAFFRON}; background:#FFF8F0; }}
    .card b {{ color:{NAVY}; }}
    :focus-visible {{ outline:3px solid #F6AD55 !important; outline-offset:2px !important; }}
    @media (max-width:700px) {{ .block-container {{ padding:1rem .75rem 2rem; }} .band {{ border-radius:10px; }} .band .pill {{ display:none; }} }}
    </style>""",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="band"><div class="band-main"><div class="band-logo">⌁</div><div>'
    '<b>HimaRoad Flood Copilot</b>'
    '<span>Satellite evidence for flood impact and mapped access screening</span></div></div>'
    '<div class="pill">LOCAL OPERATIONS WORKBENCH</div></div>',
    unsafe_allow_html=True,
)

page = st.navigation(
    [
        st.Page("views/dashboard.py", title="Evidence map", default=True),
        st.Page("ui/app.py", title="Ask the copilot", url_path="copilot"),
        st.Page("views/about.py", title="About and limits", url_path="about"),
    ],
    position="top",
)
page.run()
