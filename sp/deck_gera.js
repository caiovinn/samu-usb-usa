const pptx = require("pptxgenjs");
const p = new pptx();
p.layout = "LAYOUT_WIDE";                 // 13.3 x 7.5
p.author = "Grupo MAI5003";
p.title = "Realocação de USB e USA em São Paulo";

const NAVY = "16263F", TEAL = "0F3D5C", CREAM = "F7F5F0", CARD = "EAF1F7";
const INK = "0F2B46", INK2 = "4A5568", GOLD = "D9A441";
const BLUE = "2A78D6", ORANGE = "EB6834", GREY = "8A8F98";
const SERIF = "Cambria", SANS = "Calibri";
const FIG = "/home/claude/eda/figs/";
const M = 0.62;                            // margem lateral

// ---------------------------------------------------------------- utilitarios
function slideClaro(titulo, sobre) {
  const s = p.addSlide();
  s.background = { color: CREAM };
  if (sobre) s.addText(sobre.toUpperCase(), { x: M, y: 0.42, w: 11, h: 0.26,
    isTextBox: true, margin: 0, fontFace: SANS, fontSize: 10.5, bold: true,
    color: GOLD, charSpacing: 1.4 });
  s.addText(titulo, { x: M, y: sobre ? 0.70 : 0.55, w: 12.1, h: 0.72,
    isTextBox: true, margin: 0, fontFace: SERIF, fontSize: 32, bold: true,
    color: INK });
  return s;
}
function slideEscuro(cor) {
  const s = p.addSlide();
  s.background = { color: cor };
  s.addShape(p.ShapeType.ellipse, { x: 10.2, y: -2.2, w: 5.6, h: 5.6,
    fill: { color: "FFFFFF", transparency: 94 }, line: { color: cor } });
  return s;
}
function bolha(s, n, x, y, cor) {
  s.addShape(p.ShapeType.ellipse, { x, y, w: 0.46, h: 0.46,
    fill: { color: cor }, line: { color: cor } });
  s.addText(String(n), { x, y, w: 0.46, h: 0.46, isTextBox: true, margin: 0,
    align: "center", valign: "middle", fontFace: SANS, fontSize: 13,
    bold: true, color: "FFFFFF" });
}
function cartao(s, o) {
  s.addShape(p.ShapeType.roundRect, { x: o.x, y: o.y, w: o.w, h: o.h,
    rectRadius: 0.10, fill: { color: o.fill || CARD },
    line: { color: o.fill || CARD } });
}
function item(s, n, x, y, w, titulo, corpo, cor) {
  bolha(s, n, x, y, cor || BLUE);
  s.addText(titulo, { x: x + 0.62, y: y - 0.02, w: w - 0.62, h: 0.28,
    isTextBox: true, margin: 0, valign: "top", fontFace: SANS, fontSize: 13.5,
    bold: true, color: INK });
  s.addText(corpo, { x: x + 0.62, y: y + 0.26, w: w - 0.62, h: 1.05,
    isTextBox: true, margin: 0, valign: "top", fontFace: SANS, fontSize: 11.5,
    color: INK2, lineSpacing: 15 });
}

// ------------------------------------------------------------------- 1 capa
{
  const s = slideEscuro(NAVY);
  s.addShape(p.ShapeType.ellipse, { x: -1.8, y: 5.2, w: 4.4, h: 4.4,
    fill: { color: "FFFFFF", transparency: 96 }, line: { color: NAVY } });
  s.addText("PROJETO DA DISCIPLINA MAI5003 — PROBABILIDADE E ESTATÍSTICA",
    { x: M, y: 1.45, w: 11, h: 0.3, isTextBox: true, margin: 0, fontFace: SANS,
      fontSize: 11, bold: true, color: GOLD, charSpacing: 1.4 });
  s.addText("Primeira versão do estudo", { x: M, y: 1.85, w: 11.5, h: 0.95,
    isTextBox: true, margin: 0, fontFace: SERIF, fontSize: 44, bold: true,
    color: "FFFFFF" });
  s.addText("Realocação de USB e USA com Huff + 2SFCA bi-objetivo",
    { x: M, y: 2.82, w: 11, h: 0.45, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 21, italic: true, color: "C9D6E4" });
  s.addText("Técnica 2 do levantamento anterior, aplicada ao município de São Paulo",
    { x: M, y: 3.42, w: 11, h: 0.35, isTextBox: true, margin: 0, fontFace: SANS,
      fontSize: 14, color: "9FB0C4" });
  s.addText([
    { text: "Paulo Henrique Brasil Ribeiro • Coordenador", options: { breakLine: true } },
    { text: "Caio Oliveira • nUSP 11932272", options: { breakLine: true } },
    { text: "Eduardo Próspero Santana • nUSP 11320731", options: { breakLine: true } },
    { text: "Lucas Martinuzzo • nUSP 11930158", options: { breakLine: true } },
    { text: "Matheus de Tulio • nUSP 11371291" }],
    { x: M, y: 5.35, w: 6, h: 1.5, isTextBox: true, margin: 0, fontFace: SANS,
      fontSize: 11, color: "8D9EB2", lineSpacing: 15 });
  s.addNotes("Esta é a primeira versão executável do estudo: a técnica 2 " +
    "(Huff + 2SFCA com metaheurística bi-objetivo) rodando ponta a ponta " +
    "sobre dados reais do município de São Paulo.");
}

// --------------------------------------------------------- 2 caminho até aqui
{
  const s = slideClaro("O caminho até esta versão", "recapitulando");
  const ys = 1.85, h = 1.42;
  const its = [
    ["EDA nacional concluída", "5.522 unidades públicas ativas, 3.710 USB para 885 USA. Gini da frota avançada em 0,67 contra 0,54 da básica — a desigualdade é o problema, não o volume."],
    ["Quatro técnicas avaliadas", "RL/GNN, Huff+2SFCA, ADNet multi-período e BOMCLP-C. A técnica 2 venceu por abandonar a suposição de que o usuário é sempre atendido pela unidade mais próxima."],
    ["Recorte controlado", "São Paulo capital: uma cidade, uma malha viária, 123 ambulâncias. Escala pequena o bastante para iterar e grande o bastante para ser um caso real."]];
  its.forEach((it, i) => {
    cartao(s, { x: M + i * 4.06, y: ys, w: 3.82, h: 3.5 });
    bolha(s, i + 1, M + 0.32 + i * 4.06, ys + 0.32, [BLUE, ORANGE, BLUE][i]);
    s.addText(it[0], { x: M + 0.32 + i * 4.06, y: ys + 0.92, w: 3.2, h: 0.6,
      isTextBox: true, margin: 0, valign: "top", fontFace: SERIF, fontSize: 16,
      bold: true, color: INK });
    s.addText(it[1], { x: M + 0.32 + i * 4.06, y: ys + 1.38, w: 3.2, h: 1.8,
      isTextBox: true, margin: 0, valign: "top", fontFace: SANS, fontSize: 11.5,
      color: INK2, lineSpacing: 16 });
  });
  s.addText("Objetivo: aplicar uma técnica recente de otimização geográfica, ainda não usada em USB/USA, a um caso real brasileiro.",
    { x: M, y: 5.72, w: 12.1, h: 0.4, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 14, italic: true, color: TEAL });
}

// ------------------------------------------------------------- 3 a técnica
{
  const s = slideClaro("Huff + 2SFCA hierárquico", "a técnica empregada");
  s.addText("O que a técnica substitui", { x: M, y: 1.72, w: 5.6, h: 0.32,
    isTextBox: true, margin: 0, fontFace: SANS, fontSize: 13, bold: true,
    color: ORANGE });
  s.addText([
    { text: "Modelo clássico: ", options: { bold: true, breakLine: false } },
    { text: "todo setor é atendido pela unidade mais próxima. É o que o protótipo do grupo faz hoje.", options: { breakLine: true } },
    { text: "\n", options: { breakLine: true } },
    { text: "Huff: ", options: { bold: true, breakLine: false } },
    { text: "o setor se reparte entre as unidades ao alcance, com probabilidade proporcional à atratividade da base e ao decaimento com o tempo de viagem. Essa probabilidade entra como peso nas duas etapas do 2SFCA.", options: {} }],
    { x: M, y: 2.12, w: 5.6, h: 2.4, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 12.5, color: INK2, lineSpacing: 18 });
  s.addText("β = 4,5 min deixa cada setor com 2,2 unidades efetivas — a leitura operacional de “a mais próxima disponível”.",
    { x: M, y: 4.60, w: 5.6, h: 0.55, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 13, italic: true, color: TEAL });

  const bx = 6.75;
  s.addText("A hierarquia do SAMU", { x: bx, y: 1.72, w: 6, h: 0.32,
    isTextBox: true, margin: 0, fontFace: SANS, fontSize: 13, bold: true,
    color: ORANGE });
  [["Pool avançado — 10% dos chamados", "Gravidade que exige médico e desfibrilador. Só USA atende.", "FBEAE7"],
   ["Pool básico — 90% dos chamados", "Escolhe entre USB e USA. A USA que atende um chamado básico fica indisponível para o avançado.", "E7F0F7"]]
   .forEach((c, i) => {
    const y = 2.16 + i * 1.42;
    cartao(s, { x: bx, y, w: 5.95, h: 1.22, fill: c[2] });
    s.addText(c[0], { x: bx + 0.3, y: y + 0.16, w: 5.4, h: 0.3, isTextBox: true,
      margin: 0, fontFace: SANS, fontSize: 13, bold: true, color: INK });
    s.addText(c[1], { x: bx + 0.3, y: y + 0.50, w: 5.4, h: 0.62, isTextBox: true,
      margin: 0, fontFace: SANS, fontSize: 11.5, color: INK2, lineSpacing: 15 });
  });
  [["Etapa 1 — a razão em cada base", "Divide as ambulâncias do local pela demanda que o Huff manda para lá. É onde a capacidade entra no modelo."],
   ["Etapa 2 — o índice de cada setor", "Soma essas razões vistas do setor, com o mesmo peso de escolha. O resultado é a acessibilidade."]]
   .forEach((c, i) => {
    const x = M + i * 6.2;
    cartao(s, { x, y: 5.52, w: 5.9, h: 1.28, fill: "EFEDE6" });
    s.addText(c[0], { x: x + 0.3, y: 5.70, w: 5.35, h: 0.3, isTextBox: true,
      margin: 0, valign: "top", fontFace: SANS, fontSize: 13, bold: true,
      color: TEAL });
    s.addText(c[1], { x: x + 0.3, y: 6.02, w: 5.35, h: 0.66, isTextBox: true,
      margin: 0, valign: "top", fontFace: SANS, fontSize: 11.5, color: INK2,
      lineSpacing: 15 });
  });
  s.addNotes("O 2SFCA tem duas etapas: primeiro a razão oferta/demanda em cada " +
    "base, depois a soma ponderada dessas razões vista de cada setor.");
}

// ---------------------------------------------------------- 4 a otimização
{
  const s = slideClaro("Como a rede é redesenhada", "a otimização");
  const its = [
    ["NSGA-II com codificação inteira", "Um gene por ambulância, 123 ao todo, apontando o candidato que a hospeda. Mutação local salta para uma base vizinha; repetição permitida, então o otimizador pode concentrar."],
    ["Dois objetivos em conflito", "Minimizar o tempo esperado de resposta e o Gini da acessibilidade avançada. Sozinho, cada um degenera: a acessibilidade agregada é constante e o Gini zera concentrando tudo num ponto."],
    ["O preço da mudança (λ)", "Quilômetros que a frota percorre para assumir a nova configuração, por emparelhamento ótimo entre origens e destinos. λ converte km em minutos e entra no objetivo."]];
  its.forEach((it, i) => {
    const y = 1.78 + i * 1.45;
    cartao(s, { x: M, y, w: 12.1, h: 1.26, fill: i === 2 ? "FBEAE7" : CARD });
    bolha(s, i + 1, M + 0.34, y + 0.40, i === 2 ? ORANGE : BLUE);
    s.addText(it[0], { x: M + 1.05, y: y + 0.17, w: 10.6, h: 0.32,
      isTextBox: true, margin: 0, fontFace: SANS, fontSize: 14, bold: true,
      color: INK });
    s.addText(it[1], { x: M + 1.05, y: y + 0.53, w: 10.6, h: 0.62,
      isTextBox: true, margin: 0, fontFace: SANS, fontSize: 11.5, color: INK2,
      lineSpacing: 15 });
  });
  s.addText("Sem o custo de mudança, toda a fronteira realocava 123 das 123 unidades — matematicamente ótimo e inútil como recomendação.",
    { x: M, y: 6.18, w: 12.1, h: 0.4, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 14, italic: true, color: TEAL });
}

// ------------------------------------------------- 5 metricas (como ler)
{
  const s = slideClaro("Como ler os números", "as métricas");

  s.addText("O default: duas linhas de base distintas", { x: M, y: 1.56, w: 12.1,
    h: 0.3, isTextBox: true, margin: 0, fontFace: SANS, fontSize: 13, bold: true,
    color: ORANGE });
  [["Operacional — a rede de hoje", "As 123 ambulâncias onde o SAMU as mantém: 107 USB e 16 USA distribuídas em 92 dos 1.107 locais possíveis. É contra ela que todo ganho é medido.", "7,44 min   •   Gini 0,224", CARD, TEAL],
   ["Metodológico — o p-median clássico", "A mesma frota realocada pela regra da unidade mais próxima, que ignora capacidade. É o comparador que diz o que a técnica 2 acrescenta.", "6,70 min   •   Gini 0,079", "FBEAE7", ORANGE]]
   .forEach((c, i) => {
    const x = M + i * 6.2;
    cartao(s, { x, y: 1.92, w: 5.9, h: 1.38, fill: c[3] });
    s.addText(c[0], { x: x + 0.3, y: 2.06, w: 5.35, h: 0.3, isTextBox: true,
      margin: 0, fontFace: SANS, fontSize: 13, bold: true, color: INK });
    s.addText(c[1], { x: x + 0.3, y: 2.38, w: 5.35, h: 0.6, isTextBox: true,
      margin: 0, valign: "top", fontFace: SANS, fontSize: 11.5, color: INK2,
      lineSpacing: 15 });
    s.addText(c[2], { x: x + 0.3, y: 2.95, w: 5.35, h: 0.3, isTextBox: true,
      margin: 0, fontFace: SERIF, fontSize: 12.5, bold: true, color: c[4] });
  });

  s.addText("As cinco métricas, e o que cada uma mede", { x: M, y: 3.44, w: 12.1,
    h: 0.3, isTextBox: true, margin: 0, fontFace: SANS, fontSize: 13, bold: true,
    color: ORANGE });
  const met = [
    ["E[T] — tempo esperado de resposta", "Minutos de viagem da base até o setor, em média ponderada pela população e pelos dois pools de gravidade. Não inclui regulação, despacho nem tempo em cena.", "7,44 min"],
    ["t até a mais próxima", "Minutos até a unidade mais próxima, sem repartir a demanda. É o objetivo do p-median e a métrica clássica de tempo-resposta.", "8,84 min"],
    ["C(20) — cobertura em 20 minutos", "Fração da população com uma USA a ≤ 20 min. Satura dentro da capital, onde já é 98,2%; no país inteiro era 66,4% e ali discriminava.", "98,2%"],
    ["G(A) — Gini da acessibilidade avançada", "Desigualdade, entre os 26.889 setores, da fatia de USA por habitante ao alcance do setor. Vai de 0 — todos com a mesma fatia — a 1, tudo concentrado. É esta a definição de equidade do trabalho.", "0,224"],
    ["Custo da mudança", "Quantas unidades saem do lugar e quantos quilômetros a frota percorre para assumir a nova configuração, pelo melhor emparelhamento entre origens e destinos.", "0 / 0 km"]];
  s.addTable([["Métrica", "O que mede", "Hoje"].map(t => ({ text: t,
      options: { bold: true, color: "FFFFFF", fill: { color: TEAL },
                 fontSize: 10.5, fontFace: SANS } }))]
    .concat(met.map((r, i) => r.map((c, j) => ({ text: c, options: {
      fontSize: 10.5, fontFace: j === 0 ? SANS : SANS, bold: j === 0 || j === 2,
      color: j === 2 ? (i === 3 ? ORANGE : INK) : (j === 0 ? INK : INK2),
      align: j === 2 ? "center" : "left",
      fill: { color: i % 2 ? "FFFFFF" : CARD } } })))),
    { x: M, y: 3.76, w: 12.1, colW: [3.0, 7.5, 1.6], rowH: 0.44,
      border: { pt: 0, color: CREAM }, valign: "middle" });

  s.addText("Em gente, a cobertura ainda diz algo: os 201 mil paulistanos hoje a mais de 20 minutos de uma USA caem para 160 mil com λ = 1 e para 72 mil com λ = 0,1 — 64% a menos.",
    { x: M, y: 6.52, w: 12.1, h: 0.6, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 13, italic: true, color: TEAL });

  s.addNotes("Equidade neste trabalho é uma coisa só: o Gini da acessibilidade " +
    "avançada entre setores censitários. Não é cobertura — a cobertura satura " +
    "em 98,2% na capital e não separa configuração nenhuma — e não é tempo. E há " +
    "dois defaults diferentes no deck — a rede que o SAMU opera hoje, que é a " +
    "referência de ganho, e o p-median, que é o comparador metodológico.");
}

// ------------------------------------------------------------- 6 premissas
{
  const s = slideClaro("O que foi assumido", "premissas");
  const its = [
    ["Gravidade fixa em 10%", "θ = 0,10 dos chamados exige suporte avançado. Valor arbitrado, não estimado de dado de ocorrência."],
    ["Demanda = população residente", "Cada setor demanda na proporção de seus moradores no Censo 2022. Sem perfil etário nem incidência de agravos."],
    ["Decaimento gaussiano, β = 4,5 min", "Ancorado no despacho (2,2 unidades efetivas por setor), não estimado de escolha observada."],
    ["Candidato = equipamento público", "Uma ambulância só pode ser baseada onde já há UBS, UPA, hospital ou base do SAMU: 1.107 pontos."],
    ["Rede viária em fluxo livre", "Tempos do OpenStreetMap sem trânsito, sem hora de pico e sem prioridade de sirene."],
    ["Frota constante", "123 unidades, 107 USB e 16 USA. O estudo realoca; não propõe compra nem corte."]];
  its.forEach((it, i) => {
    const x = M + (i % 2) * 6.2, y = 1.80 + Math.floor(i / 2) * 1.68;
    cartao(s, { x, y, w: 5.9, h: 1.48 });
    item(s, i + 1, x + 0.28, y + 0.28, 5.35, it[0], it[1], BLUE);
  });
}

// ---------------------------------------------------------------- 6 os dados
{
  const s = slideEscuro(TEAL);
  s.addText("A BASE", { x: M, y: 0.55, w: 11, h: 0.26, isTextBox: true,
    margin: 0, fontFace: SANS, fontSize: 10.5, bold: true, color: GOLD,
    charSpacing: 1.4 });
  s.addText("Tudo público, tudo reconstruível", { x: M, y: 0.83, w: 11.5, h: 0.7,
    isTextBox: true, margin: 0, fontFace: SERIF, fontSize: 32, bold: true,
    color: "FFFFFF" });
  const stats = [["26.889", "setores censitários\nhabitados"],
                 ["11,45 mi", "habitantes\n(Censo 2022)"],
                 ["1.107", "candidatos a base\n(CNES)"],
                 ["123", "ambulâncias\n107 USB + 16 USA"],
                 ["122.830", "nós da malha viária\n(OpenStreetMap)"]];
  stats.forEach((st, i) => {
    const x = M + i * 2.46;
    s.addText(st[0], { x, y: 2.05, w: 2.3, h: 0.75, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 33, bold: true, color: GOLD });
    s.addText(st[1], { x, y: 2.85, w: 2.3, h: 0.8, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 11.5, color: "C9D6E4", lineSpacing: 15 });
  });
  s.addShape(p.ShapeType.roundRect, { x: M, y: 4.25, w: 12.1, h: 1.62,
    rectRadius: 0.10, fill: { color: "FFFFFF", transparency: 92 },
    line: { color: "FFFFFF", transparency: 80 } });
  s.addText("Matriz de tempo de viagem setor × candidato", { x: M + 0.35,
    y: 4.45, w: 11.4, h: 0.3, isTextBox: true, margin: 0, fontFace: SANS,
    fontSize: 13.5, bold: true, color: "FFFFFF" });
  s.addText("Dijkstra a partir de cada uma das 1.107 bases candidatas sobre a rede viária de São Paulo, com corte em 60 minutos. Na limpeza, 23 registros do CNES apareceram com uma coordenada de fábrica errada a 17 km da malha — o “CECO Parque Ibirapuera” entre eles. Todos descartados.",
    { x: M + 0.35, y: 4.80, w: 11.4, h: 0.95, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 11.5, color: "C9D6E4", lineSpacing: 16 });
  s.addText("O pipeline vai da coleta bruta à matriz sem intervenção manual; a avaliação de uma configuração leva 10,5 ms.",
    { x: M, y: 6.15, w: 12.1, h: 0.4, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 13, italic: true, color: "9FB0C4" });
}

// ------------------------------------------------ 7 resultado: a fronteira
{
  const s = slideClaro("Quatro fronteiras, um orçamento de mudança cada",
                       "resultado 1");
  s.addImage({ path: FIG + "sp_01_pareto.png", x: M, y: 1.72, w: 7.3, h: 4.65 });
  const bx = 8.2;
  s.addText("Cada curva é o que se consegue quando a mudança custa λ. Quanto mais cara, mais a fronteira recua para a direita — pior tempo para o mesmo nível de equidade.",
    { x: bx, y: 1.9, w: 4.5, h: 1.3, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 12.5, color: INK2, lineSpacing: 18 });
  cartao(s, { x: bx, y: 3.3, w: 4.5, h: 1.5 });
  s.addText("A configuração atual está fora de qualquer fronteira", { x: bx + 0.28,
    y: 3.48, w: 3.95, h: 0.55, isTextBox: true, margin: 0, fontFace: SANS,
    fontSize: 12.5, bold: true, color: INK });
  s.addText("Há ganho simultâneo de tempo e de equidade disponível — não é um trade-off entre os dois.",
    { x: bx + 0.28, y: 4.02, w: 3.95, h: 0.65, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 11.5, color: INK2, lineSpacing: 15 });
  s.addText("E o p-median clássico já captura boa parte disso — ponto laranja.",
    { x: bx, y: 4.95, w: 4.5, h: 0.8, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 13, italic: true, color: TEAL });
}

// ------------------------------------------- 8 resultado: ganho x quilômetro
{
  const s = slideClaro("Doze unidades e 39 km cortam 62% da desigualdade",
                       "resultado 2");
  s.addImage({ path: FIG + "sp_02_ganho_km.png", x: M, y: 1.82, w: 7.2, h: 3.26 });
  const bx = 8.02;
  const linhas = [["atual", "7,44", "—", "0,224", "—"],
                  ["λ = 1", "7,30", "−8 s", "0,085", "12 / 39 km"],
                  ["λ = 0,3", "7,02", "−25 s", "0,072", "39 / 103 km"],
                  ["λ = 0,1", "6,67", "−46 s", "0,025", "110 / 293 km"],
                  ["λ = 0", "6,64", "−48 s", "0,031", "115 / 385 km"]];
  s.addTable([["", "E[T] min", "Δ por chamado", "Gini", "movidas / km"].map(t => ({ text: t,
      options: { bold: true, color: "FFFFFF", fill: { color: TEAL },
                 fontSize: 9.5, fontFace: SANS } }))]
    .concat(linhas.map((r, i) => r.map((c, j) => ({ text: c, options: {
      fontSize: 10, fontFace: SANS, bold: j === 0 || i === 1,
      color: i === 1 ? INK : INK2,
      fill: { color: i === 1 ? "FBEAE7" : (i % 2 ? "FFFFFF" : CARD) } } })))),
    { x: bx, y: 1.85, w: 4.66, colW: [0.80, 0.80, 1.00, 0.80, 1.26], rowH: 0.34,
      border: { pt: 0, color: CREAM }, valign: "middle" });
  s.addText("Mover 12 das 123 unidades, 39 km no total, derruba o Gini de 0,224 para 0,085 — 62% do ganho de equidade com 10% do deslocamento.",
    { x: bx, y: 4.00, w: 4.66, h: 1.0, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 12.5, color: INK2, lineSpacing: 18 });
  s.addText("Em tempo, essas doze mudanças devolvem só 8 s por chamado: o que elas compram é equidade.",
    { x: bx, y: 5.02, w: 4.66, h: 0.62, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 11.5, color: ORANGE, lineSpacing: 16 });
  cartao(s, { x: bx, y: 5.70, w: 4.66, h: 1.32, fill: CARD });
  s.addText("Por que não λ = 0,1, se o ganho é maior?", { x: bx + 0.28, y: 5.86,
    w: 4.1, h: 0.28, isTextBox: true, margin: 0, fontFace: SANS, fontSize: 12,
    bold: true, color: INK });
  s.addText("Ele é melhor nos dois eixos, mas move 110 das 123 unidades e 293 km — é redesenhar a rede, não realocar. λ = 1 entrega 70% daquele ganho de equidade com 13% do deslocamento.",
    { x: bx + 0.28, y: 6.16, w: 4.1, h: 0.78, isTextBox: true, margin: 0,
      valign: "top", fontFace: SANS, fontSize: 11, color: INK2, lineSpacing: 14 });
  s.addText("Mesmo no redesenho livre, cada unidade anda só 3,1 km em média: a realocação é um salto para a esquina, não uma travessia da cidade.",
    { x: M, y: 5.40, w: 7.2, h: 0.85, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 13.5, italic: true, color: TEAL });
}

// ------------------------------------------------- 9 resultado: as 12 trocas
{
  const s = slideClaro("As doze realocações que mais rendem", "resultado 3");
  s.addImage({ path: FIG + "sp_03_mapa_troca.png", x: M, y: 1.55, w: 4.95, h: 4.63 });
  const bx = 6.1;
  s.addText("Com λ = 1 — mudança cara — o otimizador escolhe doze movimentos e nada mais. O padrão é geográfico e nítido:",
    { x: bx, y: 1.78, w: 6.6, h: 0.85, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 12.5, color: INK2, lineSpacing: 18 });
  [["As USA migram para a periferia", "Saem do centro expandido em direção ao leste e ao sul, onde a densidade é alta e a cobertura avançada é rala.", ORANGE],
   ["As USB pulam a esquina", "Movimentos de poucas centenas de metros, para um equipamento vizinho que cobre melhor o entorno.", BLUE]]
   .forEach((c, i) => {
    const y = 2.85 + i * 1.55;
    cartao(s, { x: bx, y, w: 6.6, h: 1.32, fill: i ? CARD : "FBEAE7" });
    s.addText(c[0], { x: bx + 0.3, y: y + 0.18, w: 6.0, h: 0.3, isTextBox: true,
      margin: 0, fontFace: SANS, fontSize: 13.5, bold: true, color: c[2] });
    s.addText(c[1], { x: bx + 0.3, y: y + 0.54, w: 6.0, h: 0.68, isTextBox: true,
      margin: 0, fontFace: SANS, fontSize: 11.5, color: INK2, lineSpacing: 15 });
  });
  s.addText("Doze decisões administrativas, nenhuma obra, nenhuma compra.",
    { x: bx, y: 5.95, w: 6.6, h: 0.4, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 14, italic: true, color: TEAL });
}

// -------------------------------------------- 10 resultado: contra o baseline
{
  const s = slideClaro("Contra o baseline clássico: o que muda e o que não",
                       "resultado 4 — o achado central");
  s.addImage({ path: FIG + "sp_05_comparacao.png", x: M, y: 1.72, w: 7.45, h: 4.85 });
  const bx = 8.35;
  cartao(s, { x: bx, y: 1.8, w: 4.35, h: 1.72, fill: "FBEAE7" });
  s.addText("O modelo de Huff quase não muda a eficiência", { x: bx + 0.28,
    y: 1.98, w: 3.8, h: 0.6, isTextBox: true, margin: 0, fontFace: SANS,
    fontSize: 13, bold: true, color: INK });
  s.addText("Planejar pela regra clássica custa só +0,4% de tempo esperado quando a demanda de fato se reparte. O p-median é robusto à hipótese de alocação.",
    { x: bx + 0.28, y: 2.56, w: 3.8, h: 0.9, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 11.5, color: INK2, lineSpacing: 15 });
  cartao(s, { x: bx, y: 3.68, w: 4.35, h: 1.9, fill: CARD });
  s.addText("O que só o 2SFCA enxerga", { x: bx + 0.28, y: 3.86, w: 3.8, h: 0.3,
    isTextBox: true, margin: 0, fontFace: SANS, fontSize: 13, bold: true,
    color: INK });
  s.addText("Capacidade. O p-median ignora quantos habitantes disputam cada base, então não vê a carga. Gini 0,025 contra 0,079 — 3,1× melhor — e com menos deslocamento: 293 km contra 373 km.",
    { x: bx + 0.28, y: 4.22, w: 3.8, h: 1.25, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 11.5, color: INK2, lineSpacing: 15 });
  s.addText("Baseline aqui é a rede que o SAMU opera hoje: 7,44 min e Gini 0,224. Se o artigo prometer ganho de tempo, um revisor derruba com o próprio p-median.",
    { x: bx, y: 5.68, w: 4.35, h: 0.85, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 12.5, italic: true, color: TEAL });
  s.addNotes("Este é o slide que reformula a contribuição do trabalho. A " +
    "novidade defensável é a dimensão de equidade com custo de mudança, não " +
    "redução de tempo de resposta.");
}

// ------------------------------------------------- 11 resultado: distribuição
{
  const s = slideClaro("Onde exatamente o ganho de equidade aparece",
                       "resultado 5");
  s.addImage({ path: FIG + "sp_04_lorenz.png", x: M, y: 1.6, w: 4.6, h: 4.27 });
  const bx = 5.8;
  s.addText("A curva de Lorenz mostra onde o ganho de equidade aparece: nos primeiros 40% da população ordenada por acessibilidade — exatamente a parcela hoje mal servida por suporte avançado.",
    { x: bx, y: 1.85, w: 6.9, h: 1.25, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 12.5, color: INK2, lineSpacing: 18 });
  const nums = [["0,224", "configuração atual", GREY],
                ["0,079", "p-median clássico", ORANGE],
                ["0,025", "Huff + 2SFCA", BLUE]];
  nums.forEach((n, i) => {
    const y = 3.35 + i * 0.92;
    s.addText(n[0], { x: bx, y, w: 1.5, h: 0.58, isTextBox: true, margin: 0,
      fontFace: SERIF, fontSize: 27, bold: true, color: n[2] });
    s.addText(n[1], { x: bx + 1.65, y: y + 0.12, w: 5.2, h: 0.36,
      isTextBox: true, margin: 0, fontFace: SANS, fontSize: 13, color: INK2 });
  });
  s.addText("Gini da acessibilidade a suporte avançado, entre os 26.889 setores: 0 significa que todo habitante dispõe da mesma fatia de USA por pessoa; 1, que tudo está concentrado num setor. É esta a definição de equidade do trabalho.",
    { x: bx, y: 6.02, w: 6.9, h: 0.6, isTextBox: true, margin: 0, fontFace: SANS,
      fontSize: 10.5, color: GREY, lineSpacing: 14 });
}

// ----------------------------------------------------------- 12 limitações
{
  const s = slideClaro("O que este resultado ainda não sustenta", "limitações");
  const its = [
    ["β não é estimado, é arbitrado", "O parâmetro governa o modelo inteiro: de β=1,5 a β=12 o tempo esperado vai de 6,5 a 13,6 min. Sem dado de escolha real, a ancoragem é argumentativa."],
    ["α é inerte neste caso", "Quase todo local tem uma só ambulância, então a atratividade é igual em todos. De α=1 para α=2 o tempo esperado vai de 11,78 para 11,80 min."],
    ["Não há fila nem ocupação", "O 2SFCA mede pressão sobre a base, não a probabilidade de a unidade estar ocupada. Um modelo de disponibilidade diria outra coisa."],
    ["Tempos sem trânsito", "A malha do OSM em fluxo livre subestima o deslocamento real, e provavelmente de forma desigual pela cidade."],
    ["Heurísticas, não ótimo", "NSGA-II e p-median são heurísticos. O p-median ficou 1,15% acima do ótimo exato em instâncias pequenas; no tamanho real não há garantia."],
    ["Um município, não a rede", "São Paulo é denso e bem servido. Nada aqui se transfere direto para o estado, que é onde a desigualdade da EDA aparecia."]];
  its.forEach((it, i) => {
    const x = M + (i % 2) * 6.2, y = 1.80 + Math.floor(i / 2) * 1.68;
    cartao(s, { x, y, w: 5.9, h: 1.48, fill: "F3EDE9" });
    item(s, i + 1, x + 0.28, y + 0.28, 5.35, it[0], it[1], ORANGE);
  });
}

// -------------------------------------------------------------- 13 evolução
{
  const s = slideClaro("Por onde seguir", "pontos de evolução");
  const its = [
    ["Sensibilidade em β — o mais urgente", "Repetir a varredura de λ para β ∈ {2, 4, 6, 8,5} e mostrar se o achado de equidade sobrevive. Enquanto não existir, é a crítica mais fácil de fazer ao trabalho."],
    ["Cobertura da USA em faixas curtas", "Em 20 min a capital satura — 98,2% hoje, 99,4% realocada — e a métrica quase não separa configurações. Abaixo de 10 min ela volta a discriminar, e é a leitura mais direta para quem chega de fora. O pipeline já calcula: falta só variar τ."],
    ["Demanda por incidência, não por população", "Ponderar o setor pelo perfil etário e pela incidência de agravos. É a ponte natural para o modelo bayesiano CAR/ICAR já previsto como fase 2."],
    ["Escalar para o estado com a técnica 1", "São Paulo é o piloto. O gargalo de escala para uma rede estadual é exatamente o que o RL/GNN resolve, e a técnica 2 lhe dá o modelo de demanda."],
    ["Disponibilidade em vez de pressão", "Trocar o proxy de carga do 2SFCA por um modelo de fila, para responder “qual a chance de a unidade estar livre” e não só “quantos disputam esta base”."],
    ["ADNet multi-período como extensão", "Exige reconstruir a série histórica do CNES, mas é o único caminho para modelar realocação como decisão ao longo do tempo, e não como foto."]];
  its.forEach((it, i) => {
    const y = 1.72 + i * 0.955;
    bolha(s, i + 1, M, y, i === 1 ? ORANGE : BLUE);
    s.addText(it[0], { x: M + 0.68, y: y - 0.03, w: 11.5, h: 0.28,
      isTextBox: true, margin: 0, valign: "top", fontFace: SANS, fontSize: 14,
      bold: true, color: INK });
    s.addText(it[1], { x: M + 0.68, y: y + 0.27, w: 11.5, h: 0.62,
      isTextBox: true, margin: 0, valign: "top", fontFace: SANS, fontSize: 11.5,
      color: INK2, lineSpacing: 15 });
  });
}

// ----------------------------------------------------------- 14 conclusões
{
  const s = slideEscuro(NAVY);
  s.addText("CONCLUSÕES PRÉVIAS", { x: M, y: 0.62, w: 11, h: 0.26,
    isTextBox: true, margin: 0, fontFace: SANS, fontSize: 10.5, bold: true,
    color: GOLD, charSpacing: 1.4 });
  s.addText("O que já dá para afirmar", { x: M, y: 0.90, w: 11.5, h: 0.7,
    isTextBox: true, margin: 0, fontFace: SERIF, fontSize: 32, bold: true,
    color: "FFFFFF" });
  const its = [
    ["A realocação é local e barata", "Doze unidades percorrendo 39 km ao todo cortam 62% da desigualdade de acesso a suporte avançado — e devolvem 8 s por chamado. Nenhuma obra, nenhuma compra: doze decisões administrativas."],
    ["O modelo de demanda não compra eficiência", "Planejar pela regra clássica da unidade mais próxima custa apenas +0,4% de tempo esperado. O p-median é robusto à hipótese que a técnica 2 se propunha a derrubar."],
    ["O ganho real, e verificável, é equidade", "Gini da acessibilidade avançada de 0,224 para 0,025, contra 0,079 do p-median, e com menos deslocamento — com o tempo esperado caindo 0,77 min (46 s) por chamado. A capacidade disputada é o que só o 2SFCA enxerga."],
    ["A tese defensável mudou de lugar", "Não é “chegamos mais rápido” — o p-median já entrega o mesmo tempo. É “distribuímos a carga de forma muito mais equânime, pelo mesmo tempo de resposta e com menos mudança”."]];
  its.forEach((it, i) => {
    const y = 2.05 + i * 1.15;
    bolha(s, i + 1, M, y, i === 3 ? GOLD : ORANGE);
    s.addText(it[0], { x: M + 0.68, y: y - 0.03, w: 10.2, h: 0.3,
      isTextBox: true, margin: 0, valign: "top", fontFace: SANS,
      fontSize: 14.5, bold: true, color: "FFFFFF" });
    s.addText(it[1], { x: M + 0.68, y: y + 0.28, w: 9.7, h: 0.68,
      isTextBox: true, margin: 0, valign: "top", fontFace: SANS,
      fontSize: 11.5, color: "AEBDCE", lineSpacing: 15 });
  });
  s.addText("Código, dados e figuras reprodutíveis em sp/ — cada módulo roda o próprio teste.",
    { x: M, y: 6.78, w: 12.1, h: 0.35, isTextBox: true, margin: 0,
      fontFace: SANS, fontSize: 10.5, color: "7C8CA0" });
}

p.writeFile({ fileName: "/home/claude/eda/deck/apresentacao_usb_usa_sp.pptx" })
 .then(f => console.log("gerado:", f));
