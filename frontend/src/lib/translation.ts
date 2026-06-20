export const getCookie = (name: string): string | null => {
  const nameEQ = name + "=";
  const ca = document.cookie.split(';');
  for (let i = 0; i < ca.length; i++) {
    let c = ca[i];
    while (c.charAt(0) === ' ') c = c.substring(1, c.length);
    if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
  }
  return null;
};

export const setCookie = (name: string, value: string, days = 365) => {
  let expires = "";
  if (days) {
    const date = new Date();
    date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
    expires = "; expires=" + date.toUTCString();
  }
  document.cookie = name + "=" + (value || "") + expires + "; path=/";
};

export const getTranslationLanguage = (): string => {
  const stored = localStorage.getItem('mootion_language_pref');
  if (stored) return stored;

  const cookieVal = getCookie('googtrans');
  if (cookieVal) {
    const parts = cookieVal.split('/');
    const lang = parts[parts.length - 1];
    if (lang === 'hi' || lang === 'en') return lang;
  }
  return 'en';
};

export const setTranslationLanguage = (langCode: string) => {
  const currentLang = getTranslationLanguage();
  if (currentLang !== langCode) {
    const targetValue = `/en/${langCode}`;
    setCookie('googtrans', targetValue);
    localStorage.setItem('mootion_language_pref', langCode);
    window.location.reload();
  }
};

export const syncOnboardingLanguage = (langName: string) => {
  const code = langName.toLowerCase() === 'hindi' ? 'hi' : 'en';
  const targetValue = `/en/${code}`;
  setCookie('googtrans', targetValue);
  localStorage.setItem('mootion_language_pref', code);
};
