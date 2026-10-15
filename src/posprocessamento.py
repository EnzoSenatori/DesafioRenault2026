from math import sqrt


# Devolve largura, altura e área da caixa de detecção.
def medidas(deteccao):
    x1, y1, x2, y2 = deteccao["caixa_xyxy"]
    largura, altura = max(0.0, x2 - x1), max(0.0, y2 - y1)
    return largura, altura, largura * altura


# Mede a interseção das projeções em cada eixo.
def intersecoes(primeira, segunda):
    ax1, ay1, ax2, ay2 = primeira["caixa_xyxy"]
    bx1, by1, bx2, by2 = segunda["caixa_xyxy"]
    return max(0.0, min(ax2, bx2) - max(ax1, bx1)), max(0.0, min(ay2, by2) - max(ay1, by1))


# Reconhece caixas muito sobrepostas ou partes alinhadas do mesmo objeto longo.
def provavel_mesmo_objeto(primeira, segunda, largura_imagem):
    if primeira["classe"] != segunda["classe"]:
        return False
    largura_a, altura_a, area_a = medidas(primeira)
    largura_b, altura_b, area_b = medidas(segunda)
    if not area_a or not area_b:
        return False
    inter_x, inter_y = intersecoes(primeira, segunda)
    inter_area = inter_x * inter_y
    if inter_area / (area_a + area_b - inter_area) >= 0.5:
        return True

    ax1, ay1, ax2, ay2 = primeira["caixa_xyxy"]
    bx1, by1, bx2, by2 = segunda["caixa_xyxy"]
    horizontais = largura_a >= 2 * altura_a and largura_b >= 2 * altura_b
    verticais = altura_a >= 2 * largura_a and altura_b >= 2 * largura_b
    if horizontais:
        distancia_y = abs((ay1 + ay2) / 2 - (by1 + by2) / 2)
        sobrepostas = (inter_x / min(largura_a, largura_b) >= 0.75
                       and inter_y > 0 and distancia_y <= 0.6 * max(altura_a, altura_b))
        vao_x = max(0.0, max(ax1, bx1) - min(ax2, bx2))
        alinhadas = (vao_x <= 0.03 * largura_imagem
                     and inter_y / min(altura_a, altura_b) >= 0.75
                     and max(largura_a, largura_b) / min(largura_a, largura_b) >= 1.5)
        return sobrepostas or alinhadas
    if verticais:
        distancia_x = abs((ax1 + ax2) / 2 - (bx1 + bx2) / 2)
        sobrepostas = (inter_y / min(altura_a, altura_b) >= 0.75
                       and inter_x > 0 and distancia_x <= 0.6 * max(largura_a, largura_b))
        return sobrepostas
    return False


# Descarta apenas um fragmento pequeno no canto quando há outro da mesma classe mais forte e próximo.
def fragmento_de_canto(candidato, outros, largura_imagem, altura_imagem):
    x1, y1, x2, y2 = candidato["caixa_xyxy"]
    bordas = sum((x1 <= 1, y1 <= 1, x2 >= largura_imagem - 1, y2 >= altura_imagem - 1))
    if bordas < 2:
        return False
    _, _, area = medidas(candidato)
    for outro in outros:
        if outro is candidato or outro["classe"] != candidato["classe"]:
            continue
        largura, altura, area_outro = medidas(outro)
        if (area_outro < 2.5 * area or
                outro["confianca"] < candidato["confianca"] + 0.15):
            continue
        margem = 0.15 * max(largura, altura)
        ox1, oy1, ox2, oy2 = outro["caixa_xyxy"]
        centro_x, centro_y = (x1 + x2) / 2, (y1 + y2) / 2
        if ox1 - margem <= centro_x <= ox2 + margem and oy1 - margem <= centro_y <= oy2 + margem:
            return True
    return False


# Consolida somente detecções aceitas, preservando as abaixo do limiar para auditoria.
def consolidar_deteccoes(deteccoes, imagem, limiar):
    altura_imagem, largura_imagem = imagem.shape[:2]
    aceitas = [d for d in deteccoes if d["confianca"] >= limiar]
    fracas = [d for d in deteccoes if d["confianca"] < limiar]
    ordenadas = sorted(aceitas, key=lambda d: d["confianca"] * sqrt(medidas(d)[2]), reverse=True)
    mantidas, suprimidas = [], []
    for deteccao in ordenadas:
        if any(provavel_mesmo_objeto(deteccao, outra, largura_imagem) for outra in mantidas):
            suprimidas.append({**deteccao, "motivo": "caixa_repetida_ou_parte_do_mesmo_objeto"})
        else:
            mantidas.append(deteccao)
    finais = []
    for deteccao in mantidas:
        if fragmento_de_canto(deteccao, mantidas, largura_imagem, altura_imagem):
            suprimidas.append({**deteccao, "motivo": "fragmento_no_canto_da_imagem"})
        else:
            finais.append(deteccao)
    return finais + fracas, suprimidas
