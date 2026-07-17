# Replicação e Extensão Neuro-Simbólica do Benchmark SONBRA

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21403789.svg)](https://doi.org/10.5281/zenodo.21403789)
[![Licença: MIT](https://img.shields.io/badge/c%C3%B3digo-MIT-blue.svg)](LICENSE)
[![Licença: CC BY 4.0](https://img.shields.io/badge/resultados-CC%20BY%204.0-lightgrey.svg)](LICENSE)

Pacote de reprodução do experimento: **código, resultados brutos e análise
estatística**.

Este pacote contém tudo que é necessário para reproduzir os resultados a partir
do dataset público. A única dependência externa é o dataset SONBRA, obtido no
Zenodo (ver [`data/README.md`](data/README.md)).

> **O texto do artigo não faz parte deste pacote.** O que está aqui é o
> experimento e sua análise — os dados que sustentam o artigo, não o artigo.
> As tabelas em `tabelas/` são geradas em LaTeX prontas para inclusão, e os
> números que elas contêm são exatamente os reportados no texto.

**Índice:** [O experimento](#o-experimento-em-uma-frase) ·
[Resultados](#principais-resultados) · [Como reproduzir](#como-reproduzir) ·
[Estrutura](#estrutura) · [Notas de reprodução](#notas-de-reprodução) ·
[Open science](#open-science) · [Como citar](#como-citar)

---

## O experimento em uma frase

Um Perceptron Multicamadas é treinado sobre o dataset SONBRA (10.000 fragmentos
de 30s, 8 gêneros musicais brasileiros) em **três condições**, repetidas com
**cinco sementes aleatórias** e comparadas de forma **pareada por semente**:

| | Condição | Divisão dos dados | Camada simbólica |
|---|---|---|---|
| **A** | Com *leakage* | aleatória por fragmento | ausente |
| **B** | Sem *leakage* | agrupada por música | ausente |
| **C** | Sem *leakage* + simbólica | agrupada por música | presente |

O contraste **A vs. B** mede o efeito do *data leakage*; **B vs. C**, o efeito
da camada simbólica.

## Principais resultados

| Contraste | Diferença média | IC 95% | Teste primário | Conclusão |
|---|---|---|---|---|
| A − B (*leakage*) | **+13,10 p.p.** | [11,55; 14,65] | *t* pareado, *p* = 0,00002 | Rejeita H₀ |
| C − B (simbólica) | +0,02 p.p. | [−0,14; +0,18] | Wilcoxon, *p* = 0,5625 | Não rejeita H₀ |

O *data leakage* infla a acurácia em ~13 pontos percentuais, de forma
consistente nas cinco sementes. A camada simbólica tem efeito agregado
indistinguível de zero — mas isso resulta do **cancelamento** entre um ganho na
Bossa Nova (+0,91 p.p.) e uma degradação sistemática no Samba (−1,11 p.p., o
único efeito por gênero cujo sinal se mantém em todas as sementes).

---

## Como reproduzir

### 1. Ambiente

Requer Python 3.11+.

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

As versões em `requirements.txt` são as **efetivamente usadas** na execução
reportada, congeladas do ambiente que produziu
`results/resultados_repeticoes.json`.

### 2. Dataset

Baixe o SONBRA do Zenodo e organize conforme [`data/README.md`](data/README.md).
Não é distribuído aqui.

### 3. Executar

```bash
python src/experimento_repeticoes.py   # ~12,5 min (CPU, 12 núcleos)
python src/analise_estatistica.py      # instantâneo
python src/gerar_tabelas.py            # instantâneo
python src/gerar_figuras.py            # instantâneo
```

Os três últimos scripts leem apenas JSON e **rodam sem o dataset** — se quiser
apenas conferir a análise estatística sobre os resultados já publicados aqui,
pule o passo 2 e o primeiro comando.

---

## Estrutura

```
sonbra-replication-kit/
├── requirements.txt                # versões congeladas
├── README.md
├── LICENSE                         # MIT (código) + CC BY 4.0 (resultados)
├── CITATION.cff                    # metadados de citação
├── data/
│   └── README.md                   # como obter e organizar o dataset
├── src/
│   ├── experimento_repeticoes.py   # 5 sementes × 3 condições  → results/resultados_repeticoes.json
│   ├── analise_estatistica.py      # IC, Shapiro-Wilk, t pareado, Wilcoxon
│   ├── gerar_tabelas.py            # → tabelas/*.tex
│   ├── gerar_figuras.py            # → figs/*.png
│   ├── camada_simbolica.py         # motor de regras (Regra, Condicao, CamadaSimbolica)
│   └── conhecimento_dominio.py     # as 6 regras de domínio e seus limiares
├── results/
│   ├── resultados_repeticoes.json  # dados brutos das 5 repetições
│   ├── analise_estatistica.json    # descritivas, ICs, testes
│   └── run_log.txt                 # log da execução, com tempos por semente
├── tabelas/                        # GERADO — não editar à mão
└── figs/                           # GERADO (exceto matriz_confusao_*)
```

### Fluxo de dados

```
dataset SONBRA
      │
      ▼
experimento_repeticoes.py ──→ results/resultados_repeticoes.json
                                      │
                                      ▼
                          analise_estatistica.py ──→ results/analise_estatistica.json
                                                              │
                                              ┌───────────────┴───────────────┐
                                              ▼                               ▼
                                     gerar_tabelas.py                 gerar_figuras.py
                                              │                               │
                                              ▼                               ▼
                                        tabelas/*.tex                    figs/*.png
                                              │                               │
                                              └───────────────┬───────────────┘
                                                              ▼
                                                    artigo (fora deste pacote,
                                                     via \input das tabelas)
```

**As tabelas do artigo são geradas, não transcritas.** O artigo inclui
`tabelas/*.tex` via `\input`, então reexecutar o pipeline e recompilar propaga
qualquer mudança nos resultados para o texto sem intervenção manual — não há
como o artigo divergir dos dados que o sustentam.

---

## Notas de reprodução

**Determinismo.** As cinco sementes `{42, 7, 123, 2024, 99}` estão fixadas em
`src/experimento_repeticoes.py` e governam todos os componentes estocásticos de
cada repetição (partição dos dados e inicialização/treino do MLP). A execução é
determinística **no mesmo ambiente**; versões diferentes de scikit-learn podem
alterar resultados mesmo com semente idêntica, por mudanças internas no
`MLPClassifier`. Use as versões de `requirements.txt` para bater os números
exatos do artigo.

**Escopo do que é repetido.** A arquitetura do MLP (`tanh`, camadas
`(200,100)`, features mel+mfcc+tempogram) e os limiares das seis regras
simbólicas foram selecionados **uma única vez**, em etapa preparatória, e são
**fatores fixos** — não são re-selecionados a cada semente. O que as repetições
medem é a variação estocástica do *pipeline final*, não do processo de seleção
de modelo. As implicações disso para a validade estão declaradas na seção
"Ameaças à Validade" do artigo.

**Verificação de manipulação.** Sob a condição B/C, o script garante 0% de
sobreposição de músicas entre desenvolvimento e teste via `assert` em tempo de
execução. Sob a condição A, a sobreposição é medida e reportada (99,65% ± 0,13).

**A figura `matriz_confusao_mlp_correto.png`** é o único artefato visual que não
é gerado por este pacote: vem da análise de explicabilidade (XAI), que é
descritiva sobre um modelo treinado com a semente 42 e não faz parte do
experimento repetido.

**Resultados nulos são reportados como resultados.** O contraste B vs. C não
rejeita a hipótese nula, e isso está no artigo com o mesmo destaque do
resultado positivo. O achado do Sertanejo, que uma análise de execução única
teria reportado como ganho, foi refutado pela repetição — e essa refutação está
documentada em vez de omitida.

---

## Open science

Este pacote segue os princípios de ciência aberta em quatro frentes.

### Disponibilidade dos dados

O dataset SONBRA é **público e de terceiros**, disponível permanentemente no
Zenodo sob DOI [10.5281/zenodo.17958966](https://doi.org/10.5281/zenodo.17958966).
Não é redistribuído aqui para preservar a fonte canônica e seus termos de
licença — ver [`data/README.md`](data/README.md) para obtenção e organização.

Os **dados gerados por este trabalho** estão integralmente incluídos:
`results/resultados_repeticoes.json` traz as medições brutas das cinco
repetições (acurácia geral e por gênero nas três condições, taxa de
intervenção, disparos por regra, tempos), e `results/run_log.txt` traz o log
completo da execução. Nenhum resultado foi descartado: as cinco sementes foram
fixadas *a priori* e todas as cinco são reportadas.

### Disponibilidade do código

Todo o código está em `src/`, sob licença MIT, sem dependências privadas ou
serviços externos. O pacote é autocontido: não requer instalação além de
`requirements.txt`, não faz chamadas de rede e roda em CPU comum.

### Preservação de longo prazo

O pacote está **arquivado no Zenodo** sob o DOI
[10.5281/zenodo.21403789](https://doi.org/10.5281/zenodo.21403789), com
preservação de longo prazo garantida pelo CERN. O arquivamento é o que torna a
referência do artigo estável: uma URL de repositório quebra se o projeto for
renomeado, movido ou removido; o DOI, não. O GitHub permanece como espaço de
navegação, *issues* e contribuição — o Zenodo, como registro citável.

### Reprodutibilidade

- **Sementes fixadas e publicadas** — `{42, 7, 123, 2024, 99}`, no código.
- **Versões congeladas** — `requirements.txt` traz as versões exatas do
  ambiente que produziu os resultados, não faixas de compatibilidade.
- **Cadeia auditável dos números** — as tabelas do artigo são geradas a partir
  do JSON de resultados (ver [Fluxo de dados](#fluxo-de-dados)); não há
  transcrição manual entre a medição e o texto publicado.
- **Auditoria sem o dataset** — a análise estatística, as tabelas e a figura
  são reproduzíveis a partir dos JSONs incluídos, sem baixar os ~10 mil
  fragmentos. Quem quiser apenas verificar as contas não precisa dos dados.
- **Custo baixo** — o experimento completo leva ~12,5 minutos em CPU. A barreira
  para contestar ou estender estes resultados é deliberadamente baixa.

### Transparência

As limitações estão declaradas, não minimizadas. As principais, detalhadas na
seção "Ameaças à Validade" do artigo:

- **n = 5 é pequeno.** O teste de Wilcoxon com essa amostra tem *p* mínimo
  bilateral de 0,0625 e, portanto, **não pode** rejeitar H₀ a α = 0,05 sob
  nenhuma configuração dos dados. A conclusão sobre a camada simbólica se apoia
  na estreiteza do intervalo de confiança, não no valor-*p*.
- **As análises por gênero são exploratórias**, sem teste de hipótese nem
  correção para múltiplas comparações. São geradoras de hipóteses, não efeitos
  confirmados.
- **A arquitetura e as regras são fatores fixos**, selecionados uma vez. Os
  intervalos de confiança medem a variabilidade do pipeline final, não a do
  processo completo de construção do modelo.

### Licenças

| Componente | Licença |
|---|---|
| Código (`src/`) | MIT |
| Resultados (`results/`, `tabelas/`, `figs/`) | CC BY 4.0 |
| Dataset SONBRA | não incluído — ver termos no Zenodo |

Texto completo em [`LICENSE`](LICENSE).

---

## Como citar

Metadados legíveis por máquina em [`CITATION.cff`](CITATION.cff).

**Este trabalho:**

> Silva, J. L. B. R. (2026). *Replicação e Extensão Neuro-Simbólica do Benchmark
> SONBRA para Classificação de Gêneros Musicais Brasileiros* [pacote de
> reprodução]. Zenodo. DOI:
> [10.5281/zenodo.21403789](https://doi.org/10.5281/zenodo.21403789)

Cite o **DOI**, não a URL do GitHub: o DOI acima é o *concept DOI*, permanente e
sempre resolvendo para a versão mais recente. Para citar a versão exata usada,
use o DOI da release específica (`10.5281/zenodo.21403790` para a v1.0.0).

**O dataset (cite sempre que usar este pacote):**

> Ribeiro, A. V.; Santana, J. M. O.; Oliveira, M. A.; Gomes, C. (2026). SONBRA: um
> dataset público e anotado para pesquisas de classificação de gêneros musicais
> brasileiros. *Revista Eletrônica de Iniciação Científica em Computação*, 24(1).
> DOI: [10.5753/reic.2026.7222](https://doi.org/10.5753/reic.2026.7222)

---

## Contribuições e contato

Correções, replicações independentes e extensões são bem-vindas — em especial
tentativas de refutar os resultados aqui reportados. Abra uma *issue* ou um
*pull request*.

Autor: João Lucas de Brito Ramalho Silva — Programa de Pós-Graduação em Ciência
da Computação, Universidade Federal de Campina Grande.
