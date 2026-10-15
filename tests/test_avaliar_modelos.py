import json

import pytest

from avaliar_modelos import avaliar_imagem, avaliar_modelo, carregar_gabarito, contar_deteccoes


# Um candidato usado no teste devolve uma resposta realista sem chamar a rede.
class ClienteFalso:
    # Simula uma detecção correta, uma ferramenta extra e uma classe incerta.
    def infer(self, imagem, model_id=None):
        return {"predictions": [
            {"x": 60, "y": 60, "width": 20, "height": 20, "confidence": 0.9, "class": "adjustable_wrench"},
            {"x": 120, "y": 60, "width": 20, "height": 20, "confidence": 0.8, "class": "pipe_wrench"},
            {"x": 180, "y": 60, "width": 20, "height": 20, "confidence": 0.3, "class": "Hammer"},
        ]}


# Confere correspondência exata, faltas, excessos e acertos parciais.
def test_metricas_de_contagem():
    resultado = avaliar_imagem({"Wrench": 2, "Pliers": 1}, {"Wrench": 1, "Hammer": 1})
    assert resultado == {
        "contagem_exata": False, "itens_corretos": 1, "faltas": 2, "excessos": 1,
        "detalhe_faltas": {"Pliers": 1, "Wrench": 1}, "detalhe_excessos": {"Hammer": 1},
    }


# Uma classe desconhecida precisa aparecer para revisão e não entrar na contagem.
def test_mapeamento_nao_supoe_classe():
    deteccoes = [{"classe": "adjustable_wrench", "confianca": 0.9},
                 {"classe": "pipe_wrench", "confianca": 0.8},
                 {"classe": "Hammer", "confianca": 0.3}]
    contagens, desconhecidas = contar_deteccoes(deteccoes, {"adjustable_wrench": "Wrench"}, 0.5)
    assert contagens == {"Wrench": 1}
    assert desconhecidas == {"pipe_wrench": 1}


# Gabarito parcial é permitido; nomes desconhecidos e booleanos são rejeitados.
def test_gabarito_parcial_e_validacao(tmp_path):
    imagens = [tmp_path / "a.jpg", tmp_path / "b.jpg"]
    caminho = tmp_path / "gabarito.json"
    caminho.write_text(json.dumps({"a.jpg": {"Wrench": 1}}), encoding="utf-8")
    assert carregar_gabarito(caminho, imagens) == {"a.jpg": {"Wrench": 1}}
    caminho.write_text(json.dumps({"c.jpg": {}}), encoding="utf-8")
    with pytest.raises(ValueError, match="nomes incorretos"):
        carregar_gabarito(caminho, imagens)
    caminho.write_text(json.dumps({"a.jpg": {"Wrench": True}, "b.jpg": {}}), encoding="utf-8")
    with pytest.raises(ValueError, match="Contagem inválida"):
        carregar_gabarito(caminho, imagens)


# A avaliação preserva a resposta bruta e distingue erro de classe não mapeada.
def test_avaliacao_com_cliente_falso(tmp_path):
    imagem = tmp_path / "foto.jpg"
    imagem.write_bytes((__import__("pathlib").Path(__file__).resolve().parent.parent /
                        "imagens/teste/Img 16.jpg").read_bytes())
    resumo = avaliar_modelo(
        "modelo-teste/1", [imagem], {"foto.jpg": {"Wrench": 1}},
        {"adjustable_wrench": "Wrench"}, {"limiar_confianca": 0.5}, ClienteFalso(), tmp_path / "saida",
    )
    assert resumo["imagens_avaliadas"] == 1
    assert resumo["imagens_com_contagem_exata"] == 0
    assert resumo["imagens"][0]["classes_nao_mapeadas"] == {"pipe_wrench": 1}
    assert (tmp_path / "saida" / "resposta_modelo-teste_1.json").exists()


# Devolve o mesmo martelo em duas caixas quase iguais, como na dupla contagem observada.
class ClienteMartelinhoDuplo:
    # Simula duas predições muito sobrepostas da mesma ferramenta.
    def infer(self, imagem, model_id=None):
        return {"predictions": [
            {"x": 100, "y": 100, "width": 80, "height": 60, "confidence": 0.95, "class": "Claw hammer"},
            {"x": 104, "y": 102, "width": 80, "height": 60, "confidence": 0.85, "class": "Claw hammer"},
        ]}


# O fluxo real aplica aliases e consolidação; o bruto mede o modelo como veio.
def test_fluxo_real_consolida_e_traduz(tmp_path):
    imagem = tmp_path / "foto.jpg"
    imagem.write_bytes((__import__("pathlib").Path(__file__).resolve().parent.parent /
                        "imagens/teste/Img 16.jpg").read_bytes())
    config = {"limiar_confianca": 0.6, "aliases_classes": {"Claw hammer": "Hammer"}}
    gabarito = {"foto.jpg": {"Hammer": 1}}
    bruto = avaliar_modelo("modelo-teste/1", [imagem], gabarito, {}, config,
                           ClienteMartelinhoDuplo(), tmp_path / "saida")
    real = avaliar_modelo("modelo-teste/1", [imagem], gabarito, {}, config,
                          ClienteMartelinhoDuplo(), tmp_path / "saida", fluxo_real=True)
    assert bruto["fluxo"] == "bruto" and bruto["imagens_com_contagem_exata"] == 0
    assert bruto["imagens"][0]["classes_nao_mapeadas"] == {"Claw hammer": 2}
    assert real["fluxo"] == "real" and real["imagens_com_contagem_exata"] == 1
    assert real["imagens"][0]["deteccoes_suprimidas"] == 1
    assert (tmp_path / "saida" / "modelo-teste_1_fluxo_real.json").exists()
    assert (tmp_path / "saida" / "modelo-teste_1.json").exists()
