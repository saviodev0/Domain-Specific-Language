const ATRIBUTOS_CONSULTAVEIS = [
  ["hp", "pontos de vida"],
  ["armor", "blindagem"],
  ["speed", "velocidade por turno"],
  ["radar", "alcance da visão"],
  ["depth", "profundidade (submarino)"],
  ["x", "posição horizontal"],
  ["y", "posição vertical"],
];
const NOMES_DE_EXEMPLO = { gun: "Canhao", torpedo: "Torpedo", missile: "Missil" };
const COMANDOS = [
  ["move", "move unidade x y", "anda até (x, y)"],
  ["fire", "fire unidade arma alvo", "dispara uma arma"],
  ["attack", "attack unidade alvo", "dispara a primeira arma pronta"],
  ["dive", "dive submarino profundidade", "submerge"],
  ["surface", "surface submarino", "emerge"],
  ["sonar", "sonar unidade", "revela inimigos a 3–4 casas"],
  ["if", "if unidade.hp < 50 { … }", "executa se for verdade"],
  ["repeat", "repeat 2 { … }", "repete o bloco"],
];

function item(texto, rotulo, dica) {
  return { text: texto, displayText: rotulo ?? texto.trim(), dica, render: desenhar };
}

function desenhar(elemento, _dados, sugestao) {
  const nome = document.createElement("span");
  nome.className = "sugestao-nome";
  nome.textContent = sugestao.displayText;
  elemento.append(nome);
  if (sugestao.dica) {
    const dica = document.createElement("span");
    dica.className = "sugestao-dica";
    dica.textContent = sugestao.dica;
    elemento.append(dica);
  }
}

/** Devolve o tipo do bloco `{` aberto no cursor (tank, gun, ...) no cenário, ignorando comentários. */
function blocoAberto(texto) {
  const pilha = [];
  let cabecalho = "";
  for (const parte of texto.replace(/#.*$/gm, "").split(/([{}])/)) {
    if (parte === "{") {
      pilha.push(cabecalho.match(/(tank|submarine|aircraft|gun|torpedo|missile)\s+\w+\s*$/)?.[1] ?? "");
    } else if (parte === "}") {
      pilha.pop();
    } else {
      cabecalho = parte;
    }
  }
  return pilha.at(-1) ?? null;
}

function sugestoesDoCenario(tokens, textoAntes, catalogo) {
  const bloco = blocoAberto(textoAntes);
  const tipos = Object.entries(catalogo.unidades);

  if (bloco && catalogo.unidades[bloco]) {
    const armas = catalogo.unidades[bloco].armas;
    if (tokens.length === 0) {
      return armas.map((arma) => {
        const a = catalogo.armas[arma];
        return item(`${arma} ${NOMES_DE_EXEMPLO[arma] || "Arma"}`, arma, `dano ${a.damage} · alcance ${a.range} · munição ${a.ammo}`);
      });
    }
    if (tokens.length === 1 && armas.includes(tokens[0])) {
      return [item(NOMES_DE_EXEMPLO[tokens[0]] || "Arma", undefined, "nome da arma")];
    }
    return [];
  }
  if (bloco) return [];

  if (tokens.length === 0) {
    return tipos.map(([tipo, u]) => item(`${tipo} `, tipo, `${u.custo} pts · hp ${u.hp} · arma ${u.armas.join(", ")}`));
  }
  if (tokens.length === 2 && catalogo.unidades[tokens[0]]) {
    const arma = catalogo.unidades[tokens[0]].armas[0];
    const nome = NOMES_DE_EXEMPLO[arma] || "Arma";
    return [
      item(`{ ${arma} ${nome} }`, `{ ${arma} ${nome} }`, "1 arma (incluída no custo)"),
      item(`{ ${arma} ${nome} ${arma} ${nome}2 }`, `{ ${arma} ${nome} ${arma} ${nome}2 }`, `2 armas (+${catalogo.custo_de_arma_extra} pt)`),
      item("{ }", "{ }", "sem armas"),
    ];
  }
  return [];
}

function sugestoesDoTurno(tokens, unidades) {
  const minhas = unidades.filter((u) => u.lado === "jogador" && u.vivo);
  const inimigas = unidades.filter((u) => u.lado === "inimigo" && u.vivo).sort((a, b) => b.visivel - a.visivel);
  const descrever = (u) => (u.lado === "jogador" || u.visivel
    ? `${u.tipo} · hp ${u.hp} · (${u.x}, ${u.y})`
    : `${u.tipo} · sem contato`);
  const nomes = (lista) => lista.map((u) => item(`${u.nome} `, u.nome, descrever(u)));
  const [comando, ...argumentos] = tokens;

  if (tokens.length === 0) {
    return COMANDOS
      .filter(([nome]) => !["dive", "surface"].includes(nome) || minhas.some((u) => u.tipo === "submarine"))
      .map(([nome, uso, dica]) => item(`${nome} `, nome, `${uso} — ${dica}`));
  }

  const unidade = minhas.find((u) => u.nome === argumentos[0]);
  switch (comando) {
    case "move":
      if (argumentos.length === 0) return nomes(minhas);
      if (argumentos.length === 1 && unidade) {
        const alvo = inimigas.find((u) => u.visivel);
        const opcoes = [item(`${Math.min(199, unidade.x + unidade.velocidade)} ${unidade.y}`, undefined, `avança ${unidade.velocidade} para a direita`)];
        if (alvo) {
          const distancia = Math.hypot(alvo.x - unidade.x, alvo.y - unidade.y) || 1;
          const passo = Math.min(unidade.velocidade, distancia);
          const x = Math.round(unidade.x + ((alvo.x - unidade.x) / distancia) * passo);
          const y = Math.round(unidade.y + ((alvo.y - unidade.y) / distancia) * passo);
          opcoes.unshift(item(`${x} ${y}`, undefined, `em direção a ${alvo.nome}`));
        }
        return opcoes;
      }
      return [];
    case "fire":
      if (argumentos.length === 0) return nomes(minhas.filter((u) => u.armas.length));
      if (argumentos.length === 1 && unidade) {
        return unidade.armas.map((a) => item(`${a.nome} `, a.nome, `${a.tipo} · dano ${a.dano} · alcance ${a.alcance} · munição ${a.municao}${a.recarga ? ` · recarga ${a.recarga}` : ""}`));
      }
      if (argumentos.length === 2) return nomes(inimigas);
      return [];
    case "attack":
      if (argumentos.length === 0) return nomes(minhas.filter((u) => u.armas.length));
      if (argumentos.length === 1) return nomes(inimigas);
      return [];
    case "dive":
      if (argumentos.length === 0) return nomes(minhas.filter((u) => u.tipo === "submarine"));
      if (argumentos.length === 1) return [item("30", undefined, "profundidade em metros")];
      return [];
    case "surface":
      return argumentos.length === 0 ? nomes(minhas.filter((u) => u.tipo === "submarine")) : [];
    case "sonar":
      return argumentos.length === 0
        ? minhas.map((u) => item(`${u.nome} `, u.nome, u.sonar_recarga ? `sonar em recarga: ${u.sonar_recarga} turno(s)` : `sonar pronto · ${u.sonar / 10} casas`))
        : [];
    case "if":
      if (argumentos.length === 0) return [...minhas, ...inimigas].map((u) => item(`${u.nome}.`, u.nome, descrever(u)));
      if (argumentos.length === 1) return [["<", "menor que"], [">", "maior que"], ["==", "igual a"]].map(([op, dica]) => item(`${op} `, op, dica));
      if (argumentos.length === 2) return [item("50 { ", "50 {", "número e abre o bloco")];
      return [];
    case "repeat":
      return argumentos.length === 0 ? [item("2 { ", "2 {", "repete 2 vezes")] : [];
    default:
      return [];
  }
}

/** Cria a função de sugestões do CodeMirror; `contexto()` informa a aba, o catálogo e as unidades do jogo. */
export function criarCompletar(contexto) {
  return function sugerir(cm) {
    const cursor = cm.getCursor();
    const linha = cm.getLine(cursor.line).slice(0, cursor.ch);
    if (/#/.test(linha)) return null;

    const palavra = linha.match(/[A-Za-z_]\w*$/)?.[0] ?? "";
    const antes = linha.slice(0, linha.length - palavra.length);
    const de = CodeMirror.Pos(cursor.line, cursor.ch - palavra.length);
    const { aba, catalogo, unidades } = contexto();
    if (!catalogo) return null;

    let lista;
    const acesso = antes.match(/([A-Za-z_]\w*)\.$/);
    if (acesso) {
      lista = ATRIBUTOS_CONSULTAVEIS.map(([nome, dica]) => item(`${nome} `, nome, dica));
    } else {
      const trecho = antes.slice(Math.max(antes.lastIndexOf("{"), antes.lastIndexOf("}")) + 1);
      const tokens = trecho.trim().split(/\s+/).filter(Boolean);
      const textoAntes = cm.getRange(CodeMirror.Pos(0, 0), de);
      lista = aba === "cenario" ? sugestoesDoCenario(tokens, textoAntes, catalogo) : sugestoesDoTurno(tokens, unidades);
    }

    const prefixo = palavra.toLowerCase();
    lista = lista.filter((sugestao) => sugestao.displayText.toLowerCase().startsWith(prefixo) && sugestao.text.trim() !== palavra);
    return lista.length ? { list: lista, from: de, to: cursor } : null;
  };
}
