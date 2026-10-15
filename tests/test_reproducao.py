import json
from pathlib import Path

import cv2
import numpy as np

from camera import processar_captura
from conferir import conferir, main
from detector import ler_imagem
from nota import validar_nota
from reproducao import hash_imagem

RAIZ = Path(__file__).resolve().parent.parent
IMAGEM = RAIZ / "imagens" / "teste" / "Img 16.jpg"
OUTRA_IMAGEM = RAIZ / "imagens" / "teste" / "Img 15.jpg"
CONFIG = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))


# Devolve uma chave ajustável e uma de grifo, como a Img 16 no modelo adotado.
class ClienteDuasChaves:
    # Responde igual para qualquer modelo; não há caixa aberta nessa resposta.
    def infer(self, imagem, model_id=None):
        return {"predictions": [
            {"x": 180, "y": 290, "width": 120, "height": 400, "confidence": 0.99, "class": "Adjustable Wrench"},
            {"x": 330, "y": 290, "width": 120, "height": 400, "confidence": 0.99, "class": "Pipe Wrench"},
        ]}


# Cliente que falha se for chamado: prova que a reprodução não usa a rede.
class ClienteProibido:
    # Qualquer chamada é um erro do teste.
    def infer(self, imagem, model_id=None):
        raise AssertionError("a reprodução não deveria chamar o Roboflow")


# Grava uma nota que pede uma chave ajustável.
def escrever_nota(pasta):
    caminho = pasta / "nota.json"
    caminho.write_text(json.dumps({"nota_id": "NF-R", "itens": [
        {"codigo": "FER-003", "descricao": "Chave inglesa ajustável", "quantidade": 1}
    ]}), encoding="utf-8")
    return caminho


# Uma execução grava as respostas e a reprodução chega ao mesmo resultado, sem rede e com aviso.
def test_grava_e_reproduz_sem_rede(tmp_path):
    nota = escrever_nota(tmp_path)
    original, pasta = conferir(IMAGEM, nota, pasta_saida=tmp_path / "gravada", config=CONFIG,
                               cliente=ClienteDuasChaves(), sem_caixas=True)
    gravado = json.loads((pasta / "respostas_brutas.json").read_text(encoding="utf-8"))
    assert [c["modelo_id"] for c in gravado["chamadas"]] == [CONFIG["model_id"]]
    assert gravado["imagem_sha256"] == hash_imagem(IMAGEM)

    reproduzido, pasta_nova = conferir(IMAGEM, nota, pasta_saida=tmp_path / "reproduzida", config=CONFIG,
                                       cliente=ClienteProibido(), sem_caixas=True, reproduzir=pasta)
    assert reproduzido["status"] == original["status"] == "divergente"
    assert reproduzido["linhas"] == original["linhas"]
    assert "Reprodução offline" in reproduzido["avisos"][-1]
    assert (pasta_nova / "imagem_anotada.jpg").exists()


# Reproduzir com opções ou imagem diferentes da gravação dá erro, nunca conforme.
def test_reproducao_incompativel_vira_erro(tmp_path):
    nota = escrever_nota(tmp_path)
    _, pasta = conferir(IMAGEM, nota, pasta_saida=tmp_path / "gravada", config=CONFIG,
                        cliente=ClienteDuasChaves(), sem_caixas=True)
    com_caixas, _ = conferir(IMAGEM, nota, pasta_saida=tmp_path / "r1", config=CONFIG, reproduzir=pasta)
    outra_imagem, _ = conferir(OUTRA_IMAGEM, nota, pasta_saida=tmp_path / "r2", config=CONFIG,
                               sem_caixas=True, reproduzir=pasta)
    assert com_caixas["status"] == outra_imagem["status"] == "erro"
    assert "não corresponde à gravação" in com_caixas["avisos"][0]


# Outra foto com exatamente as mesmas dimensões não pode receber detecções antigas.
def test_reproducao_rejeita_outra_foto_do_mesmo_tamanho(tmp_path):
    nota = escrever_nota(tmp_path)
    _, pasta = conferir(IMAGEM, nota, pasta_saida=tmp_path / "gravada", config=CONFIG,
                        cliente=ClienteDuasChaves(), sem_caixas=True)
    outra = tmp_path / "outra_foto.jpg"
    imagem = np.full_like(ler_imagem(IMAGEM), 255)
    sucesso, dados = cv2.imencode(".jpg", imagem)
    assert sucesso
    outra.write_bytes(dados.tobytes())
    assert ler_imagem(outra).shape == ler_imagem(IMAGEM).shape

    relatorio, _ = conferir(outra, nota, pasta_saida=tmp_path / "reproduzida", config=CONFIG,
                            cliente=ClienteProibido(), sem_caixas=True, reproduzir=pasta)

    assert relatorio["status"] == "erro"
    assert "imagem não corresponde à gravação" in relatorio["avisos"][0]


# Gravações antigas sem identificação da imagem exigem uma gravação nova.
def test_reproducao_rejeita_gravacao_antiga_sem_hash(tmp_path):
    nota = escrever_nota(tmp_path)
    _, pasta = conferir(IMAGEM, nota, pasta_saida=tmp_path / "gravada", config=CONFIG,
                        cliente=ClienteDuasChaves(), sem_caixas=True)
    caminho = pasta / "respostas_brutas.json"
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    del dados["imagem_sha256"]
    caminho.write_text(json.dumps(dados), encoding="utf-8")

    relatorio, _ = conferir(IMAGEM, nota, pasta_saida=tmp_path / "reproduzida", config=CONFIG,
                            cliente=ClienteProibido(), sem_caixas=True, reproduzir=pasta)

    assert relatorio["status"] == "erro"
    assert "não identifica a imagem original" in relatorio["avisos"][0]


# A foto analisada salva pela câmera também serve para reproduzir sua resposta sem rede.
def test_reproducao_da_foto_salva_pela_camera(tmp_path):
    config = {**CONFIG, "modelo_caixas_id": None}
    nota_dados = {"nota_id": "NF-CAMERA-REPLAY", "itens": [
        {"codigo": "FER-003", "quantidade": 1}
    ]}
    nota = validar_nota(nota_dados, config["de_para"])
    caminho_nota = tmp_path / "nota_camera.json"
    caminho_nota.write_text(json.dumps(nota_dados), encoding="utf-8")
    pasta = tmp_path / "captura"
    original, _ = processar_captura(
        np.zeros((480, 640, 3), dtype=np.uint8), nota, config, pasta, ClienteDuasChaves()
    )

    reproduzido, _ = conferir(
        pasta / "quadro_analisado.jpg", caminho_nota, pasta_saida=tmp_path / "reproduzida",
        config=config, cliente=ClienteProibido(), reproduzir=pasta,
    )

    assert reproduzido["status"] == original["status"]
    assert reproduzido["linhas"] == original["linhas"]
    assert "Reprodução offline" in reproduzido["avisos"][-1]


# Pasta sem gravação vira erro pela CLI, com código de saída 2.
def test_reproducao_sem_arquivo_vira_erro(tmp_path, capsys):
    nota = escrever_nota(tmp_path)
    codigo = main(["--imagem", str(IMAGEM), "--nota", str(nota), "--saida", str(tmp_path / "s"),
                   "--reproduzir", str(tmp_path / "vazia"), "--json"])
    assert codigo == 2
    assert "respostas_brutas.json" in capsys.readouterr().out
