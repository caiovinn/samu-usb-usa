const fs = require("fs");
const path = require("path");
const pptx = require("pptxgenjs");

/* Deck curto para a aula: o modelo de despacho, a funcao objetivo de vidas
 * salvas e a comparacao de todos os metodos (Huff + 2SFCA, despacho + 2SFCA,
 * p-median, despacho + vidas) nas metricas antigas e nas novas.
 *
 *     uv run python -m fase3_vidas.docs.deck_dados            # deck_vidas.json
 *     uv run python -m fase3_vidas.docs.deck_evolucao_dados   # deck_evolucao.json
 *     uv run python -m fase3_vidas.docs.formulas_gera         # formulas em PNG
 *     node fase3_vidas/docs/deck_evolucao.js
 *
 * Mesma familia visual de deck_vidas.js. Todo numero vem de JSON: os mapas
 * medidos por todas as metricas em deck_evolucao.json; Huff x despacho e a
 * ponte beta <-> q em dados/fase2/sp_q_sens.json; o resto em dados/fase3/v*.json.
 */

const RAIZ = path.join(__dirname, "..", "..");
const DADOS = path.join(RAIZ, "dados", "fase3");
const DADOS2 = path.join(RAIZ, "dados", "fase2");
const FORM3 = path.join(RAIZ, "figs", "fase3", "formulas") + path.sep;
const FORM2 = path.join(RAIZ, "figs", "fase2", "formulas") + path.sep;
const SAIDA = path.join(__dirname, "apresentacao_evolucao_sp.pptx");

const lerJson = (p) => JSON.parse(fs.readFileSync(p, "utf-8"));
const D = lerJson(path.join(DADOS, "deck_vidas.json"));
const EV = lerJson(path.join(DADOS, "deck_evolucao.json"));
const CAL = lerJson(path.join(DADOS, "v1_calibracao.json"));
const BU = lerJson(path.join(DADOS, "v3_busca.json"));
const SIM = lerJson(path.join(DADOS, "v5_simulacao.json"));
const ROB = lerJson(path.join(DADOS, "v6_robustez.json"));
const CL = lerJson(path.join(DADOS, "v7_classes.json"));
const QS = lerJson(path.join(DADOS2, "sp_q_sens.json"));
const FIG3 = path.join(RAIZ, "figs", "fase3") + path.sep;
const MP = lerJson(path.join(DADOS, "v05_mapa4.json"));     // figuras.py mapa4
const U = lerJson(path.join(DADOS2, "sp_utilizacao.json"));

const n = (x, casas = 1) => Number(x).toFixed(casas).replace(".", ",").replace("-", "−");
const pct = (x, casas = 1) => `${n(x, casas)}%`;
const mil = (x) => Math.round(x).toLocaleString("pt-BR");

// ---------------------------------------------------------------- dados
const M_ = EV.mapas;
const HOJE = M_["hoje"], PM = M_["p-median"], HF = M_["fase2 lam=0.1"], DG = M_["fase2b central lam=0.1"];
const REC_NOME = ROB.minimax_arrependimento;               // "vidas lam=0 K=livre G=pm"
const REC = M_[REC_NOME], EQ = M_["vidas lam=1 K=livre G=pm"];
const SOL = BU.solucoes;
const LV = SOL["lam=0 K=livre"].exato;
const fracK = (k) => (SOL[`lam=0 K=${k}`].exato.vidas - HOJE.vidas) / (LV.vidas - HOJE.vidas);
const POR_MIL = D.pcr_ano / 1000;                           // vidas/ano por 1 sobrevivente /1.000 PCR
const ano = (d) => d * POR_MIL;
const RC = Object.fromEntries(ROB.por_config.map((d) => [d.config, d]));
const SIMC = SIM.medias.filter((m) => m.servico === "central");
const DIF_SIM = Math.max(...SIMC.map((m) => m.an_vidas_mean - m.sim_vidas_mean));
const CLS = CL.solucoes["classes chamadas K=livre"];
const PONTE = QS.ponte, BEQ = QS.beta_equivalente;
const QSr = (modelo, config) => QS.tabela.find((r) => r.modelo === modelo && r.config === config);
const HUFF_HOJE = QSr("huff b=4.5", "atual"), DESP_HOJE = QSr("desp SIA central", "atual");
const Q = U.q;
const TAU = n(D.tau_guarda, 0);
const V0 = MP[ROB.minimax_arrependimento], V1 = MP["vidas lam=1 K=livre G=pm"];

// confere o que o texto afirma antes de afirmar
console.assert(REC.dif_pm_usa === 0, "o mapa recomendado nao tem as USA do p-median: revise o slide do recomendado");
console.assert(REC.vidas > PM.vidas && PM.vidas > DG.vidas && DG.vidas > HF.vidas, "a ordem em vidas mudou");
console.assert(HF.huff_gini < PM.huff_gini, "Huff + 2SFCA deixou de vencer o p-median no Gini");
console.assert(BEQ["SIA baixo"] < 4.5 && 4.5 < BEQ["SIA alto"], "beta = 4,5 saiu da faixa do SIA");

// nomes dos metodos, iguais em todos os slides
const NOME = {
  "hoje": "rede de hoje", "p-median": "p-median",
  "fase2 lam=0.1": "Huff + 2SFCA (Gini)", "fase2b central lam=0.1": "despacho + 2SFCA (Gini)",
  [REC_NOME]: "despacho + vidas", "vidas lam=1 K=livre G=pm": "despacho + vidas, λ = 1",
};

// ---------------------------------------------------------------- estilo
const NAVY = "16263F", TEAL = "0F3D5C", CREAM = "F7F5F0", CARD = "EAF1F7";
const INK = "0F2B46", INK2 = "4A5568", GOLD = "D9A441";
const BLUE = "2A78D6", ORANGE = "EB6834", GREEN = "2E7D5A", GREY = "8A8F98", PURPLE = "7A5BA6";
// cor fixa por metodo em todos os graficos e tabelas
const corDe = (k) => k === "hoje" ? GREY : k === "p-median" ? BLUE : k.startsWith("fase2b") ? PURPLE :
  k.startsWith("fase2") ? ORANGE : GREEN;

const L = {
  huff: ["Huff (1964)", "https://doi.org/10.1177/002224296402800307"],
  luo: ["Luo & Wang (2003)", "https://doi.org/10.1068/b29120"],
  daskin: ["Daskin (1983)", "https://doi.org/10.1287/trsc.17.1.48"],
  revelle: ["ReVelle & Hogan (1989)", "https://doi.org/10.1287/trsc.23.3.192"],
  demaio: ["De Maio et al. (2003)", "https://doi.org/10.1067/mem.2003.266"],
  erkut: ["Erkut, Ingolfsson & Erdoğan (2008)", "https://doi.org/10.1002/nav.20267"],
  ru: ["Rockafellar & Uryasev (2000)", "https://doi.org/10.21314/JOR.2000.038"],
  sia: ["SIA/SUS · notas técnicas", "http://tabnet.datasus.gov.br/cgi/sia/qadescr.htm"],
  pref23: ["Prefeitura de SP, dez/2023", "https://prefeitura.sp.gov.br/web/saude/w/noticias/359560"],
  eureca: ["Gräsner et al. (2020), EuReCa TWO", "https://doi.org/10.1016/j.resuscitation.2019.12.042"],
  budge: ["Budge, Ingolfsson & Erkut (2009)", "https://doi.org/10.1287/opre.1080.0591"],
};

// ------------------------------------------------- exemplo de brinquedo
// o mesmo de deck_vidas.js e deck_despacho.js (formulas de huff2sfca.py)
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

const doc = new pptx();
doc.layout = "LAYOUT_WIDE";
doc.author = "Grupo MAI5003";
doc.title = "Onde colocar as ambulâncias: despacho real e vidas salvas";
const SERIF = "Cambria", SANS = "Calibri";
const M = 0.62;

let _pag = 0;
function pagina(s, cor) {
  _pag++;
  s.addText(String(_pag), { x: 12.75, y: 7.1, w: 0.45, h: 0.3, isTextBox: true,
    margin: 0, align: "right", fontFace: SANS, fontSize: 9.5, color: cor });
}
function slideClaro(titulo, sobre) {
  const s = doc.addSlide();
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
  const s = doc.addSlide();
  s.background = { color: cor };
  s.addShape(doc.ShapeType.ellipse, { x: 10.2, y: -2.2, w: 5.6, h: 5.6,
    fill: { color: "FFFFFF", transparency: 94 }, line: { color: cor } });
  pagina(s, "9FB0C4");
  return s;
}
function cartao(s, o) {
  s.addShape(doc.ShapeType.roundRect, { x: o.x, y: o.y, w: o.w, h: o.h,
    rectRadius: 0.10, fill: { color: o.fill || CARD }, line: { color: o.line || o.fill || CARD, width: o.line ? 1.5 : 0.75 } });
}
function bolha(s, t, x, y, cor, d = 0.46) {
  s.addShape(doc.ShapeType.ellipse, { x, y, w: d, h: d, fill: { color: cor }, line: { color: cor } });
  s.addText(String(t), { x, y, w: d, h: d, isTextBox: true, margin: 0, align: "center",
    valign: "middle", fontFace: SANS, fontSize: 13, bold: true, color: "FFFFFF" });
}
function texto(s, t, x, y, w, h, o = {}) {
  s.addText(t, Object.assign({ x, y, w, h, isTextBox: true, margin: 0, valign: "top",
    fontFace: SANS, fontSize: 14, color: INK2, lineSpacing: 19 }, o));
}
function conclusao(s, t, y = 6.4) {
  texto(s, t, M, y, 12.1, 0.6, { fontFace: SERIF, fontSize: 15, italic: true, color: TEAL, lineSpacing: 20 });
}
function destaque(s, x, y, w, num, rot, cor = INK, fill = "FFFFFF", h = 1.6) {
  cartao(s, { x, y, w, h, fill });
  texto(s, num, x + 0.25, y + 0.12, w - 0.5, 0.65, { fontFace: SERIF, fontSize: 30, bold: true, color: cor, valign: "middle" });
  texto(s, rot, x + 0.25, y + 0.8, w - 0.5, h - 0.85, { fontSize: 12, lineSpacing: 15 });
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
// dimensoes do PNG lidas do cabecalho IHDR, para nao distorcer as formulas
function pngDim(arq) {
  const b = fs.readFileSync(arq);
  return [b.readUInt32BE(16), b.readUInt32BE(20)];
}
function formula(s, chave, x, y, h, fase = 3) {
  const arq = (fase === 3 ? FORM3 : FORM2) + chave + ".png";
  const [pw, ph] = pngDim(arq);
  s.addImage({ path: arq, x, y, w: h * pw / ph, h });
  return h * pw / ph;
}
// tabela com estilo do projeto; o: {fontSize, rowH, destaque:[linhas], negrito:[[i,j]], corPrimeira}
function tabela(s, x, y, w, colW, cab, linhas, o = {}) {
  const fs_ = o.fontSize || 13;
  const neg = new Set((o.negrito || []).map(([i, j]) => `${i},${j}`));
  s.addTable([cab.map((t) => ({ text: t, options: { bold: true, color: "FFFFFF",
      fill: { color: TEAL }, fontSize: fs_, fontFace: SANS, align: "center", valign: "middle" } }))]
    .concat(linhas.map((r, i) => r.map((c, j) => {
      const real = (o.destaque || []).includes(i);
      return { text: c, options: {
        fontSize: fs_, fontFace: SANS, bold: (real && j === 0) || neg.has(`${i},${j}`),
        color: j === 0 && o.corPrimeira ? o.corPrimeira[i] : (real ? INK : INK2),
        align: j === 0 || o.esquerda ? "left" : "center",
        fill: { color: real ? "E6F0EA" : (i % 2 ? "FFFFFF" : CARD) } } };
    }))),
    { x, y, w, colW, rowH: o.rowH || 0.42, border: { pt: 0, color: CREAM }, valign: "middle", margin: 0.06 });
}
function barras(s, x, y, w, h, rot, val, cores, o = {}) {
  s.addChart(doc.ChartType.bar, [{ name: o.serie || "valor", labels: rot, values: val }], Object.assign({
    x, y, w, h, barDir: o.barDir || "bar", chartColors: cores, barGapWidthPct: 45,
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: o.fmt || "0.0",
    dataLabelFontSize: 11, dataLabelFontFace: SANS, dataLabelColor: INK,
    catAxisLabelFontSize: 11.5, catAxisLabelFontFace: SANS, catAxisLabelColor: INK2,
    valAxisHidden: true, valGridLine: { style: "none" }, catGridLine: { style: "none" },
    catAxisLineShow: false, valAxisMinVal: 0, showLegend: false,
    catAxisOrientation: o.barDir === "col" ? "minMax" : "maxMin",
    showTitle: !!o.titulo, title: o.titulo, titleFontFace: SANS, titleFontSize: 12, titleColor: INK,
  }, o.extra || {}));
}

// ======================================================================
// 1 — capa
{
  const s = slideEscuro(NAVY);
  texto(s, "MAI5003 · PROBABILIDADE E ESTATÍSTICA · REALOCAÇÃO DE USB E USA EM SÃO PAULO", M, 1.3, 11.5, 0.3,
    { fontSize: 11, bold: true, color: GOLD, charSpacing: 1.4 });
  texto(s, "Onde colocar as ambulâncias: despacho real e vidas salvas", M, 1.75, 11.7, 1.6,
    { valign: "middle", fontFace: SERIF, fontSize: 40, bold: true, color: "FFFFFF", lineSpacing: 46 });
  texto(s, "O que os testes com Huff + 2SFCA nos levaram a medir: quem de fato atende cada chamado e quantas vidas cada mapa de bases salva",
    M, 3.55, 11.2, 0.9, { fontFace: SERIF, fontSize: 19, italic: true, color: "C9D6E4", lineSpacing: 24 });
  texto(s, `${D.n_usb} USB e ${D.n_usa} USA · ${mil(D.n_setores)} setores censitários · ${mil(D.n_cand)} locais candidatos`,
    M, 4.75, 11, 0.4, { fontSize: 13, color: "9FB0C4" });
  texto(s, "Grupo MAI5003 · outubro de 2026", M, 6.6, 6, 0.4, { fontSize: 11, color: "8D9EB2" });
  s.addNotes("Na última apresentação mostramos o modelo de Huff com o 2SFCA e o Gini. Ao testar aqueles mapas com mais cuidado, " +
    "apareceram duas perguntas: quem de fato atende cada chamado, e o que um minuto a mais custa para o paciente. " +
    "Hoje mostramos o modelo de despacho, que responde à primeira, a função objetivo de vidas salvas, que responde à segunda, " +
    "e depois comparamos todos os métodos — inclusive os anteriores — em todas as métricas.");
}

// 2 — o modelo de despacho
{
  const s = slideClaro("O modelo de despacho: vai a ambulância livre mais próxima", "parte 1 · quem atende");
  texto(s, "Quando chega um chamado, o médico regulador percorre as ambulâncias da mais próxima para a mais distante e manda a primeira que estiver livre:",
    M, 1.5, 12.1, 0.5, { fontSize: 14 });
  const xs = [M, M + 3.1, M + 6.2, M + 9.3];
  [["1ª mais próxima", "ocupada", ORANGE], ["2ª mais próxima", "ocupada", ORANGE],
   ["3ª mais próxima", "LIVRE → vai ela", GREEN], ["4ª mais próxima", "nem é consultada", GREY]]
    .forEach((c, i) => {
      cartao(s, { x: xs[i], y: 2.1, w: 2.8, h: 0.95, fill: "FFFFFF" });
      texto(s, c[0], xs[i] + 0.2, 2.18, 2.4, 0.3, { fontSize: 14, bold: true, color: INK });
      texto(s, c[1], xs[i] + 0.2, 2.55, 2.4, 0.4, { fontSize: 14, bold: true, color: c[2] });
    });
  formula(s, "desp_geom", M + 0.2, 3.3, 0.5, 2);
  texto(s, "Se cada ambulância está ocupada uma fração q do tempo, a k-ésima mais próxima atende quando as k−1 anteriores estão ocupadas (qᵏ⁻¹) e ela está livre (1−q). A distância decide a ordem; a ocupação decide quem vai.",
    M + 4.1, 3.2, 8.0, 0.85, { fontSize: 13.5 });
  destaque(s, M, 4.25, 2.9, n(Q.central.q_usb, 2), `ocupação de cada USB: ${pct(100 * Q.central.q_usb, 0)} do tempo fora, atendendo`, GREEN);
  destaque(s, M + 3.1, 4.25, 2.9, n(Q.central.q_usa, 2), "ocupação de cada USA: menor, porque ela fica para os casos graves", GREEN);
  cartao(s, { x: M + 6.2, y: 4.25, w: 5.9, h: 1.6, fill: "FFFFFF" });
  texto(s, "De onde vem q", M + 6.45, 4.33, 5.4, 0.3, { fontSize: 14, bold: true, color: INK });
  texto(s, `Das saídas registradas no SIA/SUS em 12 meses (${mil(U.por_ano_12m.usb)} de USB e ${mil(U.por_ano_12m.usa)} de USA), pela lei de Little: saídas por hora × duração de cada saída ÷ número de ambulâncias.`,
    M + 6.45, 4.68, 5.45, 1.1, { fontSize: 12.5, lineSpacing: 16 });
  conclusao(s, "É a regra que o SAMU de fato segue, com um único parâmetro que pode ser medido nos dados públicos do SUS.", 6.15);
  fontes(s, [L.daskin, L.revelle, L.sia], "dados/fase2/sp_utilizacao.json");
  s.addNotes("O despacho descreve o que o regulador faz: ele não sorteia uma base, manda a mais próxima que estiver livre. " +
    "O modelo tem um único parâmetro, a ocupação q, e ele é medido: contamos as saídas de USB e USA da capital no SIA/SUS e aplicamos a lei de Little. " +
    "A duração de cada saída não está no SIA; usamos 70 minutos no cenário central e testamos 45 e 100 depois. " +
    "É o mesmo raciocínio dos modelos clássicos de cobertura com ocupação, de Daskin e de ReVelle e Hogan.");
}

// 3 — exemplo didatico: Huff x despacho num setor da periferia
{
  const s = slideClaro("Um exemplo: o Huff esconde a demora da periferia", "parte 1 · quem atende");
  const h = huffP(PER), d = despP(PER, Q_EX), eh = esp(h, PER), ed = esp(d, PER);
  const hc = huffP(CEN), dc = despP(CEN, Q_EX);
  const lista = (ts) => ts.join(", ").replace(/, (\d+)$/, " e $1");
  texto(s, `Um setor da periferia tem USAs a ${lista(PER)} min. Em média, quanto tempo até uma USA chegar? Cada modelo dá a cada USA uma chance de ser a que atende; o tempo esperado é a média dos tempos, ponderada por essas chances.`,
    M, 1.45, 12.1, 0.65, { fontSize: 14 });

  // painel principal: o setor periferico
  cartao(s, { x: M, y: 2.2, w: 7.7, h: 3.85, fill: "FFFFFF" });
  texto(s, `Setor periférico · USAs a ${lista(PER)} min`, M + 0.25, 2.28, 7.2, 0.35, { fontSize: 15, bold: true, color: INK });
  s.addChart(doc.ChartType.bar, [
    { name: "Huff (β = 4,5)", labels: PER.map((t) => `USA a ${t} min`), values: h.map((p) => 100 * p) },
    { name: `despacho (q = ${n(Q_EX, 2)})`, labels: PER.map((t) => `USA a ${t} min`), values: d.map((p) => 100 * p) }], {
    x: M + 0.15, y: 2.62, w: 7.4, h: 1.95, barDir: "col", barGrouping: "clustered", chartColors: [ORANGE, GREEN], barGapWidthPct: 70,
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0\"%\"", dataLabelFontSize: 11, dataLabelFontFace: SANS, dataLabelColor: INK,
    catAxisLabelFontSize: 11.5, catAxisLabelFontFace: SANS, catAxisLabelColor: INK2, valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 125,
    valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: true, legendPos: "t", legendFontSize: 11, legendFontFace: SANS,
  });
  const conta = (p) => p.map((v, i) => `${n(100 * v, 0)}% × ${PER[i]}`).join(" + ");
  texto(s, [
    { text: "Huff: ", options: { bold: true, color: ORANGE } }, { text: `${conta(h)} ≈ `, options: { color: INK2 } },
    { text: `${n(eh, 2)} min`, options: { bold: true, color: ORANGE, breakLine: true } },
    { text: "Despacho: ", options: { bold: true, color: GREEN } }, { text: `${conta(d)} ≈ `, options: { color: INK2 } },
    { text: `${n(ed, 2)} min`, options: { bold: true, color: GREEN } }],
    M + 0.25, 4.62, 7.2, 0.62, { fontSize: 13.5, lineSpacing: 18 });
  texto(s, `→ O Huff calcula como se a USA de ${PER[0]} min viesse sempre e esconde ${n(ed - eh, 2)} min de demora.`,
    M + 0.25, 5.35, 7.2, 0.6, { fontSize: 13.5, bold: true, color: INK, lineSpacing: 17 });

  // lateral: por que, e o centro em uma linha
  cartao(s, { x: 8.6, y: 2.2, w: 4.12, h: 2.5, fill: "FBEAE7" });
  texto(s, "Por que o Huff erra aqui", 8.85, 2.3, 3.7, 0.3, { fontSize: 14, bold: true, color: ORANGE });
  texto(s, `No Huff, a chance cai com a distância: a USA de ${PER[1]} min recebe ${n(100 * h[1], 3)}%, quase nunca vem. No despacho, a de ${PER[0]} min está ocupada ${pct(100 * Q_EX, 0)} do tempo; nessas vezes a de ${PER[1]} min é a livre mais próxima e vai: ${pct(100 * d[1], 0)} dos chamados.`,
    8.85, 2.65, 3.7, 2.0, { fontSize: 12.5, lineSpacing: 16 });
  cartao(s, { x: 8.6, y: 4.85, w: 4.12, h: 1.2, fill: "FFFFFF" });
  texto(s, "E no centro?", 8.85, 4.92, 3.7, 0.3, { fontSize: 13, bold: true, color: INK });
  texto(s, `USAs a ${lista(CEN)} min: ${n(esp(hc, CEN), 2)} min no Huff, ${n(esp(dc, CEN), 2)} no despacho. O erro é pequeno e no sentido oposto.`,
    8.85, 5.22, 3.7, 0.8, { fontSize: 12, lineSpacing: 15 });

  conclusao(s, "Na periferia, onde as USAs estão longe umas das outras, o Huff faz o setor parecer mais bem servido do que é — justamente onde a equidade importa. O despacho põe essa demora no cálculo.", 6.15);
  fontes(s, [L.huff, L.daskin], `q = ${n(Q_EX, 2)} é a ocupação equivalente a β = 4,5; se todas estão ocupadas, o chamado conta para a mais próxima (por isso ${pct(100 * d[0], 0)}, não ${pct(100 * (1 - Q_EX), 0)})`);
  s.addNotes("Os dois modelos respondem à mesma pergunta: em média, quanto tempo até uma USA chegar a este setor da periferia? Cada um dá a cada USA uma chance de ser a que atende, e o tempo esperado é a média ponderada. " +
    `No Huff, a chance vem da distância. A USA de ${PER[1]} min recebe peso quase zero só por estar longe, e o Huff calcula como se a de ${PER[0]} min viesse sempre: ${n(eh, 2)} min. ` +
    `No despacho, a distância só decide a ordem. A de ${PER[0]} min vai quando está livre; quando está ocupada, o que acontece ${pct(100 * Q_EX, 0)} do tempo, vai a de ${PER[1]} min. ` +
    `Somando, o tempo esperado sobe para ${n(ed, 2)} min: ${n(ed - eh, 1)} min a mais do que o Huff dizia. ` +
    "No centro o erro é pequeno e vai no sentido oposto, porque as USAs estão perto umas das outras. O problema do Huff está na periferia, que é onde o projeto quer medir desigualdade. " +
    "Detalhe: q = 0,27 não é a ocupação medida no SIA; é a que torna o despacho comparável ao Huff com β = 4,5.");
}

// 4 — cada minuto custa vidas
{
  const s = slideClaro("A prioridade é salvar vidas: quanto vale cada minuto", "parte 2 · a função objetivo");
  formula(s, "g_geral", M + 0.1, 1.5, 0.6);
  texto(s, "Com o despacho, cada setor tem uma distribuição do tempo de chegada. Até aqui resumíamos essa distribuição pelo tempo médio; a pergunta é quanto vale chegar em t minutos.",
    M, 2.2, 6.0, 0.85, { fontSize: 13 });
  const R = [
    ["g(t) = t", "tempo médio", "cada minuto pesa igual, chegue a ambulância em 3 ou em 13 min", ORANGE],
    ["g(t) = 1[t ≤ τ]", "cobertura", `só importa chegar antes do limite (${TAU} min); 5 ou 14 min dão no mesmo`, PURPLE],
    ["g(t) = s(t)", "sobrevida", "o peso de cada minuto vem do que se observou em 9.273 paradas cardíacas", GREEN],
  ];
  R.forEach((r, i) => {
    const y = 3.1 + i * 0.97, ult = i === R.length - 1, h = ult ? 1.08 : 0.88;
    cartao(s, { x: M, y, w: 6.0, h, fill: "FFFFFF" });
    texto(s, r[0], M + 0.2, y + 0.08, 1.95, h - 0.16, { fontFace: SERIF, fontSize: 16, bold: true, color: r[3], valign: "middle" });
    texto(s, r[1], M + 2.2, y + 0.07, 3.7, 0.3, { fontSize: 13.5, bold: true, color: INK });
    if (ult) {
      // a curva de De Maio et al. (2003), a mesma de sobrevida.py
      formula(s, "sobrev", M + 2.2, y + 0.4, 0.6);
      texto(s, "curva medida em 9.273 paradas cardíacas (De Maio, 2003)", M + 4.85, y + 0.4, 1.05, 0.62, { fontSize: 10, lineSpacing: 12, valign: "middle" });
    } else texto(s, r[2], M + 2.2, y + 0.38, 3.7, 0.5, { fontSize: 11.5, lineSpacing: 14 });
  });
  // tres reguas, normalizadas em 1 no tempo zero: so a forma importa
  const ts = D.curva_t, s0 = D.curva_s[0], tmax = ts[ts.length - 1];
  s.addChart(doc.ChartType.line, [
    { name: "tempo médio (reta)", labels: ts.map((t) => (t % 5 === 0 ? String(t) : "")), values: ts.map((t) => 1 - t / tmax) },
    { name: `cobertura (limite de ${TAU} min)`, labels: ts.map(String), values: ts.map((t) => (t <= D.tau_guarda ? 1 : 0)) },
    { name: "sobrevida (curva medida)", labels: ts.map(String), values: D.curva_s.map((v) => v / s0) }], {
    x: M + 6.3, y: 1.45, w: 5.8, h: 3.6, chartColors: [ORANGE, PURPLE, GREEN], lineSize: 2.5, lineDataSymbol: "none",
    showTitle: true, title: "quanto vale chegar em t minutos (1 = chegar já)", titleFontFace: SANS, titleFontSize: 12.5, titleColor: INK,
    catAxisLabelFontSize: 11, catAxisLabelFontFace: SANS, catAxisLabelColor: INK2, catAxisLabelFrequency: 1,
    catAxisTitle: "minutos até a chegada", showCatAxisTitle: true, catAxisTitleFontSize: 11, catAxisTitleColor: INK2,
    valAxisLabelFontSize: 11, valAxisLabelFontFace: SANS, valAxisLabelColor: INK2, valAxisLabelFormatCode: "0.0",
    valAxisMinVal: 0, valAxisMaxVal: 1.05, valGridLine: { color: "E3E0D8", size: 0.5 }, catGridLine: { style: "none" },
    showLegend: true, legendPos: "b", legendFontSize: 11, legendFontFace: SANS,
  });
  [["5 min", D.s5], ["9 min", D.s9], ["15 min", D.s15]].forEach((c, i) => {
    const x = M + 6.3 + i * 1.97;
    cartao(s, { x, y: 5.15, w: 1.85, h: 0.95, fill: "FFFFFF" });
    texto(s, pct(100 * c[1]), x + 0.12, 5.18, 1.6, 0.48, { fontFace: SERIF, fontSize: 20, bold: true, color: GREEN, valign: "middle" });
    texto(s, `sobrevivem se o DEA chega em ${c[0]}`, x + 0.12, 5.62, 1.65, 0.46, { fontSize: 10.5, lineSpacing: 12 });
  });
  conclusao(s, `A parada cardíaca é a emergência em que se sabe medir quanto cada minuto custa: entre 9 e 10 min a chance de sobreviver cai ${pct(100 * D.queda_min, 0)}. Os primeiros minutos valem muito mais que os últimos.`, 6.25);
  fontes(s, [L.daskin, L.erkut, L.demaio], "deck_vidas.json");
  s.addNotes("Esta é a ideia central da função objetivo. O despacho dá, para cada setor, a chance de cada base atender — portanto uma distribuição do tempo de chegada. " +
    "Para comparar mapas precisamos resumir essa distribuição numa média de alguma função g do tempo. O tempo médio que usávamos é o caso em que g é uma reta: cada minuto pesa igual. " +
    "A cobertura, o caso em que g é um degrau. A sobrevida usa a curva medida em 9.273 paradas cardíacas no Canadá (De Maio, 2003). " +
    "Se a curva fosse reta, os dois objetivos escolheriam o mesmo mapa; como os primeiros minutos valem mais, os mapas mudam. " +
    "Erkut, Ingolfsson e Erdoğan (2008) propuseram exatamente isso para ambulâncias: incorporar a função de sobrevivência aos modelos de cobertura (leitura do resumo do artigo).");
}

// 5 — a funcao objetivo
{
  const s = slideClaro("A função objetivo: vidas na cidade e nos 10% mais mal servidos", "parte 2 · a função objetivo");
  cartao(s, { x: M, y: 1.5, w: 7.3, h: 1.1, fill: "FFFFFF", line: GREEN });
  formula(s, "objetivo", M + 0.35, 1.78, 0.5);
  const P = [
    ["vidas", "sobreviventes esperados por 1.000 paradas cardíacas na cidade: a curva s(t) aplicada ao tempo de cada base, pela chance de ela ser a primeira livre a chegar.", GREEN],
    ["CVaR₁₀", "a mesma medida, só entre os 10% da população mais mal servidos. Sobe apenas se a situação de quem está pior melhorar.", GREEN],
    ["λ", "o peso da equidade. Com λ = 1, um ganho para quem está nos 10% piores pesa 11 vezes mais que o mesmo ganho para os demais.", GOLD],
  ];
  P.forEach((p, i) => {
    const y = 2.9 + i * 1.12;
    texto(s, p[0], M + 0.1, y, 1.2, 0.35, { fontFace: SERIF, fontSize: 17, bold: true, color: p[2] });
    texto(s, p[1], M + 1.35, y + 0.02, 5.95, 1.0, { fontSize: 14, lineSpacing: 18 });
  });
  cartao(s, { x: 8.3, y: 1.5, w: 4.42, h: 2.3, fill: "FFFFFF" });
  texto(s, "Sujeito a", 8.55, 1.6, 4.0, 0.3, { fontSize: 14, bold: true, color: INK });
  texto(s, [
    { text: `a frota de hoje: ${D.n_usb} USB e ${D.n_usa} USA`, options: { bullet: true, breakLine: true } },
    { text: `no máximo ${D.cap} unidades por local`, options: { bullet: true, breakLine: true } },
    { text: "no máximo K ambulâncias mudam de base", options: { bullet: true, breakLine: true } },
    { text: `pisos: a chance de USB no chamado básico e de USA no grave, em até ${TAU} min, não pode cair`, options: { bullet: true } }],
    8.55, 1.95, 4.0, 1.8, { fontSize: 12, paraSpaceAfter: 3, lineSpacing: 15 });
  cartao(s, { x: 8.3, y: 3.95, w: 4.42, h: 2.15, fill: "FFF4DC" });
  texto(s, "Tempos calibrados", 8.55, 4.05, 4.0, 0.3, { fontSize: 14, bold: true, color: INK });
  texto(s, `As ruas em trânsito livre davam ${n(CAL.et_grave_bruto)} min até o chamado grave; a Prefeitura informa ~${n(CAL.alvo_grave_min, 0)}. Usamos ${n(CAL.atraso, 0)} min até a saída + tempo de ruas × ${n(CAL.fator, 2)}: a sobrevida depende do relógio certo.`,
    8.55, 4.4, 4.0, 1.6, { fontSize: 12.5, color: INK, lineSpacing: 16 });
  conclusao(s, "Vidas e CVaR₁₀ estão na mesma unidade — sobreviventes por 1.000 paradas cardíacas —, então a soma com peso λ tem leitura direta.", 6.3);
  fontes(s, [L.ru, L.pref23], "deck_evolucao.json, v1_calibracao.json");
  s.addNotes("A função objetivo tem duas parcelas na mesma unidade. A primeira é a média da cidade. A segunda é a média dos 10% mais mal servidos, o CVaR, uma medida que vem de finanças. " +
    "Ela ocupa o lugar que antes era do Gini. O Gini mede se os setores são parecidos, e pode melhorar sem que ninguém melhore; o CVaR só melhora se os piores melhorarem. O próximo slide mostra o que isso muda nos números. " +
    "As restrições mantêm a frota de hoje, limitam quantas ambulâncias mudam de base e impedem que o atendimento dos outros chamados piore. " +
    "Os tempos foram calibrados para reproduzir os 20 minutos que a Prefeitura informa para os casos mais graves, porque a sobrevida depende do relógio certo.");
}

// 6 — todos os metodos, todas as metricas
{
  const s = slideClaro("Todos os métodos medidos por todas as métricas", "parte 3 · comparação");
  const cfg = ["hoje", "fase2 lam=0.1", "fase2b central lam=0.1", "p-median", REC_NOME, "vidas lam=1 K=livre G=pm"];
  const cols = [["huff_tempo", -1], ["huff_gini", -1], ["desp_p10_usa10", 1], ["vidas", 1], ["cvar10", 1]];
  const neg = [];
  cols.forEach(([k, sinal], j) => {
    const best = Math.max(...cfg.map((c) => sinal * M_[c][k]));
    cfg.forEach((c, i) => { if (Math.abs(sinal * M_[c][k] - best) < 1e-9) neg.push([i, j + 1]); });
  });
  const xs = [M + 3.55, M + 6.15, M + 7.85];
  [["métricas anteriores", 2.6, ORANGE], ["despacho", 1.7, PURPLE], ["vidas salvas", 2.8, GREEN]].forEach((g, i) => {
    s.addShape(doc.ShapeType.rect, { x: xs[i] + 0.05, y: 1.48, w: g[1] - 0.1, h: 0.05, fill: { color: g[2] }, line: { color: g[2] } });
    texto(s, g[0], xs[i], 1.55, g[1], 0.28, { fontSize: 11.5, bold: true, color: g[2], align: "center" });
  });
  tabela(s, M, 1.9, 12.1, [3.55, 1.3, 1.3, 1.7, 1.4, 1.4, 1.45],
    ["método", "E[T] (min)", "Gini USA", "10% piores: USA ≤ 10 min", "vidas /1.000", "CVaR₁₀", "ambulâncias movidas"],
    cfg.map((c) => {
      const v = M_[c];
      return [c === REC_NOME ? `${NOME[c]}, λ = 0` : NOME[c], n(v.huff_tempo, 2), n(v.huff_gini, 3), pct(v.desp_p10_usa10), n(v.vidas), n(v.cvar10), String(v.movidas)];
    }), { fontSize: 12.5, rowH: [0.55, 0.45, 0.45, 0.45, 0.45, 0.45, 0.45], destaque: [4], negrito: neg,
      corPrimeira: cfg.map(corDe) });
  texto(s, "Negrito: melhor valor da coluna. E[T] e Gini (Huff, β = 4,5): quanto menor, melhor; as demais: quanto maior, melhor. Vidas e CVaR₁₀ em sobreviventes por 1.000 paradas cardíacas.",
    M, 5.05, 12.1, 0.3, { fontSize: 10.5, color: GREY });
  const T = [
    ["Nas métricas anteriores", `Huff + 2SFCA tem o menor Gini (${n(HF.huff_gini, 3)}); no tempo médio, os quatro métodos otimizados ficam a menos de ${n(Math.ceil(60 * (Math.max(HF.huff_tempo, DG.huff_tempo, PM.huff_tempo, REC.huff_tempo) - Math.min(HF.huff_tempo, DG.huff_tempo, PM.huff_tempo, REC.huff_tempo))), 0)} s uns dos outros.`, ORANGE, "FBEAE7"],
    ["Por que a equidade é medida pelos 10% piores", `Com o despacho, os 10% mais mal servidos do Huff + 2SFCA (menor Gini) ficam quase todos entre 10 e 15 min. ` +
      `Em até 15 min, ${Math.abs(HF.desp_p10_usa15 - PM.desp_p10_usa15) < 0.5 ? `ele e o p-median empatam (${pct(HF.desp_p10_usa15)})` : `${pct(HF.desp_p10_usa15)} contra ${pct(PM.desp_p10_usa15)} no p-median`}; ` +
      `em até 10 min, o p-median alcança ${pct(PM.desp_p10_usa10)} e o do Gini, ${pct(HF.desp_p10_usa10)}. O Gini iguala a oferta por habitante, mas não vê esses minutos.`, GREEN, "E6F0EA"],
  ];
  T.forEach((t, i) => {
    const x = M + i * 6.2;
    cartao(s, { x, y: 5.45, w: 5.9, h: 1.45, fill: t[3] });
    texto(s, t[0], x + 0.25, 5.52, 5.4, 0.3, { fontSize: 13.5, bold: true, color: t[2] });
    texto(s, t[1], x + 0.25, 5.83, 5.4, 1.05, { fontSize: i ? 11.5 : 12.5, color: INK, lineSpacing: i ? 14.5 : 16 });
  });
  fontes(s, [], "deck_evolucao.json (E[T] e Gini: Huff; 10% piores: despacho; vidas e CVaR₁₀: v2_reavaliacao, v3_busca)");
  s.addNotes("Aqui está a comparação completa. Cada linha é um método; cada grupo de colunas, um conjunto de métricas: as que usávamos (tempo médio e Gini pelo Huff), " +
    "a cobertura dos 10% piores pelo despacho, e as de vidas salvas. Os métodos: Huff + 2SFCA com Gini é o que apresentamos antes; " +
    "despacho + 2SFCA é o mesmo otimizador com o despacho no lugar do Huff; o p-median é a solução clássica; despacho + vidas é a função objetivo nova, com dois pesos de equidade. " +
    "Leitura: nas métricas anteriores, Huff + 2SFCA continua com o menor Gini, e o tempo médio quase não separa os métodos. " +
    "Na coluna dos 10% piores aparece por que a equidade passou a ser medida assim: no mapa de menor Gini, os piores ficam quase todos entre 10 e 15 minutos. " +
    "Em 15 minutos ele empata com o p-median, mas em 10 quase não chega, enquanto o p-median alcança um terço deles. " +
    "Em vidas, a ordem é outra, e o próximo slide explica o papel do p-median nessa ordem.");
}

// 7 — o p-median nas duas metricas
{
  const s = slideClaro("O p-median: perdia nas métricas anteriores, ganha em vidas", "parte 3 · comparação");
  texto(s, "O p-median põe as bases onde o tempo médio até a ambulância mais próxima é o menor possível. Ele era a referência que o Huff + 2SFCA superava — e superava mesmo, no Gini. Medido em vidas, o resultado se inverte:",
    M, 1.5, 12.1, 0.75, { fontSize: 14 });
  tabela(s, M, 2.35, 7.4, [3.0, 1.45, 1.45, 1.5], ["", "Huff + 2SFCA", "p-median", "diferença"],
    [["Gini da USA (menor é melhor)", n(HF.huff_gini, 3), n(PM.huff_gini, 3), `${n(PM.huff_gini / HF.huff_gini, 1)}× pior`],
     ["tempo médio, Huff (min)", n(HF.huff_tempo, 2), n(PM.huff_tempo, 2), `${n(60 * (PM.huff_tempo - HF.huff_tempo), 0)} s`],
     ["vidas por 1.000 paradas", n(HF.vidas), n(PM.vidas), `+${n(PM.vidas - HF.vidas)}`],
     ["vidas nos 10% piores (CVaR₁₀)", n(HF.cvar10), n(PM.cvar10), `+${n(PM.cvar10 - HF.cvar10)}`],
     ["10% piores: USA em até 10 min", pct(HF.desp_p10_usa10), pct(PM.desp_p10_usa10), `+${n(PM.desp_p10_usa10 - HF.desp_p10_usa10)} p.p.`]],
    { fontSize: 12.5, rowH: 0.45, destaque: [2, 3, 4], corPrimeira: [ORANGE, ORANGE, GREEN, GREEN, GREEN] });
  texto(s, "Laranja: métricas anteriores. Verde: métricas de vidas e dos 10% piores.", M, 5.1, 7.4, 0.3, { fontSize: 10.5, color: GREY });
  cartao(s, { x: 8.3, y: 2.35, w: 4.42, h: 1.55, fill: "E6F0EA" });
  texto(s, `+${n(PM.vidas - HF.vidas)} por 1.000`, 8.55, 2.42, 4.0, 0.6, { fontFace: SERIF, fontSize: 26, bold: true, color: BLUE, valign: "middle" });
  texto(s, `ganho do p-median sobre o Huff + 2SFCA em vidas: ordem de ${n(ano(PM.vidas - HF.vidas), 0)} vidas por ano na capital`, 8.55, 3.05, 4.0, 0.8, { fontSize: 12, lineSpacing: 15 });
  cartao(s, { x: 8.3, y: 4.05, w: 4.42, h: 2.05, fill: "FFFFFF" });
  texto(s, "Por que se inverte", 8.55, 4.13, 4.0, 0.3, { fontSize: 14, bold: true, color: INK });
  texto(s, "A sobrevida premia chegar cedo, e é isso que o p-median otimiza: a unidade mais próxima, que no despacho é a que vai na maioria das vezes. O Gini iguala ambulâncias por habitante, o que não garante chegar cedo.",
    8.55, 4.47, 4.0, 1.6, { fontSize: 12, lineSpacing: 15 });
  conclusao(s, `O despacho + 2SFCA fica perto (${n(DG.vidas)}), mas ainda abaixo do p-median. Por isso a otimização de vidas parte do p-median e procura melhorá-lo.`, 6.3);
  fontes(s, [L.eureca], "deck_evolucao.json; vidas por ano com a incidência do EuReCa TWO (deck_vidas.json)");
  s.addNotes(`Este ponto precisa ficar claro. Na apresentação anterior, o p-median era a referência e o Huff + 2SFCA o superava: Gini ${n(PM.huff_gini / HF.huff_gini, 1)} vezes menor com praticamente o mesmo tempo médio. ` +
    `Nas métricas de vidas o resultado se inverte: o p-median salva ${n(PM.vidas - HF.vidas)} pessoas a mais por 1.000 paradas cardíacas — algo como ${n(ano(PM.vidas - HF.vidas), 0)} vidas por ano na capital, com a incidência de um registro europeu —, ` +
    `tem CVaR maior (${n(PM.cvar10)} contra ${n(HF.cvar10)}) e dá aos 10% piores ${pct(PM.desp_p10_usa10)} de chance de USA em 10 minutos, contra ${pct(HF.desp_p10_usa10)}. ` +
    "A razão: a sobrevida cai rápido nos primeiros minutos, e o p-median é justamente quem minimiza o tempo até a unidade mais próxima. " +
    "O Gini equilibrava a oferta por habitante, não o tempo de chegada. Esse resultado é o que nos levou a usar o p-median como ponto de partida da busca por vidas.");
}

// 8 — os quatro mapas
{
  const s = slideClaro("Onde ficam as ambulâncias em cada mapa", "parte 3 · resultado");
  const [pw, ph] = pngDim(FIG3 + "v05_mapa4.png");
  const w = 11.0, h = w * ph / pw;
  s.addImage({ path: FIG3 + "v05_mapa4.png", x: (13.333 - w) / 2, y: 1.45, w, h });
  const yl = 1.45 + h + 0.05;
  texto(s, "Cor do setor: sobreviventes por 1.000 paradas cardíacas (mais escuro = mais sobrevida). Círculos: USB; triângulos: USA; o tamanho indica quantas unidades há no local.",
    M, yl, 12.1, 0.3, { fontSize: 11, color: GREY });
  const H0 = MP["hoje"], HG = MP["fase2 lam=0.1"], V0 = MP[REC_NOME], V1 = MP["vidas lam=1 K=livre G=pm"];
  const C = [
    ["Bases mais espalhadas", `${H0.locais} locais hoje, ${HG.locais} no Huff + 2SFCA e ${V0.locais} nos mapas de vidas: uma ambulância por local.`],
    ["As mesmas USA", `Nos dois mapas de vidas, as ${D.n_usa} USA ficam nos locais do p-median, por causa do piso do chamado grave.`],
    ["λ = 0 × λ = 1", `Diferem só nas USB. Com λ = 1, o mapa troca ${n(V0.vidas - V1.vidas)} vidas por 1.000 na média por +${n(V1.cvar10 - V0.cvar10)} nos 10% piores (tabela do slide 6).`],
  ];
  C.forEach((c, i) => {
    const x = M + i * 4.1, y = yl + 0.42;
    cartao(s, { x, y, w: 3.85, h: 6.95 - y, fill: "FFFFFF" });
    texto(s, c[0], x + 0.2, y + 0.07, 3.45, 0.3, { fontSize: 13, bold: true, color: INK });
    texto(s, c[1], x + 0.2, y + 0.38, 3.45, 6.95 - y - 0.42, { fontSize: 11.5, lineSpacing: 14.5 });
  });
  s.addNotes("Os quatro mapas, com a mesma escala de cor. O fundo é a sobrevida a uma parada cardíaca em cada setor; os símbolos são as bases. " +
    `Da rede de hoje para os mapas otimizados, as bases se espalham: ${H0.locais}, ${HG.locais} e ${V0.locais} locais, e o fundo escurece — mais sobrevida. ` +
    "Os dois mapas de vidas têm as USA nos mesmos locais do p-median, porque o piso de cobertura do chamado grave as prende ali; eles diferem só nas USB. " +
    `Os números acima de cada mapa são os da tabela: vidas na cidade e nos 10% piores. ` +
    `Entre λ = 0 e λ = 1 mudam só USB: com peso na equidade, o otimizador abre mão de ${n(V0.vidas - V1.vidas)} vidas por mil na média para ganhar ${n(V1.cvar10 - V0.cvar10)} nos 10% mais mal servidos. ` +
    "Qual dos dois usar é uma escolha de valores; o modelo mostra o preço de cada um.");
  fontes(s, [], "figs/fase3/v05_mapa4.png, v05_mapa4.json (figuras.py mapa4)");
}

// 9 — conclusoes
{
  const s = slideEscuro(TEAL);
  texto(s, "CONCLUSÕES", M, 0.6, 11, 0.3, { fontSize: 11, bold: true, color: GOLD, charSpacing: 1.4 });
  texto(s, "O que levar desta apresentação", M, 1.0, 11, 0.8, { fontFace: SERIF, fontSize: 30, bold: true, color: "FFFFFF", valign: "middle" });
  const V = [
    ["Despacho", `Descreve a regra real do SAMU com um parâmetro medido no SUS, mostra a demora da periferia e confirma o β = 4,5 que usávamos (faixa de ${n(BEQ["SIA baixo"], 1)} a ${n(BEQ["SIA alto"], 1)} min).`],
    ["Vidas como prioridade", "A sobrevida é a mesma média do tempo médio, com cada minuto pesado pelo que custa em vidas; a equidade passa a olhar os 10% mais mal servidos."],
    ["Comparação", `Huff + 2SFCA segue com o menor Gini; em vidas, o p-median supera o Huff + 2SFCA em ${n(PM.vidas - HF.vidas)} por 1.000, e despacho + vidas soma mais ${n(REC.vidas - PM.vidas)} partindo do p-median.`],
    ["Rede de hoje", `De ${n(HOJE.vidas)} para ${n(REC.vidas)} sobreviventes por 1.000 paradas cardíacas: ordem de ${n(ano(REC.vidas - HOJE.vidas), 0)} vidas por ano, com mudança possível em etapas.`],
  ];
  V.forEach((v, i) => {
    const y = 1.95 + i * 1.02;
    bolha(s, i + 1, M, y, GREEN, 0.52);
    texto(s, v[0], M + 0.75, y - 0.05, 2.9, 0.62, { fontSize: 15.5, bold: true, color: "8FD3AE", valign: "middle" });
    texto(s, v[1], M + 3.7, y - 0.2, 8.4, 0.92, { fontSize: 13.5, color: "E7ECF2", valign: "middle", lineSpacing: 17 });
  });
  texto(s, "Próximos passos: ocupação dependente entre ambulâncias vizinhas (hipercubo aproximado, Budge, Ingolfsson & Erkut, 2009) e demanda por incidência, não por população.",
    M, 6.1, 12.0, 0.7, { fontFace: SERIF, fontSize: 15, italic: true, color: "C9D6E4", lineSpacing: 19 });
  s.addNotes("Fechando. O despacho torna o modelo de quem atende fiel ao SAMU e mensurável. A função objetivo coloca a sobrevida no centro, sem perder a equidade. " +
    "Na comparação, cada métrica conta uma parte: o Huff + 2SFCA equilibra a oferta; o p-median e o despacho + vidas salvam mais. " +
    "E o ganho sobre a rede de hoje é grande, da ordem de uma centena de vidas por ano, mesmo com mudanças graduais.");
}

// 10 — limitacoes
{
  const s = slideClaro("Limitações: o que ainda é hipótese", "para discussão");
  const lim = [
    ["Uma curva de sobrevida", "De Ontário, anos 1990, paradas de causa cardíaca. O nível absoluto em São Paulo pode ser outro; a comparação entre mapas é mais confiável que o número de vidas."],
    ["Vidas por ano", "Dependem de uma incidência de parada cardíaca europeia (EuReCa TWO), testada com metade e 1,5 vez o valor. São ordem de grandeza, não previsão."],
    ["Calibração em um ponto", `O fator de trânsito vem de um único número da Prefeitura (${n(CAL.alvo_grave_min, 0)} min nos casos mais graves); os cenários testam trânsito livre e mais pesado.`],
    ["Duração das saídas", "O SIA conta saídas, não quanto tempo cada uma durou; entra como cenário (45/70/100 min)."],
    ["Demanda", "Paradas cardíacas onde as pessoas moram, sem idade nem população de dia."],
    ["Otimalidade", "A busca acha o ótimo nos casos pequenos, onde dá para conferir; no caso real não há certificado."],
  ];
  lim.forEach((l, i) => {
    const col = i % 2, lin = Math.floor(i / 2);
    const x = M + col * 6.2, y = 1.55 + lin * 1.5;
    bolha(s, i + 1, x, y, ORANGE);
    texto(s, l[0], x + 0.62, y - 0.02, 5.3, 0.3, { fontSize: 14, bold: true, color: INK });
    texto(s, l[1], x + 0.62, y + 0.3, 5.3, 1.05, { fontSize: 12.5, lineSpacing: 16 });
  });
  conclusao(s, "Não há validação externa: nenhum dado público traz tempos de resposta observados por bairro para comparar com o modelo.", 6.2);
  fontes(s, [L.demaio, L.eureca, L.pref23]);
}

// 11 — referencias
{
  const s = slideClaro("Referências", "fontes");
  const refs = [
    "Huff, D. (1964). Defining and estimating a trading area. Journal of Marketing 28(3). doi:10.1177/002224296402800307",
    "Luo, W. & Wang, F. (2003). Measures of spatial accessibility to health care in a GIS environment. Environment and Planning B 30(6). doi:10.1068/b29120",
    "Daskin, M. (1983). A maximum expected covering location model. Transportation Science 17(1). doi:10.1287/trsc.17.1.48",
    "ReVelle, C. & Hogan, K. (1989). The maximum availability location problem. Transportation Science 23(3). doi:10.1287/trsc.23.3.192",
    "Erkut, E., Ingolfsson, A. & Erdoğan, G. (2008). Ambulance location for maximum survival. Naval Research Logistics 55(1). doi:10.1002/nav.20267",
    "De Maio, V. J. et al. (2003). Optimal defibrillation response intervals for maximum out-of-hospital cardiac arrest survival rates. Ann. Emerg. Med. 42(2). doi:10.1067/mem.2003.266",
    "Rockafellar, R. T. & Uryasev, S. (2000). Optimization of conditional value-at-risk. Journal of Risk 2(3). doi:10.21314/JOR.2000.038",
    "Budge, S., Ingolfsson, A. & Erkut, E. (2009). Approximating vehicle dispatch probabilities for emergency service systems. Operations Research 57(1). doi:10.1287/opre.1080.0591",
    "Gräsner, J.-T. et al. (2020). Survival after out-of-hospital cardiac arrest in Europe — EuReCa TWO. Resuscitation 148. doi:10.1016/j.resuscitation.2019.12.042",
    "Dados: IBGE, Censo 2022 · CNES/DATASUS · SIA/SUS (PASP, SIGTAP) · OpenStreetMap · Prefeitura de SP (21/12/2023). Relatórios completos: fase2_sao_paulo/docs/ e fase3_vidas/docs/.",
  ];
  texto(s, refs.map((r, i) => ({ text: r, options: { bullet: true, breakLine: i < refs.length - 1 } })),
    M, 1.55, 12.1, 5.3, { fontSize: 12, paraSpaceAfter: 6, lineSpacing: 15 });
}

doc.writeFile({ fileName: SAIDA }).then(() => console.log("-> " + SAIDA + ` (${_pag} slides)`));
