#!/usr/bin/env python3
"""
Base de conhecimento musicológico — regras simbólicas para classificação de gêneros.

Thresholds foram determinados a partir de:
  1. Análise estatística das features no conjunto de TREINO
     (camada_simbolica/results/features_por_genero.json, gerado por analise_features_genero.py)
  2. Conhecimento musicológico dos gêneros brasileiros (Bezerra, 2017; Dias & Dupan, 2022;
     Quadros Júnior, 2019, citados em Ribeiro et al., 2026)

Foco nos gêneros de classificação mais difícil no MLP correto:
  - Forró: 66.4%   (confundido com Forró Piseiro e Pagode)
  - Bossa Nova: 68.5%   (confundida com Forró e Samba)
  - Samba: 69.3%   (confundido com Pagode e Forró)

Confusões mais frequentes (matriz de confusão MLP correto):
  Pagode → Samba (52 casos), Sertanejo → Bossa Nova (44 casos),
  Bossa Nova → Forró (36 casos), Bossa Nova → Samba (35 casos),
  Forró → Pagode (34 casos), Samba → Forró (32 casos)

Features utilizadas (nomes reais do parquet mean/):
  - zcr-mean0:             zero-crossing rate — textura/ruído
  - rms-mean0:             energia/volume RMS
  - spectral_centroid-mean0: "brilho" (Hz) — grave=baixo, agudo=alto
  - roll_off-mean0.85:     frequência abaixo da qual está 85% da energia

Médias por gênero no conjunto de treino (referência para thresholds):
  Gênero           zcr     rms     spectral_centroid  roll_off
  Bossa Nova       0.040   0.141   2051               4267
  Sertanejo        0.055   0.149   2266               4610
  Forró            0.068   0.155   2652               5705
  Samba            0.057   0.141   2720               5866
  Samba-Enredo     0.058   0.213   2851               6366
  Funk             0.066   0.177   2925               6166
  Pagode           0.059   0.197   3069               7051
  Forró Piseiro    0.071   0.253   3237               7108
"""

from camada_simbolica import Condicao, Regra

# ─── Thresholds (ponto médio entre médias dos gêneros alvo) ──────────────────

# Forró (0.155) vs Forró Piseiro (0.253) — separação muito boa
THRESH_RMS_PISEIRO = 0.2040        # (0.155 + 0.253) / 2

# Forró (2652) vs Forró Piseiro (3237) — separação boa
THRESH_SC_PISEIRO  = 2944.67       # (2652 + 3237) / 2

# Forró (5705) vs Forró Piseiro (7108) — reforço para R1
THRESH_ROLLOFF_PISEIRO = 6406.58   # (5705 + 7108) / 2

# Bossa Nova (0.040) vs Samba (0.057) — maior discriminante BN
THRESH_ZCR_BN      = 0.0488        # (0.040 + 0.057) / 2

# Bossa Nova (2051) vs Sertanejo (2266) — BN tem SC menor
THRESH_SC_BN       = 2350.0        # q75 de BN (~2434), abaixo da média de Sertanejo

# Samba (0.141) vs Samba-Enredo (0.213) — separação boa
THRESH_RMS_SE      = 0.1766        # (0.141 + 0.213) / 2

# Samba (5866) vs Samba-Enredo (6366) — segunda condição de R4 para reduzir falsos disparos
THRESH_ROLLOFF_SE  = 6116.0        # (5866 + 6366) / 2

# Samba (0.141) vs Pagode (0.197) — Pagode mais energético
THRESH_RMS_PAGODE  = 0.1690        # (0.141 + 0.197) / 2

# Samba (5866) vs Pagode (7051) — Pagode tem roll-off mais alto
THRESH_ROLLOFF_PAGODE = 6458.84    # (5866 + 7051) / 2

# Samba (2720) vs Pagode (3069) — Pagode mais brilhante
THRESH_SC_PAGODE   = 2894.40       # (2720 + 3069) / 2

# Bossa Nova (2051) vs Sertanejo (2266) — threshold de separação
THRESH_SC_SERT     = 2158.62       # (2051 + 2266) / 2

# Limite superior de ZCR para Sertanejo — acima disso é território de Forró
# Sertanejo zcr q75=0.066, Forró zcr q25=0.049 → overlap real só até 0.066
THRESH_ZCR_SERT_MAX = 0.0660       # q75 de Sertanejo

# ─── Regras ──────────────────────────────────────────────────────────────────

REGRAS = [

    # R1: Forró Piseiro — eletrônico, alta energia, som brilhante
    # Motivação: Dias & Dupan (2022) descrevem Forró Piseiro como variante com
    # instrumentação eletrônica e bateria eletrônica, contrastando com o Forró
    # tradicional (zabumba + triângulo + sanfona). Reflete-se em RMS e SC maiores.
    Regra(
        nome="R1: Forró Piseiro eletrônico (rms + spectral_centroid altos)",
        condicoes=[
            Condicao('rms-mean0',              'gt', THRESH_RMS_PISEIRO),
            Condicao('spectral_centroid-mean0', 'gt', THRESH_SC_PISEIRO),
        ],
        genero_alvo='Forró Piseiro',
        generos_penalizar=['Forró', 'Samba'],
        fator_boost=1.35,
        fator_penalidade=0.70,
    ),

    # R2: Forró tradicional — acústico, energia moderada, som intermediário
    # Regra inversa de R1: zabumba, triângulo e sanfona produzem espectro
    # menos brilhante e volume menor que a versão eletrônica.
    Regra(
        nome="R2: Forró acústico (rms + spectral_centroid intermediários)",
        condicoes=[
            Condicao('rms-mean0',              'lt', THRESH_RMS_PISEIRO),
            Condicao('spectral_centroid-mean0', 'between', [2100.0, THRESH_SC_PISEIRO]),
        ],
        genero_alvo='Forró',
        generos_penalizar=['Forró Piseiro'],
        fator_boost=1.20,
        fator_penalidade=0.80,
    ),

    # R3: Bossa Nova — jazz brasileiro, suave, baixo ZCR e SC
    # Motivação: BN combina Samba com influências de Jazz/Blues — geralmente
    # menos percussiva, mais harmônica e com instrumentação mais suave
    # (Ribeiro et al., 2026, Seção 2.5; Quadros Júnior, 2019).
    Regra(
        nome="R3: Bossa Nova suave (zcr + spectral_centroid baixos)",
        condicoes=[
            Condicao('zcr-mean0',              'lt', THRESH_ZCR_BN),
            Condicao('spectral_centroid-mean0', 'lt', THRESH_SC_BN),
        ],
        genero_alvo='Bossa Nova',
        generos_penalizar=['Samba', 'Forró', 'Pagode'],
        fator_boost=1.30,
        fator_penalidade=0.80,
    ),

    # R4: Samba-Enredo — carnavalesco, alta percussão, mais energético que Samba
    # Motivação: executado em desfiles de carnaval com baterias de escolas de samba
    # — alta energia e percussão intensa (Ribeiro et al., 2026, Seção 2.5).
    # Segunda condição (roll_off) reduz falsos disparos em amostras de Samba com
    # RMS elevado mas perfil espectral típico do Samba (roll_off mais baixo).
    Regra(
        nome="R4: Samba-Enredo enérgico (rms + roll_off altos)",
        condicoes=[
            Condicao('rms-mean0',        'gt', THRESH_RMS_SE),
            Condicao('roll_off-mean0.85', 'gt', THRESH_ROLLOFF_SE),
        ],
        genero_alvo='Samba-Enredo',
        generos_penalizar=['Samba'],
        fator_boost=1.20,
        fator_penalidade=0.80,
    ),

    # R5: Pagode — derivado do Samba, mais energético e brilhante
    # Motivação: Pagode mantém raízes do Samba mas com instrumentação elétrica
    # adicional (baixo elétrico, cavaquinho amplificado) que eleva RMS e SC.
    Regra(
        nome="R5: Pagode brilhante (rms + spectral_centroid acima do Samba)",
        condicoes=[
            Condicao('rms-mean0',              'gt', THRESH_RMS_PAGODE),
            Condicao('spectral_centroid-mean0', 'gt', THRESH_SC_PAGODE),
        ],
        genero_alvo='Pagode',
        generos_penalizar=['Samba', 'Forró'],
        fator_boost=1.25,
        fator_penalidade=0.80,
    ),

    # R6: Sertanejo — viola caipira/guitarra, ZCR moderado, SC baixo-médio
    # Distingue de Bossa Nova (ZCR muito mais baixo) e de Forró (ZCR mais alto).
    # Limite superior de ZCR (0.066 = q75 de Sertanejo) evita falsos disparos
    # em amostras de Forró, cujo ZCR médio (0.068) ultrapassa esse teto.
    # Motivação: Bezerra (2017) descreve viola caipira como instrumento definidor
    # do Sertanejo — produz padrão de ZCR diferente do violão de BN e da sanfona.
    Regra(
        nome="R6: Sertanejo (zcr intermediário, spectral_centroid baixo-médio)",
        condicoes=[
            Condicao('zcr-mean0',              'between', [THRESH_ZCR_BN, THRESH_ZCR_SERT_MAX]),
            Condicao('spectral_centroid-mean0', 'between', [THRESH_SC_SERT, 2700.0]),
        ],
        genero_alvo='Sertanejo',
        generos_penalizar=['Bossa Nova'],
        fator_boost=1.20,
        fator_penalidade=0.80,
    ),

]
