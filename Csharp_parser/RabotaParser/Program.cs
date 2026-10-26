using HtmlAgilityPack;
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;

class Program
{
    private static readonly HttpClient Client = new HttpClient
    {
        Timeout = TimeSpan.FromSeconds(40)
    };

    private const string HabrUrl = "https://career.habr.com";
    private const string RabotaUrl = "https://www.rabota.ru";
    private const string SuperJobUrl = "https://www.superjob.ru";

    private const int HabrPages = 5;
    private const int RabotaPages = 2;
    private const int SuperJobPages = 3;

    private const int DelayMs = 2500;

    private static readonly string[] SearchQueries =
    {
        "Python",
        "Data Scientist",
        "Machine Learning"
    };

    private static readonly HashSet<string> SeenLinks =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase);

    private static readonly List<Vacancy> AllVacancies =
        new List<Vacancy>();

    private static readonly List<PageStat> AllStats =
        new List<PageStat>();

    private static int Errors;

    static async Task Main()
    {
        ConfigureHttpClient();

        var timer = Stopwatch.StartNew();

        Console.WriteLine("========================================");
        Console.WriteLine(" СБОР ВАКАНСИЙ С ТРЁХ ИСТОЧНИКОВ");
        Console.WriteLine("========================================");

        // 1. Habr Career
        await RunSource(
            "Habr Career",
            SearchHabrPage,
            HabrPages);

        // 2. Rabota.ru
        await RunSource(
            "Rabota.ru",
            SearchRabotaPage,
            RabotaPages);

        // 3. SuperJob
        await RunSource(
            "SuperJob",
            SearchSuperJobPage,
            SuperJobPages);

        timer.Stop();

        string outputDirectory = Directory.GetCurrentDirectory();

        string vacanciesPath = Path.Combine(
            outputDirectory,
            "vacancies_all.csv");

        string statsPath = Path.Combine(
            outputDirectory,
            "parsing_stats_all.csv");

        SaveVacanciesCsv(vacanciesPath, AllVacancies);
        SaveStatsCsv(statsPath, AllStats);

        Console.WriteLine();
        Console.WriteLine("============== ИТОГИ ==============");
        Console.WriteLine($"Обработано источников: 3");
        Console.WriteLine($"Поисковых запросов: {SearchQueries.Length}");
        Console.WriteLine($"Загружено страниц поиска: {AllStats.Count}");
        Console.WriteLine($"Уникальных вакансий: {AllVacancies.Count}");
        Console.WriteLine($"Ошибок: {Errors}");
        Console.WriteLine(
            $"Время выполнения: {timer.Elapsed.TotalSeconds:F2} сек.");
        Console.WriteLine();
        Console.WriteLine("Вакансии: " + vacanciesPath);
        Console.WriteLine("Статистика: " + statsPath);
        Console.WriteLine("===================================");
    }

    // =========================================================
    // ОБЩИЕ НАСТРОЙКИ И ЗАПУСК ИСТОЧНИКА
    // =========================================================

    static void ConfigureHttpClient()
    {
        Client.DefaultRequestHeaders.Clear();

        Client.DefaultRequestHeaders.UserAgent.ParseAdd(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
            "AppleWebKit/537.36 (KHTML, like Gecko) " +
            "Chrome/130.0.0.0 Safari/537.36");

        Client.DefaultRequestHeaders.Accept.ParseAdd(
            "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8");

        Client.DefaultRequestHeaders.AcceptLanguage.ParseAdd(
            "ru-RU,ru;q=0.9,en;q=0.8");
    }

    static async Task RunSource(
        string source,
        Func<string, int, Task<List<Vacancy>>> searchPage,
        int maxPages)
    {
        Console.WriteLine();
        Console.WriteLine("----------------------------------------");
        Console.WriteLine("Источник: " + source);
        Console.WriteLine("----------------------------------------");

        foreach (string query in SearchQueries)
        {
            Console.WriteLine();
            Console.WriteLine("Поисковый запрос: " + query);

            for (int page = 1; page <= maxPages; page++)
            {
                var pageTimer = Stopwatch.StartNew();

                int found = 0;
                int added = 0;
                string status = "OK";

                try
                {
                    Console.WriteLine(
                        $"Загрузка страницы {page}...");

                    List<Vacancy> parsed =
                        await searchPage(query, page);

                    found = parsed.Count;

                    foreach (Vacancy vacancy in parsed)
                    {
                        vacancy.Source = source;
                        vacancy.SearchQuery = query;
                        vacancy.CollectedAt = DateTime.UtcNow;

                        if (string.IsNullOrWhiteSpace(vacancy.Link))
                            continue;

                        if (SeenLinks.Add(NormalizeLink(vacancy.Link)))
                        {
                            AllVacancies.Add(vacancy);
                            added++;

                            Console.WriteLine(
                                $"  + {vacancy.Title} | " +
                                $"{vacancy.Company} | {vacancy.City}");
                        }
                    }

                    if (found == 0)
                    {
                        status = "Пустая страница";
                        Console.WriteLine(
                            "Вакансии не найдены. " +
                            "Возможны изменения HTML-разметки сайта.");

                        pageTimer.Stop();

                        AllStats.Add(new PageStat
                        {
                            Source = source,
                            Query = query,
                            Page = page,
                            Found = found,
                            Added = added,
                            ElapsedMs = pageTimer.ElapsedMilliseconds,
                            Status = status
                        });

                        break;
                    }
                }
                catch (Exception ex)
                {
                    Errors++;
                    status = "Ошибка: " + ex.GetType().Name;

                    Console.WriteLine(
                        $"Ошибка на странице {page}: {ex.Message}");
                }

                pageTimer.Stop();

                AllStats.Add(new PageStat
                {
                    Source = source,
                    Query = query,
                    Page = page,
                    Found = found,
                    Added = added,
                    ElapsedMs = pageTimer.ElapsedMilliseconds,
                    Status = status
                });

                if (status.StartsWith("Ошибка"))
                    break;

                if (page < maxPages)
                    await Task.Delay(DelayMs);
            }
        }

        Console.WriteLine(
            $"\nИсточник {source}: собрано вакансий — " +
            $"{AllVacancies.Count(v => v.Source == source)}");
    }

    // =========================================================
    // 1. HABR CAREER
    // =========================================================

    static async Task<List<Vacancy>> SearchHabrPage(
        string query, int page)
    {
        string url =
            $"{HabrUrl}/vacancies?q={Uri.EscapeDataString(query)}" +
            $"&type=all&page={page}";

        string html = await DownloadHtml(url);
        var doc = new HtmlDocument();
        doc.LoadHtml(html);

        var result = new List<Vacancy>();

        var cards = doc.DocumentNode.SelectNodes(
            "//div[contains(concat(' ', normalize-space(@class), ' '), " +
            "' vacancy-card ')]");

        if (cards == null)
        {
            Console.WriteLine(
                "  Habr Career: карточки не обнаружены.");
            return result;
        }

        foreach (var card in cards)
        {
            try
            {
                var titleNode = card.SelectSingleNode(
                    ".//div[contains(@class, 'vacancy-card__title')]//a")
                    ?? card.SelectSingleNode(
                    ".//a[contains(@href, '/vacancies/')]");

                if (titleNode == null)
                    continue;

                string title = Clean(titleNode.InnerText);
                string href = titleNode.GetAttributeValue("href", "");

                if (title == "" || href == "")
                    continue;

                if (!Uri.TryCreate(
                    new Uri(HabrUrl),
                    href,
                    out Uri? parsedUri))
                    continue;

                if (!Regex.IsMatch(
                    parsedUri.AbsolutePath,
                    @"^/vacancies/\d+/?$"))
                    continue;

                string link = parsedUri.GetLeftPart(UriPartial.Path);
                string cardText = Clean(card.InnerText);

                var companyNode = card.SelectSingleNode(
                    ".//a[contains(@href, '/companies/')]")
                    ?? card.SelectSingleNode(
                    ".//*[contains(@class, 'vacancy-card__company')]");

                string company = companyNode == null
                    ? ""
                    : Clean(companyNode.InnerText);

                result.Add(new Vacancy
                {
                    Title = title,
                    Company = company,
                    City = FindCity(card, cardText),
                    Salary = FindSalary(cardText),
                    Level = FindLevel(title + " " + cardText),
                    WorkFormat = FindWorkFormat(cardText),
                    Skills = FindSkills(card),
                    Link = link
                });
            }
            catch (Exception ex)
            {
                Errors++;
                Console.WriteLine(
                    "  Ошибка карточки Habr Career: " + ex.Message);
            }
        }

        return result;
    }

    // =========================================================
    // 2. RABOTA.RU
    // Сначала собираем ссылки из выдачи, затем загружаем детали.
    // =========================================================

    static async Task<List<Vacancy>> SearchRabotaPage(
        string query, int page)
    {
        string url =
            $"{RabotaUrl}/vacancy/?query={Uri.EscapeDataString(query)}" +
            $"&page={page}";

        string html = await DownloadHtml(url);

        var doc = new HtmlDocument();
        doc.LoadHtml(html);

        var result = new List<Vacancy>();

        // Сначала ищем карточки с известными вариантами классов.
        var cards = doc.DocumentNode.SelectNodes(
            "//div[contains(@class, 'vacancy-card')]" +
            " | //div[contains(@class, 'vacancy-preview-card')]" +
            " | //article" +
            " | //div[contains(@class, 'card')]");

        var links = new Dictionary<string, (string Title, string Company)>(
            StringComparer.OrdinalIgnoreCase);

        if (cards != null)
        {
            foreach (var card in cards)
            {
                var anchor = card.SelectSingleNode(
                    ".//a[contains(@href, '/vacancy/')]");

                if (anchor == null)
                    continue;

                AddRabotaLink(
                    links,
                    anchor,
                    card);
            }
        }

        // Запасной вариант: ищем ссылки во всём документе.
        if (links.Count == 0)
        {
            var anchors = doc.DocumentNode.SelectNodes(
                "//a[contains(@href, '/vacancy/')]");

            if (anchors != null)
            {
                foreach (var anchor in anchors)
                    AddRabotaLink(links, anchor, anchor);
            }
        }

        Console.WriteLine(
            $"  Rabota.ru: найдено ссылок — {links.Count}");

        if (links.Count == 0)
        {
            Console.WriteLine(
                "  Начало полученного HTML: " +
                Clean(doc.DocumentNode.InnerText).Substring(
                    0,
                    Math.Min(
                        300,
                        Clean(doc.DocumentNode.InnerText).Length)));

            return result;
        }

        // Получаем подробную информацию о каждой вакансии.
        foreach (var entry in links)
        {
            string link = entry.Key;

            try
            {
                await Task.Delay(DelayMs);

                string detailHtml = await DownloadHtml(link);

                Vacancy vacancy = ParseRabotaDetail(
                    detailHtml,
                    link,
                    entry.Value.Title,
                    entry.Value.Company);

                result.Add(vacancy);
            }
            catch (Exception ex)
            {
                Errors++;

                Console.WriteLine(
                    $"  Ошибка загрузки вакансии Rabota.ru: {ex.Message}");

                // Если детальная страница недоступна,
                // сохраняем хотя бы данные из поисковой выдачи.
                result.Add(new Vacancy
                {
                    Title = entry.Value.Title,
                    Company = entry.Value.Company,
                    City = "Не указан",
                    Salary = "Не указана",
                    Level = FindLevel(entry.Value.Title),
                    WorkFormat = "Не указан",
                    Skills = "Не указаны",
                    Link = link
                });
            }
        }

        return result;
    }

    static void AddRabotaLink(
        Dictionary<string, (string Title, string Company)> links,
        HtmlNode anchor,
        HtmlNode card)
    {
        string href = anchor.GetAttributeValue("href", "");
        string title = Clean(anchor.InnerText);

        if (href == "")
            return;

        if (!Uri.TryCreate(
            new Uri(RabotaUrl),
            href,
            out Uri? parsedUri))
            return;

        // Не принимаем ссылки на поисковую выдачу и категории.
        if (!Regex.IsMatch(
            parsedUri.AbsolutePath,
            @"/vacancy/\d+/?$"))
            return;

        string link = parsedUri.GetLeftPart(UriPartial.Path);

        if (title == "")
        {
            var titleNode = card.SelectSingleNode(
                ".//*[contains(@class, 'vacancy-card__title')]" +
                " | .//*[contains(@class, 'vacancy-preview-card__title')]");

            if (titleNode != null)
                title = Clean(titleNode.InnerText);
        }

        if (title == "")
            return;

        var companyNode = card.SelectSingleNode(
            ".//*[contains(@class, 'vacancy-card__company')]" +
            " | .//*[contains(@class, 'company-name')]");

        string company = companyNode == null
            ? ""
            : Clean(companyNode.InnerText);

        if (!links.ContainsKey(link))
            links.Add(link, (title, company));
    }

    static Vacancy ParseRabotaDetail(
        string html,
        string url,
        string fallbackTitle,
        string fallbackCompany)
    {
        var doc = new HtmlDocument();
        doc.LoadHtml(html);

        var titleNode = doc.DocumentNode.SelectSingleNode("//h1")
            ?? doc.DocumentNode.SelectSingleNode(
                "//meta[@property='og:title']");

        string title = fallbackTitle;

        if (titleNode != null)
        {
            string candidate =
                titleNode.Name.Equals(
                    "meta",
                    StringComparison.OrdinalIgnoreCase)
                ? titleNode.GetAttributeValue("content", "")
                : titleNode.InnerText;

            candidate = Clean(candidate);

            if (candidate != "")
                title = Regex.Replace(
                    candidate,
                    @"\s*[|–-]\s*Работа\.ru\s*$",
                    "",
                    RegexOptions.IgnoreCase);
        }

        var companyNode = doc.DocumentNode.SelectSingleNode(
            "//*[@itemprop='hiringOrganization']//*[@itemprop='name']")
            ?? doc.DocumentNode.SelectSingleNode(
            "//a[contains(@class, 'company')]")
            ?? doc.DocumentNode.SelectSingleNode(
            "//div[contains(@class, 'company-name')]");

        string company = companyNode == null
            ? fallbackCompany
            : Clean(companyNode.InnerText);

        string fullText = Clean(doc.DocumentNode.InnerText);

        var salaryNode = doc.DocumentNode.SelectSingleNode(
            "//*[contains(@class, 'salary')]")
            ?? doc.DocumentNode.SelectSingleNode(
            "//*[@itemprop='baseSalary']");

        string salary = salaryNode == null
            ? FindSalary(fullText)
            : Clean(salaryNode.InnerText);

        if (salary == "Не указана" &&
            Regex.IsMatch(
                fullText,
                @"по\s+договор[её]нности|договорная\s+зарплата",
                RegexOptions.IgnoreCase))
        {
            salary = "По договорённости";
        }

        return new Vacancy
        {
            Title = title,
            Company = company,
            City = FindCity(doc, url, fullText),
            Salary = string.IsNullOrWhiteSpace(salary)
                ? "Не указана"
                : salary,
            Level = FindLevel(fullText),
            WorkFormat = FindWorkFormat(fullText),
            Skills = FindSkills(doc),
            Link = url
        };
    }

    // =========================================================
    // 3. SUPERJOB
    // =========================================================

    static async Task<List<Vacancy>> SearchSuperJobPage(
        string query, int page)
    {
        string url =
            $"{SuperJobUrl}/vacancy/search/" +
            $"?keywords={Uri.EscapeDataString(query)}&page={page}";

        string html = await DownloadHtml(url);

        var doc = new HtmlDocument();
        doc.LoadHtml(html);

        var result = new List<Vacancy>();

        var cards = doc.DocumentNode.SelectNodes(
            "//div[contains(@class, '_-toc9')]" +
            " | //article" +
            " | //div[contains(@class, 'f-test-vacancy-item')]");

        Console.WriteLine(
            $"  SuperJob: найдено карточек — {cards?.Count ?? 0}");

        if (cards == null)
            return result;

        foreach (var card in cards)
        {
            try
            {
                var titleNode = card.SelectSingleNode(
                    ".//a[contains(@href, '/vakansii/')]");

                if (titleNode == null)
                    continue;

                string title = Clean(titleNode.InnerText);
                string href = titleNode.GetAttributeValue("href", "");

                if (title == "" || href == "")
                    continue;

                if (!Uri.TryCreate(
                    new Uri(SuperJobUrl),
                    href,
                    out Uri? parsedUri))
                    continue;

                if (!parsedUri.AbsolutePath.Contains(
                    "/vakansii/",
                    StringComparison.OrdinalIgnoreCase))
                    continue;

                string link = parsedUri.GetLeftPart(UriPartial.Path);
                string cardText = Clean(card.InnerText);

                var companyNode = card.SelectSingleNode(
                    ".//span[contains(@class, 'f-test-text-company-item')]")
                    ?? card.SelectSingleNode(
                    ".//a[contains(@href, '/clients/')]");

                string company = companyNode == null
                    ? ""
                    : Clean(companyNode.InnerText);

                result.Add(new Vacancy
                {
                    Title = title,
                    Company = company,
                    City = FindCity(card, cardText),
                    Salary = FindSalary(cardText),
                    Level = FindLevel(title + " " + cardText),
                    WorkFormat = FindWorkFormat(cardText),
                    Skills = FindSkills(card),
                    Link = link
                });
            }
            catch (Exception ex)
            {
                Errors++;
                Console.WriteLine(
                    "  Ошибка карточки SuperJob: " + ex.Message);
            }
        }

        return result;
    }

    // =========================================================
    // ЗАГРУЗКА HTML И ОБЩИЕ ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    // =========================================================

    static async Task<string> DownloadHtml(string url)
    {
        using var response = await Client.GetAsync(url);

        if (response.StatusCode == HttpStatusCode.Forbidden ||
            (int)response.StatusCode == 429)
        {
            throw new HttpRequestException(
                $"Сайт ограничил запрос: HTTP {(int)response.StatusCode}. " +
                $"URL: {url}");
        }

        response.EnsureSuccessStatusCode();

        return await response.Content.ReadAsStringAsync();
    }

    static string NormalizeLink(string link)
    {
        if (Uri.TryCreate(link, UriKind.Absolute, out Uri? uri))
            return uri.GetLeftPart(UriPartial.Path).TrimEnd('/');

        return link.Split('#')[0].TrimEnd('/');
    }

    static string Clean(string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
            return "";

        string text = HtmlEntity.DeEntitize(value);
        text = text.Replace('\u00A0', ' ');
        text = Regex.Replace(text, @"\s+", " ");

        return text.Trim();
    }

    // =========================================================
    // ИЗВЛЕЧЕНИЕ ГОРОДА
    // =========================================================

    static string FindCity(HtmlNode node, string text)
    {
        var cityNode = node.SelectSingleNode(
            ".//*[contains(@class, 'f-test-text-address')]")
            ?? node.SelectSingleNode(
            ".//*[contains(@class, 'address')]")
            ?? node.SelectSingleNode(
            ".//*[contains(@class, 'location')]")
            ?? node.SelectSingleNode(
            ".//*[contains(@class, 'region')]");

        if (cityNode != null)
        {
            string cityText = Clean(cityNode.InnerText);

            if (cityText != "")
                return cityText;
        }

        return FindCityInText(text);
    }

    static string FindCity(
        HtmlDocument doc,
        string url,
        string text)
    {
        var cityNode = doc.DocumentNode.SelectSingleNode(
            "//*[contains(@class, 'address')]")
            ?? doc.DocumentNode.SelectSingleNode(
            "//*[contains(@class, 'region')]")
            ?? doc.DocumentNode.SelectSingleNode(
            "//*[contains(@class, 'location')]");

        if (cityNode != null)
        {
            string cityText = Clean(cityNode.InnerText);

            if (cityText != "")
                return cityText;
        }

        // Не определяем город по домену www.rabota.ru:
        // он не указывает на конкретный город.
        return FindCityInText(text);
    }

    static string FindCityInText(string text)
    {
        string[] cities =
        {
            "Санкт-Петербург",
            "Нижний Новгород",
            "Екатеринбург",
            "Новосибирск",
            "Краснодар",
            "Москва",
            "Казань",
            "Минск",
            "Алматы"
        };

        foreach (string city in cities)
        {
            if (text.Contains(
                city,
                StringComparison.OrdinalIgnoreCase))
                return city;
        }

        return "Не указан";
    }

    // =========================================================
    // ИЗВЛЕЧЕНИЕ ЗАРПЛАТЫ, УРОВНЯ, ФОРМАТА И НАВЫКОВ
    // =========================================================

    static string FindSalary(string text)
    {
        var match = Regex.Match(
            text,
            @"(?:от|до)?\s*\d[\d\s]*(?:[.,]\d+)?" +
            @"(?:\s*[–—-]\s*\d[\d\s]*(?:[.,]\d+)?)?" +
            @"\s*(?:₽|руб\.?|USD|\$|EUR|€)",
            RegexOptions.IgnoreCase);

        if (match.Success)
            return Clean(match.Value);

        if (Regex.IsMatch(
            text,
            @"по\s+договор[её]нности|договорная\s+зарплата",
            RegexOptions.IgnoreCase))
            return "По договорённости";

        return "Не указана";
    }

    static string FindLevel(string text)
    {
        if (Regex.IsMatch(
            text,
            @"\bTech\s*Lead\b|\bLead\b|\bруководитель\b",
            RegexOptions.IgnoreCase))
            return "Lead";

        if (Regex.IsMatch(
            text,
            @"\bSenior\b|\bсеньор\b|\bстарший\b",
            RegexOptions.IgnoreCase))
            return "Senior";

        if (Regex.IsMatch(
            text,
            @"\bMiddle\b|\bмидл\b",
            RegexOptions.IgnoreCase))
            return "Middle";

        if (Regex.IsMatch(
            text,
            @"\bJunior\b|\bджуниор\b|\bмладший\b",
            RegexOptions.IgnoreCase))
            return "Junior";

        if (Regex.IsMatch(
            text,
            @"\bIntern\b|стаж[её]р|стажировка",
            RegexOptions.IgnoreCase))
            return "Intern";

        return "Не указан";
    }

    static string FindWorkFormat(string text)
    {
        if (Regex.IsMatch(
            text,
            @"удал[её]нн|remote",
            RegexOptions.IgnoreCase))
            return "Удалённо";

        if (Regex.IsMatch(
            text,
            @"гибрид|hybrid",
            RegexOptions.IgnoreCase))
            return "Гибрид";

        if (Regex.IsMatch(
            text,
            @"офис|on[\s-]?site",
            RegexOptions.IgnoreCase))
            return "Офис";

        return "Не указан";
    }

    static string FindSkills(HtmlNode node)
    {
        var nodes = node.SelectNodes(
            ".//*[contains(@class, 'vacancy-card__skills')]//a" +
            " | .//*[contains(@class, 'skills')]//a" +
            " | .//a[contains(@href, '/skills/')]" +
            " | .//a[contains(@class, 'tag')]" +
            " | .//span[contains(@class, 'tag')]" +
            " | .//ul[contains(@class, 'skills')]//li");

        if (nodes == null)
            return "Не указаны";

        string skills = string.Join(
            "; ",
            nodes.Select(n => Clean(n.InnerText))
                .Where(s => s != "")
                .Distinct(StringComparer.OrdinalIgnoreCase));

        return skills == "" ? "Не указаны" : skills;
    }

    static string FindSkills(HtmlDocument doc)
    {
        return FindSkills(doc.DocumentNode);
    }

    // =========================================================
    // СОХРАНЕНИЕ ОБЩЕГО CSV С ВАКАНСИЯМИ
    // =========================================================

    static void SaveVacanciesCsv(
        string path,
        List<Vacancy> vacancies)
    {
        using var writer = new StreamWriter(
            path,
            false,
            new UTF8Encoding(true));

        writer.WriteLine(
            "Источник;Поисковый запрос;Дата сбора;Название;" +
            "Компания;Город;Зарплата;Уровень;Формат работы;" +
            "Навыки;Ссылка");

        foreach (var v in vacancies)
        {
            writer.WriteLine(string.Join(";",
                Csv(v.Source),
                Csv(v.SearchQuery),
                Csv(v.CollectedAt.ToString("O")),
                Csv(v.Title),
                Csv(v.Company),
                Csv(v.City),
                Csv(v.Salary),
                Csv(v.Level),
                Csv(v.WorkFormat),
                Csv(v.Skills),
                Csv(v.Link)));
        }
    }

    // =========================================================
    // СОХРАНЕНИЕ СТАТИСТИКИ
    // =========================================================

    static void SaveStatsCsv(
        string path,
        List<PageStat> stats)
    {
        using var writer = new StreamWriter(
            path,
            false,
            new UTF8Encoding(true));

        writer.WriteLine(
            "Источник;Запрос;Страница;Найдено карточек;" +
            "Добавлено уникальных;Время, мс;Статус");

        foreach (var s in stats)
        {
            writer.WriteLine(string.Join(";",
                Csv(s.Source),
                Csv(s.Query),
                s.Page.ToString(CultureInfo.InvariantCulture),
                s.Found.ToString(CultureInfo.InvariantCulture),
                s.Added.ToString(CultureInfo.InvariantCulture),
                s.ElapsedMs.ToString(CultureInfo.InvariantCulture),
                Csv(s.Status)));
        }
    }

    static string Csv(string? value)
    {
        value = (value ?? "").Replace("\"", "\"\"");
        return "\"" + value + "\"";
    }

    // =========================================================
    // МОДЕЛИ ДАННЫХ
    // =========================================================

    class Vacancy
    {
        public string Source { get; set; } = "";
        public string SearchQuery { get; set; } = "";
        public DateTime CollectedAt { get; set; }

        public string Title { get; set; } = "";
        public string Company { get; set; } = "";
        public string City { get; set; } = "Не указан";
        public string Salary { get; set; } = "Не указана";
        public string Level { get; set; } = "Не указан";
        public string WorkFormat { get; set; } = "Не указан";
        public string Skills { get; set; } = "Не указаны";
        public string Link { get; set; } = "";
    }

    class PageStat
    {
        public string Source { get; set; } = "";
        public string Query { get; set; } = "";
        public int Page { get; set; }
        public int Found { get; set; }
        public int Added { get; set; }
        public long ElapsedMs { get; set; }
        public string Status { get; set; } = "";
    }
}