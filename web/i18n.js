(function () {
  const K = {
    ru: { tags: "все теги", franchises: "франшизы", compare: "сравнение", method: "методика",
      search: "поиск тега", sort: "сортировка", by_total: "по объёму", by_rise: "по росту",
      by_fall: "по падению", by_ai: "по доле ИИ", aish: "ИИ", ainote: "Доля ИИ — посты с этим тегом, также помеченные ai_generated. Разметка ручная, реальная доля выше.", n_posts: "n постов", ai: "ИИ, %", trend: "тренд", pm: "±",
      jump: "скачок", of: "из", peak: "пик", now: "сейчас", related: "похожие",
      badge: "бейдж", back: "← все теги", dash: "← дашборд", type: "тип", year: "год",
      title: "Популярность тегов по годам (доля постов)",
      foot: "Доля постов с тегом от всех постов года, %. Год восстановлен по ID поста, а не по дате загрузки: API не отдаёт дату, это оценка. Строка «n постов» — размер выборки по году, ранние годы слабы. «±» — 95% интервал за последние три года, п.п. «скачок» — максимальный рост доли за год, выше 8 отброшено как артефакт ретэггинга. Строка «ИИ, %» — доля постов с тегом ai_generated. Данные: rule34.xxx, рейтинги: {r}.",
      scale: "масштаб общий, пик", cmp: "сравнение тегов" },
    en: { tags: "all tags", franchises: "franchises", compare: "compare", method: "method",
      search: "search tag", sort: "sort", by_total: "by volume", by_rise: "by rise",
      by_fall: "by fall", by_ai: "by AI share", by_ai: "by AI share", aish: "AI", ainote: "AI share — posts with this tag also tagged ai_generated. Tagged manually, so the real figure is higher.", n_posts: "n posts", n_posts: "n posts", ai: "AI, %", trend: "trend", pm: "±",
      jump: "jump", of: "of", peak: "peak", now: "now", related: "related",
      badge: "badge", back: "← all tags", dash: "← dashboard", type: "type", year: "year",
      title: "Tag popularity by year (share of posts)",
      foot: "Share of posts carrying the tag, per year (%). Year is estimated from post ID, not upload date — the API exposes no date, so it is an estimate. Row «n posts» is the sample size for that year; early years are thin. «±» is a 95% interval over the last three years, pp. «jump» is the largest one-year rise; above 8 is dropped as a retagging artifact. Row «AI, %» is the share of posts tagged ai_generated. Data: rule34.xxx, ratings: {r}.",
      scale: "shared scale, peak", cmp: "tag comparison" }
  };
  let cur = localStorage.getItem("lang") || "en";
  window.t = k => (K[cur] && K[cur][k]) || k;
  window.setLang = l => { cur = l; localStorage.setItem("lang", l); paint(); };
  function paint() {
    document.documentElement.lang = cur;
    document.querySelectorAll("[data-i18n]").forEach(e => e.textContent = t(e.dataset.i18n));
    document.querySelectorAll("[data-i18n-ph]").forEach(e => e.placeholder = t(e.dataset.i18nPh));
    if (window.rerender) window.rerender();
  }
  window.addEventListener("DOMContentLoaded", paint);
})();