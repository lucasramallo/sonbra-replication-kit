#!/usr/bin/env python3
"""
Camada de IA Simbólica — pós-processador do MLP.

Arquitetura:
    prob_vector = MLP.predict_proba(features)
    if max(prob_vector) < limiar_confianca:
        prob_vector = camada.aplicar(prob_vector, features_dict)
    predicao = argmax(prob_vector)

Cada Regra tem:
  - condicoes: lista de Condicao (feature, operador, valor)
  - genero_alvo: gênero a ser favorecido quando a regra dispara
  - generos_penalizar: gêneros a serem penalizados
  - fator_boost: multiplicador para o gênero alvo (ex: 1.3 = +30%)
  - fator_penalidade: multiplicador para os gêneros penalizados (ex: 0.7 = -30%)
"""

from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np

# Ordem das classes: bate com sorted(y_train.unique()) no experimento
GENEROS = [
    'Bossa Nova',
    'Forró',
    'Forró Piseiro',
    'Funk',
    'Pagode',
    'Samba',
    'Samba-Enredo',
    'Sertanejo',
]
GENERO_IDX: Dict[str, int] = {g: i for i, g in enumerate(GENEROS)}


@dataclass
class Condicao:
    """Uma condição avaliada sobre o valor de uma feature acústica."""
    feature: str    # nome da coluna (ex: 'zcr-mean0', 'spectral_centroid-mean0')
    operador: str   # 'gt' (>), 'lt' (<), 'between' ([a, b])
    valor: object   # float para gt/lt, [float, float] para between

    def avaliar(self, features: Dict[str, float]) -> bool:
        v = features.get(self.feature)
        if v is None or np.isnan(v):
            return False
        if self.operador == 'gt':
            return float(v) > float(self.valor)
        if self.operador == 'lt':
            return float(v) < float(self.valor)
        if self.operador == 'between':
            return float(self.valor[0]) <= float(v) <= float(self.valor[1])
        raise ValueError(f"Operador desconhecido: {self.operador}")


@dataclass
class Regra:
    """Regra IF-THEN musicológica."""
    nome: str
    condicoes: List[Condicao]
    genero_alvo: str
    generos_penalizar: List[str] = field(default_factory=list)
    fator_boost: float = 1.3
    fator_penalidade: float = 0.7

    def dispara(self, features: Dict[str, float]) -> bool:
        return all(c.avaliar(features) for c in self.condicoes)


class CamadaSimbolica:
    """
    Pós-processador simbólico do vetor de probabilidades do MLP.

    Uso:
        camada = CamadaSimbolica(regras=REGRAS, limiar_confianca=0.5)
        prob_ajustado = camada.aplicar(prob_vector, features_dict)
    """

    def __init__(self, regras: List[Regra], limiar_confianca: float = 0.5):
        self.regras = regras
        self.limiar = limiar_confianca
        self._n_total = 0
        self._n_intervencoes = 0
        self._regras_disparadas: Dict[str, int] = {r.nome: 0 for r in regras}

    def aplicar(self, prob_vector: np.ndarray, features: Dict[str, float]) -> np.ndarray:
        """
        Aplica a camada simbólica ao vetor de probabilidades.

        Args:
            prob_vector: array (8,) com probabilidades do MLP (soma = 1.0)
            features: dict {nome_feature: valor} com features escalares da amostra

        Returns:
            array (8,) com probabilidades ajustadas (re-normalizadas, soma = 1.0)
        """
        self._n_total += 1
        confianca = float(prob_vector.max())

        if confianca >= self.limiar:
            return prob_vector  # MLP confiante — não interferir

        self._n_intervencoes += 1
        ajustado = prob_vector.copy().astype(float)

        for regra in self.regras:
            if regra.dispara(features):
                self._regras_disparadas[regra.nome] += 1

                idx_alvo = GENERO_IDX[regra.genero_alvo]
                ajustado[idx_alvo] *= regra.fator_boost

                for g in regra.generos_penalizar:
                    ajustado[GENERO_IDX[g]] *= regra.fator_penalidade

        soma = ajustado.sum()
        if soma > 0:
            ajustado /= soma

        return ajustado

    def taxa_intervencao(self) -> float:
        """Fração das amostras em que a camada interveio."""
        return self._n_intervencoes / self._n_total if self._n_total > 0 else 0.0

    def relatorio_intervencoes(self) -> str:
        linhas = [
            f"Total de amostras processadas: {self._n_total}",
            f"Intervenções (confiança < {self.limiar}): {self._n_intervencoes} "
            f"({self.taxa_intervencao()*100:.1f}%)",
            "",
            "Regras disparadas:",
        ]
        for nome, n in sorted(self._regras_disparadas.items(), key=lambda x: -x[1]):
            linhas.append(f"  {nome}: {n}x")
        return "\n".join(linhas)
