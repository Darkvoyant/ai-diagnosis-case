import numpy as np
import pandas as pd
from scipy.fft import fft, fftfreq
from scipy.signal import find_peaks
import plotly.graph_objects as go

class BearingDefectAnalyzer:
    """
    Модуль для спектрального анализа тока двигателя (MCSA) с целью
    идентификации дефектов подшипников качения.
    """
    def __init__(self, signal, sampling_rate, rpm, bearing_params):
        self.signal = np.array(signal)
        self.sampling_rate = sampling_rate
        self.rpm = rpm
        self.bearing_params = bearing_params

        self.rpm_hz = self.rpm / 60.0
        self.n_samples = len(self.signal)

        self.xf = None
        self.yf_amp = None
        self.report = {}
        self.found_peaks = {}
        self.all_peaks_indices = None
        self.line_freq = None

    def _perform_fft(self):
        """1. Выполняет БПФ и подготавливает амплитудный спектр."""
        yf = fft(self.signal)
        self.xf = fftfreq(self.n_samples, 1 / self.sampling_rate)

        n_pos = self.n_samples // 2
        self.xf = self.xf[0:n_pos]
        self.yf_amp = 2.0 / self.n_samples * np.abs(yf[0:n_pos])
        
        # Для MCSA амплитуды очень малы, поэтому ищем пики, которые хотя бы немного выделяются
        min_prominence = self.yf_amp[self.yf_amp > 0].std()
        self.all_peaks_indices, _ = find_peaks(self.yf_amp, prominence=min_prominence)

    def _find_line_frequency(self, search_range=(45, 55)):
        """2. Находит основную частоту сети."""
        mask = (self.xf > search_range[0]) & (self.xf < search_range[1])
        if not np.any(mask):
            self.line_freq = None
            return

        # Находим частоту пика с максимальной амплитудой в диапазоне
        peak_indices_in_range = self.all_peaks_indices[
            (self.xf[self.all_peaks_indices] > search_range[0]) & 
            (self.xf[self.all_peaks_indices] < search_range[1])
        ]
        if len(peak_indices_in_range) == 0:
            self.line_freq = None
            return
            
        main_peak_idx = peak_indices_in_range[np.argmax(self.yf_amp[peak_indices_in_range])]
        self.line_freq = self.xf[main_peak_idx]


    def _find_mcs_sidebands(self, defect_name, base_freq, max_order, tolerance):
        """Универсальная функция для поиска боковых полос MCSA."""
        found_sidebands = []
        if self.line_freq is None or len(self.all_peaks_indices) == 0 or base_freq <= 0:
            return found_sidebands

        for k in range(1, max_order + 1):
            target_freqs = [self.line_freq - k * base_freq, self.line_freq + k * base_freq]
            
            for side, target_freq in enumerate(target_freqs):
                if target_freq < 0: continue

                peak_distances = np.abs(self.xf[self.all_peaks_indices] - target_freq)
                closest_peak_index_in_peaks_array = np.argmin(peak_distances)

                if peak_distances[closest_peak_index_in_peaks_array] < tolerance:
                    best_peak_idx = self.all_peaks_indices[closest_peak_index_in_peaks_array]
                    
                    sideband_info = {
                        'defect_type': defect_name, 'order': k,
                        'side': 'lower' if side == 0 else 'upper',
                        'target_freq_hz': target_freq,
                        'found_freq_hz': self.xf[best_peak_idx],
                        'amplitude': self.yf_amp[best_peak_idx]
                    }
                    found_sidebands.append(sideband_info)
        return found_sidebands

    def _analyze_defect_frequencies(self):
        """3. Анализ характерных частот дефектов методом MCSA."""
        report = {}
        tolerance = 1.5 # Гц, можно немного увеличить допуск

        # BPFO (Outer Ring)
        bpfo_sbs = self._find_mcs_sidebands('BPFO', self.bearing_params['BPFO'], 2, tolerance)
        self.found_peaks['BPFO'] = bpfo_sbs
        if len(bpfo_sbs) >= 2:
            report['Outer Ring Defect (BPFO)'] = f"Обнаружено {len(bpfo_sbs)} боковых полос BPFO. Возможен дефект наружного кольца."

        # BPFI (Inner Ring)
        bpfi_sbs = self._find_mcs_sidebands('BPFI', self.bearing_params['BPFI'], 2, tolerance)
        self.found_peaks['BPFI'] = bpfi_sbs
        if len(bpfi_sbs) >= 2:
            report['Inner Ring Defect (BPFI)'] = f"Обнаружено {len(bpfi_sbs)} боковых полос BPFI. Возможен дефект внутреннего кольца."

        # BSF (Rolling Element)
        bsf_sbs = self._find_mcs_sidebands('BSF', self.bearing_params['BSF'], 2, tolerance)
        self.found_peaks['BSF'] = bsf_sbs
        if len(bsf_sbs) >= 2:
            report['Rolling Element Defect (BSF)'] = f"Обнаружено {len(bsf_sbs)} боковых полос BSF. Возможен дефект тел качения."

        # FTF (Cage)
        ftf_sbs = self._find_mcs_sidebands('FTF', self.bearing_params['FTF'], 2, tolerance)
        self.found_peaks['FTF'] = ftf_sbs
        if len(ftf_sbs) >= 1:
            report['Cage Defect (FTF)'] = f"Обнаружено {len(ftf_sbs)} боковых полос FTF. Возможен дефект сепаратора."
            
        return report

    def run_analysis(self):
        """Запускает полный цикл анализа."""
        self._perform_fft()
        self._find_line_frequency()
        if self.line_freq is None:
            st.warning("Не удалось определить основную частоту сети. Анализ дефектов невозможен.")
            return {}
            
        self.report['Defect Frequencies'] = self._analyze_defect_frequencies()
        return self.report

    def plot_spectrum(self, use_db_scale=False):
        """
        Строит интерактивный график спектра с улучшенной визуализацией.
        :param use_db_scale: Использовать логарифмическую шкалу (дБ) для амплитуды.
        """
        fig = go.Figure()
        
        if self.xf is None or self.line_freq is None:
            return fig

        # --- УЛУЧШЕННАЯ ЛОГИКА ВИЗУАЛИЗАЦИИ ---
        max_defect_freq = max(self.bearing_params.get(k, 0) for k in ['BPFO', 'BPFI', 'BSF'])
        if max_defect_freq == 0: max_defect_freq = 165 # Значение по умолчанию, если ничего не введено

        zoom_range = (self.line_freq - max_defect_freq * 2.5, self.line_freq + max_defect_freq * 2.5)
        zoom_range = (max(0, zoom_range[0]), zoom_range[1]) # Не уходим в отрицательные частоты

        # Преобразование в дБ, если опция включена
        if use_db_scale:
            yf_display = 20 * np.log10(self.yf_amp + 1e-9) # Добавляем малое число, чтобы избежать log(0)
            yaxis_title = "Амплитуда (дБ)"
            line_freq_amp_display = 20 * np.log10(self.yf_amp[np.argmin(np.abs(self.xf - self.line_freq))] + 1e-9)
        else:
            yf_display = self.yf_amp
            yaxis_title = "Амплитуда"
            line_freq_amp_display = self.yf_amp.max()

        fig.add_trace(go.Scatter(x=self.xf, y=yf_display, mode='lines', name='Спектр тока', line=dict(color='royalblue')))
        
        fig.add_vline(x=self.line_freq, line_width=2, line_dash="dash", line_color="green",
                      annotation_text=f"Line Freq: {self.line_freq:.2f} Hz", annotation_position="bottom right")

        # --- Добавляем маркеры, показывающие ГДЕ мы ищем дефекты ---
        target_markers_x = []
        for defect_type, base_freq in self.bearing_params.items():
            if defect_type in ['BPFO', 'BPFI', 'BSF', 'FTF'] and base_freq > 0:
                for k in range(1, 3):
                    for sign in [-1, 1]:
                        target_freq = self.line_freq + sign * k * base_freq
                        if target_freq > 0:
                            fig.add_vline(x=target_freq, line_width=1, line_dash="dot", line_color="rgba(128, 128, 128, 0.7)",
                                          annotation_text=f"{defect_type} SB{k}", annotation_position="top")

        # --- Отмечаем найденные пики ---
        all_found_peaks = [item for sublist in self.found_peaks.values() for item in sublist]
        if all_found_peaks:
            freqs = [p['found_freq_hz'] for p in all_found_peaks]
            labels = [f"{p['defect_type']}<br>{p['side'][0].upper()}SB{p['order']}<br>{p['amplitude']:.4f}" for p in all_found_peaks]
            
            if use_db_scale:
                amps = 20 * np.log10(np.array([p['amplitude'] for p in all_found_peaks]) + 1e-9)
            else:
                amps = [p['amplitude'] for p in all_found_peaks]
            
            fig.add_trace(go.Scatter(
                x=freqs, y=amps, text=labels, mode='markers+text',
                marker=dict(symbol='x', color='red', size=10, line=dict(width=2)),
                textposition="bottom center", name='Найденные дефекты', textfont=dict(size=10, color='red')
            ))

        # Динамическое масштабирование оси Y для лучшей видимости
        zoom_mask = (self.xf >= zoom_range[0]) & (self.xf <= zoom_range[1])
        if np.any(zoom_mask):
            visible_amps = yf_display[zoom_mask]
            # Исключаем гигантский пик основной частоты из автомасштабирования
            if use_db_scale:
                 y_range_max = np.max(visible_amps[visible_amps < line_freq_amp_display - 3]) if np.any(visible_amps < line_freq_amp_display - 3) else np.max(visible_amps)
                 y_range_min = np.min(visible_amps)
            else:
                 y_range_max = np.max(visible_amps[visible_amps < self.yf_amp.max() * 0.5]) if np.any(visible_amps < self.yf_amp.max() * 0.5) else np.max(visible_amps)
                 y_range_min = 0
            
            yaxis_range = [y_range_min * 0.9, y_range_max * 1.5]
        else:
            yaxis_range = None # Автомасштаб по умолчанию

        fig.update_layout(
            title="Спектральный анализ тока (MCSA) - Область поиска дефектов",
            xaxis_title="Частота (Гц)", yaxis_title=yaxis_title,
            xaxis_range=zoom_range, yaxis_range=yaxis_range,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        return fig