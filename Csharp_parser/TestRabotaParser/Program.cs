// using System;
// using System.Collections.Generic;
// using System.Diagnostics;
// using System.Globalization;
// using System.IO;
// using System.Linq;
// using System.Net;
// using System.Net.Http;
// using System.Text;
// using System.Text.RegularExpressions;
// using System.Threading.Tasks;
// using HtmlAgilityPack;

// internal class Program
// {
//     private static readonly HttpClient Http = CreateClient();
//     private static readonly string[] Queries = { "Python", "Data Scientist", "Machine Learning" };
//     private static readonly Dictionary<string, int> PageCounts = new() { ["Habr Career"] = 5, ["Rabota.ru"] = 2, ["SuperJob"] = 3 };
//     private static readonly HashSet<string> Seen = new(StringComparer.OrdinalIgnoreCase);
//     private static readonly List<Vacancy> Vacancies = new();
//     private static readonly List<PageStat> Stats = new();
//     private static readonly TimeSpan Delay = TimeSpan.FromMilliseconds(2500);

//     private static HttpClient CreateClient()
//     {
//         var handler = new HttpClientHandler { AutomaticDecompression = DecompressionMethods.All, AllowAutoRedirect = true };
//         var client = new HttpClient(handler) { Timeout = TimeSpan.FromSeconds(40) };
//         client.DefaultRequestHeaders.UserAgent.ParseAdd("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36");
//         client.DefaultRequestHeaders.Accept.ParseAdd("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8");
//         client.DefaultRequestHeaders.AcceptLanguage.ParseAdd("ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7");
//         return client;
//     }

//     private static async Task Main()
//     {
//         Console.OutputEncoding = Encoding.UTF8;
//         Console.WriteLine("Парсер вакансий: HtmlAgilityPack / C#");
//         foreach (string query in Queries)
//         {
//             await ParseHabr(query);
//             await ParseRabota(query);
//             await ParseSuperJob(query);
//         }
//         WriteVacancies();
//         WriteStats();
//         Console.WriteLine($"Готово: {Vacancies.Count} уникальных вакансий.");
//         Console.WriteLine("Файлы: vacancies_all.csv, parsing_stats_all.csv");
//     }

//     private static async Task ParseHabr(string query)
//     {
//         const string source = "Habr Career";
//         for (int page = 1; page <= PageCounts[source]; page++)
//         {
//             string url = $"https://career.habr.com/vacancies?query={Uri.EscapeDataString(query)}&page={page}";
//             await ParseSearchPage(source, query, page, url, async (doc, add) =>
//             {
//                 var cards = doc.DocumentNode.SelectNodes("//div[contains(@class,'vacancy-card')] | //article[contains(@class,'vacancy-card')]");
//                 if (cards == null) return 0;
//                 int found = 0;
//                 foreach (var card in cards)
//                 {
//                     var a = card.SelectSingleNode(".//a[contains(@href,'/vacancies/')]");
//                     string link = Normalize(a?.GetAttributeValue("href", "") ?? "", "https://career.habr.com");
//                     if (!IsHabrVacancy(link)) continue;
//                     found++;
//                     add(new Vacancy(source, query, Clean(a?.InnerText),
//                         Clean(card.SelectSingleNode(".//*[contains(@class,'company')]")?.InnerText),
//                         Clean(card.SelectSingleNode(".//*[contains(@class,'location')] ")?.InnerText),
//                         Clean(card.SelectSingleNode(".//*[contains(@class,'salary')] ")?.InnerText),
//                         Clean(card.SelectSingleNode(".//*[contains(@class,'experience')] ")?.InnerText),
//                         Clean(card.SelectSingleNode(".//*[contains(@class,'remote') or contains(@class,'employment')] ")?.InnerText),
//                         Clean(card.SelectSingleNode(".//*[contains(@class,'skills')] ")?.InnerText), link));
//                 }
//                 return found;
//             });
//         }
//     }

//     private static async Task ParseRabota(string query)
//     {
//         const string source = "Rabota.ru";
//         for (int page = 1; page <= PageCounts[source]; page++)
//         {
//             string url = $"https://www.rabota.ru/vacancy/?query={Uri.EscapeDataString(query)}&page={page}";
//             await ParseSearchPage(source, query, page, url, async (doc, add) =>
//             {
//                 var nodes = doc.DocumentNode.SelectNodes("//a[contains(@href,'/vacancy/')]");
//                 var links = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
//                 if (nodes != null)
//                     foreach (var a in nodes)
//                     {
//                         string link = Normalize(a.GetAttributeValue("href", ""), "https://www.rabota.ru");
//                         string title = Clean(a.InnerText);
//                         if (IsRabotaVacancy(link) && title.Length >= 3 && !links.ContainsKey(link)) links[link] = title;
//                     }
//                 foreach (var pair in links)
//                 {
//                     string title = pair.Value;
//                     try
//                     {
//                         string detail = await GetHtml(pair.Key);
//                         var d = new HtmlDocument(); d.LoadHtml(detail);
//                         title = First(Clean(d.DocumentNode.SelectSingleNode("//h1")?.InnerText), title);
//                         string description = Clean(d.DocumentNode.SelectSingleNode("//*[contains(@class,'description')] ")?.InnerText);
//                         add(new Vacancy(source, query, title,
//                             Clean(d.DocumentNode.SelectSingleNode("//*[contains(@class,'company')] ")?.InnerText),
//                             Clean(d.DocumentNode.SelectSingleNode("//*[contains(@class,'location') or contains(@class,'address')] ")?.InnerText),
//                             Clean(d.DocumentNode.SelectSingleNode("//*[contains(@class,'salary')] ")?.InnerText),
//                             ExtractLevel(description), ExtractFormat(description), ExtractSkills(description), pair.Key));
//                     }
//                     catch (Exception ex)
//                     {
//                         Console.WriteLine($"[Rabota.ru detail] {pair.Key}: {ex.Message}");
//                         add(new Vacancy(source, query, title, "", "", "", "", "", "", pair.Key));
//                     }
//                     await Task.Delay(Delay);
//                 }
//                 return links.Count;
//             });
//         }
//     }

//     private static async Task ParseSuperJob(string query)
//     {
//         const string source = "SuperJob";
//         for (int page = 1; page <= PageCounts[source]; page++)
//         {
//             string url = $"https://www.superjob.ru/vacancy/search/?keywords={Uri.EscapeDataString(query)}&page={page}";
//             await ParseSearchPage(source, query, page, url, async (doc, add) =>
//             {
//                 var nodes = doc.DocumentNode.SelectNodes("//a[contains(@href,'/vacancy/')]");
//                 var links = new Dictionary<string, HtmlNode>(StringComparer.OrdinalIgnoreCase);
//                 if (nodes != null)
//                     foreach (var a in nodes)
//                     {
//                         string link = Normalize(a.GetAttributeValue("href", ""), "https://www.superjob.ru");
//                         if (IsSuperJobVacancy(link) && !links.ContainsKey(link)) links[link] = a;
//                     }
//                 foreach (var pair in links)
//                 {
//                     var a = pair.Value; var card = a;
//                     for (int i = 0; i < 3 && card.ParentNode != null; i++) card = card.ParentNode;
//                     add(new Vacancy(source, query, Clean(a.InnerText),
//                         Clean(card.SelectSingleNode(".//*[contains(@class,'company')] ")?.InnerText),
//                         Clean(card.SelectSingleNode(".//*[contains(@class,'town') or contains(@class,'location')] ")?.InnerText),
//                         Clean(card.SelectSingleNode(".//*[contains(@class,'salary')] ")?.InnerText),
//                         Clean(card.SelectSingleNode(".//*[contains(@class,'experience')] ")?.InnerText),
//                         Clean(card.SelectSingleNode(".//*[contains(@class,'remote') or contains(@class,'employment')] ")?.InnerText),
//                         Clean(card.SelectSingleNode(".//*[contains(@class,'skills')] ")?.InnerText), pair.Key));
//                 }
//                 return links.Count;
//             });
//         }
//     }

//     private static async Task ParseSearchPage(string source, string query, int page, string url,
//         Func<HtmlDocument, Action<Vacancy>, Task<int>> parse)
//     {
//         var sw = Stopwatch.StartNew(); int found = 0, added = 0; string status = "OK";
//         try
//         {
//             var doc = new HtmlDocument(); doc.LoadHtml(await GetHtml(url));
//             found = await parse(doc, v => { v.DateCollected = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"); if (!string.IsNullOrWhiteSpace(v.Title) && !string.IsNullOrWhiteSpace(v.Link) && Seen.Add(v.Link)) { Vacancies.Add(v); added++; } });
//         }
//         catch (Exception ex)
//         {
//             status = ex is TaskCanceledException ? "TIMEOUT" : ex is HttpRequestException h && h.StatusCode.HasValue ? $"HTTP_{(int)h.StatusCode.Value}" : "ERROR";
//             Console.WriteLine($"[{source}] {query}, стр. {page}: {ex.Message}");
//         }
//         finally { sw.Stop(); Stats.Add(new PageStat(source, query, page, found, added, sw.ElapsedMilliseconds, status)); await Task.Delay(Delay); }
//     }

//     private static async Task<string> GetHtml(string url)
//     {
//         using var response = await Http.GetAsync(url);
//         response.EnsureSuccessStatusCode();
//         return await response.Content.ReadAsStringAsync();
//     }

//     private static string Normalize(string href, string baseUrl)
//     {
//         if (string.IsNullOrWhiteSpace(href) || href.StartsWith("javascript:", StringComparison.OrdinalIgnoreCase)) return "";
//         if (!Uri.TryCreate(new Uri(baseUrl), WebUtility.HtmlDecode(href.Trim()), out var uri)) return "";
//         return new UriBuilder(uri) { Query = "", Fragment = "" }.Uri.AbsoluteUri.TrimEnd('/');
//     }
//     private static bool IsHabrVacancy(string u) => Uri.TryCreate(u, UriKind.Absolute, out var x) && Regex.IsMatch(x.AbsolutePath, @"/vacancies/\d+$");
//     private static bool IsRabotaVacancy(string u) => Uri.TryCreate(u, UriKind.Absolute, out var x) && Regex.IsMatch(x.AbsolutePath, @"/vacancy/[^/]+$");
//     private static bool IsSuperJobVacancy(string u) => Uri.TryCreate(u, UriKind.Absolute, out var x) && Regex.IsMatch(x.AbsolutePath, @"/vacancy/[^/]+$");
//     private static string Clean(string? s) => string.IsNullOrWhiteSpace(s) ? "" : Regex.Replace(HtmlEntity.DeEntitize(s), @"\s+", " ").Trim();
//     private static string First(params string[] values) => values.FirstOrDefault(x => !string.IsNullOrWhiteSpace(x)) ?? "";
//     private static string ExtractLevel(string s) => Regex.Match(s ?? "", @"(?i)\b(junior|middle|senior|lead|стаж[её]р|без опыта|1[-– ]?3 года|3[-– ]?6 лет)\b").Value;
//     private static string ExtractFormat(string s) => Regex.Match(s ?? "", @"(?i)\b(удал[её]нно|гибрид|офис|remote|hybrid|on[- ]site)\b").Value;
//     private static string ExtractSkills(string s) => string.Join("; ", new[] { "Python", "C#", "SQL", "Java", "JavaScript", "Machine Learning", "TensorFlow", "PyTorch", "Pandas", "NumPy", "Docker", "Kubernetes", "Git" }.Where(x => (s ?? "").Contains(x, StringComparison.OrdinalIgnoreCase)));
//     private static string Csv(string? s) => "\"" + (s ?? "").Replace("\"", "\"\"") + "\"";

//     private static void WriteVacancies()
//     {
//         using var w = new StreamWriter("vacancies_all.csv", false, new UTF8Encoding(true));
//         w.WriteLine("Источник;Поисковый запрос;Дата сбора;Название;Компания;Город;Зарплата;Уровень;Формат работы;Навыки;Ссылка");
//         foreach (var v in Vacancies) w.WriteLine(string.Join(";", new[] { v.Source, v.Query, v.DateCollected, v.Title, v.Company, v.City, v.Salary, v.Level, v.WorkFormat, v.Skills, v.Link }.Select(Csv)));
//     }
//     private static void WriteStats()
//     {
//         using var w = new StreamWriter("parsing_stats_all.csv", false, new UTF8Encoding(true));
//         w.WriteLine("Источник;Поисковый запрос;Страница;Найдено ссылок;Добавлено уникальных;Время, мс;Статус");
//         foreach (var s in Stats) w.WriteLine(string.Join(";", new[] { s.Source, s.Query, s.Page.ToString(CultureInfo.InvariantCulture), s.Found.ToString(CultureInfo.InvariantCulture), s.Added.ToString(CultureInfo.InvariantCulture), s.ElapsedMs.ToString(CultureInfo.InvariantCulture), s.Status }.Select(Csv)));
//     }

//     private sealed class Vacancy
//     {
//         public string Source, Query, Title, Company, City, Salary, Level, WorkFormat, Skills, Link;
//         public string DateCollected = "";
//         public Vacancy(string source, string query, string title, string company, string city, string salary, string level, string format, string skills, string link)
//         { Source = source; Query = query; Title = title; Company = company; City = city; Salary = salary; Level = level; WorkFormat = format; Skills = skills; Link = link; }
//     }
//     private sealed record PageStat(string Source, string Query, int Page, int Found, int Added, long ElapsedMs, string Status);
// }
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
using HtmlAgilityPack;

internal class Program
{
    private static readonly HttpClient Http = CreateClient();
    private static readonly string[] Queries = { "Python", "Data Scientist", "Machine Learning" };
    private static readonly Dictionary<string, int> PageCounts = new() { ["Habr Career"] = 5, ["Rabota.ru"] = 2, ["SuperJob"] = 3 };
    private static readonly HashSet<string> Seen = new(StringComparer.OrdinalIgnoreCase);
    private static readonly List<Vacancy> Vacancies = new();
    private static readonly List<PageStat> Stats = new();
    private static readonly TimeSpan Delay = TimeSpan.FromMilliseconds(2500);
    private static readonly Dictionary<string, long> LastRequestTicks = new(StringComparer.OrdinalIgnoreCase);
    private static int DetailRequestCount = 0;
    private static int ErrorCount = 0;

    private static HttpClient CreateClient()
    {
        var handler = new HttpClientHandler { AutomaticDecompression = DecompressionMethods.All, AllowAutoRedirect = true };
        var client = new HttpClient(handler) { Timeout = TimeSpan.FromSeconds(40) };
        client.DefaultRequestHeaders.UserAgent.ParseAdd("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36");
        client.DefaultRequestHeaders.Accept.ParseAdd("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8");
        client.DefaultRequestHeaders.AcceptLanguage.ParseAdd("ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7");
        return client;
    }

    private static async Task Main()
    {
        Console.OutputEncoding = Encoding.UTF8;
        Console.WriteLine("Парсер вакансий: HtmlAgilityPack / C#");
        var runSw = Stopwatch.StartNew();
        foreach (string query in Queries)
        {
            await ParseHabr(query);
            await ParseRabota(query);
            await ParseSuperJob(query);
        }
        WriteVacancies();
        WriteStats();
        runSw.Stop();
        WriteRunSummary(runSw.Elapsed.TotalSeconds);
        Console.WriteLine($"Готово: {Vacancies.Count} уникальных вакансий.");
        Console.WriteLine($"Общее время: {runSw.Elapsed.TotalSeconds:F2} сек.");
        Console.WriteLine("Файлы: vacancies_all.csv, parsing_stats_all.csv, run_summary.csv");
    }

    private static async Task ParseHabr(string query)
    {
        const string source = "Habr Career";
        for (int page = 1; page <= PageCounts[source]; page++)
        {
            string url = $"https://career.habr.com/vacancies?query={Uri.EscapeDataString(query)}&page={page}";
            await ParseSearchPage(source, query, page, url, async (doc, add) =>
            {
                var cards = doc.DocumentNode.SelectNodes("//div[contains(@class,'vacancy-card')] | //article[contains(@class,'vacancy-card')]");
                if (cards == null) return 0;
                int found = 0;
                foreach (var card in cards)
                {
                    var a = card.SelectSingleNode(".//a[contains(@href,'/vacancies/')]");
                    string link = Normalize(a?.GetAttributeValue("href", "") ?? "", "https://career.habr.com");
                    if (!IsHabrVacancy(link)) continue;
                    found++;
                    add(new Vacancy(source, query, Clean(a?.InnerText),
                        Clean(card.SelectSingleNode(".//*[contains(@class,'company')]")?.InnerText),
                        Clean(card.SelectSingleNode(".//*[contains(@class,'location')] ")?.InnerText),
                        Clean(card.SelectSingleNode(".//*[contains(@class,'salary')] ")?.InnerText),
                        Clean(card.SelectSingleNode(".//*[contains(@class,'experience')] ")?.InnerText),
                        Clean(card.SelectSingleNode(".//*[contains(@class,'remote') or contains(@class,'employment')] ")?.InnerText),
                        Clean(card.SelectSingleNode(".//*[contains(@class,'skills')] ")?.InnerText), link));
                }
                return found;
            });
        }
    }

    private static async Task ParseRabota(string query)
    {
        const string source = "Rabota.ru";
        for (int page = 1; page <= PageCounts[source]; page++)
        {
            string url = $"https://www.rabota.ru/vacancy/?query={Uri.EscapeDataString(query)}&page={page}";
            await ParseSearchPage(source, query, page, url, async (doc, add) =>
            {
                var nodes = doc.DocumentNode.SelectNodes("//a[contains(@href,'/vacancy/')]");
                var links = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
                if (nodes != null)
                    foreach (var a in nodes)
                    {
                        string link = Normalize(a.GetAttributeValue("href", ""), "https://www.rabota.ru");
                        string title = Clean(a.InnerText);
                        if (IsRabotaVacancy(link) && title.Length >= 3 && !links.ContainsKey(link)) links[link] = title;
                    }
                foreach (var pair in links)
                {
                    string title = pair.Value;
                    try
                    {
                        DetailRequestCount++;
                        string detail = await GetHtml(pair.Key);
                        var d = new HtmlDocument(); d.LoadHtml(detail);
                        title = First(Clean(d.DocumentNode.SelectSingleNode("//h1")?.InnerText), title);
                        string description = Clean(d.DocumentNode.SelectSingleNode("//*[contains(@class,'description')] ")?.InnerText);
                        add(new Vacancy(source, query, title,
                            Clean(d.DocumentNode.SelectSingleNode("//*[contains(@class,'company')] ")?.InnerText),
                            Clean(d.DocumentNode.SelectSingleNode("//*[contains(@class,'location') or contains(@class,'address')] ")?.InnerText),
                            Clean(d.DocumentNode.SelectSingleNode("//*[contains(@class,'salary')] ")?.InnerText),
                            ExtractLevel(description), ExtractFormat(description), ExtractSkills(description), pair.Key));
                    }
                    catch (Exception ex)
                    {
                        ErrorCount++;
                        Console.WriteLine($"[Rabota.ru detail] {pair.Key}: {ex.Message}");
                        add(new Vacancy(source, query, title, "", "", "", "", "", "", pair.Key));
                    }
                }
                return links.Count;
            });
        }
    }

    private static async Task ParseSuperJob(string query)
    {
        const string source = "SuperJob";
        for (int page = 1; page <= PageCounts[source]; page++)
        {
            string url = $"https://www.superjob.ru/vacancy/search/?keywords={Uri.EscapeDataString(query)}&page={page}";
            await ParseSearchPage(source, query, page, url, async (doc, add) =>
            {
                var nodes = doc.DocumentNode.SelectNodes("//a[contains(@href,'/vacancy/')]");
                var links = new Dictionary<string, HtmlNode>(StringComparer.OrdinalIgnoreCase);
                if (nodes != null)
                    foreach (var a in nodes)
                    {
                        string link = Normalize(a.GetAttributeValue("href", ""), "https://www.superjob.ru");
                        if (IsSuperJobVacancy(link) && !links.ContainsKey(link)) links[link] = a;
                    }
                foreach (var pair in links)
                {
                    var a = pair.Value; var card = a;
                    for (int i = 0; i < 3 && card.ParentNode != null; i++) card = card.ParentNode;
                    add(new Vacancy(source, query, Clean(a.InnerText),
                        Clean(card.SelectSingleNode(".//*[contains(@class,'company')] ")?.InnerText),
                        Clean(card.SelectSingleNode(".//*[contains(@class,'town') or contains(@class,'location')] ")?.InnerText),
                        Clean(card.SelectSingleNode(".//*[contains(@class,'salary')] ")?.InnerText),
                        Clean(card.SelectSingleNode(".//*[contains(@class,'experience')] ")?.InnerText),
                        Clean(card.SelectSingleNode(".//*[contains(@class,'remote') or contains(@class,'employment')] ")?.InnerText),
                        Clean(card.SelectSingleNode(".//*[contains(@class,'skills')] ")?.InnerText), pair.Key));
                }
                return links.Count;
            });
        }
    }

    private static async Task ParseSearchPage(string source, string query, int page, string url,
        Func<HtmlDocument, Action<Vacancy>, Task<int>> parse)
    {
        long searchResponseMs = 0; int found = 0, added = 0; string status = "OK";
        try
        {
            // The timer starts after the politeness delay and measures only the HTTP request
            // plus reading the response body. Parsing and detail-page requests are excluded.
            var result = await GetHtmlTimed(url);
            searchResponseMs = result.ElapsedMs;
            var doc = new HtmlDocument(); doc.LoadHtml(result.Html);
            found = await parse(doc, v => { v.DateCollected = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"); if (!string.IsNullOrWhiteSpace(v.Title) && !string.IsNullOrWhiteSpace(v.Link) && Seen.Add(v.Link)) { Vacancies.Add(v); added++; } });
        }
        catch (Exception ex)
        {
            ErrorCount++;
            status = ex is TaskCanceledException ? "TIMEOUT" : ex is HttpRequestException h && h.StatusCode.HasValue ? $"HTTP_{(int)h.StatusCode.Value}" : "ERROR";
            Console.WriteLine($"[{source}] {query}, стр. {page}: {ex.Message}");
        }
        finally { Stats.Add(new PageStat(source, query, page, found, added, searchResponseMs, status)); }
    }

    private static async Task<string> GetHtml(string url)
    {
        var result = await GetHtmlTimed(url);
        return result.Html;
    }

    private static async Task<(string Html, long ElapsedMs)> GetHtmlTimed(string url)
    {
        // Match Scrapy's per-domain DOWNLOAD_DELAY behaviour as closely as possible.
        string host = new Uri(url).Host;
        if (LastRequestTicks.TryGetValue(host, out long previousTicks))
        {
            double elapsedSeconds = (Stopwatch.GetTimestamp() - previousTicks) / (double)Stopwatch.Frequency;
            double waitMs = Delay.TotalMilliseconds - elapsedSeconds * 1000.0;
            if (waitMs > 0) await Task.Delay(TimeSpan.FromMilliseconds(waitMs));
        }
        LastRequestTicks[host] = Stopwatch.GetTimestamp();

        var sw = Stopwatch.StartNew();
        using var response = await Http.GetAsync(url);
        response.EnsureSuccessStatusCode();
        string html = await response.Content.ReadAsStringAsync();
        sw.Stop();
        return (html, sw.ElapsedMilliseconds);
    }

    private static string Normalize(string href, string baseUrl)
    {
        if (string.IsNullOrWhiteSpace(href) || href.StartsWith("javascript:", StringComparison.OrdinalIgnoreCase)) return "";
        if (!Uri.TryCreate(new Uri(baseUrl), WebUtility.HtmlDecode(href.Trim()), out var uri)) return "";
        return new UriBuilder(uri) { Query = "", Fragment = "" }.Uri.AbsoluteUri.TrimEnd('/');
    }
    private static bool IsHabrVacancy(string u) => Uri.TryCreate(u, UriKind.Absolute, out var x) && Regex.IsMatch(x.AbsolutePath, @"/vacancies/\d+$");
    private static bool IsRabotaVacancy(string u) => Uri.TryCreate(u, UriKind.Absolute, out var x) && Regex.IsMatch(x.AbsolutePath, @"/vacancy/[^/]+$");
    private static bool IsSuperJobVacancy(string u) => Uri.TryCreate(u, UriKind.Absolute, out var x) && Regex.IsMatch(x.AbsolutePath, @"/vacancy/[^/]+$");
    private static string Clean(string? s) => string.IsNullOrWhiteSpace(s) ? "" : Regex.Replace(HtmlEntity.DeEntitize(s), @"\s+", " ").Trim();
    private static string First(params string[] values) => values.FirstOrDefault(x => !string.IsNullOrWhiteSpace(x)) ?? "";
    private static string ExtractLevel(string s) => Regex.Match(s ?? "", @"(?i)\b(junior|middle|senior|lead|стаж[её]р|без опыта|1[-– ]?3 года|3[-– ]?6 лет)\b").Value;
    private static string ExtractFormat(string s) => Regex.Match(s ?? "", @"(?i)\b(удал[её]нно|гибрид|офис|remote|hybrid|on[- ]site)\b").Value;
    private static string ExtractSkills(string s) => string.Join("; ", new[] { "Python", "C#", "SQL", "Java", "JavaScript", "Machine Learning", "TensorFlow", "PyTorch", "Pandas", "NumPy", "Docker", "Kubernetes", "Git" }.Where(x => (s ?? "").Contains(x, StringComparison.OrdinalIgnoreCase)));
    private static string Csv(string? s) => "\"" + (s ?? "").Replace("\"", "\"\"") + "\"";

    private static void WriteVacancies()
    {
        using var w = new StreamWriter("vacancies_all.csv", false, new UTF8Encoding(true));
        w.WriteLine("Источник;Поисковый запрос;Дата сбора;Название;Компания;Город;Зарплата;Уровень;Формат работы;Навыки;Ссылка");
        foreach (var v in Vacancies) w.WriteLine(string.Join(";", new[] { v.Source, v.Query, v.DateCollected, v.Title, v.Company, v.City, v.Salary, v.Level, v.WorkFormat, v.Skills, v.Link }.Select(Csv)));
    }
    private static void WriteStats()
    {
        using var w = new StreamWriter("parsing_stats_all.csv", false, new UTF8Encoding(true));
        w.WriteLine("Источник;Поисковый запрос;Страница;Найдено ссылок;Добавлено уникальных;Время ответа поисковой страницы, мс;Статус");
        foreach (var s in Stats) w.WriteLine(string.Join(";", new[] { s.Source, s.Query, s.Page.ToString(CultureInfo.InvariantCulture), s.Found.ToString(CultureInfo.InvariantCulture), s.Added.ToString(CultureInfo.InvariantCulture), s.ElapsedMs.ToString(CultureInfo.InvariantCulture), s.Status }.Select(Csv)));
    }

    private static void WriteRunSummary(double totalElapsedSeconds)
    {
        using var w = new StreamWriter("run_summary.csv", false, new UTF8Encoding(true));
        w.WriteLine("Парсер;Общее время, сек;Уникальных вакансий;Поисковых страниц;Запросов к страницам вакансий;Ошибок");
        w.WriteLine(string.Join(";", new[] { "C# HtmlAgilityPack", totalElapsedSeconds.ToString("F3", CultureInfo.InvariantCulture),
            Vacancies.Count.ToString(CultureInfo.InvariantCulture), Stats.Count.ToString(CultureInfo.InvariantCulture),
            DetailRequestCount.ToString(CultureInfo.InvariantCulture), ErrorCount.ToString(CultureInfo.InvariantCulture) }.Select(Csv)));
    }

    private sealed class Vacancy
    {
        public string Source, Query, Title, Company, City, Salary, Level, WorkFormat, Skills, Link;
        public string DateCollected = "";
        public Vacancy(string source, string query, string title, string company, string city, string salary, string level, string format, string skills, string link)
        { Source = source; Query = query; Title = title; Company = company; City = city; Salary = salary; Level = level; WorkFormat = format; Skills = skills; Link = link; }
    }
    private sealed record PageStat(string Source, string Query, int Page, int Found, int Added, long ElapsedMs, string Status);
}
