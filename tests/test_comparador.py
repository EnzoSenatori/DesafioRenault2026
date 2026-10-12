from comparador import AVISO_SEM_DETECCAO, comparar, resultado_erro

CONFIG = {
    "limiar_confianca": 0.5,
    "classes_ignoradas": ["Fasteners"],
    "de_para": {"FER-001": "Pliers", "FER-002": "Screwdriver", "FER-003": "Wrench", "FER-004": "Hammer"},
    "nomes_exibicao": {"Pliers": "Alicate", "Screwdriver": "Chave de fenda", "Wrench": "Chave inglesa", "Hammer": "Martelo"},
}


# Monta uma nota já validada a partir de pares (classe, quantidade)
def nota(*pares):
    codigo = {classe: cod for cod, classe in CONFIG["de_para"].items()}
    return {"nota_id": "NF", "itens": [
        {"codigo": codigo[c], "descricao": "", "classe": c, "quantidade": q} for c, q in pares
    ]}


# Gera detecções simuladas de uma classe, todas com a mesma confiança
def det(classe, n=1, confianca=0.9):
    return [{"classe": classe, "confianca": confianca, "caixa_xyxy": [0, 0, 1, 1]} for _ in range(n)]


# Indexa as linhas do resultado pela classe
def por_classe(resultado):
    return {linha["classe"]: linha for linha in resultado["linhas"]}


# Verifica: igualdade conforme
def test_igualdade_conforme():
    r = comparar(nota(("Pliers", 2), ("Hammer", 1)), det("Pliers", 2) + det("Hammer"), CONFIG)
    assert r["status"] == "conforme"
    assert all(l["situacao"] == "igual" and l["delta"] == 0 for l in r["linhas"])
    assert r["avisos"] == []


# Verifica: falta
def test_falta():
    r = comparar(nota(("Pliers", 2)), det("Pliers", 1), CONFIG)
    linha = por_classe(r)["Pliers"]
    assert (linha["esperado"], linha["detectado"], linha["delta"], linha["situacao"]) == (2, 1, -1, "falta")
    assert linha["codigo"] == "FER-001" and linha["item"] == "Alicate"
    assert r["status"] == "divergente"


# Verifica: excesso
def test_excesso():
    r = comparar(nota(("Wrench", 1)), det("Wrench", 3), CONFIG)
    linha = por_classe(r)["Wrench"]
    assert (linha["delta"], linha["situacao"]) == (2, "excesso")
    assert r["status"] == "divergente"


# Verifica: item nao previsto
def test_item_nao_previsto():
    r = comparar(nota(("Pliers", 1)), det("Pliers") + det("Hammer"), CONFIG)
    linha = por_classe(r)["Hammer"]
    assert (linha["esperado"], linha["detectado"], linha["situacao"]) == (0, 1, "nao_previsto")
    assert linha["codigo"] == "FER-004"
    assert [l["classe"] for l in r["linhas"]] == ["Pliers", "Hammer"]
    assert r["status"] == "divergente"


# Verifica: nenhuma deteccao com itens gera aviso
def test_nenhuma_deteccao_com_itens_gera_aviso():
    r = comparar(nota(("Pliers", 1)), [], CONFIG)
    assert r["status"] == "divergente"
    assert por_classe(r)["Pliers"]["situacao"] == "falta"
    assert r["avisos"] == [AVISO_SEM_DETECCAO]


# Verifica: so descartadas tambem gera aviso
def test_so_descartadas_tambem_gera_aviso():
    r = comparar(nota(("Pliers", 1)), det("Pliers", confianca=0.3), CONFIG)
    assert r["avisos"] == [AVISO_SEM_DETECCAO]
    assert r["descartadas"] == [{"classe": "Pliers", "confianca": 0.3}]


# Verifica: classe ignorada nao conta nem vira linha
def test_classe_ignorada_nao_conta_nem_vira_linha():
    r = comparar(nota(("Pliers", 1)), det("Pliers") + det("Fasteners", 4) + det("Fasteners", confianca=0.2), CONFIG)
    assert r["status"] == "conforme"
    assert "Fasteners" not in por_classe(r)
    assert r["descartadas"] == []


# Verifica: abaixo do limiar nao conta
def test_abaixo_do_limiar_nao_conta():
    r = comparar(nota(("Pliers", 1)), det("Pliers") + det("Pliers", confianca=0.49), CONFIG)
    assert por_classe(r)["Pliers"]["detectado"] == 1
    assert r["status"] == "conforme"
    assert r["descartadas"] == [{"classe": "Pliers", "confianca": 0.49}]


# Verifica: limiar exato conta
def test_limiar_exato_conta():
    r = comparar(nota(("Pliers", 1)), det("Pliers", confianca=0.5), CONFIG)
    assert r["status"] == "conforme"


# Verifica: linhas repetidas da nota somadas no esperado
def test_linhas_repetidas_da_nota_somadas_no_esperado():
    n = {"nota_id": "NF", "itens": [
        {"codigo": "FER-001", "descricao": "", "classe": "Pliers", "quantidade": 1},
        {"codigo": "FER-001", "descricao": "", "classe": "Pliers", "quantidade": 2},
    ]}
    r = comparar(n, det("Pliers", 3), CONFIG)
    assert por_classe(r)["Pliers"]["esperado"] == 3
    assert r["status"] == "conforme"


# Verifica: erro nunca e conforme
def test_erro_nunca_e_conforme():
    r = resultado_erro("Falha na chamada ao Roboflow")
    assert r["status"] == "erro"
    assert r["linhas"] == []
