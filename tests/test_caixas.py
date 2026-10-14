import json
from pathlib import Path

import numpy as np

from camera import processar_captura
from caixas import associar_produtos
from conferir import analisar_quadro, conferir
from nota import validar_nota


RAIZ = Path(__file__).resolve().parent.parent
CONFIG = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))


# Simula respostas distintas dos dois modelos e registra o quadro recebido por cada um.
class ClienteDoisModelos:
    # Recebe listas de caixas e ferramentas já no formato bruto do Roboflow.
    def __init__(self, caixas, produtos, produtos_recortes=None):
        self.caixas = caixas
        self.produtos = produtos
        self.produtos_recortes = list(produtos_recortes or [])
        self.chamadas = []
        self.chamadas_produtos = 0

    # Escolhe a resposta pelo identificador do modelo, sem chamar a rede.
    def infer(self, imagem, model_id=None):
        self.chamadas.append((model_id, imagem.copy()))
        if model_id == "modelo-caixas-teste/1":
            return {"predictions": self.caixas}
        self.chamadas_produtos += 1
        if self.chamadas_produtos == 1:
            return {"predictions": self.produtos}
        return {"predictions": self.produtos_recortes.pop(0) if self.produtos_recortes else []}


# Monta uma predição sintética no formato do serviço.
def predicao(classe, x, y, largura=30, altura=30, confianca=0.9):
    return {"class": classe, "x": x, "y": y, "width": largura,
            "height": altura, "confidence": confianca}


# Converte coordenadas dos relatórios de câmera para a resposta bruta simulada.
def predicao_xyxy(classe, confianca, x1, y1, x2, y2):
    return predicao(classe, (x1 + x2) / 2, (y1 + y2) / 2,
                    x2 - x1, y2 - y1, confianca)


# Ativa o modo de dois modelos sem alterar a configuração real do projeto.
def config_dupla():
    return {**CONFIG, "modelo_caixas_id": "modelo-caixas-teste/1",
            "classes_caixas": ["Open Cardboard Box"]}


# Monta uma nota que pede dois martelos e uma chave de fenda.
def nota_teste():
    return validar_nota({"nota_id": "NF-CAIXAS", "itens": [
        {"codigo": "FER-004", "quantidade": 2},
        {"codigo": "FER-002", "quantidade": 1},
    ]}, CONFIG["de_para"])


# O modelo de caixas vê o quadro inteiro; o de ferramentas também examina cada abertura.
def test_duas_caixas_e_produto_fora():
    imagem = np.zeros((200, 300, 3), dtype=np.uint8)
    cliente = ClienteDoisModelos(
        [predicao("Open Cardboard Box", 65, 80, 100, 120),
         predicao("Open Cardboard Box", 210, 80, 100, 120)],
        [predicao("Claw hammer", 65, 80), predicao("Claw hammer", 210, 80),
         predicao("Flat Head Screwdriver", 280, 170)],
    )

    relatorio, evidencia, analise = analisar_quadro(imagem, nota_teste(), config_dupla(), cliente)

    assert relatorio["status"] == "conforme"
    assert analise["total_produtos"] == 3
    assert [grupo["produtos"][0]["classe"] for grupo in analise["caixas"]] == ["Hammer", "Hammer"]
    assert [produto["classe"] for produto in analise["produtos_fora"]] == ["Screwdriver"]
    assert [chamada[0] for chamada in cliente.chamadas] == [
        "modelo-caixas-teste/1", CONFIG["model_id"], CONFIG["model_id"], CONFIG["model_id"]
    ]
    assert all(np.array_equal(chamada[1], imagem) for chamada in cliente.chamadas[:2])
    assert all(chamada[1].shape[0] < imagem.shape[0] for chamada in cliente.chamadas[2:])
    assert evidencia.ndim == 3
    assert set(relatorio) == {"nota_id", "imagem", "status", "linhas", "descartadas", "avisos",
                              "modelo_id", "limiar_confianca", "gerado_em"}


# O recorte interno corrige uma classe errada no quadro geral sem duplicar a ferramenta.
def test_recorte_interno_substitui_deteccao_global_da_caixa():
    imagem = np.zeros((300, 400, 3), dtype=np.uint8)
    cliente = ClienteDoisModelos(
        [predicao("Open Cardboard Box", 180, 150, 260, 240)],
        [predicao("Mallet", 180, 150, 200, 180),
         predicao("Flat Head Screwdriver", 365, 260)],
        [[predicao("Claw hammer", 120, 100, 80, 60)]],
    )
    nota = validar_nota({"nota_id": "NF-RECORTE", "itens": [
        {"codigo": "FER-004", "quantidade": 1},
        {"codigo": "FER-002", "quantidade": 1},
    ]}, CONFIG["de_para"])

    relatorio, _, analise = analisar_quadro(imagem, nota, config_dupla(), cliente)

    assert relatorio["status"] == "conforme"
    assert [item["classe"] for item in analise["caixas"][0]["produtos"]] == ["Hammer"]
    assert [item["classe"] for item in analise["produtos_fora"]] == ["Screwdriver"]
    assert analise["recortes_internos"][0]["produtos_aceitos"] == 1
    assert cliente.chamadas[2][1].shape == (188, 260, 3)


# A ausência de caixa não impede contar ferramentas visíveis fora dela.
def test_sem_caixa_todos_os_produtos_ficam_fora():
    cliente = ClienteDoisModelos([], [predicao("Claw hammer", 65, 80)])
    relatorio, _, analise = analisar_quadro(
        np.zeros((200, 300, 3), dtype=np.uint8), nota_teste(), config_dupla(), cliente
    )
    assert relatorio["status"] == "divergente"
    assert analise["caixas"] == []
    assert [item["classe"] for item in analise["produtos_fora"]] == ["Hammer"]
    assert "Nenhuma caixa aberta" in relatorio["avisos"][0]


# Uma caixa fraca e uma ferramenta fraca não entram na contagem ou associação.
def test_limiar_atual_vale_para_ambos_modelos():
    cliente = ClienteDoisModelos(
        [predicao("Open Cardboard Box", 65, 80, 100, 120, confianca=0.59)],
        [predicao("Claw hammer", 65, 80, confianca=0.59),
         predicao("Flat Head Screwdriver", 280, 170, confianca=0.73)],
    )
    relatorio, _, analise = analisar_quadro(
        np.zeros((200, 300, 3), dtype=np.uint8), nota_teste(), config_dupla(), cliente
    )
    assert config_dupla()["limiar_confianca"] == 0.6
    assert analise["caixas"] == []
    assert analise["caixas_ignoradas"][0]["motivo"] == "abaixo_do_limiar"
    assert [item["classe"] for item in analise["produtos_fora"]] == ["Screwdriver"]
    assert relatorio["descartadas"] == [{"classe": "Hammer", "confianca": 0.59}]


# Um produto no cruzamento de duas caixas pertence só à menor delas.
def test_caixas_sobrepostas_nao_duplicam_produto():
    caixas = [
        {"classe": "Open Cardboard Box", "confianca": 0.9, "caixa_xyxy": [10, 10, 200, 180]},
        {"classe": "Open Cardboard Box", "confianca": 0.8, "caixa_xyxy": [50, 50, 100, 100]},
    ]
    produtos = [{"classe": "Hammer", "confianca": 0.9, "caixa_xyxy": [65, 65, 80, 80]}]
    analise = associar_produtos(produtos, caixas, config_dupla())
    assert analise["total_produtos"] == 1
    assert [len(grupo["produtos"]) for grupo in analise["caixas"]] == [0, 1]


# Falha do modelo de caixas não pode virar conferência conforme por omissão.
def test_falha_modelo_caixas_vira_erro():
    # Simula um cliente que cai apenas na primeira chamada.
    class ClienteFalhaCaixas:
        # A chamada deve produzir erro técnico em vez de contagem presumida.
        def infer(self, imagem, model_id=None):
            raise ConnectionError("falha simulada")

    relatorio, _, analise = analisar_quadro(
        np.zeros((200, 300, 3), dtype=np.uint8), nota_teste(), config_dupla(), ClienteFalhaCaixas()
    )
    assert relatorio["status"] == "erro"
    assert analise is None


# A câmera grava a análise separada e mantém o relatório com os campos anteriores.
def test_camera_salva_analise_por_caixa(tmp_path):
    cliente = ClienteDoisModelos(
        [predicao("Open Cardboard Box", 65, 80, 100, 120)],
        [predicao("Claw hammer", 65, 80)],
    )
    relatorio, _ = processar_captura(
        np.zeros((200, 300, 3), dtype=np.uint8), nota_teste(), config_dupla(), tmp_path, cliente
    )
    salvo = json.loads((tmp_path / "analise_caixas.json").read_text(encoding="utf-8"))
    assert salvo["modelo_caixas_id"] == "modelo-caixas-teste/1"
    assert salvo["total_produtos"] == 1
    assert relatorio["status"] == "divergente"
    assert (tmp_path / "imagem_anotada.jpg").exists()
    assert (tmp_path / "caixa_1_interior.jpg").exists()


# A conferência por foto também grava a distribuição por caixa sem mudar o relatório.
def test_foto_salva_analise_por_caixa(tmp_path):
    cliente = ClienteDoisModelos(
        [predicao("Open Cardboard Box", 65, 80, 100, 120)],
        [predicao("Claw hammer", 65, 80)],
    )
    caminho_nota = tmp_path / "nota.json"
    caminho_nota.write_text(json.dumps({"nota_id": "NF-CAIXA", "itens": [
        {"codigo": "FER-004", "quantidade": 1}
    ]}), encoding="utf-8")
    relatorio, pasta = conferir(
        RAIZ / "imagens" / "teste" / "Img 8.jpeg", caminho_nota,
        tmp_path / "saida", config_dupla(), cliente
    )
    assert relatorio["status"] == "conforme"
    assert (pasta / "analise_caixas.json").exists()
    assert (pasta / "relatorio.json").exists()
    assert (pasta / "caixa_1_interior.jpg").exists()


# A conferência completa deixa de contar três vezes a mesma ferramenta da captura observada.
def test_captura_com_fragmentos_conta_um_de_cada():
    cliente = ClienteDoisModelos([], [
        predicao_xyxy("Flat Head Screwdriver", 0.9986, 36, 273, 472, 341),
        predicao_xyxy("Flat Head Screwdriver", 0.9959, 40, 327, 468, 363),
        predicao_xyxy("Claw hammer", 0.9943, 46, 0, 419, 80),
        predicao_xyxy("Claw hammer", 0.9836, 64, 44, 424, 149),
        predicao_xyxy("Flat Head Screwdriver", 0.9820, 35, 281, 217, 321),
        predicao_xyxy("Claw hammer", 0.7014, 422, 0, 480, 192),
    ])
    nota = validar_nota({"nota_id": "NF-CAPTURA", "itens": [
        {"codigo": "FER-004", "quantidade": 1},
        {"codigo": "FER-002", "quantidade": 1},
    ]}, CONFIG["de_para"])
    relatorio, _, analise = analisar_quadro(
        np.zeros((365, 480, 3), dtype=np.uint8), nota, config_dupla(), cliente
    )
    assert relatorio["status"] == "conforme"
    assert {linha["classe"]: linha["detectado"] for linha in relatorio["linhas"]} == {
        "Hammer": 1, "Screwdriver": 1
    }
    assert analise["total_produtos"] == 2
    assert len(analise["deteccoes_suprimidas"]) == 4
    assert any("4 detecção" in aviso for aviso in relatorio["avisos"])
