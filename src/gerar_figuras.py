"""Gera as figuras da análise estatística para o artigo.

simbolica_por_genero.png — efeito da camada simbólica por gênero (análise
exploratória): média das diferenças ± DP entre as 5 sementes.

Figura para impressão (LaTeX): só modo claro, sem interação.
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BASE = Path(__file__).resolve().parents[1]   # raiz do pacote
ENTRADA = BASE / "results/analise_estatistica.json"
FIGS = BASE / "figs"
FIGS.mkdir(parents=True, exist_ok=True)

# Paleta para impressão: azul/vermelho como polos divergentes (ganho/custo),
# verificada para contraste e para distinção sob daltonismo.
AZUL = "#2a78d6"        # polo positivo (ganho)
VERMELHO = "#e34948"    # polo negativo (custo)
SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_SEC = "#52514e"
GRADE = "#dcdbd7"

plt.rcParams.update({
    "figure.facecolor": SUPERFICIE,
    "axes.facecolor": SUPERFICIE,
    "axes.edgecolor": GRADE,
    "axes.labelcolor": TINTA,
    "text.color": TINTA,
    "xtick.color": TINTA_SEC,
    "ytick.color": TINTA_SEC,
    "font.size": 10,
    "axes.grid": True,
    "grid.color": GRADE,
    "grid.linewidth": 0.8,
})


def cor(v):
    return AZUL if v >= 0 else VERMELHO


def fig_por_genero(dados):
    pg = dados["por_genero_exploratorio"]["simbolica_vs_mlp_puro"]
    itens = sorted(pg.items(), key=lambda kv: kv[1]["diferenca"]["media"])
    generos = [g for g, _ in itens]
    medias = np.array([v["diferenca"]["media"] for _, v in itens]) * 100
    dps = np.array([v["diferenca"]["desvio_padrao"] for _, v in itens]) * 100
    consistente = [v["sinal_consistente"] for _, v in itens]

    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    y = np.arange(len(generos))

    ax.barh(y, medias, height=0.62, color=[cor(m) for m in medias],
            edgecolor=SUPERFICIE, linewidth=2, zorder=2)
    ax.errorbar(medias, y, xerr=dps, fmt="none", ecolor=TINTA_SEC,
                elinewidth=1.5, capsize=4, alpha=0.85, zorder=3)
    ax.axvline(0, color=TINTA, linewidth=1.2, zorder=4)

    # Rótulo ancorado além da ponta da barra de erro, não da barra — senão colide.
    for yi, m, dp, c in zip(y, medias, dps, consistente):
        ponta = m + dp if m >= 0 else m - dp
        desloc = 10 if m >= 0 else -10
        ha = "left" if m >= 0 else "right"
        texto = f"{m:+.2f}" + ("  (sinal consistente nas 5 seeds)" if c else "")
        ax.annotate(texto, xy=(ponta, yi), xytext=(desloc, 0),
                    textcoords="offset points", va="center", ha=ha,
                    fontsize=9, color=TINTA if c else TINTA_SEC,
                    fontweight="bold" if c else "normal")

    ax.set_yticks(y)
    ax.set_yticklabels(generos, fontsize=10)
    ax.set_xlabel("Diferença de acurácia: MLP + simbólica − MLP puro (p.p.)")
    ax.set_title("Efeito da camada simbólica por gênero (média ± DP, 5 seeds)",
                 fontsize=11, fontweight="bold", pad=10)
    ax.grid(axis="y", visible=False)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    # Folga extra à esquerda acomoda o rótulo longo do Samba (a barra mais negativa).
    extremo = float(np.max(np.abs(medias) + dps))
    ax.set_xlim(-extremo * 3.1, extremo * 1.5)

    fig.tight_layout()
    destino = FIGS / "simbolica_por_genero.png"
    fig.savefig(destino, dpi=200, facecolor=SUPERFICIE)
    plt.close(fig)
    print(f"  {destino}")


def main():
    dados = json.loads(ENTRADA.read_text())
    print("Gerando figura:")
    fig_por_genero(dados)


if __name__ == "__main__":
    main()
