import streamlit as st
import os
import re

# Импортируем наши обработчики данных
# (Предполагаем, что они находятся в src/data_handling)
try:
    from src.data_handling.file_handler import FileHandler
    from src.data_handling.data_handler import DataHandler
except ImportError:
    st.error("Критическая ошибка: Не найдены модули для обработки данных!")
    st.stop()

# Импортируем функции для отрисовки UI
from src.ui.sections import (
    display_file_overview,
    display_rms_analysis,
    display_clarke_transform_analysis,
    display_harmonic_analysis_section,
    display_bearing_defect_analysis_section
)

# --- Инициализация состояния сессии ---
if 'df' not in st.session_state: st.session_state.df = None
if 'current_file' not in st.session_state: st.session_state.current_file = None

# --- ЗАГОЛОВОК ---
st.markdown("<h1 style='text-align: center; ...'> Экспедиция 404 </h1>", unsafe_allow_html=True)
st.markdown("### 📂 Выберите файл для анализа")

# --- ЛОГИКА ВЫБОРА И ЗАГРУЗКИ ФАЙЛА ---
DATA_FOLDER = './data/raw'
if not os.path.exists(DATA_FOLDER):
    st.warning("Папка с данными не найдена.")
else:
    def extract_number(filename):
        match = re.search(r'\d+', filename)
        return int(match.group()) if match else float('inf')

    csv_files = sorted([f for f in os.listdir(DATA_FOLDER) if f.endswith('.csv')], key=extract_number)
    
    if not csv_files:
        st.warning("В папке нет CSV-файлов.")
    else:
        selected_file = st.selectbox("Выберите файл:", csv_files)
        if selected_file != st.session_state.current_file:
            try:
                file_path = os.path.join(DATA_FOLDER, selected_file)
                raw_data = FileHandler.read_file(file_path)
                handler = DataHandler(raw_data)
                st.session_state.df = handler.df
                st.session_state.current_file = selected_file
                st.success(f"Файл `{selected_file}` успешно обработан!")
            except Exception as e:
                st.error(f"Ошибка при обработке файла: {e}")
                st.session_state.df = None
                st.session_state.current_file = None


if st.session_state.df is not None:
    # Передаем df и current_file как аргументы
    display_file_overview(st.session_state.df, st.session_state.current_file) 
    display_rms_analysis(st.session_state.df)
    display_clarke_transform_analysis(st.session_state.df)
    # Передаем только df
    display_harmonic_analysis_section(st.session_state.df)
    display_bearing_defect_analysis_section(st.session_state.df)