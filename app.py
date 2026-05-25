import streamlit as st

st.set_page_config(
    page_title="入浴介助管理表",
    page_icon="🛁",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "page" not in st.session_state:
    st.session_state.page = "settings"

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.markdown("### 🛁 入浴介助管理表")
with col2:
    if st.button("⚙️ 設定", use_container_width=True,
                type="primary" if st.session_state.page == "settings" else "secondary"):
        st.session_state.page = "settings"
        st.rerun()
with col3:
    if st.button("📋 管理表", use_container_width=True,
                type="primary" if st.session_state.page == "schedule" else "secondary"):
        st.session_state.page = "schedule"
        st.rerun()

st.divider()

if st.session_state.page == "settings":
    from pages import settings
    settings.render()
else:
    from pages import schedule
    schedule.render()