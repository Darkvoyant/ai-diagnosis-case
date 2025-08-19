import streamlit as st
import plotly.graph_objects as go
import numpy as np
from src.file_handler import FileHandler
from src.data_handler import DataHandler
import os
import re

# --------- ОБРАБОТКА СОСТОЯНИЯ СЕССИИ --------- #

if 'df' not in st.session_state:
    st.session_state.df = None


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

# markdown
# display text in bold formatting
st.markdown("""Если датасет не скачан, то можно нажать на кнопку""")

#button
if st.button('Скачать датасет', help="Нажмите для загрузки датасета"):
    try:
        with st.spinner("⏳ Загрузка и распаковка..."):
            FileHandler.download_and_unpack_data(
                "https://drive.usercontent.google.com/download?id=1KK8lVq-enJ_qk-to7GyHiiVnS-cHE9EZ&export=download&authuser=0&confirm=t&uuid=ca382593-85d4-4bca-86ed-0adcaa5859a6&at=AN8xHoqsfzl2-hj7Uhf_Vj_m9S2Q:1752765506294",
                './data/raw'
            )
        st.success("✅ Датасет успешно загружен и распакован!")
        st.info("Данные сохранены в папку `./data/raw`")
    except Exception as e: 
        st.error(f"Не удалось скачать данные, ошибка: {e}")

st.markdown("### 📂 Просмотр CSV-файла")

# Папка, где лежат скачанные данные
DATA_FOLDER = './data/raw'

if not os.path.exists(DATA_FOLDER):
    st.warning("Папка с данными не найдена. Сначала загрузите датасет.")
else:
    # Получение списка CSV-файлов и сортировка по алфавиту
    def extract_number(filename):
        match = re.search(r'\d+', filename)
        return int(match.group()) if match else float('inf')  # если нет числа — в конец

    csv_files = sorted(
        [f for f in os.listdir(DATA_FOLDER) if f.endswith('.csv')],
        key=extract_number
    )

    if not csv_files:
        st.warning("В папке нет CSV-файлов. Сначала загрузите датасет.")
    else:
        selected_file = st.selectbox("Выберите файл:", csv_files)

        file_path = os.path.join(DATA_FOLDER, selected_file)

        # Кнопка для отображения содержимого
        if st.button("📖 Открыть CSV"):
            try:
                handler = DataHandler(FileHandler.read_file(file_path))
                st.session_state.df = handler.df

                st.success(f"Файл `{selected_file}` успешно загружен!")
                st.write("🔍 Предпросмотр данных:")
                st.dataframe(st.session_state.df.head(100))  # показываем первые 100 строк
                st.info(f"Форма: {st.session_state.df.shape[0]} строк × {st.session_state.df.shape[1]} столбцов")

            except Exception as e:
                st.error(f"Ошибка при чтении файла: {e}")
    if (st.session_state.df is not None):
        if st.button("🎨 Нарисовать график"):
            if st.session_state.df is None:
                st.warning("Сначала нужно выбрать файл")
            else:
                with st.spinner("⏳ Рисуем график..."):
                    x = st.session_state.df['time'].to_numpy()
                    y1 = st.session_state.df['current_R'].to_numpy()
                    y2 = st.session_state.df['current_S'].to_numpy()
                    y3 = st.session_state.df['current_T'].to_numpy()

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=x, y=y1, mode='lines', name='current_R'))
                    fig.add_trace(go.Scatter(x=x, y=y2, mode='lines', name='current_S'))
                    fig.add_trace(go.Scatter(x=x, y=y3, mode='lines', name='current_T'))

                    fig.update_layout(
                        xaxis=dict(title="Время, секунды", type="linear"),
                        yaxis=dict(title="Значение тока, Ампер"),
                        dragmode="pan",
                    )

                    st.plotly_chart(fig, use_container_width=True)