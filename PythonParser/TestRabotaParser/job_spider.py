# import csv
# import re
# import time
# from datetime import datetime
# from pathlib import Path
# from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit
#
# import scrapy
# from scrapy.crawler import CrawlerProcess
#
# OUT = Path.cwd()
# VACANCIES_FILE = OUT / "vacancies_all.csv"
# STATS_FILE = OUT / "parsing_stats_all.csv"
# QUERIES = ["Python", "Data Scientist", "Machine Learning"]
# PAGES = {"Habr Career": 5, "Rabota.ru": 2, "SuperJob": 3}
# DELAY = 2.5
# UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
#       "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
#
#
# def clean(value):
#     return re.sub(r"\s+", " ", str(value or "")).strip()
#
#
# def normalize(href, base):
#     if not href or href.strip().lower().startswith(("javascript:", "#")):
#         return ""
#     parts = urlsplit(urljoin(base, href.strip()))
#     return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))
#
#
# def first(*values):
#     return next((clean(v) for v in values if clean(v)), "")
#
#
# class JobSpider(scrapy.Spider):
#     name = "job_spider"
#     custom_settings = {
#         "USER_AGENT": UA,
#         "DOWNLOAD_TIMEOUT": 40,
#         "RETRY_ENABLED": True,
#         "RETRY_TIMES": 2,
#         "RETRY_HTTP_CODES": [408, 429, 500, 502, 503, 504],
#         "CONCURRENT_REQUESTS": 1,
#         "DOWNLOAD_DELAY": DELAY,
#         "DOWNLOAD_DELAY_JITTER": 0,
#         "AUTOTHROTTLE_ENABLED": False,
#         "REDIRECT_ENABLED": True,
#         "LOG_LEVEL": "INFO",
#         "FEED_EXPORT_ENCODING": "utf-8-sig",
#     }
#
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.seen = set()
#         self.items = []
#         self.stats = {}
#         self.errors = 0
#         self.started = time.perf_counter()
#
#     async def start(self):
#         for query in QUERIES:
#             q = urlencode({"query": query})
#             for page in range(1, PAGES["Habr Career"] + 1):
#                 yield self.request(f"https://career.habr.com/vacancies?{q}&page={page}", self.parse_habr, "Habr Career", query, page)
#             for page in range(1, PAGES["Rabota.ru"] + 1):
#                 yield self.request(f"https://www.rabota.ru/vacancy/?{q}&page={page}", self.parse_rabota, "Rabota.ru", query, page)
#             for page in range(1, PAGES["SuperJob"] + 1):
#                 url = "https://www.superjob.ru/vacancy/search/?" + urlencode({"keywords": query, "page": page})
#                 yield self.request(url, self.parse_superjob, "SuperJob", query, page)
#
#     def request(self, url, callback, source, query, page, **extra):
#         key = (source, query, page)
#         self.stats.setdefault(key, {"source": source, "query": query, "page": page,
#                                     "found": 0, "added": 0, "elapsed_ms": 0, "status": "PENDING"})
#         return scrapy.Request(url, callback=callback, errback=self.request_error, dont_filter=True,
#             headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#                      "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"},
#             meta={"source": source, "query": query, "page": page, "stats_key": key,
#                   "request_started": time.perf_counter(), **extra})
#
#     def finish_request(self, response, status=None):
#         key = response.meta.get("stats_key") or response.meta.get("parent_stats_key")
#         if key in self.stats:
#             self.stats[key]["elapsed_ms"] += int((time.perf_counter() - response.meta["request_started"]) * 1000)
#             self.stats[key]["status"] = status or ("OK" if response.status < 400 else f"HTTP_{response.status}")
#
#     def request_error(self, failure):
#         self.errors += 1
#         req = failure.request
#         key = req.meta.get("stats_key") or req.meta.get("parent_stats_key")
#         if key in self.stats:
#             self.stats[key]["elapsed_ms"] += int((time.perf_counter() - req.meta["request_started"]) * 1000)
#             self.stats[key]["status"] = "ERROR"
#         self.logger.warning("Request failed: %s (%s)", req.url, failure.value)
#
#     def make_item(self, response, title, link):
#         return {"source": response.meta["source"], "query": response.meta["query"],
#                 "date_collected": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#                 "title": clean(title), "company": "", "city": "", "salary": "",
#                 "level": "", "work_format": "", "skills": "", "link": normalize(link, response.url)}
#
#     def add_item(self, item, key):
#         link = item.get("link", "")
#         if not link or not item.get("title") or link in self.seen:
#             return False
#         self.seen.add(link)
#         self.items.append(item)
#         if key in self.stats:
#             self.stats[key]["added"] += 1
#         return True
#
#     def parse_habr(self, response):
#         self.finish_request(response)
#         key = response.meta["stats_key"]
#         found = 0
#         cards = response.css("div.vacancy-card, article.vacancy-card, div[class*='vacancy-card']")
#         for card in cards:
#             href = card.css("a[href*='/vacancies/']::attr(href)").get()
#             link = normalize(href, "https://career.habr.com")
#             if not link or not re.search(r"/vacancies/\d+$", urlsplit(link).path):
#                 continue
#             title = first(card.css("a[href*='/vacancies/']::text").get(), card.css("[class*='title']::text").get())
#             if not title:
#                 continue
#             found += 1
#             item = self.make_item(response, title, link)
#             item["company"] = clean(" ".join(card.css("[class*='company'] ::text").getall()))
#             item["city"] = clean(" ".join(card.css("[class*='location'] ::text").getall()))
#             item["salary"] = clean(" ".join(card.css("[class*='salary'] ::text").getall()))
#             item["level"] = clean(" ".join(card.css("[class*='experience'] ::text").getall()))
#             item["work_format"] = clean(" ".join(card.css("[class*='remote'] ::text, [class*='employment'] ::text").getall()))
#             item["skills"] = clean(" ".join(card.css("[class*='skills'] ::text").getall()))
#             self.add_item(item, key)
#         self.stats[key]["found"] = found
#
#     def parse_rabota(self, response):
#         self.finish_request(response)
#         key = response.meta["stats_key"]
#         links = {}
#         for a in response.css("a[href*='/vacancy/']"):
#             link = normalize(a.attrib.get("href", ""), "https://www.rabota.ru")
#             title = clean(" ".join(a.css("::text").getall()))
#             if link and re.search(r"/vacancy/[^/]+$", urlsplit(link).path) and len(title) >= 3:
#                 links.setdefault(link, title)
#         self.stats[key]["found"] = len(links)
#         for link, title in links.items():
#             yield self.request(link, self.parse_rabota_detail, "Rabota.ru", response.meta["query"], response.meta["page"],
#                                parent_stats_key=key, fallback_title=title, detail_link=link)
#
#     def parse_rabota_detail(self, response):
#         key = response.meta.get("parent_stats_key")
#         self.finish_request(response)
#         title = first(response.css("h1::text").get(), response.meta.get("fallback_title"))
#         description = clean(" ".join(response.css("[class*='description'] ::text").getall()))
#         item = self.make_item(response, title, response.meta.get("detail_link", response.url))
#         item["company"] = first(" ".join(response.css("[class*='company'] ::text").getall()), response.css("meta[property='og:site_name']::attr(content)").get())
#         item["city"] = clean(" ".join(response.css("[class*='location'] ::text, [class*='address'] ::text").getall()))
#         item["salary"] = clean(" ".join(response.css("[class*='salary'] ::text").getall()))
#         item["level"] = self.extract_level(description)
#         item["work_format"] = self.extract_format(description)
#         item["skills"] = self.extract_skills(description)
#         self.add_item(item, key)
#
#     def parse_superjob(self, response):
#         self.finish_request(response)
#         key = response.meta["stats_key"]
#         links = {}
#         for a in response.css("a[href*='/vacancy/']"):
#             link = normalize(a.attrib.get("href", ""), "https://www.superjob.ru")
#             title = clean(" ".join(a.css("::text").getall()))
#             if link and re.search(r"/vacancy/[^/]+$", urlsplit(link).path) and len(title) >= 3:
#                 links.setdefault(link, a)
#         self.stats[key]["found"] = len(links)
#         for link, a in links.items():
#             card = a
#             for _ in range(3):
#                 parent = card.xpath("..")
#                 if not parent:
#                     break
#                 card = parent[0]
#             item = self.make_item(response, clean(" ".join(a.css("::text").getall())), link)
#             item["company"] = clean(" ".join(card.css("[class*='company'] ::text").getall()))
#             item["city"] = clean(" ".join(card.css("[class*='town'] ::text, [class*='location'] ::text").getall()))
#             item["salary"] = clean(" ".join(card.css("[class*='salary'] ::text").getall()))
#             item["level"] = clean(" ".join(card.css("[class*='experience'] ::text").getall()))
#             item["work_format"] = clean(" ".join(card.css("[class*='remote'] ::text, [class*='employment'] ::text").getall()))
#             item["skills"] = clean(" ".join(card.css("[class*='skills'] ::text").getall()))
#             self.add_item(item, key)
#
#     @staticmethod
#     def extract_level(text):
#         m = re.search(r"\b(junior|middle|senior|lead|стаж[её]р|без опыта|1[-– ]?3 года|3[-– ]?6 лет)\b", text or "", re.I)
#         return m.group(0) if m else ""
#
#     @staticmethod
#     def extract_format(text):
#         m = re.search(r"\b(удал[её]нно|гибрид|офис|remote|hybrid|on[- ]site)\b", text or "", re.I)
#         return m.group(0) if m else ""
#
#     @staticmethod
#     def extract_skills(text):
#         skills = ["Python", "C#", "SQL", "Java", "JavaScript", "Machine Learning", "TensorFlow", "PyTorch", "Pandas", "NumPy", "Docker", "Kubernetes", "Git"]
#         low = (text or "").lower()
#         return "; ".join(s for s in skills if s.lower() in low)
#
#     def closed(self, reason):
#         fields = ["source", "query", "date_collected", "title", "company", "city", "salary", "level", "work_format", "skills", "link"]
#         with VACANCIES_FILE.open("w", newline="", encoding="utf-8-sig") as f:
#             writer = csv.DictWriter(f, fieldnames=fields, delimiter=";")
#             writer.writeheader()
#             writer.writerows(self.items)
#         stat_fields = ["source", "query", "page", "found_links", "unique_added", "elapsed_ms", "status"]
#         with STATS_FILE.open("w", newline="", encoding="utf-8-sig") as f:
#             writer = csv.DictWriter(f, fieldnames=stat_fields, delimiter=";")
#             writer.writeheader()
#             for s in sorted(self.stats.values(), key=lambda x: (x["source"], x["query"], x["page"])):
#                 writer.writerow({"source": s["source"], "query": s["query"], "page": s["page"],
#                                  "found_links": s["found"], "unique_added": s["added"],
#                                  "elapsed_ms": s["elapsed_ms"], "status": s["status"]})
#         self.logger.info("Saved %d unique vacancies to %s", len(self.items), VACANCIES_FILE)
#         self.logger.info("Stats saved to %s; total elapsed %.1f sec", STATS_FILE, time.perf_counter() - self.started)
#
#
# if __name__ == "__main__":
#     process = CrawlerProcess()
#     process.crawl(JobSpider)
#     process.start()

import csv
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit

import scrapy
from scrapy.crawler import CrawlerProcess

OUT = Path.cwd()
VACANCIES_FILE = OUT / "vacancies_all.csv"
STATS_FILE = OUT / "parsing_stats_all.csv"
SUMMARY_FILE = OUT / "run_summary.csv"
QUERIES = ["Python", "Data Scientist", "Machine Learning"]
PAGES = {"Habr Career": 5, "Rabota.ru": 2, "SuperJob": 3}
DELAY = 2.5
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize(href, base):
    if not href or href.strip().lower().startswith(("javascript:", "#")):
        return ""
    parts = urlsplit(urljoin(base, href.strip()))
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def first(*values):
    return next((clean(v) for v in values if clean(v)), "")


class JobSpider(scrapy.Spider):
    name = "job_spider"
    custom_settings = {
        "USER_AGENT": UA,
        "DOWNLOAD_TIMEOUT": 40,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 2,
        "RETRY_HTTP_CODES": [408, 429, 500, 502, 503, 504],
        "CONCURRENT_REQUESTS": 1,
        "DOWNLOAD_DELAY": DELAY,
        "DOWNLOAD_DELAY_JITTER": 0,
        "AUTOTHROTTLE_ENABLED": False,
        "REDIRECT_ENABLED": True,
        "LOG_LEVEL": "INFO",
        "FEED_EXPORT_ENCODING": "utf-8-sig",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.seen = set()
        self.items = []
        self.stats = {}
        self.errors = 0
        self.detail_requests = 0
        self.started = time.perf_counter()

    async def start(self):
        self.logger.info("Начинаем сбор вакансий")

        for query in QUERIES:
            q = urlencode({"query": query})

            for page in range(1, PAGES["Habr Career"] + 1):
                yield self.request(
                    f"https://career.habr.com/vacancies?{q}&page={page}",
                    self.parse_habr,
                    "Habr Career",
                    query,
                    page
                )

            for page in range(1, PAGES["Rabota.ru"] + 1):
                yield self.request(
                    f"https://www.rabota.ru/vacancy/?{q}&page={page}",
                    self.parse_rabota,
                    "Rabota.ru",
                    query,
                    page
                )

            for page in range(1, PAGES["SuperJob"] + 1):
                url = (
                        "https://www.superjob.ru/vacancy/search/?"
                        + urlencode({"keywords": query, "page": page})
                )

                yield self.request(
                    url,
                    self.parse_superjob,
                    "SuperJob",
                    query,
                    page
                )

    def request(self, url, callback, source, query, page, **extra):
        key = (source, query, page)
        meta = {"source": source, "query": query, "page": page}
        # Search requests own a stats row. Detail requests refer to their parent
        # search page only for associating the extracted vacancy, not for timing.
        if "parent_stats_key" not in extra:
            self.stats.setdefault(key, {"source": source, "query": query, "page": page,
                                        "found": 0, "added": 0, "elapsed_ms": 0, "status": "PENDING"})
            meta["stats_key"] = key
        meta.update(extra)
        return scrapy.Request(url, callback=callback, errback=self.request_error, dont_filter=True,
            headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                     "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"}, meta=meta)

    def finish_request(self, response, status=None):
        # Scrapy's download_latency measures the HTTP request/response interval,
        # excluding the time the request spent waiting in the scheduler queue.
        key = response.meta.get("stats_key")
        if key not in self.stats:
            # Detail pages have no stats_key: they contribute to total run time,
            # but are not incorrectly added to a search-page timing.
            return
        elapsed_ms = int(float(response.meta.get("download_latency", 0.0)) * 1000)
        self.stats[key]["elapsed_ms"] = elapsed_ms
        self.stats[key]["status"] = status or ("OK" if response.status < 400 else f"HTTP_{response.status}")

    def request_error(self, failure):
        self.errors += 1
        req = failure.request
        key = req.meta.get("stats_key")
        if key in self.stats:
            self.stats[key]["status"] = "ERROR"
        self.logger.warning("Request failed: %s (%s)", req.url, failure.value)

    def make_item(self, response, title, link):
        return {"source": response.meta["source"], "query": response.meta["query"],
                "date_collected": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "title": clean(title), "company": "", "city": "", "salary": "",
                "level": "", "work_format": "", "skills": "", "link": normalize(link, response.url)}

    def add_item(self, item, key):
        link = item.get("link", "")
        if not link or not item.get("title") or link in self.seen:
            return False
        self.seen.add(link)
        self.items.append(item)
        if key in self.stats:
            self.stats[key]["added"] += 1
        return True

    def parse_habr(self, response):
        self.finish_request(response)
        key = response.meta["stats_key"]
        found = 0
        cards = response.css("div.vacancy-card, article.vacancy-card, div[class*='vacancy-card']")
        for card in cards:
            href = card.css("a[href*='/vacancies/']::attr(href)").get()
            link = normalize(href, "https://career.habr.com")
            if not link or not re.search(r"/vacancies/\d+$", urlsplit(link).path):
                continue
            title = first(card.css("a[href*='/vacancies/']::text").get(), card.css("[class*='title']::text").get())
            if not title:
                continue
            found += 1
            item = self.make_item(response, title, link)
            item["company"] = clean(" ".join(card.css("[class*='company'] ::text").getall()))
            item["city"] = clean(" ".join(card.css("[class*='location'] ::text").getall()))
            item["salary"] = clean(" ".join(card.css("[class*='salary'] ::text").getall()))
            item["level"] = clean(" ".join(card.css("[class*='experience'] ::text").getall()))
            item["work_format"] = clean(" ".join(card.css("[class*='remote'] ::text, [class*='employment'] ::text").getall()))
            item["skills"] = clean(" ".join(card.css("[class*='skills'] ::text").getall()))
            self.add_item(item, key)
        self.stats[key]["found"] = found

    def parse_rabota(self, response):
        self.finish_request(response)
        key = response.meta["stats_key"]
        links = {}
        for a in response.css("a[href*='/vacancy/']"):
            link = normalize(a.attrib.get("href", ""), "https://www.rabota.ru")
            title = clean(" ".join(a.css("::text").getall()))
            if link and re.search(r"/vacancy/[^/]+$", urlsplit(link).path) and len(title) >= 3:
                links.setdefault(link, title)
        self.stats[key]["found"] = len(links)
        for link, title in links.items():
            self.detail_requests += 1
            yield self.request(link, self.parse_rabota_detail, "Rabota.ru", response.meta["query"], response.meta["page"],
                               parent_stats_key=key, fallback_title=title, detail_link=link)

    def parse_rabota_detail(self, response):
        key = response.meta.get("parent_stats_key")
        self.finish_request(response)
        title = first(response.css("h1::text").get(), response.meta.get("fallback_title"))
        description = clean(" ".join(response.css("[class*='description'] ::text").getall()))
        item = self.make_item(response, title, response.meta.get("detail_link", response.url))
        item["company"] = first(" ".join(response.css("[class*='company'] ::text").getall()), response.css("meta[property='og:site_name']::attr(content)").get())
        item["city"] = clean(" ".join(response.css("[class*='location'] ::text, [class*='address'] ::text").getall()))
        item["salary"] = clean(" ".join(response.css("[class*='salary'] ::text").getall()))
        item["level"] = self.extract_level(description)
        item["work_format"] = self.extract_format(description)
        item["skills"] = self.extract_skills(description)
        self.add_item(item, key)

    def parse_superjob(self, response):
        self.finish_request(response)
        key = response.meta["stats_key"]
        links = {}
        for a in response.css("a[href*='/vacancy/']"):
            link = normalize(a.attrib.get("href", ""), "https://www.superjob.ru")
            title = clean(" ".join(a.css("::text").getall()))
            if link and re.search(r"/vacancy/[^/]+$", urlsplit(link).path) and len(title) >= 3:
                links.setdefault(link, a)
        self.stats[key]["found"] = len(links)
        for link, a in links.items():
            card = a
            for _ in range(3):
                parent = card.xpath("..")
                if not parent:
                    break
                card = parent[0]
            item = self.make_item(response, clean(" ".join(a.css("::text").getall())), link)
            item["company"] = clean(" ".join(card.css("[class*='company'] ::text").getall()))
            item["city"] = clean(" ".join(card.css("[class*='town'] ::text, [class*='location'] ::text").getall()))
            item["salary"] = clean(" ".join(card.css("[class*='salary'] ::text").getall()))
            item["level"] = clean(" ".join(card.css("[class*='experience'] ::text").getall()))
            item["work_format"] = clean(" ".join(card.css("[class*='remote'] ::text, [class*='employment'] ::text").getall()))
            item["skills"] = clean(" ".join(card.css("[class*='skills'] ::text").getall()))
            self.add_item(item, key)

    @staticmethod
    def extract_level(text):
        m = re.search(r"\b(junior|middle|senior|lead|стаж[её]р|без опыта|1[-– ]?3 года|3[-– ]?6 лет)\b", text or "", re.I)
        return m.group(0) if m else ""

    @staticmethod
    def extract_format(text):
        m = re.search(r"\b(удал[её]нно|гибрид|офис|remote|hybrid|on[- ]site)\b", text or "", re.I)
        return m.group(0) if m else ""

    @staticmethod
    def extract_skills(text):
        skills = ["Python", "C#", "SQL", "Java", "JavaScript", "Machine Learning", "TensorFlow", "PyTorch", "Pandas", "NumPy", "Docker", "Kubernetes", "Git"]
        low = (text or "").lower()
        return "; ".join(s for s in skills if s.lower() in low)

    def closed(self, reason):
        fields = ["source", "query", "date_collected", "title", "company", "city", "salary", "level", "work_format", "skills", "link"]
        with VACANCIES_FILE.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fields, delimiter=";")
            writer.writeheader()
            writer.writerows(self.items)
        stat_fields = ["source", "query", "page", "found_links", "unique_added", "search_response_ms", "status"]
        with STATS_FILE.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=stat_fields, delimiter=";")
            writer.writeheader()
            for s in sorted(self.stats.values(), key=lambda x: (x["source"], x["query"], x["page"])):
                writer.writerow({"source": s["source"], "query": s["query"], "page": s["page"],
                                 "found_links": s["found"], "unique_added": s["added"],
                                 "search_response_ms": s["elapsed_ms"],
                                 "status": s["status"]})
        total_elapsed = time.perf_counter() - self.started
        with SUMMARY_FILE.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["parser", "total_elapsed_seconds", "unique_vacancies", "search_pages", "detail_requests", "errors"], delimiter=";")
            writer.writeheader()
            writer.writerow({"parser": "Python Scrapy", "total_elapsed_seconds": round(total_elapsed, 3),
                             "unique_vacancies": len(self.items), "search_pages": len(self.stats),
                             "detail_requests": self.detail_requests, "errors": self.errors})
        self.logger.info("Saved %d unique vacancies to %s", len(self.items), VACANCIES_FILE)
        self.logger.info("Stats saved to %s", STATS_FILE)
        self.logger.info("Total elapsed: %.1f sec; summary: %s", total_elapsed, SUMMARY_FILE)


if __name__ == "__main__":
    process = CrawlerProcess()
    process.crawl(JobSpider)
    process.start()
