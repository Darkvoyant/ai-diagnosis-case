import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import os
import re
import sys
from scipy.fft import fft, fftfreq
from scipy.signal import find_peaks

# --- Константа частоты дискретизации, как вы и указали ---
SAMPLING_RATE = 25600

# Пытаемся импортировать обязательные модули
try:
    from src.file_handler import FileHandler
    from src.data_handler import DataHandler
except ImportError:
    st.error(
        """
        **Критическая ошибка: Не найдены модули для обработки данных!**
        Убедитесь, что в корне проекта есть папка `src` с файлами `file_handler.py`, `data_handler.py` и `__init__.py`.
        """
    )
    st.stop()

# --- Инициализация состояния сессии ---
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

# --- БЛОК ОТОБРАЖЕНИЯ (таблица и графики) ---
if st.session_state.df is not None:
    st.write("---")
    st.write("### 🔍 Предпросмотр обработанных данных")
    st.dataframe(st.session_state.df.head(100))
    st.info(f"Форма: {st.session_state.df.shape[0]} строк × {st.session_state.df.shape[1]} столбцов")

    st.write("### 📈 Временной график")
    if st.button("🎨 Построить временной график"):
        # ... (код графика временных рядов без изменений) ...
        pass # Скрыто для краткости, ваш код здесь работает

    # --- БЛОК ЧАСТОТНОГО АНАЛИЗА С ВЫБОРОМ ЧАСТОТЫ ---
    st.write("---")
    st.write("### 🔬 Частотный анализ (FFT) и поиск гармоник")

    st.write("**Настройки анализа и отображения:**")
    
    col_main, col1, col2, col3 = st.columns(4)
    with col_main:
        nominal_freq = st.radio("Номинальная частота сети (Гц):", (50, 60), horizontal=True)
    with col1:
        max_harmonic = st.number_input("Гармоники до:", min_value=5, max_value=100, value=25)
    with col2:
        freq_tolerance = st.slider("Допуск (Гц)", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
    with col3:
        use_db_scale = st.checkbox("Амплитуда в дБ", value=True)
    
    if st.button("🚀 Выполнить анализ и найти гармоники"):
        df = st.session_state.df
        st.info(f"Анализ для сети **{nominal_freq} Гц**. Частота дискретизации: **{SAMPLING_RATE} Гц**")
        
        with st.spinner("⏳ Анализируем спектры..."):
            fig_fft = go.Figure()
            phases = ['current_R', 'current_S', 'current_T']
            all_harmonics_df = pd.DataFrame()

            for phase in phases:
                signal = df[phase].values
                n = len(signal)
                yf = fft(signal)
                xf = fftfreq(n, 1 / SAMPLING_RATE)

                n_pos = n // 2
                yf_amp = 2.0/n * np.abs(yf[0:n_pos])
                xf_pos = xf[0:n_pos]
                
                search_window = 5
                fundamental_mask = (xf_pos > nominal_freq - search_window) & (xf_pos < nominal_freq + search_window)

                if not np.any(fundamental_mask): 
                    st.warning(f"Не удалось найти основную гармонику около {nominal_freq} Гц для фазы {phase}. Фаза пропущена.")
                    continue
                
                fundamental_amp = yf_amp[fundamental_mask].max()
                fundamental_freq = xf_pos[fundamental_mask][np.argmax(yf_amp[fundamental_mask])]
                
                peaks, _ = find_peaks(yf_amp, height=fundamental_amp * 0.001, distance=5)
                harmonics_data = []
                harmonic_amplitudes_sq = []

                for i in range(2, max_harmonic + 1):
                    target_freq = fundamental_freq * i
                    for peak_idx in peaks:
                        peak_freq = xf_pos[peak_idx]
                        if abs(peak_freq - target_freq) < freq_tolerance:
                            peak_amp = yf_amp[peak_idx]
                            harmonics_data.append({'Фаза': phase, 'Гармоника': i, 'Частота (Гц)': peak_freq, 'Амплитуда': peak_amp})
                            harmonic_amplitudes_sq.append(peak_amp**2)
                            break
                
                thd = (np.sqrt(sum(harmonic_amplitudes_sq)) / fundamental_amp) * 100 if fundamental_amp > 0 else 0
                
                if harmonics_data:
                    phase_df = pd.DataFrame(harmonics_data)
                    phase_df['THD (%)'] = thd
                    all_harmonics_df = pd.concat([all_harmonics_df, phase_df], ignore_index=True)

                y_display = 20 * np.log10(yf_amp + 1e-9) if use_db_scale else yf_amp
                fig_fft.add_trace(go.Scatter(x=xf_pos, y=y_display, mode='lines', name=f'Спектр {phase}'))
                if harmonics_data:
                    harm_freqs = [h['Частота (Гц)'] for h in harmonics_data]
                    harm_amps = [h['Амплитуда'] for h in harmonics_data]
                    harm_labels = [f"H{h['Гармоника']}" for h in harmonics_data]
                    y_markers = 20 * np.log10(np.array(harm_amps) + 1e-9) if use_db_scale else harm_amps
                    fig_fft.add_trace(go.Scatter(x=harm_freqs, y=y_markers, text=harm_labels, mode='markers+text',
                        marker=dict(symbol='x', color='red', size=8), textposition="top center", 
                        name=f'Гармоники {phase}', showlegend=False))
            
            yaxis_title = "Амплитуда (дБ)" if use_db_scale else "Амплитуда"
            fig_fft.update_layout(title="Частотные спектры с отмеченными гармониками", xaxis_title="Частота (Гц)", yaxis_title=yaxis_title)
            fig_fft.update_xaxes(range=[0, nominal_freq * (max_harmonic + 1)])
            st.plotly_chart(fig_fft, use_container_width=True)

            st.write("### 📄 Результаты анализа гармоник")
            if not all_harmonics_df.empty:
                st.write("**Суммарный коэффициент гармонических искажений (THD):**")
                thd_summary = all_harmonics_df[['Фаза', 'THD (%)']].drop_duplicates().set_index('Фаза')
                st.dataframe(thd_summary.style.format("{:.2f}"))
                st.write("**Найденные гармоники:**")
                st.dataframe(all_harmonics_df.style.format({'Частота (Гц)': '{:.2f}', 'Амплитуда': '{:.3f}'}))
            else:
                st.warning("Значимых гармоник не найдено с заданными параметрами.")