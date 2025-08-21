import streamlit as st
import os
import re
import pandas as pd # Добавлен импорт для примера, если DataHandler его возвращает

# --- 1. ИМПОРТ МОДУЛЕЙ ПРОЕКТА ---
# Используем try-except для более плавной работы, если модули отсутствуют.
# В среде разработки это можно закомментировать для более явного отслеживания ошибок.
try:
    # Предполагается, что эти модули существуют и корректно работают
    from src.data_handling.file_handler import FileHandler
    from src.data_handling.data_handler import DataHandler
    from src.ui.sections import (
        display_file_overview,
        display_rms_analysis,
        display_clarke_transform_analysis,
        display_harmonic_analysis_section,
        display_bearing_defect_analysis_section
    )
except ImportError:
    st.error(
        "Критическая ошибка: Не найдены необходимые модули в папке 'src'."
        "Пожалуйста, убедитесь, что структура проекта корректна."
    )
    # Останавливаем выполнение приложения, так как без этих модулей оно бесполезно
    st.stop()


# --- 2. КОНФИГУРАЦИЯ И КОНСТАНТЫ ---
DATA_FOLDER = './data/raw'


# --- 3. КЭШИРОВАННАЯ ФУНКЦИЯ ЗАГРУЗКИ ДАННЫХ ---
@st.cache_data
def load_and_process_data(file_path: str) -> pd.DataFrame:
    """
    Читает и обрабатывает файл данных, возвращая pandas DataFrame.
    Результаты выполнения этой функции кэшируются Streamlit, чтобы избежать
    повторной загрузки при каждом действии пользователя.
    
    Args:
        file_path: Полный путь к файлу.

    Returns:
        Обработанный DataFrame.
    """
    raw_data = FileHandler.read_file(file_path)
    handler = DataHandler(raw_data)
    return handler.df


# --- 4. ИНИЦИАЛИЗАЦИЯ СОСТОЯНИЯ СЕССИИ ---
# Это гарантирует, что переменные существуют при первом запуске приложения.
if 'df' not in st.session_state:
    st.session_state.df = None
if 'current_file' not in st.session_state:
    st.session_state.current_file = None


# --- 5. ОТРСОВКА ИНТЕРФЕЙСА (UI) ---

# --- ЗАГОЛОВОК ---
st.markdown("<h1 style='text-align: center;'>Анализатор данных «Экспедиция 404»</h1>", unsafe_allow_html=True)
st.markdown("---")

# --- БЛОК ВЫБОРА ФАЙЛА ---
st.markdown("### 📂 Выберите файл для анализа")

if not os.path.exists(DATA_FOLDER):
    st.error(f"Папка с данными не найдена по пути: `{os.path.abspath(DATA_FOLDER)}`")
    st.stop()
else:
    def extract_number(filename: str) -> int:
        """Извлекает число из имени файла для корректной сортировки."""
        match = re.search(r'\d+', filename)
        return int(match.group()) if match else float('inf')

    # Получаем и сортируем только CSV-файлы
    csv_files = sorted(
        [f for f in os.listdir(DATA_FOLDER) if f.endswith('.csv')],
        key=extract_number
    )

    if not csv_files:
        st.warning(f"В папке `{DATA_FOLDER}` нет CSV-файлов для анализа.")
    else:
        # Виджет выбора файла с улучшенным UX
        selected_file = st.selectbox(
            label="Доступные файлы:",
            options=csv_files,
            index=None, # По умолчанию ничего не выбрано
            placeholder="Нажмите, чтобы выбрать файл..."
        )

        # --- ЛОГИКА ОБРАБОТКИ ФАЙЛА ---
        # Проверяем, был ли выбран новый файл
        if selected_file and selected_file != st.session_state.current_file:
            # Показываем индикатор загрузки, пока файл обрабатывается
            with st.spinner(f"Анализируем файл `{selected_file}`... Это может занять некоторое время."):
                try:
                    file_path = os.path.join(DATA_FOLDER, selected_file)
                    # Вызываем кэшированную функцию для загрузки и обработки
                    st.session_state.df = load_and_process_data(file_path)
                    st.session_state.current_file = selected_file
                    st.success(f"Файл `{selected_file}` успешно загружен и обработан!")
                except Exception as e:
                    st.error(f"Произошла ошибка при обработке файла: {e}")
                    # Сбрасываем состояние в случае ошибки
                    st.session_state.df = None
                    st.session_state.current_file = None

# --- 6. ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ АНАЛИЗА ---
# Этот блок выполняется только если в состоянии сессии есть обработанный DataFrame
if st.session_state.df is not None:
    st.markdown("---")
    st.markdown("## 📊 Результаты анализа")

    # Передаем df и current_file в функции отображения
    display_file_overview(st.session_state.df, st.session_state.current_file)
    display_rms_analysis(st.session_state.df)
    display_clarke_transform_analysis(st.session_state.df)
    display_harmonic_analysis_section(st.session_state.df)
    display_bearing_defect_analysis_section(st.session_state.df)

# Если файлы есть, но ни один еще не выбран, показываем подсказку
elif csv_files:
    st.info("👆 **Пожалуйста, выберите файл из списка выше, чтобы начать анализ.**")