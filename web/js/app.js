/* ==========================================================================
   Quantum Terminal — front-end da News Analytics Platform
   Consome a API em /api (api/servidor.py). JavaScript puro, sem build.
   ========================================================================== */
'use strict';

/* ---------------------------------------------------------------------------
   Utilitários
--------------------------------------------------------------------------- */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const fmt = (n, d = 2) => (n == null || isNaN(n) ? '—' : Number(n).toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d }));
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const sinal = (v) => (v > 0 ? '▲' : v < 0 ? '▼' : '=');
const classe = (v) => (v > 0 ? 'up-t' : v < 0 ? 'down-t' : 'flat-t');
// Casas decimais: câmbio com 4 (R$ 5,5146); índices/cripto altos sem decimais; o resto com 2
const casas = (preco, ticker = '') => (/=X$|^USD|^EUR|D[óo]lar|DOLAR|EURO/i.test(ticker) ? 4 : preco >= 10000 ? 0 : 2);

const armazenamento = {
  ler(chave, padrao) { try { const v = localStorage.getItem(chave); return v == null ? padrao : JSON.parse(v); } catch { return padrao; } },
  gravar(chave, valor) { try { localStorage.setItem(chave, JSON.stringify(valor)); } catch { /* modo privado */ } },
};

async function api(caminho, opcoes = {}) {
  const resp = await fetch(caminho, { headers: { 'Content-Type': 'application/json' }, ...opcoes });
  let dados = null;
  try { dados = await resp.json(); } catch { /* sem corpo */ }
  if (!resp.ok) {
    const detalhe = dados?.detail;
    const msg = Array.isArray(detalhe) ? detalhe.map((d) => d.msg).join('; ') : detalhe || `Erro ${resp.status}`;
    throw new Error(msg);
  }
  return dados;
}

function icones() { if (window.lucide) window.lucide.createIcons(); }

function toast(msg, tipo = 'ok') {
  const t = document.createElement('div');
  t.className = 'toast' + (tipo === 'err' ? ' err' : '');
  t.innerHTML = `<i data-lucide="${tipo === 'err' ? 'octagon-x' : 'check-circle-2'}" style="color:var(${tipo === 'err' ? '--qt-down' : '--qt-cyan'})"></i><span>${esc(msg)}</span>`;
  $('#toasts').appendChild(t); icones();
  setTimeout(() => { t.classList.add('out'); setTimeout(() => t.remove(), 260); }, 3200);
}

function renderMarkdown(md) {
  if (window.marked && window.DOMPurify) {
    // breaks: as referências "[1] ...", "[2] ..." vêm em linhas simples, sem linha em branco entre elas
    const html = window.DOMPurify.sanitize(window.marked.parse(md || '', { gfm: true, breaks: true }), { ADD_ATTR: ['target'] });
    const div = document.createElement('div'); div.innerHTML = html;
    $$('a[href^="http"]', div).forEach((a) => { a.target = '_blank'; a.rel = 'noopener noreferrer'; });
    return div.innerHTML;
  }
  return `<pre style="white-space:pre-wrap">${esc(md)}</pre>`; // fallback sem bibliotecas
}

/* ---------------------------------------------------------------------------
   Estado
--------------------------------------------------------------------------- */
const WATCH_PADRAO = ['PETR4', 'VALE3', 'ITUB4', 'BBAS3', 'WEGE3', 'MXRF11', 'IVVB11'];
const estado = {
  versoes: [],
  versao: armazenamento.ler('qt-versao', 'V5'),
  watchlist: armazenamento.ler('qt-watchlist', WATCH_PADRAO),
  panorama: {},
  indicadores: {},
  cotacoes: [],
  materias: [],
  periodo: '1mo',
  executando: false,
};

/* ---------------------------------------------------------------------------
   Navegação
--------------------------------------------------------------------------- */
const TITULOS = { painel: 'Painel', materias: 'Matérias', watchlist: 'Watchlist', simulador: 'Simulador RF' };
function navegar(view) {
  if (!TITULOS[view]) view = 'painel';
  $$('.view').forEach((v) => v.classList.toggle('active', v.dataset.view === view));
  $$('.side-link[data-nav]').forEach((l) => l.classList.toggle('active', l.dataset.nav === view));
  $('#crumb').textContent = TITULOS[view];
  if (location.hash !== '#' + view) history.replaceState(null, '', '#' + view);
  fecharPaineis();
  if (view === 'materias') carregarMaterias();
  if (view === 'simulador') simularCompleto();
}
document.addEventListener('click', (e) => {
  const n = e.target.closest('[data-nav]'); if (n) { e.preventDefault(); navegar(n.dataset.nav); }
  const a = e.target.closest('[data-ask]'); if (a) { abrirChat(); perguntar(a.dataset.ask); }
  if (e.target.closest('[data-open-chat]')) abrirChat();
});
addEventListener('hashchange', () => navegar(location.hash.slice(1)));

const chatEmGaveta = () => matchMedia('(max-width: 1080px)').matches;
function abrirChat() {
  if (chatEmGaveta()) { $('#chat').classList.add('open'); $('#scrim').classList.add('show'); }
  setTimeout(() => $('#chat-in').focus(), 200);
}
function fecharPaineis() { $('#chat').classList.remove('open'); $('#side').classList.remove('open'); $('#scrim').classList.remove('show'); }
$('#scrim').addEventListener('click', fecharPaineis);
$('#chat-close').addEventListener('click', fecharPaineis);
$('#open-side').addEventListener('click', () => { $('#side').classList.add('open'); $('#scrim').classList.add('show'); });
$('#collapse').addEventListener('click', () => { const c = $('#side').classList.toggle('collapsed'); armazenamento.gravar('qt-side', c); });
if (armazenamento.ler('qt-side', false)) $('#side').classList.add('collapsed');
addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); ($('#search').offsetParent ? $('#search') : $('#chat-in')).focus(); }
  if (e.key === 'Escape') {
    const painelAberto = $('#chat.open, #side.open');
    if (painelAberto && !estado.executando) fecharPaineis();
    else if (estado.executando) cancelarPergunta();
    else fecharPaineis();
  }
});

/* ---------------------------------------------------------------------------
   Relógio do pregão (B3: 10h00–17h55, dias úteis, horário de Brasília)
--------------------------------------------------------------------------- */
function relogio() {
  const agora = new Date();
  const partes = Object.fromEntries(new Intl.DateTimeFormat('pt-BR', { timeZone: 'America/Sao_Paulo', weekday: 'short', hour: '2-digit', minute: '2-digit', hour12: false })
    .formatToParts(agora).map((p) => [p.type, p.value]));
  const min = +partes.hour * 60 + +partes.minute;
  const util = !/sáb|dom/i.test(partes.weekday);
  const aberto = util && min >= 600 && min < 1075;
  const el = $('#clock'); el.style.color = aberto ? css('--qt-up') : css('--qt-text-3');
  $('.dot', el).classList.toggle('blink', aberto);
  $('#clock-txt').textContent = `${aberto ? 'ABERTO' : 'FECHADO'} · ${partes.hour}:${partes.minute} BRT`;
}

/* ---------------------------------------------------------------------------
   Gráficos (SVG)
--------------------------------------------------------------------------- */
function sparkline(svg, valores, cor) {
  if (!svg || !valores?.length) return;
  const w = 200, h = 40, min = Math.min(...valores), max = Math.max(...valores);
  const pts = valores.map((v, i) => [(i / (valores.length - 1 || 1)) * w, h - 2 - ((v - min) / (max - min || 1)) * (h - 4)]);
  const d = pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ',' + p[1].toFixed(1)).join(' ');
  const id = 's' + Math.random().toString(36).slice(2, 8);
  svg.innerHTML = `<defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${cor}" stop-opacity=".35"/><stop offset="1" stop-color="${cor}" stop-opacity="0"/></linearGradient></defs>
    <path d="${d} L${w},${h} L0,${h} Z" fill="url(#${id})"/><path d="${d}" fill="none" stroke="${cor}" stroke-width="1.5" vector-effect="non-scaling-stroke" style="filter:drop-shadow(0 0 4px ${cor})"/>`;
}

function rotuloTempo(iso, periodo) {
  const d = new Date(iso);
  if (periodo === '1d') return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', timeZone: 'America/Sao_Paulo' });
  if (periodo === '5d') return d.toLocaleDateString('pt-BR', { weekday: 'short', timeZone: 'America/Sao_Paulo' }).replace('.', '');
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', timeZone: 'America/Sao_Paulo' });
}

function graficoLinha(el, pontos, periodo, { h = 240 } = {}) {
  if (!pontos?.length) { el.innerHTML = '<div class="chart-empty">sem dados para o período</div>'; return; }
  const dados = pontos.map((p) => p.v);
  const w = Math.max(320, el.clientWidth || 800), pad = { l: 6, r: 62, t: 10, b: 24 };
  const min = Math.min(...dados), max = Math.max(...dados), folga = (max - min) * 0.08 || max * 0.002;
  const lo = min - folga, hi = max + folga;
  const sobe = dados.at(-1) >= dados[0];
  const cor = sobe ? css('--qt-cyan') : css('--qt-down');
  const x = (i) => pad.l + (i / (dados.length - 1 || 1)) * (w - pad.l - pad.r);
  const y = (v) => pad.t + (1 - (v - lo) / (hi - lo)) * (h - pad.t - pad.b);
  const d = dados.map((v, i) => (i ? 'L' : 'M') + x(i).toFixed(1) + ',' + y(v).toFixed(1)).join(' ');
  const dec = casas(max);
  const grade = [0, 0.25, 0.5, 0.75, 1].map((f) => { const v = lo + (hi - lo) * (1 - f), yy = pad.t + f * (h - pad.t - pad.b);
    return `<line x1="${pad.l}" x2="${w - pad.r}" y1="${yy}" y2="${yy}"/><text class="chart-axis" x="${w - pad.r + 8}" y="${yy + 3}">${fmt(v, dec)}</text>`; }).join('');
  const nRot = Math.min(5, pontos.length);
  const eixoX = Array.from({ length: nRot }, (_, k) => { const i = Math.round((k * (pontos.length - 1)) / (nRot - 1 || 1));
    return `<text class="chart-axis" x="${x(i)}" y="${h - 4}" text-anchor="${k === 0 ? 'start' : k === nRot - 1 ? 'end' : 'middle'}">${esc(rotuloTempo(pontos[i].t, periodo))}</text>`; }).join('');
  const gid = 'g' + Math.random().toString(36).slice(2, 8);
  el.innerHTML = `<svg viewBox="0 0 ${w} ${h}" style="height:${h}px" role="img" aria-label="Gráfico de linha"><defs><linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${cor}" stop-opacity=".22"/><stop offset="1" stop-color="${cor}" stop-opacity="0"/></linearGradient></defs>
    <g class="chart-grid">${grade}</g>${eixoX}<path d="${d} L${x(dados.length - 1)},${h - pad.b} L${x(0)},${h - pad.b} Z" fill="url(#${gid})"/>
    <path class="chart-line" d="${d}" stroke="${cor}" style="filter:drop-shadow(0 0 6px ${cor})"/><line class="chart-cross" y1="${pad.t}" y2="${h - pad.b}"/><circle r="4" fill="${cor}" opacity="0"/></svg><div class="chart-tip"></div>`;
  const linha = $('.chart-line', el);
  if (!reduce) { const L = linha.getTotalLength(); linha.style.strokeDasharray = L; linha.style.strokeDashoffset = L; requestAnimationFrame(() => { linha.style.transition = 'stroke-dashoffset 1.4s cubic-bezier(.22,1,.36,1)'; linha.style.strokeDashoffset = 0; }); }
  const svg = $('svg', el), cruz = $('.chart-cross', el), ponto = $('circle', el), dica = $('.chart-tip', el);
  svg.addEventListener('mousemove', (e) => {
    const r = svg.getBoundingClientRect(), px = ((e.clientX - r.left) / r.width) * w;
    const i = Math.max(0, Math.min(dados.length - 1, Math.round(((px - pad.l) / (w - pad.l - pad.r)) * (dados.length - 1))));
    cruz.setAttribute('x1', x(i)); cruz.setAttribute('x2', x(i)); cruz.style.opacity = 1;
    ponto.setAttribute('cx', x(i)); ponto.setAttribute('cy', y(dados[i])); ponto.setAttribute('opacity', 1);
    const ch = (dados[i] / dados[0] - 1) * 100;
    dica.style.opacity = 1; dica.style.left = (x(i) / w) * 100 + '%'; dica.style.top = (y(dados[i]) / h) * 100 + '%';
    dica.innerHTML = `${esc(rotuloTempo(pontos[i].t, periodo))} · ${fmt(dados[i], dec)} <span class="${classe(ch)}">${ch >= 0 ? '+' : ''}${fmt(ch)}%</span>`;
  });
  svg.addEventListener('mouseleave', () => { cruz.style.opacity = 0; ponto.setAttribute('opacity', 0); dica.style.opacity = 0; });
}

/* ---------------------------------------------------------------------------
   Mercado: KPIs, fita, gráfico, watchlist
--------------------------------------------------------------------------- */
function kpi(id, valor, delta, meta) {
  const el = $('#' + id); if (!el) return;
  $('.value', el).textContent = valor;
  const d = $('.delta', el); d.className = 'delta ' + (delta?.cls || 'flat-t'); d.textContent = delta?.txt || '';
  if (meta !== undefined && $('.meta', el)) $('.meta', el).textContent = meta;
}

async function carregarMercado() {
  try {
    const { panorama, indicadores } = await api('/api/mercado');
    estado.panorama = panorama || {}; estado.indicadores = indicadores || {};
    const ibov = estado.panorama['Ibovespa'] || {}, usd = estado.panorama['Dólar (R$)'] || {};
    kpi('kpi-ibov', ibov.preco != null ? fmt(ibov.preco, 0) : '—', ibov.preco != null ? { cls: classe(ibov.variacao_dia_pct), txt: `${sinal(ibov.variacao_dia_pct)} ${fmt(Math.abs(ibov.variacao_dia_pct ?? 0))}% hoje` } : { txt: 'indisponível' });
    const ptax = indicadores?.dolar_ptax;
    kpi('kpi-usd', usd.preco != null ? 'R$ ' + fmt(usd.preco, 4) : ptax?.valor ? 'R$ ' + fmt(ptax.valor, 4) : '—',
      usd.variacao_dia_pct != null ? { cls: classe(usd.variacao_dia_pct), txt: `${sinal(usd.variacao_dia_pct)} ${fmt(Math.abs(usd.variacao_dia_pct))}% hoje${ptax?.valor ? ' · PTAX ' + fmt(ptax.valor, 4) : ''}` } : { txt: ptax?.valor ? `PTAX · ${ptax.data}` : 'indisponível' });
    const selic = indicadores?.selic_meta_aa, cdi = indicadores?.cdi_aa, ipca = indicadores?.ipca_12m;
    kpi('kpi-selic', selic?.valor != null ? fmt(selic.valor) + '%' : '—', { txt: cdi?.valor != null ? `CDI ${fmt(cdi.valor)}% a.a.` : 'CDI indisponível' }, selic?.data ? `BCB · SGS 432 · ${selic.data}` : '');
    kpi('kpi-ipca', ipca?.valor != null ? fmt(ipca.valor) + '%' : '—', { cls: ipca?.valor > 4.5 ? 'down-t' : 'up-t', txt: ipca?.valor != null ? (ipca.valor > 4.5 ? 'acima do teto da meta (4,5%)' : 'dentro da meta (3% ± 1,5)') : 'indisponível' }, ipca?.data ? `BCB · SGS 13522 · ${ipca.data}` : '');
    if (cdi?.valor && !$('#sim-taxa').dataset.editado) $('#sim-taxa').value = cdi.valor;
    $('#sim-mini-rate').textContent = cdi?.valor ? `CDI ${fmt(cdi.valor)}%` : '';
    preencherFita(); simularMini();
  } catch (e) {
    ['kpi-ibov', 'kpi-usd', 'kpi-selic', 'kpi-ipca'].forEach((id) => kpi(id, '—', { cls: 'down-t', txt: 'falha ao carregar' }));
    toast('Dados de mercado indisponíveis: ' + e.message, 'err');
  }
  // sparklines (1 mês)
  for (const [id, t] of [['kpi-ibov', 'IBOV'], ['kpi-usd', 'DOLAR']]) {
    api(`/api/mercado/historico/${t}?periodo=1mo`).then((h) => { if (h.pontos) { const v = h.pontos.map((p) => p.v); sparkline($(`#${id} .spark`), v, v.at(-1) >= v[0] ? css('--qt-up') : css('--qt-down')); } }).catch(() => {});
  }
}

async function carregarGrafico() {
  const el = $('#main-chart');
  try {
    const h = await api(`/api/mercado/historico/IBOV?periodo=${estado.periodo}`);
    if (h.erro) throw new Error(h.erro);
    graficoLinha(el, h.pontos, estado.periodo);
    const v = h.variacao_pct; $('#chart-var').innerHTML = v != null ? `<span class="${classe(v)}">${v >= 0 ? '+' : ''}${fmt(v)}% no período</span>` : '';
  } catch (e) { el.innerHTML = `<div class="chart-empty">histórico indisponível · ${esc(e.message)}</div>`; $('#chart-var').textContent = ''; }
}
$$('#chart-range button').forEach((b) => b.addEventListener('click', () => {
  $$('#chart-range button').forEach((x) => x.classList.toggle('active', x === b)); estado.periodo = b.dataset.p; carregarGrafico();
}));

function preencherFita() {
  const itens = [];
  for (const [nome, d] of Object.entries(estado.panorama)) if (d.preco != null) itens.push([nome.replace(/ \(.*\)/, ''), d.preco, d.variacao_dia_pct, nome]);
  for (const c of estado.cotacoes) if (c.preco != null) itens.push([c.entrada, c.preco, c.variacao_dia_pct, c.ticker]);
  if (!itens.length) { $('#tape .tape-track').innerHTML = '<div class="tape-item"><span class="px">aguardando cotações…</span></div>'; return; }
  const html = itens.map(([t, p, v, id]) => `<div class="tape-item"><b>${esc(t)}</b><span class="px">${fmt(p, casas(p, id))}</span><span class="${classe(v)}">${sinal(v)} ${fmt(Math.abs(v ?? 0))}%</span></div>`).join('');
  $('#tape .tape-track').innerHTML = html + html;
}

async function carregarWatchlist() {
  $('#count-watch').textContent = estado.watchlist.length;
  if (!estado.watchlist.length) { estado.cotacoes = []; renderWatchlist(); preencherFita(); return; }
  try {
    const { cotacoes } = await api('/api/mercado/cotacoes?tickers=' + encodeURIComponent(estado.watchlist.join(',')));
    estado.cotacoes = cotacoes;
  } catch (e) { estado.cotacoes = estado.watchlist.map((t) => ({ entrada: t, erro: e.message })); }
  renderWatchlist(); preencherFita();
}

function linhaAtivo(c, completa) {
  const ok = c.preco != null;
  const nome = c.ticker || c.entrada;
  const moeda = c.moeda === 'USD' ? 'US$ ' : c.ticker?.startsWith('^') ? '' : 'R$ ';
  const cel = (v) => (v == null ? '<td class="num flat-t">—</td>' : `<td class="num ${classe(v)}">${v > 0 ? '+' : ''}${fmt(v)}%</td>`);
  return `<tr><td><div class="asset"><span class="logo">${esc(c.entrada.replace(/[^A-Z0-9]/g, '').slice(0, 2) || '··')}</span><div>${esc(c.entrada)}<small>${esc(ok ? nome : c.erro || 'indisponível')}</small></div></div></td>
    <td class="num">${ok ? moeda + fmt(c.preco, casas(c.preco, nome)) : '—'}</td>${cel(c.variacao_dia_pct)}${cel(c.variacao_mes_pct)}${cel(c.variacao_12m_pct)}
    ${completa ? `<td class="num flat-t">${ok ? fmt(c.minima_periodo, casas(c.preco, nome)) + ' – ' + fmt(c.maxima_periodo, casas(c.preco, nome)) : '—'}</td>` : ''}
    <td class="num"><span class="row-action" style="display:inline-flex;gap:4px"><button class="btn ghost sm icon" data-ask="Quais as notícias mais recentes sobre ${esc(c.entrada)} e o que significam para o investidor?" title="Perguntar à redação"><i data-lucide="message-square-text"></i></button>${completa ? `<button class="btn ghost sm icon danger" data-remove="${esc(c.entrada)}" title="Remover"><i data-lucide="x"></i></button>` : ''}</span></td></tr>`;
}

function renderWatchlist() {
  const cab = (completa) => `<thead><tr><th>Ativo</th><th class="num">Preço</th><th class="num">Dia</th><th class="num">Mês</th><th class="num">12 meses</th>${completa ? '<th class="num">Mín – máx 12m</th>' : ''}<th></th></tr></thead>`;
  const vazio = (n) => `<tbody><tr><td colspan="${n}" class="empty">Watchlist vazia. Adicione um ticker.</td></tr></tbody>`;
  $('#watch-mini').innerHTML = cab(false) + (estado.cotacoes.length ? `<tbody>${estado.cotacoes.slice(0, 8).map((c) => linhaAtivo(c, false)).join('')}</tbody>` : vazio(6));
  $('#watch-full').innerHTML = cab(true) + (estado.cotacoes.length ? `<tbody>${estado.cotacoes.map((c) => linhaAtivo(c, true)).join('')}</tbody>` : vazio(7));
  icones();
}

function adicionarTicker(valor) {
  const t = valor.trim().toUpperCase().replace(/\s+/g, '');
  if (!t) return;
  if (!/^[\^A-Z0-9.=\-&]{2,15}$/.test(t)) { toast('Ticker inválido: ' + valor, 'err'); return; }
  if (estado.watchlist.includes(t)) { toast(t + ' já está na watchlist'); return; }
  if (estado.watchlist.length >= 20) { toast('Limite de 20 ativos na watchlist', 'err'); return; }
  estado.watchlist.push(t); armazenamento.gravar('qt-watchlist', estado.watchlist);
  toast(t + ' adicionado à watchlist'); carregarWatchlist();
}
$('#search-form').addEventListener('submit', (e) => { e.preventDefault(); adicionarTicker($('#search').value); $('#search').value = ''; });
$('#watch-form').addEventListener('submit', (e) => { e.preventDefault(); adicionarTicker($('#watch-input').value); $('#watch-input').value = ''; });
document.addEventListener('click', (e) => {
  const r = e.target.closest('[data-remove]'); if (!r) return;
  estado.watchlist = estado.watchlist.filter((t) => t !== r.dataset.remove); armazenamento.gravar('qt-watchlist', estado.watchlist);
  estado.cotacoes = estado.cotacoes.filter((c) => c.entrada !== r.dataset.remove); renderWatchlist(); preencherFita();
  $('#count-watch').textContent = estado.watchlist.length;
});
$('#refresh').addEventListener('click', async () => {
  const b = $('#refresh'); b.disabled = true;
  await Promise.all([carregarMercado(), carregarWatchlist(), carregarGrafico()]);
  b.disabled = false; toast('Dados de mercado atualizados');
});

/* ---------------------------------------------------------------------------
   Simulador de renda fixa (cálculo na API)
--------------------------------------------------------------------------- */
async function simular(valor, taxa, meses, isento) {
  return api('/api/simulacao/renda-fixa', { method: 'POST', body: JSON.stringify({ valor, taxa_anual_pct: taxa, meses, isento_ir: isento }) });
}
let tMini;
function simularMini() {
  clearTimeout(tMini);
  tMini = setTimeout(async () => {
    const meses = +$('#sim-mini-months').value, taxa = estado.indicadores?.cdi_aa?.valor;
    $('#sim-mini-desc').textContent = `R$ 10.000 · ${meses} ${meses === 1 ? 'mês' : 'meses'} · 100% do CDI`;
    if (!taxa) { $('#sim-mini-out').textContent = '—'; $('#sim-mini-meta').textContent = 'CDI indisponível'; return; }
    try {
      const r = await simular(10000, taxa, meses, false);
      $('#sim-mini-out').textContent = 'R$ ' + fmt(r.valor_liquido);
      $('#sim-mini-meta').textContent = `IR ${fmt(r.aliquota_ir_pct, 1)}% · líquido +${fmt(r.rentabilidade_liquida_pct)}%`;
    } catch (e) { $('#sim-mini-meta').textContent = e.message; }
  }, 150);
}
$('#sim-mini-months').addEventListener('input', simularMini);

let tFull;
function simularCompleto() {
  clearTimeout(tFull);
  tFull = setTimeout(async () => {
    const valor = +$('#sim-valor').value, taxa = +$('#sim-taxa').value, meses = +$('#sim-meses').value;
    const isento = $('#sim-isento').getAttribute('aria-checked') === 'true';
    $('#sim-meses-out').textContent = `${meses} ${meses === 1 ? 'mês' : 'meses'}`;
    try {
      const r = await simular(valor, taxa, meses, isento);
      $('#sim-liquido').textContent = 'R$ ' + fmt(r.valor_liquido);
      $('#sim-rent').innerHTML = `<span class="up-t">+${fmt(r.rentabilidade_liquida_pct)}% líquido</span> <span class="flat-t">em ${meses} ${meses === 1 ? 'mês' : 'meses'}</span>`;
      const tot = r.valor_bruto; const [i1, i2, i3] = $$('#sim-bar i');
      i1.style.width = (r.valor_investido / tot) * 100 + '%'; i2.style.width = ((r.rendimento_bruto - r.imposto_renda) / tot) * 100 + '%'; i3.style.width = (r.imposto_renda / tot) * 100 + '%';
      $('#sim-stats').innerHTML = [['Valor investido', 'R$ ' + fmt(r.valor_investido)], ['Valor bruto', 'R$ ' + fmt(r.valor_bruto)], ['Rendimento bruto', 'R$ ' + fmt(r.rendimento_bruto)],
        ['Alíquota de IR', isento ? 'isento' : fmt(r.aliquota_ir_pct, 1) + '%'], ['Imposto de renda', 'R$ ' + fmt(r.imposto_renda)], ['Valor líquido', 'R$ ' + fmt(r.valor_liquido)]]
        .map(([k, v]) => `<div><span>${k}</span><b>${v}</b></div>`).join('');
    } catch (e) { $('#sim-liquido').textContent = '—'; $('#sim-rent').innerHTML = `<span class="down-t">${esc(e.message)}</span>`; }
  }, 200);
}
['#sim-valor', '#sim-taxa', '#sim-meses'].forEach((s) => $(s).addEventListener('input', simularCompleto));
$('#sim-taxa').addEventListener('input', () => ($('#sim-taxa').dataset.editado = '1'));
$('#sim-usar-cdi').addEventListener('click', () => { const c = estado.indicadores?.cdi_aa?.valor; if (c) { $('#sim-taxa').value = c; delete $('#sim-taxa').dataset.editado; simularCompleto(); } else toast('CDI indisponível', 'err'); });
const alternar = (el) => { el.setAttribute('aria-checked', el.getAttribute('aria-checked') === 'true' ? 'false' : 'true'); simularCompleto(); };
$('#sim-isento').addEventListener('click', (e) => alternar(e.currentTarget));
$('#sim-isento').addEventListener('keydown', (e) => { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); alternar(e.currentTarget); } });

/* ---------------------------------------------------------------------------
   Matérias
--------------------------------------------------------------------------- */
const quando = (iso) => new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
async function carregarMaterias() {
  try { estado.materias = (await api('/api/materias')).materias; }
  catch (e) { estado.materias = []; toast('Falha ao listar matérias: ' + e.message, 'err'); }
  $('#count-materias').textContent = estado.materias.length;
  const vazio = '<div class="empty">Nenhuma matéria ainda. Faça uma pergunta no console.</div>';
  $('#news-latest').innerHTML = estado.materias.length ? estado.materias.slice(0, 4).map((m) => `<button class="news-item" data-materia="${esc(m.versao)}/${esc(m.arquivo)}"><span class="badge cyan" style="height:18px;font-size:9px;margin-bottom:4px">${esc(m.versao)}</span><b>${esc(m.titulo)}</b><span class="t-label" style="font-size:9px">${quando(m.modificado_em)}</span></button>`).join('') : vazio;
  $('#mat-list').innerHTML = estado.materias.length ? estado.materias.map((m) => { const c = `${m.versao}/${m.arquivo}`;
    return `<button class="mat-item ${c === estado.materiaAtual ? 'active' : ''}" data-materia="${esc(c)}"><b>${esc(m.titulo)}</b><span class="t-label">${esc(m.versao)} · ${quando(m.modificado_em)}</span></button>`; }).join('') : vazio;
}
async function abrirMateria(caminho) {
  estado.materiaAtual = caminho;
  navegar('materias');
  $$('.mat-item').forEach((m) => m.classList.toggle('active', m.dataset.materia === caminho));
  const leitor = $('#mat-reader'); leitor.innerHTML = '<div class="skeleton" style="width:70%;height:22px"></div><div class="skeleton"></div><div class="skeleton" style="width:85%"></div>';
  try {
    const m = await api('/api/materias/' + caminho);
    leitor.innerHTML = `<div class="msg-actions" style="margin:0 0 16px"><span class="badge cyan">${esc(m.versao)}</span><span class="badge neutral">${esc(m.arquivo)}</span><button class="btn ghost sm" data-copy><i data-lucide="copy"></i><span>Copiar markdown</span></button></div>${renderMarkdown(m.markdown)}`;
    leitor.dataset.markdown = m.markdown; icones();
  } catch (e) { leitor.innerHTML = `<div class="alert err"><i data-lucide="octagon-x"></i><div><b>Erro</b>${esc(e.message)}</div></div>`; icones(); }
}
document.addEventListener('click', (e) => {
  const m = e.target.closest('[data-materia]'); if (m) abrirMateria(m.dataset.materia);
  const c = e.target.closest('[data-copy]');
  if (c) { const md = c.closest('[data-markdown]')?.dataset.markdown; if (md) navigator.clipboard?.writeText(md).then(() => toast('Markdown copiado'), () => toast('Não foi possível copiar', 'err')); }
});
$('#reload-materias').addEventListener('click', carregarMaterias);

/* ---------------------------------------------------------------------------
   Console da redação (perguntas + telemetria do pipeline via SSE)
--------------------------------------------------------------------------- */
const SUGESTOES = [
  'Como a decisão mais recente do Copom afeta a renda fixa e a bolsa?',
  'Por que a Petrobras (PETR4) oscilou hoje?',
  'Fundos imobiliários (FIIs) ainda valem a pena com a Selic atual?',
  'Como o dólar e os juros dos EUA afetam o Ibovespa?',
];

function initSeg() {
  const seg = $('#seg-versoes');
  seg.innerHTML = '<span class="thumb"></span>' + estado.versoes.map((v) => `<button type="button" data-v="${esc(v.chave)}" title="${esc(v.rotulo)}">${esc(v.chave)}</button>`).join('');
  const mover = (b) => {
    const th = $('.thumb', seg); th.style.left = b.offsetLeft + 'px'; th.style.width = b.offsetWidth + 'px';
    $$('button', seg).forEach((x) => x.classList.toggle('active', x === b));
    estado.versao = b.dataset.v; armazenamento.gravar('qt-versao', estado.versao);
    const v = estado.versoes.find((x) => x.chave === estado.versao);
    $('#versao-desc').innerHTML = v ? `<b style="color:var(--qt-text);font-weight:500">${esc(v.rotulo)}</b> · ${esc(v.pipeline)}` : '';
  };
  $$('button', seg).forEach((b) => b.addEventListener('click', () => { if (!estado.executando) mover(b); }));
  requestAnimationFrame(() => mover($(`button[data-v="${estado.versao}"]`, seg) || $('button', seg)));
}

function boasVindas() {
  $('#chat-log').innerHTML = `<div class="msg ai"><div class="who">AI</div><div class="body"><div class="meta">Redação · ${esc(estado.versao)}</div>Pergunte sobre um ativo, indicador ou notícia. Os agentes pesquisam, apuram, checam os fatos e explicam com dados reais de mercado.</div></div>
    <div class="suggestions" id="sugg">${SUGESTOES.map((s) => `<button type="button" class="suggestion" data-ask="${esc(s)}">${esc(s)}</button>`).join('')}</div>`;
}
$('#chat-clear').addEventListener('click', () => { if (!estado.executando) boasVindas(); });

function addMsg(html, tipo) {
  const log = $('#chat-log'); $('#sugg')?.remove();
  log.insertAdjacentHTML('beforeend', html); icones();
  log.scrollTop = log.scrollHeight;
  return log.lastElementChild;
}

let cronometro;
// Pergunta em andamento: { controle: AbortController do envio, id, fonte: EventSource, encerrar() }
let atual = null;

function travar(sim) {
  estado.executando = sim;
  $('#chat-in').disabled = sim;
  const b = $('#chat-send');
  b.disabled = false;
  b.classList.toggle('primary', !sim); b.classList.toggle('danger', sim);
  b.title = sim ? 'Cancelar pesquisa (Esc)' : 'Enviar'; b.setAttribute('aria-label', b.title);
  b.innerHTML = sim ? '<i data-lucide="square"></i>' : '<i data-lucide="corner-down-left"></i>'; icones();
  $$('#seg-versoes button').forEach((x) => (x.disabled = sim));
  clearInterval(cronometro);
  if (sim) { const t0 = Date.now(); cronometro = setInterval(() => ($('#chat-timer').textContent = `executando · ${Math.round((Date.now() - t0) / 1000)}s`), 1000); }
  else $('#chat-timer').textContent = '';
}

function avisoCancelado(texto) {
  addMsg(`<div class="msg err"><div class="who">■</div><div class="body"><div class="alert warn"><i data-lucide="circle-slash"></i><div><b>Cancelado</b>${esc(texto)}</div></div></div></div>`);
}

async function cancelarPergunta() {
  if (!atual) return;
  if (!atual.id) {  // ainda enviando: aborta a requisição
    atual.controle.abort();
    return;
  }
  const b = $('#chat-send'); b.disabled = true; b.innerHTML = '<span class="spinner"></span>';
  $$('[data-cancel]').forEach((x) => (x.disabled = true));
  try { await api(`/api/perguntas/${atual.id}/cancelar`, { method: 'POST' }); }
  catch (e) { if (!/terminou/.test(e.message)) toast('Não foi possível cancelar: ' + e.message, 'err'); b.disabled = false; }
  // o evento "cancelado" chega pelo SSE e encerra a pergunta na interface
}

async function perguntar(tema) {
  tema = (tema || '').trim();
  if (!tema || estado.executando) { if (estado.executando) toast('Aguarde a pergunta atual terminar ou cancele-a'); return; }
  if (tema.length < 3) { toast('Pergunta muito curta', 'err'); return; }
  addMsg(`<div class="msg user"><div class="who">EU</div><div class="body"><div class="meta">você · ${esc(estado.versao)}</div>${esc(tema)}</div></div>`);
  atual = { controle: new AbortController(), id: null };
  travar(true);
  let tarefa;
  try { tarefa = await api('/api/perguntas', { method: 'POST', body: JSON.stringify({ tema, versao: estado.versao }), signal: atual.controle.signal }); }
  catch (e) {
    if (e.name === 'AbortError') avisoCancelado('Envio cancelado antes de a pesquisa começar.');
    else erroNoChat(e.message);
    atual = null; travar(false); return;
  }
  atual.id = tarefa.id;

  const card = addMsg(`<div class="hud pipeline-card"><div class="hud-title"><i data-lucide="cpu"></i>Telemetria · ${esc(tarefa.versao)}<span class="end"><span class="mono" style="font-size:10px" data-elapsed></span><button type="button" class="btn ghost sm danger" data-cancel title="Cancelar pesquisa"><i data-lucide="square"></i><span>Cancelar</span></button></span></div>
    <div data-steps>${tarefa.etapas.map((e) => `<div class="step" data-step="${esc(e.id)}"><span class="node"><i data-lucide="circle"></i></span><span class="label">${esc(e.rotulo)}</span><span class="time">—</span></div>`).join('')}</div>
    <div class="scanbar" data-scan></div></div>`);
  const passo = (id) => $(`[data-step="${CSS.escape(id)}"]`, card);
  const marcar = (id, status, extra) => {
    const s = passo(id); if (!s) return;
    s.classList.remove('run', 'done', 'err', 'cancel'); s.classList.add(status);
    $('.node', s).innerHTML = `<i data-lucide="${{ run: 'loader', done: 'check', err: 'x', cancel: 'minus' }[status]}"></i>`;
    if (extra != null) $('.time', s).textContent = extra;
    icones();
  };

  const fonte = new EventSource(`/api/perguntas/${tarefa.id}/eventos`);
  let finalizado = false;
  const encerrar = (duracao) => {
    finalizado = true; fonte.close();
    $('[data-scan]', card)?.remove(); $('[data-cancel]', card)?.remove();
    if (duracao != null) $('[data-elapsed]', card).textContent = `${duracao}s`;
    atual = null; travar(false); carregarMaterias(); atualizarStatus();
  };
  fonte.onmessage = (msg) => {
    const ev = JSON.parse(msg.data);
    if (ev.tipo === 'etapa') marcar(ev.id, ev.status === 'iniciada' ? 'run' : ev.status === 'concluida' ? 'done' : 'err', ev.status === 'iniciada' ? '…' : ev.duracao_s != null ? ev.duracao_s + 's' : null);
    else if (ev.tipo === 'tentativa') { const l = $('.label', passo(ev.id) || document.createElement('div')); if (l) { $('small', l)?.remove(); l.insertAdjacentHTML('beforeend', `<small>tentativa ${ev.atual}/${ev.maximo ?? '?'}</small>`); } }
    else if (ev.tipo === 'conteudo') {
      const m = addMsg(`<div class="msg ai"><div class="who">AI</div><div class="body"><div class="meta">${esc(tarefa.versao)} · matéria</div><div class="md">${renderMarkdown(ev.markdown)}</div>
        <div class="msg-actions"><button class="btn ghost sm" data-copy><i data-lucide="copy"></i><span>Copiar</span></button><button class="btn ghost sm" data-nav="materias"><i data-lucide="newspaper"></i><span>Ver em matérias</span></button></div></div></div>`);
      m.dataset.markdown = ev.markdown;
    } else if (ev.tipo === 'erro') {
      $$('.step.run', card).forEach((s) => marcar(s.dataset.step, 'err'));
      erroNoChat(ev.mensagem);
    } else if (ev.tipo === 'cancelado') {
      // as etapas em andamento e as que faltavam ficam marcadas como canceladas
      $$('.step:not(.done):not(.err)', card).forEach((s) => marcar(s.dataset.step, 'cancel', s.classList.contains('run') ? 'cancelada' : null));
      avisoCancelado('Pesquisa interrompida. Nenhuma matéria foi salva.');
      encerrar(null);
    } else if (ev.tipo === 'fim') {
      encerrar(ev.duracao_s);
    }
  };
  atual.fonte = fonte;
  fonte.onerror = () => {
    if (finalizado) return;
    fonte.close(); atual = null; travar(false);
    erroNoChat('A conexão com o servidor caiu durante a execução. Verifique se a API ainda está rodando.');
  };
}
document.addEventListener('click', (e) => { if (e.target.closest('[data-cancel]')) cancelarPergunta(); });

function erroNoChat(mensagem) {
  addMsg(`<div class="msg err"><div class="who">!</div><div class="body"><div class="alert err"><i data-lucide="octagon-x"></i><div><b>Falha na execução</b>${esc(mensagem)}</div></div></div></div>`);
}

$('#chat-form').addEventListener('submit', (e) => {
  e.preventDefault();
  if (estado.executando) { cancelarPergunta(); return; }  // durante a execução, o botão de enviar vira "cancelar"
  const v = $('#chat-in').value; $('#chat-in').value = ''; autoAltura(); perguntar(v);
});
$('#chat-in').addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); $('#chat-form').requestSubmit(); } });
function autoAltura() { const t = $('#chat-in'); t.style.height = 'auto'; t.style.height = Math.min(140, t.scrollHeight) + 'px'; }
$('#chat-in').addEventListener('input', autoAltura);

/* ---------------------------------------------------------------------------
   Status do sistema
--------------------------------------------------------------------------- */
async function atualizarStatus() {
  try {
    const s = await api('/api/status');
    $('#sys-key').innerHTML = s.api_key_configurada ? '<span class="up-t">configurada</span>' : '<span class="down-t">ausente</span>';
    $('#sys-model').textContent = s.modelo; $('#sys-model').title = s.modelo;
    const cota = s.cota || [], esgotados = cota.filter((c) => !c.disponivel);
    const q = $('#sys-quota');
    if (!esgotados.length) { q.innerHTML = '<span class="up-t">disponível</span>'; q.title = cota.map((c) => c.modelo).join(', '); }
    else if (esgotados.length < cota.length) { q.innerHTML = `<span style="color:var(--qt-warn)">reserva em uso</span>`; q.title = esgotados.map((c) => `${c.modelo}: libera em ~${Math.max(1, Math.round(c.libera_em_s / 60))} min`).join('\n'); }
    else { const min = Math.max(1, Math.round(Math.min(...cota.map((c) => c.libera_em_s)) / 60)); q.innerHTML = `<span class="down-t">esgotada · ~${min} min</span>`; q.title = 'Todos os modelos sem cota diária'; }
    $('#sys-search').textContent = s.busca_backend;
    $('#sys-running').textContent = s.tarefas_em_andamento;
    $('#avatar').classList.toggle('off', !s.api_key_configurada);
    if (!s.api_key_configurada && !$('#alerta-chave')) {
      addMsg(`<div class="alert warn" id="alerta-chave"><i data-lucide="key-round"></i><div><b>GROQ_API_KEY ausente</b>Crie o arquivo <span class="mono">.env</span> na raiz (veja <span class="mono">.env.example</span>) e reinicie o servidor. O painel de mercado funciona sem a chave.</div></div>`);
    }
  } catch { $('#sys-key').innerHTML = '<span class="down-t">API offline</span>'; $('#avatar').classList.add('off'); }
}

/* ---------------------------------------------------------------------------
   Inicialização
--------------------------------------------------------------------------- */
async function iniciar() {
  icones(); relogio(); setInterval(relogio, 30000);
  try {
    const v = await api('/api/versoes');
    estado.versoes = v.versoes;
    if (!estado.versoes.some((x) => x.chave === estado.versao)) estado.versao = v.padrao;
  } catch { estado.versoes = [{ chave: 'V5', rotulo: 'V5 · Investidor', pipeline: '' }]; }
  initSeg(); boasVindas();
  navegar(location.hash.slice(1) || 'painel');
  atualizarStatus();
  carregarMercado(); carregarWatchlist(); carregarGrafico(); carregarMaterias(); simularCompleto();
  setInterval(() => { if (!document.hidden) { carregarMercado(); carregarWatchlist(); } }, 5 * 60 * 1000);
  setInterval(() => { if (!document.hidden) atualizarStatus(); }, 60 * 1000);
  let tRes; addEventListener('resize', () => { clearTimeout(tRes); tRes = setTimeout(carregarGrafico, 250); });
}
iniciar();
