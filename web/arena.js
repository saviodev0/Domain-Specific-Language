const CELULA = 56;
const MARGEM = 26;

const CORES = {
  jogador: 0x1d4ed8,
  inimigo: 0xdc2626,
  neutro: 0x6b7280,
  destruido: 0x9ca3af,
};

export const TERRENOS = {
  ".": "Terreno aberto",
  I: "Ilha: bloqueia o movimento",
  "#": "Ruínas: o alvo aqui recebe 50% do dano",
  "~": "Água rasa: submarinos não submergem",
};

const ALERTAS = [
  ["[RECARREGANDO]", "recarregando"],
  ["[SEM MUNIÇÃO]", "sem munição"],
  ["[FIRE ERROU]", "fora de alcance"],
  ["[FIRE FALHOU]", "falhou"],
  ["[FIRE INEFICAZ]", "ineficaz: alvo submerso"],
];

function escurecer(cor, quanto = 30) {
  return Phaser.Display.Color.IntegerToColor(cor).darken(quanto).color;
}

function porNome(estado) {
  return new Map((estado?.unidades || []).map((unidade) => [unidade.nome, unidade]));
}

export class Arena {
  constructor(elemento, callbacks = {}) {
    this.pronta = new Promise((resolve) => {
      const cena = new CenaArena(resolve, callbacks);
      this.jogo = new Phaser.Game({
        type: Phaser.AUTO,
        parent: elemento,
        backgroundColor: "#f4f1ea",
        antialias: true,
        scale: {
          mode: Phaser.Scale.FIT,
          autoCenter: Phaser.Scale.CENTER_BOTH,
          width: MARGEM + 20 * CELULA + 4,
          height: MARGEM + 10 * CELULA + 4,
        },
        scene: cena,
      });
    });
  }
}

class CenaArena extends Phaser.Scene {
  constructor(aoCriar, callbacks) {
    super({ key: "arena" });
    this.aoCriar = aoCriar;
    this.callbacks = callbacks;
    this.velocidade = 1;
    this.visuais = new Map();
    this.mapa = { largura: 20, altura: 10, terreno: Array(10).fill(".".repeat(20)) };
  }

  create() {
    const faisca = this.make.graphics({ x: 0, y: 0, add: false });
    faisca.fillStyle(0xffffff).fillCircle(4, 4, 4).generateTexture("faisca", 8, 8).destroy();

    this.terreno = this.add.graphics();
    this.rotulos = this.add.group();
    this.nevoa = this.add.graphics().setDepth(5);
    this.cursor = this.add.rectangle(0, 0, CELULA, CELULA).setOrigin(0).setStrokeStyle(2, 0x2563eb, 0.9)
      .setFillStyle(0x2563eb, 0.08).setDepth(6).setVisible(false);

    this.input.on("pointermove", (ponteiro) => this.aoMoverPonteiro(ponteiro));
    this.input.on("pointerdown", (ponteiro) => {
      const celula = this.celulaEm(ponteiro);
      if (celula) this.callbacks.aoClicarCelula?.(celula);
    });
    this.input.on("gameout", () => {
      this.cursor.setVisible(false);
      this.callbacks.aoSairDoMapa?.();
    });

    this.montarMapa(this.mapa);
    this.aoCriar(this);
  }

  duracao(ms) {
    return ms / this.velocidade;
  }

  tween(configuracao) {
    return new Promise((resolve) => {
      this.tweens.add({ ...configuracao, duration: this.duracao(configuracao.duration ?? 300), onComplete: resolve });
    });
  }

  esperar(ms) {
    return new Promise((resolve) => this.time.delayedCall(this.duracao(ms), resolve));
  }

  celula(x, y) {
    return [
      Phaser.Math.Clamp(Math.floor(x / 10), 0, this.mapa.largura - 1),
      Phaser.Math.Clamp(Math.floor(y / 10), 0, this.mapa.altura - 1),
    ];
  }

  centro(gx, gy) {
    return { x: MARGEM + gx * CELULA + CELULA / 2, y: MARGEM + gy * CELULA + CELULA / 2 };
  }

  celulaEm(ponteiro) {
    const gx = Math.floor((ponteiro.worldX - MARGEM) / CELULA);
    const gy = Math.floor((ponteiro.worldY - MARGEM) / CELULA);
    if (gx < 0 || gy < 0 || gx >= this.mapa.largura || gy >= this.mapa.altura) return null;
    return { gx, gy, x: gx * 10, y: gy * 10, terreno: this.mapa.terreno[gy][gx] };
  }

  aoMoverPonteiro(ponteiro) {
    const celula = this.celulaEm(ponteiro);
    if (!celula) {
      this.cursor.setVisible(false);
      this.callbacks.aoSairDoMapa?.();
      return;
    }
    this.cursor.setPosition(MARGEM + celula.gx * CELULA, MARGEM + celula.gy * CELULA).setVisible(true);
    this.callbacks.aoPassarNaCelula?.(celula);
  }

  montarMapa(mapa) {
    this.mapa = mapa;
    const largura = MARGEM + mapa.largura * CELULA + 4;
    const altura = MARGEM + mapa.altura * CELULA + 4;
    if (this.scale.width !== largura || this.scale.height !== altura) this.scale.resize(largura, altura);

    for (const visual of this.visuais.values()) visual.container.destroy();
    this.visuais.clear();
    this.nevoa.clear();
    this.rotulos.clear(true, true);

    const g = this.terreno.clear();
    for (let gy = 0; gy < mapa.altura; gy += 1) {
      for (let gx = 0; gx < mapa.largura; gx += 1) {
        this.desenharCelula(g, gx, gy, mapa.terreno[gy][gx]);
      }
    }
    g.lineStyle(1, 0xcfc8b6, 1);
    for (let gx = 0; gx <= mapa.largura; gx += 1) {
      g.lineBetween(MARGEM + gx * CELULA, MARGEM, MARGEM + gx * CELULA, MARGEM + mapa.altura * CELULA);
    }
    for (let gy = 0; gy <= mapa.altura; gy += 1) {
      g.lineBetween(MARGEM, MARGEM + gy * CELULA, MARGEM + mapa.largura * CELULA, MARGEM + gy * CELULA);
    }
    g.lineStyle(2, 0x8a8475, 1).strokeRect(MARGEM, MARGEM, mapa.largura * CELULA, mapa.altura * CELULA);

    const estilo = { fontFamily: "JetBrains Mono, monospace", fontSize: "11px", color: "#8a8475" };
    for (let gx = 0; gx < mapa.largura; gx += 1) {
      this.rotulos.add(this.add.text(MARGEM + gx * CELULA + CELULA / 2, MARGEM / 2, String(gx * 10), estilo).setOrigin(0.5));
    }
    for (let gy = 0; gy < mapa.altura; gy += 1) {
      this.rotulos.add(this.add.text(MARGEM / 2, MARGEM + gy * CELULA + CELULA / 2, String(gy * 10), estilo).setOrigin(0.5));
    }
  }

  desenharCelula(g, gx, gy, tipo) {
    const x = MARGEM + gx * CELULA;
    const y = MARGEM + gy * CELULA;
    const c = { x: x + CELULA / 2, y: y + CELULA / 2 };
    g.fillStyle((gx + gy) % 2 ? 0xe6e1d3 : 0xebe7db).fillRect(x, y, CELULA, CELULA);

    if (tipo === "~") {
      g.fillStyle(0x9cc7d9).fillRect(x, y, CELULA, CELULA);
      g.lineStyle(2, 0x5b9db8, 0.7);
      for (const deslocamento of [-14, 0, 14]) {
        const pontos = [];
        for (let i = 0; i <= 8; i += 1) {
          pontos.push(new Phaser.Math.Vector2(x + 8 + i * 5, c.y + deslocamento + Math.sin(i * 1.2 + gx) * 2.5));
        }
        g.strokePoints(pontos);
      }
    } else if (tipo === "I") {
      g.fillStyle(0xd9c48f).fillCircle(c.x, c.y, CELULA * 0.42);
      g.fillStyle(0x6a994e).fillCircle(c.x - 3, c.y - 2, CELULA * 0.32);
      g.fillStyle(0x386641);
      for (const [dx, dy] of [[-8, -8], [6, -4], [-2, 7], [9, 8]]) g.fillCircle(c.x + dx, c.y + dy, 4);
    } else if (tipo === "#") {
      const blocos = [[-18, -14, 14, 10], [2, -16, 16, 12], [-14, 2, 12, 14], [6, 4, 14, 9], [-4, -4, 8, 7]];
      for (const [indice, [dx, dy, w, h]] of blocos.entries()) {
        g.fillStyle(indice % 2 ? 0x6b7280 : 0x8b8f99).fillRect(c.x + dx, c.y + dy, w, h);
      }
      g.lineStyle(1, 0x4b5563, 1).strokeRect(c.x - 18, c.y - 14, 14, 10);
    }
  }

  posicoes(estado) {
    const ocupacao = new Map();
    const posicoes = new Map();
    const deslocamentos = [[0, 0], [-11, -9], [11, 9], [11, -9], [-11, 9]];
    for (const unidade of estado.unidades) {
      const [gx, gy] = this.celula(unidade.x, unidade.y);
      const chave = `${gx},${gy}`;
      const indice = ocupacao.get(chave) || 0;
      ocupacao.set(chave, indice + 1);
      const [dx, dy] = deslocamentos[indice % deslocamentos.length];
      const centro = this.centro(gx, gy);
      posicoes.set(unidade.nome, { x: centro.x + dx, y: centro.y + dy });
    }
    return posicoes;
  }

  visual(unidade) {
    let visual = this.visuais.get(unidade.nome);
    if (visual) return visual;

    const container = this.add.container(0, 0).setDepth(10);
    const anel = this.add.graphics();
    const sombra = this.add.graphics();
    const corpo = this.add.graphics();
    const torre = this.add.graphics();
    const barra = this.add.graphics();
    const rotulo = this.add.text(0, 20, unidade.nome, {
      fontFamily: "JetBrains Mono, monospace",
      fontSize: "11px",
      fontStyle: "600",
      color: "#1f2328",
      stroke: "#f4f1ea",
      strokeThickness: 3,
    }).setOrigin(0.5, 0);
    container.add([anel, sombra, corpo, torre, barra, rotulo]);
    visual = { container, anel, sombra, corpo, torre, barra, rotulo, unidade: null, aparencia: "" };
    this.visuais.set(unidade.nome, visual);
    return visual;
  }

  desenharUnidade(visual, unidade) {
    const cor = unidade.vivo ? CORES[unidade.lado] : CORES.destruido;
    const escura = escurecer(cor, 35);
    const { corpo, torre, sombra } = visual;
    corpo.clear();
    torre.clear();
    sombra.clear();

    if (unidade.tipo === "aircraft") {
      if (unidade.vivo) sombra.fillStyle(0x000000, 0.35).fillEllipse(6, 14, 30, 9);
      corpo.fillStyle(escura).fillPoints([
        { x: 3, y: 0 }, { x: -7, y: -19 }, { x: -12, y: -19 }, { x: -6, y: 0 }, { x: -12, y: 19 }, { x: -7, y: 19 },
      ], true);
      corpo.fillStyle(escura).fillTriangle(-14, 0, -20, -8, -20, 8);
      corpo.fillStyle(cor).fillEllipse(0, 0, 34, 8);
      corpo.fillStyle(0xe8f6ff, 0.9).fillEllipse(9, 0, 7, 4);
    } else if (unidade.tipo === "tank") {
      corpo.fillStyle(0x374151).fillRoundedRect(-17, -15, 34, 8, 3).fillRoundedRect(-17, 7, 34, 8, 3);
      corpo.fillStyle(cor).fillRoundedRect(-14, -10, 28, 20, 5);
      corpo.lineStyle(2, escura, 1).strokeRoundedRect(-14, -10, 28, 20, 5);
      torre.fillStyle(escura).fillRect(0, -2.5, 20, 5);
      torre.fillStyle(escura).fillCircle(0, 0, 7.5);
      torre.lineStyle(2, cor, 1).strokeCircle(0, 0, 7.5);
    } else {
      corpo.fillStyle(escura).fillRect(-24, -4, 5, 8);
      corpo.fillStyle(cor).fillEllipse(0, 0, 42, 16);
      corpo.lineStyle(2, escura, 1).strokeEllipse(0, 0, 42, 16);
      corpo.fillStyle(escura).fillRoundedRect(-4, -13, 11, 9, 3);
      corpo.lineStyle(2, escura, 1).lineBetween(3, -13, 3, -18);
    }
    if (!unidade.vivo) {
      corpo.lineStyle(3, 0x374151, 0.9).lineBetween(-12, -12, 12, 12).lineBetween(12, -12, -12, 12);
    }
  }

  desenharStatus(visual, unidade) {
    const { barra, anel } = visual;
    barra.clear();
    anel.clear();
    if (!unidade.vivo) return;

    const proporcao = unidade.hp_max ? Phaser.Math.Clamp(unidade.hp / unidade.hp_max, 0, 1) : 0;
    const cor = proporcao > 0.6 ? 0x16a34a : proporcao > 0.3 ? 0xd97706 : 0xdc2626;
    barra.fillStyle(0x374151, 0.9).fillRoundedRect(-19, -28, 38, 6, 2);
    barra.fillStyle(cor).fillRoundedRect(-18, -27, 36 * proporcao, 4, 2);

    if (unidade.exposto) {
      anel.lineStyle(2, 0xdc2626, 0.95).strokeCircle(0, 0, 25);
    } else if (unidade.detectado && unidade.lado !== "jogador") {
      anel.lineStyle(2, 0xd97706, 0.9);
      for (let i = 0; i < 12; i += 1) {
        const angulo = (i / 12) * Math.PI * 2;
        anel.beginPath().arc(0, 0, 25, angulo, angulo + 0.3).strokePath();
      }
    }
    if (unidade.profundidade > 0) {
      anel.lineStyle(1.5, 0x2563eb, 0.6).strokeEllipse(0, 4, 50, 14);
    }
  }

  aplicarEstado(estado, { instantaneo = false } = {}) {
    const posicoes = this.posicoes(estado);
    const visiveis = new Set(estado.visiveis.map(([x, y]) => `${x},${y}`));

    for (const unidade of estado.unidades) {
      const visual = this.visual(unidade);
      const aparencia = `${unidade.lado}|${unidade.vivo}`;
      if (visual.aparencia !== aparencia) {
        this.desenharUnidade(visual, unidade);
        visual.aparencia = aparencia;
      }
      this.desenharStatus(visual, unidade);

      const [gx, gy] = this.celula(unidade.x, unidade.y);
      const mostrar = unidade.vivo ? unidade.visivel : unidade.lado === "jogador" || visiveis.has(`${gx},${gy}`);
      const posicao = posicoes.get(unidade.nome);
      if (instantaneo || !visual.container.visible || !this.tweens.isTweening(visual.container)) {
        visual.container.setPosition(posicao.x, posicao.y);
      }
      visual.container.setVisible(mostrar);
      visual.corpo.setAlpha(unidade.profundidade > 0 ? 0.45 : 1);
      visual.torre.setAlpha(unidade.profundidade > 0 ? 0.45 : 1);
      visual.unidade = unidade;
    }

    this.nevoa.clear().fillStyle(0x57534e, 0.5);
    for (let gy = 0; gy < this.mapa.altura; gy += 1) {
      for (let gx = 0; gx < this.mapa.largura; gx += 1) {
        if (!visiveis.has(`${gx},${gy}`)) this.nevoa.fillRect(MARGEM + gx * CELULA, MARGEM + gy * CELULA, CELULA, CELULA);
      }
    }
  }

  async animarEvento(evento, anterior) {
    const antes = porNome(anterior);
    const depois = porNome(evento.estado);
    const dados = evento.instrucao || {};

    switch (evento.tipo) {
      case "InicioDoTurno":
        return this.faixa(`TURNO ${evento.turno}`);
      case "MoveStatement":
        return this.animarMovimento(dados.unit, antes, depois, evento);
      case "FireStatement":
      case "AttackStatement":
        return this.animarDisparo(dados.attacker, dados.weapon, dados.target, antes, depois, evento);
      case "DiveStatement":
      case "SurfaceStatement":
        return this.animarMergulho(dados.unit, antes, depois);
      case "SonarStatement":
        return this.animarSonar(dados.unit, antes);
      default:
        return this.esperar(120);
    }
  }

  async animarMovimento(nome, antes, depois, evento) {
    const visual = this.visuais.get(nome);
    const anterior = antes.get(nome);
    const atual = depois.get(nome);
    if (!visual || !anterior || !atual || !(anterior.visivel || atual.visivel)) return;

    if (evento.mensagens.some((mensagem) => mensagem.includes("[COLISÃO]"))) {
      const destino = this.centro(...this.celula(evento.instrucao.x, evento.instrucao.y));
      this.texto(destino.x, destino.y, "bloqueado", "#b45309");
      await this.tween({ targets: visual.container, x: visual.container.x + 4, yoyo: true, repeat: 2, duration: 50 });
      return;
    }

    const destino = this.posicoes(evento.estado).get(nome);
    const distancia = Phaser.Math.Distance.Between(visual.container.x, visual.container.y, destino.x, destino.y);
    if (distancia < 1) return this.esperar(80);

    visual.container.setVisible(true);
    if (atual.tipo === "tank" || atual.tipo === "aircraft") {
      const angulo = Phaser.Math.Angle.Between(visual.container.x, visual.container.y, destino.x, destino.y);
      visual.corpo.setRotation(angulo);
      visual.torre.setRotation(angulo);
    } else {
      visual.corpo.setScale(destino.x < visual.container.x ? -1 : 1, 1);
    }
    await this.tween({
      targets: visual.container,
      x: destino.x,
      y: destino.y,
      ease: "Sine.easeInOut",
      duration: Phaser.Math.Clamp(distancia * 1.6, 260, 900),
    });
  }

  async animarDisparo(atacante, nomeArma, alvo, antes, depois, evento) {
    const origem = this.visuais.get(atacante);
    const destino = this.visuais.get(alvo);
    const unidadeAtacante = antes.get(atacante);
    if (!origem || !destino || !unidadeAtacante) return;

    const alerta = ALERTAS.find(([marca]) => evento.mensagens.some((mensagem) => mensagem.includes(marca)));
    const visivelAtacante = antes.get(atacante)?.visivel;
    if (alerta && alerta[0] !== "[FIRE INEFICAZ]") {
      if (visivelAtacante) this.texto(origem.container.x, origem.container.y - 30, alerta[1], "#b45309");
      return this.esperar(250);
    }

    const arma = unidadeAtacante.armas.find((item) => item.nome === nomeArma) || unidadeAtacante.armas[0];
    const torpedo = arma?.tipo === "torpedo";
    const missil = arma?.tipo === "missile";
    const de = { x: origem.container.x, y: origem.container.y };
    const para = { x: destino.container.x, y: destino.container.y };
    const angulo = Phaser.Math.Angle.Between(de.x, de.y, para.x, para.y);

    if (visivelAtacante) {
      if (unidadeAtacante.tipo === "tank") {
        await this.tween({ targets: origem.torre, rotation: angulo, duration: 160 });
      } else if (unidadeAtacante.tipo === "aircraft") {
        await this.tween({ targets: origem.corpo, rotation: angulo, duration: 160 });
      }
      const clarao = this.add.circle(de.x + Math.cos(angulo) * 20, de.y + Math.sin(angulo) * 20, 7, 0xffe08a).setDepth(20);
      this.tween({ targets: clarao, scale: 2.2, alpha: 0, duration: 180 }).then(() => clarao.destroy());

      const projetil = torpedo
        ? this.add.rectangle(de.x, de.y, 14, 4, 0x0e7490).setRotation(angulo)
        : missil
          ? this.add.rectangle(de.x, de.y, 12, 3, 0x374151).setRotation(angulo)
          : this.add.circle(de.x, de.y, 4, 0xd97706);
      projetil.setDepth(20);
      const rastro = this.add.particles(0, 0, "faisca", {
        follow: projetil,
        lifespan: torpedo ? 500 : missil ? 420 : 220,
        scale: { start: torpedo || missil ? 0.7 : 0.5, end: 0 },
        alpha: { start: 0.6, end: 0 },
        tint: torpedo ? 0x0e7490 : missil ? [0xff8c42, 0x9ca3af] : 0xd97706,
        frequency: 18,
        blendMode: "NORMAL",
      }).setDepth(19);
      const distancia = Phaser.Math.Distance.Between(de.x, de.y, para.x, para.y);
      await this.tween({
        targets: projetil,
        x: para.x,
        y: para.y,
        ease: torpedo || missil ? "Sine.easeIn" : "Linear",
        duration: Phaser.Math.Clamp(distancia * (torpedo ? 1.4 : 0.7), 180, 900),
      });
      projetil.destroy();
      rastro.stop();
      this.time.delayedCall(600, () => rastro.destroy());
    } else if (destino.container.visible) {
      this.texto(para.x, para.y - 34, "ataque oculto!", "#dc2626");
      await this.esperar(250);
    }

    const hpAntes = antes.get(alvo)?.hp ?? 0;
    const hpDepois = depois.get(alvo)?.hp ?? 0;
    if (hpDepois < hpAntes) {
      const destruido = hpDepois === 0;
      this.explosao(para.x, para.y, destruido ? 60 : 26);
      this.cameras.main.shake(this.duracao(destruido ? 320 : 140), destruido ? 0.012 : 0.005);
      this.texto(para.x, para.y - 30, `-${hpAntes - hpDepois}`, "#dc2626", 18);
      if (destruido) this.texto(para.x, para.y + 26, "destruído", "#dc2626");
      await this.esperar(destruido ? 420 : 260);
    } else {
      const respingo = this.add.circle(para.x, para.y, 6, 0x0e7490, 0.6).setDepth(20);
      this.tween({ targets: respingo, scale: 4, alpha: 0, duration: 380 }).then(() => respingo.destroy());
      if (alerta) this.texto(para.x, para.y - 30, alerta[1], "#0e7490");
      await this.esperar(260);
    }
  }

  async animarMergulho(nome, antes, depois) {
    const visual = this.visuais.get(nome);
    const anterior = antes.get(nome);
    const atual = depois.get(nome);
    if (!visual || !anterior || !atual || anterior.profundidade === atual.profundidade) return this.esperar(120);
    if (!(anterior.visivel || atual.visivel)) return;

    const { x, y } = visual.container;
    for (const atraso of [0, 140]) {
      const onda = this.add.ellipse(x, y + 4, 36, 12).setStrokeStyle(2, 0x2563eb, 0.8).setDepth(9);
      this.time.delayedCall(this.duracao(atraso), () => {
        this.tween({ targets: onda, scaleX: 2.2, scaleY: 2.2, alpha: 0, duration: 520 }).then(() => onda.destroy());
      });
    }
    const alvo = atual.profundidade > 0 ? 0.45 : 1;
    await this.tween({ targets: [visual.corpo, visual.torre], alpha: alvo, duration: 420 });
  }

  async animarSonar(nome, antes) {
    const visual = this.visuais.get(nome);
    const unidade = antes.get(nome);
    if (!visual || !unidade || !unidade.vivo) return;
    const raio = (unidade.sonar / 10 + 0.5) * CELULA;
    const { x, y } = visual.container;
    for (const atraso of [0, 220]) {
      const onda = this.add.circle(x, y, raio).setStrokeStyle(3, 0x2563eb, 0.9).setScale(0.05).setDepth(8);
      this.time.delayedCall(this.duracao(atraso), () => {
        this.tween({ targets: onda, scale: 1, alpha: 0.05, duration: 900, ease: "Cubic.easeOut" }).then(() => onda.destroy());
      });
    }
    await this.esperar(700);
  }

  explosao(x, y, quantidade) {
    const emissor = this.add.particles(x, y, "faisca", {
      speed: { min: 40, max: 60 + quantidade * 4 },
      angle: { min: 0, max: 360 },
      lifespan: { min: 250, max: 650 },
      scale: { start: 1.6, end: 0 },
      tint: [0xffe08a, 0xff8c42, 0xdc2626],
      blendMode: "NORMAL",
      emitting: false,
    }).setDepth(21);
    emissor.explode(quantidade);
    const clarao = this.add.circle(x, y, 10, 0xd97706, 0.9).setDepth(20);
    this.tween({ targets: clarao, scale: 3.5, alpha: 0, duration: 300 }).then(() => clarao.destroy());
    this.time.delayedCall(900, () => emissor.destroy());
  }

  texto(x, y, conteudo, cor, tamanho = 13) {
    const texto = this.add.text(x, y, conteudo, {
      fontFamily: "Chakra Petch, sans-serif",
      fontSize: `${tamanho}px`,
      fontStyle: "700",
      color: cor,
      stroke: "#f4f1ea",
      strokeThickness: 4,
    }).setOrigin(0.5).setDepth(30);
    this.tween({ targets: texto, y: y - 26, alpha: 0, duration: 1100, ease: "Cubic.easeIn" }).then(() => texto.destroy());
  }

  async faixa(conteudo) {
    const { width, height } = this.scale;
    const fundo = this.add.rectangle(width / 2, height / 2, width, 64, 0xffffff, 0.85).setDepth(40).setAlpha(0);
    const texto = this.add.text(width / 2, height / 2, conteudo, {
      fontFamily: "Chakra Petch, sans-serif",
      fontSize: "34px",
      fontStyle: "700",
      color: "#2563eb",
    }).setOrigin(0.5).setDepth(41).setAlpha(0).setScale(1.3);
    await this.tween({ targets: [fundo, texto], alpha: 1, scale: 1, duration: 260, ease: "Back.easeOut" });
    await this.esperar(380);
    await this.tween({ targets: [fundo, texto], alpha: 0, duration: 240 });
    fundo.destroy();
    texto.destroy();
  }
}

