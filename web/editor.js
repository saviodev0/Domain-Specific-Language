const PROPRIEDADES = "hp|armor|speed|radar|depth|damage|range|ammo|cooldown";

CodeMirror.defineSimpleMode("tankscript", {
  start: [
    { regex: /#.*/, token: "comment" },
    { regex: /"(?:[^\\"]|\\.)*"?|'(?:[^\\']|\\.)*'?/, token: "string" },
    { regex: /(?:tank|submarine|gun|torpedo|team|battle|vs)\b/, token: "keyword" },
    { regex: /(?:move|attack|fire|dive|surface|sonar)\b/, token: "builtin" },
    { regex: /(?:if|repeat)\b/, token: "atom" },
    { regex: new RegExp(`(\\.)(${PROPRIEDADES}|x|y)\\b`), token: ["operator", "attribute"] },
    { regex: new RegExp(`(?:${PROPRIEDADES})\\b`), token: "attribute" },
    { regex: /[A-Za-z_]\w*/, token: "variable" },
    { regex: /\d+(?:\.\d+)?/, token: "number" },
    { regex: /==|<|>/, token: "operator" },
    { regex: /\{/, token: "bracket", indent: true },
    { regex: /\}/, token: "bracket", dedent: true },
  ],
  meta: { lineComment: "#", electricInput: /^\s*\}$/ },
});

export class Editor {
  constructor(elemento, aoExecutar, aoMudar, sugerir) {
    this.documentos = {
      cenario: CodeMirror.Doc("", "tankscript"),
      turno: CodeMirror.Doc("", "tankscript"),
    };
    this.atual = "cenario";
    this.cm = CodeMirror(elemento, {
      value: this.documentos.cenario,
      theme: "tank",
      lineNumbers: true,
      indentUnit: 4,
      tabSize: 4,
      gutters: ["erros", "CodeMirror-linenumbers"],
      hintOptions: { hint: sugerir, completeSingle: false },
      extraKeys: {
        "Ctrl-Space": "autocomplete",
        "Ctrl-Enter": () => aoExecutar(),
        "Cmd-Enter": () => aoExecutar(),
        Tab: (cm) => cm.execCommand(cm.somethingSelected() ? "indentMore" : "insertSoftTab"),
      },
    });
    this.marcas = [];
    this.linhaExecutando = null;
    const sugerirDepois = () => setTimeout(() => {
      if (!this.cm.state.completionActive && !this.cm.getOption("readOnly")) this.cm.showHint();
    }, 0);
    this.cm.on("inputRead", (_cm, mudanca) => {
      if (/[\w. ]$/.test(mudanca.text.at(-1))) sugerirDepois();
    });
    this.cm.on("change", (_cm, mudanca) => {
      if (mudanca.origin === "complete" && /[ .]$/.test(mudanca.text.at(-1))) sugerirDepois();
    });
    this.cm.on("changes", () => {
      this.limparErros();
      aoMudar?.(this.atual, this.cm.getValue());
    });
  }

  mostrar(nome) {
    if (this.atual === nome) return;
    this.limparErros();
    this.destacar(null);
    this.cm.swapDoc(this.documentos[nome]);
    this.atual = nome;
    this.cm.focus();
  }

  texto(nome) {
    return this.documentos[nome].getValue();
  }

  definir(nome, texto) {
    this.documentos[nome].setValue(texto);
  }

  inserir(texto) {
    this.cm.replaceSelection(texto);
    this.cm.focus();
  }

  irPara(linha) {
    const posicao = { line: linha - 1, ch: 0 };
    this.cm.setCursor(posicao);
    this.cm.scrollIntoView(posicao, 80);
    this.cm.focus();
  }

  somenteLeitura(ativo) {
    this.cm.setOption("readOnly", ativo);
    this.cm.getWrapperElement().classList.toggle("executando", ativo);
  }

  marcarErros(erros) {
    this.limparErros();
    for (const erro of erros) {
      if (!erro.linha) continue;
      const linha = Math.min(erro.linha - 1, this.cm.lineCount() - 1);
      const texto = this.cm.getLine(linha);
      let inicio = Math.max(0, Math.min((erro.coluna || 1) - 1, texto.length));
      let fim = inicio + (texto.slice(inicio).match(/^\S+/)?.[0].length || 1);
      if (inicio === texto.length && inicio > 0) inicio -= 1;
      this.marcas.push(this.cm.markText({ line: linha, ch: inicio }, { line: linha, ch: fim }, { className: "erro-trecho" }));
      this.cm.addLineClass(linha, "background", "linha-erro");
      const marcador = document.createElement("span");
      marcador.className = "marcador-erro";
      marcador.textContent = "●";
      marcador.title = erro.mensagem;
      this.cm.setGutterMarker(linha, "erros", marcador);
    }
  }

  limparErros() {
    for (const marca of this.marcas) marca.clear();
    this.marcas = [];
    this.cm.clearGutter("erros");
    for (let linha = 0; linha < this.cm.lineCount(); linha += 1) {
      this.cm.removeLineClass(linha, "background", "linha-erro");
    }
  }

  destacar(linha) {
    if (this.linhaExecutando !== null) {
      this.cm.removeLineClass(this.linhaExecutando, "background", "linha-executando");
      this.linhaExecutando = null;
    }
    if (!linha) return;
    this.linhaExecutando = linha - 1;
    this.cm.addLineClass(this.linhaExecutando, "background", "linha-executando");
    this.cm.scrollIntoView({ line: this.linhaExecutando, ch: 0 }, 60);
  }
}
