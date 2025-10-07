import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from scipy.fft import fft, fftfreq
from scipy.signal import find_peaks
import numpy as np

# Импортируем вашу логику и константы
from src.analysis.bearing_analyzer import BearingDefectAnalyzer
from src.utils.config import SAMPLING_RATE, RPM, LINE_FREQ_SEARCH_RANGE, DEFAULT_BEARING_PARAMS

# --- ОСНОВНЫЕ ФУНКЦИИ ОТОБРАЖЕНИЯ С ОБНОВЛЕННОЙ ЛОГИКОЙ ---

# Эта функция находится в вашем файле src/ui/sections.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# Эта функция находится в вашем файле src/ui/sections.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np # Для округления

def display_file_overview(df, current_file):
    """Отображает превью данных и, по запросу, график временного ряда с обрезкой по длительности."""
    st.write("---")
    st.write("### 🔍 Предпросмотр обработанных данных")
    st.dataframe(df.head(100))
    st.info(f"Форма: {df.shape[0]:,} строк × {df.shape[1]} столбцов")

    st.write("---")
    st.write("### 📈 Временной график")

    # --- Управление видимостью блока настроек ---
    if 'show_ts_controls' not in st.session_state:
        st.session_state.show_ts_controls = False

    button_text = "Скрыть настройки графика" if st.session_state.show_ts_controls else "⚙️ Настроить и построить временной график"
    if st.button(button_text):
        st.session_state.show_ts_controls = not st.session_state.show_ts_controls
        if not st.session_state.show_ts_controls:
            st.session_state.active_plot = None # Скрываем график при закрытии настроек
            
    # --- Блок с настройками (виден по условию) ---
    if st.session_state.show_ts_controls:
        with st.container(border=True):
            st.markdown("##### ⚙️ Настройки отображения")
            
            required_columns = ['time', 'current_R', 'current_S', 'current_T']
            if not all(col in df.columns for col in required_columns):
                st.error(f"Необходимые столбцы не найдены: {required_columns}")
            else:
                # --- НОВЫЙ БЛОК: Слайдер для выбора длительности ---
                total_duration = df['time'].max()
                
                # Устанавливаем разумное значение по умолчанию (например, 5 секунд или вся длина, если она меньше)
                default_duration = min(5.0, total_duration)

                max_duration = st.slider(
                    "Длительность анализа (секунды):",
                    min_value=0.1,
                    max_value=float(np.ceil(total_duration)), # Округляем общую длительность вверх
                    value=default_duration,
                    step=0.1,
                    format="%.1f сек", # Форматирование для наглядности
                    help="Ограничьте длительность для ускорения отрисовки и анализа начальных процессов."
                )
                
                # --- ФИНАЛЬНАЯ КНОПКА ЗАПУСКА ---
                if st.button("🎨 Построить график с выбранными настройками", type="primary"):
                    st.session_state.active_plot = 'time_series'
                    # Сохраняем выбранную длительность в сессию
                    st.session_state.duration_for_plot = max_duration

    # --- Блок отрисовки графика (виден, когда активен) ---
    if st.session_state.get('active_plot') == 'time_series':
        duration_to_render = st.session_state.get('duration_for_plot', 5.0)
        
        # --- НОВАЯ ЛОГИКА: Обрезка DataFrame по времени ---
        df_to_plot = df[df['time'] <= duration_to_render]

        st.info(f"💡 Отображены данные за первые **{duration_to_render:.1f}** секунд ({len(df_to_plot):,} точек).")

        with st.spinner("⏳ Рисуем временной график..."):
            fig = go.Figure()
            fig.add_trace(go.Scattergl(x=df_to_plot['time'], y=df_to_plot['current_R'], mode='lines', name='current_R'))
            fig.add_trace(go.Scattergl(x=df_to_plot['time'], y=df_to_plot['current_S'], mode='lines', name='current_S'))
            fig.add_trace(go.Scattergl(x=df_to_plot['time'], y=df_to_plot['current_T'], mode='lines', name='current_T'))
            fig.update_layout(
                title=f"График токов из файла {current_file}",
                xaxis_title="Время, секунды",
                yaxis_title="Значение тока, Ампер",
                dragmode="pan"
            )
            st.plotly_chart(fig, use_container_width=True)

def display_rms_analysis(df):
    """Рассчитывает и отображает RMS. Не содержит графиков, поэтому логика не меняется."""
    st.write("---")
    st.write("### ⚡ Расчет среднеквадратичного значения (RMS)")
    
    required_columns = ['current_R', 'current_S', 'current_T']
    if not all(col in df.columns for col in required_columns):
        st.error("Необходимые столбцы токов (current_R, current_S, current_T) не найдены.")
        return

    if st.button("💪 Рассчитать RMS"):
        with st.spinner("⏳ Вычисляем RMS..."):
            rms_values = {
                'Фаза': ['Ток R', 'Ток S', 'Ток T'],
                'Среднеквадратичное значение (А)': [
                    np.sqrt(np.mean(df['current_R']**2)),
                    np.sqrt(np.mean(df['current_S']**2)),
                    np.sqrt(np.mean(df['current_T']**2))
                ]
            }
            rms_df = pd.DataFrame(rms_values)
            
            st.write("**Результаты расчета RMS:**")
            st.dataframe(rms_df.set_index('Фаза').style.format('{:.3f}'))

@st.cache_data
def calculate_clarke_transform(df):
    """Выполняет преобразование Кларка. Результат кэшируется."""
    st.info("💡 Выполняется кэшированное вычисление преобразования Кларка...")
    k = np.sqrt(2/3)
    i_r, i_s, i_t = df['current_R'].values, df['current_S'].values, df['current_T'].values
    i_alpha = k * (i_r - 0.5 * i_s - 0.5 * i_t)
    i_beta = k * ((np.sqrt(3)/2) * i_s - (np.sqrt(3)/2) * i_t)
    return pd.DataFrame({'time': df['time'], 'I_alpha': i_alpha, 'I_beta': i_beta})

def display_clarke_transform_analysis(df):
    """Выполняет преобразование Кларка и отображает результаты по одному."""
    st.write("---")
    st.write("### 🔄 Преобразование Кларка (α, β)")
    st.info("💡 **Что это такое:** Преобразование Кларка проецирует трехфазную систему на двухфазную стационарную систему координат (Alpha-Beta).")

    required_columns = ['time', 'current_R', 'current_S', 'current_T']
    if not all(col in df.columns for col in required_columns):
        st.error(f"ОШИБКА: Для выполнения преобразования необходимы столбцы: {required_columns}")
        return

    # Функция для выполнения расчета и сохранения в состояние
    def run_clarke_calculation():
        if 'clarke_df' not in st.session_state or st.session_state.clarke_df is None:
            with st.spinner("⏳ Выполняем преобразование Кларка..."):
                st.session_state.clarke_df = calculate_clarke_transform(df)

    st.write("**Выберите, что вы хотите отобразить:**")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📈 Показать временной график", use_container_width=True):
            run_clarke_calculation()
            st.session_state.active_plot = 'clarke_time_series'
    with col2:
        if st.button("🗺️ Показать векторную диаграмму", use_container_width=True):
            run_clarke_calculation()
            st.session_state.active_plot = 'clarke_vector'
    with col3:
        if st.button("📄 Показать таблицу данных", use_container_width=True):
            run_clarke_calculation()
            st.session_state.active_plot = 'clarke_table'

    # --- Блок условного отображения ---
    active_view = st.session_state.get('active_plot')
    
    if active_view == 'clarke_time_series' and 'clarke_df' in st.session_state:
        st.write("---")
        st.write("#### Временной график компонент Alpha-Beta")
        fig = go.Figure()
        fig.add_trace(go.Scattergl(x=st.session_state.clarke_df['time'], y=st.session_state.clarke_df['I_alpha'], mode='lines', name='I_alpha'))
        fig.add_trace(go.Scattergl(x=st.session_state.clarke_df['time'], y=st.session_state.clarke_df['I_beta'], mode='lines', name='I_beta'))
        fig.update_layout(title="Временной график компонент Alpha-Beta", xaxis_title="Время, секунды", yaxis_title="Амплитуда", dragmode="pan")
        st.plotly_chart(fig, use_container_width=True)

    elif active_view == 'clarke_vector' and 'clarke_df' in st.session_state:
        st.write("---")
        st.write("#### Векторная диаграмма (Фигура Лиссажу)")
        st.info("💡 Для ускорения используйте прореживание. '1' — все точки, '10' — каждая десятая и т.д.")
        
        decimation_factor = st.number_input("Коэффициент прореживания", min_value=1, value=1, step=1)
        df_for_plot = st.session_state.clarke_df.iloc[::decimation_factor]
        
        st.write(f"Отображается **{len(df_for_plot):,}** из **{len(st.session_state.clarke_df):,}** точек.")
        fig_vector = go.Figure()
        fig_vector.add_trace(go.Scattergl(x=df_for_plot['I_alpha'], y=df_for_plot['I_beta'], mode='lines', name='Траектория вектора', line=dict(width=1)))
        fig_vector.update_layout(title="Пространственная траектория вектора тока", xaxis_title="I_alpha", yaxis_title="I_beta", xaxis=dict(scaleanchor="y", scaleratio=1), dragmode="pan")
        st.plotly_chart(fig_vector, use_container_width=True)

    elif active_view == 'clarke_table' and 'clarke_df' in st.session_state:
        st.write("---")
        st.write("#### 🔍 Предпросмотр рассчитанных данных")
        st.dataframe(st.session_state.clarke_df, use_container_width=True)

@st.cache_data
def perform_harmonic_analysis(df, max_harmonic, tolerance):
    """Выполняет FFT и анализ гармоник. Результат кэшируется."""
    st.info("💡 Выполняется кэшированное вычисление FFT и анализ гармоник...")
    phases = ['current_R', 'current_S', 'current_T']
    all_harmonics_list = []
    analysis_summary_data = []
    plot_data = {}

    for phase in phases:
        signal = df[phase].values
        n = len(signal)
        yf = fft(signal)
        xf = fftfreq(n, 1 / SAMPLING_RATE)
        n_pos = n // 2
        yf_amp = 2.0/n * np.abs(yf[0:n_pos])
        xf_pos = xf[0:n_pos]
        
        fundamental_mask = (xf_pos > LINE_FREQ_SEARCH_RANGE[0]) & (xf_pos < LINE_FREQ_SEARCH_RANGE[1])
        if not np.any(fundamental_mask):
            continue
        
        fundamental_idx_in_mask = np.argmax(yf_amp[fundamental_mask])
        fundamental_amp = yf_amp[fundamental_mask][fundamental_idx_in_mask]
        fundamental_freq = xf_pos[fundamental_mask][fundamental_idx_in_mask]
        
        plot_data[phase] = {'xf': xf_pos, 'yf': yf_amp, 'fundamental_freq': fundamental_freq}
        
        peaks, _ = find_peaks(yf_amp, height=fundamental_amp * 0.001, distance=5)
        harmonics_data = []
        harmonic_amplitudes_sq = []

        for i in range(2, max_harmonic + 1):
            target_freq = fundamental_freq * i
            for peak_idx in peaks:
                peak_freq = xf_pos[peak_idx]
                if abs(peak_freq - target_freq) < tolerance:
                    peak_amp = yf_amp[peak_idx]
                    harmonics_data.append({'Фаза': phase, 'Гармоника': i, 'Частота (Гц)': peak_freq, 'Амплитуда': peak_amp})
                    harmonic_amplitudes_sq.append(peak_amp**2)
                    break
        
        thd = (np.sqrt(sum(harmonic_amplitudes_sq)) / fundamental_amp) * 100 if fundamental_amp > 0 else 0
        analysis_summary_data.append({'Фаза': phase, 'Опред. частота (Гц)': fundamental_freq, 'THD (%)': thd})
        if harmonics_data:
            all_harmonics_list.extend(harmonics_data)

    return {
        "plot_data": plot_data,
        "summary_df": pd.DataFrame(analysis_summary_data),
        "harmonics_df": pd.DataFrame(all_harmonics_list)
    }

def display_harmonic_analysis_section(df):
    """Отображает UI для анализа гармоник и показывает результат по запросу."""
    st.write("---")
    st.write("### 🔬 Частотный анализ (FFT) и поиск гармоник")
    st.info("💡 **Как это работает:** Алгоритм автоматически находит основную частоту сети в диапазоне 45-55 Гц.")

    st.write("**Настройки анализа и отображения:**")
    col1_fft, col2_fft, col3_fft = st.columns(3)
    with col1_fft:
        max_harmonic_fft = st.number_input("Гармоники до:", min_value=5, max_value=100, value=25, key="max_harmonic_fft")
    with col2_fft:
        freq_tolerance_fft = st.slider("Допуск (Гц)", min_value=0.1, max_value=5.0, value=1.0, step=0.1, key="freq_tolerance_fft")
    with col3_fft:
        use_db_scale_fft = st.checkbox("Амплитуда в дБ", value=True, key="use_db_scale_fft")
        display_as_harmonics = st.checkbox("Ось X в гармониках", value=False, key="display_as_harmonics")
    
    if st.button("🚀 Выполнить анализ гармоник"):
        with st.spinner("⏳ Анализируем спектры..."):
            # Сохраняем результаты и настройки в состояние
            st.session_state.harmonic_results = perform_harmonic_analysis(df, max_harmonic_fft, freq_tolerance_fft)
            st.session_state.harmonic_settings = {
                'use_db': use_db_scale_fft, 
                'as_harmonics': display_as_harmonics, 
                'max_harmonic': max_harmonic_fft
            }
            # Устанавливаем активный график
            st.session_state.active_plot = 'harmonic_analysis'

    # --- Блок отображения ---
    if st.session_state.get('active_plot') == 'harmonic_analysis' and 'harmonic_results' in st.session_state:
        results = st.session_state.harmonic_results
        settings = st.session_state.harmonic_settings
        
        fig_fft = go.Figure()
        first_fundamental_freq = None

        for phase, data in results["plot_data"].items():
            if data.get('fundamental_freq') and first_fundamental_freq is None:
                first_fundamental_freq = data['fundamental_freq']
            
            y_display = 20 * np.log10(data['yf'] + 1e-9) if settings['use_db'] else data['yf']
            x_axis_data = data['xf'] / data['fundamental_freq'] if settings['as_harmonics'] and data.get('fundamental_freq', 0) > 0 else data['xf']
            fig_fft.add_trace(go.Scatter(x=x_axis_data, y=y_display, mode='lines', name=f'Спектр {phase}'))

        yaxis_title = "Амплитуда (дБ)" if settings['use_db'] else "Амплитуда"
        if settings['as_harmonics']:
            xaxis_title = "Номер гармоники"
            x_range = [0, settings['max_harmonic'] + 1]
        else:
            xaxis_title = "Частота (Гц)"
            max_freq = (first_fundamental_freq or LINE_FREQ_SEARCH_RANGE[1]) * (settings['max_harmonic'] + 1)
            x_range = [0, max_freq]

        fig_fft.update_layout(title="Частотные спектры токов", xaxis_title=xaxis_title, yaxis_title=yaxis_title)
        fig_fft.update_xaxes(range=x_range)
        st.plotly_chart(fig_fft, use_container_width=True)

        st.write("### 📄 Результаты анализа гармоник")
        if not results["summary_df"].empty:
            st.write("**Сводка по фазам:**")
            st.dataframe(results["summary_df"].set_index('Фаза').style.format({'Опред. частота (Гц)': '{:.2f}', 'THD (%)': '{:.2f}'}))
        if not results["harmonics_df"].empty:
            st.write("**Найденные гармоники:**")
            st.dataframe(results["harmonics_df"].style.format({'Частота (Гц)': '{:.2f}', 'Амплитуда': '{:.3f}'}))
        else:
            st.warning("Значимых гармоник не найдено.")

def display_bearing_defect_analysis_section(df):
    """Отображает UI для диагностики подшипников и показывает результат по запросу."""
    st.write("---")
    st.write("### ⚙️ Диагностика дефектов подшипников")
    st.info(f"Анализ спектра тока для поиска характерных частот. **Номинальная скорость: {RPM} об/мин**.")

    col1_br, col2_br = st.columns(2)
    with col1_br:
        signal_options = [col for col in df.columns if col != 'time']
        selected_signal = st.selectbox("Сигнал для анализа:", signal_options, key="signal_selector")
        st.write("##### Параметры подшипника (Гц):")
        bpfo = st.number_input("BPFO", value=DEFAULT_BEARING_PARAMS['BPFO'], format="%.2f")
        bpfi = st.number_input("BPFI", value=DEFAULT_BEARING_PARAMS['BPFI'], format="%.2f")
    with col2_br:
        bsf = st.number_input("BSF", value=DEFAULT_BEARING_PARAMS['BSF'], format="%.2f")
        ftf = st.number_input("FTF", value=DEFAULT_BEARING_PARAMS['FTF'], format="%.2f")
        n_b = st.number_input("N_B", min_value=1, value=DEFAULT_BEARING_PARAMS['N_B'], step=1)

    use_db_scale_bearing = st.checkbox("Логарифмическая шкала (дБ)", value=True, key="db_scale_bearing")

    if st.button("🚀 Запустить анализ дефектов подшипника"):
        with st.spinner("Анализирую спектр тока..."):
            signal_data = df[selected_signal].values
            bearing_params = {'BPFO': bpfo, 'BPFI': bpfi, 'BSF': bsf, 'FTF': ftf, 'N_B': n_b}

            analyzer = BearingDefectAnalyzer(signal=signal_data, sampling_rate=SAMPLING_RATE, rpm=RPM, bearing_params=bearing_params)
            report = analyzer.run_analysis()
            fig_bearing = analyzer.plot_spectrum(use_db_scale=use_db_scale_bearing)
            
            # Сохраняем все результаты в состояние
            st.session_state.bearing_results = {
                "report": report,
                "fig": fig_bearing,
                "analyzer": analyzer
            }
            # Устанавливаем активный график
            st.session_state.active_plot = 'bearing_analysis'

    # --- Блок отображения ---
    if st.session_state.get('active_plot') == 'bearing_analysis' and 'bearing_results' in st.session_state:
        results = st.session_state.bearing_results
        report = results['report']
        fig_bearing = results['fig']
        analyzer = results['analyzer']

        st.write("### 📈 Результаты диагностики (MCSA)")
        if not report:
            st.error("Анализ не был выполнен.")
        else:
            with st.expander("📝 **Сводный отчет по дефектам**", expanded=True):
                defect_freqs = report.get('Defect Frequencies', {})
                if not defect_freqs:
                    st.success("Явных признаков дефектов по боковым полосам не обнаружено.")
                else:
                    for defect, message in defect_freqs.items():
                        st.warning(f"**{defect}:** {message}")

            st.plotly_chart(fig_bearing, use_container_width=True)
            
            with st.expander("📄 **Детализация по найденным боковым полосам**"):
                all_found_peaks = [item for sublist in analyzer.found_peaks.values() for item in sublist]
                if all_found_peaks:
                    df_details = pd.DataFrame(all_found_peaks)
                    st.dataframe(df_details[['defect_type', 'order', 'side', 'found_freq_hz', 'amplitude']].style.format({
                        'found_freq_hz': '{:.2f}', 'amplitude': '{:.5f}'
                    }))
                else:
                    st.info("Значимых боковых полос не найдено.")