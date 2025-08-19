import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import os
import re
import sys

# --- КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: НАДЕЖНЫЙ ИМПОРТ ---
# Пытаемся импортировать обязательные модули.
# Если их нет, приложение не сможет работать, поэтому мы останавливаемся.
try:
    from src.file_handler import FileHandler
    from src.data_handler import DataHandler
except ImportError:
    # Выводим понятную ошибку в интерфейсе Streamlit
    st.error(
        """
        **Критическая ошибка: Не найдены модули для обработки данных!**

        Приложение не может запуститься, так как отсутствуют необходимые файлы.

        **Как исправить:**
        1. Убедитесь, что в корне вашего проекта есть папка `src`.
        2. Внутри папки `src` должны находиться файлы `file_handler.py` и `data_handler.py`.
        3. Убедитесь, что в `src` также есть файл `__init__.py` (может быть пустым), чтобы Python мог рассматривать эту папку как пакет.

        После исправления структуры файлов перезапустите приложение.
        """
    )
    # st.stop() немедленно прекращает выполнение скрипта.
    # Никакой код ниже этой строки не будет выполнен.
    st.stop()


# --- Инициализация состояния сессии ---
# Этот код выполнится только если импорт прошел успешно.
if 'df' not in st.session_state:
    st.session_state.df = None
if 'current_file' not in st.session_state:
    st.session_state.current_file = None


st.markdown("""
<h1 style='
    text-align: center;
    font-size: 48px;
    background: -webkit-linear-gradient(45deg, #00c6ff, #0072ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
'>
Добро пожаловать, экспедиция 404!
</h1>
""", unsafe_allow_html=True)


st.markdown("### 📂 Выберите файл для анализа")
DATA_FOLDER = './data/raw'

# --- Создание демонстрационных файлов (если их нет) ---
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)
    pd.DataFrame({
        'current_R': np.random.randn(2000).cumsum(),
        'current_S': np.random.randn(2000).cumsum(),
        'current_T': np.random.randn(2000).cumsum()
    }).to_csv(os.path.join(DATA_FOLDER, 'raw_data_1.csv'), index=False)


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
        selected_file = st.selectbox("Выберите файл (данные загрузятся и обработаются автоматически):", csv_files)

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


# --- БЛОК ОТОБРАЖЕНИЯ (таблица и график) ---
if st.session_state.df is not None:
    st.write("---")
    st.write("### 🔍 Предпросмотр обработанных данных")
    st.dataframe(st.session_state.df.head(100))
    st.info(f"Форма: {st.session_state.df.shape[0]} строк × {st.session_state.df.shape[1]} столбцов")

    st.write("### 📈 Построение графика")
    if st.button("🎨 Нарисовать график"):
        required_columns = ['time', 'current_R', 'current_S', 'current_T']
        if all(col in st.session_state.df.columns for col in required_columns):
            with st.spinner("⏳ Рисуем график..."):
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=st.session_state.df['time'], y=st.session_state.df['current_R'], mode='lines', name='current_R'))
                fig.add_trace(go.Scatter(x=st.session_state.df['time'], y=st.session_state.df['current_S'], mode='lines', name='current_S'))
                fig.add_trace(go.Scatter(x=st.session_state.df['time'], y=st.session_state.df['current_T'], mode='lines', name='current_T'))
                fig.update_layout(
                    title=f"График токов из файла {st.session_state.current_file}",
                    xaxis_title="Время, секунды", yaxis_title="Значение тока, Ампер", dragmode="pan"
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.error(f"Ошибка после обработки: в данных все равно отсутствуют необходимые столбцы. Требуются: {required_columns}.")