import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from scipy.fft import fft, fftfreq
from scipy.signal import find_peaks
import numpy as np

# Импортируем нашу логику и константы
from src.analysis.bearing_analyzer import BearingDefectAnalyzer
from src.utils.config import SAMPLING_RATE, RPM, LINE_FREQ_SEARCH_RANGE, DEFAULT_BEARING_PARAMS

def display_file_overview(df, current_file):
    """Отображает превью данных и график временного ряда."""
    st.write("---")
    st.write("### 🔍 Предпросмотр обработанных данных")
    st.dataframe(df.head(100))
    st.info(f"Форма: {df.shape[0]} строк × {df.shape[1]} столбцов")

    # --- ВРЕМЕННОЙ ГРАФИК ---
    st.write("---")
    st.write("### 📈 Временной график")
    if st.button("🎨 Построить временной график"):
        required_columns = ['time', 'current_R', 'current_S', 'current_T']
        if all(col in df.columns for col in required_columns):
            with st.spinner("⏳ Рисуем временной график..."):
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df['time'], y=df['current_R'], mode='lines', name='current_R'))
                fig.add_trace(go.Scatter(x=df['time'], y=df['current_S'], mode='lines', name='current_S'))
                fig.add_trace(go.Scatter(x=df['time'], y=df['current_T'], mode='lines', name='current_T'))
                fig.update_layout(title=f"График токов из файла {current_file}", xaxis_title="Время, секунды", yaxis_title="Значение тока, Ампер", dragmode="pan")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.error(f"Не удалось построить график. Необходимые столбцы не найдены: {required_columns}")

def display_harmonic_analysis_section(df):
    """Отображает UI и логику для анализа гармоник."""
    st.write("---")
    st.write("### 🔬 Частотный анализ (FFT) и поиск гармоник")
    st.info("💡 **Как это работает:** Алгоритм автоматически находит основную частоту сети в диапазоне 45-55 Гц для максимальной точности.")

    st.write("**Настройки анализа и отображения:**")
    col1_fft, col2_fft, col3_fft = st.columns(3)
    with col1_fft:
        max_harmonic_fft = st.number_input("Гармоники до:", min_value=5, max_value=100, value=25, key="max_harmonic_fft")
    with col2_fft:
        freq_tolerance_fft = st.slider("Допуск (Гц)", min_value=0.1, max_value=5.0, value=1.0, step=0.1, key="freq_tolerance_fft")
    with col3_fft:
        use_db_scale_fft = st.checkbox("Амплитуда в дБ", value=True, key="use_db_scale_fft")
    
    if st.button("🚀 Выполнить анализ и найти гармоники"):
        with st.spinner("⏳ Анализируем спектры..."):
            fig_fft = go.Figure()
            phases = ['current_R', 'current_S', 'current_T']
            all_harmonics_df = pd.DataFrame()
            analysis_summary_data = []

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
                    st.warning(f"Не удалось найти основную гармонику в диапазоне {LINE_FREQ_SEARCH_RANGE} Гц для фазы {phase}. Фаза пропущена.")
                    continue
                
                fundamental_idx_in_mask = np.argmax(yf_amp[fundamental_mask])
                fundamental_amp = yf_amp[fundamental_mask][fundamental_idx_in_mask]
                fundamental_freq = xf_pos[fundamental_mask][fundamental_idx_in_mask]
                
                peaks, _ = find_peaks(yf_amp, height=fundamental_amp * 0.001, distance=5)
                harmonics_data = []
                harmonic_amplitudes_sq = []

                for i in range(2, max_harmonic_fft + 1):
                    target_freq = fundamental_freq * i
                    for peak_idx in peaks:
                        peak_freq = xf_pos[peak_idx]
                        if abs(peak_freq - target_freq) < freq_tolerance_fft:
                            peak_amp = yf_amp[peak_idx]
                            harmonics_data.append({'Фаза': phase, 'Гармоника': i, 'Частота (Гц)': peak_freq, 'Амплитуда': peak_amp})
                            harmonic_amplitudes_sq.append(peak_amp**2)
                            break
                
                thd = (np.sqrt(sum(harmonic_amplitudes_sq)) / fundamental_amp) * 100 if fundamental_amp > 0 else 0
                analysis_summary_data.append({'Фаза': phase, 'Опред. частота (Гц)': fundamental_freq, 'THD (%)': thd})
                if harmonics_data:
                    all_harmonics_df = pd.concat([all_harmonics_df, pd.DataFrame(harmonics_data)], ignore_index=True)

                y_display = 20 * np.log10(yf_amp + 1e-9) if use_db_scale_fft else yf_amp
                fig_fft.add_trace(go.Scatter(x=xf_pos, y=y_display, mode='lines', name=f'Спектр {phase}'))
            
            yaxis_title = "Амплитуда (дБ)" if use_db_scale_fft else "Амплитуда"
            fig_fft.update_layout(title="Частотные спектры токов", xaxis_title="Частота (Гц)", yaxis_title=yaxis_title)
            fig_fft.update_xaxes(range=[0, LINE_FREQ_SEARCH_RANGE[1] * (max_harmonic_fft + 1)])
            st.plotly_chart(fig_fft, use_container_width=True)

            st.write("### 📄 Результаты анализа гармоник")
            if analysis_summary_data:
                st.write("**Сводка по фазам:**")
                st.dataframe(pd.DataFrame(analysis_summary_data).set_index('Фаза').style.format({'Опред. частота (Гц)': '{:.2f}', 'THD (%)': '{:.2f}'}))
            if not all_harmonics_df.empty:
                st.write("**Найденные гармоники:**")
                st.dataframe(all_harmonics_df.style.format({'Частота (Гц)': '{:.2f}', 'Амплитуда': '{:.3f}'}))
            else:
                st.warning("Значимых гармоник не найдено с заданными параметрами.")

def display_bearing_defect_analysis_section(df):
    """Отображает UI и логику для диагностики подшипников."""
    st.write("---")
    st.write("### ⚙️ Диагностика дефектов подшипников")
    st.info(f"Этот модуль анализирует спектр тока для поиска характерных частот. **Номинальная скорость вращения: {RPM} об/мин**.")

    col1_br, col2_br = st.columns(2)
    with col1_br:
        signal_options = [col for col in df.columns if col != 'time']
        selected_signal = st.selectbox("Выберите сигнал для анализа:", signal_options, key="signal_selector")
        st.write("##### Параметры подшипника (Гц):")
        bpfo = st.number_input("BPFO (наружное кольцо)", min_value=0.0, value=DEFAULT_BEARING_PARAMS['BPFO'], format="%.2f")
        bpfi = st.number_input("BPFI (внутреннее кольцо)", min_value=0.0, value=DEFAULT_BEARING_PARAMS['BPFI'], format="%.2f")

    with col2_br:
        st.write("‎") 
        st.write("‎")
        st.write("##### ‎")
        bsf = st.number_input("BSF (тела качения)", min_value=0.0, value=DEFAULT_BEARING_PARAMS['BSF'], format="%.2f")
        ftf = st.number_input("FTF (сепаратор)", min_value=0.0, value=DEFAULT_BEARING_PARAMS['FTF'], format="%.2f")
        n_b = st.number_input("N_B (количество тел качения)", min_value=1, value=DEFAULT_BEARING_PARAMS['N_B'], step=1)

    st.write("**Настройки отображения графика:**")
    use_db_scale_bearing = st.checkbox("Использовать логарифмическую шкалу (дБ)", value=True, key="db_scale_bearing",
                                    help="Рекомендуется для MCSA, чтобы увидеть слабые боковые полосы.")

    if st.button("🚀 Запустить анализ дефектов подшипника"):
        with st.spinner("Анализирую спектр тока... Пожалуйста, подождите."):
            signal_data = df[selected_signal].values
            bearing_params = {'BPFO': bpfo, 'BPFI': bpfi, 'BSF': bsf, 'FTF': ftf, 'N_B': n_b}

            analyzer = BearingDefectAnalyzer(signal=signal_data, sampling_rate=SAMPLING_RATE, rpm=RPM, bearing_params=bearing_params)
            report = analyzer.run_analysis()
            fig_bearing = analyzer.plot_spectrum(use_db_scale=use_db_scale_bearing)

            st.write("### 📈 Результаты диагностики (MCSA)")
            
            if not report:
                st.error("Анализ не был выполнен.")
            else:
                with st.expander("📝 **Сводный отчет по дефектам**", expanded=True):
                    defect_freqs = report.get('Defect Frequencies', {})
                    if not defect_freqs:
                        st.success("Явных признаков дефектов по боковым полосам частот не обнаружено.")
                    else:
                        for defect, message in defect_freqs.items():
                            st.warning(f"**{defect}:** {message}")

                st.plotly_chart(fig_bearing, use_container_width=True)
            
                with st.expander("📄 **Детализация по найденным боковым полосам**"):
                    all_found_peaks = [item for sublist in analyzer.found_peaks.values() for item in sublist]
                    
                    if all_found_peaks:
                        df_details = pd.DataFrame(all_found_peaks)
                        st.dataframe(df_details[['defect_type', 'order', 'side', 'found_freq_hz', 'amplitude']].style.format({
                            'found_freq_hz': '{:.2f}',
                            'amplitude': '{:.5f}'
                        }))
                    else:
                        st.info("Значимых боковых полос, указывающих на дефекты, не найдено.")