"""Emite as tabelas LaTeX do artigo a partir de results/analise_estatistica.json.

Gerar em vez de transcrever à mão mantém os números do artigo sincronizados
com os resultados: main_mqe.tex traz \\input destes arquivos, então reexecutar
o experimento e este script basta para atualizar o artigo.

Saída: tabelas/tab_{descritiva,testes,genero}.tex
"""

import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]   # raiz do pacote
ENTRADA = BASE / "results/analise_estatistica.json"
SAIDA_DIR = BASE / "tabelas"

D = json.loads(ENTRADA.read_text())


def num(v, casas=2, sinal=False):
    """Formata em porcentagem/p.p. com vírgula decimal (padrão pt-BR)."""
    fmt = f"{{:+.{casas}f}}" if sinal else f"{{:.{casas}f}}"
    s = fmt.format(100 * v).replace(".", ",")
    if sinal:
        s = s.replace("+", "$+$").replace("-", "$-$")
    return s


def tabela_geral():
    # Rótulos curtos: os do JSON estouram a largura de coluna do template ACM.
    # A/B/C são as mesmas condições nomeadas na seção de desenho experimental.
    curtos = {
        "com_leakage": "(A) Com \\textit{leakage}",
        "sem_leakage_mlp_puro": "(B) Sem \\textit{leakage}",
        "sem_leakage_mlp_simbolico": "(C) Sem \\textit{leak.} + simb.",
    }
    dc = D["descritiva_por_cenario"]
    linhas = []
    for k, rot in curtos.items():
        d = dc[k]
        linhas.append(
            f"{rot} & {num(d['media'])} & {num(d['desvio_padrao'])} & "
            f"[{num(d['ic95_inf'])};\\,{num(d['ic95_sup'])}] \\\\"
        )
    return r"""\begin{table}[h]
\centering
\small
\caption{Acurácia de teste por cenário: média, desvio-padrão e intervalo
de confiança de 95\% sobre as cinco repetições. As condições A, B e C são
as definidas na Seção~\ref{sec:desenho}.}
\label{tab:descritiva}
\begin{tabular}{@{}lrrc@{}}
\toprule
\textbf{Cenário} & \textbf{Média}~(\%) & \textbf{DP}~(p.p.) & \textbf{IC 95\%}~(\%) \\
\midrule
""" + "\n".join(linhas) + r"""
\bottomrule
\end{tabular}
\end{table}"""


def tabela_testes():
    linhas = []
    rotulos = {
        "leakage_vs_sem_leakage": "Com \\textit{leak.} $-$ Sem \\textit{leak.}",
        "simbolica_vs_mlp_puro": "Simbólica $-$ MLP puro",
    }
    for k, rot in rotulos.items():
        c = D["comparacoes"][k]
        dif, sw, tt, wx = c["diferenca"], c["shapiro_wilk"], c["t_pareado"], c["wilcoxon"]
        p_t = f"{tt['p_valor']:.5f}".replace(".", ",")
        p_w = f"{wx['p_valor']:.4f}".replace(".", ",")
        p_sw = f"{sw['p_valor']:.4f}".replace(".", ",")
        # A vírgula decimal é aplicada por número; nunca à linha inteira,
        # senão corrompe os pontos do LaTeX (ex.: \textit{leak.}).
        d_cohen = f"{c['cohen_d']:.2f}".replace(".", ",")
        linhas.append(
            f"{rot} & {num(dif['media'], sinal=True)} & "
            f"[{num(dif['ic95_inf'], sinal=True)};\\,{num(dif['ic95_sup'], sinal=True)}] & "
            f"{p_sw} & {p_t} & {p_w} & {d_cohen} \\\\"
        )
    return r"""\begin{table*}[t]
\centering
\caption{Testes de hipótese sobre as diferenças pareadas por semente
($n{=}5$, $\alpha{=}0{,}05$). Shapiro-Wilk é aplicado às diferenças;
$p$ do teste primário em cada linha aparece em negrito no texto.}
\label{tab:testes}
\begin{tabular}{@{}lrrrrrr@{}}
\toprule
\textbf{Comparação} & \textbf{Dif.\ média}~(p.p.) & \textbf{IC 95\%}~(p.p.) &
\textbf{$p$ Shapiro} & \textbf{$p$ $t$ pareado} & \textbf{$p$ Wilcoxon} &
\textbf{$d$ de Cohen} \\
\midrule
""" + "\n".join(linhas) + r"""
\bottomrule
\end{tabular}
\end{table*}"""


def tabela_por_genero():
    pg_leak = D["por_genero_exploratorio"]["leakage_vs_sem_leakage"]
    pg_simb = D["por_genero_exploratorio"]["simbolica_vs_mlp_puro"]
    linhas = []
    for g in sorted(pg_leak):
        leak = pg_leak[g]
        simb = pg_simb[g]
        marca = "$^{\\dagger}$" if simb["sinal_consistente"] else ""
        linhas.append(
            f"{g} & {num(leak['grupo_a']['media'])} & "
            f"{num(leak['grupo_b']['media'])} & "
            f"{num(leak['diferenca']['media'], sinal=True)} & "
            f"{num(simb['grupo_a']['media'])} & "
            f"{num(simb['diferenca']['media'], sinal=True)}{marca} \\\\"
        )
    dc = D["descritiva_por_cenario"]
    geral = (
        f"\\textbf{{Geral}} & \\textbf{{{num(dc['com_leakage']['media'])}}} & "
        f"\\textbf{{{num(dc['sem_leakage_mlp_puro']['media'])}}} & "
        f"\\textbf{{{num(D['comparacoes']['leakage_vs_sem_leakage']['diferenca']['media'], sinal=True)}}} & "
        f"\\textbf{{{num(dc['sem_leakage_mlp_simbolico']['media'])}}} & "
        f"\\textbf{{{num(D['comparacoes']['simbolica_vs_mlp_puro']['diferenca']['media'], sinal=True)}}} \\\\"
    )
    return r"""\begin{table*}[t]
\centering
\caption{Acurácia média por gênero nas cinco repetições (\%) e diferenças
médias (p.p.). Análise exploratória: sem teste de hipótese por gênero.
$^{\dagger}$ indica sinal consistente nas cinco sementes.}
\label{tab:genero}
\begin{tabular}{@{}lrrrrr@{}}
\toprule
& \multicolumn{3}{c}{\textbf{Efeito do \textit{leakage}}} & \multicolumn{2}{c}{\textbf{Efeito da camada simbólica}} \\
\cmidrule(lr){2-4} \cmidrule(lr){5-6}
\textbf{Gênero} & \textbf{Com \textit{leak.}} & \textbf{Sem \textit{leak.}} & $\boldsymbol{\Delta}$ &
\textbf{+\,Simb.} & $\boldsymbol{\Delta}$ \\
\midrule
""" + "\n".join(linhas) + r"""
\midrule
""" + geral + r"""
\bottomrule
\end{tabular}
\end{table*}"""


def main():
    SAIDA_DIR.mkdir(parents=True, exist_ok=True)
    tabelas = {
        "tab_descritiva": tabela_geral(),
        "tab_testes": tabela_testes(),
        "tab_genero": tabela_por_genero(),
    }
    cabecalho = "% Gerado por src/gerar_tabelas.py — não editar à mão.\n"
    for nome, corpo in tabelas.items():
        destino = SAIDA_DIR / f"{nome}.tex"
        destino.write_text(cabecalho + corpo + "\n")
        print(f"  {destino}")


if __name__ == "__main__":
    main()
