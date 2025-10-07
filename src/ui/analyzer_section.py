# src/ui/analyzer_section.py
import streamlit as st
import os
import re
import pandas as pd

# --- 1. ИМПОРТ МОДУЛЕЙ ПРОЕКТА ---
from src.data_handling.file_handler import FileHandler
from src.data_handling.data_handler import DataHandler
from src.ui.sections import (
    display_file_overview,
    display_rms_analysis,
    display_clarke_transform_analysis,
    display_harmonic_analysis_section,
    display_bearing_defect_analysis_section
)

# --- 2. КОНФИГУРАЦИЯ И КОНСТАНТЫ ---
DATA_FOLDER = './data/raw'

# --- 3. КЭШИРОВАННАЯ ФУНКЦИЯ ЗАГРУЗКИ ДАННЫХ ---
@st.cache_data
def load_and_process_data(file_path: str) -> pd.DataFrame:
    raw_data = FileHandler.read_file(file_path)
    handler = DataHandler(raw_data)
    # Имитируем столбцы для примера, если их нет
    if 'time' not in handler.df.columns:
        handler.df['time'] = [i / 50000 for i in range(len(handler.df))]
    return handler.df

def display_analyzer_ui():
    """
    Основная функция, которая отрисовывает весь интерфейс анализатора данных.
    """
    # Инициализация состояния сессии, специфичного для анализатора
    if 'df' not in st.session_state:
        st.session_state.df = None
    if 'current_file' not in st.session_state:
        st.session_state.current_file = None

    with st.container(border=True):
        st.markdown("<h2 style='text-align: center;'>Анализатор данных «Экспедиция 404»</h2>", unsafe_allow_html=True)
        st.markdown("---")

        # --- БЛОК ВЫБОРА ФАЙЛА ---
        st.markdown("##### 📂 Шаг 1: Выберите файл для анализа")
        
        # Проверяем и создаем папку, если нужно
        if not os.path.exists(DATA_FOLDER):
            os.makedirs(DATA_FOLDER)
            st.info(f"Создана папка `{DATA_FOLDER}`. Поместите в нее CSV файлы для анализа.")
        
        csv_files = sorted([f for f in os.listdir(DATA_FOLDER) if f.endswith('.csv')])

        if not csv_files:
            st.warning(f"В папке `{DATA_FOLDER}` нет CSV-файлов. Добавьте файлы, чтобы начать анализ.")
            return # Прерываем выполнение, если файлов нет
        
        selected_file = st.selectbox(
            label="Доступные файлы измерений:", options=csv_files, index=None,
            placeholder="Нажмите, чтобы выбрать файл...", label_visibility="collapsed"
        )

        # --- ЛОГИКА ОБРАБОТКИ ФАЙЛА ---
        if selected_file and selected_file != st.session_state.current_file:
            with st.spinner(f"Анализируем `{selected_file}`..."):
                try:
                    file_path = os.path.join(DATA_FOLDER, selected_file)
                    st.session_state.df = load_and_process_data(file_path)
                    st.session_state.current_file = selected_file
                except Exception as e:
                    st.error(f"Ошибка при обработке файла: {e}")
                    st.session_state.df = None
                    st.session_state.current_file = None

        # --- ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ АНАЛИЗА ---
        if st.session_state.df is not None:
            st.success(f"**Готов к работе файл:** `{st.session_state.current_file}`")
            st.markdown("##### 📊 Шаг 2: Выполните необходимые анализы")
            
            # ВАЖНО: Передаем df и current_file из session_state
            display_file_overview(st.session_state.df, st.session_state.current_file)
            display_rms_analysis(st.session_state.df)
            display_clarke_transform_analysis(st.session_state.df)
            display_harmonic_analysis_section(st.session_state.df)
            display_bearing_defect_analysis_section(st.session_state.df)
        elif csv_files:
            st.info("👆 **Пожалуйста, выберите файл из списка выше, чтобы начать анализ.**")