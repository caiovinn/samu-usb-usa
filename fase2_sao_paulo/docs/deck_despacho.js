const fs = require("fs");
const path = require("path");
const pptx = require("pptxgenjs");

/* Deck da fase 2b — "quem atende o chamado?": do Huff ao despacho real do
 * SAMU, passo a passo, para quem nunca viu as fórmulas.
 *
 *     node fase2_sao_paulo/docs/deck_despacho.js
 *
 * Mesma família visual de deck_didatico.js. Todo número de resultado vem dos
 * JSONs de dados/fase2/ (sp_utilizacao, sp_q_sens, sp_q_sweep, sp_simulacao,
 * sp_resultado); os exemplos de brinquedo são calculados aqui com as mesmas
 * fórmulas de fase2_sao_paulo/modelo/huff2sfca.py (huff, despacho).
 */

const RAIZ = path.join(__dirname, "..", "..");
const DADOS = path.join(RAIZ, "dados", "fase2");
const FIG = path.join(RAIZ, "figs", "fase2") + path.sep;
const FORMULAS = path.join(FIG, "formulas") + path.sep;
const SAIDA = path.join(__dirname, "apresentacao_despacho_sp.pptx");

const lerJson = (nome) => JSON.parse(fs.readFileSync(path.join(DADOS, nome), "utf-8"));
const U = lerJson("sp_utilizacao.json");
const QS = lerJson("sp_q_sens.json");
const SW = lerJson("sp_q_sweep.json");
const SIM = lerJson("sp_simulacao.json");
const RES = lerJson("sp_resultado.json");

const n = (x, casas = 2) => Number(x).toFixed(casas).replace(".", ",").replace("-", "−");
const pct = (x, casas = 0) => `${n(x, casas)}%`;
const mil = (x) => Math.round(x).toLocaleString("pt-BR");
const faixa = (xs, casas = 2, f = (v) => v) => {
  const a = Math.min(...xs), b = Math.max(...xs);
  return Math.abs(a - b) < 0.5 * 10 ** -casas ? n(f(a), casas) : `${n(f(a), casas)}–${n(f(b), casas)}`;
};

// ---------------------------------------------------------------- dados
const Q = U.q;                                   // baixo/central/alto
const REF = SW.referencias;
const J = (c, lam) => SW.joelhos.filter((r) => r.cenario === c && r.lam === lam);
const ATUAL = REF["central|atual"], PMED = REF["central|p-median"];
const HUFF1 = RES.por_lambda["1"].joelho;
const tabQ = (modelo, config) => QS.tabela.find((r) => r.modelo === modelo && r.config === config);
const simC = (config) => SIM.medias.find((r) => r.config === config && r.servico === "central");
// o p-median tambem reposiciona a frota: unidades movidas e km saem da comparacao
// (as posicoes nao dependem do modelo de "quem atende")
const CMP = lerJson("sp_comparacao.json");
const PMED_MUDA = CMP.find((c) => c.config.startsWith("p-median"));
const ATUAL_MUDA = CMP.find((c) => c.config === "atual");
// quanto o modelo despacho fica otimista no chamado grave, pela simulacao
const GAP_GRAVE = SIM.medias.map((r) => r.sim_et_grave - r.an_et_grave);
// motolancia: primeiro mes da serie e ultimo mes fechado
const MESES = Object.keys(U.mensal).sort();
const MOTO0 = U.mensal[MESES[0]].moto, MOTO1 = U.mensal[U.janela[1]].moto;
const ENVIOS_DIA_2024 = U.validacao_anual["2024"].sia_envios / 366;

// ------------------------------------------- dados externos (com link no rodape)
// Prefeitura de SP, noticia de 21/12/2023 (link L.pref23)
const PREF23 = { ambulancias: 120, bases: 86, saidas_dia: 350, chegada_grave_min: 20 };
// Hora et al. 2019 (Salvador, 465 ocorrencias clinicas): duracao total media 2 h,
// das quais 22 min entre a abertura da ocorrencia e a saida da base
const HORA = { total_min: 120, antes_saida_min: 22, n: 465 };
// Feldmeier et al. 2024 (California, 5,9 milhoes de entregas): entrega no hospital
const FELD = { media_min: 42.8, mediana_min: 28.9 };
// Malvestio & Sousa 2024: custeio do SAMU independe da producao registrada

const L = {
  ibge: ["IBGE · Censo 2022, setores", "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/"],
  cnes: ["CNES/DATASUS", "https://cnes.datasus.gov.br/"],
  osm: ["OpenStreetMap", "https://www.openstreetmap.org/copyright"],
  sia: ["SIA/SUS · notas técnicas", "http://tabnet.datasus.gov.br/cgi/sia/qadescr.htm"],
  ftp: ["DATASUS · arquivos PASP", "ftp://ftp.datasus.gov.br/dissemin/publicos/SIASUS/200801_/Dados/"],
  sigtap: ["SIGTAP · Tabela Unificada", "http://sigtap.datasus.gov.br/tabela-unificada/app/sec/inicio.jsp"],
  pref23: ["Prefeitura de SP, dez/2023", "https://prefeitura.sp.gov.br/web/saude/w/noticias/359560"],
  pref24: ["Prefeitura de SP, dado de 2024", "https://prefeitura.sp.gov.br/w/saiba-como-usar-corretamente-os-servi%C3%A7os-do-samu"],
  pref25: ["Prefeitura de SP, dado de 2025", "https://prefeitura.sp.gov.br/web/saude/w/samu-192-como-usar-corretamente-e-evitar-sobrecarga-do-servi%C3%A7o-5"],
  malvestio: ["Malvestio & Sousa (2024)", "https://doi.org/10.1590/1413-81232024291.18482022"],
  hora: ["Hora et al. (2019)", "https://doi.org/10.5935/1415-2762.20190104"],
  feldmeier: ["Feldmeier et al. (2024)", "https://doi.org/10.1001/jamanetworkopen.2024.51022"],
  huff: ["Huff (1964)", "https://doi.org/10.1177/002224296402800307"],
  daskin: ["Daskin (1983)", "https://doi.org/10.1287/trsc.17.1.48"],
  revelle: ["ReVelle & Hogan (1989)", "https://doi.org/10.1287/trsc.23.3.192"],
  larson: ["Larson (1974)", "https://doi.org/10.1016/0305-0548(74)90076-8"],
  budge: ["Budge, Ingolfsson & Erkut (2009)", "https://doi.org/10.1287/opre.1080.0591"],
  takeda: ["Takeda, Widmer & Morabito (2007)", "https://doi.org/10.1016/j.cor.2005.03.022"],
  luo: ["Luo & Wang (2003)", "https://doi.org/10.1068/b29120"],
  deb: ["Deb et al. (2002), NSGA-II", "https://doi.org/10.1109/4235.996017"],
};

// ------------------------------------------------- exemplos de brinquedo
const BETA = 4.5, Q_EX = 0.27;
const fH = (t) => Math.exp(-(t * t) / (2 * BETA * BETA));
const huffP = (ts) => { const w = ts.map(fH), s = w.reduce((a, b) => a + b); return w.map((x) => x / s); };
// despacho com uma unidade por local; "todas ocupadas" espera a mais proxima
const despP = (ts, q) => {
  const p = ts.map((_, k) => Math.pow(q, k) * (1 - q));
  p[0] += Math.pow(q, ts.length);
  return p;
};
const esp = (p, ts) => p.reduce((a, x, k) => a + x * ts[k], 0);
const H13 = huffP([1, 3]), H1012 = huffP([10, 12]);
const EX_H = huffP([5, 10]), EX_D = despP([5, 10], Q_EX);
const CEN = [2, 4], PER = [10, 22, 25];

// ---------------------------------------------------------------- estilo
const doc = new pptx();
doc.layout = "LAYOUT_WIDE";
doc.author = "Grupo MAI5003";
doc.title = "Quem atende o chamado? Do modelo de Huff ao despacho real do SAMU";

const NAVY = "16263F", TEAL = "0F3D5C", CREAM = "F7F5F0", CARD = "EAF1F7";
const INK = "0F2B46", INK2 = "4A5568", GOLD = "D9A441";
const BLUE = "2A78D6", ORANGE = "EB6834", GREEN = "2E7D5A", GREY = "8A8F98";
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
    rectRadius: 0.10, fill: { color: o.fill || CARD }, line: { color: o.fill || CARD } });
}
function bolha(s, texto, x, y, cor) {
  s.addShape(doc.ShapeType.ellipse, { x, y, w: 0.46, h: 0.46,
    fill: { color: cor }, line: { color: cor } });
  s.addText(String(texto), { x, y, w: 0.46, h: 0.46, isTextBox: true, margin: 0,
    align: "center", valign: "middle", fontFace: SANS, fontSize: 13, bold: true, color: "FFFFFF" });
}
function item(s, num, x, y, w, titulo, corpo, cor, hCorpo = 1.0) {
  bolha(s, num, x, y, cor || BLUE);
  s.addText(titulo, { x: x + 0.62, y: y - 0.02, w: w - 0.62, h: 0.3, isTextBox: true,
    margin: 0, valign: "top", fontFace: SANS, fontSize: 13.5, bold: true, color: INK });
  s.addText(corpo, { x: x + 0.62, y: y + 0.28, w: w - 0.62, h: hCorpo, isTextBox: true,
    margin: 0, valign: "top", fontFace: SANS, fontSize: 12, color: INK2, lineSpacing: 16 });
}
function texto(s, t, x, y, w, h, o = {}) {
  s.addText(t, Object.assign({ x, y, w, h, isTextBox: true, margin: 0, valign: "top",
    fontFace: SANS, fontSize: 13, color: INK2, lineSpacing: 18 }, o));
}
function conclusao(s, t, y = 6.45) {
  texto(s, t, M, y, 12.1, 0.6, { fontFace: SERIF, fontSize: 14, italic: true, color: TEAL, lineSpacing: 19 });
}
// rodape de fontes: cada dado externo citado no slide leva o link da origem;
// `proj` nomeia o arquivo de resultado do projeto de onde saem os numeros
function fontes(s, refs, proj, cor = GREY) {
  const runs = [{ text: refs.length ? "Fontes: " : "Fonte: ", options: { bold: true, color: cor } }];
  refs.forEach((r, i) => {
    if (i) runs.push({ text: " · ", options: { color: cor } });
    runs.push({ text: r[0], options: { hyperlink: { url: r[1], tooltip: r[1] }, color: cor } });
  });
  if (proj) runs.push({ text: `${refs.length ? "  |  dados do projeto: " : "resultados do projeto, "}${proj}`, options: { color: cor } });
  s.addText(runs, { x: M, y: 7.06, w: 11.95, h: 0.3, isTextBox: true, margin: 0,
    valign: "middle", fontFace: SANS, fontSize: 8.5 });
}
// seta de um fluxo (linha com ponta)
function seta(s, x, y, w, h) {
  s.addShape(doc.ShapeType.line, { x, y, w, h,
    line: { color: GREY, width: 1.5, endArrowType: "triangle" } });
}
// dimensoes (px) dos PNGs de formulas_gera.py, para nao distorcer
const DIM = { huff_principal: [723, 286], huff_decaimento: [499, 110],
  desp_geom: [704, 100], desp_local: [1035, 181], q_def: [322, 159],
  et_def: [682, 175], cob_def: [909, 175] };
function formula(s, chave, x, y, h) {
  const [pw, ph] = DIM[chave];
  s.addImage({ path: FORMULAS + chave + ".png", x, y, w: h * pw / ph, h });
  return h * pw / ph;
}
function figura(s, arq, x, y, w, px) {
  s.addImage({ path: FIG + arq, x, y, w, h: w * px[1] / px[0] });
}
function tabela(s, x, y, w, colW, cab, linhas, o = {}) {
  const fs_ = o.fontSize || 12;
  s.addTable([cab.map((t) => ({ text: t, options: { bold: true, color: "FFFFFF",
      fill: { color: TEAL }, fontSize: fs_, fontFace: SANS, align: "center" } }))]
    .concat(linhas.map((r, i) => r.map((c, j) => ({ text: String(c), options: {
      fontSize: fs_, fontFace: SANS, bold: (o.destaque || []).includes(i) && j === 0,
      color: (o.destaque || []).includes(i) ? INK : INK2, align: j === 0 ? "left" : "center",
      fill: { color: (o.destaque || []).includes(i) ? "FBEAE7" : (i % 2 ? "FFFFFF" : CARD) } } })))),
    { x, y, w, colW, rowH: o.rowH || 0.38, border: { pt: 0, color: CREAM }, valign: "middle" });
}

// ======================================================================
// — capa
{
  const s = slideEscuro(NAVY);
  texto(s, "MAI5003 · PROBABILIDADE E ESTATÍSTICA · FASE 2b", M, 1.3, 11, 0.3,
    { fontSize: 11, bold: true, color: GOLD, charSpacing: 1.4 });
  // caixa alta o bastante para a linha de 42 pt: com valign "top" numa caixa
  // baixa, o PowerPoint sobe o texto por cima do sobretitulo
  texto(s, "Quem atende o chamado?", M, 1.75, 11.7, 1.1,
    { valign: "middle", fontFace: SERIF, fontSize: 42, bold: true, color: "FFFFFF" });
  texto(s, "Do modelo de Huff ao despacho real do SAMU — com dado do SUS e uma cidade simulada",
    M, 3.05, 11, 0.9, { fontFace: SERIF, fontSize: 19, italic: true, color: "C9D6E4" });
  texto(s, "Realocação de USB e USA em São Paulo · passo a passo, sem pressupor as fórmulas",
    M, 4.1, 11, 0.4, { fontSize: 13, color: "9FB0C4" });
  texto(s, "Grupo MAI5003 · outubro de 2026", M, 6.6, 6, 0.4, { fontSize: 11, color: "8D9EB2" });
  s.addNotes("Esta apresentação conta o que foi feito depois da fase 2: trocamos o modelo de " +
    "escolha (Huff) por um modelo do despacho real do SAMU, estimamos o único parâmetro dele com " +
    "dado público do SUS, refizemos a otimização e validamos tudo com uma simulação.");
}

// — roteiro
{
  const s = slideClaro("O roteiro em oito passos", "roteiro");
  const passos = [
    ["Onde estávamos", "o que a fase 2 entregou e a pergunta que ficou aberta: quanto vale β?"],
    ["O que o Huff supõe", "um modelo de escolha de consumidor — e por que ele erra para ambulância"],
    ["Como o SAMU decide", "a regra do regulador vira uma fórmula com um parâmetro só, q"],
    ["Medir q no dado", "31 meses de produção do SAMU-SP no SIA/SUS, 111 arquivos do DATASUS"],
    ["Responder sobre β", "a ponte entre os dois modelos: o β = 4,5 escolhido cabe no dado?"],
    ["Uma métrica nova", "a chance de a USA chegar a tempo, olhando os 10% mais mal servidos"],
    ["Otimizar de novo", "29 rodadas do otimizador, com e sem uma regra de cobertura mínima"],
    ["Conferir por simulação", "a cidade simulada chamado a chamado, um ano inteiro"]];
  passos.forEach((p, i) => {
    const col = i < 4 ? 0 : 1, lin = i % 4;
    item(s, i + 1, M + col * 6.2, 1.75 + lin * 1.15, 5.9, p[0], p[1], i < 4 ? BLUE : ORANGE, 0.7);
  });
  conclusao(s, "Cada resultado sai de um arquivo do projeto; cada dado externo traz o link da fonte no rodapé do slide.");
}

// — o pipeline completo
{
  const s = slideClaro("O pipeline completo: dos dados à simulação", "visão geral");
  const W = 2.1, X = (k) => M + k * 2.5;
  ["1 · dados", "2 · preparo", "3 · quem atende", "4 · objetivos", "5 · otimização e teste"]
    .forEach((t, k) => texto(s, t.toUpperCase(), X(k), 1.5, W + 0.3, 0.3,
      { fontSize: 10.5, bold: true, color: GOLD, charSpacing: 1 }));
  const caixa = (k, y, h, tit, corpo, fill = "FFFFFF") => {
    cartao(s, { x: X(k), y, w: W, h, fill });
    texto(s, tit, X(k) + 0.12, y + 0.1, W - 0.24, 0.3, { fontSize: 12, bold: true, color: INK });
    texto(s, corpo, X(k) + 0.12, y + 0.42, W - 0.24, h - 0.5, { fontSize: 10.5, lineSpacing: 13.5 });
  };
  caixa(0, 1.9, 1.0, "IBGE · Censo 2022", "população de cada setor censitário");
  caixa(0, 3.05, 1.0, "CNES", `locais candidatos e a frota de hoje: ${U.frota.usb} USB, ${U.frota.usa} USA`);
  caixa(0, 4.2, 1.0, "OpenStreetMap", "ruas e velocidades da cidade");
  caixa(0, 5.35, 1.0, "SIA/SUS", "saídas do SAMU por mês, faturadas no SUS");
  caixa(1, 1.9, 3.3, "Matriz de tempos", "minutos de carro de cada local a cada setor: caminho mais curto na malha de ruas (algoritmo de Dijkstra).\n\nmonta.py", CARD);
  caixa(1, 5.35, 1.0, "Ocupação q e θ", "lei de Little (demanda_samu.py)", CARD);
  caixa(2, 1.9, 1.95, "P(j | i)", "chance de a base j atender o setor i.\nFase 2: Huff (β).\nFase 2b: despacho (q).", "FFF4DC");
  caixa(2, 4.25, 2.1, "Acessibilidade 2SFCA", "oferta de cada base ÷ demanda que ela recebe, somada por setor.\n\nhuff2sfca.py", CARD);
  caixa(3, 1.9, 1.95, "Objetivo 1 · tempo", "tempo esperado até a ambulância chegar, + λ × km de mudança", "E7F0F7");
  caixa(3, 4.25, 2.1, "Objetivo 2 · equidade", "Gini da acessibilidade à USA entre os setores", "FBEAE7");
  caixa(4, 1.9, 1.95, "NSGA-II", "busca a fronteira tempo × Gini; parte da rede de hoje e do p-median. Escolhe o joelho.\notimiza.py", CARD);
  caixa(4, 4.25, 2.1, "Simulação", "um ano de chamados ao acaso, regulador com a regra real: confere o modelo.\n\nsimula.py", CARD);
  // setas: dados -> preparo -> quem atende -> objetivos -> otimizacao
  [2.4, 3.55, 4.7].forEach((y) => seta(s, X(0) + W, y, 0.4, 0));
  seta(s, X(0) + W, 5.85, 0.4, 0);
  seta(s, X(1) + W, 2.9, 0.4, 0);
  s.addShape(doc.ShapeType.line, { x: X(1) + W, y: 3.6, w: 0.4, h: 2.25, flipV: true,
    line: { color: GREY, width: 1.5, endArrowType: "triangle" } });
  seta(s, X(2) + W / 2, 3.88, 0, 0.34);
  seta(s, X(2) + W, 2.9, 0.4, 0);
  seta(s, X(2) + W, 5.3, 0.4, 0);
  seta(s, X(3) + W, 2.9, 0.4, 0);
  s.addShape(doc.ShapeType.line, { x: X(3) + W, y: 3.3, w: 0.4, h: 2.0, flipV: true,
    line: { color: GREY, width: 1.5, endArrowType: "triangle" } });
  seta(s, X(4) + W / 2, 3.88, 0, 0.34);
  conclusao(s, "Da fase 2 para a 2b só muda a peça 3 — quem atende cada setor. Dados, objetivos e otimizador são os mesmos.", 6.5);
  fontes(s, [L.ibge, L.cnes, L.osm, L.sia, L.huff, L.daskin, L.luo, L.deb]);
  s.addNotes("Leitura da esquerda para a direita. A peça 3 é a única que muda entre as fases: o Huff distribui os chamados por peso que cai com a distância; o despacho usa a ordem de proximidade e a ocupação q, estimada do SIA pela lei de Little (carga = taxa × tempo de serviço). O 2SFCA divide a oferta de cada base pela demanda que ela recebe e soma, por setor, o que cada setor enxerga; o Gini dessa acessibilidade (só USA) é o objetivo 2. O NSGA-II é um algoritmo genético multiobjetivo; o p-median (guloso + trocas de Teitz-Bart) entra como solução inicial e como comparação. A simulação de eventos discretos não usa as fórmulas do modelo: ela sorteia chamados e ocupações e serve para testar se o modelo acerta.");
}

// — onde estavamos
{
  const s = slideClaro("Ponto de partida: o que a fase 2 entregou", "passo 1");
  texto(s, "O problema: 123 ambulâncias do SAMU em São Paulo (107 USB, básicas, e 16 USA, avançadas, com médico). Onde colocá-las para que (1) cheguem rápido e (2) a oferta seja distribuída com justiça entre os bairros?",
    M, 1.65, 12.1, 0.9);
  [["Objetivo 1 — tempo", "Tempo médio esperado até a ambulância chegar, ponderado pela população de cada setor censitário (26.889 setores).", BLUE],
   ["Objetivo 2 — equidade", "Gini da “quantidade de USA por habitante” que cada setor enxerga: 0 = todos iguais, 1 = tudo num lugar só.", ORANGE]]
    .forEach((c, i) => {
      const x = M + i * 6.2;
      cartao(s, { x, y: 2.65, w: 5.9, h: 1.45, fill: i ? "FBEAE7" : "E7F0F7" });
      texto(s, c[0], x + 0.3, 2.82, 5.3, 0.3, { fontSize: 14.5, bold: true, color: c[2] });
      texto(s, c[1], x + 0.3, 3.2, 5.3, 0.85, { fontSize: 12.5 });
    });
  texto(s, `Resultado da fase 2: mover só ${HUFF1.movidas} das 123 unidades (${Math.round(HUFF1.km_total)} km no total) derrubava o Gini da USA de ${n(RES.atual.f_gini, 3)} para ${n(HUFF1.f_gini, 3)}.`,
    M, 4.4, 12.1, 0.6, { fontSize: 14, bold: true, color: INK });
  cartao(s, { x: M, y: 5.15, w: 12.1, h: 1.1, fill: "FFF4DC" });
  texto(s, "A pergunta que ficou aberta: tudo isso dependia de um parâmetro, β, que foi escolhido por argumento (4,5 minutos), não medido. Quais valores β pode ter? E qual é o certo?",
    M + 0.3, 5.3, 11.5, 0.85, { fontSize: 13.5, color: INK });
  fontes(s, [L.cnes, L.ibge], "sp_resultado.json");
  s.addNotes("Recapitulação em linguagem simples. Setor censitário = um pedaço de bairro com algumas centenas de moradores. O Gini é o mesmo índice usado para desigualdade de renda.");
}

// — o que o Huff supoe
{
  const s = slideClaro("O que o modelo de Huff supõe", "passo 2");
  texto(s, "O Huff vem do varejo (1964): explica em qual loja o consumidor compra. Cada base recebe um “peso” que cai com a distância, e a chance de cada base atender é o peso dela dividido pela soma dos pesos.",
    M, 1.65, 12.1, 0.9);
  formula(s, "huff_principal", M + 0.3, 2.7, 1.25);
  formula(s, "huff_decaimento", M + 0.3, 4.3, 0.55);
  cartao(s, { x: 6.6, y: 2.65, w: 6.1, h: 2.4 });
  texto(s, "Lendo a fórmula", 6.9, 2.8, 5.5, 0.3, { fontSize: 13.5, bold: true, color: INK });
  texto(s, "P(j | i): chance de a base j atender o setor i.\nS_j: quantas ambulâncias a base j tem.\nt_ij: minutos de carro do setor até a base.\nf(t): o peso, que cai com o tempo; β diz quão rápido cai.\nα: quanto uma base com mais viaturas atrai a mais (aqui, α = 1).",
    6.9, 3.15, 5.6, 1.8, { fontSize: 12.5 });
  texto(s, "β pequeno: só a base mais próxima conta. β grande: todas as bases a menos de 30 min contam quase igual. Qualquer β > 0 é matematicamente válido — o modelo não diz qual escolher.",
    M, 5.3, 12.1, 0.8, { fontSize: 13 });
  conclusao(s, "O Huff descreve alguém que escolhe. No SAMU, ninguém escolhe: há uma regra.");
  fontes(s, [L.huff]);
}

// — o erro do Huff
{
  const s = slideClaro("Onde o Huff erra com ambulâncias", "passo 2");
  texto(s, `Com β = 4,5, a chance de a segunda base mais próxima atender:`, M, 1.65, 12.1, 0.4);
  tabela(s, M, 2.15, 8.0, [3.4, 2.3, 2.3],
    ["setor", "1ª e 2ª base", "2ª base atende"],
    [["perto de uma base", "1 e 3 min", pct(100 * H13[1])],
     ["longe das bases", "10 e 12 min", pct(100 * H1012[1])]], { fontSize: 13, rowH: 0.45 });
  texto(s, "No Huff, quem mora colado na base vê a segunda base atender quase metade das vezes; quem mora longe, só um quarto. A diferença é a mesma (2 minutos), mas a curva gaussiana trata as duas situações de forma oposta.",
    M, 3.65, 12.1, 0.9);
  cartao(s, { x: M, y: 4.7, w: 12.1, h: 1.35, fill: "FBEAE7" });
  texto(s, "Na vida real, a segunda base atende quando a primeira está ocupada — e isso depende de quanto trabalho a primeira tem, não de quão perto você mora dela. A distância deveria decidir a ORDEM das bases, não o peso.",
    M + 0.3, 4.85, 11.5, 1.1, { fontSize: 13.5, color: INK });
  conclusao(s, "Consequência: o Huff exagera o tempo perto das bases e esconde o tempo da periferia.");
}

// — como o SAMU decide
{
  const s = slideClaro("Como o SAMU realmente decide", "passo 3");
  texto(s, "O médico regulador recebe o chamado e manda a ambulância DISPONÍVEL mais próxima. A única coisa incerta é quem está ocupado naquele momento.",
    M, 1.65, 12.1, 0.7, { fontSize: 14 });
  const xs = [M, M + 3.1, M + 6.2, M + 9.3];
  [["1ª mais próxima", "ocupada", ORANGE], ["2ª mais próxima", "ocupada", ORANGE],
   ["3ª mais próxima", "LIVRE → vai ela", GREEN], ["4ª mais próxima", "nem é consultada", GREY]]
    .forEach((c, i) => {
      cartao(s, { x: xs[i], y: 2.6, w: 2.8, h: 1.3, fill: "FFFFFF" });
      texto(s, c[0], xs[i] + 0.2, 2.75, 2.4, 0.3, { fontSize: 13, bold: true, color: INK });
      texto(s, c[1], xs[i] + 0.2, 3.15, 2.4, 0.5, { fontSize: 13, bold: true, color: c[2] });
    });
  texto(s, "Se cada ambulância está ocupada uma fração q do tempo, independente das outras, a chance de a k-ésima mais próxima atender é:",
    M, 4.2, 12.1, 0.6);
  formula(s, "desp_geom", M + 0.3, 4.95, 0.5);
  texto(s, "q elevado a (k−1): as k−1 mais próximas estão todas ocupadas.  (1−q): a k-ésima está livre.",
    M + 5.5, 4.95, 6.6, 0.6, { fontSize: 12.5 });
  conclusao(s, "Esse é o “modelo de despacho” (Daskin 1983; ReVelle & Hogan 1989). Ele tem um parâmetro só, q — e q pode ser medido.", 5.85);
  fontes(s, [L.daskin, L.revelle]);
}

// — exemplo de brinquedo
{
  const s = slideClaro("Um exemplo com duas bases: Huff × despacho", "passo 3");
  texto(s, `Um setor, duas bases com uma ambulância cada: A a 5 min, B a 10 min. No despacho, q = ${n(Q_EX)}.`, M, 1.65, 12.1, 0.4);
  tabela(s, M, 2.2, 12.1, [4.1, 2.6, 2.6, 2.8],
    ["", "A atende", "B atende", "tempo esperado"],
    [["Huff (β = 4,5)", pct(100 * EX_H[0]), pct(100 * EX_H[1]), `${n(esp(EX_H, [5, 10]))} min`],
     ["Despacho (q = 0,27)", pct(100 * EX_D[0]), pct(100 * EX_D[1]), `${n(esp(EX_D, [5, 10]))} min`]],
    { fontSize: 13, rowH: 0.45 });
  cartao(s, { x: M, y: 3.75, w: 12.1, h: 1.9 });
  texto(s, "A conta do despacho, à mão", M + 0.3, 3.9, 11, 0.3, { fontSize: 13.5, bold: true, color: INK });
  texto(s, `B atende quando A está ocupada e B livre: q × (1 − q) = ${n(Q_EX)} × ${n(1 - Q_EX)} = ${n(Q_EX * (1 - Q_EX), 3)}.\nA atende quando está livre (${n(1 - Q_EX)}) — e também quando as duas estão ocupadas e o chamado espera por ela (${n(Q_EX)}² = ${n(Q_EX * Q_EX, 3)}).\nTotal de A: ${n(1 - Q_EX)} + ${n(Q_EX * Q_EX, 3)} = ${n(EX_D[0], 3)}. As duas chances somam 1.`,
    M + 0.3, 4.28, 11.5, 1.35, { fontSize: 12.5 });
  texto(s, "Com uma base por local e muitas bases, a chance da k-ésima é a distribuição geométrica — a mesma do “número de tentativas até o primeiro sucesso”.",
    M, 5.85, 12.1, 0.6, { fontSize: 12.5, italic: true, color: TEAL });
  s.addNotes("q = 0,27 é o valor que dá ao despacho o mesmo número efetivo de unidades que o Huff com beta 4,5 (slide da ponte). Os números são calculados pelo gerador com as mesmas fórmulas do código.");
}

// — centro x periferia
{
  const s = slideClaro("Na periferia, os dois modelos divergem", "passo 3");
  const hc = huffP(CEN), dc = despP(CEN, Q_EX), hp = huffP(PER), dp = despP(PER, Q_EX);
  texto(s, "Tempo esperado (média das distâncias, pesadas pela chance de cada base atender):", M, 1.65, 8, 0.4);
  formula(s, "et_def", 8.9, 1.55, 0.6);
  tabela(s, M, 2.4, 12.1, [3.7, 2.8, 2.8, 2.8],
    ["setor", "USAs a", "Huff (β = 4,5)", "Despacho (q = 0,27)"],
    [["central", "2 e 4 min", `${n(esp(hc, CEN))} min`, `${n(esp(dc, CEN))} min`],
     ["periférico", "10, 22 e 25 min", `${n(esp(hp, PER))} min`, `${n(esp(dp, PER))} min`]],
    { fontSize: 13, rowH: 0.45, destaque: [1] });
  texto(s, `No setor periférico o Huff dá à USA de 22 min uma chance de ${n(100 * hp[1], 3)}% — praticamente nunca. No despacho ela vem toda vez que a de 10 min está ocupada: ${pct(100 * dp[1])} das vezes.`,
    M, 3.9, 12.1, 0.9, { fontSize: 13.5 });
  cartao(s, { x: M, y: 4.95, w: 12.1, h: 1.2, fill: "FBEAE7" });
  texto(s, "O Huff faz a periferia parecer mais bem servida do que é — justamente onde o projeto quer medir desigualdade. A intuição de que a distância importa está certa — mas ela entra como custo de cada atendimento, não como probabilidade de ser chamado.",
    M + 0.3, 5.1, 11.5, 1.0, { fontSize: 13, color: INK });
}

// — de onde vem q: a formula
{
  const s = slideClaro("O parâmetro do despacho: a ocupação q", "passo 4");
  texto(s, "q é a fração do tempo em que uma ambulância está fora da base, atendendo. Se sabemos quantas saídas há por hora e quanto tempo cada saída prende a viatura:",
    M, 1.65, 12.1, 0.8);
  formula(s, "q_def", M + 0.3, 2.55, 1.1);
  texto(s, "r = saídas por hora (do dado)\ns̄ = horas que cada saída ocupa a viatura (hipótese)\nN = número de unidades (107 USB, 16 USA)",
    M + 3.0, 2.6, 6, 1.2, { fontSize: 13 });
  cartao(s, { x: M, y: 4.05, w: 12.1, h: 1.45 });
  const r = U.por_ano_12m.usa / 8760;
  texto(s, "Exemplo, USA", M + 0.3, 4.2, 11, 0.3, { fontSize: 13.5, bold: true, color: INK });
  texto(s, `${mil(U.por_ano_12m.usa)} saídas em 12 meses ÷ 8.760 h = ${n(r)} por hora.  × 70 min (1,17 h) = ${n(r * 70 / 60)} viaturas ocupadas em média.  ÷ ${U.frota.usa} USAs = q ≈ ${n(Q.central.q_usa)}.`,
    M + 0.3, 4.58, 11.5, 0.8, { fontSize: 13 });
  conclusao(s, "Isso é a lei de Little das filas: carga média = taxa de chegada × tempo de serviço.", 5.8);
  fontes(s, [L.sia, L.cnes], "sp_utilizacao.json");
}

// — o dado
{
  const s = slideClaro("Onde medir q: a produção do SAMU no SIA/SUS", "passo 4");
  texto(s, "O SIA, sistema de produção ambulatorial do SUS, recebe todo mês os procedimentos que cada serviço registra, cada um com um código da tabela SIGTAP. O SAMU tem códigos próprios — inclusive “envio de USA” e “envio de USB”: é exatamente a contagem de saídas que q precisa.",
    M, 1.65, 6.1, 2.4, { fontSize: 13 });
  texto(s, `O que fizemos: baixamos do DATASUS os 111 arquivos de São Paulo (jan/2024 a jul/2026, ~11 GB), filtramos só as linhas do SAMU na capital (${mil(81921)} linhas) e apagamos o resto.`,
    M, 3.2, 6.1, 1.4, { fontSize: 13 });
  figura(s, "sp_06_producao_samu.png", 6.95, 1.6, 5.8, [1040, 598]);
  texto(s, "Saídas por mês. A faixa cinza são meses que ainda podem receber registros atrasados.",
    6.95, 5.05, 5.8, 0.5, { fontSize: 11, italic: true, color: GREY });
  conclusao(s, `Janela usada: ${U.janela[0]} a ${U.janela[1]}, os últimos 12 meses fechados.`, 5.9);
  fontes(s, [L.sia, L.ftp, L.sigtap], "sp_utilizacao.json");
}

// — o que e o SIA e o que conta como faturado
{
  const s = slideClaro("O que é o SIA e o que conta como “faturado”", "passo 4");
  item(s, 1, M, 1.75, 7.3, "SIA = Sistema de Informações Ambulatoriais do SUS",
    "Mantido pelo DATASUS. Cada serviço informa, mês a mês, os procedimentos que fez, no Boletim de Produção Ambulatorial (BPA). Nasceu para pagar procedimentos; hoje é a maior base pública da produção do SUS.", BLUE, 1.0);
  item(s, 2, M, 3.15, 7.3, "Atendimento faturado",
    "Saída que entrou no SIA: a equipe registrou o procedimento e o sistema aprovou. É o que dá para contar.", GREEN, 0.7);
  item(s, 3, M, 4.2, 7.3, "Atendimento não faturado",
    "Saída que aconteceu, mas não foi registrada. No SAMU, o repasse federal é fixo por unidade habilitada e só para se a produção ficar zerada ou sem informar por 3 meses (Malvestio & Sousa, 2024): registrar cada saída não traz dinheiro a mais, e parte delas fica de fora.", ORANGE, 1.25);
  const v = U.validacao_anual["2025"], cob = v.sia_atend_usb_usa / v.prefeitura;
  cartao(s, { x: 8.45, y: 1.75, w: 4.27, h: 3.7, fill: "FFF4DC" });
  texto(s, "2025, cidade de São Paulo", 8.7, 1.9, 3.8, 0.3, { fontSize: 12, bold: true, color: INK });
  texto(s, `${mil(v.prefeitura)}`, 8.7, 2.3, 3.8, 0.5, { fontFace: SERIF, fontSize: 26, bold: true, color: INK });
  texto(s, "atendimentos presenciais divulgados pela Prefeitura", 8.7, 2.78, 3.8, 0.5, { fontSize: 11.5 });
  texto(s, `${mil(v.sia_atend_usb_usa)}`, 8.7, 3.35, 3.8, 0.5, { fontFace: SERIF, fontSize: 26, bold: true, color: BLUE });
  texto(s, "atendimentos de USB e USA faturados no SIA", 8.7, 3.83, 3.8, 0.5, { fontSize: 11.5 });
  texto(s, `${pct(100 * cob)} faturado`, 8.7, 4.6, 3.8, 0.5, { fontFace: SERIF, fontSize: 20, bold: true, color: ORANGE });
  conclusao(s, `Consequência: o SIA conta um pouco menos saídas do que houve. Se a falta for parecida em todos os meses, o q estimado fica ~${pct(100 * (1 / cob - 1))} abaixo do real.`, 5.85);
  fontes(s, [L.sia, L.malvestio, L.pref25], "sp_utilizacao.json");
  s.addNotes("Faturado = registrado e aprovado no SIA/SUS. Não faturado = feito, mas não registrado. A comparação usa os códigos de atendimento pré-hospitalar por USB e USA (03.01.03.009-0 e 03.01.03.010-3) contra o total de atendimentos presenciais que a Prefeitura divulga. A frase sobre o repasse fixo vem de Malvestio & Sousa (2024), Ciência & Saúde Coletiva 29(1). O ajuste de ~8% em q é uma conta nossa, supondo a mesma fração não registrada em todos os meses; não foi aplicado aos resultados.");
}

// — checar o dado
{
  const s = slideClaro("Conferindo o dado do SIA", "passo 4");
  const v24 = U.validacao_anual["2024"], v25 = U.validacao_anual["2025"];
  const passo = 0.98, y0 = 1.6, h = 0.62;
  item(s, 1, M, y0, 12.1, "O total anual bate com a Prefeitura",
    `Faturados no SIA: ${mil(v24.sia_atend_usb_usa)} em 2024 e ${mil(v25.sia_atend_usb_usa)} em 2025. A Prefeitura divulga ${mil(v24.prefeitura)} e ${mil(v25.prefeitura)} atendimentos presenciais: o SIA cobre ~${pct(100 * v25.sia_atend_usb_usa / v25.prefeitura)}.`, GREEN, h);
  item(s, 2, M, y0 + passo, 12.1, "Um número da Prefeitura não bate",
    `Em dez/2023 a Prefeitura falou em ~${PREF23.saidas_dia} saídas de ambulância por dia. O SIA de 2024 dá ~${mil(ENVIOS_DIA_2024)} envios por dia, e o próprio total anual da Prefeitura dá ~${mil(v24.prefeitura / 366)} por dia. Não sabemos explicar a diferença.`, ORANGE, h);
  item(s, 3, M, y0 + 2 * passo, 12.1, "A frota confere",
    `O CNES lista ${U.frota.usb + U.frota.usa} ambulâncias (${U.frota.usb} USB e ${U.frota.usa} USA) em ${ATUAL_MUDA.locais} locais; a Prefeitura falava em ${PREF23.ambulancias} ambulâncias e ${PREF23.bases} bases em dez/2023.`, GREEN, h);
  const an = U.anomalias_corrigidas[0];
  item(s, 4, M, y0 + 3 * passo, 12.1, "Um erro de lançamento",
    an ? `Em ${an.mes}, ${mil(an.valor)} envios de USB contra ${mil(an.trocado_por)} atendimentos — 10 vezes o normal. Regra: envio maior que 3× o atendimento do mês é erro; trocamos pelo atendimento e registramos.` : "Nenhuma anomalia encontrada.", ORANGE, h);
  item(s, 5, M, y0 + 4 * passo, 12.1, "O que o dado não tem",
    `Quanto tempo cada saída dura (por isso testamos 45, 70 e 100 min) e qual base fez cada saída: o faturamento cai em ${U.cnes_faturantes} estabelecimentos e só ${pct(100 * U.frac_volume_em_bases_atuais)} nas bases atuais. Logo, um q para a cidade, não um por base.`, GREY, h);
  fontes(s, [L.pref24, L.pref25, L.pref23, L.cnes, L.sia], "sp_utilizacao.json, sp_comparacao.json");
  s.addNotes("O item 2 é uma inconsistência que não resolvemos: o número diário divulgado em dez/2023 é menos da metade do que o SIA registra e do que o próprio total anual da Prefeitura implica. Se o valor diário estivesse certo, q seria menos da metade do estimado.");
}

// — resultado da estimacao
{
  const s = slideClaro("A ocupação medida: q das USB e das USA", "passo 4");
  tabela(s, M, 1.7, 8.2, [3.4, 2.4, 2.4],
    ["tempo por saída (hipótese)", "q das USB", "q das USA"],
    ["baixo", "central", "alto"].map((k, i) => [`${[45, 70, 100][i]} min${k === "central" ? " (central)" : ""}`,
      n(Q[k].q_usb), n(Q[k].q_usa)]), { fontSize: 13, rowH: 0.45, destaque: [1] });
  cartao(s, { x: 9.15, y: 1.7, w: 3.55, h: 1.8, fill: "FFF4DC" });
  texto(s, "θ = fração de saídas que é de USA", 9.4, 1.85, 3.1, 0.6, { fontSize: 12.5, bold: true, color: INK });
  texto(s, `${n(U.theta_dados, 3)}`, 9.4, 2.45, 3.1, 0.6, { fontFace: SERIF, fontSize: 30, bold: true, color: ORANGE });
  texto(s, "a fase 2 supunha 0,10", 9.4, 3.05, 3.1, 0.3, { fontSize: 11.5, color: INK2 });
  item(s, "!", M, 3.95, 12.1, "Uma USA é menos ocupada que uma USB",
    `Cada USA faz em média ${n(U.por_ano_12m.usa / U.frota.usa / 365, 1)} saídas por dia; cada USB, ${n(U.por_ano_12m.usb / U.frota.usb / 365, 1)}. O regulador preserva a USA para os casos graves.`, ORANGE, 0.8);
  conclusao(s, "Agora q é medido — a menos do tempo por saída, que ainda é hipótese (próximo slide).", 5.6);
  fontes(s, [L.sia], "sp_utilizacao.json");
}

// o tempo por saida: o que as fontes publicadas dizem
{
  const s = slideClaro("Quanto tempo uma saída prende a ambulância?", "passo 4");
  texto(s, "O tempo por saída vai da saída da base até a viatura estar livre de novo. O SIA não o registra, e não achamos medida publicada para São Paulo. Uma saída típica soma cinco partes:",
    M, 1.6, 12.1, 0.7);
  const partes = ["ir até o local", "atender na cena", "levar ao hospital", "entregar o paciente", "voltar à base"];
  partes.forEach((p, i) => {
    const x = M + i * 2.45;
    cartao(s, { x, y: 2.4, w: 2.25, h: 0.6, fill: i === 3 ? "FBEAE7" : "FFFFFF" });
    texto(s, p, x, 2.4, 2.25, 0.6, { align: "center", valign: "middle", fontSize: 12.5, bold: true, color: INK });
  });
  tabela(s, M, 3.25, 12.1, [3.3, 5.3, 3.5],
    ["fonte", "o que mede", "valor"],
    [["Prefeitura de SP (dez/2023)", "chegada ao local, casos mais graves", `média de ${PREF23.chegada_grave_min} min`],
     [`Hora et al. (2019), Salvador, ${HORA.n} ocorrências`, "duração total, da abertura ao fim da ocorrência", `média de ${HORA.total_min / 60} h, ${HORA.antes_saida_min} min antes de a viatura sair`],
     ["Feldmeier et al. (2024), Califórnia", "só a entrega do paciente no hospital", `média de ${n(FELD.media_min, 1)} min`],
     ["este projeto", "tempo por saída (hipótese)", "45 · 70 · 100 min"]],
    { fontSize: 11.5, rowH: 0.42, destaque: [3] });
  conclusao(s, `Salvador dá ~${HORA.total_min - HORA.antes_saida_min} min de viatura ocupada; só a entrega no hospital leva ~${Math.round(FELD.media_min)} min. Saídas sem transporte são mais curtas. As medidas apoiam o cenário central e não descartam o alto; o baixo (45 min) é o menos sustentado.`, 5.55);
  fontes(s, [L.pref23, L.hora, L.feldmeier], "sp_utilizacao.json");
  s.addNotes("Nenhuma das fontes é de São Paulo para o tempo total por saída. Salvador: estudo de 465 ocorrências clínicas (REME 2019), duração total média de 2 h (DP 1h23) desde a abertura da ocorrência, com 22 min entre a abertura e a saída da base; descontar os 22 min é conta nossa. Califórnia: 5,9 milhões de entregas de paciente, média 42,8 min (mediana mensal por hospital 28,9 min); é outro sistema de saúde. Prefeitura de SP: notícia de 21/12/2023, média de 20 min para chegar ao local nos casos mais graves. Os resultados do projeto foram calculados nos três cenários (45, 70 e 100 min).");
}

// — a ponte beta <-> q
{
  const s = slideClaro("O β = 4,5 da fase 2 é compatível com o dado?", "passo 5");
  texto(s, "Os dois modelos podem ser comparados por uma régua comum: o número efetivo de ambulâncias que “dividem” o atendimento de um setor. Para cada β existe um q que dá o mesmo número.",
    M, 1.65, 12.1, 0.8);
  const ponte = QS.ponte.filter((p) => [1.5, 3, 4.5, 6, 8.5].includes(p.beta));
  tabela(s, M, 2.6, 12.1, [2.6].concat(ponte.map(() => 9.5 / ponte.length)),
    ["β (min)"].concat(ponte.map((p) => n(p.beta, 1))),
    [["unidades efetivas"].concat(ponte.map((p) => n(p.n_ef_usa, 1))),
     ["q equivalente"].concat(ponte.map((p) => n(p.q_mesmo_n_ef)))], { fontSize: 13, rowH: 0.45 });
  const be = QS.beta_equivalente;
  cartao(s, { x: M, y: 4.2, w: 12.1, h: 1.45, fill: "E5F2EA" });
  texto(s, `O q das USA medido no SIA corresponde a β entre ${n(be["SIA baixo"], 1)} e ${n(be["SIA alto"], 1)} (central ${n(be["SIA central"], 1)}).`,
    M + 0.3, 4.35, 11.5, 0.5, { fontSize: 15, bold: true, color: GREEN });
  texto(s, "O β = 4,5 escolhido na fase 2 está dentro da faixa que o dado sustenta. β = 8,5 (q ≈ 0,66) exigiria duas em cada três ambulâncias ocupadas o tempo todo — não é o SAMU-SP.",
    M + 0.3, 4.85, 11.5, 0.75, { fontSize: 13 });
  conclusao(s, `Valores válidos de β: qualquer número positivo. Valores plausíveis para o SAMU-SP: ~${n(be["SIA baixo"], 1)} a ~${n(be["SIA alto"], 1)}.`, 5.95);
  fontes(s, [L.sia], "sp_q_sens.json");
}

// — reproducao
{
  const s = slideClaro("Reprodutibilidade: a rede de hoje dá o mesmo número", "passo 5");
  texto(s, "Para rodar em outra máquina, a matriz de tempos de viagem (1.107 locais × 26.889 setores, por ruas reais do OpenStreetMap) foi refeita do zero, com o mapa de hoje.",
    M, 1.65, 12.1, 0.8);
  tabela(s, M, 2.6, 8.5, [3.5, 2.5, 2.5], ["rede atual, Huff β = 4,5", "publicado", "refeito"],
    [["tempo esperado", `${n(QS.reproducao.publicado.f_tempo, 3)} min`, `${n(QS.reproducao.f_tempo, 3)} min`],
     ["Gini da USA", n(QS.reproducao.publicado.f_gini, 3), n(QS.reproducao.f_gini, 3)]],
    { fontSize: 13, rowH: 0.45 });
  texto(s, "Mesmo número até a terceira casa. O modelo novo convive com o antigo: o código continua rodando o Huff por padrão, e todos os resultados da fase 2 seguem reproduzíveis.",
    M, 4.15, 12.1, 0.9);
  conclusao(s, "Só depois disso faz sentido trocar o modelo e comparar.");
  fontes(s, [L.osm, L.ibge, L.cnes], "sp_q_sens.json, sp_resultado.json");
}

// — metrica nova
{
  const s = slideClaro("Nova métrica: a chance de a USA chegar em até 10 min", "passo 6");
  texto(s, "Cada minuto conta, principalmente para a USA. Por isso medimos, para cada setor, a chance de a ambulância que vier chegar em até τ minutos:",
    M, 1.65, 12.1, 0.7);
  formula(s, "cob_def", M + 0.3, 2.45, 0.6);
  texto(s, "1[...] vale 1 se a base está a até τ minutos e 0 se não. A soma junta as chances das bases que chegam a tempo.",
    M + 5.0, 2.45, 7.1, 0.7, { fontSize: 12.5 });
  const lin = (cfg, rot) => { const r = tabQ("desp SIA central", cfg); return [rot, `${n(r.f_tempo)} min`, n(r.f_gini, 3), pct(r.cob_usa_10_p10)]; };
  tabela(s, M, 3.4, 12.1, [4.0, 2.5, 2.4, 3.2], ["configuração (despacho, q do SIA)", "tempo", "Gini USA", "pior 10%: USA ≤ 10 min"],
    [lin("atual", "rede de hoje"), lin("p-median", "p-median (clássico)"), lin("huff lam=0.1", "solução “equânime” da fase 2")],
    { fontSize: 13, rowH: 0.45, destaque: [2] });
  texto(s, "“Pior 10%”: ordenamos os setores pela chance de chegar a tempo e olhamos os 10% da população com menor chance.",
    M, 5.35, 12.1, 0.5, { fontSize: 12, italic: true, color: GREY });
  conclusao(s, "A solução que iguala as USAs por habitante deixa os 10% mais mal servidos sem chance real de USA em 10 minutos.", 5.9);
  fontes(s, [], "sp_q_sens.json");
}

// — otimizar de novo
{
  const s = slideClaro("A nova rodada de otimização", "passo 7");
  texto(s, "O otimizador (NSGA-II, um algoritmo genético) testa milhares de mapas de bases e guarda os que não podem melhorar o tempo sem piorar a equidade — a “fronteira”. De cada fronteira escolhemos o ponto de equilíbrio.",
    M, 1.65, 12.1, 0.9);
  item(s, 1, M, 2.75, 5.9, "Três cenários de q", "45, 70 e 100 min por saída — porque o tempo de serviço é a hipótese que sobrou.", BLUE, 0.8);
  item(s, 2, M + 6.2, 2.75, 5.9, "Três preços de mudança (λ)", "λ = 0: redesenho livre. λ = 1: cada km deslocado custa caro, a rede quase congela.", BLUE, 0.8);
  item(s, 3, M, 4.15, 5.9, "Repetições", "Três sementes aleatórias no cenário central, para medir o ruído do algoritmo.", BLUE, 0.8);
  item(s, 4, M + 6.2, 4.15, 5.9, "Com e sem restrição", "Variante que exige: pior 10% com pelo menos 25% de chance de USA em 10 min.", ORANGE, 0.8);
  conclusao(s, `${SW.joelhos.length} otimizações completas, 13 em paralelo no computador do grupo, em 72 minutos.`, 5.6);
  fontes(s, [L.deb], "sp_q_sweep.json");
}

// — achado 1
{
  const s = slideClaro("Achado 1: o ganho de equidade se mantém, mas menor", "resultados");
  const l0 = J("central", 0)[0], l01 = J("central", 0.1), l1 = J("central", 1);
  tabela(s, M, 1.65, 12.1, [3.6, 1.9, 1.9, 2.3, 2.4],
    ["configuração (q central)", "tempo (min)", "Gini USA", "unidades movidas", "km deslocados"],
    [["rede de hoje", n(ATUAL.f_tempo), n(ATUAL.f_gini, 3), ATUAL_MUDA.movidas, Math.round(ATUAL_MUDA.km_mudanca)],
     ["p-median", n(PMED.f_tempo), n(PMED.f_gini, 3), PMED_MUDA.movidas, Math.round(PMED_MUDA.km_mudanca)],
     ["redesenho livre (λ = 0)", n(l0.f_tempo), n(l0.f_gini, 3), l0.movidas, Math.round(l0.km_total)],
     ["λ = 0,1 (3 sementes)", faixa(l01.map((r) => r.f_tempo)), faixa(l01.map((r) => r.f_gini), 3), faixa(l01.map((r) => r.movidas), 0), faixa(l01.map((r) => r.km_total), 0)],
     ["λ = 1 (3 sementes)", faixa(l1.map((r) => r.f_tempo)), faixa(l1.map((r) => r.f_gini), 3), faixa(l1.map((r) => r.movidas), 0), faixa(l1.map((r) => r.km_total), 0)]],
    { fontSize: 12.5, rowH: 0.42, destaque: [4] });
  const rho = l1.map((r) => 100 * r.rho_g);
  // mesma base nos dois modelos: p-median contra o joelho de lambda = 0,1
  const g01 = l01.reduce((a, r) => a + r.f_gini, 0) / l01.length;
  const razHuff = tabQ("huff b=4.5", "p-median").f_gini / tabQ("huff b=4.5", "huff lam=0.1").f_gini;
  texto(s, `O p-median também é um redesenho: põe uma unidade em cada um de ${PMED_MUDA.locais} locais (hoje são ${ATUAL_MUDA.locais}) e move ${PMED_MUDA.movidas} das ${U.frota.usb + U.frota.usa}. Por isso tempo e Gini mudam. Km em linha reta, entre a base antiga e a nova.`,
    M, 4.22, 12.1, 0.5, { fontSize: 11.5, italic: true, color: GREY });
  texto(s, `Com λ = 0,1, mesmo tempo do p-median e Gini ${n(PMED.f_gini / g01, 1)}× menor (sob o Huff, ${n(razHuff, 1)}×). O “pacote barato” (λ = 1) move ${faixa(l1.map((r) => r.movidas), 0)} ambulâncias e entrega ${faixa(rho, 0)}% do ganho de equidade possível.`,
    M, 4.8, 12.1, 0.8, { fontSize: 13.5 });
  texto(s, `E o Huff superestimava o tempo: a rede de hoje sai de ${n(RES.atual.f_tempo)} min (Huff) para ${n(ATUAL.f_tempo)} min (despacho).`,
    M, 5.65, 12.1, 0.45, { fontSize: 13 });
  conclusao(s, "A conclusão principal da fase 2 continua de pé, com números mais modestos.", 6.25);
  fontes(s, [], "sp_q_sweep.json, sp_comparacao.json, sp_q_sens.json, sp_resultado.json");
}

// — achado 2
{
  const s = slideClaro("Achado 2: equidade de carga não é equidade de chegada", "resultados");
  const r01 = J("central_r25", 0.1), r1 = J("central_r25", 1), l01 = J("central", 0.1);
  tabela(s, M, 1.65, 12.1, [3.6, 1.9, 1.9, 2.4, 2.3],
    ["λ = 0,1 (q central)", "tempo (min)", "Gini USA", "pior 10%: ≤ 10 min", "movidas / km"],
    [["sem restrição", faixa(l01.map((r) => r.f_tempo)), faixa(l01.map((r) => r.f_gini), 3), faixa(l01.map((r) => r.cob_usa_10_p10), 0, (v) => v) + "%", `${faixa(l01.map((r) => r.movidas), 0)} / ${faixa(l01.map((r) => r.km_total), 0)}`],
     ["com restrição de 25%", faixa(r01.map((r) => r.f_tempo)), faixa(r01.map((r) => r.f_gini), 3), faixa(r01.map((r) => r.cob_usa_10_p10), 0) + "%", `${faixa(r01.map((r) => r.movidas), 0)} / ${faixa(r01.map((r) => r.km_total), 0)}`],
     ["p-median", n(PMED.f_tempo), n(PMED.f_gini, 3), pct(PMED.cob_usa_10_p10), `${PMED_MUDA.movidas} / ${Math.round(PMED_MUDA.km_mudanca)}`]],
    { fontSize: 12.5, rowH: 0.42, destaque: [1] });
  item(s, "✓", M, 3.6, 5.9, "No redesenho, a restrição sai quase de graça",
    "Mesmo tempo, Gini um pouco maior e ainda melhor que o p-median — e o pior decil passa a ter chance real.", GREEN, 1.0);
  item(s, "✗", M + 6.2, 3.6, 5.9, "Mas o pacote barato deixa de existir",
    `Com λ = 1 e a restrição, é preciso mover ${faixa(r1.map((r) => r.movidas), 0)} unidades (${faixa(r1.map((r) => r.km_total), 0)} km), não ${faixa(J("central", 1).map((r) => r.movidas), 0)}.`, ORANGE, 1.0);
  conclusao(s, "Cobrir a periferia exige redesenhar a rede, não ajustar algumas bases. É uma decisão do grupo qual equidade defender.", 5.75);
  fontes(s, [], "sp_q_sweep.json, sp_comparacao.json");
}

// — simulacao
{
  const s = slideClaro("Validação: uma cidade simulada, chamado a chamado", "passo 8");
  texto(s, "O modelo supõe que as ocupações das ambulâncias são independentes. Para testar, simulamos São Paulo chamado a chamado, por um ano: chamados chegando ao acaso (Poisson) nas taxas do SIA, o regulador seguindo a regra real, fila quando todas estão ocupadas.",
    M, 1.65, 6.0, 2.6, { fontSize: 12.5 });
  figura(s, "sp_07_validacao.png", 6.85, 1.6, 5.9, [1092, 494]);
  texto(s, "Cada ponto: uma configuração × um tempo de serviço (média de 3 sementes). Na diagonal, o modelo acerta.",
    6.85, 4.3, 5.9, 0.5, { fontSize: 11, italic: true, color: GREY });
  const a = simC("p-median");
  item(s, 1, M, 4.4, 6.0, "Cobertura do pior decil: acerta",
    `Diferença de ~1 ponto (p-median: ${pct(a.an_cob10_p10, 1)} previsto, ${pct(a.sim_cob10_p10, 1)} simulado).`, GREEN, 0.6);
  item(s, 2, M, 5.25, 6.0, "Tempo do chamado grave: um pouco otimista",
    `O modelo erra para baixo em ${faixa(GAP_GRAVE, 1)} min — vizinhas se ocupam juntas nos picos.`, ORANGE, 0.6);
  item(s, 3, 6.85, 5.25, 5.9, "A ordem das configurações não muda",
    "Fila quase nunca acontece com a frota atual.", BLUE, 0.6);
  fontes(s, [L.sia], "sp_simulacao.json");
}

// — limitacoes
{
  const s = slideClaro("Limitações: o que ainda é hipótese", "limitações");
  const g = simC("atual");
  [["Tempo por saída", "Não está no SIA. Testamos 45, 70 e 100 min; as medidas publicadas ficam entre o central e o alto."],
   ["Um q para a cidade inteira", "O faturamento não identifica a base de cada saída; bairros mais carregados não aparecem."],
   ["Independência entre ocupações", `O modelo é ${faixa(GAP_GRAVE, 1)} min otimista no chamado grave (medido pela simulação).`],
   ["Tempos de viagem sem trânsito", `Velocidades do OpenStreetMap, sem congestionamento nem regulação: hoje o modelo dá ~${Math.round(g.an_et_grave)} min para a USA chegar; a Prefeitura informa ~${PREF23.chegada_grave_min} min nos casos graves.`],
   ["Demanda = população", "Sem variação ao longo do dia e sem incidência real de agravos por bairro."],
   ["Motolâncias fora do modelo", `A produção delas passou de ~${mil(MOTO0)} para ~${mil(MOTO1)} por mês (${MESES[0]} a ${U.janela[1]}).`]]
    .forEach((l, i) => item(s, i + 1, M, 1.55 + i * 0.9, 12.1, l[0], l[1], GREY, 0.5));
  fontes(s, [L.sia, L.osm, L.pref23, L.hora, L.feldmeier], "sp_simulacao.json, sp_utilizacao.json");
}

// — fechamento
{
  const s = slideEscuro(TEAL);
  texto(s, "O QUE LEVAR DAQUI", M, 1.1, 11, 0.3, { fontSize: 11, bold: true, color: GOLD, charSpacing: 1.4 });
  const pontos = [
    `β não é uma escolha livre: é a ocupação das ambulâncias disfarçada. Medida no SUS, ela dá β ≈ ${n(QS.beta_equivalente["SIA central"], 1)}.`,
    "Para ambulância, a distância define a ordem de quem atende; a ocupação define a chance.",
    `A equidade da fase 2 sobrevive ao modelo novo: Gini ~${n(PMED.f_gini / (J("central", 0.1).reduce((a, r) => a + r.f_gini, 0) / J("central", 0.1).length), 1)}× menor que o clássico, no mesmo tempo.`,
    "Mas igualar ambulâncias por habitante não garante que a USA chegue a tempo nos 10% mais mal servidos.",
    "Garantir isso é barato num redesenho e caro num ajuste: a escolha da métrica de equidade é do grupo."];
  pontos.forEach((p, i) => {
    // numero e frase na mesma caixa de altura, centrados: alinham na vertical
    texto(s, `${i + 1}`, M, 1.6 + i * 0.95, 0.5, 0.7, { valign: "middle", fontFace: SERIF, fontSize: 24, bold: true, color: GOLD });
    texto(s, p, M + 0.6, 1.6 + i * 0.95, 11.3, 0.7, { valign: "middle", fontSize: 15, color: "FFFFFF", lineSpacing: 20 });
  });
}

// referencias, com link
{
  const s = slideClaro("Referências", "fontes");
  const lista = (refs, x, w) => {
    const runs = [];
    refs.forEach((r, k) => {
      const fim = k < refs.length - 1;
      if (!r[1]) { runs.push({ text: r[0], options: { color: INK2, breakLine: fim } }); return; }
      runs.push({ text: r[0] + " ", options: { color: INK2 } });
      const rot = r[1].includes("doi.org/") ? "doi:" + r[1].split("doi.org/")[1] : r[1].split("/")[2];
      runs.push({ text: rot, options: { hyperlink: { url: r[1] }, color: BLUE, breakLine: fim } });
    });
    s.addText(runs, { x, y: 1.95, w, h: 4.9, isTextBox: true, margin: 0, valign: "top",
      fontFace: SANS, fontSize: 10.5, lineSpacing: 14, paraSpaceAfter: 4 });
  };
  texto(s, "Literatura", M, 1.55, 6, 0.3, { fontSize: 13, bold: true, color: INK });
  texto(s, "Dados", 6.95, 1.55, 5.8, 0.3, { fontSize: 13, bold: true, color: INK });
  lista([
    ["Huff, D. (1964). Defining and estimating a trading area. Journal of Marketing 28(3).", L.huff[1]],
    ["Larson, R. (1974). A hypercube queuing model… Computers & Operations Research 1(1).", L.larson[1]],
    ["Daskin, M. (1983). A maximum expected covering location model. Transportation Science 17(1).", L.daskin[1]],
    ["ReVelle, C. & Hogan, K. (1989). The maximum availability location problem. Transportation Science 23(3).", L.revelle[1]],
    ["Deb, K. et al. (2002). A fast and elitist multiobjective genetic algorithm: NSGA-II. IEEE Trans. Evol. Comput. 6(2).", L.deb[1]],
    ["Luo, W. & Wang, F. (2003). Measures of spatial accessibility to health care in a GIS environment. Env. & Planning B 30(6).", L.luo[1]],
    ["Takeda, R., Widmer, J. & Morabito, R. (2007). Ambulance decentralization… hypercube (SAMU Campinas). Computers & OR 34(3).", L.takeda[1]],
    ["Budge, S., Ingolfsson, A. & Erkut, E. (2009). Approximating vehicle dispatch probabilities… Operations Research 57(1).", L.budge[1]],
    ["Hora, R. S. et al. (2019). Caracterização do atendimento do SAMU às emergências clínicas. REME 23.", L.hora[1]],
    ["Malvestio, M. A. A. & Sousa, R. M. C. (2024). Produção de procedimentos pelo SAMU 192 no Brasil. Ciênc. Saúde Colet. 29(1).", L.malvestio[1]],
    ["Feldmeier, M. et al. (2024). Patterns in California ambulance patient offload times. JAMA Netw. Open 7(12).", L.feldmeier[1]]],
    M, 6.0);
  lista([
    ["DATASUS — SIA/SUS, notas técnicas.", L.sia[1]],
    ["DATASUS — arquivos PASP do SIA (FTP), jan/2024 a jul/2026.", L.ftp[1]],
    ["SIGTAP — Tabela Unificada de procedimentos (2026-07).", L.sigtap[1]],
    ["CNES — Cadastro Nacional de Estabelecimentos de Saúde (frota e bases).", L.cnes[1]],
    ["IBGE — Censo 2022, agregados por setor censitário.", L.ibge[1]],
    ["OpenStreetMap — malha de ruas (© colaboradores do OSM).", L.osm[1]],
    [`Prefeitura de SP — SAMU em 2024 (${mil(U.validacao_anual["2024"].prefeitura)} atendimentos presenciais).`, L.pref24[1]],
    [`Prefeitura de SP — SAMU em 2025 (${mil(U.validacao_anual["2025"].prefeitura)} atendimentos presenciais).`, L.pref25[1]],
    ["Prefeitura de SP — notícia de 21/12/2023 (frota, saídas por dia, tempo de chegada).", L.pref23[1]],
    ["Código e resultados do projeto: fase2_sao_paulo/ e dados/fase2/*.json; CONTEXTO_PROJETO.md §4.1 e §5.1.", null]],
    6.95, 5.75);
}

doc.writeFile({ fileName: SAIDA }).then(() => console.log("-> " + SAIDA + ` (${_pag} slides)`));
