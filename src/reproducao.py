import json
from pathlib import Path

from detector import ErroDeteccao, criar_cliente

ARQUIVO_RESPOSTAS = "respostas_brutas.json"


# Repassa as chamadas ao Roboflow e guarda cada resposta bruta, na ordem, para reproduzir sem rede.
class ClienteGravador:
    # Recebe o config e, opcionalmente, um cliente pronto (real, falso ou de reprodução).
    def __init__(self, config, cliente=None):
        self.config = config
        self.cliente = cliente
        self.chamadas = []

    # Cria o cliente real só na primeira chamada, preservando as mensagens de erro do detector.
    def infer(self, imagem, model_id=None):
        if self.cliente is None:
            self.cliente = criar_cliente(self.config)
        resposta = self.cliente.infer(imagem, model_id=model_id)
        self.chamadas.append({"modelo_id": model_id, "forma_imagem": list(imagem.shape), "resposta": resposta})
        return resposta


# Grava as respostas brutas da execução na pasta de saída; sem chamadas, não grava nada.
def salvar_respostas(pasta, gravador):
    if not gravador.chamadas:
        return
    dados = {"modelo_id": gravador.config.get("model_id"),
             "modelo_caixas_id": gravador.config.get("modelo_caixas_id"),
             "chamadas": gravador.chamadas}
    (Path(pasta) / ARQUIVO_RESPOSTAS).write_text(
        json.dumps(dados, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )


# Lê as respostas gravadas numa pasta de execução (ou no próprio arquivo).
def carregar_respostas(origem):
    caminho = Path(origem)
    if caminho.is_dir():
        caminho = caminho / ARQUIVO_RESPOSTAS
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as erro:
        raise ErroDeteccao(
            f"Não foi possível ler {caminho} ({type(erro).__name__}) — informe uma pasta com {ARQUIVO_RESPOSTAS}"
        )
    if not isinstance(dados, dict) or not isinstance(dados.get("chamadas"), list):
        raise ErroDeteccao(f"{caminho.name} sem a lista \"chamadas\" — grave a execução de novo")
    return dados["chamadas"]


# Devolve as respostas gravadas, na mesma ordem, no lugar do Roboflow.
class ClienteReproducao:
    # Recebe as chamadas gravadas e a origem, usada nas mensagens de erro.
    def __init__(self, chamadas, origem):
        self.chamadas = list(chamadas)
        self.origem = origem
        self.indice = 0

    # Confere modelo e tamanho da imagem antes de devolver a resposta gravada.
    def infer(self, imagem, model_id=None):
        if self.indice >= len(self.chamadas):
            raise ErroDeteccao(
                f"A gravação em {self.origem} tem só {len(self.chamadas)} chamada(s) — "
                "reproduza com a mesma imagem e as mesmas opções da execução gravada"
            )
        chamada = self.chamadas[self.indice]
        self.indice += 1
        if chamada.get("modelo_id") != model_id or chamada.get("forma_imagem") != list(imagem.shape):
            raise ErroDeteccao(
                f"A chamada {self.indice} não corresponde à gravação em {self.origem} — "
                "use a mesma imagem e as mesmas opções (por exemplo, --sem-caixas) da execução gravada"
            )
        return chamada["resposta"]
