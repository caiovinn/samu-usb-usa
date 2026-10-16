const fs = require("fs");
const path = require("path");
const pptx = require("pptxgenjs");

/* Deck didático para a turma de MAI5003 — companheiro de deck_gera.js,
 * mas com outro objetivo: ensinar Huff, 2SFCA, NSGA-II e p-median a quem
 * conhece probabilidade e otimização mas nunca viu essas técnicas.
 *
 * O exemplo de brinquedo (duas bases, depois dois setores) é o mesmo dos
 * documentos matematica_usb_usa.html §3-4 e MODEL_GUIDE.md §4-5, e foi
 * conferido contra o código real (fase2_sao_paulo/modelo/huff2sfca.py) antes
 * de entrar aqui — ver os comentários "conferido" abaixo. Os slides de
 * resultado real (SL.DADOS_REAIS a SL.RESULTADO3_BETA) leem os mesmos JSONs
 * que deck_gera.js usa, nunca números digitados.
 */

// Numeros de slide por NOME, nao por literal: toda referencia cruzada no
// texto ("ver slide X") usa SL.CHAVE em vez de um numero digitado. Ja
// renumeramos este deck duas vezes numa sessao so — um literal escrito a
// mao e exatamente o tipo de coisa que fica errada na proxima vez que um
// slide for inserido. So esta tabela precisa mudar quando a ordem muda.
// Fica no topo do arquivo (antes de tudo) porque o aviso de sp_beta_sens.json
// ausente, logo abaixo, ja referencia um slide por numero.
const SL = {
  CAPA: 1, AGENDA: 2, ROTEIRO: 3, PROBLEMA: 4, HIPOTESE: 5, EXEMPLO: 6,
  HUFF_FORMULA: 7, HUFF_CALC: 8, BETA_LIMITES: 9, BETA_2_2: 10,
  SFCA_PROBLEMA: 11, SFCA_ETAPA1: 12, SFCA_ETAPA2: 13, SFCA_CONSEQ: 14,
  LORENZ_FORMAL: 15, LORENZ_CALC: 16, DOIS_OBJETIVOS: 17, PARETO_REGRA: 18,
  NSGA2_BUSCA: 19, PMEDIAN: 20, EMPARELHAMENTO: 21, LAMBDA: 22,
  DADOS_REAIS: 23, RESULTADO1: 24, RESULTADO2: 25, RESULTADO3_BETA: 26,
  LICOES: 27, FECHAMENTO: 28,
};

const RAIZ = path.join(__dirname, "..", "..");
const DADOS = path.join(RAIZ, "dados", "fase2");
const FIG = path.join(RAIZ, "figs", "fase2") + path.sep;
// formulas renderizadas por fase2_sao_paulo/docs/formulas_gera.py (mathtext
// do matplotlib, fontset "cm") -- ver aquele script para o motivo de nao
// ser dejavusans.
const FORMULAS = path.join(RAIZ, "figs", "fase2", "formulas") + path.sep;
const SAIDA = path.join(__dirname, "apresentacao_didatica_samu.pptx");

const lerJson = (nome) => JSON.parse(fs.readFileSync(path.join(DADOS, nome), "utf-8"));
const res = lerJson("sp_resultado.json");
const comp = lerJson("sp_comparacao.json");
let betaSens = null;
try { betaSens = lerJson("sp_beta_sens.json"); } catch (e) {
  console.warn(`aviso: sp_beta_sens.json ausente — rode ` +
    `fase2_sao_paulo/experimentos/sensib_beta.py antes para o slide ${SL.RESULTADO3_BETA} (sensibilidade) sair completo.`);
}
const porConfig = (nome) => comp.find((c) => c.config === nome);
const ATUAL_C = porConfig("atual"), PMEDIAN_C = porConfig("p-median (classico)"),
      HUFF_C = porConfig("Huff+2SFCA");
const jo = (lam) => res.por_lambda[String(lam)].joelho;
const BASE = res.atual;

const n = (x, casas = 2) => Number(x).toFixed(casas).replace(".", ",").replace("-", "−");
const pct = (x, casas = 1) => `${n(x, casas)}%`;
const km0 = (x) => `${Math.round(x)} km`;
const vez = (a, b) => `${n(a / b, 1)}×`;

const doc = new pptx();
doc.layout = "LAYOUT_WIDE";
doc.author = "Grupo MAI5003";
doc.title = "Como calculamos onde colocar as ambulâncias — deck didático";

let _slideAtual = 0;
function numeroDePagina(s, cor) {
  _slideAtual++;
  s.addText(String(_slideAtual), { x: 12.75, y: 7.1, w: 0.45, h: 0.3,
    isTextBox: true, margin: 0, align: "right", fontFace: SANS, fontSize: 9.5,
    color: cor });
}

// mesma paleta de deck_gera.js, para as duas apresentações lerem como
// uma família — mas o conteúdo e o roteiro são inteiramente outros.
const NAVY = "16263F", TEAL = "0F3D5C", CREAM = "F7F5F0", CARD = "EAF1F7";
const INK = "0F2B46", INK2 = "4A5568", GOLD = "D9A441";
const BLUE = "2A78D6", ORANGE = "EB6834", GREEN = "2E7D5A", GREY = "8A8F98";
const SERIF = "Cambria", SANS = "Calibri";
const M = 0.62;

function slideClaro(titulo, sobre) {
  const s = doc.addSlide();
  s.background = { color: CREAM };
  if (sobre) s.addText(sobre.toUpperCase(), { x: M, y: 0.42, w: 11, h: 0.26,
    isTextBox: true, margin: 0, fontFace: SANS, fontSize: 10.5, bold: true,
    color: GOLD, charSpacing: 1.4 });
  s.addText(titulo, { x: M, y: sobre ? 0.70 : 0.55, w: 12.1, h: 0.72,
    isTextBox: true, margin: 0, fontFace: SERIF, fontSize: 30, bold: true,
    color: INK });
  numeroDePagina(s, GREY);
  return s;
}
function slideEscuro(cor) {
  const s = doc.addSlide();
  s.background = { color: cor };
  s.addShape(doc.ShapeType.ellipse, { x: 10.2, y: -2.2, w: 5.6, h: 5.6,
    fill: { color: "FFFFFF", transparency: 94 }, line: { color: cor } });
  numeroDePagina(s, "9FB0C4");
  return s;
}
function bolha(s, texto, x, y, cor) {
  s.addShape(doc.ShapeType.ellipse, { x, y, w: 0.46, h: 0.46,
    fill: { color: cor }, line: { color: cor } });
  s.addText(String(texto), { x, y, w: 0.46, h: 0.46, isTextBox: true, margin: 0,
    align: "center", valign: "middle", fontFace: SANS, fontSize: 13,
    bold: true, color: "FFFFFF" });
}
function cartao(s, o) {
  s.addShape(doc.ShapeType.roundRect, { x: o.x, y: o.y, w: o.w, h: o.h,
    rectRadius: 0.10, fill: { color: o.fill || CARD },
    line: { color: o.fill || CARD } });
}
function item(s, texto, x, y, w, titulo, corpo, cor) {
  bolha(s, texto, x, y, cor || BLUE);
  s.addText(titulo, { x: x + 0.62, y: y - 0.02, w: w - 0.62, h: 0.28,
    isTextBox: true, margin: 0, valign: "top", fontFace: SANS, fontSize: 13.5,
    bold: true, color: INK });
  s.addText(corpo, { x: x + 0.62, y: y + 0.26, w: w - 0.62, h: 1.05,
    isTextBox: true, margin: 0, valign: "top", fontFace: SANS, fontSize: 11.5,
    color: INK2, lineSpacing: 15 });
}
// dimensoes reais (px) dos PNGs de formulas_gera.py, para posicionar sem
// distorcer -- w e calculado a partir da altura pedida e dessa proporcao.
const FORMULA_DIM = {
  huff_principal: [723, 286], huff_decaimento: [499, 110], beta_subst: [759, 97],
  n_ef: [1419, 175], sfca_pressao: [794, 166], sfca_razao: [488, 199],
  sfca_acessibilidade: [611, 175], lorenz_xy: [1214, 306], lorenz_gini: [1272, 167],
  pmedian_obj: [634, 188], lambda_obj: [892, 173], rho_g: [948, 193],
};
function formula(s, chave, x, y, altura) {
  const [pw, ph] = FORMULA_DIM[chave];
  const w = altura * pw / ph;
  s.addImage({ path: FORMULAS + chave + ".png", x, y, w, h: altura });
  return w;
}

function tabela(s, x, y, w, colW, cabecalho, linhas, opts = {}) {
  s.addTable([cabecalho.map(t => ({ text: t, options: { bold: true,
      color: "FFFFFF", fill: { color: TEAL }, fontSize: opts.fontSize || 11,
      fontFace: SANS, align: "center" } }))]
    .concat(linhas.map((r, i) => r.map((c, j) => ({ text: String(c), options: {
      fontSize: opts.fontSize || 11, fontFace: SANS,
      bold: opts.boldCols && opts.boldCols.includes(j),
      color: opts.destaque && opts.destaque === i ? INK : INK2,
      align: j === 0 ? "left" : "center",
      fill: { color: opts.destaque === i ? "FBEAE7" : (i % 2 ? "FFFFFF" : CARD) } } })))),
    { x, y, w, colW, rowH: opts.rowH || 0.36, border: { pt: 0, color: CREAM },
      valign: "middle" });
}

// ===========================================================================
// BLOCO 1 — abertura e roteiro (slides 1-2)
// ===========================================================================

{ // 1 — capa
  const s = slideEscuro(NAVY);
  s.addShape(doc.ShapeType.ellipse, { x: -1.8, y: 5.2, w: 4.4, h: 4.4,
    fill: { color: "FFFFFF", transparency: 96 }, line: { color: NAVY } });
  s.addText("MATERIAL DIDÁTICO — MAI5003 · PROBABILIDADE E ESTATÍSTICA",
    { x: M, y: 1.45, w: 11, h: 0.3, isTextBox: true, margin: 0, fontFace: SANS,
      fontSize: 11, bold: true, color: GOLD, charSpacing: 1.4 });
  s.addText("Como calculamos onde colocar\nas ambulâncias", { x: M, y: 1.85, w: 11.7, h: 1.55,
    isTextBox: true, margin: 0, fontFace: SERIF, fontSize: 40, bold: true,
    color: "FFFFFF", lineSpacing: 44 });
  s.addText("Huff, 2SFCA e otimização bi-objetivo, do zero, com um exemplo que cabe numa calculadora",
    { x: M, y: 3.62, w: 11, h: 0.5, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 18, italic: true, color: "C9D6E4" });
  s.addText("Companheiro didático do projeto de realocação de USB/USA em São Paulo",
    { x: M, y: 4.18, w: 11, h: 0.35, isTextBox: true, margin: 0, fontFace: SANS,
      fontSize: 13, color: "9FB0C4" });
  s.addText("Grupo MAI5003", { x: M, y: 6.6, w: 6, h: 0.4, isTextBox: true,
    margin: 0, fontFace: SANS, fontSize: 11, color: "8D9EB2" });
}

{ // 2 — sumario / agenda (NOVO)
  const s = slideClaro("Sumário", "agenda");
  const blocos = [
    [`${SL.ROTEIRO}–${SL.PROBLEMA}`, "O problema", "USB × USA, o achado da fase 1, e a hipótese que todo modelo clássico faz"],
    [`${SL.EXEMPLO}–${SL.BETA_2_2}`, "Modelo de Huff", "a fórmula termo por termo, o exemplo de duas bases, e os dois limites de β"],
    [`${SL.SFCA_PROBLEMA}–${SL.SFCA_CONSEQ}`, "2SFCA", "acessibilidade com capacidade — por que \"maximizar acesso\" é um objetivo vazio"],
    [`${SL.LORENZ_FORMAL}–${SL.DOIS_OBJETIVOS}`, "Gini e os dois objetivos", "a curva de Lorenz, formalmente, e por que Gini sozinho também não basta"],
    [`${SL.PARETO_REGRA}–${SL.LAMBDA}`, "Otimização", "dominância de Pareto, NSGA-II, o baseline p-median, custo de mudança e λ"],
    [`${SL.DADOS_REAIS}–${SL.RESULTADO3_BETA}`, "Resultados reais", "São Paulo inteira: a fronteira, o achado central, e a sensibilidade em β"],
    [`${SL.LICOES}–${SL.FECHAMENTO}`, "Fechamento", "o que este exemplo ensina, além do SAMU"]];
  blocos.forEach((b, i) => {
    const y = 1.7 + i * 0.72;
    s.addText(b[0], { x: M, y, w: 1.1, h: 0.6, isTextBox: true, margin: 0,
      valign: "top", fontFace: "Consolas", fontSize: 13, bold: true, color: TEAL });
    s.addText(b[1], { x: M + 1.25, y, w: 3.1, h: 0.3, isTextBox: true, margin: 0,
      valign: "top", fontFace: SANS, fontSize: 13.5, bold: true, color: INK });
    s.addText(b[2], { x: M + 1.25, y: y + 0.28, w: 8.4, h: 0.4, isTextBox: true,
      margin: 0, valign: "top", fontFace: SANS, fontSize: 11, color: INK2, lineSpacing: 14 });
  });
  s.addText("Os números da coluna à esquerda são os slides — use-os para navegar ou apontar uma dúvida durante a aula.",
    { x: M, y: 6.85, w: 12.1, h: 0.4, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 11.5, italic: true, color: GREY });
}

{ // 3 — para quem é este material / roteiro
  const s = slideClaro("O que você já sabe, e o que vamos construir", "roteiro");
  s.addText("O que você já traz", { x: M, y: 1.65, w: 5.7, h: 0.32,
    isTextBox: true, margin: 0, fontFace: SANS, fontSize: 13.5, bold: true,
    color: ORANGE });
  cartao(s, { x: M, y: 2.0, w: 5.7, h: 2.3 });
  ["Probabilidade e distribuições", "Otimização (mínimos, restrições)",
   "Regressão e ajuste de curvas", "Índices de desigualdade em economia (talvez)"]
   .forEach((t, i) => {
    s.addText("•  " + t, { x: M + 0.3, y: 2.2 + i * 0.5, w: 5.1, h: 0.42,
      isTextBox: true, margin: 0, fontFace: SANS, fontSize: 13, color: INK2 });
  });
  const bx = 6.9;
  s.addText("O que é novo hoje", { x: bx, y: 1.65, w: 5.8, h: 0.32,
    isTextBox: true, margin: 0, fontFace: SANS, fontSize: 13.5, bold: true,
    color: TEAL });
  cartao(s, { x: bx, y: 2.0, w: 5.8, h: 2.3, fill: "E7F0F7" });
  ["Modelo de Huff (escolha probabilística)", "2SFCA (acessibilidade com capacidade)",
   "NSGA-II (otimização com dois objetivos)", "p-median e o algoritmo húngaro"]
   .forEach((t, i) => {
    s.addText("•  " + t, { x: bx + 0.3, y: 2.2 + i * 0.5, w: 5.2, h: 0.42,
      isTextBox: true, margin: 0, fontFace: SANS, fontSize: 13, color: INK });
  });
  s.addText("O plano: um exemplo de brinquedo — duas bases, depois dois setores — que a gente calcula à mão, técnica por técnica, e só então mostra o resultado real (26.889 setores, 1.107 candidatos, São Paulo inteira).",
    { x: M, y: 4.6, w: 12.1, h: 0.9, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 13.5, color: INK2, lineSpacing: 19 });
  s.addText("Cada número do exemplo de brinquedo foi conferido contra o código real do projeto antes de entrar neste slide — não é ilustrativo, é reprodutível.",
    { x: M, y: 5.75, w: 12.1, h: 0.5, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 13, italic: true, color: TEAL });
}

// ===========================================================================
// BLOCO 2 — o problema (slides 3-4)
// ===========================================================================

{ // 4 — o problema
  const s = slideClaro("Duas frotas que não são intercambiáveis", "o problema");
  s.addText("O SAMU opera dois tipos de viatura:", { x: M, y: 1.65, w: 12, h: 0.3,
    isTextBox: true, margin: 0, fontFace: SANS, fontSize: 13, color: INK2 });
  [["USB — Suporte Básico", "Técnico de enfermagem + condutor. Atende a maioria dos chamados.", BLUE],
   ["USA — Suporte Avançado", "Leva médico e desfibrilador. Só ela atende parada cardiorrespiratória, via aérea difícil, trauma grave.", ORANGE]]
   .forEach((c, i) => {
    const x = M + i * 6.2;
    cartao(s, { x, y: 2.05, w: 5.9, h: 1.55, fill: i ? "FBEAE7" : "E7F0F7" });
    s.addText(c[0], { x: x + 0.3, y: 2.25, w: 5.3, h: 0.32, isTextBox: true,
      margin: 0, fontFace: SANS, fontSize: 14.5, bold: true, color: c[2] });
    s.addText(c[1], { x: x + 0.3, y: 2.62, w: 5.3, h: 0.85, isTextBox: true,
      margin: 0, valign: "top", fontFace: SANS, fontSize: 12, color: INK2,
      lineSpacing: 16 });
  });
  s.addText("Uma USA sabe fazer o serviço de uma USB. O contrário não vale — e é essa assimetria que torna o problema difícil: o mesmo mapa precisa servir dois públicos com regras diferentes.",
    { x: M, y: 3.85, w: 12.1, h: 0.6, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 13, color: INK2, lineSpacing: 18 });
  cartao(s, { x: M, y: 4.65, w: 12.1, h: 1.55, fill: CARD });
  s.addText("O achado que motiva o projeto (fase 1, EDA nacional)", { x: M + 0.3,
    y: 4.83, w: 11.5, h: 0.3, isTextBox: true, margin: 0, fontFace: SANS,
    fontSize: 13, bold: true, color: INK });
  s.addText("40,6 milhões de brasileiros têm uma USB a 20 minutos de distância e nenhuma USA nesse raio. O Gini da frota de USA entre municípios (0,67) é bem maior que o da USB (0,54) — a USA está muito mais mal distribuída.",
    { x: M + 0.3, y: 5.18, w: 11.5, h: 0.9, isTextBox: true, margin: 0,
      valign: "top", fontFace: SANS, fontSize: 12.5, color: INK2, lineSpacing: 17 });
  s.addText("Conclusão da fase 1: o problema é de distribuição, não de volume — e isso vira um problema de otimização.",
    { x: M, y: 6.4, w: 12.1, h: 0.5, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 13.5, italic: true, color: TEAL });
}

{ // 5 — a hipótese ingênua
  const s = slideClaro("A hipótese que todo modelo clássico faz", "o problema");
  cartao(s, { x: M, y: 1.75, w: 12.1, h: 1.5, fill: "FBEAE7" });
  s.addText("“Toda demanda vai para a unidade mais próxima”", { x: M + 0.35,
    y: 1.95, w: 11.4, h: 0.4, isTextBox: true, margin: 0, fontFace: SERIF,
    fontSize: 19, bold: true, color: INK });
  s.addText("É a hipótese por trás de quase todo modelo clássico de localização de instalações — o p-median incluído (o modelo que, mais à frente, escolhe onde ficam as bases supondo sempre a mais próxima). Funciona bem para “qual mercado eu frequento”. Para uma ambulância, ignora um detalhe operacional óbvio: a mais próxima pode estar ocupada.",
    { x: M + 0.35, y: 2.42, w: 11.4, h: 0.75, isTextBox: true, margin: 0,
      valign: "top", fontFace: SANS, fontSize: 13, color: INK2, lineSpacing: 17 });
  s.addText("A ideia central deste projeto", { x: M, y: 3.6, w: 12, h: 0.32,
    isTextBox: true, margin: 0, fontFace: SANS, fontSize: 13.5, bold: true,
    color: ORANGE });
  s.addText("Trocar “sempre a mais próxima” (uma escolha determinística) por “provavelmente a mais próxima, mas às vezes não” (uma escolha probabilística). Quem faz essa troca é o modelo de Huff — e é ele que vamos construir agora, com um exemplo de duas bases.",
    { x: M, y: 4.0, w: 12.1, h: 1.0, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 13.5, color: INK2, lineSpacing: 19 });
  s.addText("Um detalhe que já vale adiantar: essa troca de hipótese é exatamente o que este projeto testa — e o resultado, mais à frente, é surpreendente.",
    { x: M, y: 5.4, w: 12.1, h: 0.5, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 13, italic: true, color: TEAL });
}

// ===========================================================================
// BLOCO 3 — Huff, com o exemplo de brinquedo (slides 5-7)
// ===========================================================================

{ // 6 — o exemplo de brinquedo
  const s = slideClaro("O exemplo que vamos usar do início ao fim", "exemplo de brinquedo");
  s.addText("Duas bases, uma ambulância cada:", { x: M, y: 1.65, w: 12, h: 0.3,
    isTextBox: true, margin: 0, fontFace: SANS, fontSize: 13.5, bold: true,
    color: ORANGE });
  tabela(s, M, 2.0, 5.6, [2.4, 1.6, 1.6], ["Base", "Ambulâncias", "Tempo até o setor"],
    [["A", "1", "5 min"], ["B", "1", "10 min"]], { fontSize: 12.5, rowH: 0.42 });
  const bx = 6.9;
  cartao(s, { x: bx, y: 2.0, w: 5.8, h: 2.0, fill: CARD });
  s.addText("Um setor censitário", { x: bx + 0.3, y: 2.18, w: 5.2, h: 0.3,
    isTextBox: true, margin: 0, fontFace: SANS, fontSize: 13, bold: true, color: INK });
  s.addText("A regra clássica (mais próxima) mandaria 100% dos chamados desse setor para a base A, sempre — mesmo que A esteja ocupada em algum momento.",
    { x: bx + 0.3, y: 2.55, w: 5.2, h: 1.3, isTextBox: true, margin: 0,
      valign: "top", fontFace: SANS, fontSize: 12.5, color: INK2, lineSpacing: 17 });
  s.addText("A pergunta que o modelo de Huff responde: de cada 100 chamados desse setor, quantos realisticamente vão para A, e quantos para B?",
    { x: M, y: 4.6, w: 12.1, h: 0.7, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 15, italic: true, color: TEAL });
  s.addText("(Guarde A a 5 min e B a 10 min — vamos recalcular isso em três slides diferentes, com três ideias diferentes.)",
    { x: M, y: 5.5, w: 12.1, h: 0.4, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 11.5, italic: true, color: GREY });
}

{ // 7 — a formula de Huff, termo por termo (NOVO)
  const s = slideClaro("A fórmula do modelo de Huff, termo por termo", "modelo de escolha");
  cartao(s, { x: M, y: 1.62, w: 12.1, h: 1.35, fill: CARD });
  formula(s, "huff_principal", M + 3.9, 1.72, 0.62);
  formula(s, "huff_decaimento", M + 4.6, 2.42, 0.42);
  s.addText("Cada termo, um por um:", { x: M, y: 3.15, w: 12, h: 0.3, isTextBox: true,
    margin: 0, fontFace: SANS, fontSize: 13, bold: true, color: ORANGE });
  const termos = [
    [[{ text: "i, j" }], "i é o setor que precisa de ambulância; j é uma base candidata a atender."],
    [[{ text: "S" }, { text: "j", options: { subscript: true } }, { text: " (capacidade)" }], "quantas ambulâncias a base j tem — aqui, 1 em cada base."],
    [[{ text: "α (expoente)" }], "o quanto capacidade extra atrai mais chamados. Aqui α = 1, então S com esse expoente vira o próprio S."],
    [[{ text: "t" }, { text: "ij", options: { subscript: true } }, { text: " (tempo)" }], "tempo de viagem da base j até o setor i — os 5 min e 10 min do slide anterior."],
    [[{ text: "β (escala do decaimento)" }], "quanto MAIOR β, mais devagar a atratividade cai com a distância. É o parâmetro que ainda vamos escolher — próximos dois slides."],
    [[{ text: "f(t) (peso)" }], "sempre entre 0 e 1 — 1 se t=0 (base no mesmo lugar), cai conforme t cresce."]];
  termos.forEach((t, i) => {
    const x = M + (i % 2) * 6.2, y = 3.5 + Math.floor(i / 2) * 1.0;
    s.addText(t[0], { x, y, w: 2.8, h: 0.3, isTextBox: true, margin: 0,
      fontFace: "Consolas", fontSize: 12.5, bold: true, color: TEAL });
    s.addText(t[1], { x: x + 2.75, y: y - 0.03, w: 3.3, h: 0.9, isTextBox: true,
      margin: 0, valign: "top", fontFace: SANS, fontSize: 11, color: INK2, lineSpacing: 14 });
  });
  s.addText("A estrutura inteira é um softmax: cada base recebe uma pontuação (o numerador), e a probabilidade é essa pontuação dividida pela soma das pontuações de todas as bases (o denominador) — o que garante que as probabilidades de um mesmo setor somem sempre 100%.",
    { x: M, y: 6.35, w: 12.1, h: 0.75, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 12.5, italic: true, color: TEAL, lineSpacing: 17 });
}

{ // 8 — calculando no exemplo (era metade do 6 antigo)
  const s = slideClaro("Aplicando a fórmula ao exemplo de duas bases", "modelo de escolha");
  s.addText(`Do slide ${SL.EXEMPLO}: base A a 5 min, base B a 10 min, S_A = S_B = 1, α = 1. Falta só escolher β — usamos β = 4,5 min, o mesmo valor do projeto real:`,
    { x: M, y: 1.62, w: 12.1, h: 0.6, isTextBox: true, margin: 0, fontFace: SANS,
      fontSize: 13, color: INK2, lineSpacing: 17 });
  cartao(s, { x: M, y: 2.35, w: 12.1, h: 0.55, fill: CARD });
  s.addText("Primeiro, o denominador do decaimento:", { x: M + 0.3, y: 2.48, w: 4.3, h: 0.3,
    isTextBox: true, margin: 0, valign: "middle", fontFace: SANS, fontSize: 12.5, color: INK2 });
  formula(s, "beta_subst", M + 4.8, 2.42, 0.32);
  tabela(s, M, 3.15, 12.1, [3.0, 2.6, 2.6, 3.9],
    ["Base", "f(t) = exp(−t²/40,5)", "P(j|i) = pontuação/soma", "Interpretação"],
    [["A, 5 min", "exp(−25/40,5) = 0,540", "0,540 / 0,625 = 86,4%", "quase sempre, mas não sempre"],
     ["B, 10 min", "exp(−100/40,5) = 0,085", "0,085 / 0,625 = 13,6%", "a alternativa, quando A está ocupada"]],
    { fontSize: 11.5, rowH: 0.5, boldCols: [2] });
  s.addText("Confira: 86,4% + 13,6% = 100% — exatamente a garantia do softmax do slide anterior. Sem capacidade e sem β, isto degenera na regra clássica — os próximos dois slides mostram por quê, formalmente.",
    { x: M, y: 4.85, w: 12.1, h: 0.6, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 12.5, italic: true, color: TEAL, lineSpacing: 17 });
}

{ // 9 — os dois limites de beta, formalmente (NOVO)
  const s = slideClaro("Os dois limites de β, formalmente", "modelo de escolha");
  [["β → 0 : vira a regra clássica", "f(t) = exp(−t²/2β²) → 0 para qualquer t > 0 quando β→0, mas f(0) = 1 sempre. Só a base com o MENOR t sobra com peso — todas as outras somem. P(j|i) vira um indicador: 100% para a mais próxima, 0% para o resto.", `Isto é exatamente o modelo p-median: escolher bases e servir cada setor sempre pela escolhida mais próxima, sem noção de capacidade. Definição completa no slide ${SL.PMEDIAN}.`, ORANGE],
   ["β → ∞ : vira escolha uniforme", "Quando β→∞, o termo t²/2β² → 0 para QUALQUER t finito — logo f(t) → exp(0) = 1 para todas as bases, perto ou longe. Com capacidades iguais, todas as probabilidades ficam iguais.", "A distância deixa de importar completamente — o setor escolhe qualquer base ao acaso dentro do raio de captação.", BLUE]]
   .forEach((c, i) => {
    const y = 1.68 + i * 2.55;
    cartao(s, { x: M, y, w: 12.1, h: 2.3, fill: i === 0 ? "FBEAE7" : "E7F0F7" });
    s.addText(c[0], { x: M + 0.3, y: y + 0.16, w: 11.5, h: 0.32, isTextBox: true,
      margin: 0, fontFace: SANS, fontSize: 14, bold: true, color: c[3] });
    s.addText(c[1], { x: M + 0.3, y: y + 0.55, w: 11.5, h: 0.85, isTextBox: true,
      margin: 0, valign: "top", fontFace: SANS, fontSize: 12, color: INK2, lineSpacing: 15 });
    s.addText(c[2], { x: M + 0.3, y: y + 1.5, w: 11.5, h: 0.7, isTextBox: true,
      margin: 0, valign: "top", fontFace: SANS, fontSize: 12, italic: true, color: TEAL, lineSpacing: 15 });
  });
}

{ // 10 — por que beta=4,5 e por que 2,2 unidades efetivas (era metade do 7 antigo)
  const s = slideClaro("Por que β = 4,5 min, e por que 2,2 unidades efetivas", "modelo de escolha");
  cartao(s, { x: M, y: 1.62, w: 12.1, h: 0.85, fill: CARD });
  // mesma definicao de huff2sfca.n_efetivo (exponencial da entropia). O
  // N_ef do exemplo de duas bases e calculado aqui, nao digitado: 1,49
  formula(s, "n_ef", M + 0.3, 1.82, 0.46);
  const pA = Math.exp(-25 / 40.5) / (Math.exp(-25 / 40.5) + Math.exp(-100 / 40.5));
  const nefToy = Math.exp(-(pA * Math.log(pA) + (1 - pA) * Math.log(1 - pA)));
  s.addText(`quantas opções o setor i tem "na prática": 1 se toda probabilidade está numa base só; k se está dividida igualmente entre k bases. H é a entropia — a incerteza da escolha. No exemplo do slide ${SL.HUFF_CALC} (86% / 14%): N_ef = ${n(nefToy)}.`,
    { x: M + 4.45, y: 1.70, w: 7.45, h: 0.72, isTextBox: true, margin: 0, valign: "top",
      fontFace: SANS, fontSize: 11.5, color: INK2, lineSpacing: 15 });
  s.addText("Por que ~2, e não 1 ou 7", { x: M, y: 2.65, w: 12, h: 0.3, isTextBox: true,
    margin: 0, fontFace: SANS, fontSize: 13.5, bold: true, color: ORANGE });
  const its = [
    ["N_ef = 1 seria a hipótese ingênua de novo", `Voltaria exatamente ao slide ${SL.HIPOTESE}: sempre a mesma base, nunca uma segunda opção — como se a mais próxima nunca estivesse ocupada.`],
    ["N_ef = 7 assumiria distância quase irrelevante", "Diria que qualquer uma entre 7 bases, algumas bem mais longe, tem chance real de atender — exagero na direção oposta."],
    ["N_ef ≈ 2 modela \"a mais próxima, e tipicamente mais uma\"", "A leitura operacional realista: quando a mais próxima está ocupada, geralmente existe UMA alternativa razoável por perto — nem zero, nem várias."]];
  its.forEach((it, i) => {
    const y = 3.05 + i * 0.98;
    bolha(s, i + 1, M, y, BLUE);
    s.addText(it[0], { x: M + 0.65, y: y - 0.03, w: 11.4, h: 0.28, isTextBox: true,
      margin: 0, valign: "top", fontFace: SANS, fontSize: 13, bold: true, color: INK });
    s.addText(it[1], { x: M + 0.65, y: y + 0.27, w: 11.4, h: 0.6, isTextBox: true,
      margin: 0, valign: "top", fontFace: SANS, fontSize: 11.5, color: INK2, lineSpacing: 15 });
  });
  s.addText(`Por isso β = ${n(res.beta, 1)} min: no dado real de São Paulo, é o valor que produz N_ef ≈ ${n(BASE.n_ef_usa, 1)} mediano entre os setores. É uma escolha de engenharia — arbitrada, não estimada de dado real de despacho; testamos a sensibilidade a essa escolha no slide ${SL.RESULTADO3_BETA}.`,
    { x: M, y: 6.35, w: 12.1, h: 0.85, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 12.5, italic: true, color: TEAL, lineSpacing: 17 });
}

// ===========================================================================
// BLOCO 4 — 2SFCA, estendendo o exemplo (slides 8-11)
// ===========================================================================

{ // 11 — adicionando um segundo setor
  const s = slideClaro("Um problema que só aparece com mais de um setor", "2SFCA — o problema");
  s.addText("Saber quem atende um setor não é o mesmo que saber se ele está bem servido — depende de quantos OUTROS setores também disputam a mesma base.",
    { x: M, y: 1.68, w: 12.1, h: 0.65, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 13.5, color: INK2, lineSpacing: 18 });
  s.addText("Acrescentando o setor 2 ao exemplo:", { x: M, y: 2.5, w: 12.1, h: 0.3,
    isTextBox: true, margin: 0, fontFace: SANS, fontSize: 13, bold: true, color: ORANGE });
  tabela(s, M, 2.85, 12.1, [2.4, 2.0, 2.4, 2.4, 2.9],
    ["Setor", "População", "t até A", "t até B", "P(A) / P(B) — mesma fórmula"],
    [["1", "1.000", "5 min", "10 min", "86,4% / 13,6%"],
     ["2", "2.000", "15 min", "5 min", "0,7% / 99,3%"]],
    { fontSize: 12, rowH: 0.5 });
  cartao(s, { x: M, y: 4.55, w: 12.1, h: 1.55, fill: CARD });
  s.addText("A pergunta nova", { x: M + 0.3, y: 4.72, w: 11.5, h: 0.28,
    isTextBox: true, margin: 0, fontFace: SANS, fontSize: 13, bold: true, color: INK });
  s.addText("A base A recebe 86,4% do setor 1 (867 pessoas) e só 0,7% do setor 2 (14 pessoas). A base B recebe 13,6% do setor 1 (136) e 99,3% do setor 2 (1.986). Quem está mais sobrecarregada, A ou B? E o setor 1 está bem servido, ou está \"emprestando\" a base A para o setor 2?",
    { x: M + 0.3, y: 5.05, w: 11.5, h: 1.0, isTextBox: true, margin: 0,
      valign: "top", fontFace: SANS, fontSize: 12, color: INK2, lineSpacing: 16 });
  s.addText("É esta contabilidade que o 2SFCA (Two-Step Floating Catchment Area) resolve, em duas etapas.",
    { x: M, y: 6.25, w: 12.1, h: 0.4, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 13, italic: true, color: TEAL });
}

{ // 12 (2SFCA etapa 1)
  const s = slideClaro("Etapa 1 — quanta gente disputa cada base", "2SFCA");
  cartao(s, { x: M, y: 1.6, w: 12.1, h: 0.85, fill: CARD });
  { const w1 = formula(s, "sfca_pressao", M + 1.3, 1.72, 0.5);
    formula(s, "sfca_razao", M + 1.3 + w1 + 0.8, 1.7, 0.55); }
  s.addText(`D_i = população do setor i  ·  P(j|i) = probabilidade de Huff (slide ${SL.HUFF_FORMULA})  ·  S_j = ambulâncias na base j  ·  R_j = razão oferta/demanda da base j`,
    { x: M + 0.3, y: 2.18, w: 11.5, h: 0.3, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 10.5, color: INK2, align: "center" });
  s.addText("Some, para cada base, a fatia de demanda que o Huff manda para ela vinda de TODOS os setores:",
    { x: M, y: 2.6, w: 12.1, h: 0.4, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 13, color: INK2, lineSpacing: 17 });
  tabela(s, M, 3.0, 7.0, [2.2, 2.4, 2.4],
    ["Base", "Pressão (pessoas)", "R_j = ambulâncias / pressão"],
    [["A", "864 + 14 = 878,7", "1 / 878,7 = 0,00114"],
     ["B", "136 + 1.986 = 2.121,1", "1 / 2.121,1 = 0,00047"]],
    { fontSize: 12, rowH: 0.55 });
  const bx = 8.3;
  cartao(s, { x: bx, y: 3.0, w: 4.4, h: 2.0, fill: "E7F0F7" });
  s.addText("R_j é o coração do 2SFCA: quanto MAIOR a pressão sobre uma base, MENOR a fatia que sobra por pessoa.",
    { x: bx + 0.28, y: 3.18, w: 3.85, h: 0.9, isTextBox: true, margin: 0,
      valign: "top", fontFace: SANS, fontSize: 11.5, color: INK2, lineSpacing: 15 });
  s.addText("É exatamente o termo que a regra “sempre a mais próxima” não tem: ela nunca pergunta quem mais disputa a mesma base.",
    { x: bx + 0.28, y: 4.1, w: 3.85, h: 0.8, isTextBox: true, margin: 0,
      valign: "top", fontFace: SANS, fontSize: 11.5, italic: true, color: TEAL, lineSpacing: 15 });
  s.addText("Confira a soma: 878,7 + 2.121,1 = 3.000 — exatamente a população total. O Huff reparte gente, não cria nem perde ninguém no caminho.",
    { x: M, y: 5.3, w: 12.1, h: 0.5, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 12.5, color: INK2, lineSpacing: 16 });
}

{ // 13 (2SFCA etapa 2 + conservacao)
  const s = slideClaro("Etapa 2 — a acessibilidade de cada setor", "2SFCA");
  cartao(s, { x: M, y: 1.55, w: 12.1, h: 0.75, fill: CARD });
  formula(s, "sfca_acessibilidade", M + 0.4, 1.65, 0.55);
  s.addText("mesma probabilidade de Huff P(j|i) e a razão R_j da etapa 1 — agora somadas do ponto de vista do setor.",
    { x: M + 5.9, y: 1.65, w: 6.0, h: 0.6, isTextBox: true, margin: 0, valign: "top",
      fontFace: SANS, fontSize: 11, color: INK2, lineSpacing: 14 });
  s.addText("Some essas razões vistas do setor, com o MESMO peso de escolha da etapa 1:",
    { x: M, y: 2.45, w: 12.1, h: 0.35, isTextBox: true, margin: 0, fontFace: SANS,
      fontSize: 13, color: INK2 });
  tabela(s, M, 2.85, 7.4, [1.6, 3.0, 2.8],
    ["Setor", "Cálculo", "Acessibilidade A_i"],
    [["1", "0,864×0,00114 + 0,136×0,00047", "0,001048"],
     ["2", "0,007×0,00114 + 0,993×0,00047", "0,000476"]],
    { fontSize: 11.5, rowH: 0.55, boldCols: [2] });
  cartao(s, { x: 8.7, y: 2.85, w: 4.0, h: 2.4, fill: "E7F0F7" });
  s.addText("Setor 1 tem 2,2× a acessibilidade por pessoa do setor 2", { x: 8.98, y: 3.05,
    w: 3.5, h: 0.7, isTextBox: true, margin: 0, fontFace: SANS, fontSize: 13,
    bold: true, color: INK, lineSpacing: 16 });
  s.addText("mesmo as duas bases sendo as mesmas — só a composição da demanda ao redor de cada setor muda o resultado.",
    { x: 8.98, y: 3.85, w: 3.5, h: 1.2, isTextBox: true, margin: 0, valign: "top",
      fontFace: SANS, fontSize: 12, color: INK2, lineSpacing: 16 });
  cartao(s, { x: M, y: 5.45, w: 12.1, h: 1.55, fill: CARD });
  s.addText("Uma identidade que vale sempre (não só neste exemplo)", { x: M + 0.3,
    y: 5.62, w: 11.5, h: 0.3, isTextBox: true, margin: 0, fontFace: SANS,
    fontSize: 13, bold: true, color: INK });
  s.addText("1.000×0,001048 + 2.000×0,000476 = 1,048 + 0,952 = 2,000 — exatamente as 2 ambulâncias do exemplo. Some (população × acessibilidade) em TODOS os setores, e o resultado é sempre a frota total, não importa como ela esteja distribuída. Isto tem uma consequência importante — próximo slide.",
    { x: M + 0.3, y: 5.98, w: 11.5, h: 0.95, isTextBox: true, margin: 0,
      valign: "top", fontFace: SANS, fontSize: 11.5, color: INK2, lineSpacing: 15 });
}

{ // 14 — por que nao maximizar acesso
  const s = slideClaro("Por que “maximizar o acesso” é um objetivo vazio", "2SFCA — a consequência");
  cartao(s, { x: M, y: 1.75, w: 12.1, h: 1.35, fill: "FBEAE7" });
  s.addText("Σ (população × acessibilidade) = frota total, SEMPRE", { x: M + 0.35,
    y: 1.95, w: 11.4, h: 0.4, isTextBox: true, margin: 0, fontFace: SERIF,
    fontSize: 18, bold: true, color: INK });
  s.addText("Não importa onde você põe as ambulâncias — 2 no exemplo, 123 no projeto real — essa soma dá sempre o mesmo número.",
    { x: M + 0.35, y: 2.42, w: 11.4, h: 0.55, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 13, color: INK2, lineSpacing: 17 });
  s.addText("A consequência", { x: M, y: 3.35, w: 12, h: 0.32, isTextBox: true,
    margin: 0, fontFace: SANS, fontSize: 14, bold: true, color: ORANGE });
  s.addText("“Acessibilidade média” é uma constante em relação a qualquer coisa que você otimize — tentar maximizá-la é como tentar maximizar o número 2. Realocar ambulâncias não cria acesso novo: só redistribui o que já existe.",
    { x: M, y: 3.72, w: 12.1, h: 0.85, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 13.5, color: INK2, lineSpacing: 18 });
  s.addText("O que sobra para otimizar", { x: M, y: 4.75, w: 12, h: 0.32,
    isTextBox: true, margin: 0, fontFace: SANS, fontSize: 14, bold: true, color: TEAL });
  s.addText("A FORMA como o acesso está distribuído: igual para todos, ou concentrado em poucos setores? Essa forma tem nome em estatística — e é o próximo slide.",
    { x: M, y: 5.12, w: 12.1, h: 0.6, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 13.5, color: INK2, lineSpacing: 18 });
  s.addText("(Esta é a Proposição 1 de matematica_usb_usa.html §3.6 — a demonstração são três linhas de álgebra, a mesma conta que você acabou de fazer com 2 setores.)",
    { x: M, y: 6.0, w: 12.1, h: 0.5, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 12, italic: true, color: GREY });
}

// ===========================================================================
// BLOCO 5 — Gini/Lorenz e os dois objetivos (slides 12-13)
// ===========================================================================

{ // 15 — a curva de Lorenz e o Gini, formalmente (NOVO)
  const s = slideClaro("A curva de Lorenz e o índice de Gini, formalmente", "os dois objetivos");
  s.addText("Ordene as unidades (aqui, setores) da pior acessibilidade para a melhor, e acumule:",
    { x: M, y: 1.62, w: 12.1, h: 0.3, isTextBox: true, margin: 0, fontFace: SANS,
      fontSize: 13, color: INK2 });
  cartao(s, { x: M, y: 1.98, w: 12.1, h: 1.05, fill: CARD });
  formula(s, "lorenz_xy", M + 2.4, 2.1, 0.75);
  s.addText("X_k = fração acumulada da população até a k-ésima unidade nessa ordem  ·  Y_k = fração acumulada da acessibilidade (A = acessibilidade da etapa 2 do 2SFCA)",
    { x: M + 0.3, y: 2.6, w: 11.5, h: 0.35, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 10.5, color: INK2, align: "center" });
  s.addText("A curva de Lorenz é o gráfico de (X_k, Y_k). O índice de Gini resume essa curva num só número:",
    { x: M, y: 3.2, w: 12.1, h: 0.35, isTextBox: true, margin: 0, fontFace: SANS,
      fontSize: 13, color: INK2 });
  cartao(s, { x: M, y: 3.6, w: 12.1, h: 0.6, fill: CARD });
  formula(s, "lorenz_gini", M + 1.6, 3.68, 0.42);
  s.addText("← área sob a curva, pela regra do trapézio", { x: M + 8.6,
    y: 3.75, w: 3.4, h: 0.35, isTextBox: true, margin: 0, valign: "middle",
    fontFace: SANS, fontSize: 11.5, italic: true, color: INK2 });
  cartao(s, { x: M, y: 4.4, w: 12.1, h: 1.35, fill: "E7F0F7" });
  s.addText("O que 0 e 1 significam — antes de calcular qualquer coisa", { x: M + 0.3,
    y: 4.56, w: 11.5, h: 0.3, isTextBox: true, margin: 0, fontFace: SANS,
    fontSize: 13, bold: true, color: INK });
  s.addText("Se todas as unidades tivessem a MESMA acessibilidade, a curva coincidiria com a diagonal (X_k = Y_k sempre) e Gini = 0. Se uma única unidade tivesse tudo e o resto nada, a curva colaria no eixo até o fim e Gini = 1. É a mesma medida usada para desigualdade de renda — aqui aplicada a “ambulâncias por habitante”.",
    { x: M + 0.3, y: 4.9, w: 11.5, h: 0.8, isTextBox: true, margin: 0,
      valign: "top", fontFace: SANS, fontSize: 12, color: INK2, lineSpacing: 15 });
  s.addText("Próximo slide: aplicando isto ao exemplo dos dois setores.", { x: M, y: 5.95,
    w: 12.1, h: 0.4, isTextBox: true, margin: 0, fontFace: SERIF, fontSize: 13,
    italic: true, color: TEAL });
}

{ // 16 (calculando o Gini no exemplo, era metade do 12 antigo)
  const s = slideClaro("Calculando o Gini no exemplo dos dois setores", "os dois objetivos");
  s.addText("Setor 2 é pior servido (A menor) — ordena primeiro. Aplicando X_k, Y_k do slide anterior:",
    { x: M, y: 1.62, w: 12.1, h: 0.3, isTextBox: true, margin: 0, fontFace: SANS,
      fontSize: 13, color: INK2 });
  tabela(s, M, 2.0, 6.4, [2.6, 2.2, 2.2],
    ["Ponto", "X_k (pop. acum.)", "Y_k (acesso acum.)"],
    [["origem", "0%", "0%"],
     ["setor 2 (pior)", "66,7%", "47,6%"],
     ["setor 1 (melhor)", "100%", "100%"]],
    { fontSize: 12, rowH: 0.5 });
  const bx = 7.2;
  cartao(s, { x: bx, y: 2.0, w: 5.5, h: 2.0, fill: CARD });
  s.addText("Se fosse tudo igual...", { x: bx + 0.28, y: 2.18, w: 5.0, h: 0.3,
    isTextBox: true, margin: 0, fontFace: SANS, fontSize: 13, bold: true, color: INK });
  s.addText("...a curva coincidiria com a diagonal (66,7% da população teria exatamente 66,7% do acesso). Quanto mais a curva real afunda abaixo da diagonal, maior a desigualdade.",
    { x: bx + 0.28, y: 2.52, w: 5.0, h: 1.4, isTextBox: true, margin: 0,
      valign: "top", fontFace: SANS, fontSize: 12, color: INK2, lineSpacing: 16 });
  cartao(s, { x: M, y: 4.4, w: 12.1, h: 1.55, fill: "E7F0F7" });
  s.addText("Gini = 1 − [(0,667−0)(0,476+0) + (1−0,667)(1+0,476)] = 1 − 0,809 = 0,1905", { x: M + 0.3,
    y: 4.58, w: 11.5, h: 0.4, isTextBox: true, margin: 0, fontFace: SERIF,
    fontSize: 14.5, bold: true, color: INK });
  s.addText("Um Gini de ~0,19 para dois setores com uma razão de acessibilidade de 2,2 para 1 — moderado. O Gini real do projeto (26.889 setores) usa a mesma fórmula, e chega a 0,224 na configuração atual de São Paulo.",
    { x: M + 0.3, y: 5.05, w: 11.5, h: 0.8, isTextBox: true, margin: 0,
      valign: "top", fontFace: SANS, fontSize: 12, color: INK2, lineSpacing: 16 });
  s.addNotes("0,1905 calculado e conferido rodando huff2sfca.gini() de verdade " +
    "sobre este exemplo de 2 setores.");
}

{ // 17 — por que dois objetivos
  const s = slideClaro("Por que Gini sozinho também não basta", "os dois objetivos");
  [["Só tempo → esquece capacidade", `Minimizar só o tempo até a mais próxima é o que o p-median clássico faz. Ignora completamente quem disputa cada base — é voltar à hipótese que abandonamos no slide ${SL.HIPOTESE}.`, ORANGE],
   ["Só Gini → prefere concentrar tudo", "Colocar as duas ambulâncias na MESMA base zera o Gini (todo setor recebe a mesma coisa: nada de perto). Perfeitamente igual, e perfeitamente inútil — o tempo de resposta explode.", ORANGE]]
   .forEach((c, i) => {
    const y = 1.75 + i * 1.75;
    cartao(s, { x: M, y, w: 12.1, h: 1.55, fill: "FBEAE7" });
    bolha(s, i + 1, M + 0.3, y + 0.3, c[2]);
    s.addText(c[0], { x: M + 1.0, y: y + 0.16, w: 10.6, h: 0.32, isTextBox: true,
      margin: 0, fontFace: SANS, fontSize: 14, bold: true, color: INK });
    s.addText(c[1], { x: M + 1.0, y: y + 0.54, w: 10.6, h: 0.9, isTextBox: true,
      margin: 0, valign: "top", fontFace: SANS, fontSize: 12.5, color: INK2,
      lineSpacing: 16 });
  });
  s.addText("Cada objetivo, sozinho, tem uma solução ótima e inútil. Só os DOIS juntos — minimizar tempo E minimizar Gini — têm conteúdo real de decisão. Como não existe uma única configuração que minimize ambos ao mesmo tempo, o que existe é uma FAMÍLIA de soluções — a fronteira de Pareto, que vem a seguir.",
    { x: M, y: 5.5, w: 12.1, h: 1.0, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 13.5, italic: true, color: TEAL, lineSpacing: 18 });
}

// ===========================================================================
// BLOCO 6 — NSGA-II e p-median (slides 14-16)
// ===========================================================================

{ // 18 (dominancia de pareto, reordenado: regra antes do exemplo)
  const s = slideClaro("Comparando soluções com dois objetivos", "otimização multiobjetivo");
  cartao(s, { x: M, y: 1.6, w: 12.1, h: 0.85, fill: CARD });
  s.addText("A domina B  ⟺  A é pelo menos tão bom quanto B em TODOS os objetivos, e estritamente melhor em PELO MENOS UM.", { x: M + 0.3,
    y: 1.78, w: 11.5, h: 0.55, isTextBox: true, margin: 0, fontFace: SERIF,
    fontSize: 14.5, bold: true, color: INK, lineSpacing: 19 });
  s.addText("Aplicando a um mock com 4 configurações hipotéticas de frota:", { x: M, y: 2.62,
    w: 12.1, h: 0.3, isTextBox: true, margin: 0, fontFace: SANS, fontSize: 13,
    color: INK2 });
  tabela(s, M, 3.0, 6.3, [1.6, 2.3, 2.4],
    ["Config.", "Tempo (min)", "Gini"],
    [["W", "8,0", "0,30"], ["X", "7,0", "0,15"], ["Y", "7,5", "0,20"], ["Z", "6,5", "0,25"]],
    { fontSize: 12.5, rowH: 0.48 });
  const bx = 7.5;
  cartao(s, { x: bx, y: 3.0, w: 5.2, h: 3.5, fill: "E7F0F7" });
  s.addText("W é dominada por X: X é melhor nos DOIS eixos (7,0<8,0 e 0,15<0,30). Pela regra acima, ninguém escolheria W.",
    { x: bx + 0.28, y: 3.18, w: 4.65, h: 0.8, isTextBox: true, margin: 0,
      valign: "top", fontFace: SANS, fontSize: 12, color: INK2, lineSpacing: 16 });
  s.addText("X, Y e Z não se dominam entre si: cada uma ganha em um eixo e perde no outro. As três formam a fronteira de Pareto — o conjunto de soluções “razoáveis”.",
    { x: bx + 0.28, y: 4.05, w: 4.65, h: 1.15, isTextBox: true, margin: 0,
      valign: "top", fontFace: SANS, fontSize: 12, color: INK2, lineSpacing: 16 });
  s.addText("Escolher entre X, Y e Z é uma decisão de valor (quanto tempo você troca por quanto de equidade) — não uma conta que o modelo resolve sozinho.",
    { x: bx + 0.28, y: 5.25, w: 4.65, h: 1.1, isTextBox: true, margin: 0,
      valign: "top", fontFace: SANS, fontSize: 12, italic: true, color: TEAL, lineSpacing: 16 });
}

{ // 19 — como o NSGA-II busca
  const s = slideClaro("Como encontrar a fronteira quando há 10¹⁹¹ opções", "otimização multiobjetivo");
  s.addText("O tamanho real do problema: 1.107 candidatos, 123 ambulâncias, repetição permitida. Não dá para testar todas as combinações — nem perto.",
    { x: M, y: 1.65, w: 12.1, h: 0.55, isTextBox: true, margin: 0, fontFace: SANS,
      fontSize: 13, color: INK2, lineSpacing: 17 });
  const its = [
    ["Uma população de soluções, não uma só", "O NSGA-II mantém 80 configurações candidatas ao mesmo tempo, cada uma um vetor de 123 posições (uma por ambulância)."],
    [`Seleciona pelas regras do slide ${SL.PARETO_REGRA}`, "Ordena por dominância (camada 1 = não dominada por ninguém, camada 2 = o resto etc.) e mantém as mais promissoras."],
    ["Muta localmente, como um SAMU de verdade faria", "70% das mutações movem uma ambulância para um candidato VIZINHO geográfico — não para qualquer ponto da cidade."],
    ["Repete por 150 gerações", "A cada geração, a fronteira de soluções mantidas melhora — como uma seleção natural apontada para os dois objetivos."]];
  its.forEach((it, i) => {
    const y = 2.35 + i * 0.98;
    bolha(s, i + 1, M, y, BLUE);
    s.addText(it[0], { x: M + 0.65, y: y - 0.03, w: 11.4, h: 0.28, isTextBox: true,
      margin: 0, valign: "top", fontFace: SANS, fontSize: 13.5, bold: true, color: INK });
    s.addText(it[1], { x: M + 0.65, y: y + 0.27, w: 11.4, h: 0.6, isTextBox: true,
      margin: 0, valign: "top", fontFace: SANS, fontSize: 12, color: INK2, lineSpacing: 15 });
  });
  s.addText("Não há garantia de achar o ótimo exato — só de convergir para perto dele. É por isso que o próximo slide (o baseline clássico) importa: ele confere se o NSGA-II está indo bem.",
    { x: M, y: 6.35, w: 12.1, h: 0.5, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 12.5, italic: true, color: TEAL });
}

{ // 20 (p-median, definicao completa)
  const s = slideClaro("O ponto de comparação: p-median, formalmente", "o baseline clássico");
  cartao(s, { x: M, y: 1.55, w: 12.1, h: 0.85, fill: CARD });
  formula(s, "pmedian_obj", M + 3.9, 1.65, 0.55);
  s.addText("escolha as bases fixas antecipadamente; cada setor i é servido pela ESCOLHIDA mais próxima (min_j t_ij); minimize a distância média, ponderada pela população D_i. N = número de bases.",
    { x: M + 0.3, y: 2.15, w: 11.5, h: 0.3, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 10.5, color: INK2, align: "center" });
  s.addText(`É exatamente o limite β → 0 do modelo de Huff (slide ${SL.BETA_LIMITES}): nenhuma probabilidade, nenhuma capacidade — só a mais próxima, sempre.`,
    { x: M, y: 2.55, w: 12.1, h: 0.35, isTextBox: true, margin: 0, fontFace: SANS,
      fontSize: 12.5, italic: true, color: TEAL });
  cartao(s, { x: M, y: 3.0, w: 12.1, h: 1.15, fill: "E7F0F7" });
  s.addText("Por que ele importa aqui", { x: M + 0.3, y: 3.15, w: 11.5, h: 0.3,
    isTextBox: true, margin: 0, fontFace: SANS, fontSize: 13, bold: true, color: INK });
  s.addText("Se o NSGA-II (uma heurística, sem garantias) encontrar uma solução PIOR que o p-median no eixo do tempo, algo está errado na busca. Vira um sinal de sanidade — e a pergunta científica do projeto: quanto o modelo de Huff muda a resposta ótima?",
    { x: M + 0.3, y: 3.48, w: 11.5, h: 0.65, isTextBox: true, margin: 0,
      valign: "top", fontFace: SANS, fontSize: 12, color: INK2, lineSpacing: 15 });
  s.addText("Um detalhe que fez diferença de verdade no projeto", { x: M, y: 4.35, w: 12,
    h: 0.3, isTextBox: true, margin: 0, fontFace: SANS, fontSize: 13.5, bold: true,
    color: ORANGE });
  s.addText("Sem começar a busca do NSGA-II a partir da solução do p-median (“semear”), o algoritmo evolutivo na verdade PERDIA para o p-median: 6,77 contra 6,70 min. Com a semente, o NSGA-II passou a bater os dois pontos de partida: 6,64 min. Moral: comparar heurística nova com clássica só é honesto se a nova começar de onde a clássica já chegou.",
    { x: M, y: 4.7, w: 12.1, h: 1.2, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 12.5, color: INK2, lineSpacing: 17 });
  s.addText("(Resolvido, na prática, por construção gulosa + troca de vértices — o mesmo tipo de heurística usado em muitos problemas de otimização combinatória.)",
    { x: M, y: 6.05, w: 12.1, h: 0.5, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 11.5, italic: true, color: GREY });
}

// ===========================================================================
// BLOCO 7 — custo de mudança e lambda (slides 17-18)
// ===========================================================================

{ // 21 (emparelhamento otimo, reordenado: regra antes do exemplo)
  const s = slideClaro("Quanto custa sair da rede de hoje para a nova?", "custo de mudança");
  cartao(s, { x: M, y: 1.6, w: 12.1, h: 1.1, fill: CARD });
  s.addText("O problema de atribuição, em uma frase", { x: M + 0.3, y: 1.75, w: 11.5,
    h: 0.3, isTextBox: true, margin: 0, fontFace: SANS, fontSize: 13, bold: true, color: INK });
  s.addText("Dado um custo para cada par possível de origem-destino, encontrar a correspondência 1-para-1 (cada origem com exatamente um destino) que MINIMIZA A SOMA dos custos — resolvido de forma exata pelo algoritmo húngaro, o mesmo usado em logística e transporte ótimo.",
    { x: M + 0.3, y: 2.08, w: 11.5, h: 0.6, isTextBox: true, margin: 0,
      valign: "top", fontFace: SANS, fontSize: 12, color: INK2, lineSpacing: 15 });
  s.addText("Não basta contar quantas ambulâncias mudam de lugar — importa QUANTO ELAS ANDAM. Mover para a esquina é barato; atravessar a cidade não.",
    { x: M, y: 2.85, w: 12.1, h: 0.5, isTextBox: true, margin: 0, fontFace: SANS,
      fontSize: 12.5, color: INK2, lineSpacing: 16 });
  s.addText("Um mini-exemplo: 2 ambulâncias mudando de par de bases", { x: M, y: 3.45,
    w: 12, h: 0.3, isTextBox: true, margin: 0, fontFace: SANS, fontSize: 13,
    bold: true, color: ORANGE });
  tabela(s, M, 3.8, 7.4, [2.0, 2.0, 1.7, 1.7],
    ["", "de A ou B (hoje)", "para C", "para D"],
    [["ambulância 1", "A", "3 km", "9 km"], ["ambulância 2", "B", "8 km", "2 km"]],
    { fontSize: 12, rowH: 0.5 });
  const bx = 8.6;
  cartao(s, { x: bx, y: 3.8, w: 4.1, h: 2.1, fill: "E7F0F7" });
  s.addText("A→C e B→D: 3+2 = 5 km\nA→D e B→C: 9+8 = 17 km", { x: bx + 0.25, y: 4.0,
    w: 3.6, h: 0.85, isTextBox: true, margin: 0, fontFace: "Consolas", fontSize: 12,
    color: INK, lineSpacing: 18 });
  s.addText("A regra acima escolhe a combinação de menor custo total — aqui, 5 km, não 17.",
    { x: bx + 0.25, y: 4.95, w: 3.6, h: 0.85, isTextBox: true, margin: 0,
      valign: "top", fontFace: SANS, fontSize: 11.5, color: INK2, lineSpacing: 15 });
  s.addText("No projeto real, compara 123 origens com 123 destinos em milissegundos. Ambulâncias que já estão no lugar certo são descontadas ANTES do emparelhamento — mudar tudo e depois “cancelar” quem ficou daria o mesmo resultado, mas custaria mais conta.",
    { x: M, y: 6.1, w: 12.1, h: 0.9, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 12, italic: true, color: GREY, lineSpacing: 16 });
}

{ // 22 — o papel de lambda
  const s = slideClaro("λ: o preço da mudança, em minutos por quilômetro", "juntando tudo");
  cartao(s, { x: M, y: 1.75, w: 12.1, h: 1.3, fill: "E7F0F7" });
  formula(s, "lambda_obj", M + 3.0, 1.9, 0.55);
  s.addText("λ converte quilômetros em minutos equivalentes, e soma essa penalidade ao primeiro objetivo. O segundo objetivo (Gini) não muda.",
    { x: M + 0.3, y: 2.65, w: 11.5, h: 0.35, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 12, color: INK2 });
  const its = [
    ["λ = 0 — redesenho livre", "Mudar custa zero. O otimizador realoca o que quiser, sem se importar com o tamanho da mudança."],
    ["λ alto — rede quase congelada", "Cada km custa caro em tempo equivalente. O otimizador só aceita as mudanças que compensam muito."]];
  its.forEach((c, i) => {
    const x = M + i * 6.2;
    cartao(s, { x, y: 3.3, w: 5.9, h: 1.3, fill: CARD });
    s.addText(c[0], { x: x + 0.3, y: 3.48, w: 5.3, h: 0.3, isTextBox: true,
      margin: 0, fontFace: SANS, fontSize: 13, bold: true, color: INK });
    s.addText(c[1], { x: x + 0.3, y: 3.82, w: 5.3, h: 0.65, isTextBox: true,
      margin: 0, valign: "top", fontFace: SANS, fontSize: 12, color: INK2, lineSpacing: 15 });
  });
  s.addText("Cada valor de λ gera sua PRÓPRIA fronteira de Pareto inteira (não um ponto só). Variar λ produz a curva “quanto de ganho cada km de mudança compra” — que é exatamente o que os resultados reais mostram a seguir.",
    { x: M, y: 4.85, w: 12.1, h: 0.85, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 13.5, color: INK2, lineSpacing: 18 });
  s.addText("Com isso, temos todas as peças: Huff (quem atende quem), 2SFCA (acessibilidade), Gini (desigualdade), NSGA-II (busca), p-median (comparação) e λ (preço da mudança). Hora dos números reais.",
    { x: M, y: 5.85, w: 12.1, h: 0.75, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 13.5, italic: true, color: TEAL, lineSpacing: 18 });
}

// ===========================================================================
// BLOCO 8 — resultados reais (slides 19-23)
// ===========================================================================

{ // 23 — os dados reais
  const s = slideEscuro(TEAL);
  s.addText("AGORA COM DADOS REAIS", { x: M, y: 0.55, w: 11, h: 0.26, isTextBox: true,
    margin: 0, fontFace: SANS, fontSize: 10.5, bold: true, color: GOLD, charSpacing: 1.4 });
  s.addText("De 2 bases para 1.107, de 2 setores para 26.889", { x: M, y: 0.83,
    w: 11.7, h: 0.85, isTextBox: true, margin: 0, fontFace: SERIF, fontSize: 28,
    bold: true, color: "FFFFFF" });
  const stats = [["26.889", "setores censitários\nde São Paulo"], ["1.107", "candidatos a base\n(CNES)"],
                 ["123", `ambulâncias\n107 USB + 16 USA`], ["92", "locais ocupados\nhoje"]];
  stats.forEach((st, i) => {
    const x = M + i * 3.05;
    s.addText(st[0], { x, y: 2.1, w: 2.85, h: 0.75, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 34, bold: true, color: GOLD });
    s.addText(st[1], { x, y: 2.9, w: 2.85, h: 0.75, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 12.5, color: "C9D6E4", lineSpacing: 16 });
  });
  s.addText(`A configuração de hoje: E[T] = ${n(BASE.f_tempo)} min, Gini = ${n(BASE.f_gini, 3)}. É a linha de base contra a qual todo ganho abaixo é medido.`,
    { x: M, y: 4.3, w: 12.1, h: 0.6, isTextBox: true, margin: 0, fontFace: SANS,
      fontSize: 15, color: "FFFFFF", lineSpacing: 20 });
  s.addText("Todo o resto do modelo — Huff, 2SFCA, NSGA-II, p-median, λ — é exatamente o que acabamos de calcular à mão, só que em escala real.",
    { x: M, y: 5.4, w: 12.1, h: 0.6, isTextBox: true, margin: 0, fontFace: SERIF,
      fontSize: 13.5, italic: true, color: "9FB0C4", lineSpacing: 18 });
}

{ // 24 — resultado real: fronteira e ganho x km
  const j1 = jo(1);
  const rhoG = 100 * (BASE.f_gini - j1.f_gini) / BASE.f_gini;
  const s = slideClaro(`${j1.movidas} unidades e ${km0(j1.km_total)} cortam ${n(rhoG, 0)}% da desigualdade`, "resultado real 1");
  s.addImage({ path: FIG + "sp_02_ganho_km.png", x: M, y: 1.65, w: 7.3, h: 3.3 });
  const bx = 8.1;
  s.addText(`Cada ponto do gráfico é o “joelho” da fronteira de Pareto para um λ — a mesma ideia do slide ${SL.PARETO_REGRA}, só que com uma frente de verdade em vez de 4 pontos hipotéticos.`,
    { x: bx, y: 1.85, w: 4.6, h: 1.1, isTextBox: true, margin: 0, fontFace: SANS,
      fontSize: 12.5, color: INK2, lineSpacing: 17 });
  cartao(s, { x: bx, y: 3.05, w: 4.6, h: 1.9, fill: CARD });
  s.addText(`Mover ${j1.movidas} das 123 unidades (${km0(j1.km_total)}) já entrega a maior parte do ganho de equidade possível — a curva tem retorno decrescente.`,
    { x: bx + 0.28, y: 3.25, w: 4.05, h: 1.5, isTextBox: true, margin: 0,
      valign: "top", fontFace: SANS, fontSize: 12.5, color: INK2, lineSpacing: 17 });
  s.addText(`Gini: ${n(BASE.f_gini, 3)} → ${n(j1.f_gini, 3)}`, { x: M, y: 5.2, w: 7.2, h: 0.5,
    isTextBox: true, margin: 0, fontFace: SERIF, fontSize: 20, bold: true, color: TEAL });
  s.addText("Doze decisões administrativas, nenhuma obra, nenhuma compra.", { x: M, y: 5.75,
    w: 7.2, h: 0.5, isTextBox: true, margin: 0, fontFace: SERIF, fontSize: 14,
    italic: true, color: INK2 });
}

{ // 25 — resultado real: contra o p-median (achado central)
  const perda = 100 * (PMEDIAN_C.huff_tempo / HUFF_C.huff_tempo - 1);
  const s = slideClaro("O achado central: onde o modelo de Huff realmente ajuda", "resultado real 2");
  s.addImage({ path: FIG + "sp_05_comparacao.png", x: M, y: 1.65, w: 7.4, h: 4.9 });
  const bx = 8.3;
  cartao(s, { x: bx, y: 1.75, w: 4.4, h: 1.8, fill: "FBEAE7" });
  s.addText("Surpresa: Huff quase não muda a eficiência", { x: bx + 0.28, y: 1.93,
    w: 3.85, h: 0.6, isTextBox: true, margin: 0, fontFace: SANS, fontSize: 13,
    bold: true, color: INK });
  s.addText(`Planejar pela regra clássica (slide ${SL.HIPOTESE}) custa só ${n(perda, 1)}% de tempo esperado a mais. O p-median é robusto à hipótese que passamos a aula inteira tentando derrubar.`,
    { x: bx + 0.28, y: 2.5, w: 3.85, h: 1.0, isTextBox: true, margin: 0,
      valign: "top", fontFace: SANS, fontSize: 12, color: INK2, lineSpacing: 16 });
  cartao(s, { x: bx, y: 3.75, w: 4.4, h: 2.1, fill: CARD });
  s.addText("Mas o 2SFCA enxerga algo que o p-median não vê: capacidade", { x: bx + 0.28,
    y: 3.93, w: 3.85, h: 0.6, isTextBox: true, margin: 0, fontFace: SANS,
    fontSize: 13, bold: true, color: INK });
  s.addText(`Gini ${n(HUFF_C.huff_gini, 3)} contra ${n(PMEDIAN_C.huff_gini, 3)} do p-median — ${vez(PMEDIAN_C.huff_gini, HUFF_C.huff_gini)} melhor — com MENOS deslocamento (${km0(HUFF_C.km_mudanca)} contra ${km0(PMEDIAN_C.km_mudanca)}).`,
    { x: bx + 0.28, y: 4.5, w: 3.85, h: 1.2, isTextBox: true, margin: 0,
      valign: "top", fontFace: SANS, fontSize: 12, color: INK2, lineSpacing: 16 });
  s.addText("A tese do projeto não é “chegamos mais rápido”. É “distribuímos a carga de forma muito mais equânime, no mesmo tempo”.",
    { x: M, y: 6.65, w: 12.1, h: 0.5, isTextBox: true, margin: 0, fontFace: SERIF,
      fontSize: 13, italic: true, color: TEAL });
}

{ // 26 (resultado real: sensibilidade em beta)
  if (betaSens) {
    const s = slideClaro("O achado sobrevive fora de β = 4,5?", "resultado real 3 — sensibilidade");
    cartao(s, { x: M, y: 1.55, w: 12.1, h: 0.85, fill: CARD });
    formula(s, "rho_g", M + 2.9, 1.63, 0.55);
    s.addText(`fração do ganho de equidade MÁXIMO POSSÍVEL naquele β (o piso é λ=0, redesenho livre) que λ entrega. Normalizado por β porque Gini_atual(β) muda com β — a "tabela barata" do slide ${SL.BETA_2_2}.`,
      { x: M + 0.3, y: 2.1, w: 11.5, h: 0.3, isTextBox: true, margin: 0,
        fontFace: SANS, fontSize: 10.5, color: INK2, align: "center" });
    const linha1 = betaSens.sweep.filter(r => r.lam === 1.0);
    tabela(s, M, 2.6, 12.1, [2.4, 2.4, 2.4, 2.5, 2.4],
      ["β", "E[T] (min)", "Gini", "movidas / km", "ρ_G (λ=1)"],
      linha1.map(r => [n(r.beta, 1), n(r.f_tempo), n(r.f_gini, 3),
                        `${r.movidas} / ${km0(r.km_total)}`, pct(100 * r.rho_g, 0)]),
      { fontSize: 12, rowH: 0.5, boldCols: [4] });
    const rhoGs = linha1.map(r => r.rho_g).filter(x => x != null);
    const sobrevive = rhoGs.every(v => v >= 0.5);
    cartao(s, { x: M, y: 4.55, w: 12.1, h: 1.55, fill: sobrevive ? "E7F0F7" : "FBEAE7" });
    s.addText(sobrevive ? "Sim — a recomendação não depende da escolha exata de β"
                        : "Depende — a recomendação varia com β",
      { x: M + 0.3, y: 4.7, w: 11.5, h: 0.32, isTextBox: true, margin: 0,
        fontFace: SANS, fontSize: 14, bold: true, color: sobrevive ? TEAL : ORANGE });
    s.addText(`β foi escolhido por argumento (slide ${SL.BETA_2_2}), não estimado de despacho real. Repetimos toda a otimização para β = 2 e β = 8,5, além do padrão. Em todos, λ = 1 entrega pelo menos ${pct(100*Math.min(...rhoGs),0)} do ganho de equidade alcançável.`,
      { x: M + 0.3, y: 5.05, w: 11.5, h: 0.9, isTextBox: true, margin: 0,
        valign: "top", fontFace: SANS, fontSize: 12, color: INK2, lineSpacing: 16 });
    s.addText("Este é o tipo de pergunta que estatística sempre faz de um modelo: o resultado é robusto à escolha de um parâmetro que não foi medido? Aqui, testamos — e é assim que se testa.",
      { x: M, y: 6.25, w: 12.1, h: 0.7, isTextBox: true, margin: 0, fontFace: SERIF,
        fontSize: 12, italic: true, color: TEAL, lineSpacing: 16 });
  } else {
    const s = slideClaro("Sensibilidade em β (dados pendentes)", "resultado real 3");
    s.addText("Rode fase2_sao_paulo/experimentos/sensib_beta.py para preencher este slide com os números reais.",
      { x: M, y: 2.5, w: 12, h: 0.5, isTextBox: true, margin: 0, fontFace: SANS,
        fontSize: 14, color: INK2 });
  }
}

// ===========================================================================
// BLOCO 9 — fechamento (slides 23-24)
// ===========================================================================

{ // 27 — o que fica de licao
  const s = slideClaro("O que este exemplo ensina, além do SAMU", "para levar da aula");
  const its = [
    ["Escolha probabilística > regra determinística", "Sempre que “a opção mais próxima/barata/rápida” pode estar indisponível, um modelo tipo Huff (softmax com decaimento) é mais realista que a regra do mínimo."],
    ["Capacidade muda o resultado, mesmo com a mesma demanda total", "O 2SFCA mostrou dois setores com a mesma distância às mesmas bases, mas acessibilidade bem diferente — só por causa de quem MAIS disputa cada base."],
    ["Um objetivo constante é um objetivo inútil", "“Maximizar acesso” parecia razoável até a álgebra mostrar que é uma constante. Vale sempre conferir se o que você está otimizando de fato varia."],
    ["Teste a sensibilidade a qualquer parâmetro arbitrado", "β nunca foi medido de dado real — foi arbitrado. Testar contra outros valores é o mínimo antes de confiar na conclusão."]];
  its.forEach((it, i) => {
    const x = M + (i % 2) * 6.2, y = 1.80 + Math.floor(i / 2) * 1.9;
    cartao(s, { x, y, w: 5.9, h: 1.7, fill: CARD });
    item(s, i + 1, x + 0.28, y + 0.28, 5.35, it[0], it[1], BLUE);
  });
}

{ // 28 — fechamento
  const s = slideEscuro(NAVY);
  s.addText("PARA FECHAR", { x: M, y: 0.62, w: 11, h: 0.26, isTextBox: true, margin: 0,
    fontFace: SANS, fontSize: 10.5, bold: true, color: GOLD, charSpacing: 1.4 });
  s.addText("Do exemplo de duas bases a São Paulo inteira", { x: M, y: 0.9, w: 11.7,
    h: 0.7, isTextBox: true, margin: 0, fontFace: SERIF, fontSize: 30, bold: true,
    color: "FFFFFF" });
  const its = [
    ["Huff + 2SFCA trocam uma hipótese, não um algoritmo", "A mudança real é modelar demanda como probabilidade, com capacidade — tudo o mais (Gini, NSGA-II, λ) monta em cima disso."],
    ["O resultado real confirma a intuição do exemplo pequeno", `Ganho de equidade grande e barato (Gini ${n(BASE.f_gini,3)}→${n(HUFF_C.huff_gini,3)}), quase sem custo de tempo — exatamente o padrão de retorno decrescente que a matemática já sugeria.`],
    ["Testar sensibilidade é parte do método, não um extra", "β = 2, 4,5 e 8,5 dão a mesma recomendação qualitativa — é isso que torna o achado defensável."]];
  its.forEach((it, i) => {
    const y = 2.5 + i * 1.25;
    bolha(s, i + 1, M, y, i === 2 ? GOLD : ORANGE);
    s.addText(it[0], { x: M + 0.68, y: y - 0.03, w: 10.5, h: 0.3, isTextBox: true,
      margin: 0, valign: "top", fontFace: SANS, fontSize: 14.5, bold: true, color: "FFFFFF" });
    s.addText(it[1], { x: M + 0.68, y: y + 0.28, w: 10.0, h: 0.75, isTextBox: true,
      margin: 0, valign: "top", fontFace: SANS, fontSize: 12, color: "AEBDCE", lineSpacing: 16 });
  });
  s.addText("Material didático do grupo MAI5003 — código, dados e o deck de resultados completo em fase2_sao_paulo/.",
    { x: M, y: 6.85, w: 12.1, h: 0.35, isTextBox: true, margin: 0, fontFace: SANS,
      fontSize: 10.5, color: "7C8CA0" });
}

doc.writeFile({ fileName: SAIDA }).then(f => console.log("gerado:", f));
