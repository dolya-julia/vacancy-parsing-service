
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from orchestrator import (
    load_config, resolve_path, run_parser, import_existing_csv
)
from database import init_db
from analytics import (
    get_vacancies, get_runs, get_stats, get_logs,
    source_summary, region_summary, skill_summary,
    field_completeness, stats_summary
)


st.set_page_config(
    page_title="Сервис анализа вакансий",
    page_icon="📊",
    layout="wide"
)

config = load_config()
DB_PATH = resolve_path(config["database_path"])
init_db(DB_PATH)

st.title("Сервис сбора и анализа вакансий")
st.caption(
    "Сбор данных, предобработка, хранение, аналитика "
    "и контроль выполнения парсеров"
)


def refresh_data():
    st.session_state["refresh"] = (
        st.session_state.get("refresh", 0) + 1
    )


def load_data():
    return (
        get_vacancies(DB_PATH),
        get_runs(DB_PATH),
        get_stats(DB_PATH),
        get_logs(DB_PATH)
    )


vacancies, runs, stats, logs = load_data()

tab_control, tab_vacancies, tab_analytics, tab_logs = st.tabs([
    "Управление сбором",
    "Вакансии",
    "Аналитика",
    "Журнал и тестирование"
])


# ---------------------------------------------------------
# 1. Управление сбором
# ---------------------------------------------------------
with tab_control:
    st.subheader("Управление процессами")

    st.write(
        "Выбери парсер. Если команда запуска не настроена, "
        "используй импорт ранее сформированных CSV."
    )

    parser_choice = st.selectbox(
        "Парсер",
        ["C#", "Python (Scrapy)"]
    )
    parser_name = "C#" if parser_choice == "C#" else "Python"

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "Импортировать готовые CSV",
            use_container_width=True
        ):
            with st.spinner("Импорт данных..."):
                result = import_existing_csv(parser_name)

            if result["ok"]:
                st.success(result["message"])
            else:
                st.error(result["message"])

            refresh_data()
            st.rerun()

    with col2:
        if st.button(
            "Запустить парсер и импортировать результат",
            use_container_width=True
        ):
            prefix = "csharp" if parser_name == "C#" else "python"
            command = config.get(f"{prefix}_command", [])

            if not command:
                st.warning(
                    "Команда запуска не настроена в config.json. "
                    "Заполни соответствующее поле команды."
                )
            else:
                with st.spinner("Выполняется сбор данных..."):
                    result = run_parser(parser_name)

                if result["ok"]:
                    st.success(result["message"])
                else:
                    st.error(result["message"])

                refresh_data()
                st.rerun()

    st.divider()
    st.subheader("Состояние базы данных")

    col1, col2, col3 = st.columns(3)
    col1.metric("Вакансии в базе", len(vacancies))
    col2.metric("Запуски", len(runs))
    col3.metric("Записи статистики", len(stats))

    st.caption(f"Файл базы данных: {DB_PATH}")


# ---------------------------------------------------------
# 2. Просмотр и фильтрация вакансий
# ---------------------------------------------------------
with tab_vacancies:
    st.subheader("Каталог вакансий")

    if vacancies.empty:
        st.info(
            "В базе пока нет вакансий. Импортируй CSV "
            "на вкладке «Управление сбором»."
        )
    else:
        data = vacancies.copy()

        col1, col2, col3 = st.columns(3)

        sources = sorted([
            x for x in data["source"].dropna().unique()
            if str(x).strip()
        ])
        source_filter = col1.multiselect(
            "Источник",
            sources,
            default=sources
        )

        regions = sorted([
            x for x in data["region"].dropna().unique()
            if str(x).strip()
        ])
        region_filter = col2.multiselect(
            "Регион",
            regions
        )

        queries = sorted([
            x for x in data["query"].dropna().unique()
            if str(x).strip()
        ])
        query_filter = col3.multiselect(
            "Поисковый запрос",
            queries
        )

        search = st.text_input(
            "Поиск по должности, компании, описанию и навыкам"
        )

        data = data[data["source"].isin(source_filter)]

        if region_filter:
            data = data[data["region"].isin(region_filter)]

        if query_filter:
            data = data[data["query"].isin(query_filter)]

        if search.strip():
            mask = (
                data["title"].fillna("").astype(str) + " " +
                data["company"].fillna("").astype(str) + " " +
                data["description"].fillna("").astype(str) + " " +
                data["skills"].fillna("").astype(str)
            ).str.contains(search, case=False, regex=False)

            data = data[mask]

        st.metric("Вакансий после фильтрации", len(data))

        display_columns = [
            "source", "title", "company", "region",
            "salary", "skills", "query", "collected_at", "url"
        ]
        display_columns = [
            c for c in display_columns if c in data.columns
        ]

        st.dataframe(
            data[display_columns],
            use_container_width=True,
            hide_index=True,
            column_config={
                "url": st.column_config.LinkColumn(
                    "Ссылка на вакансию"
                )
            }
        )

        csv_bytes = data[display_columns].to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            "Экспортировать отфильтрованные вакансии в CSV",
            data=csv_bytes,
            file_name="vacancies_filtered.csv",
            mime="text/csv"
        )


# ---------------------------------------------------------
# 3. Аналитика
# ---------------------------------------------------------
with tab_analytics:
    st.subheader("Аналитика вакансий")

    if vacancies.empty:
        st.info("Для построения аналитики сначала импортируй данные.")
    else:
        source_data = source_summary(vacancies)
        region_data = region_summary(vacancies)
        skills_data = skill_summary(vacancies)
        completeness = field_completeness(vacancies)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Количество вакансий по источникам**")
            fig = px.bar(
                source_data,
                x="source", y="count",
                labels={
                    "source": "Источник",
                    "count": "Количество вакансий"
                }
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**Количество вакансий по регионам**")
            top_regions = region_data.head(15)
            fig = px.bar(
                top_regions,
                x="count", y="region",
                orientation="h",
                labels={
                    "region": "Регион",
                    "count": "Количество вакансий"
                }
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Частота упоминания навыков**")
        if not skills_data.empty:
            fig = px.bar(
                skills_data.head(20),
                x="skill", y="mentions",
                labels={
                    "skill": "Навык",
                    "mentions": "Число упоминаний"
                }
            )
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(skills_data, hide_index=True)
        else:
            st.info(
                "В выбранных полях не обнаружены навыки "
                "из текущего словаря."
            )

        st.markdown("**Полнота заполнения полей**")
        fig = px.bar(
            completeness,
            x="field", y="completeness_percent",
            range_y=[0, 100],
            labels={
                "field": "Поле",
                "completeness_percent": "Заполнено, %"
            }
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(completeness, hide_index=True)

        st.markdown("**Зарплаты**")
        st.caption(
            "Зарплаты сохранены в исходном текстовом формате. "
            "Сравнивать их численно можно после нормализации "
            "валюты, периода и диапазонов."
        )


# ---------------------------------------------------------
# 4. Журналирование и исследовательское тестирование
# ---------------------------------------------------------
with tab_logs:
    st.subheader("История запусков")

    if runs.empty:
        st.info("Запусков пока нет.")
    else:
        st.dataframe(
            runs.sort_values("id", ascending=False),
            use_container_width=True,
            hide_index=True
        )

    st.subheader("Статистика парсеров")

    if stats.empty:
        st.info("Статистика парсеров ещё не импортирована.")
    else:
        summary = stats_summary(stats)
        st.dataframe(summary, use_container_width=True, hide_index=True)

        timed = stats.copy()
        timed["elapsed_ms"] = pd.to_numeric(
            timed["elapsed_ms"], errors="coerce"
        )
        timed["page"] = pd.to_numeric(
            timed["page"], errors="coerce"
        )
        timed = timed.dropna(subset=["elapsed_ms"])

        if not timed.empty:
            fig = px.line(
                timed,
                x="page", y="elapsed_ms",
                color="parser",
                markers=True,
                hover_data=["source", "query", "status"],
                labels={
                    "page": "Номер страницы",
                    "elapsed_ms": "Время обработки, мс",
                    "parser": "Парсер"
                },
                title="Время обработки страниц"
            )
            st.plotly_chart(fig, use_container_width=True)

            if "status" in timed.columns:
                status_data = (
                    timed.groupby(["parser", "status"])
                    .size().reset_index(name="count")
                )
                fig = px.bar(
                    status_data,
                    x="status", y="count", color="parser",
                    barmode="group",
                    labels={
                        "status": "Статус",
                        "count": "Количество страниц"
                    },
                    title="Статусы обработки страниц"
                )
                st.plotly_chart(fig, use_container_width=True)

    st.subheader("Журнал событий")

    if logs.empty:
        st.info("Записи журнала пока отсутствуют.")
    else:
        level_options = sorted(logs["level"].dropna().unique())
        selected_levels = st.multiselect(
            "Уровень события",
            level_options,
            default=level_options
        )

        filtered_logs = logs[logs["level"].isin(selected_levels)]
        st.dataframe(
            filtered_logs.sort_values("id", ascending=False),
            use_container_width=True,
            hide_index=True
        )
