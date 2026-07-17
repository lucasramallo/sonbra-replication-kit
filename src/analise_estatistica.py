"""Análise estatística dos resultados das repetições (5 seeds).

Duas comparações pareadas por seed:
  (A) com leakage        vs. (B) sem leakage        -> efeito do protocolo de split
  (B) sem leakage puro   vs. (C) sem leakage + simbólica -> efeito da camada simbólica

Para cada uma: média, desvio-padrão, IC 95% (t, n=5), Shapiro-Wilk sobre as
diferenças, t pareado e Wilcoxon. Análise por gênero é exploratória (sem teste
formal): n=5 por gênero em 8 gêneros não sustenta inferência.

Saída: results/analise_estatistica.json + relatório em stdout.
"""

import json
from pathlib import Path

import numpy as np
from scipy import stats

BASE = Path(__file__).resolve().parents[1]   # raiz do pacote
ENTRADA = BASE / "results/resultados_repeticoes.json"
SAIDA = BASE / "results/analise_estatistica.json"

CENARIOS = {
    "com_leakage": "Com leakage",
    "sem_leakage_mlp_puro": "Sem leakage (MLP puro)",
    "sem_leakage_mlp_simbolico": "Sem leakage + camada simbólica",
}
ALFA = 0.05


def descritiva(x):
    """Média, DP amostral (ddof=1) e IC 95% pela t de Student."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    media = float(np.mean(x))
    dp = float(np.std(x, ddof=1))
    erro_padrao = dp / np.sqrt(n)
    t_crit = float(stats.t.ppf(1 - ALFA / 2, df=n - 1))
    margem = t_crit * erro_padrao
    return {
        "n": n,
        "media": media,
        "desvio_padrao": dp,
        "erro_padrao": erro_padrao,
        "ic95_inf": media - margem,
        "ic95_sup": media + margem,
        "valores": [float(v) for v in x],
    }


def cohen_d_pareado(dif):
    """Cohen's d para amostras pareadas: média das diferenças / DP das diferenças."""
    dif = np.asarray(dif, dtype=float)
    dp = float(np.std(dif, ddof=1))
    return float(np.mean(dif) / dp) if dp > 0 else float("nan")


def comparacao_pareada(nome, rotulo_a, x_a, rotulo_b, x_b):
    """Compara dois cenários pareados por seed. Diferença = A - B."""
    x_a = np.asarray(x_a, dtype=float)
    x_b = np.asarray(x_b, dtype=float)
    dif = x_a - x_b

    shapiro_stat, shapiro_p = stats.shapiro(dif)
    normal_ok = shapiro_p > ALFA

    t_stat, t_p = stats.ttest_rel(x_a, x_b)
    # Wilcoxon com n=5: o menor p bilateral possível é 0.0625, nunca < 0.05.
    w_stat, w_p = stats.wilcoxon(x_a, x_b)

    return {
        "nome": nome,
        "grupo_a": {"rotulo": rotulo_a, **descritiva(x_a)},
        "grupo_b": {"rotulo": rotulo_b, **descritiva(x_b)},
        "diferenca": descritiva(dif),
        "shapiro_wilk": {
            "estatistica": float(shapiro_stat),
            "p_valor": float(shapiro_p),
            "normalidade_rejeitada": not normal_ok,
        },
        "t_pareado": {
            "estatistica": float(t_stat),
            "p_valor": float(t_p),
            "gl": len(dif) - 1,
            "significativo": bool(t_p < ALFA),
        },
        "wilcoxon": {
            "estatistica": float(w_stat),
            "p_valor": float(w_p),
            "significativo": bool(w_p < ALFA),
            "nota": "n=5: p mínimo bilateral = 0.0625; o teste não pode atingir alfa=0.05",
        },
        "cohen_d": cohen_d_pareado(dif),
        "teste_primario": "t_pareado" if normal_ok else "wilcoxon",
    }


def por_genero(execucoes, chave_a, chave_b):
    """Diferença média por gênero entre dois cenários (exploratório, sem teste)."""
    generos = sorted(execucoes[0][chave_a]["acuracia_por_genero"].keys())
    saida = {}
    for g in generos:
        a = [e[chave_a]["acuracia_por_genero"][g] for e in execucoes]
        b = [e[chave_b]["acuracia_por_genero"][g] for e in execucoes]
        dif = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
        saida[g] = {
            "grupo_a": descritiva(a),
            "grupo_b": descritiva(b),
            "diferenca": descritiva(dif),
            "sinal_consistente": bool(np.all(dif > 0) or np.all(dif < 0)),
        }
    return saida


def pct(v):
    return f"{100 * v:.2f}"


def main():
    dados = json.loads(ENTRADA.read_text())
    execucoes = dados["execucoes"]
    seeds = [e["seed"] for e in execucoes]

    acc = {k: [e[k]["acc_teste"] for e in execucoes] for k in CENARIOS}

    comp_leakage = comparacao_pareada(
        "Efeito do protocolo de split (leakage)",
        CENARIOS["com_leakage"], acc["com_leakage"],
        CENARIOS["sem_leakage_mlp_puro"], acc["sem_leakage_mlp_puro"],
    )
    comp_simbolica = comparacao_pareada(
        "Efeito da camada simbólica",
        CENARIOS["sem_leakage_mlp_simbolico"], acc["sem_leakage_mlp_simbolico"],
        CENARIOS["sem_leakage_mlp_puro"], acc["sem_leakage_mlp_puro"],
    )

    resultado = {
        "seeds": seeds,
        "alfa": ALFA,
        "descritiva_por_cenario": {
            k: {"rotulo": r, **descritiva(acc[k])} for k, r in CENARIOS.items()
        },
        "comparacoes": {
            "leakage_vs_sem_leakage": comp_leakage,
            "simbolica_vs_mlp_puro": comp_simbolica,
        },
        "por_genero_exploratorio": {
            "leakage_vs_sem_leakage": por_genero(
                execucoes, "com_leakage", "sem_leakage_mlp_puro"
            ),
            "simbolica_vs_mlp_puro": por_genero(
                execucoes, "sem_leakage_mlp_simbolico", "sem_leakage_mlp_puro"
            ),
        },
        "taxa_intervencao": descritiva(
            [e["sem_leakage_mlp_simbolico"]["taxa_intervencao"] for e in execucoes]
        ),
        "overlap_musicas_pct": descritiva(
            [e["com_leakage"]["overlap_musicas_pct"] for e in execucoes]
        ),
    }

    SAIDA.write_text(json.dumps(resultado, indent=2, ensure_ascii=False))

    # ---- relatório em texto ----
    print("=" * 78)
    print(f"ANÁLISE ESTATÍSTICA — {len(seeds)} repetições (seeds {seeds})")
    print("=" * 78)

    print("\n## Descritiva por cenário (acurácia de teste, %)\n")
    print(f"{'Cenário':<34} {'Média':>7} {'DP':>7} {'IC 95%':>18}")
    for k, r in CENARIOS.items():
        d = resultado["descritiva_por_cenario"][k]
        ic = f"[{pct(d['ic95_inf'])}, {pct(d['ic95_sup'])}]"
        print(f"{r:<34} {pct(d['media']):>7} {pct(d['desvio_padrao']):>7} {ic:>18}")

    for comp in (comp_leakage, comp_simbolica):
        print(f"\n{'-' * 78}\n## {comp['nome']}\n")
        print(f"  A = {comp['grupo_a']['rotulo']}")
        print(f"  B = {comp['grupo_b']['rotulo']}")
        d = comp["diferenca"]
        print(f"\n  Diferença (A - B), em p.p.:")
        print(f"    por seed : {[round(100 * v, 2) for v in d['valores']]}")
        print(f"    média    : {pct(d['media'])} p.p.")
        print(f"    DP       : {pct(d['desvio_padrao'])} p.p.")
        print(f"    IC 95%   : [{pct(d['ic95_inf'])}, {pct(d['ic95_sup'])}] p.p.")
        sw = comp["shapiro_wilk"]
        print(f"\n  Shapiro-Wilk (diferenças): W={sw['estatistica']:.4f}, "
              f"p={sw['p_valor']:.4f} -> normalidade "
              f"{'REJEITADA' if sw['normalidade_rejeitada'] else 'não rejeitada'}")
        tt = comp["t_pareado"]
        print(f"  t pareado    : t({tt['gl']})={tt['estatistica']:.4f}, "
              f"p={tt['p_valor']:.6f} -> "
              f"{'SIGNIFICATIVO' if tt['significativo'] else 'não significativo'}")
        wx = comp["wilcoxon"]
        print(f"  Wilcoxon     : W={wx['estatistica']:.1f}, p={wx['p_valor']:.4f} -> "
              f"{'significativo' if wx['significativo'] else 'não significativo'}")
        print(f"  Cohen's d    : {comp['cohen_d']:.3f}")
        print(f"  Teste primário: {comp['teste_primario']}")

    for chave, titulo in (
        ("leakage_vs_sem_leakage", "Com leakage - Sem leakage"),
        ("simbolica_vs_mlp_puro", "Simbólica - MLP puro"),
    ):
        print(f"\n{'-' * 78}\n## Por gênero (exploratório): {titulo}\n")
        print(f"{'Gênero':<16} {'dif. média':>11} {'DP':>7}  {'sinal'}")
        pg = resultado["por_genero_exploratorio"][chave]
        for g, v in sorted(pg.items(), key=lambda kv: -kv[1]["diferenca"]["media"]):
            d = v["diferenca"]
            sinal = "consistente" if v["sinal_consistente"] else "varia entre seeds"
            print(f"{g:<16} {pct(d['media']):>10} {pct(d['desvio_padrao']):>7}  {sinal}")

    ti = resultado["taxa_intervencao"]
    ov = resultado["overlap_musicas_pct"]
    print(f"\n{'-' * 78}")
    print(f"Taxa de intervenção da camada simbólica: {pct(ti['media'])}% "
          f"(DP {pct(ti['desvio_padrao'])})")
    print(f"Overlap de músicas dev/teste (com leakage): {ov['media']:.2f}% "
          f"(DP {ov['desvio_padrao']:.2f})")
    print(f"\nSalvo em: {SAIDA}")


if __name__ == "__main__":
    main()
