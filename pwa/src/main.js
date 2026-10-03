import './style.css';
import { t, lang, setLang, LANGS, isUsingFallback } from './lib/i18n.js';
import { prepare } from './lib/preprocess.js';
import { loadModel, classify } from './lib/infer.js';
import { guardMetrics, guardReasons } from './lib/guard.js';
import { addObservation, listObservations, markShared, removeObservation, pendingCount } from './lib/store.js';

const app = document.getElementById('app');
const state = { screen: 'home', config: null, advice: null, last: null, ready: false, error: null };
const CLASSES = ['healthy', 'miner', 'rust', 'phoma', 'cercospora'];

const el = (tag, props = {}, ...kids) => {
  const n = Object.assign(document.createElement(tag), props);
  for (const k of kids.flat()) if (k != null) n.append(k.nodeType ? k : document.createTextNode(k));
  return n;
};
const clsName = (i) => t('cls_' + CLASSES[i]);
const fmtDate = (ts) => new Date(ts).toLocaleString(lang === 'en' ? 'en-GB' : 'fr-FR', { dateStyle: 'short', timeStyle: 'short' });

async function init() {
  try {
    state.config = await loadModel();
    state.advice = await (await fetch(new URL('./knowledge/advice.json', document.baseURI))).json();
    state.ready = true;
  } catch (e) { state.error = String(e); }
  render();
}

function header() {
  const online = navigator.onLine;
  return el('header', {},
    el('h1', {}, t('app_name')),
    el('span', { className: 'badge ok' }, t('works_offline')),
    el('span', { className: 'badge ' + (online ? 'ok' : 'off'), id: 'net' }, online ? t('online') : t('offline')),
    el('div', { className: 'langs' }, LANGS.map((l) => el('button', { className: l === lang ? 'on' : '', textContent: l.toUpperCase(), onclick: () => { setLang(l); render(); } }))));
}

function nav() {
  const b = (id, label) => el('button', { className: state.screen === id ? 'on' : '', textContent: label, onclick: () => { state.screen = id; render(); } });
  return el('nav', {}, b('home', t('home')), b('history', t('my_obs')));
}

function filePicker() {
  const input = el('input', { type: 'file', accept: 'image/*', id: 'file' });
  input.setAttribute('capture', 'environment');
  input.onchange = () => input.files[0] && analyse(input.files[0]);
  const gallery = el('input', { type: 'file', accept: 'image/*', id: 'gallery' });
  gallery.onchange = () => gallery.files[0] && analyse(gallery.files[0]);
  return { input, gallery };
}

function homeScreen() {
  const { input, gallery } = filePicker();
  const box = el('main', {},
    el('p', { className: 'tagline' }, t('tagline')),
    el('button', { className: 'btn', id: 'take', textContent: '📷  ' + t('take_photo'), onclick: () => input.click() }),
    el('button', { className: 'btn secondary', id: 'choose', textContent: t('choose_photo'), onclick: () => gallery.click() }),
    input, gallery,
    el('div', { className: 'panel' }, el('h2', {}, t('protocol_title')), el('ul', {}, ['protocol_1', 'protocol_2', 'protocol_3'].map((k) => el('li', {}, t(k))))),
    el('div', { className: 'panel muted', id: 'limits' }, t('limits_note')),
    state.config ? el('div', { className: 'muted' }, t('model_info', { name: state.config.display_name, size: state.config.model_mb })) : null);
  pendingCount().then((n) => { if (n) box.insertBefore(el('div', { className: 'banner' }, t('waiting', { n })), box.children[1]); });
  return box;
}

function analysingScreen() { return el('main', {}, el('div', { className: 'spinner' }), el('p', { className: 'tagline', style: 'text-align:center' }, t('analyzing'))); }

async function analyse(file) {
  state.screen = 'analyzing'; render();
  try {
    const { previewCanvas, imageData } = await prepare(file);
    const metrics = guardMetrics(imageData);
    const reasons = state.config.guard ? guardReasons(metrics, state.config.guard.bounds) : [];
    const photo = await previewCanvas.convertToBlob({ type: 'image/jpeg', quality: 0.85 });
    if (reasons.length) {
      const id = await addObservation({ photo, tier: 'guard', reasons, metrics, lang, model: state.config.model_version });
      state.last = { photo, reasons, id, kind: 'guard' };
    } else {
      const res = await classify(imageData);
      const id = await addObservation({ photo, tier: res.tier, top1: res.top1, p1: res.p1, top2: res.top2, p2: res.p2, probs: res.probs, ms: res.ms, metrics, lang, model: state.config.model_version });
      state.last = { photo, res, id, kind: 'result' };
    }
    state.screen = 'result';
  } catch (e) { state.error = String(e); state.screen = 'home'; }
  render();
}

function resultScreen() {
  const L = state.last, url = URL.createObjectURL(L.photo);
  const main = el('main', {}, el('img', { className: 'photo', src: url, alt: '' }));
  if (L.kind === 'guard') {
    main.append(el('div', { className: 'tier guard', id: 'tier-guard' }, el('h2', {}, t('guard_title')), el('div', {}, t('guard_intro')),
      el('ul', {}, L.reasons.map((r) => el('li', {}, t('guard_' + r))))));
    main.append(el('button', { className: 'btn', textContent: t('retake'), onclick: () => { state.screen = 'home'; render(); } }));
    main.append(el('div', { className: 'muted' }, '✔ ' + t('saved_on_device') + ' — ' + t('obs_no_diag')));
    return main;
  }
  const r = L.res, name = clsName(r.top1), pct = Math.round(r.p1 * 100), adv = state.advice[lang === 'en' ? 'en' : 'fr'];
  if (r.tier === 'low') {
    main.append(el('div', { className: 'tier low', id: 'tier-low' }, el('h2', {}, t('result_low')), el('div', {}, t('result_low_body'))));
  } else {
    main.append(el('div', { className: 'tier ' + r.tier, id: 'tier-' + r.tier },
      el('div', { style: 'font-size:14px;opacity:.9' }, r.tier === 'high' ? t('result_high') : t('result_medium')),
      el('h2', {}, name),
      el('div', {}, t('confidence') + ' : ' + pct + ' %'), el('div', { className: 'bar' }, el('i', { style: `width:${pct}%` })),
      r.tier === 'medium' ? el('div', { style: 'margin-top:8px' }, t('result_medium_warn')) : null));
    const a = adv[CLASSES[r.top1]];
    main.append(el('div', { className: 'panel' }, el('h2', {}, name), el('div', {}, a.what),
      el('h2', { style: 'margin-top:10px' }, t('what_to_do') + ' — ' + t('ask_note')), el('ul', {}, a.do.map((x) => el('li', {}, x))), el('p', { style: 'margin:8px 0 0' }, adv.escalate)));
    if (r.p2 > 0.15) main.append(el('div', { className: 'muted' }, t('other_possibility') + ' : ' + clsName(r.top2) + ' (' + Math.round(r.p2 * 100) + ' %)'));
  }
  main.append(el('button', { className: 'btn warn', id: 'share', textContent: '✉  ' + t('ask_officer'), onclick: () => shareObs(L.id) }));
  main.append(el('button', { className: 'btn secondary', textContent: t('retake'), onclick: () => { state.screen = 'home'; render(); } }));
  main.append(el('div', { className: 'muted' }, '✔ ' + t('saved_on_device') + ' · ' + t('analyzed_in', { ms: r.ms })));
  main.append(el('div', { className: 'muted' }, t('validate_note')));
  return main;
}

function labelOf(o) {
  if (o.tier === 'guard') return t('obs_no_diag');
  if (o.tier === 'low') return t('result_low');
  return (o.tier === 'high' ? t('result_high') : t('result_medium')) + ': ' + clsName(o.top1) + ' (' + Math.round(o.p1 * 100) + ' %)';
}

async function shareObs(id) {
  const o = (await listObservations()).find((x) => x.id === id);
  if (!o) return;
  const file = new File([o.photo], `esaaka-${o.id}.jpg`, { type: 'image/jpeg' });
  const text = t('share_text', { date: fmtDate(o.ts), label: labelOf(o) });
  try {
    if (navigator.canShare?.({ files: [file] })) { await navigator.share({ files: [file], title: t('share_title'), text }); await markShared(id); }
    else {
      const a = el('a', { href: URL.createObjectURL(o.photo), download: file.name }); a.click();
      window.open('https://wa.me/?text=' + encodeURIComponent(text), '_blank'); alert(t('share_unavailable')); await markShared(id);
    }
  } catch (e) { /* user cancelled sharing: observation stays pending */ }
  render();
}

function historyScreen() {
  const main = el('main', {});
  listObservations().then((list) => {
    if (!list.length) main.append(el('p', { className: 'muted', id: 'empty' }, t('obs_empty')));
    for (const o of list) {
      main.append(el('div', { className: 'panel obs', 'data-id': o.id },
        el('img', { src: URL.createObjectURL(o.photo), alt: '' }),
        el('div', { className: 'meta' }, el('b', {}, labelOf(o)), el('span', { className: 'muted' }, fmtDate(o.ts)), ' ',
          el('span', { className: 'pill ' + (o.status === 'pending' ? 'pending' : '') }, o.status === 'pending' ? t('obs_pending') : t('obs_shared'))),
        el('div', {}, el('button', { className: 'btn small', textContent: t('send_now'), onclick: () => shareObs(o.id) }), ' ',
          el('button', { className: 'btn small secondary', textContent: '✕', 'aria-label': t('delete'), onclick: async () => { await removeObservation(o.id); render(); } }))));
    }
  });
  return main;
}

function render() {
  app.replaceChildren(header());
  if (lang === 'ee') app.append(el('div', { className: 'banner', style: 'margin:8px 16px 0' }, t('ee_banner')));
  if (state.error) app.append(el('main', {}, el('div', { className: 'tier low' }, state.error)));
  else if (!state.ready) app.append(el('main', {}, el('div', { className: 'spinner' })));
  else if (state.screen === 'analyzing') app.append(analysingScreen());
  else if (state.screen === 'result' && state.last) app.append(resultScreen());
  else if (state.screen === 'history') app.append(historyScreen());
  else app.append(homeScreen());
  app.append(nav());
}

window.addEventListener('online', render);
window.addEventListener('offline', render);
// test hook: runs the exact shipped pipeline (crop -> guard -> model -> tiers) without touching the UI
async function evalFile(file) {
  const { imageData } = await prepare(file);
  const metrics = guardMetrics(imageData);
  const reasons = state.config.guard ? guardReasons(metrics, state.config.guard.bounds) : [];
  const res = reasons.length ? null : await classify(imageData);
  return { metrics, reasons, res };
}
window.__esaaka = { state, analyse, evalFile };
render();
init();
