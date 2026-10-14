import json
from pathlib import Path

import pytest

from conferir import CODIGOS_SAIDA, conferir, main

RAIZ = Path(__file__).resolve().parent.parent
IMAGEM = RAIZ / "imagens" / "teste" / "Img 16.jpg"
CONFIG = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))


# Cliente falso que devolve uma chave inglesa e um parafuso (classe ignorada)
class ClienteFalso:
    # Simula a resposta do Roboflow no formato real observado
    def infer(self, imagem, model_id=None):
        return {"predictions": [
            {"x": 230, "y": 290, "width": 200, "height": 410, "confidence": 0.9, "class": "Wrench"},
            {"x": 400, "y": 290, "width": 40, "height": 40, "confidence": 0.8, "class": "Fasteners"},
            {"x": 100, "y": 100, "width": 50, "height": 50, "confidence": 0.2, "class": "Hammer"},
        ]}


# Cliente falso que simula queda de rede
class ClienteSemRede:
    # Sempre lança erro de conexão
    def infer(self, imagem, model_id=None):
        raise ConnectionError("sem rede")


# Simula as duas classes distintas devolvidas pelo modelo adotado.
class ClienteDuasChaves:
    # Devolve uma inglesa ajustável e uma chave de grifo.
    def infer(self, imagem, model_id=None):
        return {"predictions": [
            {"x": 180, "y": 290, "width": 120, "height": 400,
             "confidence": 0.99, "class": "Adjustable Wrench"},
            {"x": 330, "y": 290, "width": 120, "height": 400,
             "confidence": 0.99, "class": "Pipe Wrench"},
        ]}


# Simula o martelo verdadeiro e a falsa chave de fenda observados na webcam.
class ClienteLimiarCamera:
    # Devolve pontuações em lados opostos do limiar escolhido por Rafael.
    def infer(self, imagem, model_id=None):
        return {"predictions": [
            {"x": 180, "y": 290, "width": 120, "height": 400,
             "confidence": 0.73, "class": "Hammer"},
            {"x": 330, "y": 290, "width": 120, "height": 400,
             "confidence": 0.52, "class": "Screwdriver"},
        ]}


# Grava uma nota temporária e devolve o caminho
def escrever_nota(pasta, quantidade):
    caminho = pasta / "nota.json"
    caminho.write_text(json.dumps({"nota_id": "NF-T", "itens": [
        {"codigo": "FER-003", "descricao": "Chave inglesa", "quantidade": quantidade}
    ]}), encoding="utf-8")
    return caminho


# Verifica: conforme gera relatório e imagem
def test_conforme_gera_relatorio_e_imagem(tmp_path):
    config = {**CONFIG, "classes_ignoradas": ["Fasteners"]}
    relatorio, pasta = conferir(IMAGEM, escrever_nota(tmp_path, 1), tmp_path / "saida", config, ClienteFalso())
    assert relatorio["status"] == "conforme"
    assert relatorio["descartadas"] == [{"classe": "Hammer", "confianca": 0.2}]
    assert (pasta / "imagem_anotada.jpg").stat().st_size > 0
    salvo = json.loads((pasta / "relatorio.json").read_text(encoding="utf-8"))
    assert salvo == relatorio
    assert set(salvo) == {"nota_id", "imagem", "status", "linhas", "descartadas", "avisos",
                          "modelo_id", "limiar_confianca", "gerado_em"}


# Verifica: divergente por falta
def test_divergente(tmp_path):
    relatorio, _ = conferir(IMAGEM, escrever_nota(tmp_path, 2), tmp_path / "saida", CONFIG, ClienteFalso())
    assert relatorio["status"] == "divergente"
    assert relatorio["linhas"][0]["situacao"] == "falta"


# A nota de uma inglesa aponta a chave de grifo adicional como não prevista.
def test_modelo_novo_distingue_os_tipos_de_chave(tmp_path):
    relatorio, _ = conferir(IMAGEM, escrever_nota(tmp_path, 1), tmp_path / "saida", CONFIG, ClienteDuasChaves())
    assert relatorio["status"] == "divergente"
    linhas = {linha["classe"]: linha for linha in relatorio["linhas"]}
    assert linhas["Wrench"]["situacao"] == "igual"
    assert linhas["PipeWrench"]["situacao"] == "nao_previsto"
    assert linhas["PipeWrench"]["codigo"] == "FER-005"


# O limiar 0,60 preserva o martelo 0,73 e descarta o falso positivo 0,52.
def test_limiar_escolhido_para_camera(tmp_path):
    nota = RAIZ / "notas" / "nota_martelo_camera.json"
    relatorio, _ = conferir(IMAGEM, nota, tmp_path / "saida", CONFIG, ClienteLimiarCamera())
    assert CONFIG["limiar_confianca"] == 0.6
    assert relatorio["status"] == "conforme"
    assert [(linha["classe"], linha["detectado"]) for linha in relatorio["linhas"]] == [("Hammer", 1)]
    assert relatorio["descartadas"] == [{"classe": "Screwdriver", "confianca": 0.52}]


# Verifica: falha de rede vira erro, nunca conforme
def test_falha_de_rede_vira_erro(tmp_path):
    relatorio, pasta = conferir(IMAGEM, escrever_nota(tmp_path, 1), tmp_path / "saida", CONFIG, ClienteSemRede())
    assert relatorio["status"] == "erro"
    assert (pasta / "imagem_anotada.jpg").exists()


# Verifica: imagem inexistente vira erro com evidência gerada
def test_imagem_inexistente_vira_erro(tmp_path):
    relatorio, pasta = conferir(tmp_path / "nao_existe.jpg", escrever_nota(tmp_path, 1), tmp_path / "saida", CONFIG, ClienteFalso())
    assert relatorio["status"] == "erro"
    assert "não encontrada" in relatorio["avisos"][0]
    assert (pasta / "imagem_anotada.jpg").exists()


# Verifica: nota inválida vira erro
def test_nota_invalida_vira_erro(tmp_path):
    nota = tmp_path / "nota.json"
    nota.write_text('{"itens": [{"codigo": "FER-999", "quantidade": 1}]}', encoding="utf-8")
    relatorio, _ = conferir(IMAGEM, nota, tmp_path / "saida", CONFIG, ClienteFalso())
    assert relatorio["status"] == "erro"
    assert "FER-999" in relatorio["avisos"][0]


# Verifica: quadro vazio vira erro sem exceção
def test_quadro_vazio_vira_erro():
    from conferir import conferir_quadro
    nota = {"nota_id": "NF", "itens": [{"codigo": "FER-003", "descricao": "", "classe": "Wrench", "quantidade": 1}]}
    relatorio, evidencia = conferir_quadro(None, nota, CONFIG, cliente=ClienteFalso())
    assert relatorio["status"] == "erro"
    assert evidencia.ndim == 3


# Verifica: CLI devolve código de saída 2 em erro de entrada
def test_cli_codigo_de_saida_em_erro(tmp_path, capsys):
    codigo = main(["--imagem", str(tmp_path / "x.jpg"), "--nota", str(tmp_path / "x.json"),
                   "--saida", str(tmp_path / "saida"), "--json"])
    assert codigo == CODIGOS_SAIDA["erro"]
    assert json.loads(capsys.readouterr().out)["status"] == "erro"
