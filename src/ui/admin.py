# src/ui/admin.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ГЕНЕРАЦИЯ ПРОФЕССИОНАЛЬНЫХ МОК-ДАННЫХ ---
@st.cache_data
def generate_mock_admin_data(num_engines=42):
    """
    Создает детализированный DataFrame для имитации реальной бизнес-аналитики.
    """
    np.random.seed(42) # Для воспроизводимости
    
    # Справочники
    models = ["АДМ-150", "АДМ-200-S", "ВЭМ-315"]
    locations = ["Цех 1", "Цех 2", "Насосная станция"]
    failure_reasons = [
        "Дефект внешней дорожки", "Межвитковые замыкания", "Обрыв стержней ротора",
        "Асимметрия фазных токов", "Дефект сепаратора", "Другое"
    ]
    
    data = {
        "engine_id": [f"М{str(i).zfill(2)}" for i in range(1, num_engines + 1)],
        "model": np.random.choice(models, num_engines, p=[0.5, 0.3, 0.2]),
        "location": np.random.choice(locations, num_engines, p=[0.6, 0.3, 0.1]),
        "failures_last_12m": np.random.randint(0, 15, num_engines),
        "oee_percentage": np.random.normal(85, 8, num_engines).clip(50, 99),
        "last_failure_type": np.random.choice(failure_reasons, num_engines, p=[0.3, 0.2, 0.15, 0.15, 0.1, 0.1]),
    }
    df = pd.DataFrame(data)
    
    # Вычисляемые поля
    df['total_downtime_hours'] = df['failures_last_12m'] * np.random.normal(4, 2, num_engines).clip(1, 10)
    df['avg_repair_time_hours'] = (df['total_downtime_hours'] / df['failures_last_12m']).fillna(0)
    
    # MTBF (Mean Time Between Failures) - среднее время наработки на отказ
    df['mtbf_hours'] = (365 * 24 / (df['failures_last_12m'] + 1)).astype(int) # +1 чтобы избежать деления на ноль
    
    # Стоимость простоя
    location_cost = {"Цех 1": 15000, "Цех 2": 25000, "Насосная станция": 18000}
    df['cost_per_downtime_hour'] = df['location'].map(location_cost)
    df['total_cost_downtime'] = df['total_downtime_hours'] * df['cost_per_downtime_hour']
    
    return df

# --- 2. ГЛАВНАЯ ФУНКЦИЯ ОТОБРАЖЕНИЯ ---
def display_admin_page():
    st.markdown("---")
    st.header("📊 Панель руководителя: Аналитика парка оборудования")
    st.info("Эта панель предоставляет стратегический обзор производительности, надежности и экономической эффективности парка двигателей.")
    
    # Загружаем или генерируем данные
    df_analytics = generate_mock_admin_data()

    # --- ВКЛАДКИ ДЛЯ РАЗНЫХ УРОВНЕЙ АНАЛИЗА ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 **Сводная панель (Dashboard)**",
        "⚙️ **Анализ OEE и Производительности**",
        "🛠️ **Анализ Отказов и Надежности**",
        "💰 **Экономический Анализ**"
    ])

    # --- ВКЛАДКА 1: СВОДНАЯ ПАНЕЛЬ ---
    with tab1:
        st.subheader("Ключевые показатели эффективности (KPI) за последние 12 месяцев")
        
        # --- Главные KPI ---
        kpi_cols = st.columns(4)
        total_downtime_cost_y = df_analytics['total_cost_downtime'].sum()
        avg_oee = df_analytics['oee_percentage'].mean()
        total_failures = df_analytics['failures_last_12m'].sum()
        avg_mtbf = df_analytics['mtbf_hours'].mean()

        kpi_cols[0].metric("💸 Потери от простоев", f"{total_downtime_cost_y/1e6:.2f} млн ₽", delta="Год к году", delta_color="off")
        kpi_cols[1].metric("📈 Средний OEE", f"{avg_oee:.1f}%", f"{avg_oee-85:.1f}% vs. цель (85%)")
        kpi_cols[2].metric("🚨 Всего отказов", f"{total_failures}", f"{total_failures - 250} vs. прошлый год")
        kpi_cols[3].metric("⏳ Средняя наработка на отказ (MTBF)", f"{int(avg_mtbf)} ч.", f"{int(avg_mtbf - 800)} ч. vs. цель")

        st.markdown("---")
        
        # --- Визуализация ---
        viz_cols = st.columns([2,3])
        with viz_cols[0]:
            st.subheader("Состояние парка")
            status_counts = df_analytics.groupby('location')['engine_id'].count()
            fig_donut = go.Figure(data=[go.Pie(labels=status_counts.index, values=status_counts.values, hole=.5,
                                               marker_colors=['#1f77b4', '#ff7f0e', '#2ca02c'])])
            fig_donut.update_layout(title_text='Распределение двигателей по объектам', showlegend=False,
                                    annotations=[dict(text='42<br>шт.', x=0.5, y=0.5, font_size=20, showarrow=False)])
            st.plotly_chart(fig_donut, use_container_width=True)
            
        with viz_cols[1]:
            st.subheader("Проблемные активы")
            top_downtime = df_analytics.sort_values('total_downtime_hours', ascending=False).head(5)
            st.write("**ТОП-5 двигателей по суммарному простою:**")
            st.dataframe(top_downtime[['engine_id', 'model', 'location', 'total_downtime_hours']],
                         use_container_width=True, hide_index=True)

    # --- ВКЛАДКА 2: АНАЛИЗ OEE ---
    with tab2:
        st.subheader("Анализ общей эффективности оборудования (OEE)")
        oee_cols = st.columns(2)
        
        with oee_cols[0]:
            st.write("**Распределение OEE по моделям**")
            # Box plot для сравнения моделей
            fig_box = go.Figure()
            for model in df_analytics['model'].unique():
                fig_box.add_trace(go.Box(y=df_analytics[df_analytics['model'] == model]['oee_percentage'], name=model))
            fig_box.update_layout(yaxis_title="OEE, %", showlegend=False)
            st.plotly_chart(fig_box, use_container_width=True)
            
        with oee_cols[1]:
            st.write("**OEE vs. Количество отказов**")
            fig_scatter = go.Figure(data=go.Scatter(
                x=df_analytics['failures_last_12m'],
                y=df_analytics['oee_percentage'],
                mode='markers',
                marker=dict(size=10, color=df_analytics['total_cost_downtime'], colorscale='Viridis', showscale=True, colorbar_title="Потери от простоя"),
                text=df_analytics['engine_id']
            ))
            fig_scatter.update_layout(xaxis_title="Количество отказов за год", yaxis_title="OEE, %")
            st.plotly_chart(fig_scatter, use_container_width=True)
            
        st.write("**Детализация по всем двигателям:**")
        st.dataframe(df_analytics[['engine_id', 'model', 'location', 'oee_percentage', 'failures_last_12m', 'mtbf_hours']],
                     use_container_width=True, hide_index=True)

    # --- ВКЛАДКА 3: АНАЛИЗ ОТКАЗОВ ---
    with tab3:
        st.subheader("Анализ отказов и надежности")
        
        # --- Анализ Парето ---
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
        st.info("💡 **80/20 правило:** Фокусируйтесь на первых 2-3 причинах, чтобы устранить ~80% всех проблем.")

        st.write("**Матрица Надежности: MTBF vs. MTTR (Среднее время ремонта)**")
        fig_mtbf = go.Figure(data=go.Scatter(
            x=df_analytics['mtbf_hours'],
            y=df_analytics['avg_repair_time_hours'],
            mode='markers',
            marker=dict(size=df_analytics['failures_last_12m']+5, color=df_analytics['oee_percentage'], colorscale='RdYlGn', showscale=True, colorbar_title="OEE, %"),
            text=df_analytics['engine_id']
        ))
        fig_mtbf.update_layout(xaxis_title="MTBF (Наработка на отказ, ч.) →", yaxis_title="MTTR (Среднее время ремонта, ч.) →")
        st.plotly_chart(fig_mtbf, use_container_width=True)

    # --- ВКЛАДКА 4: ЭКОНОМИЧЕСКИЙ АНАЛИЗ ---
    with tab4:
        st.subheader("Анализ экономической эффективности")
        
        cost_cols = st.columns(2)
        with cost_cols[0]:
            st.write("**Структура потерь от простоев по объектам**")
            cost_by_location = df_analytics.groupby('location')['total_cost_downtime'].sum()
            fig_cost_pie = go.Figure(data=[go.Pie(labels=cost_by_location.index, values=cost_by_location.values, textinfo='percent+label')])
            st.plotly_chart(fig_cost_pie, use_container_width=True)
            
        with cost_cols[1]:
            st.write("**Структура потерь по моделям двигателей**")
            cost_by_model = df_analytics.groupby('model')['total_cost_downtime'].sum()
            fig_cost_bar = go.Figure(data=[go.Bar(x=cost_by_model.index, y=cost_by_model.values)])
            fig_cost_bar.update_layout(yaxis_title="Суммарные потери, ₽")
            st.plotly_chart(fig_cost_bar, use_container_width=True)
        
        st.markdown("---")
        st.write("**Расчет потенциальной экономии**")
        st.info("Инструмент для оценки возврата инвестиций (ROI) в предиктивное обслуживание.")
        
        # Интерактивный симулятор
        reduction_percentage = st.slider("Прогнозируемое снижение отказов (%)", 0, 100, 20)
        potential_failures_avoided = (total_failures * reduction_percentage / 100)
        avg_cost_per_failure = total_downtime_cost_y / total_failures if total_failures > 0 else 0
        potential_savings = potential_failures_avoided * avg_cost_per_failure
        
        st.metric("💰 **Потенциальная годовая экономия**", f"{potential_savings/1e6:.2f} млн ₽")