import numpy as np

from posprocessamento import consolidar_deteccoes


# Monta uma detecção sintética usando apenas a geometria do erro observado.
def deteccao(classe, confianca, caixa):
    return {"classe": classe, "confianca": confianca, "caixa_xyxy": caixa}


# As seis caixas da captura real representam um martelo e uma chave de fenda.
def test_fragmentos_da_captura_real_viram_dois_itens():
    imagem = np.zeros((365, 480, 3), dtype=np.uint8)
    brutas = [
        deteccao("Screwdriver", 0.9986, [36, 273, 472, 341]),
        deteccao("Screwdriver", 0.9959, [40, 327, 468, 363]),
        deteccao("Hammer", 0.9943, [46, 0, 419, 80]),
        deteccao("Hammer", 0.9836, [64, 44, 424, 149]),
        deteccao("Screwdriver", 0.9820, [35, 281, 217, 321]),
        deteccao("Hammer", 0.7014, [422, 0, 480, 192]),
    ]
    finais, suprimidas = consolidar_deteccoes(brutas, imagem, 0.6)
    assert sorted(d["classe"] for d in finais) == ["Hammer", "Screwdriver"]
    assert len(suprimidas) == 4
    assert {d["motivo"] for d in suprimidas} == {
        "caixa_repetida_ou_parte_do_mesmo_objeto", "fragmento_no_canto_da_imagem"
    }


# Uma segunda captura tinha a ferramenta longa quebrada em duas caixas vizinhas.
def test_partes_alinhadas_da_mesma_chave_se_unem():
    imagem = np.zeros((365, 480, 3), dtype=np.uint8)
    brutas = [
        deteccao("Hammer", 0.9953, [15, 13, 480, 136]),
        deteccao("Hammer", 0.9935, [22, 88, 338, 179]),
        deteccao("Screwdriver", 0.9112, [0, 301, 153, 364]),
        deteccao("Screwdriver", 0.7999, [163, 305, 472, 363]),
    ]
    finais, suprimidas = consolidar_deteccoes(brutas, imagem, 0.6)
    assert sorted(d["classe"] for d in finais) == ["Hammer", "Screwdriver"]
    assert len(suprimidas) == 2


# Dois objetos reais separados não podem ser reduzidos a uma única contagem.
def test_duas_ferramentas_separadas_continuam_distintas():
    imagem = np.zeros((300, 500, 3), dtype=np.uint8)
    brutas = [
        deteccao("Hammer", 0.95, [20, 30, 190, 100]),
        deteccao("Hammer", 0.93, [260, 30, 430, 100]),
        deteccao("Hammer", 0.91, [20, 170, 190, 240]),
    ]
    finais, suprimidas = consolidar_deteccoes(brutas, imagem, 0.6)
    assert len(finais) == 3
    assert suprimidas == []


# Dois itens inteiros de tamanho parecido podem estar próximos na mesma linha.
def test_duas_ferramentas_alinhadas_de_tamanho_parecido_continuam_distintas():
    imagem = np.zeros((300, 500, 3), dtype=np.uint8)
    brutas = [
        deteccao("Screwdriver", 0.95, [20, 100, 200, 140]),
        deteccao("Screwdriver", 0.93, [210, 101, 390, 141]),
    ]
    finais, suprimidas = consolidar_deteccoes(brutas, imagem, 0.6)
    assert len(finais) == 2
    assert suprimidas == []


# Uma detecção única no canto e as detecções fracas continuam disponíveis.
def test_canto_isolado_e_descartadas_por_limiar_sao_preservados():
    imagem = np.zeros((300, 500, 3), dtype=np.uint8)
    brutas = [
        deteccao("Hammer", 0.9, [420, 0, 500, 100]),
        deteccao("Hammer", 0.4, [20, 100, 190, 150]),
    ]
    finais, suprimidas = consolidar_deteccoes(brutas, imagem, 0.6)
    assert finais == brutas
    assert suprimidas == []
