import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from fpdf import FPDF
import os
import io
from datetime import datetime

# --- 1. ГЕНЕРАЦИЯ ПРОФЕССИОНАЛЬНЫХ МОК-ДАННЫХ (БЕЗ ИЗМЕНЕНИЙ) ---
@st.cache_data
def generate_mock_admin_data(num_engines=42):
    np.random.seed(42)
    models = ["АДМ-150", "АДМ-200-S", "ВЭМ-315"]
    locations = ["Цех 1", "Цех 2", "Насосная станция"]
    failure_reasons = ["Дефект внешней дорожки", "Межвитковые замыкания", "Обрыв стержней ротора",
                       "Асимметрия фазных токов", "Дефект сепаратора", "Другое"]
    data = {"engine_id": [f"М{str(i).zfill(2)}" for i in range(1, num_engines + 1)],
            "model": np.random.choice(models, num_engines, p=[0.5, 0.3, 0.2]),
            "location": np.random.choice(locations, num_engines, p=[0.6, 0.3, 0.1]),
            "failures_last_12m": np.random.randint(0, 15, num_engines),
            "oee_percentage": np.random.normal(85, 8, num_engines).clip(50, 99),
            "last_failure_type": np.random.choice(failure_reasons, num_engines, p=[0.3, 0.2, 0.15, 0.15, 0.1, 0.1])}
    df = pd.DataFrame(data)
    df['total_downtime_hours'] = df['failures_last_12m'] * np.random.normal(4, 2, num_engines).clip(1, 10)
    df['avg_repair_time_hours'] = (df['total_downtime_hours'] / df['failures_last_12m']).fillna(0)
    df['mtbf_hours'] = (365 * 24 / (df['failures_last_12m'] + 1)).astype(int)
    return df

# --- ФУНКЦИЯ ДЛЯ ГЕНЕРАЦИИ PDF (ИСПРАВЛЕННАЯ И ПОЛНАЯ ВЕРСИЯ) ---
def generate_pdf_report(df_analytics, figs):
    """
    Генерирует PDF-отчет профессионального уровня с титульной страницей,
    аналитическими выводами и улучшенным дизайном.
    """
    # --- 1. Настройки дизайна ---
    LOGO_PATH = "logo.png"
    PRIMARY_COLOR = (47, 85, 151)
    SECONDARY_COLOR = (128, 128, 128)
    TABLE_HEADER_BG = (221, 235, 247)
    TABLE_ROW_ALT_BG = (242, 242, 242)
    report_date = datetime.now().strftime("%d.%m.%Y")
    FONT_PATH = 'DejaVuSansCondensed.ttf'

    class PDF(FPDF):
        def header(self):
            if self.page_no() == 1: return
            if not os.path.exists(FONT_PATH): return
            self.add_font('DejaVu', '', FONT_PATH, uni=True)
            self.set_font('DejaVu', '', 9)
            self.set_text_color(*SECONDARY_COLOR)
            self.cell(0, 10, 'Аналитический отчет по парку оборудования', 0, 0, 'L')
            self.cell(0, 10, report_date, 0, 0, 'R')
            self.ln(15)

        def footer(self):
            self.set_y(-15)
            if not os.path.exists(FONT_PATH): return
            self.add_font('DejaVu', '', FONT_PATH, uni=True)
            self.set_font('DejaVu', '', 8)
            self.set_text_color(*SECONDARY_COLOR)
            self.cell(0, 10, f'Страница {self.page_no()}', 0, 0, 'C')

        def section_title(self, title):
            self.set_font('DejaVu', '', 16)
            self.set_text_color(*PRIMARY_COLOR)
            self.cell(0, 10, title, 0, 1, 'L')
            self.set_draw_color(*PRIMARY_COLOR)
            self.line(self.get_x(), self.get_y(), self.get_x() + 190, self.get_y())
            self.ln(10)
        
        def write_interpretation(self, text):
            self.set_font('DejaVu', '', 10)
            self.set_text_color(0, 0, 0)
            self.multi_cell(0, 5, text)
            self.ln(5)

        def add_chart_with_interpretation(self, title, fig, interpretation):
            if self.get_y() + 115 > self.h - self.b_margin: self.add_page()
            self.set_font('DejaVu', '', 12)
            self.set_text_color(0, 0, 0)
            self.cell(0, 6, title, 0, 1)
            self.ln(2)
            self.write_interpretation(interpretation)
            fig.update_layout(template="plotly_white")
            img_bytes = fig.to_image(format="png", width=700, height=400, scale=2)
            with io.BytesIO(img_bytes) as img_file: self.image(img_file, w=170)
            self.ln(5)

    pdf = PDF('P', 'mm', 'A4')
    if not os.path.exists(FONT_PATH):
        st.error(f"Шрифт '{FONT_PATH}' не найден. PDF-отчет не может быть создан.")
        return None
    
    pdf.add_font('DejaVu', '', FONT_PATH, uni=True)
    pdf.add_page()

    if os.path.exists(LOGO_PATH): pdf.image(LOGO_PATH, x=10, y=20, w=50)
    pdf.set_y(100)
    pdf.set_font('DejaVu', '', 28)
    pdf.set_text_color(*PRIMARY_COLOR)
    pdf.cell(0, 15, "Аналитический отчет", 0, 1, 'C')
    pdf.set_font('DejaVu', '', 18)
    pdf.cell(0, 12, "Состояние парка промышленного оборудования", 0, 1, 'C')
    pdf.set_y(220)
    pdf.set_font('DejaVu', '', 12)
    pdf.set_text_color(*SECONDARY_COLOR)
    pdf.cell(0, 8, f"Дата формирования: {report_date}", 0, 1, 'C')
    pdf.cell(0, 8, "Исполнитель: Администратор", 0, 1, 'C')

    pdf.add_page()
    pdf.section_title("1. Ключевые показатели эффективности (KPI)")
    total_downtime_hours = df_analytics['total_downtime_hours'].sum()
    avg_oee = df_analytics['oee_percentage'].mean()
    total_failures = df_analytics['failures_last_12m'].sum()
    kpi_text = (f"Средняя Общая Эффективность Оборудования (OEE) составляет {avg_oee:.1f}%, что незначительно "
                f"отклоняется от целевого показателя в 85%.\n\nЗа последние 12 месяцев зафиксировано {total_failures} отказов, "
                f"что привело к суммарному простою в {int(total_downtime_hours)} часов.")
    pdf.set_font('DejaVu', '', 10)
    pdf.multi_cell(0, 5, kpi_text)
    pdf.ln(10)

    pdf.section_title("2. Визуальный анализ состояния парка")
    if 'Распределение по объектам' in figs:
        pdf.add_chart_with_interpretation( '2.1 Распределение двигателей по объектам', figs['Распределение по объектам'],
            "Вывод: Наибольшее количество оборудования сконцентрировано в 'Цехе 1', "
            "что делает его приоритетным объектом для мониторинга и обслуживания.")
    if 'Анализ Парето' in figs:
        pdf.add_chart_with_interpretation( '2.2 Анализ Парето по причинам отказов', figs['Анализ Парето'],
            "Вывод: Около 80% всех отказов вызваны тремя основными причинами. Устранение 'Дефекта внешней дорожки' и "
            "'Межвитковых замыканий' даст наибольший эффект в повышении общей надежности.")
        
    # --- ВОССТАНОВЛЕННЫЙ РАЗДЕЛ 3 ---
    pdf.section_title("3. Анализ производительности и надежности")

    if 'OEE по моделям' in figs:
        pdf.add_chart_with_interpretation(
            '3.1 Эффективность (OEE) в разрезе моделей',
            figs['OEE по моделям'],
            "Вывод: Модель 'АДМ-150' показывает наибольший разброс в значениях OEE, что указывает на "
            "нестабильность ее работы или разнородные условия эксплуатации. Модель 'ВЭМ-315', напротив, "
            "демонстрирует стабильно высокую эффективность."
        )
    
    if pdf.get_y() + 80 > pdf.h - pdf.b_margin: pdf.add_page()
    pdf.set_font('DejaVu', '', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, "3.2 Активы с наибольшим временем простоя", 0, 1)
    pdf.ln(2)
    pdf.write_interpretation(
        "Вывод: В таблице ниже представлены 5 двигателей, которые внесли наибольший вклад в общее "
        "время простоя. Эти активы являются главными кандидатами на внеплановое техническое "
        "обслуживание, углубленную диагностику или замену."
    )
    
    top_downtime = df_analytics.sort_values('total_downtime_hours', ascending=False).head(5)
    pdf.set_font('DejaVu', '', 10)
    pdf.set_fill_color(*TABLE_HEADER_BG)
    col_widths = {'id': 30, 'model': 35, 'loc': 50, 'down': 35, 'fail': 30}
    pdf.cell(col_widths['id'], 8, 'ID Двигателя', 1, 0, 'C', fill=True)
    pdf.cell(col_widths['model'], 8, 'Модель', 1, 0, 'C', fill=True)
    pdf.cell(col_widths['loc'], 8, 'Объект', 1, 0, 'C', fill=True)
    pdf.cell(col_widths['down'], 8, 'Часы простоя', 1, 0, 'C', fill=True)
    pdf.cell(col_widths['fail'], 8, 'Кол-во отказов', 1, 0, 'C', fill=True)
    pdf.ln()

    pdf.set_font('DejaVu', '', 9)
    fill = False
    for _, row in top_downtime.iterrows():
        pdf.set_fill_color(*TABLE_ROW_ALT_BG if fill else (255,255,255))
        pdf.cell(col_widths['id'], 7, str(row['engine_id']), 1, 0, 'C', fill=True)
        pdf.cell(col_widths['model'], 7, str(row['model']), 1, 0, 'C', fill=True)
        pdf.cell(col_widths['loc'], 7, str(row['location']), 1, 0, 'L', fill=True)
        pdf.cell(col_widths['down'], 7, f"{row['total_downtime_hours']:.1f}", 1, 0, 'C', fill=True)
        pdf.cell(col_widths['fail'], 7, str(row['failures_last_12m']), 1, 0, 'C', fill=True)
        pdf.ln()
        fill = not fill

    return bytes(pdf.output())

# --- 2. ГЛАВНАЯ ФУНКЦИЯ ОТОБРАЖЕНИЯ (БЕЗ ИЗМЕНЕНИЙ) ---
def display_admin_page():
    st.markdown("---")
    st.header("📊 Панель руководителя: Аналитика парка оборудования")
    st.info("Эта панель предоставляет стратегический обзор производительности, надежности и операционной эффективности парка двигателей.")

    df_analytics = generate_mock_admin_data()
    figs = {}

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 **Сводная панель (Dashboard)**",
        "⚙️ **Анализ OEE и Производительности**",
        "🛠️ **Анализ Отказов и Надежности**",
        "💡 **Анализ Потенциала Улучшений**",
        "📄 **Сгенерировать отчет (.pdf)**"
    ])

    with tab1:
        st.subheader("Ключевые показатели эффективности (KPI) за последние 12 месяцев")
        kpi_cols = st.columns(3)
        total_downtime_hours = df_analytics['total_downtime_hours'].sum()
        avg_oee = df_analytics['oee_percentage'].mean()
        total_failures = df_analytics['failures_last_12m'].sum()
        kpi_cols[0].metric("📈 Средний OEE", f"{avg_oee:.1f}%", f"{avg_oee-85:.1f}% vs. цель (85%)")
        kpi_cols[1].metric("🚨 Всего отказов", f"{total_failures}", f"{total_failures - 250} vs. прошлый год")
        kpi_cols[2].metric("⏳ Суммарный простой", f"{int(total_downtime_hours)} ч.", f"{int(total_downtime_hours - 1500)} ч. vs. прошлый год")
        st.markdown("---")
        viz_cols = st.columns([2, 3])
        with viz_cols[0]:
            st.subheader("Состояние парка")
            status_counts = df_analytics.groupby('location')['engine_id'].count()
            fig_donut = go.Figure(data=[go.Pie(labels=status_counts.index, values=status_counts.values, hole=.5, marker_colors=['#1f77b4', '#ff7f0e', '#2ca02c'])])
            fig_donut.update_layout(title_text='Распределение двигателей по объектам', showlegend=False, annotations=[dict(text='42<br>шт.', x=0.5, y=0.5, font_size=20, showarrow=False)])
            st.plotly_chart(fig_donut, use_container_width=True)
            figs['Распределение по объектам'] = fig_donut
        with viz_cols[1]:
            st.subheader("Проблемные двигатели")
            top_downtime = df_analytics.sort_values('total_downtime_hours', ascending=False).head(5)
            st.write("**ТОП-5 двигателей по суммарному простою:**")
            st.dataframe(top_downtime[['engine_id', 'model', 'location', 'total_downtime_hours', 'failures_last_12m']], use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Анализ общей эффективности оборудования (OEE)")
        oee_cols = st.columns(2)
        with oee_cols[0]:
            st.write("**Распределение OEE по моделям**")
            fig_box = go.Figure()
            for model in df_analytics['model'].unique():
                fig_box.add_trace(go.Box(y=df_analytics[df_analytics['model'] == model]['oee_percentage'], name=model))
            fig_box.update_layout(yaxis_title="OEE, %", showlegend=False)
            st.plotly_chart(fig_box, use_container_width=True)
            figs['OEE по моделям'] = fig_box
        with oee_cols[1]:
            st.write("**OEE vs. Количество отказов**")
            fig_scatter = go.Figure(data=go.Scatter(x=df_analytics['failures_last_12m'], y=df_analytics['oee_percentage'], mode='markers', marker=dict(size=10, color=df_analytics['total_downtime_hours'], colorscale='Viridis', showscale=True, colorbar_title="Часы простоя"), text=df_analytics['engine_id']))
            fig_scatter.update_layout(xaxis_title="Количество отказов за год", yaxis_title="OEE, %")
            st.plotly_chart(fig_scatter, use_container_width=True)
        st.write("**Детализация по всем двигателям:**")
        st.dataframe(df_analytics[['engine_id', 'model', 'location', 'oee_percentage', 'failures_last_12m', 'mtbf_hours']], use_container_width=True, hide_index=True)

    with tab3:
        st.subheader("Анализ отказов и надежности")
        st.write("**Ключевые причины отказов (Анализ Парето)**")
        reason_counts = df_analytics['last_failure_type'].value_counts()
        pareto_df = pd.DataFrame({'Reason': reason_counts.index, 'Count': reason_counts.values})
        pareto_df['Cumulative Percentage'] = (pareto_df['Count'].cumsum() / pareto_df['Count'].sum()) * 100
        fig_pareto = make_subplots(specs=[[{"secondary_y": True}]])
        fig_pareto.add_trace(go.Bar(x=pareto_df['Reason'], y=pareto_df['Count'], name='Кол-во отказов'), secondary_y=False)
        fig_pareto.add_trace(go.Scatter(x=pareto_df['Reason'], y=pareto_df['Cumulative Percentage'], name='Накопленный %', mode='lines+markers'), secondary_y=True)
        fig_pareto.update_layout(title_text="Анализ Парето для причин отказов", yaxis_title="Количество отказов")
        fig_pareto.update_yaxes(title_text="Накопленный процент", secondary_y=True)
        st.plotly_chart(fig_pareto, use_container_width=True)
        figs['Анализ Парето'] = fig_pareto
        st.write("**Матрица Надежности: MTBF vs. MTTR (Среднее время ремонта)**")
        fig_mtbf = go.Figure(data=go.Scatter(x=df_analytics['mtbf_hours'], y=df_analytics['avg_repair_time_hours'], mode='markers', marker=dict(size=df_analytics['failures_last_12m']+5, color=df_analytics['oee_percentage'], colorscale='RdYlGn', showscale=True, colorbar_title="OEE, %"), text=df_analytics['engine_id']))
        fig_mtbf.update_layout(xaxis_title="MTBF (Наработка на отказ, ч.) →", yaxis_title="MTTR (Среднее время ремонта, ч.) →")
        st.plotly_chart(fig_mtbf, use_container_width=True)

    with tab4:
        st.subheader("Анализ потенциала для повышения эффективности")
        cost_cols = st.columns(2)
        with cost_cols[0]:
            st.write("**Структура простоев по объектам**")
            downtime_by_location = df_analytics.groupby('location')['total_downtime_hours'].sum()
            fig_downtime_pie = go.Figure(data=[go.Pie(labels=downtime_by_location.index, values=downtime_by_location.values, textinfo='percent+label')])
            fig_downtime_pie.update_layout(title_text="Доля объектов в общем времени простоя")
            st.plotly_chart(fig_downtime_pie, use_container_width=True)
        with cost_cols[1]:
            st.write("**Структура простоев по моделям двигателей**")
            downtime_by_model = df_analytics.groupby('model')['total_downtime_hours'].sum()
            fig_downtime_bar = go.Figure(data=[go.Bar(x=downtime_by_model.index, y=downtime_by_model.values)])
            fig_downtime_bar.update_layout(yaxis_title="Суммарные часы простоя", title_text="Вклад моделей в общее время простоя")
            st.plotly_chart(fig_downtime_bar, use_container_width=True)
        st.markdown("---")
        st.write("**Оценка потенциального сокращения простоев**")
        st.info("Инструмент для оценки эффекта от внедрения предиктивного обслуживания или других улучшений.")
        reduction_percentage = st.slider("Прогнозируемое снижение отказов (%)", 0, 100, 20, help="Какой процент отказов можно предотвратить благодаря новым мерам?")
        if 'total_failures' not in locals():
            total_failures = df_analytics['failures_last_12m'].sum()
            total_downtime_hours = df_analytics['total_downtime_hours'].sum()
        avg_downtime_per_failure = total_downtime_hours / total_failures if total_failures > 0 else 0
        potential_failures_avoided = (total_failures * reduction_percentage / 100)
        potential_hours_saved = potential_failures_avoided * avg_downtime_per_failure
        st.metric("⏰ **Потенциальное сокращение времени простоя (в год)**", f"{potential_hours_saved:.0f} часов")

    with tab5:
        st.subheader("Генерация PDF-отчета")
        st.write("Нажмите кнопку ниже, чтобы сгенерировать и скачать полный аналитический отчет в формате PDF. В отчет будут включены ключевые графики с первых трех вкладок.")
        if st.button("Сгенерировать отчет"):
            with st.spinner("Создание отчета, пожалуйста, подождите..."):
                pdf_bytes = generate_pdf_report(df_analytics, figs)
                if pdf_bytes:
                    st.success("Отчет успешно создан!")
                    st.download_button(label="Нажмите, чтобы скачать PDF", data=pdf_bytes, file_name=f"analytical_report_{datetime.now().strftime('%Y-%m-%d')}.pdf", mime="application/pdf")

if __name__ == "__main__":
    st.set_page_config(layout="wide", page_title="Панель руководителя")
    display_admin_page()