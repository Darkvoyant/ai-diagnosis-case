# src/ui/engineer.py
import streamlit as st
from src.data_handling.engine_manager import EngineManager
from src.ui.analyzer_section import display_analyzer_ui # <<< ИМПОРТИРУЕМ НАШ НОВЫЙ МОДУЛЬ

def display_engineer_page(manager: EngineManager):
    st.markdown("---")
    st.header("🧪 Панель инженера")
    st.write("Углубленная диагностика оборудования, требующего внимания.")

    faulty_engines_list = manager.get_faulty_engines()
    
    if not faulty_engines_list:
        st.success("🎉 Нет двигателей, требующих диагностики. Все системы в норме.")
        return

    # Создаем словарь для selectbox: {ID: EngineObject}
    faulty_map = {e['id']: e for e in faulty_engines_list}
    
    col_sel, col_info = st.columns([1, 2])
    
    with col_sel:
        selected_id = st.selectbox(
            "Выберите двигатель для анализа:", 
            options=list(faulty_map.keys())
        )
    
    if selected_id:
        selected_engine = faulty_map[selected_id]
        
        with col_info:
            with st.container(border=True):
                st.subheader(f"🔧 Диагностическая карта: {selected_engine['id']}")
                st.text(f"Серийный номер: {selected_engine['serial']}")
                st.markdown("---")
                st.write(f"**Текущий статус:** {selected_engine['status']}")
                st.write(f"**Обнаруженный дефект:** `{selected_engine['defect']}`")
                st.metric("Остаточный ресурс (RUL)", f"{selected_engine['rul']} ч.")

                st.markdown("### Рекомендации системы:")
                if selected_engine['status'] == 'Предупреждение':
                    st.warning("📌 Запланировать ТО в ближайшее время")
                else:
                    st.error("⛔ ВЫВЕСТИ ИЗ ЭКСПЛУАТАЦИИ. Требуется капитальный ремонт узла.")

    # --- Блок 2: Кнопка-триггер для анализатора ---
    st.subheader("Инструменты углубленного анализа")

    # Инициализируем состояние видимости анализатора
    if 'show_analyzer' not in st.session_state:
        st.session_state.show_analyzer = False

    # Кнопка меняет свое название в зависимости от состояния
    button_text = "Свернуть анализатор" if st.session_state.show_analyzer else "⚡ Выполнить детальный анализ токов"
    
    if st.button(button_text, type="primary"):
        st.session_state.show_analyzer = not st.session_state.show_analyzer
        # При открытии сбрасываем состояние старого анализа, чтобы не было путаницы
        if st.session_state.show_analyzer:
            st.session_state.df = None
            st.session_state.current_file = None
            st.session_state.active_plot = None


    # --- Блок 3: Отображение анализатора по условию ---
    if st.session_state.show_analyzer:
        display_analyzer_ui()