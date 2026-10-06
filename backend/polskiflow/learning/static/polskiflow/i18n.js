(() => {
  const translations = document.documentElement.lang === 'pl' ? window.PolskiFlowPolishMessages || {} : {};
  const t = (text, ...values) => {
    if (!Array.isArray(text)) return translations[text] || text;
    const key = text.map((part, i) => part + (i < values.length ? `%(v${i})s` : '')).join('');
    const translated = translations[key];
    if (translated) return translated.replace(/%\(v(\d+)\)s/g, (_, index) => String(values[Number(index)]));
    return text.map((part, i) => part + (values[i] ?? '')).join('');
  };
  window.PolskiFlowI18n = {t};
})();
