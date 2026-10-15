import json
from pathlib import Path

import numpy as np

from camera import (AREA_LEITURA, executar_camera, limites_area, main,
                    marcar_area, nova_pasta_captura, processar_captura)
from detector import ler_imagem
from nota import validar_nota


RAIZ = Path(__file__).resolve().parent.parent
CONFIG = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))


# Simula a resposta do modelo adotado com dois tipos distintos de chave.
class ClienteDuasChaves:
    # Devolve as mesmas detecções em cada captura, sem acesso à rede.
    def infer(self, imagem, model_id=None):
        return {"predictions": [
            {"x": 60, "y": 60, "width": 35, "height": 60,
             "confidence": 0.99, "class": "Adjustable Wrench"},
            {"x": 150, "y": 60, "width": 35, "height": 60,
             "confidence": 0.99, "class": "Pipe Wrench"},
        ]}


# Registra os pixels enviados ao detector para provar que o entorno foi excluído.
class ClienteRegistraRecorte:
    # Mantém uma cópia do quadro recebido e devolve um martelo.
    def infer(self, imagem, model_id=None):
        self.quadro = imagem.copy()
        return {"predictions": [
            {"x": imagem.shape[1] / 2, "y": imagem.shape[0] / 2,
             "width": 30, "height": 30, "confidence": 0.85, "class": "Hammer"}
        ]}


# Simula uma webcam sem acessar o equipamento físico.
class CameraFalsa:
    # Guarda se a rotina liberou a câmera ao terminar.
    def __init__(self, aberta=True):
        self.aberta = aberta
        self.liberada = False

    # Informa se a câmera abriu.
    def isOpened(self):
        return self.aberta

    # Entrega um quadro sintético.
    def read(self):
        return True, np.zeros((120, 220, 3), dtype=np.uint8)

    # Registra a liberação do dispositivo.
    def release(self):
        self.liberada = True


# A captura salva foto, recorte, relatório, evidência e respostas brutas, distinguindo o item não previsto.
def test_processar_captura_salva_e_compara(tmp_path):
    nota = validar_nota({"nota_id": "NF-CAM", "itens": [
        {"codigo": "FER-003", "quantidade": 1}
    ]}, CONFIG["de_para"])
    quadro = np.full((120, 220, 3), 255, dtype=np.uint8)
    pasta = nova_pasta_captura(tmp_path)
    relatorio, evidencia = processar_captura(quadro, nota, CONFIG, pasta, ClienteDuasChaves())
    assert relatorio["status"] == "divergente"
    assert {linha["classe"]: linha["situacao"] for linha in relatorio["linhas"]} == {
        "Wrench": "igual", "PipeWrench": "nao_previsto"
    }
    assert evidencia.ndim == 3
    assert {p.name for p in pasta.iterdir()} == {
        "quadro_original.jpg", "quadro_analisado.jpg", "imagem_anotada.jpg",
        "relatorio.json", "analise_caixas.json", "respostas_brutas.json"
    }
    assert json.loads((pasta / "analise_caixas.json").read_text(encoding="utf-8"))["modelo_caixas_id"] == CONFIG["modelo_caixas_id"]
    assert json.loads((pasta / "relatorio.json").read_text(encoding="utf-8")) == relatorio


# O detector recebe só o retângulo verde; os arquivos preservam ambas as versões.
def test_area_leitura_exclui_entorno(tmp_path):
    nota = validar_nota({"nota_id": "NF-CAM", "itens": [
        {"codigo": "FER-004", "quantidade": 1}
    ]}, CONFIG["de_para"])
    quadro = np.zeros((120, 220, 3), dtype=np.uint8)
    x1, y1, x2, y2 = limites_area(quadro)
    quadro[y1:y2, x1:x2] = 255
    cliente = ClienteRegistraRecorte()
    pasta = nova_pasta_captura(tmp_path)

    relatorio, _ = processar_captura(quadro, nota, CONFIG, pasta, cliente)

    assert relatorio["status"] == "conforme"
    assert cliente.quadro.shape[:2] == (y2 - y1, x2 - x1)
    assert np.all(cliente.quadro == 255)
    assert ler_imagem(pasta / "quadro_original.jpg").shape == quadro.shape
    assert ler_imagem(pasta / "quadro_analisado.jpg").shape[:2] == cliente.quadro.shape[:2]
    assert np.array_equal(cliente.quadro, quadro[y1:y2, x1:x2])
    assert AREA_LEITURA[0] > 0


# A borda aparece no mesmo lugar que a região enviada ao detector.
def test_previa_marca_area_correspondente():
    quadro = np.zeros((120, 220, 3), dtype=np.uint8)
    x1, y1, x2, y2 = limites_area(quadro)
    previa = marcar_area(quadro)
    assert previa.shape == quadro.shape
    assert tuple(previa[y1, x1]) == (65, 205, 35)
    assert np.array_equal(quadro, np.zeros_like(quadro))


# Duas capturas criam pastas independentes e não acumulam detecções.
def test_capturas_sao_independentes(tmp_path):
    nota = validar_nota({"nota_id": "NF-CAM", "itens": [
        {"codigo": "FER-003", "quantidade": 1},
        {"codigo": "FER-005", "quantidade": 1},
    ]}, CONFIG["de_para"])
    quadro = np.zeros((120, 220, 3), dtype=np.uint8)
    pastas = [nova_pasta_captura(tmp_path) for _ in range(2)]
    resultados = [processar_captura(quadro, nota, CONFIG, pasta, ClienteDuasChaves())[0]
                  for pasta in pastas]
    assert pastas[0] != pastas[1]
    assert all(resultado["status"] == "conforme" for resultado in resultados)
    assert all(sum(linha["detectado"] for linha in resultado["linhas"]) == 2
               for resultado in resultados)


# Uma nota inválida encerra antes de qualquer tentativa de abrir a webcam.
def test_nota_invalida_nao_abre_camera(tmp_path, monkeypatch, capsys):
    import camera

    nota = tmp_path / "nota.json"
    nota.write_text('{"itens": [{"codigo": "INEXISTENTE", "quantidade": 1}]}', encoding="utf-8")

    def nao_abrir(*args, **kwargs):
        raise AssertionError("A webcam não deveria ter sido aberta")

    monkeypatch.setattr(camera.cv2, "VideoCapture", nao_abrir)
    assert main(["--nota", str(nota)]) == 2
    assert "INEXISTENTE" in capsys.readouterr().err


# Câmera ausente produz erro claro e libera o dispositivo.
def test_camera_indisponivel(tmp_path, capsys):
    camera = CameraFalsa(aberta=False)
    assert executar_camera({}, CONFIG, captura_video=camera, base=tmp_path) == 2
    assert camera.liberada
    assert "Não foi possível abrir" in capsys.readouterr().err


# O laço captura com espaço, salva a conferência e encerra com Q.
def test_laco_camera_captura_e_sai(tmp_path, monkeypatch):
    import camera

    dispositivo = CameraFalsa()
    teclas = iter([32, 0, 0, ord("q")])
    monkeypatch.setattr(camera.cv2, "imshow", lambda *args: None)
    monkeypatch.setattr(camera.cv2, "waitKey", lambda *args: next(teclas))
    monkeypatch.setattr(camera.cv2, "destroyAllWindows", lambda: None)
    monkeypatch.setattr(camera, "processar_captura", lambda quadro, nota, config, pasta: (
        {"status": "erro", "nota_id": "NF", "linhas": [], "avisos": ["Falha de rede"],
         "descartadas": []}, quadro
    ))
    assert executar_camera({}, CONFIG, captura_video=dispositivo, base=tmp_path) == 0
    assert dispositivo.liberada
    assert len(list(tmp_path.glob("camera_*"))) == 1
