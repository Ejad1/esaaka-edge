import fr from '../i18n/fr.json';
import en from '../i18n/en.json';
import ee from '../i18n/ee.json';

const dict = { fr, en, ee };
export let lang = localStorage.getItem('esaaka_lang') || 'fr';
export const LANGS = ['fr', 'en', 'ee'];
export function setLang(l) { lang = l; localStorage.setItem('esaaka_lang', l); document.documentElement.lang = l === 'ee' ? 'ee' : l; }
/** Ewe strings are shown only when a human-validated translation exists; otherwise French is shown (never machine-invented Ewe). */
export function t(key, vars = {}) {
  let s = (lang !== 'fr' && dict[lang][key]) || (dict.fr[key] ?? key);
  for (const [k, v] of Object.entries(vars)) s = s.replaceAll(`{${k}}`, v);
  return s;
}
export function isUsingFallback(key) { return lang === 'ee' && !dict.ee[key]; }
export function eeCoverage() { const ks = Object.keys(dict.fr); return [ks.filter((k) => dict.ee[k]).length, ks.length]; }
