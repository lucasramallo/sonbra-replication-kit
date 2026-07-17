#!/usr/bin/env python3
"""
Experimento principal: MLP sobre o dataset SONBRA em três condições, repetidas
com cinco sementes aleatórias e pareadas por semente.

Condições avaliadas em cada semente (a mesma semente é usada nas três, o que
torna as comparações pareadas):
  A) Com leakage   — split aleatório por fragmento (replica o protocolo do
     artigo original de Ribeiro et al. 2026)
  B) Sem leakage   — split por música (grupo = arquivo), 0% de overlap,
     garantido por assert
  C) Sem leakage + camada simbólica — pós-processador de 6 regras de domínio
     sobre o MLP de (B)

Contrastes: A vs. B mede o efeito do data leakage; B vs. C, o efeito da
camada simbólica.

FATORES FIXOS (não variam entre sementes, por decisão de desenho):
  - Arquitetura do MLP: ativação tanh, camadas (200,100), features
    mel+mfcc+tempogram (532 colunas). Selecionada UMA vez por grid search em
    etapa preparatória; não é re-selecionada a cada semente.
  - As 6 regras simbólicas e seus limiares (ver conhecimento_dominio.py).

O que as repetições medem, portanto, é a variação estocástica do pipeline
final — partição dos dados e inicialização/treino da rede —, não a do
processo de seleção de modelo. As implicações disso para a validade estão
declaradas na seção "Ameaças à Validade" do artigo.

Uso:
    python src/experimento_repeticoes.py

Requer o dataset SONBRA; ver data/README.md. Duração: ~12,5 min em CPU.
"""

import json
import os
import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

from camada_simbolica import CamadaSimbolica, GENEROS
from conhecimento_dominio import REGRAS

warnings.filterwarnings('ignore')

# ─── Configuração ──────────────────────────────────────────────────────────

SEEDS = [42, 7, 123, 2024, 99]

BASE = Path(__file__).resolve().parents[1]   # raiz do pacote
RESULTS_DIR = BASE / 'results'
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def resolver_data_path() -> Path:
    """Localiza a base SONBRA. Ver data/README.md para obter o dataset.

    Ordem: variável de ambiente SONBRA_DATA, depois data/ neste pacote, depois
    um data/ no diretório-pai (conveniência para layouts alternativos).
    """
    candidatos = []
    if os.environ.get('SONBRA_DATA'):
        candidatos.append(Path(os.environ['SONBRA_DATA']))
    candidatos.append(BASE / 'data/base_sonbra/parquet/mean')
    candidatos.append(BASE.parent / 'data/base_sonbra/parquet/mean')

    for c in candidatos:
        if c.is_dir():
            return c
    raise SystemExit(
        "Base SONBRA não encontrada. Procurei em:\n  "
        + "\n  ".join(str(c) for c in candidatos)
        + "\n\nBaixe o dataset do Zenodo e siga data/README.md, ou aponte\n"
          "a variável de ambiente SONBRA_DATA para o diretório 'mean'."
    )


DATA_PATH = resolver_data_path()

GENEROS_DIR = {
    'bossa_nova':   'Bossa Nova',
    'forro':        'Forró',
    'pisadinha':    'Forró Piseiro',
    'funk':         'Funk',
    'pagode':       'Pagode',
    'samba':        'Samba',
    'samba_enredo': 'Samba-Enredo',
    'sertanejo':    'Sertanejo',
}

FEATURE_PREFIXES = {'tempogram': 'tempogram-', 'mel': 'mel-', 'mfcc': 'mfcc-'}
COMBO = ['mel', 'mfcc', 'tempogram']  # fator fixo (ver docstring)

FEATURES_ESCALARES = [
    'zcr-mean0', 'rms-mean0', 'spectral_centroid-mean0', 'roll_off-mean0.85',
]

LIMIAR_CONFIANCA = 0.65
META = {'classe', 'arquivo', 'divisao', 'genero'}


# ─── Dados ──────────────────────────────────────────────────────────────────

def carregar_dataset() -> pd.DataFrame:
    dfs = []
    for pasta, genero in GENEROS_DIR.items():
        for arq in sorted((DATA_PATH / pasta).glob('*.parquet')):
            df = pd.read_parquet(arq)
            df['genero'] = genero
            dfs.append(df)
    return pd.concat(dfs, ignore_index=True)


def idx_combo(feat_cols):
    idx = []
    for g in COMBO:
        pref = FEATURE_PREFIXES[g]
        idx.extend(i for i, c in enumerate(feat_cols) if c.startswith(pref))
    return idx


def mlp_fixed(seed):
    return dict(
        hidden_layer_sizes=(200, 100), activation='tanh',
        solver='adam', alpha=0.0001, learning_rate_init=0.001,
        max_iter=500, random_state=seed,
        early_stopping=True, validation_fraction=0.1,
        n_iter_no_change=15, tol=1e-4,
    )


# ─── Cenário A: com leakage (split por fragmento) ───────────────────────────

def rodar_com_leakage(df, feat_cols, idx, seed):
    X = df[feat_cols].to_numpy(dtype=np.float64)[:, idx]
    y = df['genero'].to_numpy()
    arquivo = df['arquivo'].to_numpy()

    X_dev, X_test, y_dev, y_test, arq_dev, arq_test = train_test_split(
        X, y, arquivo, test_size=0.30, stratify=y, random_state=seed)

    overlap_pct = len(set(arq_dev) & set(arq_test)) / len(set(arq_test)) * 100

    scaler = StandardScaler()
    X_dev_s  = scaler.fit_transform(X_dev)
    X_test_s = scaler.transform(X_test)

    modelo = MLPClassifier(**mlp_fixed(seed))
    modelo.fit(X_dev_s, y_dev)
    y_pred = modelo.predict(X_test_s)

    acc = accuracy_score(y_test, y_pred)
    classes = sorted(np.unique(y_test))
    acc_pg = {g: round(float(accuracy_score(y_test[y_test == g], y_pred[y_test == g])), 4)
              for g in classes}
    return dict(acc_teste=round(float(acc), 4), acuracia_por_genero=acc_pg,
                overlap_musicas_pct=round(overlap_pct, 2))


# ─── Cenários B/C: sem leakage (split por música) + camada simbólica ────────

def split_por_musica(df, seed):
    arquivo_genero = (
        df.groupby('arquivo')['genero'].agg(lambda x: x.mode().iloc[0]).reset_index()
    )
    arq_dev, arq_test = train_test_split(
        arquivo_genero, test_size=0.30,
        stratify=arquivo_genero['genero'], random_state=seed)

    df_dev  = df[df['arquivo'].isin(arq_dev['arquivo'])]
    df_test = df[df['arquivo'].isin(arq_test['arquivo'])]

    overlap = len(set(df_dev['arquivo']) & set(df_test['arquivo']))
    assert overlap == 0, f"ERRO: {overlap} músicas em dev e teste (seed={seed})"

    return df_dev, df_test


def rodar_sem_leakage_e_simbolica(df, feat_cols, idx, seed):
    df_dev, df_test = split_por_musica(df, seed)

    X_dev  = df_dev[feat_cols].to_numpy(dtype=np.float64)[:, idx]
    X_test = df_test[feat_cols].to_numpy(dtype=np.float64)[:, idx]
    y_dev  = df_dev['genero'].to_numpy()
    y_test = df_test['genero'].to_numpy()

    scaler = StandardScaler()
    X_dev_s  = scaler.fit_transform(X_dev)
    X_test_s = scaler.transform(X_test)

    modelo = MLPClassifier(**mlp_fixed(seed))
    modelo.fit(X_dev_s, y_dev)

    # MLP puro
    y_pred_mlp = modelo.predict(X_test_s)
    acc_mlp = accuracy_score(y_test, y_pred_mlp)
    classes = sorted(np.unique(y_test))
    acc_pg_mlp = {g: round(float(accuracy_score(y_test[y_test == g], y_pred_mlp[y_test == g])), 4)
                  for g in classes}

    # MLP + camada simbólica (regras fixas, importadas de conhecimento_dominio)
    camada = CamadaSimbolica(regras=REGRAS, limiar_confianca=LIMIAR_CONFIANCA)
    proba = modelo.predict_proba(X_test_s)
    classes_mlp = list(modelo.classes_)
    feat_escalares_test = df_test[FEATURES_ESCALARES].to_dict('records')

    y_pred_ns = []
    for prob_vec, feat_dict in zip(proba, feat_escalares_test):
        prob_reordenado = np.array([
            prob_vec[classes_mlp.index(g)] if g in classes_mlp else 0.0
            for g in GENEROS
        ])
        prob_ajustado = camada.aplicar(prob_reordenado, feat_dict)
        y_pred_ns.append(GENEROS[np.argmax(prob_ajustado)])
    y_pred_ns = np.array(y_pred_ns)

    acc_ns = accuracy_score(y_test, y_pred_ns)
    acc_pg_ns = {g: round(float(accuracy_score(y_test[y_test == g], y_pred_ns[y_test == g])), 4)
                 for g in classes}

    res_mlp = dict(acc_teste=round(float(acc_mlp), 4), acuracia_por_genero=acc_pg_mlp)
    res_ns = dict(
        acc_teste=round(float(acc_ns), 4), acuracia_por_genero=acc_pg_ns,
        taxa_intervencao=round(camada.taxa_intervencao(), 4),
        regras_disparadas=dict(camada._regras_disparadas),
    )
    return res_mlp, res_ns


# ─── Orquestração ────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print(f"REPETIÇÃO COM {len(SEEDS)} SEEDS — MQE (Métodos Quantitativos e Experimentação)")
    print(f"Seeds: {SEEDS}")
    print("=" * 70)

    df = carregar_dataset()
    feat_cols = [c for c in df.columns if c not in META]
    idx = idx_combo(feat_cols)
    print(f"Dataset: {len(df)} amostras, {df['arquivo'].nunique()} músicas, "
          f"{len(idx)} features (mel+mfcc+tempogram)\n")

    resultados = {
        'seeds': SEEDS,
        'arquitetura_fixa': {
            'combo_features': 'mel+mfcc+tempogram', 'n_features': len(idx),
            'hidden_layer_sizes': [200, 100], 'activation': 'tanh',
            'origem': 'selecionada uma única vez por grid search em etapa preparatória; fator fixo, não re-selecionada a cada semente',
        },
        'execucoes': [],
    }

    for seed in SEEDS:
        print(f"\n{'─'*70}\nSEED = {seed}\n{'─'*70}")
        t0 = time.time()

        print("  [A] Com leakage (split aleatório por fragmento)...")
        res_leak = rodar_com_leakage(df, feat_cols, idx, seed)
        print(f"      acc={res_leak['acc_teste']:.4f}  "
              f"overlap_musicas={res_leak['overlap_musicas_pct']:.1f}%")

        print("  [B/C] Sem leakage (split por música) + camada simbólica...")
        res_mlp, res_ns = rodar_sem_leakage_e_simbolica(df, feat_cols, idx, seed)
        print(f"      MLP puro:        acc={res_mlp['acc_teste']:.4f}")
        print(f"      MLP + simbólica: acc={res_ns['acc_teste']:.4f}  "
              f"(delta={res_ns['acc_teste']-res_mlp['acc_teste']:+.4f})")

        dt = time.time() - t0
        print(f"  Tempo desta seed: {dt/60:.1f} min")

        resultados['execucoes'].append(dict(
            seed=seed,
            tempo_seg=round(dt, 1),
            com_leakage=res_leak,
            sem_leakage_mlp_puro=res_mlp,
            sem_leakage_mlp_simbolico=res_ns,
        ))

        # salva incrementalmente — permite inspecionar resultados parciais
        # se a execução completa (5 seeds) for interrompida
        with open(RESULTS_DIR / 'resultados_repeticoes.json', 'w', encoding='utf-8') as f:
            json.dump(resultados, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*70}")
    print("RESUMO — acurácia geral por seed e cenário")
    print(f"{'='*70}")
    print(f"{'seed':<8}{'com_leakage':>14}{'sem_leakage':>14}{'+simbolica':>14}")
    for e in resultados['execucoes']:
        print(f"{e['seed']:<8}"
              f"{e['com_leakage']['acc_teste']:>14.4f}"
              f"{e['sem_leakage_mlp_puro']['acc_teste']:>14.4f}"
              f"{e['sem_leakage_mlp_simbolico']['acc_teste']:>14.4f}")

    print(f"\nResultados salvos em {RESULTS_DIR / 'resultados_repeticoes.json'}")
    return resultados


if __name__ == '__main__':
    t0 = time.time()
    main()
    print(f"\nTempo total: {(time.time() - t0)/60:.1f} min")
