import os
from pathlib import Path

import cv2
import numpy as np
from dotenv import load_dotenv
from inference_sdk import InferenceConfiguration, InferenceHTTPClient
from inference_sdk.http.errors import HTTPCallErrorError

RAIZ = Path(__file__).resolve().parent.parent

# Confiança mínima pedida ao servidor: baixa, para o relatório enxergar as descartadas
CONFIANCA_SERVIDOR = 0.1

CAMPOS_PREDICAO = ("x", "y", "width", "height", "confidence", "class")


# Falha técnica na detecção: chave, rede, imagem ou resposta inesperada
class ErroDeteccao(Exception):
    pass


# Lê a imagem em BGR, aceitando caminhos com espaços ou acentos no Windows
def ler_imagem(caminho):
    caminho = Path(caminho)
    if not caminho.is_file():
        raise ErroDeteccao(f"Imagem não encontrada: {caminho} — confira o caminho informado em --imagem")
    imagem = cv2.imdecode(np.fromfile(str(caminho), dtype=np.uint8), cv2.IMREAD_COLOR)
    if imagem is None:
        raise ErroDeteccao(f"Imagem ilegível: {caminho.name} — use um arquivo JPG ou PNG válido")
    return imagem


# Converte a resposta bruta do Roboflow (centro, largura, altura) para o formato interno
def converter_resposta(resposta):
    if not isinstance(resposta, dict) or not isinstance(resposta.get("predictions"), list):
        raise ErroDeteccao("Resposta do Roboflow sem a lista \"predictions\" — formato inesperado")
    deteccoes = []
    for predicao in resposta["predictions"]:
        faltando = [campo for campo in CAMPOS_PREDICAO if campo not in predicao]
        if faltando:
            raise ErroDeteccao(f"Predição do Roboflow sem os campos {faltando} — formato inesperado")
        x, y = float(predicao["x"]), float(predicao["y"])
        meia_l, meia_a = float(predicao["width"]) / 2, float(predicao["height"]) / 2
        deteccoes.append({
            "classe": str(predicao["class"]),
            "confianca": float(predicao["confidence"]),
            "caixa_xyxy": [x - meia_l, y - meia_a, x + meia_l, y + meia_a],
        })
    return deteccoes


# Cria o cliente do Roboflow com a chave do .env, sem nunca exibi-la
def criar_cliente(config):
    load_dotenv(RAIZ / ".env")
    chave = os.getenv("ROBOFLOW_API_KEY")
    if not chave:
        raise ErroDeteccao("Chave do Roboflow ausente — defina ROBOFLOW_API_KEY no arquivo .env")
    cliente = InferenceHTTPClient(api_url=config["api_url"], api_key=chave)
    cliente.configure(InferenceConfiguration(
        confidence_threshold=CONFIANCA_SERVIDOR,
        api_key_transport="header",
    ))
    return cliente


# Roda o modelo indicado num quadro BGR e devolve as detecções no formato interno.
def detectar(imagem_bgr, config, cliente=None, modelo_id=None, aliases=None):
    try:
        cliente = cliente or criar_cliente(config)
        resposta = cliente.infer(imagem_bgr, model_id=modelo_id or config["model_id"])
    except ErroDeteccao:
        raise
    except HTTPCallErrorError as erro:
        if erro.status_code in (401, 403):
            raise ErroDeteccao("Chave do Roboflow recusada — confira ROBOFLOW_API_KEY no arquivo .env")
        raise ErroDeteccao(f"Roboflow respondeu com erro HTTP {erro.status_code} — tente de novo ou use a saída de reserva")
    except Exception as erro:
        raise ErroDeteccao(
            f"Falha na chamada ao Roboflow ({type(erro).__name__}) — verifique a internet ou use a saída de reserva"
        )
    deteccoes = converter_resposta(resposta)
    aliases = config.get("aliases_classes", {}) if aliases is None else aliases
    for deteccao in deteccoes:
        deteccao["classe"] = aliases.get(deteccao["classe"], deteccao["classe"])
    return deteccoes
