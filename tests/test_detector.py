import json
from pathlib import Path

import pytest

from detector import ErroDeteccao, converter_resposta, detectar

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


# Carrega uma resposta bruta salva do Roboflow
def fixture(nome):
    with open(FIXTURES / nome, encoding="utf-8") as arquivo:
        return json.load(arquivo)


# Verifica: converte resposta real
def test_converte_resposta_real():
    deteccoes = converter_resposta(fixture("resposta_roboflow_com_deteccoes.json"))
    assert len(deteccoes) == 4
    primeira = deteccoes[0]
    assert primeira["classe"] == "Hammer"
    assert primeira["confianca"] == pytest.approx(0.3048, abs=1e-4)
    # x=180.5, y=232, width=59, height=414
    assert primeira["caixa_xyxy"] == pytest.approx([151.0, 25.0, 210.0, 439.0])


# Verifica: resposta real sem predicoes
def test_resposta_real_sem_predicoes():
    assert converter_resposta(fixture("resposta_roboflow.json")) == []


# Verifica: resposta sem predictions gera erro
def test_resposta_sem_predictions_gera_erro():
    with pytest.raises(ErroDeteccao, match="formato inesperado"):
        converter_resposta({"image": {}})


# Verifica: predicao incompleta gera erro
def test_predicao_incompleta_gera_erro():
    with pytest.raises(ErroDeteccao, match="formato inesperado"):
        converter_resposta({"predictions": [{"x": 1, "y": 1, "class": "Hammer"}]})


# Cliente falso que simula falha de rede
class ClienteQueFalha:
    # Sempre lança erro de conexão
    def infer(self, *args, **kwargs):
        raise ConnectionError("sem rede")


# Verifica: falha na chamada vira erro deteccao
def test_falha_na_chamada_vira_erro_deteccao():
    with pytest.raises(ErroDeteccao, match="Falha na chamada ao Roboflow"):
        detectar(None, {"model_id": "x"}, cliente=ClienteQueFalha())
