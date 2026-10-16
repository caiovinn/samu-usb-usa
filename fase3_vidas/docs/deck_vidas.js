const fs = require("fs");
const path = require("path");
const pptx = require("pptxgenjs");

/* Deck da fase 3 — "onde colocar as ambulancias para salvar mais vidas":
 * a hipotese da fase 3, passo a passo, para quem nunca viu as formulas.
 *
 *     uv run python -m fase3_vidas.docs.deck_dados      # numeros derivados
 *     uv run python -m fase3_vidas.docs.formulas_gera   # formulas em PNG
 *     node fase3_vidas/docs/deck_vidas.js
 *
 * Mesma familia visual de fase2_sao_paulo/docs/deck_despacho.js. Todo numero
 * de resultado vem de dados/fase3/*.json (v1..v7 e deck_vidas.json). A fase 2
 * entra so onde explica por que o modelo de Huff nao serve ao projeto
 * (dados/fase2/sp_q_sens.json e os exemplos de brinquedo de deck_despacho.js).
 */

const RAIZ = path.join(__dirname, "..", "..");
const DADOS = path.join(RAIZ, "dados", "fase3");
const DADOS2 = path.join(RAIZ, "dados", "fase2");
const FIG = path.join(RAIZ, "figs", "fase3") + path.sep;
const FORM3 = path.join(FIG, "formulas") + path.sep;
const FORM2 = path.join(RAIZ, "figs", "fase2", "formulas") + path.sep;
const SAIDA = path.join(__dirname, "apresentacao_vidas_sp.pptx");

const lerJson = (p) => JSON.parse(fs.readFileSync(p, "utf-8"));
const D = lerJson(path.join(DADOS, "deck_vidas.json"));
const CAL = lerJson(path.join(DADOS, "v1_calibracao.json"));
const RE = lerJson(path.join(DADOS, "v2_reavaliacao.json")).configs;
const BU = lerJson(path.join(DADOS, "v3_busca.json"));
const LIM = lerJson(path.join(DADOS, "v4_limite.json")).por_K[0];
const SIM = lerJson(path.join(DADOS, "v5_simulacao.json"));
const ROB = lerJson(path.join(DADOS, "v6_robustez.json"));
const CL = lerJson(path.join(DADOS, "v7_classes.json"));
const QS = lerJson(path.join(DADOS2, "sp_q_sens.json")).tabela;
const DIM3 = lerJson(path.join(FORM3, "dims.json"));

const n = (x, casas = 1) => Number(x).toFixed(casas).replace(".", ",").replace("-", "−");
const pct = (x, casas = 1) => `${n(x, casas)}%`;
const mil = (x) => Math.round(x).toLocaleString("pt-BR");

// ---------------------------------------------------------------- dados
const SOL = BU.solucoes;
const ex = (k) => SOL[k].exato;
const HOJE = RE["hoje"], PM = RE["p-median"];
const REC_NOME = ROB.minimax_arrependimento;                // "vidas lam=0 K=livre G=pm"
const REC = ex(REC_NOME.replace(/^vidas /, ""));
const LV = ex("lam=0 K=livre"), EQ = ex("lam=1 K=livre G=pm");
const KS = BU.Ks.filter((k) => k !== null);
const GANHO = LV.vidas - HOJE.vidas;
const fracK = (k) => (ex(`lam=0 K=${k}`).vidas - HOJE.vidas) / GANHO;
const POR_MIL = D.pcr_ano / 1000;                           // vidas/ano por 1 sobrevivente /1.000 PCR
const ANO = (REC.vidas - HOJE.vidas) * POR_MIL, ANO_PM = (REC.vidas - PM.vidas) * POR_MIL;
const GINI = Object.entries(RE).filter(([k, v]) => k.startsWith("fase2") && v.movidas > 60);
const MELHOR_GINI = Math.max(...GINI.map(([, v]) => v.vidas));
const SIMC = SIM.medias.filter((m) => m.servico === "central");
const simDe = (c) => SIMC.find((m) => m.config === c);
const DIF_SIM = Math.max(...SIMC.map((m) => m.an_vidas_mean - m.sim_vidas_mean));
const RC = Object.fromEntries(ROB.por_config.map((d) => [d.config, d]));
const CLS = CL.solucoes["classes chamadas K=livre"];
const QSr = (modelo, config) => QS.find((r) => r.modelo === modelo && r.config === config);
const HUFF_HOJE = QSr("huff b=4.5", "atual"), DESP_HOJE = QSr("desp SIA central", "atual");
const DESP_GINI = QSr("desp SIA central", "huff lam=0"), DESP_PM = QSr("desp SIA central", "p-median");
const KM = (k) => mil(SOL[k].km);
const TAU = n(D.tau_guarda, 0);

// nomes curtos e cor fixa por entidade em todos os graficos
function rotulo(k) {
  const m = {
    "hoje": "rede de hoje", "p-median": "p-median",
    "fase2 lam=0.1": "fase 2, λ=0,1", "fase2 lam=1": "fase 2, λ=1",
    "fase2b central lam=0.1": "fase 2b, λ=0,1", "fase2b central lam=1": "fase 2b, λ=1",
    "fase2b central_r25 lam=0.1": "fase 2b c/ restrição, λ=0,1",
    "fase2b central_r25 lam=1": "fase 2b c/ restrição, λ=1",
  };
  if (m[k]) return m[k];
  const s = k.replace(/^vidas /, "");
  const lam = (s.match(/lam=([\d.]+)/) || [])[1], K = (s.match(/K=(\w+)/) || [])[1];
  return `vidas, λ=${n(Number(lam), lam.includes(".") ? 1 : 0)}, ` +
    (K === "livre" ? "sem limite" : `K=${K}`) + (s.includes("G=pm") ? " · piso p-median" : "");
}
const NAVY = "16263F", TEAL = "0F3D5C", CREAM = "F7F5F0", CARD = "EAF1F7";
const INK = "0F2B46", INK2 = "4A5568", GOLD = "D9A441";
const BLUE = "2A78D6", ORANGE = "EB6834", GREEN = "2E7D5A", GREY = "8A8F98";
const corDe = (k) => k === "hoje" ? GREY : k === "p-median" ? BLUE :
  k.startsWith("fase2") ? ORANGE : k.startsWith("classes") ? GOLD : GREEN;

const L = {
  ibge: ["IBGE · Censo 2022, setores", "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/"],
  cnes: ["CNES/DATASUS", "https://cnes.datasus.gov.br/"],
  osm: ["OpenStreetMap", "https://www.openstreetmap.org/copyright"],
  sia: ["SIA/SUS · notas técnicas", "http://tabnet.datasus.gov.br/cgi/sia/qadescr.htm"],
  pref23: ["Prefeitura de SP, dez/2023", "https://prefeitura.sp.gov.br/web/saude/w/noticias/359560"],
  huff: ["Huff (1964)", "https://doi.org/10.1177/002224296402800307"],
  daskin: ["Daskin (1983)", "https://doi.org/10.1287/trsc.17.1.48"],
  revelle: ["ReVelle & Hogan (1989)", "https://doi.org/10.1287/trsc.23.3.192"],
  demaio: ["De Maio et al. (2003)", "https://doi.org/10.1067/mem.2003.266"],
  erkut: ["Erkut, Ingolfsson & Erdoğan (2008)", "https://doi.org/10.1002/nav.20267"],
  ru: ["Rockafellar & Uryasev (2000)", "https://doi.org/10.21314/JOR.2000.038"],
  eureca: ["Gräsner et al. (2020), EuReCa TWO", "https://doi.org/10.1016/j.resuscitation.2019.12.042"],
};

// ------------------------------------------------- exemplos de brinquedo
// os mesmos de fase2_sao_paulo/docs/deck_despacho.js (formulas de huff2sfca.py)
const BETA = 4.5, Q_EX = 0.27;
const fH = (t) => Math.exp(-(t * t) / (2 * BETA * BETA));
const huffP = (ts) => { const w = ts.map(fH), s = w.reduce((a, b) => a + b); return w.map((x) => x / s); };
const despP = (ts, q) => {
  const p = ts.map((_, k) => Math.pow(q, k) * (1 - q));
  p[0] += Math.pow(q, ts.length);
  return p;
};
const esp = (p, ts) => p.reduce((a, x, k) => a + x * ts[k], 0);
const CEN = [2, 4], PER = [10, 22, 25];

// ---------------------------------------------------------------- estilo
const doc = new pptx();
doc.layout = "LAYOUT_WIDE";
doc.author = "Grupo MAI5003";
doc.title = "Onde colocar as ambulâncias para salvar mais vidas — fase 3";
const SERIF = "Cambria", SANS = "Calibri";
const M = 0.62;

let _pag = 0, SEC = null;
function secao(t) { doc.addSection({ title: t }); SEC = t; }
function pagina(s, cor) {
  _pag++;
  s.addText(String(_pag), { x: 12.75, y: 7.1, w: 0.45, h: 0.3, isTextBox: true,
    margin: 0, align: "right", fontFace: SANS, fontSize: 9.5, color: cor });
}
function slideClaro(titulo, sobre) {
  const s = doc.addSlide({ sectionTitle: SEC });
  s.background = { color: CREAM };
  if (sobre) s.addText(sobre.toUpperCase(), { x: M, y: 0.42, w: 11, h: 0.26,
    isTextBox: true, margin: 0, fontFace: SANS, fontSize: 10.5, bold: true,
    color: GOLD, charSpacing: 1.4 });
  s.addText(titulo, { x: M, y: sobre ? 0.70 : 0.55, w: 12.1, h: 0.72,
    isTextBox: true, margin: 0, fontFace: SERIF, fontSize: 28, bold: true, color: INK });
  pagina(s, GREY);
  return s;
}
function slideEscuro(cor) {
  const s = doc.addSlide({ sectionTitle: SEC });
  s.background = { color: cor };
  s.addShape(doc.ShapeType.ellipse, { x: 10.2, y: -2.2, w: 5.6, h: 5.6,
    fill: { color: "FFFFFF", transparency: 94 }, line: { color: cor } });
  pagina(s, "9FB0C4");
  return s;
}
function cartao(s, o) {
  s.addShape(doc.ShapeType.roundRect, { x: o.x, y: o.y, w: o.w, h: o.h,
    rectRadius: 0.10, fill: { color: o.fill || CARD }, line: { color: o.fill || CARD } });
}
function bolha(s, t, x, y, cor, d = 0.46) {
  s.addShape(doc.ShapeType.ellipse, { x, y, w: d, h: d, fill: { color: cor }, line: { color: cor } });
  s.addText(String(t), { x, y, w: d, h: d, isTextBox: true, margin: 0, align: "center",
    valign: "middle", fontFace: SANS, fontSize: 13, bold: true, color: "FFFFFF" });
}
function item(s, num, x, y, w, titulo, corpo, cor, hCorpo = 1.0) {
  bolha(s, num, x, y, cor || BLUE);
  s.addText(titulo, { x: x + 0.62, y: y - 0.02, w: w - 0.62, h: 0.3, isTextBox: true,
    margin: 0, valign: "top", fontFace: SANS, fontSize: 14, bold: true, color: INK });
  s.addText(corpo, { x: x + 0.62, y: y + 0.3, w: w - 0.62, h: hCorpo, isTextBox: true,
    margin: 0, valign: "top", fontFace: SANS, fontSize: 12.5, color: INK2, lineSpacing: 16 });
}
function texto(s, t, x, y, w, h, o = {}) {
  s.addText(t, Object.assign({ x, y, w, h, isTextBox: true, margin: 0, valign: "top",
    fontFace: SANS, fontSize: 14, color: INK2, lineSpacing: 19 }, o));
}
function conclusao(s, t, y = 6.4) {
  texto(s, t, M, y, 12.1, 0.6, { fontFace: SERIF, fontSize: 15, italic: true, color: TEAL, lineSpacing: 20 });
}
// numero grande com rotulo embaixo
function destaque(s, x, y, w, num, rot, cor = INK, fill = "FFFFFF") {
  cartao(s, { x, y, w, h: 1.6, fill });
  texto(s, num, x + 0.25, y + 0.12, w - 0.5, 0.65, { fontFace: SERIF, fontSize: 32, bold: true, color: cor, valign: "middle" });
  texto(s, rot, x + 0.25, y + 0.8, w - 0.5, 0.75, { fontSize: 12, lineSpacing: 15 });
}
function fontes(s, refs, proj, cor = GREY) {
  const runs = [{ text: refs.length ? "Fontes: " : "Fonte: ", options: { bold: true, color: cor } }];
  refs.forEach((r, i) => {
    if (i) runs.push({ text: " · ", options: { color: cor } });
    runs.push({ text: r[0], options: { hyperlink: { url: r[1], tooltip: r[1] }, color: cor } });
  });
  if (proj) runs.push({ text: `${refs.length ? "  |  dados do projeto: " : "resultados do projeto, "}${proj}`, options: { color: cor } });
  s.addText(runs, { x: M, y: 7.06, w: 11.95, h: 0.3, isTextBox: true, margin: 0,
    valign: "middle", fontFace: SANS, fontSize: 9 });
}
function seta(s, x, y, w, h) {
  s.addShape(doc.ShapeType.line, { x, y, w, h, line: { color: GREY, width: 1.5, endArrowType: "triangle" } });
}
const DIM2 = { huff_principal: [723, 286], desp_geom: [704, 100] };   // PNGs da fase 2
function formula(s, chave, x, y, h) {
  const fase3 = DIM3[chave];
  const [pw, ph] = fase3 || DIM2[chave];
  s.addImage({ path: (fase3 ? FORM3 : FORM2) + chave + ".png", x, y, w: h * pw / ph, h });
  return h * pw / ph;
}
function figura(s, arq, x, y, w, px) {
  s.addImage({ path: FIG + arq, x, y, w, h: w * px[1] / px[0] });
}
function tabela(s, x, y, w, colW, cab, linhas, o = {}) {
  const fs_ = o.fontSize || 13;
  s.addTable([cab.map((t) => ({ text: t, options: { bold: true, color: "FFFFFF",
      fill: { color: TEAL }, fontSize: fs_, fontFace: SANS, align: "center" } }))]
    .concat(linhas.map((r, i) => r.map((c, j) => ({ text: String(c), options: {
      fontSize: fs_, fontFace: SANS, bold: (o.destaque || []).includes(i) && j === 0,
      color: (o.destaque || []).includes(i) ? INK : INK2, align: j === 0 ? "left" : "center",
      fill: { color: (o.destaque || []).includes(i) ? "FBEAE7" : (i % 2 ? "FFFFFF" : CARD) } } })))),
    { x, y, w, colW, rowH: o.rowH || 0.42, border: { pt: 0, color: CREAM }, valign: "middle" });
}
// grafico de barras de uma serie, uma cor por barra (cor da entidade)
function barras(s, x, y, w, h, rot, val, cores, o = {}) {
  s.addChart(doc.ChartType.bar, [{ name: o.serie || "valor", labels: rot, values: val }], Object.assign({
    x, y, w, h, barDir: o.barDir || "bar", chartColors: cores, barGapWidthPct: 45,
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: o.fmt || "0.0",
    dataLabelFontSize: 11, dataLabelFontFace: SANS, dataLabelColor: INK,
    catAxisLabelFontSize: 11.5, catAxisLabelFontFace: SANS, catAxisLabelColor: INK2,
    valAxisHidden: true, valGridLine: { style: "none" }, catGridLine: { style: "none" },
    catAxisLineShow: false, valAxisMinVal: 0, showLegend: false,
    catAxisOrientation: o.barDir === "col" ? "minMax" : "maxMin",
  }, o.extra || {}));
}

// ======================================================================
secao("Abertura");
// — capa
{
  const s = slideEscuro(NAVY);
  texto(s, "MAI5003 · PROBABILIDADE E ESTATÍSTICA · FASE 3", M, 1.3, 11, 0.3,
    { fontSize: 11, bold: true, color: GOLD, charSpacing: 1.4 });
  texto(s, "Onde colocar as ambulâncias para salvar mais vidas", M, 1.75, 11.7, 1.6,
    { valign: "middle", fontFace: SERIF, fontSize: 40, bold: true, color: "FFFFFF", lineSpacing: 46 });
  texto(s, "A hipótese da fase 3: medir um mapa de bases pela sobrevida a uma parada cardíaca",
    M, 3.55, 11, 0.9, { fontFace: SERIF, fontSize: 19, italic: true, color: "C9D6E4" });
  texto(s, "Realocação de USB e USA em São Paulo · passo a passo, sem pressupor as fórmulas",
    M, 4.55, 11, 0.4, { fontSize: 13, color: "9FB0C4" });
  texto(s, "Grupo MAI5003 · outubro de 2026", M, 6.6, 6, 0.4, { fontSize: 11, color: "8D9EB2" });
  s.addNotes("Esta apresentação conta a fase 3. A pergunta muda de 'o mapa é rápido e justo?' para " +
    "'quantas pessoas o mapa salva?'. A fase 2 aparece só para explicar por que trocamos o modelo de Huff " +
    "pelo modelo de despacho.");
}

// — a pergunta e a hipotese
{
  const s = slideClaro("A pergunta e a hipótese", "o que queremos testar");
  texto(s, "A fase 2 escolhia mapas de bases pelo tempo médio de chegada e pela igualdade de acesso entre bairros (índice de Gini). A fase 3 muda a pergunta: em vez de perguntar se o mapa é rápido e equilibrado, pergunta quantas pessoas ele salva. Para isso usamos a parada cardíaca, a emergência em que se sabe medir quanto cada minuto de atraso custa em vidas.",
    M, 1.55, 12.1, 1.05, { fontSize: 14.5 });
  const H = [
    ["Mirar a sobrevida salva mais vidas", "Um mapa escolhido para maximizar a sobrevida a uma parada cardíaca salva mais pessoas que a rede de hoje, que o p-median clássico e que os mapas guiados pelo Gini nas fases 2 e 2b.", GREEN],
    ["Mudar pouco já rende", "Não é preciso redesenhar a rede inteira: mover só uma parte da frota (K ambulâncias) já entrega boa parte do ganho de um redesenho completo.", BLUE],
    ["A conclusão resiste", "A ordem dos mapas se mantém quando a cidade é simulada chamado a chamado e quando as hipóteses que não conseguimos medir (tempo, trânsito, carga) mudam.", ORANGE],
  ];
  H.forEach((h, i) => {
    const x = M + i * 4.1;
    cartao(s, { x, y: 2.8, w: 3.85, h: 2.75 });
    bolha(s, `H${i + 1}`, x + 0.25, 2.98, h[2], 0.55);
    texto(s, h[0], x + 0.95, 3.0, 2.75, 0.55, { fontSize: 15, bold: true, color: INK, valign: "middle", lineSpacing: 17 });
    texto(s, h[1], x + 0.25, 3.7, 3.4, 1.8, { fontSize: 13, lineSpacing: 17 });
  });
  conclusao(s, "Superar a rede de hoje é fácil, porque ela não foi desenhada por otimização. O teste de verdade é superar o p-median, a solução clássica que põe as bases onde o tempo médio até a ambulância mais próxima é o menor possível.", 5.8);
  s.addNotes("As três hipóteses resumem o que a fase 3 se propôs a testar. O p-median é a referência forte: se o método novo não o superar, o ganho vem só de redesenhar a rede, não do método.");
}

// — roteiro
{
  const s = slideClaro("O roteiro", "roteiro");
  const passos = [
    ["Dois conjuntos", "Os setores censitários, onde a demanda é medida, e os locais candidatos, onde uma ambulância pode ficar."],
    ["Por que não o Huff", "O único pedaço da fase 2 que precisamos: o modelo de escolha usado antes descreve mal o despacho de ambulâncias."],
    ["Quem atende e em quanto tempo", "A regra real do regulador, a ocupação das ambulâncias medida no SUS e os tempos de viagem corrigidos pelo trânsito."],
    ["Como medir vidas", "A curva de sobrevida da parada cardíaca, a média da cidade e a média dos 10% mais mal servidos."],
    ["O problema e como resolver", "O que se decide, o que se maximiza, as restrições e o algoritmo de busca."],
    ["H1 e H2: resultados", "Os mapas existentes medidos em vidas e quanto rende mover só K ambulâncias."],
    ["H3: conferência", "Uma cidade simulada chamado a chamado, 18 cenários de hipóteses e uma contraprova sem a parada cardíaca."],
    ["O que levar", "O veredito da hipótese, o ganho em vidas por ano e as limitações."]];
  passos.forEach((p, i) => {
    const col = i < 4 ? 0 : 1, lin = i % 4;
    item(s, i + 1, M + col * 6.2, 1.65 + lin * 1.2, 5.9, p[0], p[1], i < 4 ? BLUE : ORANGE, 0.8);
  });
  conclusao(s, "Todo número da apresentação sai de um arquivo de resultado do projeto, e todo dado externo traz o link da fonte no rodapé do slide.", 6.5);
}

// — dois conjuntos
{
  const s = slideClaro("Dois conjuntos: onde está a demanda, onde a ambulância pode ficar", "passo 1");
  destaque(s, M, 1.6, 3.85, mil(D.n_setores), "setores censitários (índice i): onde as pessoas moram e onde as paradas cardíacas acontecem", INK);
  destaque(s, M + 4.12, 1.6, 3.85, mil(D.n_cand), "locais candidatos (índice j): estabelecimentos públicos do CNES, os únicos lugares onde uma base pode ficar", GREEN);
  destaque(s, M + 8.24, 1.6, 3.85, String(D.n_usb + D.n_usa), `ambulâncias: ${D.n_usb} USB e ${D.n_usa} USA, hoje distribuídas em ${D.n_locais_hoje} locais`, BLUE);
  cartao(s, { x: M, y: 3.45, w: 5.9, h: 2.5, fill: "FFFFFF" });
  texto(s, "Os dois tipos de ambulância", M + 0.3, 3.6, 5.4, 0.3, { fontSize: 14.5, bold: true, color: INK });
  texto(s, [{ text: "USB", options: { bold: true, color: INK } }, { text: " — Unidade de Suporte Básico: condutor e técnico de enfermagem, com desfibrilador automático (DEA). Atende a maior parte dos chamados.", options: { breakLine: true } },
    { text: "USA", options: { bold: true, color: INK } }, { text: " — Unidade de Suporte Avançado: tem médico a bordo e é reservada para os casos mais graves." }],
    M + 0.3, 4.0, 5.4, 1.9, { fontSize: 13.5, paraSpaceAfter: 8 });
  cartao(s, { x: M + 6.2, y: 3.45, w: 5.9, h: 2.5, fill: "FFF4DC" });
  texto(s, "O que se decide e o que se mede", M + 6.5, 3.6, 5.4, 0.3, { fontSize: 14.5, bold: true, color: INK });
  texto(s, `Decide-se quantas USB e quantas USA ficam em cada local j (até ${D.cap} por local). Mede-se a sobrevida em cada setor i. Os dois conjuntos se ligam por uma matriz de tempos de viagem, ${mil(D.n_cand)} locais × ${mil(D.n_setores)} setores, calculada pelo caminho mais curto nas ruas.`,
    M + 6.5, 4.0, 5.4, 1.9, { fontSize: 13.5 });
  conclusao(s, `O problema tem poucas variáveis (dois números por local), mas cada mapa candidato precisa ser avaliado nos ${mil(D.n_setores)} setores, e é isso que torna a conta pesada.`, 6.2);
  fontes(s, [L.ibge, L.cnes, L.osm]);
}

// ======================================================================
secao("Por que não o Huff");
// — huff x despacho
{
  const s = slideClaro("O Huff supõe uma escolha; o SAMU segue uma regra", "passo 2 · o que veio da fase 2");
  cartao(s, { x: M, y: 1.55, w: 5.9, h: 4.55, fill: "FBEAE7" });
  texto(s, "Huff (usado na fase 2)", M + 0.3, 1.7, 5.3, 0.35, { fontSize: 16, bold: true, color: ORANGE });
  formula(s, "huff_principal", M + 0.4, 2.15, 1.0);
  texto(s, "O modelo de Huff vem do varejo (1964) e descreve em qual loja um consumidor escolhe comprar. Cada base recebe um peso que diminui com a distância, e a chance de ela atender um setor é o seu peso dividido pela soma dos pesos de todas as bases. O ritmo dessa queda, β, não é medido em lugar nenhum: na fase 2 ele foi fixado em 4,5 min por argumento.",
    M + 0.3, 3.3, 5.35, 2.7, { fontSize: 13.5, lineSpacing: 18 });
  cartao(s, { x: M + 6.2, y: 1.55, w: 5.9, h: 4.55, fill: "E6F0EA" });
  texto(s, "Despacho (usado nas fases 2b e 3)", M + 6.5, 1.7, 5.3, 0.35, { fontSize: 16, bold: true, color: GREEN });
  formula(s, "desp_geom", M + 6.6, 2.4, 0.48);
  texto(s, "No SAMU ninguém escolhe: o médico regulador manda a ambulância livre mais próxima. A distância só decide a ordem em que as bases são consultadas; quem atende depende de quais estão ocupadas naquele momento. O único parâmetro é a ocupação q, a fração do tempo em que uma ambulância está fora atendendo, e ela pode ser estimada com as saídas registradas no SUS.",
    M + 6.5, 3.3, 5.35, 2.7, { fontSize: 13.5, lineSpacing: 18 });
  conclusao(s, "A diferença não é detalhe técnico: um modelo descreve uma escolha que não existe; o outro descreve a regra que o regulador de fato segue.", 6.35);
  fontes(s, [L.huff, L.daskin, L.revelle]);
}

// — consequencia: periferia
{
  const s = slideClaro("Consequência: o Huff esconde a demora da periferia", "passo 2 · o que veio da fase 2");
  const hc = huffP(CEN), dc = despP(CEN, Q_EX), hp = huffP(PER), dp = despP(PER, Q_EX);
  texto(s, "Um exemplo pequeno mostra o efeito. Um setor central tem USAs a 2 e 4 min; um periférico, a 10, 22 e 25 min. Calculamos o tempo esperado até a USA chegar pelos dois modelos:",
    M, 1.5, 7.4, 0.8, { fontSize: 13.5 });
  tabela(s, M, 2.35, 7.3, [2.0, 1.9, 1.7, 1.7],
    ["setor", "USAs a", "Huff (β = 4,5)", `despacho (q = ${n(Q_EX, 2)})`],
    [["central", "2 e 4 min", `${n(esp(hc, CEN), 2)} min`, `${n(esp(dc, CEN), 2)} min`],
     ["periférico", "10, 22 e 25 min", `${n(esp(hp, PER), 2)} min`, `${n(esp(dp, PER), 2)} min`]],
    { destaque: [1] });
  texto(s, `No setor periférico, o Huff dá à USA de 22 min uma chance de ${n(100 * hp[1], 3)}% de atender — na prática, nunca. No despacho ela atende toda vez que a de 10 min estiver ocupada, o que acontece em ${pct(100 * dp[1], 0)} dos chamados. Por isso o Huff calcula um tempo menor do que o real.`,
    M, 3.75, 7.3, 1.05, { fontSize: 13.5 });
  cartao(s, { x: M, y: 4.9, w: 7.3, h: 1.2, fill: "FBEAE7" });
  texto(s, "O Huff faz a periferia parecer mais bem servida do que é — justamente onde o projeto quer medir desigualdade. Um otimizador guiado por ele pode escolher mapas que abandonam a periferia sem perceber.",
    M + 0.3, 4.98, 6.8, 1.05, { fontSize: 13.5, color: INK, valign: "middle" });
  cartao(s, { x: 8.3, y: 1.5, w: 4.42, h: 4.6, fill: "FFFFFF" });
  texto(s, "No mapa real (resultados da fase 2)", 8.55, 1.65, 4, 0.3, { fontSize: 14, bold: true, color: INK });
  texto(s, `${n(HUFF_HOJE.f_tempo, 2)} × ${n(DESP_HOJE.f_tempo, 2)} min`, 8.55, 2.05, 4, 0.5, { fontFace: SERIF, fontSize: 24, bold: true, color: ORANGE, valign: "middle" });
  texto(s, "Tempo esperado de chegada na rede de hoje pelo Huff e pelo despacho. O mapa e as ruas são os mesmos; só muda o modelo de quem atende.",
    8.55, 2.6, 4, 1.1, { fontSize: 12.5, lineSpacing: 16 });
  texto(s, `${pct(DESP_GINI.cob_usa_10_p10)} × ${pct(DESP_PM.cob_usa_10_p10)}`, 8.55, 3.8, 4, 0.5, { fontFace: SERIF, fontSize: 24, bold: true, color: ORANGE, valign: "middle" });
  texto(s, "Chance de uma USA chegar em até 10 min para os 10% mais mal servidos: no mapa que a fase 2 otimizou com Huff e Gini, e no p-median (ambos medidos com o despacho).",
    8.55, 4.35, 4, 1.65, { fontSize: 12.5, lineSpacing: 16 });
  conclusao(s, "Por isso a fase 3 usa o modelo de despacho e mede cada mapa pelo que importa no fim: quantas vidas ele salva.", 6.4);
  fontes(s, [L.huff, L.daskin], "dados/fase2/sp_q_sens.json (trânsito livre)");
  s.addNotes(`Os exemplos de brinquedo usam β = 4,5 e q = ${n(Q_EX, 2)}, os mesmos do deck da fase 2b. Os dois números da direita são da fase 2b, em trânsito livre (antes da calibração da fase 3): por isso os tempos são menores que os desta apresentação.`);
}

// ======================================================================
secao("O modelo");
// — despacho e ocupacao
{
  const s = slideClaro("Quem atende: a ambulância livre mais próxima", "passo 3");
  texto(s, "Quando chega um chamado, o regulador percorre as ambulâncias da mais próxima para a mais distante e manda a primeira que estiver livre:", M, 1.5, 12.1, 0.45, { fontSize: 14 });
  const xs = [M, M + 3.1, M + 6.2, M + 9.3];
  [["1ª mais próxima", "ocupada", ORANGE], ["2ª mais próxima", "ocupada", ORANGE],
   ["3ª mais próxima", "LIVRE → vai ela", GREEN], ["4ª mais próxima", "nem é consultada", GREY]]
    .forEach((c, i) => {
      cartao(s, { x: xs[i], y: 2.05, w: 2.8, h: 1.0, fill: "FFFFFF" });
      texto(s, c[0], xs[i] + 0.2, 2.15, 2.4, 0.3, { fontSize: 14, bold: true, color: INK });
      texto(s, c[1], xs[i] + 0.2, 2.52, 2.4, 0.4, { fontSize: 14, bold: true, color: c[2] });
    });
  formula(s, "desp_geom", M + 0.2, 3.35, 0.5);
  texto(s, "Se cada ambulância está ocupada uma fração q do tempo, independentemente das outras, a chance de a k-ésima mais próxima atender é a chance de as k−1 anteriores estarem ocupadas (q elevado a k−1) vezes a chance de ela estar livre (1−q).",
    M + 4.0, 3.2, 8.1, 0.85, { fontSize: 13.5 });
  destaque(s, M, 4.25, 2.9, n(D.q_usb, 2), `q das USB: cada uma passa ${pct(100 * D.q_usb, 0)} do tempo fora, atendendo`, GREEN);
  destaque(s, M + 3.1, 4.25, 2.9, n(D.q_usa, 2), "q das USA: menos ocupadas, porque ficam reservadas aos casos graves", GREEN);
  cartao(s, { x: M + 6.2, y: 4.25, w: 5.9, h: 1.6, fill: "FFFFFF" });
  texto(s, [{ text: "Chamado grave", options: { bold: true, color: INK } }, { text: " → USA livre mais próxima.", options: { breakLine: true } },
    { text: "Chamado básico", options: { bold: true, color: INK } }, { text: " → USB livre mais próxima; se nenhuma, USA.", options: { breakLine: true } },
    { text: "Parada cardíaca", options: { bold: true, color: INK } }, { text: " → vão a USB e a USA livres mais próximas; quem chegar primeiro desfibrila." }],
    M + 6.45, 4.35, 5.45, 1.45, { fontSize: 13, paraSpaceAfter: 4 });
  conclusao(s, "A ocupação vem da lei de Little: o número médio de ambulâncias ocupadas é igual às saídas por hora (registradas no SIA/SUS) vezes a duração de cada saída (70 min no cenário central). Dividindo pelo número de ambulâncias, temos q.", 6.0);
  fontes(s, [L.daskin, L.sia], "dados/fase2/sp_utilizacao.json");
  s.addNotes("O tempo por saída (70 min no cenário central) não está no SIA: é hipótese, testada com 45 e 100 min na robustez. A ocupação é estimada para a cidade inteira, porque o faturamento não identifica a base de cada saída.");
}

// — tempos calibrados
{
  const s = slideClaro("Tempos reais: o mapa de ruas é rápido demais", "passo 3");
  texto(s, "A matriz de tempos vem do mapa de ruas do OpenStreetMap, que supõe trânsito livre e não conta o tempo até a ambulância sair da base. Isso deixa todas as chegadas mais rápidas do que são.",
    M, 1.5, 12.1, 0.7, { fontSize: 14 });
  destaque(s, M, 2.3, 3.6, `${n(CAL.et_grave_bruto)} min`, "tempo médio da USA até o chamado grave na rede de hoje, pelo mapa de ruas", ORANGE);
  seta(s, M + 3.75, 3.05, 0.6, 0);
  destaque(s, M + 4.5, 2.3, 3.6, `${n(CAL.alvo_grave_min, 0)} min`, "o que a Prefeitura informa para a chegada nos casos mais graves", INK);
  cartao(s, { x: M + 8.4, y: 2.3, w: 3.7, h: 1.6, fill: "E6F0EA" });
  texto(s, `f = ${n(CAL.fator, 3)}`, M + 8.65, 2.42, 3.3, 0.6, { fontFace: SERIF, fontSize: 28, bold: true, color: GREEN, valign: "middle" });
  texto(s, `fator de trânsito, mais ${n(CAL.atraso, 0)} min de atraso até a saída`, M + 8.65, 3.05, 3.3, 0.75, { fontSize: 12 });
  formula(s, "t_calib", M + 0.2, 4.2, 0.5);
  texto(s, "f é o único número que faz a rede de hoje reproduzir os 20 min da Prefeitura. Como ele multiplica todos os tempos por igual, não muda a ordem das bases — só ajusta o relógio.",
    M + 4.6, 4.1, 7.5, 0.8, { fontSize: 13.5 });
  cartao(s, { x: M, y: 5.05, w: 12.1, h: 0.95, fill: "FFF4DC" });
  texto(s, `Por que importa: com os tempos de trânsito livre, a rede de hoje salvaria ${n(CAL.hoje.livre.vidas)} de cada 1.000 paradas cardíacas; com os tempos calibrados, ${n(CAL.hoje.calibrado.vidas)}. Como a sobrevida cai rápido com o minuto, acertar o relógio muda tudo.`,
    M + 0.3, 5.1, 11.5, 0.85, { fontSize: 13.5, color: INK, valign: "middle" });
  conclusao(s, "Como a calibração depende de um único número publicado pela Prefeitura, a análise de robustez repete tudo também com trânsito livre e com trânsito 25% mais lento.", 6.25);
  fontes(s, [L.osm, L.pref23], "v1_calibracao.json");
}

// — a curva de sobrevida
{
  const s = slideClaro("Por que a parada cardíaca: cada minuto custa vidas", "passo 4");
  s.addChart(doc.ChartType.line, [{ name: "sobrevida", labels: D.curva_t.map((t) => (t % 2 === 0 ? String(t) : "")),
    values: D.curva_s.map((v) => 100 * v) }], {
    x: M, y: 1.5, w: 7.0, h: 4.4, chartColors: [GREEN], lineSize: 3, lineDataSymbol: "none",
    showTitle: true, title: "chance de sobreviver (%) × minutos até o desfibrilador",
    titleFontFace: SANS, titleFontSize: 13, titleColor: INK,
    catAxisLabelFontSize: 11, catAxisLabelFontFace: SANS, catAxisLabelColor: INK2,
    valAxisLabelFontSize: 11, valAxisLabelFontFace: SANS, valAxisLabelColor: INK2,
    valAxisLabelFormatCode: "0", valGridLine: { color: "E3E0D8", size: 0.5 }, catGridLine: { style: "none" },
    showLegend: false, valAxisMinVal: 0, catAxisLabelFrequency: 1,
  });
  const cs = [["5 min", D.s5], ["9 min", D.s9], ["15 min", D.s15]];
  cs.forEach((c, i) => {
    cartao(s, { x: 7.95, y: 1.5 + i * 0.95, w: 4.77, h: 0.82, fill: "FFFFFF" });
    texto(s, pct(100 * c[1]), 8.15, 1.55 + i * 0.95, 1.9, 0.72, { fontFace: SERIF, fontSize: 26, bold: true, color: GREEN, valign: "middle" });
    texto(s, `sobrevivem se o desfibrilador chega em ${c[0]}`, 10.05, 1.55 + i * 0.95, 2.55, 0.72, { fontSize: 12.5, valign: "middle" });
  });
  formula(s, "sobrev", 8.0, 4.4, 0.55);
  texto(s, `A curva vem de 9.273 paradas cardíacas em Ontário (Canadá). Entre 9 e 10 min, a chance de sobreviver cai ${pct(100 * D.queda_min, 0)} em um único minuto.`,
    7.95, 5.05, 4.77, 0.85, { fontSize: 12.5, lineSpacing: 16 });
  conclusao(s, "A parada cardíaca é a emergência em que a relação entre minutos e mortes está mais bem medida. Por isso ela serve de régua (condição traçadora) para comparar mapas, mesmo sendo só uma parte dos chamados.", 6.05);
  fontes(s, [L.demaio, L.erkut]);
  s.addNotes("Curva de De Maio et al. (2003), 9.273 paradas cardíacas no estudo OPALS (Ontário), usada por Erkut, Ingolfsson e Erdoğan (2008) para localizar ambulâncias. A PCR não entra como uma terceira classe de chamado: o SIA não diz quantos chamados são PCR. Ela é avaliada por cima do mapa, supondo que acontece onde as pessoas moram.");
}

// — vidas e CVaR
{
  const s = slideClaro("Duas medidas: vidas na cidade e nos 10% piores", "passo 4");
  cartao(s, { x: M, y: 1.5, w: 5.9, h: 3.45, fill: "FFFFFF" });
  texto(s, "Vidas: a média da cidade", M + 0.3, 1.65, 5.3, 0.35, { fontSize: 15, bold: true, color: INK });
  formula(s, "s_setor", M + 0.4, 2.1, 0.55);
  formula(s, "vidas", M + 0.4, 2.75, 0.55);
  texto(s, "Sᵢ é a chance de sobreviver a uma parada cardíaca no setor i: a curva de sobrevida aplicada ao tempo de cada base, ponderada pela chance pᵢⱼ de ela ser a primeira livre a chegar. Somando os setores pelo peso da população wᵢ, temos os sobreviventes esperados por 1.000 paradas na cidade.",
    M + 0.3, 3.45, 5.3, 1.45, { fontSize: 12.5, lineSpacing: 16 });
  cartao(s, { x: M + 6.2, y: 1.5, w: 5.9, h: 3.45, fill: "FFFFFF" });
  texto(s, "CVaR₁₀: os 10% mais mal servidos", M + 6.5, 1.65, 5.3, 0.35, { fontSize: 15, bold: true, color: INK });
  formula(s, "cvar", M + 6.6, 2.2, 0.62);
  texto(s, "CVaR (conditional value at risk) é uma medida das finanças: a média da cauda ruim de uma distribuição. Aqui, ordenamos os setores da pior para a melhor sobrevida e tiramos a média até completar 10% da população (os pesos ωᵢ). É a sobrevida de quem mora mais longe de tudo.",
    M + 6.5, 3.05, 5.3, 1.85, { fontSize: 12.5, lineSpacing: 16 });
  const bx = M, by = 5.15, bw = 12.1;
  s.addShape(doc.ShapeType.rect, { x: bx, y: by, w: bw * 0.1, h: 0.35, fill: { color: ORANGE }, line: { color: ORANGE } });
  s.addShape(doc.ShapeType.rect, { x: bx + bw * 0.1, y: by, w: bw * 0.9, h: 0.35, fill: { color: "C9D6E4" }, line: { color: "C9D6E4" } });
  texto(s, "10% piores → CVaR₁₀", bx + 0.1, by + 0.4, 3, 0.3, { fontSize: 12, bold: true, color: ORANGE });
  texto(s, "toda a população, ordenada da pior para a melhor sobrevida → a média de todos dá as vidas", bx + 2.4, by + 0.4, 9.6, 0.3, { fontSize: 12 });
  conclusao(s, `Na rede de hoje, de cada 1.000 paradas cardíacas na cidade, ${n(HOJE.vidas)} pessoas sobreviveriam em média; entre os 10% mais mal servidos, só ${n(HOJE.cvar10)}.`, 6.15);
  fontes(s, [L.ru]);
  s.addNotes("Diferente do Gini, o CVaR só melhora se a situação dos piores melhorar: não melhora tirando de quem tem mais.");
}

// — pisos
{
  const s = slideClaro("Sem desmontar o resto: pisos de cobertura", "passo 4");
  texto(s, "Otimizar só a parada cardíaca poderia piorar o atendimento dos outros chamados — por exemplo, tirando USAs de onde elas são necessárias para infartos e traumas. Por isso, duas coberturas não podem cair:",
    M, 1.5, 12.1, 0.75, { fontSize: 14 });
  formula(s, "cob", M + 0.2, 2.35, 0.55);
  texto(s, `É a chance de haver uma ambulância livre a até ${TAU} min do setor, somada pela população. nᵢ é o número de ambulâncias desse tipo a até ${TAU} min do setor i, e q é a ocupação.`,
    M + 4.4, 2.3, 7.7, 0.7, { fontSize: 13, valign: "middle" });
  destaque(s, M, 3.2, 3.85, pct(HOJE.cob_basico), `chamado básico: chance de uma USB livre a até ${TAU} min, rede de hoje`, BLUE);
  destaque(s, M + 4.12, 3.2, 3.85, pct(HOJE.cob_grave), `chamado grave: chance de uma USA livre a até ${TAU} min, rede de hoje`, ORANGE);
  destaque(s, M + 8.24, 3.2, 3.85, pct(PM.cob_grave), `chamado grave no p-median, para comparação`, BLUE);
  cartao(s, { x: M, y: 4.95, w: 12.1, h: 1.05, fill: "FFF4DC" });
  texto(s, [{ text: "Piso de hoje", options: { bold: true, color: INK } }, { text: " (padrão): nenhuma das duas coberturas pode ficar abaixo da de hoje.  " },
    { text: "Piso do p-median", options: { bold: true, color: INK } }, { text: " (variante): o chamado grave precisa alcançar a cobertura do p-median." }],
    M + 0.3, 5.0, 11.5, 0.95, { fontSize: 13.5, valign: "middle" });
  conclusao(s, "Os pisos são restrições: o otimizador pode melhorar essas coberturas, mas nunca aceita um mapa que as deixe abaixo do mínimo.", 6.3);
}

// — o problema
{
  const s = slideClaro("O problema de otimização", "passo 5");
  const lin = [
    ["DECIDIR", `quantas USB e USA ficam em cada um dos ${mil(D.n_cand)} locais`],
    ["MAXIMIZAR", null],
    ["FROTA", `exatamente ${D.n_usb} USB e ${D.n_usa} USA, como hoje`],
    ["CAPACIDADE", `no máximo ${D.cap} unidades por local`],
    ["MUDANÇA", "no máximo K unidades saem do local onde estão hoje"],
    ["PISOS", "coberturas do chamado básico e do grave ≥ as de hoje"],
  ];
  cartao(s, { x: M, y: 1.5, w: 7.3, h: 4.4, fill: "FFFFFF" });
  lin.forEach((l, i) => {
    const y = 1.65 + i * 0.7;
    texto(s, l[0], M + 0.25, y + 0.05, 1.7, 0.3, { fontSize: 11, bold: true, color: GOLD, charSpacing: 1 });
    if (i === 1) formula(s, "objetivo", M + 2.0, y - 0.02, 0.38);
    else texto(s, l[1], M + 2.0, y, 5.1, 0.6, { fontSize: 13.5, color: INK });
    if (i < lin.length - 1) s.addShape(doc.ShapeType.line, { x: M + 0.25, y: y + 0.6, w: 6.8, h: 0, line: { color: "E3E0D8", width: 0.75 } });
  });
  item(s, "λ", M + 7.6, 1.6, 4.5, "Peso da equidade",
    "Com λ = 0 só conta a média da cidade. Com λ > 0, melhorar a sobrevida de quem está nos 10% piores vale mais: na margem, 1 + λ/0,10 vezes o mesmo ganho para qualquer outra pessoa (com λ = 1, 11 vezes).", GOLD, 1.6);
  item(s, "K", M + 7.6, 3.6, 4.5, "Tamanho da mudança",
    `Quantas ambulâncias a gestão aceita mudar de base. Testamos K = ${KS.join(", ")} e sem limite.`, BLUE, 0.9);
  cartao(s, { x: M + 7.6, y: 4.85, w: 4.5, h: 1.05, fill: "FFF4DC" });
  texto(s, `Cada combinação de λ, K e piso é uma configuração resolvida separadamente: ${Object.keys(SOL).length} no total.`, M + 7.85, 4.9, 4.0, 0.95, { fontSize: 13, color: INK, valign: "middle" });
  conclusao(s, "Vidas e CVaR₁₀ estão na mesma unidade — sobreviventes por 1.000 paradas cardíacas —, por isso faz sentido somá-los com o peso λ.", 6.2);
}

// — como resolver
{
  const s = slideClaro("Como resolver: o tamanho vem dos setores, não dos locais", "passo 5");
  destaque(s, M, 1.5, 3.0, mil(D.n_vars_y), "variáveis de decisão: duas por local candidato", GREEN);
  destaque(s, M + 3.2, 1.5, 3.0, `~${n(D.n_restr / 1e6, 0)} mi`, `restrições num programa inteiro exato: ${mil(D.n_setores)} setores × ${D.n_bandas} faixas de tempo × ${D.n_cortes} cortes`, ORANGE);
  cartao(s, { x: M + 6.4, y: 1.5, w: 5.7, h: 1.6, fill: "FFF4DC" });
  texto(s, "Agrupar setores em zonas encolhe o problema, mas distorce a sobrevida em ~20%. Com zonas pequenas, o solver não termina em tempo útil. Por isso não usamos o programa inteiro como otimizador principal.",
    M + 6.65, 1.55, 5.2, 1.5, { fontSize: 13, valign: "middle" });
  texto(s, "A solução: uma busca local que avalia a sobrevida exata em todos os setores a cada passo", M, 3.3, 12.1, 0.35, { fontSize: 15, bold: true, color: INK });
  const passos = [["1", "Tirar", "uma ambulância de um local."], ["2", "Avaliar", "o ganho de pô-la em cada um dos outros locais, todos de uma vez."],
    ["3", "Aceitar", "a melhor troca que respeita a frota, o limite K e os pisos."], ["4", "Sacudir", `${BU.tam_chute} ambulâncias ao acaso e repetir (${BU.chutes} vezes), para não parar num ótimo local.`]];
  passos.forEach((p, i) => {
    const x = M + i * 3.08;
    cartao(s, { x, y: 3.8, w: 2.8, h: 1.75, fill: "FFFFFF" });
    bolha(s, p[0], x + 0.2, 3.95, GREEN);
    texto(s, p[1], x + 0.8, 3.97, 1.9, 0.4, { fontSize: 15, bold: true, color: INK, valign: "middle" });
    texto(s, p[2], x + 0.2, 4.5, 2.45, 1.0, { fontSize: 12.5, lineSpacing: 15 });
    if (i < 3) seta(s, x + 2.82, 4.6, 0.24, 0);
  });
  conclusao(s, "O programa inteiro fica como conferência: em casos pequenos, onde dá para testar todas as combinações, a busca e o solver encontram o mesmo ótimo da força bruta.", 5.85);
  fontes(s, [L.daskin, L.ru], "v3_busca.json, v4_limite.json");
  s.addNotes(`Cada configuração parte de ${BU.sementes.length} sementes aleatórias (e, sem limite K, também do p-median); a melhor vai para a busca iterada. Em zonas de ${n(LIM.lado_km, 0)} km, o limite dual do programa inteiro é um teto válido, mas largo (folga de ${pct(100 * LIM.folga_max_rel, 0)}): não certifica que a busca achou o ótimo.`);
}

// ======================================================================
secao("Resultados");
// — H1: mapas existentes
{
  const s = slideClaro("H1 · Os mapas que já existiam, medidos em vidas", "resultados");
  const ks = Object.keys(RE).sort((a, b) => RE[a].vidas - RE[b].vidas);
  const rot = ks.map(rotulo).concat(["vidas, piso p-median (fase 3)"]);
  const val = ks.map((k) => RE[k].vidas).concat([REC.vidas]);
  const cor = ks.map(corDe).concat([GREEN]);
  // ordem crescente com eixo minMax: o maior valor fica no topo
  barras(s, M, 1.45, 7.6, 4.75, rot, val, cor, { extra: { catAxisOrientation: "minMax" } });
  texto(s, "sobreviventes por 1.000 paradas cardíacas, todos medidos com o mesmo modelo e os mesmos tempos", M, 6.2, 7.6, 0.3, { fontSize: 11, color: GREY, align: "center" });
  cartao(s, { x: 8.5, y: 1.5, w: 4.22, h: 2.55, fill: "FBEAE7" });
  texto(s, "O Gini não comprou vidas", 8.75, 1.65, 3.8, 0.35, { fontSize: 15, bold: true, color: ORANGE });
  texto(s, `Os redesenhos guiados pelo Gini nas fases 2 e 2b (em laranja) chegam a no máximo ${n(MELHOR_GINI)} sobreviventes por 1.000 — abaixo do p-median (${n(PM.vidas)}). Igualar o número de ambulâncias por habitante não garante chegar a tempo.`,
    8.75, 2.05, 3.8, 1.95, { fontSize: 13 });
  cartao(s, { x: 8.5, y: 4.25, w: 4.22, h: 1.95, fill: "E6F0EA" });
  texto(s, "O otimizado por vidas fica no topo", 8.75, 4.4, 3.8, 0.35, { fontSize: 15, bold: true, color: GREEN });
  texto(s, `O mapa da fase 3 salva ${n(REC.vidas)} de cada 1.000, contra ${n(HOJE.vidas)} da rede de hoje (em cinza).`, 8.75, 4.8, 3.8, 1.3, { fontSize: 13 });
  fontes(s, [], "v2_reavaliacao.json, v3_busca.json, v6_robustez.json");
  s.addNotes("Cinza: rede de hoje. Laranja: mapas das fases 2 e 2b (Huff ou despacho + Gini, NSGA-II). Azul: p-median. Verde: o mapa da fase 3 escolhido pela robustez (só vidas, sem limite K, com o piso do p-median no chamado grave). Todos medidos com o mesmo modelo de despacho e os mesmos tempos calibrados.");
}

// — H1: contra o p-median
{
  const s = slideClaro("H1 · Muito melhor que hoje; um pouco melhor que o p-median", "resultados");
  destaque(s, M, 1.5, 3.85, n(HOJE.vidas), "rede de hoje: sobreviventes por 1.000 paradas cardíacas", GREY);
  destaque(s, M + 4.12, 1.5, 3.85, n(PM.vidas), "p-median clássico (minimiza o tempo médio)", BLUE);
  destaque(s, M + 8.24, 1.5, 3.85, n(REC.vidas), `otimizado por vidas: ${pct(100 * (REC.vidas / HOJE.vidas - 1), 0)} a mais que hoje`, GREEN);
  tabela(s, M, 3.35, 7.3, [3.0, 2.15, 2.15], ["", "p-median", "otimizado"],
    [["vidas na cidade", n(PM.vidas), n(REC.vidas)], ["vidas nos 10% piores (CVaR₁₀)", n(PM.cvar10), n(REC.cvar10)],
     ["USA a até 15 min, chamado grave", pct(PM.cob_grave), pct(REC.cob_grave)], ["ambulâncias que mudam de base", String(PM.movidas), String(SOL[REC_NOME.replace(/^vidas /, "")].movidas)]]);
  cartao(s, { x: 8.3, y: 3.35, w: 4.42, h: 2.55, fill: "FFF4DC" });
  texto(s, "Veredito de H1: parcial", 8.55, 3.5, 4, 0.35, { fontSize: 15, bold: true, color: INK });
  texto(s, `Confirmada contra a rede de hoje e contra os mapas do Gini. Contra o p-median, o ganho é pequeno: +${n(REC.vidas - PM.vidas)} por 1.000 paradas (~${n(ANO_PM, 0)} vidas por ano) e com menos equidade nos 10% piores.`,
    8.55, 3.9, 4, 1.95, { fontSize: 13.5 });
  conclusao(s, "Entre o otimizado e o p-median, a escolha é de valores — mais vidas na média ou mais nos piores —, não de técnica.", 6.2);
  fontes(s, [], "v2_reavaliacao.json, v3_busca.json");
}

// — H2: quanto mudar
{
  const s = slideClaro("H2 · Quanto rende mover só parte da frota", "resultados");
  const cats = ["hoje"].concat(KS.map((k) => `K = ${k}`)).concat(["sem limite", "p-median"]);
  const vals = [HOJE.vidas].concat(KS.map((k) => ex(`lam=0 K=${k}`).vidas)).concat([LV.vidas, PM.vidas]);
  const cores = [GREY].concat(KS.map(() => GREEN)).concat([GREEN, BLUE]);
  barras(s, M, 1.45, 7.6, 4.55, cats, vals, cores, { barDir: "col", extra: { catAxisLabelFontSize: 12 } });
  texto(s, "sobreviventes por 1.000 paradas cardíacas (λ = 0, piso de hoje)", M, 6.0, 7.6, 0.3, { fontSize: 11, color: GREY, align: "center" });
  const linhas = KS.map((k) => [`K = ${k}`, KM(`lam=0 K=${k}`) + " km", pct(100 * fracK(k), 0)]);
  tabela(s, 8.5, 1.5, 4.22, [1.4, 1.4, 1.42], ["movidas", "km", "do ganho"], linhas);
  texto(s, `"Do ganho" compara com o redesenho sem limite, que move ${SOL["lam=0 K=livre"].movidas} ambulâncias. O p-median também é um redesenho completo: move ${PM.movidas}.`, 8.5, 3.75, 4.22, 1.0, { fontSize: 12.5 });
  cartao(s, { x: 8.5, y: 4.85, w: 4.22, h: 1.15, fill: "E6F0EA" });
  texto(s, `H2 confirmada: mudar ${KS[1]} ambulâncias de base entrega ${pct(100 * fracK(KS[1]), 0)} do ganho; ${KS[2]} ambulâncias, ${pct(100 * fracK(KS[2]), 0)}.`, 8.75, 4.9, 3.8, 1.05, { fontSize: 13.5, color: INK, valign: "middle" });
  conclusao(s, "Os primeiros movimentos são os que mais rendem: cada ambulância movida acrescenta menos que a anterior. Uma mudança em etapas é possível.", 6.35);
  fontes(s, [], "v3_busca.json");
  s.addNotes("“Do ganho” = (vidas com K − vidas hoje) ÷ (vidas sem limite − vidas hoje). Km em linha reta, no emparelhamento que minimiza a distância entre bases antigas e novas; só informativo, não entra no problema.");
}

// — o piso do grave
{
  const s = slideClaro("O piso do chamado grave quase não custa vidas", "resultados");
  texto(s, "Comparamos o melhor mapa só por vidas com o melhor mapa que também exige, para o chamado grave, a cobertura do p-median:", M, 1.5, 12.1, 0.45, { fontSize: 14 });
  [["Só vidas (λ = 0, piso de hoje)", LV, ORANGE, "FBEAE7"], ["Com o piso do p-median", REC, GREEN, "E6F0EA"]].forEach((c, i) => {
    const x = M + i * 4.12;
    cartao(s, { x, y: 2.1, w: 3.85, h: 2.75, fill: c[3] });
    texto(s, c[0], x + 0.25, 2.22, 3.4, 0.35, { fontSize: 14.5, bold: true, color: c[2] });
    texto(s, n(c[1].vidas), x + 0.25, 2.62, 3.4, 0.6, { fontFace: SERIF, fontSize: 30, bold: true, color: INK, valign: "middle" });
    texto(s, "sobreviventes por 1.000 paradas", x + 0.25, 3.2, 3.4, 0.35, { fontSize: 12 });
    texto(s, pct(c[1].cob_grave), x + 0.25, 3.65, 3.4, 0.6, { fontFace: SERIF, fontSize: 30, bold: true, color: INK, valign: "middle" });
    texto(s, `chance de uma USA a até ${TAU} min no chamado grave`, x + 0.25, 4.25, 3.4, 0.5, { fontSize: 12 });
  });
  cartao(s, { x: 8.86, y: 2.1, w: 3.86, h: 2.75, fill: "FFFFFF" });
  texto(s, "Por que o piso é preciso", 9.1, 2.22, 3.4, 0.35, { fontSize: 14.5, bold: true, color: INK });
  texto(s, "Na parada cardíaca, a USB com desfibrilador costuma chegar primeiro. O objetivo, então, não enxerga os chamados que só a USA resolve (AVC, infarto, trauma grave) e deixa a USA perto do piso de hoje.",
    9.1, 2.62, 3.4, 2.15, { fontSize: 13 });
  cartao(s, { x: M, y: 5.05, w: 12.1, h: 0.95, fill: "FFF4DC" });
  const kg = KS.map((k) => ex(`lam=0 K=${k}`).cob_grave);
  texto(s, `Um limite: com K limitado, a cobertura do p-median não é alcançável a partir da rede de hoje. Os mapas com K ficam com ${n(Math.min(...kg), 0)}–${n(Math.max(...kg), 0)}% de cobertura grave.`,
    M + 0.3, 5.1, 11.5, 0.85, { fontSize: 13.5, color: INK, valign: "middle" });
  conclusao(s, "Exigir a cobertura do p-median custa só 0,1 sobrevivente por 1.000 e protege o chamado grave. Por isso a recomendação usa esse piso: a parada cardíaca sozinha não basta como objetivo.", 6.15);
  fontes(s, [], "v3_busca.json");
}

// — equidade
{
  const s = slideClaro("Equidade: um ponto de escolha, não de técnica", "resultados");
  figura(s, "v01_fronteira.png", M, 1.45, 7.4, [988, 598]);
  const cs = [["p-median", PM, BLUE], ["otimizado, λ = 0 · piso p-median", REC, GREEN], ["otimizado, λ = 1 · piso p-median", EQ, GOLD]];
  cs.forEach((c, i) => {
    const y = 1.5 + i * 1.2;
    cartao(s, { x: 8.3, y, w: 4.42, h: 1.05, fill: "FFFFFF" });
    texto(s, c[0], 8.5, y + 0.08, 4.0, 0.3, { fontSize: 13, bold: true, color: c[2] });
    texto(s, `${n(c[1].vidas)} na cidade · ${n(c[1].cvar10)} nos 10% piores`, 8.5, y + 0.45, 4.0, 0.5, { fontSize: 14, color: INK });
  });
  texto(s, "Aumentar λ troca vidas da média por vidas dos piores. O p-median fica praticamente sobre essa fronteira: ele já é um bom equilíbrio entre as duas coisas.",
    8.3, 5.15, 4.42, 1.05, { fontSize: 13 });
  conclusao(s, "Qual ponto defender — mais vidas no total ou mais vidas para quem está mais longe — é uma decisão de valores do grupo, não algo que o modelo decide.", 6.3);
  fontes(s, [], "v3_busca.json, v2_reavaliacao.json");
  s.addNotes("No gráfico, cada linha é um limite K e os pontos de uma linha são os pesos λ. Os losangos são os mapas das fases anteriores.");
}

// — mapa
{
  const s = slideClaro("Onde a sobrevida muda", "resultados");
  figura(s, "v03_mapa.png", (13.333 - 8.3) / 2, 1.35, 8.3, [963, 574]);
  texto(s, "Sobrevida a uma parada cardíaca em cada setor, na rede de hoje e no mapa recomendado. Círculos: USB; triângulos: USA (o tamanho indica quantas unidades há no local). O mapa novo espalha as bases e clareia a periferia.",
    M, 6.35, 12.1, 0.6, { fontSize: 12.5, align: "center" });
  fontes(s, [], "figs/fase3/v03_mapa.png");
}

// ======================================================================
secao("Conferência");
// — modelo x simulacao: o que e cada um
{
  const s = slideClaro("H3 · Modelo e simulação: duas formas de calcular a mesma coisa", "conferência");
  const R = simDe(REC_NOME);
  texto(s, "Os números até aqui saíram de uma fórmula (o modelo). Para saber se a fórmula engana, calculamos as mesmas vidas de outro jeito, sem a sua principal simplificação (a simulação).",
    M, 1.5, 12.1, 0.7, { fontSize: 14 });
  cartao(s, { x: M, y: 2.35, w: 5.9, h: 3.55, fill: "E7F0F7" });
  texto(s, "O modelo: uma fórmula", M + 0.3, 2.5, 5.3, 0.35, { fontSize: 16, bold: true, color: TEAL });
  texto(s, [
    { text: "Supõe que cada ambulância está ocupada uma fração q do tempo, de forma independente das outras.", options: { bullet: true, breakLine: true } },
    { text: "Com isso, a sobrevida de cada setor sai de uma conta direta, em frações de segundo por mapa.", options: { bullet: true, breakLine: true } },
    { text: "É o que permite ao otimizador testar milhões de mapas.", options: { bullet: true, breakLine: true } },
    { text: "Ponto fraco: na vida real as ocupações não são independentes. Num pico de chamados, ambulâncias vizinhas ficam ocupadas ao mesmo tempo.", options: { bullet: true } }],
    M + 0.3, 2.95, 5.35, 2.9, { fontSize: 13, paraSpaceAfter: 5, lineSpacing: 16 });
  cartao(s, { x: M + 6.2, y: 2.35, w: 5.9, h: 3.55, fill: "FFF4DC" });
  texto(s, "A simulação: uma cidade sorteada", M + 6.5, 2.5, 5.3, 0.35, { fontSize: 16, bold: true, color: GOLD });
  texto(s, [
    { text: `Reproduz um ano de São Paulo chamado a chamado: ~${mil(R.sim_n_chamados_mean / 1000)} mil chamados sorteados nas taxas do SIA, em setores sorteados pela população.`, options: { bullet: true, breakLine: true } },
    { text: "O regulador aplica a regra real; cada ambulância fica de fato ocupada durante a saída; se todas estão ocupadas, o chamado espera.", options: { bullet: true, breakLine: true } },
    { text: "A cada chamado, mede em quanto tempo um desfibrilador chegaria a uma parada cardíaca naquele setor, com a frota no estado em que estava naquele instante.", options: { bullet: true, breakLine: true } },
    { text: `Leva minutos por mapa: serve para conferir os finalistas, com ${SIM.sementes.length} sorteios diferentes cada.`, options: { bullet: true } }],
    M + 6.5, 2.95, 5.35, 2.9, { fontSize: 13, paraSpaceAfter: 5, lineSpacing: 16 });
  conclusao(s, "Se o modelo e a simulação concordarem na ordem dos mapas, a simplificação do modelo não está levando à escolha do mapa errado.", 6.15);
  fontes(s, [L.sia], "v5_simulacao.json; código em fase3_vidas/experimentos/simula_vidas.py");
  s.addNotes("A simulação é uma simulação de eventos discretos. Os chamados chegam por um processo de Poisson com as taxas de envio de USB e USA do SIA/SUS; o setor de cada chamado é sorteado com probabilidade proporcional à população. A duração de cada saída é o deslocamento mais um tempo aleatório, com média de 70 min no cenário central. A parada cardíaca não ocupa ninguém na simulação: ela já está dentro dos volumes do SIA, e só medimos quanto tempo o primeiro desfibrilador levaria.");
}

// — simulacao: resultado
{
  const s = slideClaro("H3 · O que a simulação mostrou", "conferência");
  const cfg = ["hoje", "fase2 lam=0.1", "vidas lam=0 K=20", "vidas lam=0 K=40", "fase2b central lam=0.1", "p-median", REC_NOME]
    .filter((c) => simDe(c));
  s.addChart(doc.ChartType.bar, [
    { name: "modelo (fórmula)", labels: cfg.map(rotulo), values: cfg.map((c) => simDe(c).an_vidas_mean) },
    { name: "simulação (cidade sorteada)", labels: cfg.map(rotulo), values: cfg.map((c) => simDe(c).sim_vidas_mean) }], {
    x: M, y: 1.45, w: 7.6, h: 4.75, barDir: "bar", chartColors: [TEAL, GOLD], barGapWidthPct: 40,
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.0", dataLabelFontSize: 10,
    dataLabelFontFace: SANS, dataLabelColor: INK, catAxisLabelFontSize: 11, catAxisLabelFontFace: SANS,
    catAxisLabelColor: INK2, valAxisHidden: true, valGridLine: { style: "none" }, catGridLine: { style: "none" },
    catAxisOrientation: "maxMin", valAxisMinVal: 0, showLegend: true, legendPos: "b", legendFontSize: 11, legendFontFace: SANS,
  });
  // pares de mapas cuja ordem muda entre modelo e simulacao
  const an_ = Object.fromEntries(SIMC.map((m) => [m.config, m.an_vidas_mean]));
  const si_ = Object.fromEntries(SIMC.map((m) => [m.config, m.sim_vidas_mean]));
  const ks = Object.keys(an_), trocas = [];
  ks.forEach((a) => ks.forEach((b) => { if (a < b && (an_[a] - an_[b]) * (si_[a] - si_[b]) < 0) trocas.push(Math.abs(an_[a] - an_[b])); }));
  const fila = Math.max(...SIMC.map((m) => m.sim_frac_fila_mean));
  cartao(s, { x: 8.5, y: 1.5, w: 4.22, h: 2.3, fill: "FFFFFF" });
  texto(s, "A fórmula é um pouco otimista", 8.75, 1.62, 3.8, 0.35, { fontSize: 14.5, bold: true, color: INK });
  texto(s, `Em todos os mapas, a simulação dá um pouco menos de vidas que o modelo: até ${n(DIF_SIM)} por 1.000. É o efeito esperado: nos picos, vizinhas ficam ocupadas juntas e o desfibrilador demora mais.`,
    8.75, 2.0, 3.8, 1.75, { fontSize: 12.5, lineSpacing: 16 });
  cartao(s, { x: 8.5, y: 3.95, w: 4.22, h: 2.25, fill: "E6F0EA" });
  texto(s, "Mas a ordem dos mapas não muda", 8.75, 4.07, 3.8, 0.35, { fontSize: 14.5, bold: true, color: GREEN });
  texto(s, (trocas.length ? `O erro é parecido para todos os mapas. Só trocam de posição mapas que o modelo separa por no máximo ${n(Math.max(...trocas))} por 1.000 — dentro do ruído.` :
    "O erro é parecido para todos os mapas, então o melhor no modelo também é o melhor na simulação.") +
    ` Fila quase nunca acontece (${pct(100 * fila, 2)} dos chamados).`,
    8.75, 4.45, 3.8, 1.7, { fontSize: 12.5, lineSpacing: 16 });
  conclusao(s, "A simplificação do modelo erra um pouco o nível, mas não muda quem é melhor: ela é segura para escolher entre mapas.", 6.45);
  fontes(s, [], `v5_simulacao.json (tempo por saída de 70 min, média de ${SIM.sementes.length} sorteios)`);
}

// — robustez: o que sao os cenarios
{
  const s = slideClaro("H3 · 18 cenários para o que não conseguimos medir", "conferência");
  const pc = ROB.por_config, ex_ = ROB.tabela.filter((r) => r.servico === "central" && r.transito === "calibrado" && r.carga === "sia");
  const melhorEx = ex_.reduce((a, b) => (b.vidas > a.vidas ? b : a));
  const recEx = ex_.find((r) => r.config === REC_NOME);
  const siaDia = D.sia_dia, prefDia = D.sia_dia * ROB.carga_baixa_fator_q;
  texto(s, `Três entradas do modelo não vêm de medição direta. Em vez de apostar num único valor para cada uma, avaliamos os ${pc.length} mapas finalistas em todas as combinações: 3 × 3 × 2 = ${ROB.cenarios.length} cenários.`,
    M, 1.45, 12.1, 0.7, { fontSize: 14 });
  tabela(s, M, 2.15, 12.1, [2.6, 3.0, 6.5], ["o que varia", "valores testados", "por que não sabemos o valor certo"],
    [["tempo que cada saída prende a ambulância", "45 · 70 · 100 min", "O SIA registra quantas saídas houve, mas não quanto tempo cada uma durou. Esse tempo define a ocupação q."],
     ["trânsito", "livre · calibrado · 25% mais lento", "A calibração se apoia num único número da Prefeitura (20 min nos casos mais graves)."],
     ["volume de saídas", `SIA (~${mil(siaDia)}/dia) · Prefeitura (~${mil(prefDia)}/dia)`, "As duas fontes oficiais discordam por mais da metade; menos saídas significa ambulâncias menos ocupadas."]],
    { fontSize: 12.5, rowH: [0.38, 0.55, 0.55, 0.55] });
  cartao(s, { x: M, y: 4.4, w: 12.1, h: 1.6, fill: "FFF4DC" });
  texto(s, "O que ganhamos com isso", M + 0.3, 4.5, 11.5, 0.35, { fontSize: 14.5, bold: true, color: INK });
  texto(s, `Se o mapa recomendado só fosse bom num cenário, a recomendação dependeria de qual chute está certo. Para cada mapa e cenário medimos o arrependimento: quanto ele perde para o melhor mapa daquele cenário. Exemplo, no cenário central: o melhor mapa salva ${n(melhorEx.vidas, 2)} por 1.000; o recomendado, ${n(recEx.vidas, 2)}; o arrependimento dele ali é ${n(melhorEx.vidas - recEx.vidas, 2)}.`,
    M + 0.3, 4.87, 11.5, 1.1, { fontSize: 13, lineSpacing: 17 });
  conclusao(s, "Escolhemos o mapa de menor arrependimento máximo: o que, no pior dos 18 cenários, fica mais perto do melhor possível. É a escolha segura quando não sabemos qual cenário é o verdadeiro.", 6.15);
  fontes(s, [L.pref23, L.sia], "v6_robustez.json");
}

// — robustez: resultado
{
  const s = slideClaro("H3 · Em todos os 18 cenários, o recomendado perde quase nada", "conferência");
  const pc = ROB.por_config;
  const venc = {};
  ROB.cenarios.forEach(([sv, tn, cg]) => {
    const xs = ROB.tabela.filter((r) => r.servico === sv && r.transito === tn && r.carga === cg);
    const b = xs.reduce((a, c) => (c.vidas > a.vidas ? c : a)).config;
    venc[b] = (venc[b] || 0) + 1;
  });
  const vs = Object.entries(venc).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${rotulo(k)} (${v})`).join("; ");
  barras(s, M, 1.45, 7.6, 4.45, pc.map((d) => rotulo(d.config)), pc.map((d) => d.arrep_max), pc.map((d) => corDe(d.config)), { fmt: "0.0" });
  texto(s, "maior perda contra o melhor mapa de cada cenário (sobreviventes por 1.000 paradas)", M, 5.9, 7.6, 0.3, { fontSize: 11, color: GREY, align: "center" });
  cartao(s, { x: 8.5, y: 1.5, w: 4.22, h: 2.5, fill: "E6F0EA" });
  texto(s, "O recomendado é o mais seguro", 8.75, 1.62, 3.8, 0.35, { fontSize: 14.5, bold: true, color: GREEN });
  texto(s, `Ele não vence nenhum cenário isolado — quem vence é ${vs} —, mas nunca fica mais de ${n(RC[REC_NOME].arrep_max, 2)} por 1.000 atrás do melhor. O p-median chega a perder ${n(RC["p-median"].arrep_max)}; a rede de hoje, ${n(RC["hoje"].arrep_max)}.`,
    8.75, 2.0, 3.8, 1.95, { fontSize: 12.5, lineSpacing: 16 });
  cartao(s, { x: 8.5, y: 4.15, w: 4.22, h: 1.95, fill: "FBEAE7" });
  texto(s, "Mas a troca de equidade continua", 8.75, 4.27, 3.8, 0.35, { fontSize: 14.5, bold: true, color: ORANGE });
  texto(s, `No pior cenário, os 10% mais mal servidos do recomendado ficam com ${n(RC[REC_NOME].cvar_min)} sobreviventes por 1.000; no p-median, ${n(RC["p-median"].cvar_min)}.`,
    8.75, 4.65, 3.8, 1.4, { fontSize: 12.5, lineSpacing: 16 });
  conclusao(s, `Os níveis mudam muito entre cenários (de ${n(RC[REC_NOME].vidas_min)} a ${n(RC[REC_NOME].vidas_max)} sobreviventes por 1.000 para o recomendado, sobretudo pelo trânsito), mas a ordem dos mapas quase não muda. H3 confirmada.`, 6.25);
  fontes(s, [], "v6_robustez.json");
}

// — contraprova
{
  const s = slideClaro("Contraprova: sem a parada cardíaca, a cobertura escolhe pior", "conferência");
  texto(s, `E se a parada cardíaca fosse uma escolha ruim de régua? Resolvemos o mesmo problema maximizando outra coisa: a fração de chamados alcançados em até ${TAU} min (graves e básicos, nos pesos do SIA). A sobrevida desse mapa foi medida só depois.`,
    M, 1.5, 12.1, 0.75, { fontSize: 14 });
  destaque(s, M, 2.45, 3.85, pct(CLS.cob_grave), `dos chamados graves com USA a até ${TAU} min: a maior cobertura de todos os mapas`, GOLD);
  destaque(s, M + 4.12, 2.45, 3.85, n(CLS.vidas), "sobreviventes por 1.000 paradas cardíacas nesse mesmo mapa", GOLD);
  destaque(s, M + 8.24, 2.45, 3.85, `−${n(REC.vidas - CLS.vidas)}`, `contra o otimizado por vidas, e −${n(PM.vidas - CLS.vidas)} contra o p-median`, ORANGE);
  cartao(s, { x: M, y: 4.25, w: 12.1, h: 1.65, fill: "FFFFFF" });
  texto(s, `O motivo é o limiar. "Em até ${TAU} min" trata do mesmo jeito chegar em 5 e chegar em 14 minutos, mas a sobrevida cai cerca de ${pct(100 * D.queda_min, 0)} a cada minuto nessa faixa. Um mapa pode cobrir mais chamados dentro do limite e, mesmo assim, chegar mais tarde a quem mais precisa.`,
    M + 0.3, 4.35, 11.5, 1.45, { fontSize: 14, color: INK, valign: "middle" });
  conclusao(s, "Métricas de cobertura com limiar largo escolhem mapas que salvam menos. Se a parada cardíaca for abandonada como régua, o objetivo deve usar o tempo inteiro, não um limiar de 15 min.", 6.15);
  fontes(s, [], "v7_classes.json");
}

// ======================================================================
secao("Fechamento");
// — vidas por ano
{
  const s = slideClaro("Em vidas por ano", "o que levar");
  texto(s, `Para traduzir "sobreviventes por 1.000 paradas" em vidas por ano, precisamos saber quantas paradas cardíacas acontecem em São Paulo. Esse número não existe em dado público: o SIA não registra diagnóstico. Usamos a incidência de um grande registro europeu (EuReCa TWO) e, como ela pode não valer para São Paulo, testamos também metade e uma vez e meia esse valor.`,
    M, 1.5, 12.1, 1.05, { fontSize: 14 });
  const ganho1000 = REC.vidas - HOJE.vidas;
  [["incidência baixa (metade)", D.inc_faixa[0], GREY], ["incidência central (EuReCa)", 1, GREEN], ["incidência alta (1,5×)", D.inc_faixa[1], GREY]].forEach((c, i) => {
    const x = M + i * 4.12, inc = D.inc_central * c[1], pcr = D.pcr_ano * c[1];
    cartao(s, { x, y: 2.7, w: 3.85, h: 2.15, fill: i === 1 ? "E6F0EA" : "FFFFFF" });
    texto(s, c[0], x + 0.25, 2.8, 3.4, 0.35, { fontSize: 13.5, bold: true, color: INK });
    texto(s, `+${n(ganho1000 * pcr / 1000, 0)}`, x + 0.25, 3.15, 3.4, 0.75, { fontFace: SERIF, fontSize: 36, bold: true, color: c[2] === GREEN ? GREEN : INK, valign: "middle" });
    texto(s, `vidas por ano. ~${n(inc, 0)} paradas por 100 mil habitantes → ~${mil(pcr)} paradas por ano na capital`, x + 0.25, 3.95, 3.4, 0.85, { fontSize: 12.5, lineSpacing: 16 });
  });
  cartao(s, { x: M, y: 5.0, w: 12.1, h: 1.05, fill: "FFF4DC" });
  texto(s, `A "faixa ${n(ANO * D.inc_faixa[0], 0)}–${n(ANO * D.inc_faixa[1], 0)}" é isso: o resultado das três hipóteses de incidência, não um intervalo de confiança estatístico. O ganho por 1.000 paradas (+${n(ganho1000)}, mapa recomendado contra a rede de hoje) é o mesmo nas três; só muda quantas paradas há por ano. Contra o p-median, o ganho seria de ~${n(ANO_PM, 0)} vidas por ano.`,
    M + 0.3, 5.05, 11.5, 0.95, { fontSize: 13, color: INK, valign: "middle", lineSpacing: 17 });
  conclusao(s, "É ordem de grandeza, não previsão: a curva de sobrevida é de Ontário e a incidência é europeia. O ganho grande vem de sair da rede de hoje.", 6.25);
  fontes(s, [L.eureca, L.ibge, L.demaio]);
}

// — veredito
{
  const s = slideEscuro(TEAL);
  texto(s, "VEREDITO DA HIPÓTESE", M, 0.6, 11, 0.3, { fontSize: 11, bold: true, color: GOLD, charSpacing: 1.4 });
  texto(s, "O que a fase 3 mostrou", M, 1.0, 11, 0.8, { fontFace: SERIF, fontSize: 30, bold: true, color: "FFFFFF", valign: "middle" });
  const V = [
    ["H1", "Parcial", `O mapa otimizado por vidas é muito melhor que a rede de hoje (${n(HOJE.vidas)} → ${n(REC.vidas)} sobreviventes por 1.000) e que os mapas do Gini. Contra o p-median, ganha só ${n(REC.vidas - PM.vidas)} por 1.000 e com menos equidade.`],
    ["H2", "Confirmada", `Não é preciso redesenhar tudo: mudar ${KS[1]} ambulâncias de base entrega ${pct(100 * fracK(KS[1]), 0)} do ganho, e ${KS[2]} ambulâncias, ${pct(100 * fracK(KS[2]), 0)}.`],
    ["H3", "Confirmada", `A simulação mostra que o modelo é otimista em até ${n(DIF_SIM)} por 1.000, sem mudar a ordem dos mapas; nos 18 cenários, o recomendado nunca fica mais de ${n(RC[REC_NOME].arrep_max, 2)} atrás do melhor.`],
  ];
  V.forEach((v, i) => {
    const y = 2.0 + i * 1.3;
    bolha(s, v[0], M, y, i === 0 ? GOLD : GREEN, 0.62);
    texto(s, v[1], M + 0.85, y, 2.0, 0.62, { fontSize: 17, bold: true, color: i === 0 ? GOLD : "8FD3AE", valign: "middle" });
    texto(s, v[2], M + 2.9, y - 0.22, 9.0, 1.06, { fontSize: 14.5, color: "E7ECF2", valign: "middle", lineSpacing: 19 });
  });
  texto(s, "Também aprendemos duas coisas: a parada cardíaca sozinha não basta como objetivo (é preciso o piso do chamado grave), e cobertura em até 15 min não é a mesma coisa que sobrevida.",
    M, 5.95, 12.0, 0.8, { fontFace: SERIF, fontSize: 16, italic: true, color: "C9D6E4" });
}

// — limitacoes
{
  const s = slideClaro("Limitações: o que ainda é hipótese", "o que levar");
  const lim = [
    ["Uma curva de sobrevida", "Vem de Ontário, nos anos 1990, e só de paradas de causa cardíaca. O nível absoluto em São Paulo pode ser outro; comparar mapas entre si é mais confiável que o número de vidas."],
    ["Parada onde as pessoas moram", "Não temos a idade por setor nem a população de dia: bairros comerciais e bairros com muitos idosos ficam sub-representados."],
    ["Calibração em um ponto", "O fator de trânsito vem de uma única notícia (20 min nos casos mais graves); a robustez testa outros valores, mas não substitui uma medida."],
    ["Tempo por saída e volume de saídas", "Nenhum dos dois é medido: entram como cenários (45/70/100 min; SIA × Prefeitura), não como fatos."],
    ["Otimalidade não provada", "A busca acha o ótimo nos casos pequenos, onde dá para conferir, mas o teto do programa inteiro é largo demais para certificar o caso real."],
    ["Viabilidade das bases", `Cada local aceita até ${D.cap} unidades no modelo; garagem, equipe e custo de instalar uma base não foram verificados.`],
  ];
  lim.forEach((l, i) => {
    const col = i % 2, lin = Math.floor(i / 2);
    item(s, i + 1, M + col * 6.2, 1.55 + lin * 1.5, 5.9, l[0], l[1], ORANGE, 1.05);
  });
  conclusao(s, "E não há validação externa: nenhum dado público traz tempos de resposta observados por bairro para comparar com o modelo.", 6.2);
  fontes(s, [L.demaio, L.pref23]);
}

// — referencias
{
  const s = slideClaro("Referências", "fontes");
  const refs = [
    "De Maio, V. J. et al. (2003). Optimal defibrillation response intervals for maximum out-of-hospital cardiac arrest survival rates. Ann. Emerg. Med. 42(2). doi:10.1067/mem.2003.266",
    "Erkut, E., Ingolfsson, A. & Erdoğan, G. (2008). Ambulance location for maximum survival. Naval Research Logistics 55(1). doi:10.1002/nav.20267",
    "Daskin, M. (1983). A maximum expected covering location model. Transportation Science 17(1). doi:10.1287/trsc.17.1.48",
    "ReVelle, C. & Hogan, K. (1989). The maximum availability location problem. Transportation Science 23(3). doi:10.1287/trsc.23.3.192",
    "Rockafellar, R. T. & Uryasev, S. (2000). Optimization of conditional value-at-risk. Journal of Risk 2(3). doi:10.21314/JOR.2000.038",
    "Gräsner, J.-T. et al. (2020). Survival after out-of-hospital cardiac arrest in Europe — EuReCa TWO. Resuscitation 148. doi:10.1016/j.resuscitation.2019.12.042",
    "Huff, D. (1964). Defining and estimating a trading area. Journal of Marketing 28(3). doi:10.1177/002224296402800307",
    "Dados: IBGE, Censo 2022 (setores) · CNES/DATASUS · SIA/SUS (arquivos PASP, SIGTAP) · OpenStreetMap · Prefeitura de SP (notícia de 21/12/2023).",
    "Código e resultados: fase3_vidas/ e dados/fase3/*.json; relatório completo em fase3_vidas/docs/relatorio_vidas.html.",
  ];
  texto(s, refs.map((r, i) => ({ text: r, options: { bullet: true, breakLine: i < refs.length - 1 } })),
    M, 1.6, 12.1, 5.2, { fontSize: 12.5, paraSpaceAfter: 7, lineSpacing: 15 });
}

doc.writeFile({ fileName: SAIDA }).then(() => console.log("-> " + SAIDA + ` (${_pag} slides)`));
