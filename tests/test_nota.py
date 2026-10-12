import json

import pytest

from nota import ErroEntrada, carregar_nota, validar_nota

DE_PARA = {"FER-001": "Pliers", "FER-002": "Screwdriver", "FER-003": "Wrench", "FER-004": "Hammer"}


# Monta uma nota mínima com os itens informados
def nota_com(*itens):
    return {"nota_id": "NF-TESTE", "fornecedor": "Teste", "itens": list(itens)}


# Verifica: nota valida associa classe
def test_nota_valida_associa_classe():
    nota = validar_nota(nota_com({"codigo": "FER-001", "descricao": "Alicate", "quantidade": 2}), DE_PARA)
    assert nota["itens"] == [{"codigo": "FER-001", "descricao": "Alicate", "classe": "Pliers", "quantidade": 2}]


# Verifica: linhas repetidas sao somadas
def test_linhas_repetidas_sao_somadas():
    nota = validar_nota(nota_com(
        {"codigo": "FER-001", "quantidade": 2},
        {"codigo": "FER-002", "quantidade": 1},
        {"codigo": "FER-001", "quantidade": 3},
    ), DE_PARA)
    assert {i["codigo"]: i["quantidade"] for i in nota["itens"]} == {"FER-001": 5, "FER-002": 1}


# Verifica: codigo tratado como texto
def test_codigo_tratado_como_texto():
    nota = validar_nota(nota_com({"codigo": 7, "quantidade": 1}), {"7": "Hammer"})
    assert nota["itens"][0]["codigo"] == "7"


# Verifica: codigo fora do de para gera erro
def test_codigo_fora_do_de_para_gera_erro():
    with pytest.raises(ErroEntrada, match="FER-999"):
        validar_nota(nota_com({"codigo": "FER-999", "quantidade": 1}), DE_PARA)


# Verifica: quantidade invalida gera erro
@pytest.mark.parametrize("quantidade", [0, -1, 1.5, 2.0, "2", None, True])
def test_quantidade_invalida_gera_erro(quantidade):
    with pytest.raises(ErroEntrada, match="Quantidade inválida"):
        validar_nota(nota_com({"codigo": "FER-001", "quantidade": quantidade}), DE_PARA)


# Verifica: codigo ausente gera erro
def test_codigo_ausente_gera_erro():
    with pytest.raises(ErroEntrada, match="código"):
        validar_nota(nota_com({"quantidade": 1}), DE_PARA)


# Verifica: sem lista de itens gera erro
def test_sem_lista_de_itens_gera_erro():
    with pytest.raises(ErroEntrada, match="itens"):
        validar_nota({"nota_id": "NF"}, DE_PARA)


# Verifica: json malformado gera erro
def test_json_malformado_gera_erro(tmp_path):
    arquivo = tmp_path / "nota.json"
    arquivo.write_text('{"itens": [', encoding="utf-8")
    with pytest.raises(ErroEntrada, match="não é um JSON válido"):
        carregar_nota(arquivo, DE_PARA)


# Verifica: arquivo inexistente gera erro
def test_arquivo_inexistente_gera_erro(tmp_path):
    with pytest.raises(ErroEntrada, match="não encontrada"):
        carregar_nota(tmp_path / "nao_existe.json", DE_PARA)


# Verifica: carrega do arquivo
def test_carrega_do_arquivo(tmp_path):
    arquivo = tmp_path / "nota.json"
    arquivo.write_text(json.dumps(nota_com({"codigo": "FER-004", "quantidade": 1})), encoding="utf-8")
    assert carregar_nota(arquivo, DE_PARA)["itens"][0]["classe"] == "Hammer"
