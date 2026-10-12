import json
from collections import Counter
from pathlib import Path


# Erro de entrada: nota inválida, ilegível ou com código desconhecido
class ErroEntrada(Exception):
    pass


# Valida e normaliza o código do item, sempre tratado como texto
def _validar_codigo(item, posicao):
    codigo = item.get("codigo")
    if isinstance(codigo, bool) or not isinstance(codigo, (str, int)):
        raise ErroEntrada(f"Item {posicao} da nota sem código válido — informe \"codigo\" como texto")
    codigo = str(codigo).strip()
    if not codigo:
        raise ErroEntrada(f"Item {posicao} da nota com código vazio — preencha \"codigo\"")
    return codigo


# Valida que a quantidade é um inteiro positivo
def _validar_quantidade(item, posicao, codigo):
    quantidade = item.get("quantidade")
    if isinstance(quantidade, bool) or not isinstance(quantidade, int) or quantidade <= 0:
        raise ErroEntrada(
            f"Quantidade inválida no item {posicao} ({codigo}): {quantidade!r} — use um inteiro positivo"
        )
    return quantidade


# Lê o JSON da nota a partir do arquivo, com erro explícito se faltar ou estiver malformado
def ler_arquivo_nota(caminho):
    caminho = Path(caminho)
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except FileNotFoundError:
        raise ErroEntrada(f"Nota fiscal não encontrada: {caminho} — confira o caminho informado em --nota")
    except json.JSONDecodeError as erro:
        raise ErroEntrada(
            f"Nota fiscal {caminho.name} não é um JSON válido (linha {erro.lineno}, coluna {erro.colno}) — corrija o arquivo"
        )


# Valida a nota já carregada, soma linhas repetidas e associa cada código à classe do modelo
def validar_nota(dados, de_para):
    if not isinstance(dados, dict):
        raise ErroEntrada("A nota deve ser um objeto JSON com \"nota_id\" e \"itens\"")
    itens = dados.get("itens")
    if not isinstance(itens, list):
        raise ErroEntrada("A nota não tem a lista \"itens\" — inclua os itens recebidos")

    quantidades = Counter()
    descricoes = {}
    for posicao, item in enumerate(itens, start=1):
        if not isinstance(item, dict):
            raise ErroEntrada(f"Item {posicao} da nota não é um objeto — use {{\"codigo\", \"descricao\", \"quantidade\"}}")
        codigo = _validar_codigo(item, posicao)
        quantidade = _validar_quantidade(item, posicao, codigo)
        if codigo not in de_para:
            raise ErroEntrada(
                f"Código {codigo} (item {posicao}) não está no de_para do config.json — cadastre-o ou corrija a nota"
            )
        quantidades[codigo] += quantidade
        descricoes.setdefault(codigo, item.get("descricao", ""))

    return {
        "nota_id": str(dados.get("nota_id", "")),
        "fornecedor": dados.get("fornecedor", ""),
        "itens": [
            {"codigo": codigo, "descricao": descricoes[codigo], "classe": de_para[codigo], "quantidade": quantidade}
            for codigo, quantidade in quantidades.items()
        ],
    }


# Lê e valida a nota do arquivo em um só passo
def carregar_nota(caminho, de_para):
    return validar_nota(ler_arquivo_nota(caminho), de_para)
