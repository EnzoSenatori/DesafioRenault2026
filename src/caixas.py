from PIL import ImageDraw

from comparador import filtrar_deteccoes
from detector import detectar
from posprocessamento import consolidar_deteccoes
from visualizacao import bgr_para_pil, carregar_fonte, pil_para_bgr, salvar_jpg


# Mantém só as caixas das classes configuradas e acima do limiar já aprovado.
def filtrar_caixas(deteccoes, config):
    classes = set(config["classes_caixas"])
    limiar = config["limiar_confianca"]
    return [deteccao for deteccao in deteccoes
            if deteccao["classe"] in classes and deteccao["confianca"] >= limiar]


# Verifica se o centro do produto está dentro da caixa detectada.
def produto_dentro(produto, caixa):
    x1, y1, x2, y2 = produto["caixa_xyxy"]
    centro_x, centro_y = (x1 + x2) / 2, (y1 + y2) / 2
    esquerda, topo, direita, fundo = caixa["caixa_xyxy"]
    return esquerda <= centro_x <= direita and topo <= centro_y <= fundo


# Associa cada produto a uma única caixa; os demais ficam na lista externa.
def associar_produtos(produtos, caixas, config):
    aceitos, _ = filtrar_deteccoes(
        produtos, config["limiar_confianca"], set(config.get("classes_ignoradas", []))
    )
    grupos = [{"indice": indice, "classe": caixa["classe"],
               "confianca": caixa["confianca"], "caixa_xyxy": caixa["caixa_xyxy"],
               "produtos": []}
              for indice, caixa in enumerate(caixas, start=1)]
    fora = []
    for produto in aceitos:
        candidatas = [grupo for grupo in grupos if produto_dentro(produto, grupo)]
        if not candidatas:
            fora.append(produto)
            continue
        menor = min(candidatas, key=lambda grupo: (
            (grupo["caixa_xyxy"][2] - grupo["caixa_xyxy"][0]) *
            (grupo["caixa_xyxy"][3] - grupo["caixa_xyxy"][1])
        ))
        menor["produtos"].append(produto)
    return {"modelo_caixas_id": config["modelo_caixas_id"],
            "modelo_produtos_id": config["model_id"],
            "limiar_confianca": config["limiar_confianca"],
            "caixas": grupos, "produtos_fora": fora,
            "total_produtos": len(aceitos)}


# Recorta a parte visível da abertura, deixando de fora a maior parte da parede frontal.
def recortar_interior(imagem_bgr, caixa):
    altura, largura = imagem_bgr.shape[:2]
    esquerda, topo, direita, fundo = caixa["caixa_xyxy"]
    x1, y1 = max(0, int(esquerda)), max(0, int(topo))
    x2 = min(largura, int(direita + 0.999))
    y2 = min(altura, int(topo + 0.78 * (fundo - topo) + 0.999))
    if x2 - x1 < 64 or y2 - y1 < 64:
        return None, None
    return imagem_bgr[y1:y2, x1:x2].copy(), (x1, y1, x2, y2)


# Traduz a caixa de uma detecção no recorte para as coordenadas da imagem analisada.
def deslocar_deteccao(deteccao, x, y):
    x1, y1, x2, y2 = deteccao["caixa_xyxy"]
    return {**deteccao, "caixa_xyxy": [x1 + x, y1 + y, x2 + x, y2 + y]}


# Consulta a caixa no quadro completo e amplia o conteúdo de cada abertura encontrada.
def detectar_caixas_e_produtos(imagem_bgr, config, cliente=None):
    caixas_brutas = detectar(imagem_bgr, config, cliente=cliente,
                             modelo_id=config["modelo_caixas_id"], aliases={})
    caixas = filtrar_caixas(caixas_brutas, config)
    produtos_brutos = detectar(imagem_bgr, config, cliente=cliente)
    produtos_globais, suprimidas = consolidar_deteccoes(
        produtos_brutos, imagem_bgr, config["limiar_confianca"]
    )
    recortes = []
    produtos_internos = []
    caixas_com_recorte_positivo = []
    for indice, caixa in enumerate(caixas, start=1):
        recorte, limites = recortar_interior(imagem_bgr, caixa)
        if recorte is None:
            recortes.append({"indice_caixa": indice, "analisado": False, "motivo": "recorte_pequeno"})
            continue
        x1, y1, x2, y2 = limites
        brutas = detectar(recorte, config, cliente=cliente)
        internas, suprimidas_locais = consolidar_deteccoes(
            brutas, recorte, config["limiar_confianca"]
        )
        aceitas = [deslocar_deteccao(item, x1, y1) for item in internas
                   if item["confianca"] >= config["limiar_confianca"]]
        aceitas = [item for item in aceitas if produto_dentro(item, caixa)]
        recortes.append({"indice_caixa": indice, "analisado": True,
                         "regiao_xyxy": [x1, y1, x2, y2],
                         "produtos_aceitos": len(aceitas)})
        if aceitas:
            caixas_com_recorte_positivo.append(caixa)
            produtos_internos.extend(aceitas)
        suprimidas.extend(deslocar_deteccao(item, x1, y1) for item in suprimidas_locais)
    produtos_globais = [item for item in produtos_globais
                        if not any(produto_dentro(item, caixa)
                                   for caixa in caixas_com_recorte_positivo)]
    produtos = produtos_globais + produtos_internos
    analise = associar_produtos(produtos, caixas, config)
    analise["recortes_internos"] = recortes
    analise["caixas_ignoradas"] = [
        {**deteccao, "motivo": (
            "abaixo_do_limiar" if deteccao["confianca"] < config["limiar_confianca"]
            else "classe_nao_configurada"
        )}
        for deteccao in caixas_brutas if deteccao not in caixas
    ]
    analise["deteccoes_suprimidas"] = suprimidas
    return produtos, caixas, analise


# Guarda a visão enviada ao detector para cada caixa, facilitando a revisão das fotos.
def salvar_recortes_internos(imagem_bgr, analise, pasta):
    if not analise:
        return
    for item in analise.get("recortes_internos", []):
        if not item["analisado"]:
            continue
        x1, y1, x2, y2 = item["regiao_xyxy"]
        salvar_jpg(pasta / f"caixa_{item['indice_caixa']}_interior.jpg",
                   imagem_bgr[y1:y2, x1:x2])


# Marca as caixas em azul antes de desenhar as ferramentas e o painel existentes.
def desenhar_caixas_embalagem(imagem_bgr, caixas):
    imagem = bgr_para_pil(imagem_bgr)
    desenho = ImageDraw.Draw(imagem)
    fonte = carregar_fonte(18, negrito=True)
    for caixa in caixas:
        x1, y1, x2, y2 = [round(valor) for valor in caixa["caixa_xyxy"]]
        desenho.rectangle((x1, y1, x2, y2), outline=(35, 110, 245), width=4)
        titulo = f"Caixa aberta {caixa['indice']} ({caixa['confianca']:.2f})"
        largura = round(desenho.textlength(titulo, font=fonte)) + 12
        topo_rotulo = y1 - 28 if y1 >= 28 else y1 + 5
        desenho.rectangle((x1, topo_rotulo, x1 + largura, topo_rotulo + 28), fill=(35, 110, 245))
        desenho.text((x1 + 6, topo_rotulo + 2), titulo, fill=(255, 255, 255), font=fonte)
    return pil_para_bgr(imagem)
