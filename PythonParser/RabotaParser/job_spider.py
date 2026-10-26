import re
import time
from datetime import datetime, timezone
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit

import scrapy
from scrapy.crawler import CrawlerProcess


class JobSpider(scrapy.Spider):
    name = "job_spider"

    allowed_domains = [
        "career.habr.com",
        "rabota.ru",
        "www.rabota.ru",
        "superjob.ru",
        "www.superjob.ru",
    ]

    search_queries = [
        "Python",
        "Data Scientist",
        "Machine Learning",
    ]

    # Параметры приближены к C#-парсеру.
    pages_per_source = {
        "Habr Career": 5,
        "Rabota.ru": 2,
        "SuperJob": 3,
    }

    base_urls = {
        "Habr Career": "https://career.habr.com",
        "Rabota.ru": "https://www.rabota.ru",
        "SuperJob": "https://www.superjob.ru",
    }

    custom_settings = {
        "LOG_LEVEL": "INFO",

        "DOWNLOAD_TIMEOUT": 40,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 2,
        "RETRY_HTTP_CODES": [408, 429, 500, 502, 503, 504],

        # Общая задержка между запросами.
        "DOWNLOAD_DELAY": 2.5,
        "CONCURRENT_REQUESTS": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,

        "USER_AGENT": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/130.0.0.0 Safari/537.36"
        ),

        "DEFAULT_REQUEST_HEADERS": {
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        },

        "FEEDS": {
            "vacancies_all.csv": {
                "format": "csv",
                "encoding": "utf-8-sig",
                "overwrite": True,
                "fields": [
                    "Источник",
                    "Поисковый запрос",
                    "Дата сбора",
                    "Название",
                    "Компания",
                    "Город",
                    "Зарплата",
                    "Уровень",
                    "Формат работы",
                    "Навыки",
                    "Ссылка",
                ],
            },
        },

        "FEED_EXPORT_ENCODING": "utf-8",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Общая дедупликация ссылок между источниками.
        self.seen_links = set()

        # Статистика по страницам поиска.
        self.page_stats = []

        # Счётчики по источникам.
        self.source_counts = {
            source: 0 for source in self.base_urls
        }

        self.total_errors = 0
        self.start_time = time.monotonic()

    # =========================================================
    # ЗАПУСК ПОИСКА
    # =========================================================

    async def start(self):
        for query in self.search_queries:
            encoded_query = urlencode({"query": query})[6:]

            for source, base_url in self.base_urls.items():
                max_pages = self.pages_per_source[source]

                for page in range(1, max_pages + 1):
                    if source == "Habr Career":
                        url = (
                            f"{base_url}/vacancies"
                            f"?q={encoded_query}&type=all&page={page}"
                        )
                        callback = self.parse_habr

                    elif source == "Rabota.ru":
                        url = (
                            f"{base_url}/vacancy/"
                            f"?query={encoded_query}&page={page}"
                        )
                        callback = self.parse_rabota

                    else:
                        url = (
                            f"{base_url}/vacancy/search/"
                            f"?keywords={encoded_query}&page={page}"
                        )
                        callback = self.parse_superjob

                    yield scrapy.Request(
                        url,
                        callback=callback,
                        errback=self.request_error,
                        headers={
                            "Referer": base_url + "/",
                        },
                        meta={
                            "source": source,
                            "query": query,
                            "page": page,
                            "started_at": time.monotonic(),
                        },
                    )

    # =========================================================
    # ОБЩАЯ СТАТИСТИКА
    # =========================================================

    def add_page_stat(
        self,
        source,
        query,
        page,
        found,
        added,
        started_at,
        status="OK",
    ):
        elapsed_ms = int(
            (time.monotonic() - started_at) * 1000
        )

        self.page_stats.append({
            "Источник": source,
            "Запрос": query,
            "Страница": page,
            "Найдено карточек": found,
            "Добавлено уникальных": added,
            "Время, мс": elapsed_ms,
            "Статус": status,
        })

    def closed(self, reason):
        elapsed = time.monotonic() - self.start_time

        stats_path = "parsing_stats_all.csv"

        fields = [
            "Источник",
            "Запрос",
            "Страница",
            "Найдено карточек",
            "Добавлено уникальных",
            "Время, мс",
            "Статус",
        ]

        import csv

        with open(
            stats_path,
            "w",
            newline="",
            encoding="utf-8-sig",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=fields,
                delimiter=";",
            )
            writer.writeheader()
            writer.writerows(self.page_stats)

        self.logger.info("=" * 45)
        self.logger.info("ИТОГИ ПАРСИНГА")
        self.logger.info("Причина завершения: %s", reason)
        self.logger.info(
            "Поисковых запросов: %s",
            len(self.search_queries),
        )
        self.logger.info(
            "Страниц поиска обработано: %s",
            len(self.page_stats),
        )

        for source, count in self.source_counts.items():
            self.logger.info(
                "%s: сохранено вакансий — %s",
                source,
                count,
            )

        self.logger.info(
            "Всего уникальных вакансий: %s",
            len(self.seen_links),
        )
        self.logger.info("Ошибок: %s", self.total_errors)
        self.logger.info(
            "Время выполнения: %.2f сек.",
            elapsed,
        )
        self.logger.info(
            "Файл вакансий: vacancies_all.csv"
        )
        self.logger.info(
            "Файл статистики: %s",
            stats_path,
        )
        self.logger.info("=" * 45)

    # =========================================================
    # HABR CAREER
    # =========================================================

    def parse_habr(self, response):
        source = "Habr Career"
        query = response.meta["query"]
        page = response.meta["page"]
        started_at = response.meta["started_at"]

        cards = response.css(
            "div.vacancy-card, "
            "div[class*='vacancy-card']"
        )

        self.logger.info(
            "%s: HTTP %s, запрос=%s, страница=%s, карточек=%s",
            source,
            response.status,
            query,
            page,
            len(cards),
        )

        found = len(cards)
        added = 0

        if response.status != 200:
            self.add_page_stat(
                source, query, page, found, added,
                started_at, f"HTTP {response.status}",
            )
            return

        for card in cards:
            title = self.clean_text(
                card.css(
                    ".vacancy-card__title a::text, "
                    ".vacancy-card__title::text"
                ).get()
            )

            href = card.css(
                ".vacancy-card__title a::attr(href), "
                "a[href*='/vacancies/']::attr(href)"
            ).get()

            if not title or not href:
                continue

            link = self.normalize_url(
                urljoin(self.base_urls[source], href)
            )

            # C# принимает только ссылки формата /vacancies/123.
            path = urlsplit(link).path

            if not re.fullmatch(r"/vacancies/\d+/?", path):
                continue

            if not self.remember_link(link):
                continue

            company = self.clean_text(
                card.css(
                    "a[href*='/companies/']::text"
                ).get()
                or card.css(
                    "[class*='vacancy-card__company']::text"
                ).get()
            )

            card_text = self.clean_text(
                " ".join(card.css("::text").getall())
            )

            skills = [
                self.clean_text(value)
                for value in card.css(
                    ".vacancy-card__skills a::text, "
                    "[class*='skills'] a::text"
                ).getall()
            ]

            yield self.make_item(
                source=source,
                query=query,
                title=title,
                company=company,
                card_text=card_text,
                skills=skills,
                link=link,
            )

            added += 1
            self.source_counts[source] += 1

        self.add_page_stat(
            source, query, page, found, added, started_at
        )

    # =========================================================
    # RABOTA.RU: ПОИСКОВАЯ ВЫДАЧА
    # =========================================================

    def parse_rabota(self, response):
        source = "Rabota.ru"
        query = response.meta["query"]
        page = response.meta["page"]
        started_at = response.meta["started_at"]

        self.logger.info(
            "%s: HTTP %s, запрос=%s, страница=%s",
            source,
            response.status,
            query,
            page,
        )

        if response.status != 200:
            self.add_page_stat(
                source, query, page, 0, 0,
                started_at, f"HTTP {response.status}",
            )
            return

        links = {}

        # Поиск ссылок во всём документе, как в Python-версии.
        # Это позволяет не зависеть от точной вложенности карточек.
        for anchor in response.css("a[href*='/vacancy/']"):
            href = anchor.attrib.get("href", "")

            if not re.search(r"/vacancy/\d+/?(?:[?#]|$)", href):
                continue

            link = self.normalize_url(
                urljoin(self.base_urls[source], href)
            )

            path = urlsplit(link).path

            if not re.fullmatch(r"/vacancy/\d+/?", path):
                continue

            title = self.clean_text(
                " ".join(anchor.css("::text").getall())
                or anchor.attrib.get("aria-label", "")
            )

            # В C# title может извлекаться из карточки, а не только
            # из самой ссылки. Поэтому проверяем ближайшие контейнеры.
            if not title:
                title = self.clean_text(
                    " ".join(
                        anchor.xpath(
                            "ancestor::*[self::article or "
                            "contains(@class, 'vacancy-card') or "
                            "contains(@class, 'card')][1]"
                            "//*[contains(@class, 'title')]//text()"
                        ).getall()
                    )
                )

            if not title:
                continue

            company = self.clean_text(
                " ".join(
                    anchor.xpath(
                        "ancestor::*[self::article or "
                        "contains(@class, 'vacancy-card') or "
                        "contains(@class, 'card')][1]"
                        "//*[contains(@class, 'company')]//text()"
                    ).getall()
                )
            )

            links.setdefault(
                link,
                {
                    "title": title,
                    "company": company,
                },
            )

        self.logger.info(
            "Rabota.ru: найдено ссылок — %s",
            len(links),
        )

        if not links:
            self.logger.warning(
                "Rabota.ru: ссылки не найдены. Начало HTML: %s",
                response.text[:500],
            )

            self.add_page_stat(
                source, query, page, 0, 0,
                started_at, "Пустая страница",
            )
            return

        found = len(links)

        # Статистика по странице поиска.
        # Количество добавленных вакансий обновится в callback деталей.
        self.add_page_stat(
            source, query, page, found, 0, started_at
        )

        for link, data in links.items():
            if link in self.seen_links:
                continue

            yield scrapy.Request(
                link,
                callback=self.parse_rabota_detail,
                errback=self.rabota_detail_error,
                headers={
                    "Referer": response.url,
                },
                meta={
                    "source": source,
                    "query": query,
                    "page": page,
                    "fallback_title": data["title"],
                    "fallback_company": data["company"],
                    "search_url": response.url,
                },
            )

    # =========================================================
    # RABOTA.RU: ДЕТАЛЬНАЯ СТРАНИЦА
    # =========================================================

    def parse_rabota_detail(self, response):
        source = "Rabota.ru"
        query = response.meta["query"]

        link = self.normalize_url(response.url)

        if link in self.seen_links:
            return

        fallback_title = response.meta.get(
            "fallback_title", ""
        )
        fallback_company = response.meta.get(
            "fallback_company", ""
        )

        title = self.clean_text(
            response.css("h1::text").get()
            or response.css(
                "meta[property='og:title']::attr(content)"
            ).get()
            or response.css("title::text").get()
            or fallback_title
        )

        # Удаляем типичные добавления SEO-заголовков.
        if title.startswith("Вакансия "):
            title = title[len("Вакансия "):]

        title = re.sub(
            r"\s*[|–-]\s*Работа\.ru\s*$",
            "",
            title,
            flags=re.IGNORECASE,
        ).strip()

        company = self.clean_text(
            response.css(
                "[itemprop='hiringOrganization'] "
                "[itemprop='name']::text, "
                "[class*='vacancy-company-stats__name']::text, "
                "[class*='company-name']::text, "
                "a[class*='company']::text"
            ).get()
            or fallback_company
        )

        description = self.clean_text(
            response.css(
                "meta[name='description']::attr(content)"
            ).get()
            or ""
        )

        og_title = self.clean_text(
            response.css(
                "meta[property='og:title']::attr(content)"
            ).get()
            or ""
        )

        full_text = self.clean_text(
            " ".join(response.css("body ::text").getall())
        )

        salary = self.extract_rabota_salary(
            description + " " + og_title
        )

        if salary == "Не указана":
            salary_text = self.clean_text(
                " ".join(
                    response.css(
                        "[class*='salary']::text, "
                        "[itemprop='baseSalary']::text, "
                        "[itemprop='baseSalary'] "
                        "[content]::attr(content)"
                    ).getall()
                )
            )
            salary = self.extract_rabota_salary(salary_text)

        city = self.find_city(
            og_title + " " + description
        )

        skills = [
            self.clean_text(value)
            for value in response.css(
                ".vacancy-card__skills-item::text, "
                "[class*='skills-list'] "
                "[class*='skills-item']::text"
            ).getall()
        ]

        skills = [
            skill for skill in skills
            if skill and not self.is_service_text(skill)
        ]

        # При успешном ответе сохраняем запись даже тогда,
        # когда отдельные поля не удалось определить.
        item = self.make_item(
            source=source,
            query=query,
            title=title or fallback_title,
            company=company,
            card_text=full_text,
            skills=skills,
            link=link,
            city_override=city,
            salary_override=salary,
        )

        self.seen_links.add(link)
        self.source_counts[source] += 1

        yield item

    def rabota_detail_error(self, failure):
        request = failure.request
        meta = request.meta

        source = "Rabota.ru"
        link = self.normalize_url(request.url)

        self.total_errors += 1

        self.logger.error(
            "Ошибка загрузки деталей Rabota.ru: %s | %s",
            failure.value,
            request.url,
        )

        # Аналог C#: если детали не загрузились, сохраняем
        # резервную запись из поисковой выдачи.
        if link in self.seen_links:
            return

        title = self.clean_text(
            meta.get("fallback_title", "")
        )
        company = self.clean_text(
            meta.get("fallback_company", "")
        )

        if not title:
            return

        self.seen_links.add(link)
        self.source_counts[source] += 1

        yield {
            "Источник": source,
            "Поисковый запрос": meta.get("query", ""),
            "Дата сбора": datetime.now(timezone.utc).isoformat(),
            "Название": title,
            "Компания": company or "Не указана",
            "Город": "Не указан",
            "Зарплата": "Не указана",
            "Уровень": self.find_level(title),
            "Формат работы": "Не указан",
            "Навыки": "Не указаны",
            "Ссылка": link,
        }

    # =========================================================
    # SUPERJOB
    # =========================================================

    def parse_superjob(self, response):
        source = "SuperJob"
        query = response.meta["query"]
        page = response.meta["page"]
        started_at = response.meta["started_at"]

        cards = response.css(
            "div[class*='_-toc9'], "
            "article, "
            "div[class*='f-test-vacancy-item']"
        )

        self.logger.info(
            "%s: HTTP %s, запрос=%s, страница=%s, карточек=%s",
            source,
            response.status,
            query,
            page,
            len(cards),
        )

        found = len(cards)
        added = 0

        if response.status != 200:
            self.add_page_stat(
                source, query, page, found, added,
                started_at, f"HTTP {response.status}",
            )
            return

        for card in cards:
            href = card.css(
                "a[href*='/vakansii/']::attr(href)"
            ).get()

            title = self.clean_text(
                card.css(
                    "a[href*='/vakansii/']::text"
                ).get()
            )

            if not title or not href:
                continue

            link = self.normalize_url(
                urljoin(self.base_urls[source], href)
            )

            if not self.remember_link(link):
                continue

            company = self.clean_text(
                card.css(
                    "span[class*='f-test-text-company-item']::text, "
                    "a[href*='/clients/']::text"
                ).get()
            )

            card_text = self.clean_text(
                " ".join(card.css("::text").getall())
            )

            skills = [
                self.clean_text(value)
                for value in card.css(
                    "span[class*='tag']::text, "
                    "a[class*='tag']::text"
                ).getall()
            ]

            yield self.make_item(
                source=source,
                query=query,
                title=title,
                company=company,
                card_text=card_text,
                skills=skills,
                link=link,
            )

            added += 1
            self.source_counts[source] += 1

        self.add_page_stat(
            source, query, page, found, added, started_at
        )

    # =========================================================
    # ДЕДУПЛИКАЦИЯ И ОБРАБОТКА ОШИБОК
    # =========================================================

    @staticmethod
    def normalize_url(link):
        parts = urlsplit(link)

        path = parts.path.rstrip("/") or "/"

        return urlunsplit((
            parts.scheme.lower(),
            parts.netloc.lower(),
            path,
            "",
            "",
        ))

    def remember_link(self, link):
        normalized = self.normalize_url(link)

        if normalized in self.seen_links:
            return False

        self.seen_links.add(normalized)
        return True

    def request_error(self, failure):
        request = failure.request
        self.total_errors += 1

        source = request.meta.get("source", "Неизвестный источник")
        query = request.meta.get("query", "")
        page = request.meta.get("page", 0)
        started_at = request.meta.get(
            "started_at", time.monotonic()
        )

        self.logger.error(
            "Ошибка запроса: %s | URL: %s",
            failure.value,
            request.url,
        )

        self.add_page_stat(
            source,
            query,
            page,
            0,
            0,
            started_at,
            "Ошибка запроса",
        )

    # =========================================================
    # ФОРМИРОВАНИЕ ЗАПИСИ
    # =========================================================

    def make_item(
        self,
        source,
        query,
        title,
        company,
        card_text,
        skills,
        link,
        city_override=None,
        salary_override=None,
    ):
        title = self.clean_text(title)
        company = self.clean_text(company)
        card_text = self.clean_text(card_text)

        city = (
            city_override
            if city_override and city_override != "Не указан"
            else self.find_city(card_text)
        )

        salary = (
            salary_override
            if salary_override and salary_override != "Не указана"
            else self.find_salary(card_text)
        )

        level = self.find_level(title)

        clean_skills = []
        for skill in skills:
            skill = self.clean_text(skill)

            if skill and not self.is_service_text(skill):
                if skill.lower() not in {
                    existing.lower() for existing in clean_skills
                }:
                    clean_skills.append(skill)

        return {
            "Источник": source,
            "Поисковый запрос": query,
            "Дата сбора": datetime.now(timezone.utc).isoformat(),
            "Название": title or "Не указано",
            "Компания": company or "Не указана",
            "Город": city,
            "Зарплата": salary,
            "Уровень": level,
            "Формат работы": self.find_work_format(card_text),
            "Навыки": "; ".join(clean_skills) or "Не указаны",
            "Ссылка": link,
        }

    # =========================================================
    # ОБЩИЕ ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================

    @staticmethod
    def clean_text(value):
        if not value:
            return ""

        value = value.replace("\xa0", " ")
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def is_service_text(text):
        service_phrases = [
            "задайте вопрос работодателю",
            "он получит его вместе с откликом",
            "быстрый отклик",
            "откликнуться",
            "показать контакты",
        ]

        text_lower = text.lower()

        return any(
            phrase in text_lower
            for phrase in service_phrases
        )

    @staticmethod
    def find_city(text):
        if not text:
            return "Не указан"

        city_patterns = [
            (r"\bСанкт-Петербург(?:е|а)?\b", "Санкт-Петербург"),
            (r"\bНижн(?:ем|его) Новгороде?\b", "Нижний Новгород"),
            (r"\bЕкатеринбург(?:е|а)?\b", "Екатеринбург"),
            (r"\bНовосибирск(?:е|а)?\b", "Новосибирск"),
            (r"\bКраснодар(?:е|а)?\b", "Краснодар"),
            (r"\bМоскв(?:а|е|ы|у)\b", "Москва"),
            (r"\bКазан(?:ь|и)\b", "Казань"),
            (r"\bМинск(?:е|а)?\b", "Минск"),
            (r"\bАлматы\b", "Алматы"),
        ]

        for pattern, city in city_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return city

        return "Не указан"

    @staticmethod
    def find_salary(text):
        if not text:
            return "Не указана"

        if re.search(
            r"по\s+договор[её]нности|договорная\s+зарплата",
            text,
            re.IGNORECASE,
        ):
            return "По договорённости"

        match = re.search(
            r"(?<!\w)(?:(?:от|до)\s*)?"
            r"\d[\d\s\u00a0]*(?:[.,]\d+)?"
            r"(?:\s*[–—-]\s*(?:от|до)?\s*"
            r"\d[\d\s\u00a0]*(?:[.,]\d+)?)?"
            r"\s*(?:₽|руб(?:\.|лей|ля)?|USD|\$|EUR|€)",
            text,
            re.IGNORECASE,
        )

        if match:
            return re.sub(
                r"\s+", " ", match.group(0)
            ).strip()

        return "Не указана"

    @staticmethod
    def extract_rabota_salary(text):
        if not text:
            return "Не указана"

        text = re.sub(r"\s+", " ", text).strip()

        if re.search(
            r"по\s+договор[её]нности|договорная\s+зарплата",
            text,
            re.IGNORECASE,
        ):
            return "По договорённости"

        match = re.search(
            r"зарплатой\s+"
            r"(?:(?:от|до)\s+)?"
            r"(?:₽\s*)?"
            r"([\d][\d\s\u00a0]*(?:[.,]\d+)?)"
            r"\s*(руб(?:\.|лей|ля)?|₽)",
            text,
            re.IGNORECASE,
        )

        if not match:
            match = re.search(
                r"(?<!\w)([\d][\d\s\u00a0]*(?:[.,]\d+)?)"
                r"\s*(руб(?:\.|лей|ля)?|₽)",
                text,
                re.IGNORECASE,
            )

        if match:
            amount = re.sub(
                r"\s+", " ", match.group(1)
            ).strip()
            return f"{amount} ₽"

        return "Не указана"

    @staticmethod
    def find_level(text):
        if not text:
            return "Не указан"

        # Порядок аналогичен C#.
        levels = [
            (r"\bTech\s*Lead\b|\bLead\b|\bруководитель\b", "Lead"),
            (r"\bSenior\b|\bсеньор\b|\bстарший\b", "Senior"),
            (r"\bMiddle\b|\bмидл\b", "Middle"),
            (r"\bJunior\b|\bджуниор\b|\bмладший\b", "Junior"),
            (r"\bIntern\b|стаж[её]р|стажировка", "Intern"),
        ]

        for pattern, level in levels:
            if re.search(pattern, text, re.IGNORECASE):
                return level

        return "Не указан"

    @staticmethod
    def find_work_format(text):
        if not text:
            return "Не указан"

        if re.search(r"удал[её]нн|remote", text, re.IGNORECASE):
            return "Удалённо"

        if re.search(r"гибрид|hybrid", text, re.IGNORECASE):
            return "Гибрид"

        if re.search(r"офис|on[\s-]?site", text, re.IGNORECASE):
            return "Офис"

        return "Не указан"


if __name__ == "__main__":
    process = CrawlerProcess()
    process.crawl(JobSpider)
    process.start()