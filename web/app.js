import { Arena, TERRENOS } from "./arena.js";
import { criarCompletar } from "./completar.js";
import { Editor } from "./editor.js";

const MAXIMO_DE_TURNOS_AUTOMATICOS = 40;
const MAXIMO_NO_REGISTRO = 300;
const NOMES_DOS_TIPOS = { tank: "tanque", submarine: "submarino", aircraft: "aeronave" };
const ESPECIAIS = {
  tank: "se abriga nas ruínas",
  submarine: "dive/surface; submerso só leva torpedo",
  aircraft: "voa sobre ilhas; torpedo não atinge",
};
const NOMES_DE_EXEMPLO = { gun: "Canhao", torpedo: "Torpedo", missile: "Missil" };
const PLACEHOLDERS = {
  cenario: "# Monte seu exército aqui. Exemplo:\n# tank Rex { gun Canhao }\n# Abra o Manual para ver os tipos e o orçamento.",
  turno: "# Ordens de cada turno. Exemplo:\n# move Rex 60 40\n# fire Rex Canhao Brutus",
};

const $ = (seletor) => document.querySelector(seletor);

const jogo = {
  fase: "cenario",
  partida: null,
  estado: null,
  ocupado: false,
  automatico: false,
};

function ler(chave) {
  try {
    return localStorage.getItem(chave);
  } catch {
    return null;
  }
}

function salvar(chave, valor) {
  try {
    localStorage.setItem(chave, valor);
  } catch {
    /* armazenamento indisponível: o rascunho só não fica salvo */
  }
}

function escapar(texto) {
  return String(texto).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

async function chamar(rota, codigo) {
  const resposta = await fetch(rota, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ codigo }),
  });
  const dados = await resposta.json();
  return { ok: resposta.ok, dados };
}

let salvarDepois;
let verificarDepois;
let catalogo;
const sugerir = criarCompletar(() => ({ aba: editor.atual, catalogo, unidades: jogo.estado?.unidades || [] }));
const editor = new Editor($("#editor"), executar, (aba, texto) => {
  clearTimeout(salvarDepois);
  salvarDepois = setTimeout(() => salvar(`tankio:v2:${aba}`, texto), 300);
  esconderErros();
  if (aba === "cenario") {
    clearTimeout(verificarDepois);
    verificarDepois = setTimeout(verificarExercito, 350);
  }
}, sugerir);

await Promise.race([document.fonts.ready, new Promise((resolve) => setTimeout(resolve, 1500))]);
const cena = await new Arena($("#arena"), {
  aoPassarNaCelula: ({ x, y, terreno }) => {
    $("#dica").textContent = `x ${x}–${x + 9} · y ${y}–${y + 9} · ${TERRENOS[terreno] || TERRENOS["."]}`;
  },
  aoSairDoMapa: () => {
    $("#dica").textContent = "Passe o mouse no mapa; clique para inserir as coordenadas.";
  },
  aoClicarCelula: ({ x, y }) => {
    if (!jogo.ocupado) editor.inserir(`${x} ${y}`);
  },
}).pronta;

let mapa;
[catalogo, mapa] = await Promise.all([
  fetch("/api/catalogo").then((resposta) => resposta.json()),
  fetch("/api/mapa").then((resposta) => resposta.json()),
]);
cena.montarMapa(mapa);

/* ---------- manual ---------- */

function montarManual() {
  for (const [classe, valor] of [["m-orcamento", catalogo.orcamento], ["m-extra", catalogo.custo_de_arma_extra], ["m-maximo", catalogo.maximo_de_armas], ["m-recarga-sonar", catalogo.recarga_do_sonar]]) {
    for (const elemento of document.getElementsByClassName(classe)) elemento.textContent = valor;
  }
  $("#manual-unidades").innerHTML = `
    <thead><tr><th>Tipo</th><th>Custo</th><th>HP</th><th>Blindagem</th><th>Velocidade</th><th>Visão</th><th>Sonar</th><th>Arma</th><th>Especial</th></tr></thead>
    <tbody>${Object.entries(catalogo.unidades).map(([tipo, u]) => `
      <tr><td><code>${tipo}</code> <small>${NOMES_DOS_TIPOS[tipo] || ""}</small></td><td>${u.custo}</td><td>${u.hp}</td><td>${u.armor}</td>
      <td>${u.speed}</td><td>${u.radar / 10} casas</td><td>${u.sonar / 10} casas</td><td><code>${u.armas.join(", ")}</code></td><td>${ESPECIAIS[tipo] || ""}</td></tr>`).join("")}
    </tbody>`;
  $("#manual-armas").innerHTML = `
    <thead><tr><th>Arma</th><th>Dano</th><th>Alcance</th><th>Munição</th><th>Recarga</th></tr></thead>
    <tbody>${Object.entries(catalogo.armas).map(([arma, a]) => `
      <tr><td><code>${arma}</code></td><td>${a.damage}</td><td>${a.range}</td><td>${a.ammo}</td><td>${a.cooldown} turno${a.cooldown > 1 ? "s" : ""}</td></tr>`).join("")}
    </tbody>`;
}

function abrirManual() {
  $("#manual").showModal();
}

/* ---------- interface ---------- */

function mostrarAba(nome) {
  editor.mostrar(nome);
  editor.cm.setOption("placeholder", PLACEHOLDERS[nome]);
  for (const aba of document.querySelectorAll(".aba")) aba.classList.toggle("ativa", aba.dataset.aba === nome);
  $("#orcamento").hidden = nome !== "cenario";
  $("#executar-rotulo").textContent = nome === "cenario" ? (jogo.partida ? "Reiniciar batalha" : "Iniciar batalha") : "Executar turno";
  $("#automatico").hidden = nome !== "turno";
  $("#explicacao").textContent = nome === "cenario"
    ? `Declare só as suas unidades e armas, até ${catalogo.orcamento} pontos. O jogo monta a frota inimiga com o mesmo orçamento.`
    : "Este programa roda uma vez por turno, comandando só o seu exército. Depois dele, a IA joga.";
  atualizarTrechos();
}

function definirFase(fase, texto) {
  jogo.fase = fase;
  $("#fase").textContent = texto;
  $("#fase").dataset.fase = fase;
}

function ocupar(ativo) {
  jogo.ocupado = ativo;
  editor.somenteLeitura(ativo);
  $("#executar").disabled = ativo;
  for (const aba of document.querySelectorAll(".aba")) aba.disabled = ativo || (aba.dataset.aba === "turno" && !jogo.partida);
}

function mostrarErros(erros) {
  editor.marcarErros(erros);
  const lista = $("#erros");
  lista.innerHTML = erros.map((erro) => `
    <li data-linha="${erro.linha ?? ""}">
      <span class="fase-erro">${escapar(erro.fase || "erro")}</span>
      ${escapar(erro.mensagem)}
    </li>`).join("");
  lista.hidden = false;
  if (erros[0]?.linha) editor.irPara(erros[0].linha);
}

function esconderErros() {
  $("#erros").hidden = true;
}

async function verificarExercito() {
  let dados;
  try {
    ({ dados } = await chamar("/api/exercito", editor.texto("cenario")));
  } catch {
    return;
  }
  const proporcao = Math.min(1, dados.custo / dados.orcamento);
  $("#orcamento-valor").textContent = `${dados.custo} / ${dados.orcamento}`;
  $("#orcamento").classList.toggle("estourado", dados.custo > dados.orcamento);
  $("#orcamento-preenchido").style.width = `${proporcao * 100}%`;
  const itens = dados.unidades.map((u) => `
    <li><b>${escapar(u.nome)}</b> ${NOMES_DOS_TIPOS[u.tipo]} · ${u.armas.length} arma${u.armas.length === 1 ? "" : "s"} · ${u.custo} pts</li>`);
  const problemas = dados.erros.filter((erro) => !/declare pelo menos uma unidade/.test(erro.mensagem));
  if (problemas.length) {
    itens.push(`<li class="problema">${problemas.length} problema${problemas.length > 1 ? "s" : ""}: ${escapar(problemas[0].mensagem.replace(/^Linha \d+, coluna \d+: /, ""))}</li>`);
  }
  $("#exercito").innerHTML = itens.join("") || '<li class="vazio">Nenhuma unidade ainda.</li>';
}

function registrar(texto, origem, linha) {
  const item = document.createElement("li");
  item.className = origem;
  const rotulos = { cenario: "cenário", jogador: "você", ia: "IA", sistema: "sistema" };
  item.innerHTML = `<span class="origem">${rotulos[origem] || origem}</span>${linha ? `<button class="linha" data-linha="${linha}">L${linha}</button>` : ""}<span class="texto">${escapar(texto)}</span>`;
  const lista = $("#registro");
  lista.append(item);
  while (lista.children.length > MAXIMO_NO_REGISTRO) lista.firstElementChild.remove();
  lista.scrollTop = lista.scrollHeight;
}

function registrarEvento(evento) {
  if (evento.tipo === "InicioDoTurno") {
    registrar(`Turno ${evento.turno}`, "turno-titulo");
  } else if (evento.tipo === "IfStatement") {
    registrar(`if → ${evento.resultado ? "verdadeiro" : "falso"}`, evento.origem, evento.linha);
  } else if (evento.tipo === "RepeatStatement") {
    registrar(`repeat × ${evento.vezes}`, evento.origem, evento.linha);
  }
  for (const mensagem of evento.mensagens) registrar(mensagem, evento.origem, evento.linha);
}

function pontos(quantidade) {
  return quantidade > 8 ? `${quantidade}` : "●".repeat(quantidade) || "0";
}

function atualizarUnidades(estado) {
  const unidades = [...estado.unidades].sort((a, b) => (a.lado === "jogador" ? -1 : 0) - (b.lado === "jogador" ? -1 : 0));
  $("#unidades").innerHTML = unidades.map((u) => {
    const oculto = u.lado !== "jogador" && !u.visivel && u.vivo;
    const etiquetas = [
      !u.vivo && "destruído",
      u.profundidade > 0 && `submerso ${u.profundidade}m`,
      u.exposto && "exposto · dano 2×",
      u.detectado && u.lado !== "jogador" && "detectado",
      u.detectado && u.lado === "jogador" && u.vivo && "posição revelada",
    ].filter(Boolean);
    const proporcao = u.hp_max ? Math.max(0, Math.min(1, u.hp / u.hp_max)) : 0;
    const armas = oculto ? "" : u.armas.map((arma) => `
      <li>
        <button type="button" class="inserir" data-inserir="${escapar(arma.nome)}">${escapar(arma.nome)}</button>
        <span>${arma.tipo} · dano ${arma.dano} · alcance ${arma.alcance}</span>
        <span class="municao" title="munição">${pontos(arma.municao)}</span>
        ${arma.recarga > 0 ? `<span class="recarga">recarga ${arma.recarga}</span>` : ""}
      </li>`).join("");
    const numeros = oculto
      ? "sem contato: posição e HP desconhecidos"
      : `HP ${u.hp}/${u.hp_max} · (${u.x}, ${u.y}) · blindagem ${u.armadura}${u.lado === "jogador" && u.vivo
        ? ` · movimento ${u.movimento}/${u.velocidade} · sonar ${u.sonar_recarga ? `recarga ${u.sonar_recarga}` : "pronto"}`
        : ""}`;
    return `
      <article class="cartao ${u.lado} ${u.vivo ? "" : "morto"} ${oculto ? "oculto" : ""}">
        <header>
          <button type="button" class="inserir nome" data-inserir="${escapar(u.nome)}">${escapar(u.nome)}</button>
          <span class="tipo">${NOMES_DOS_TIPOS[u.tipo] || u.tipo}</span>
        </header>
        ${oculto ? "" : `<div class="vida" role="meter" aria-valuemin="0" aria-valuemax="${u.hp_max}" aria-valuenow="${u.hp}" aria-label="HP de ${escapar(u.nome)}">
          <div style="width:${proporcao * 100}%" class="${proporcao > 0.6 ? "alta" : proporcao > 0.3 ? "media" : "baixa"}"></div>
        </div>`}
        <p class="numeros">${numeros}</p>
        ${etiquetas.length ? `<p class="etiquetas">${etiquetas.map((e) => `<span>${e}</span>`).join("")}</p>` : ""}
        ${armas ? `<ul class="armas">${armas}</ul>` : ""}
      </article>`;
  }).join("");
}

function atualizarTrechos() {
  const estado = jogo.estado;
  const minhas = estado?.unidades.filter((u) => u.lado === "jogador" && u.vivo) || [];
  const inimigas = estado?.unidades.filter((u) => u.lado === "inimigo" && u.vivo) || [];
  const unidade = minhas[0]?.nome || "Unidade";
  const arma = minhas[0]?.armas[0]?.nome || "Arma";
  const alvo = inimigas.find((u) => u.visivel)?.nome || inimigas[0]?.nome || "Alvo";
  const submarino = minhas.find((u) => u.tipo === "submarine")?.nome;

  const trechos = editor.atual === "cenario"
    ? Object.entries(catalogo.unidades).map(([tipo, dados]) => {
        const armaDoTipo = dados.armas[0];
        return [`${tipo} · ${dados.custo} pts`, `${tipo} Nome { ${armaDoTipo} ${NOMES_DE_EXEMPLO[armaDoTipo] || "Arma"} }\n`];
      })
    : [
        ["move", `move ${unidade} 60 40\n`],
        ["fire", `fire ${unidade} ${arma} ${alvo}\n`],
        ["attack", `attack ${unidade} ${alvo}\n`],
        ...(submarino ? [["dive", `dive ${submarino} 30\n`], ["surface", `surface ${submarino}\n`]] : []),
        ["sonar", `sonar ${unidade}\n`],
        ["if", `if ${unidade}.hp < 50 {\n    \n}\n`],
        ["repeat", "repeat 2 {\n    \n}\n"],
      ];
  $("#trechos").innerHTML = trechos.map(([nome, codigo]) => `
    <button type="button" class="trecho" data-codigo="${escapar(codigo)}" title="${escapar(codigo.trim())}">
      <b>${nome}</b><code>${escapar(codigo.split("\n")[0])}</code>
    </button>`).join("");
}

/* ---------- execução ---------- */

async function reproduzir(eventos) {
  const rapido = eventos.length > 120;
  if (rapido) registrar(`${eventos.length} instruções: animação acelerada`, "sistema");
  const velocidadeOriginal = cena.velocidade;
  if (rapido) cena.velocidade = Math.max(cena.velocidade, 6);

  let anterior = jogo.estado;
  for (const evento of eventos) {
    if (evento.linha && (evento.origem === "cenario" || evento.origem === "jogador")) editor.destacar(evento.linha);
    registrarEvento(evento);
    await cena.animarEvento(evento, anterior);
    cena.aplicarEstado(evento.estado);
    atualizarUnidades(evento.estado);
    jogo.estado = evento.estado;
    anterior = evento.estado;
  }
  cena.velocidade = velocidadeOriginal;
  editor.destacar(null);
  atualizarTrechos();
}

function modeloDoTurno(partida) {
  const minhas = partida.estado_inicial.unidades.filter((u) => u.lado === "jogador");
  const linhas = [
    "# Este programa roda uma vez por turno.",
    `# Você comanda: ${minhas.map((u) => u.nome).join(", ")}.`,
    "# Clique numa célula do mapa para inserir as coordenadas.",
  ];
  for (const unidade of minhas) linhas.push(`move ${unidade.nome} ${unidade.x + unidade.velocidade} ${unidade.y}`);
  return `${linhas.join("\n")}\n`;
}

async function iniciarBatalha() {
  const { ok, dados } = await chamar("/api/partidas", editor.texto("cenario"));
  if (!ok) return mostrarErros(dados.erros);

  jogo.partida = dados;
  jogo.estado = dados.estado_inicial;
  $("#registro").innerHTML = "";
  cena.montarMapa(dados.mapa);
  cena.aplicarEstado(dados.estado_inicial, { instantaneo: true });
  atualizarUnidades(dados.estado_inicial);
  $("#turno").textContent = "Turno 0";
  $("#lados").hidden = false;
  $("#lados").innerHTML = `<b class="azul">${escapar(dados.jogador)}</b> vs <b class="vermelho">${escapar(dados.inimigo)}</b>`;
  registrar(`Seu exército: ${dados.comandaveis.join(", ")}.`, "sistema");
  registrar("A IA montou a frota inimiga:", "sistema");
  for (const linha of dados.codigo_do_inimigo.split("\n")) registrar(linha, "ia");

  await reproduzir(dados.eventos);

  if (!editor.texto("turno").trim()) editor.definir("turno", modeloDoTurno(dados));
  definirFase("turnos", "Sua vez");
  ocupar(false);
  mostrarAba("turno");
}

async function jogarTurno() {
  const { ok, dados } = await chamar(`/api/partidas/${jogo.partida.id}/turnos`, editor.texto("turno"));
  if (!ok) {
    jogo.automatico = false;
    return mostrarErros(dados.erros);
  }
  definirFase("executando", "Executando turno");
  $("#turno").textContent = `Turno ${dados.turno}`;
  await reproduzir(dados.eventos);
  jogo.partida = { ...jogo.partida, ...dados };
  if (dados.vencedor) {
    jogo.automatico = false;
    definirFase("fim", dados.vencedor === jogo.partida.jogador ? "Vitória" : "Derrota");
    mostrarFim(dados);
  } else {
    definirFase("turnos", "Sua vez");
  }
}

async function executar() {
  if (jogo.ocupado) return;
  esconderErros();
  ocupar(true);
  try {
    if (editor.atual === "cenario") {
      jogo.partida = null;
      await iniciarBatalha();
    } else if (jogo.fase !== "fim") {
      do {
        await jogarTurno();
      } while (jogo.automatico && jogo.fase === "turnos" && jogo.partida.turno < MAXIMO_DE_TURNOS_AUTOMATICOS);
    }
  } catch (erro) {
    mostrarErros([{ mensagem: `Falha ao falar com o servidor: ${erro.message}` }]);
  } finally {
    jogo.automatico = false;
    $("#automatico").classList.remove("ativo");
    $("#automatico").textContent = "Automático";
    ocupar(false);
  }
}

function mostrarFim(dados) {
  const venceu = dados.vencedor === jogo.partida.jogador;
  $("#fim").dataset.resultado = venceu ? "vitoria" : "derrota";
  $("#fim-titulo").textContent = venceu ? "Vitória" : "Derrota";
  $("#fim-texto").textContent = venceu
    ? `Você destruiu a frota inimiga no turno ${dados.turno}.`
    : `Seu exército foi destruído no turno ${dados.turno}. Ajuste o exército ou o programa e tente de novo.`;
  $("#fim").hidden = false;
}

/* ---------- eventos da página ---------- */

for (const aba of document.querySelectorAll(".aba")) {
  aba.addEventListener("click", () => mostrarAba(aba.dataset.aba));
}

$("#executar").addEventListener("click", executar);
$("#abrir-manual").addEventListener("click", abrirManual);
for (const botao of document.querySelectorAll("[data-fechar-manual]")) {
  botao.addEventListener("click", () => $("#manual").close());
}
$("#manual").addEventListener("close", () => salvar("tankio:v2:manual-visto", "1"));

$("#automatico").addEventListener("click", () => {
  if (jogo.ocupado) {
    jogo.automatico = false;
    $("#automatico").textContent = "Parando…";
    return;
  }
  jogo.automatico = true;
  $("#automatico").classList.add("ativo");
  $("#automatico").textContent = "Parar";
  executar();
});

for (const botao of document.querySelectorAll("[data-velocidade]")) {
  botao.addEventListener("click", () => {
    cena.velocidade = Number(botao.dataset.velocidade);
    for (const outro of document.querySelectorAll("[data-velocidade]")) outro.classList.toggle("ativo", outro === botao);
  });
}

document.addEventListener("click", (evento) => {
  const inserir = evento.target.closest("[data-inserir]");
  if (inserir && !jogo.ocupado) editor.inserir(`${inserir.dataset.inserir} `);
  const trecho = evento.target.closest("[data-codigo]");
  if (trecho && !jogo.ocupado) editor.inserir(trecho.dataset.codigo);
  const linha = evento.target.closest("[data-linha]");
  if (linha?.dataset.linha) editor.irPara(Number(linha.dataset.linha));
});

$("#fim-ver").addEventListener("click", () => {
  $("#fim").hidden = true;
});

$("#fim-nova").addEventListener("click", () => {
  $("#fim").hidden = true;
  jogo.partida = null;
  definirFase("cenario", "Planejamento");
  mostrarAba("cenario");
  ocupar(false);
});

montarManual();
editor.definir("cenario", ler("tankio:v2:cenario") || "");
editor.definir("turno", ler("tankio:v2:turno") || "");
mostrarAba("cenario");
verificarExercito();
if (!ler("tankio:v2:manual-visto")) abrirManual();
