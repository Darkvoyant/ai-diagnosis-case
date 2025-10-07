# src/ui/dashboard.py
import streamlit as st
from src.utils import config
from src.data_handling.engine_manager import EngineManager

def display_dashboard_page(manager: EngineManager):
    st.title("🛠 Пульт мониторинга двигателей")

    engines = manager.get_all_engines()

    # --- 1. Сводка по системе ---
    st.markdown("### Общая сводка по системе")
    working, warning, error = manager.get_system_summary()

    if error == 0 and warning == 0:
        st.success(f"✅ Все системы в норме: {working} из {config.TOTAL_ENGINES} двигателей работают исправно.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("✅ В норме", f"{working}")
        c2.metric("⚠️ Предупреждения", f"{warning}", delta=f"{warning} требуют внимания", delta_color="inverse")
        c3.metric("🚨 В аварии", f"{error}", delta=f"{error} не работают", delta_color="inverse")
    st.markdown("---")

    # --- 2. Пагинация ---
    # Убеждаемся, что страница в session_state
    if "dashboard_page_num" not in st.session_state:
        st.session_state.dashboard_page_num = 0
        
    total_pages = (len(engines) - 1) // config.ENGINES_PER_PAGE + 1
    
    col_prev, col_center, col_next = st.columns([1, 3, 1])
    with col_prev:
        if st.button("⏪ Назад", use_container_width=True) and st.session_state.dashboard_page_num > 0:
            st.session_state.dashboard_page_num -= 1
            st.rerun()
    with col_center:
        st.markdown(f"<div style='text-align:center; font-size:18px; padding-top: 5px;'>Страница {st.session_state.dashboard_page_num + 1} / {total_pages}</div>", unsafe_allow_html=True)
    with col_next:
        if st.button("⏩ Вперёд", use_container_width=True) and st.session_state.dashboard_page_num < total_pages - 1:
            st.session_state.dashboard_page_num += 1
            st.rerun()
            
    st.markdown("---")

    # --- 3. Отображение карточек ---
    start = st.session_state.dashboard_page_num * config.ENGINES_PER_PAGE
    end = start + config.ENGINES_PER_PAGE
    visible_engines = engines[start:end]

    for engine in visible_engines:
        _render_engine_card(engine, manager)

def _render_engine_card(engine, manager: EngineManager):
    """Внутренняя функция для отрисовки одной карточки."""
    with st.container(border=True):
        col1, col2 = st.columns([1, 3])

        # Определение стилей
        if engine["status"] == "Работает":
            color, icon, p_val = "#2E7D32", "✅", 100
        elif engine["status"] == "Предупреждение":
            color, icon, p_val = "#FFC107", "⚠️", 50
        else: # "Не работает"
            color, icon, p_val = "#D32F2F", "🚨", 5
        
        # Левая колонка (ID и SN)
        with col1:
            st.markdown(f"""
            <div style="background-color:{color}; height:150px; padding:15px; border-radius:8px; text-align:center; color:white; display:flex; flex-direction:column; justify-content:center;">
                <h2 style="color:white; margin:0;">{engine['id']}</h2>
                <small style="opacity:0.8;">{engine['serial']}</small>
            </div>""", unsafe_allow_html=True)

        # Правая колонка (Инфо и действия)
        with col2:
            st.markdown(f"**Статус:** {icon} {engine['status']}")
            st.progress(p_val, text=f"Прогноз RUL: {engine['rul']:,} ч.")

            # Блок для сообщений и кнопок
            btn_col1, btn_col2 = st.columns([2, 1])
            with btn_col1:
                if engine['status'] == "Предупреждение":
                    st.warning(f"**Нарушение:** {engine['defect']}", icon="⚠️")
                elif engine['status'] == "Не работает":
                    st.error(f"**Авария:** {engine['defect']}", icon="🚨")
                else:
                    st.write("") # Пустое место для выравнивания

            with btn_col2:
                # Кнопка только для проблемных и выровнена по вертикали
                if engine["status"] != "Работает":
                    st.markdown("<div style='padding-top: 5px;'></div>", unsafe_allow_html=True) # Небольшой отступ
                    if st.button("🛠️ Устранить", key=f"fix_{engine['id']}", use_container_width=True, type="primary"):
                        manager.fix_engine(engine['id'])
                        st.rerun()