import streamlit as st

# --- 1. ИМПОРТ МОДУЛЕЙ ПРОЕКТА ---
try:
    from src.utils import config
    from src.data_handling.engine_manager import EngineManager
    from src.ui.sidebar import display_sidebar
    from src.ui.dashboard import display_dashboard_page
    from src.ui.engineer import display_engineer_page
    from src.ui.admin import display_admin_page
except ImportError as e:
    st.error(f"Критическая ошибка импорта: {e}. Проверьте структуру папок.")
    st.stop()

# --- 2. КОНФИГУРАЦИЯ СТРАНИЦЫ ---
st.set_page_config(
    page_title=config.APP_TITLE,
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 3. ИНИЦИАЛИЗАЦИЯ СОСТОЯНИЯ СЕССИИ ---
# Инициализируем менеджер данных один раз и храним его в сессии
if 'engine_manager' not in st.session_state:
    st.session_state.engine_manager = EngineManager()

# Инициализируем состояние пользователя
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.user_role = None

# Получаем ссылку на менеджер для удобства
manager = st.session_state.engine_manager


# --- 4. ОТРИСОВКА ИНТЕРФЕЙСА (UI) ---

# A. Сайдбар (всегда виден)
display_sidebar(manager)

# B. Главный дашборд (всегда виден)
display_dashboard_page(manager)

# C. Ролевые страницы (видны только при входе)
if st.session_state.logged_in:
    role = st.session_state.user_role

    # Можно использовать табы для разделения главной и спец. страниц,
    # но следуя вашему прошлому дизайну, показываем их ниже.
    
    if role == "engineer":
        display_engineer_page(manager)
        
    elif role == "admin":
        display_admin_page()

# D. Подвал (опционально)
st.markdown("---")
st.markdown(f"<div style='text-align:center; color: gray;'>{config.APP_TITLE} | Экспедиция 404 </div>", unsafe_allow_html=True)