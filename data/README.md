# Dados — dataset SONBRA

O dataset **não é distribuído neste repositório** (é grande e tem fonte
canônica própria). Baixe do Zenodo e organize aqui conforme abaixo.

## 1. Obter

**Fonte:** <https://doi.org/10.5281/zenodo.17958966>

Artigo de referência: Ribeiro et al. (2026), *SONBRA: um dataset público e
anotado para pesquisas de classificação de gêneros musicais brasileiros*,
REIC 24(1). DOI: [10.5753/reic.2026.7222](https://doi.org/10.5753/reic.2026.7222)

Este experimento usa **apenas a versão de média das características**
(`mean`), em formato Parquet. As demais versões do dataset não são
necessárias.

## 2. Organizar

Posicione os arquivos nesta estrutura, a partir desta pasta:

```
data/
└── base_sonbra/
    └── parquet/
        └── mean/
            ├── bossa_nova/
            │   ├── db_bossa_nova_mean_begin_30.parquet
            │   ├── db_bossa_nova_mean_middle_1_30.parquet
            │   ├── db_bossa_nova_mean_middle_30.parquet
            │   ├── db_bossa_nova_mean_middle_2_30.parquet
            │   └── db_bossa_nova_mean_end_30.parquet
            ├── forro/
            ├── pisadinha/          ← Forró Piseiro
            ├── funk/
            ├── pagode/
            ├── samba/
            ├── samba_enredo/
            └── sertanejo/
```

São **cinco arquivos por gênero**, um por região do fragmento (`begin`,
`middle_1`, `middle`, `middle_2`, `end`); cada arquivo contém as linhas de
todas as músicas daquele gênero para aquela região.

Atenção a dois pontos que costumam confundir:

- A pasta do **Forró Piseiro** chama-se `pisadinha` no dataset original. O
  código faz esse mapeamento em `GENEROS_DIR` (`src/experimento_repeticoes.py`).
- Os nomes de arquivo seguem o padrão `db_<gênero>_mean_<região>_30.parquet`.
  O código não depende do nome exato — ele lê todos os `*.parquet` de cada
  pasta de gênero —, mas depende da **estrutura de diretórios** acima.

## 3. Usar outro caminho

Se preferir manter o dataset fora desta pasta, aponte a variável de ambiente
`SONBRA_DATA` para o diretório `mean`:

```bash
export SONBRA_DATA=/caminho/para/base_sonbra/parquet/mean
python src/experimento_repeticoes.py
```

A ordem de busca é: `SONBRA_DATA` → `data/base_sonbra/parquet/mean` (neste
pacote) → `../data/base_sonbra/parquet/mean` (no diretório-pai). Se nada for encontrado, o script falha
com uma mensagem listando onde procurou.

## 4. Verificar

Depois de organizar, confira que o carregamento encontra as 10.000 amostras
e as 1.993 músicas:

```bash
python src/experimento_repeticoes.py
```

As primeiras linhas do log reportam o total de amostras, de músicas únicas e
de features carregadas. Se os números divergirem, a estrutura de pastas está
incompleta.
