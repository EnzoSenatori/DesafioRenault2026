import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

CORES_CLASSE = {
    "Pliers": (230, 120, 0),
    "Screwdriver": (0, 140, 230),
    "Wrench": (150, 60, 200),
    "PipeWrench": (255, 170, 0),
    "Hammer": (210, 40, 40),
}
COR_PADRAO = (255, 170, 0)
CINZA = (150, 150, 150)

CORES_STATUS = {
    "conforme": (30, 150, 70),
    "divergente": (200, 40, 40),
    "erro": (110, 110, 110),
}
CORES_SITUACAO = {
    "igual": (30, 150, 70),
    "falta": (200, 40, 40),
    "excesso": (210, 120, 0),
    "nao_previsto": (210, 120, 0),
}
TEXTO_SITUACAO = {
    "igual": "OK",
    "falta": "Falta",
    "excesso": "Excesso",
    "nao_previsto": "Não previsto",
}

ALTURA_MINIMA = 560
LARGURA_PAINEL = 640


# Carrega uma fonte TTF do sistema (com acentos); cai para a padrão se não houver
def carregar_fonte(tamanho, negrito=False):
    nomes = ("arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf") if negrito else ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf")
    for nome in nomes:
        try:
            return ImageFont.truetype(nome, tamanho)
        except OSError:
            continue
    return ImageFont.load_default()


# Converte BGR (OpenCV) para imagem Pillow RGB
def bgr_para_pil(imagem_bgr):
    return Image.fromarray(cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2RGB))


# Converte imagem Pillow RGB para BGR (OpenCV)
def pil_para_bgr(imagem_pil):
    return cv2.cvtColor(np.array(imagem_pil), cv2.COLOR_RGB2BGR)


# Desenha um rótulo com fundo colorido, mantendo-o dentro da imagem
def _rotulo(desenho, x, y, texto, cor, fonte, largura_img):
    caixa = desenho.textbbox((0, 0), texto, font=fonte)
    largura, altura = caixa[2] - caixa[0] + 8, caixa[3] - caixa[1] + 8
    x = max(0, min(x, largura_img - largura))
    y = y - altura if y - altura >= 0 else y
    desenho.rectangle([x, y, x + largura, y + altura], fill=cor)
    desenho.text((x + 4, y + 4 - caixa[1]), texto, fill=(255, 255, 255), font=fonte)


# Desenha as caixas: aceitas com a cor da classe, abaixo do limiar em cinza; classes ignoradas não aparecem
def desenhar_caixas(imagem_bgr, deteccoes, config):
    escala = max(1.0, ALTURA_MINIMA / imagem_bgr.shape[0])
    if escala > 1.0:
        imagem_bgr = cv2.resize(imagem_bgr, None, fx=escala, fy=escala, interpolation=cv2.INTER_CUBIC)
    imagem = bgr_para_pil(imagem_bgr)
    desenho = ImageDraw.Draw(imagem)
    espessura = max(2, round(min(imagem.size) / 180))
    fonte = carregar_fonte(max(14, round(min(imagem.size) / 32)))
    limiar = config["limiar_confianca"]
    ignoradas = set(config.get("classes_ignoradas", []))
    nomes = config.get("nomes_exibicao", {})

    visiveis = [d for d in deteccoes if d["classe"] not in ignoradas]
    for deteccao in sorted(visiveis, key=lambda d: d["confianca"]):
        aceita = deteccao["confianca"] >= limiar
        cor = CORES_CLASSE.get(deteccao["classe"], COR_PADRAO) if aceita else CINZA
        x1, y1, x2, y2 = [v * escala for v in deteccao["caixa_xyxy"]]
        desenho.rectangle([x1, y1, x2, y2], outline=cor, width=espessura)
        texto = f"{nomes.get(deteccao['classe'], deteccao['classe'])} {deteccao['confianca']:.2f}"
        _rotulo(desenho, x1, y1, texto, cor, fonte, imagem.width)
    return pil_para_bgr(imagem)


# Quebra um texto em linhas que caibam na largura dada
def _quebrar(desenho, texto, fonte, largura):
    linhas, atual = [], ""
    for palavra in texto.split():
        tentativa = f"{atual} {palavra}".strip()
        if desenho.textlength(tentativa, font=fonte) <= largura or not atual:
            atual = tentativa
        else:
            linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


# Desenha o painel "esperado × detectado × situação" ao lado da imagem anotada
def montar_evidencia(imagem_anotada_bgr, relatorio):
    fonte_status = carregar_fonte(40, negrito=True)
    fonte_titulo = carregar_fonte(18, negrito=True)
    fonte = carregar_fonte(18)
    fonte_pequena = carregar_fonte(15)
    margem, largura_util = 24, LARGURA_PAINEL - 48
    colunas = [margem, margem + 230, margem + 345, margem + 470]

    rascunho = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    avisos = [l for aviso in relatorio.get("avisos", []) for l in _quebrar(rascunho, f"• {aviso}", fonte_pequena, largura_util)]
    altura_painel = 120 + 40 + 34 * max(1, len(relatorio["linhas"])) + 30 + 22 * len(avisos) + 60
    altura = max(imagem_anotada_bgr.shape[0], altura_painel)

    imagem = bgr_para_pil(imagem_anotada_bgr)
    tela = Image.new("RGB", (imagem.width + LARGURA_PAINEL, altura), (255, 255, 255))
    tela.paste(imagem, (0, (altura - imagem.height) // 2))
    desenho = ImageDraw.Draw(tela)
    x0 = imagem.width
    desenho.line([x0, 0, x0, altura], fill=(220, 220, 220), width=2)

    status = relatorio["status"]
    desenho.rectangle([x0, 0, x0 + LARGURA_PAINEL, 90], fill=CORES_STATUS.get(status, CINZA))
    desenho.text((x0 + margem, 22), status.upper(), fill=(255, 255, 255), font=fonte_status)
    y = 104
    desenho.text((x0 + margem, y), f"Nota: {relatorio.get('nota_id') or '—'}", fill=(60, 60, 60), font=fonte_pequena)
    y += 36

    for titulo, x in zip(("Item", "Esperado", "Detectado", "Situação"), colunas):
        desenho.text((x0 + x, y), titulo, fill=(40, 40, 40), font=fonte_titulo)
    y += 28
    desenho.line([x0 + margem, y, x0 + LARGURA_PAINEL - margem, y], fill=(200, 200, 200), width=1)
    y += 8
    if not relatorio["linhas"]:
        desenho.text((x0 + margem, y), "—", fill=(120, 120, 120), font=fonte)
        y += 34
    for linha in relatorio["linhas"]:
        situacao = linha["situacao"]
        valores = (linha["item"], str(linha["esperado"]), str(linha["detectado"]), TEXTO_SITUACAO.get(situacao, situacao))
        for valor, x in zip(valores[:3], colunas[:3]):
            desenho.text((x0 + x, y), valor, fill=(30, 30, 30), font=fonte)
        desenho.text((x0 + colunas[3], y), valores[3], fill=CORES_SITUACAO.get(situacao, CINZA), font=fonte_titulo)
        y += 34

    if avisos:
        y += 14
        for linha_aviso in avisos:
            desenho.text((x0 + margem, y), linha_aviso, fill=(170, 90, 0), font=fonte_pequena)
            y += 22

    rodape = f"Limiar {relatorio.get('limiar_confianca')} · {relatorio.get('gerado_em', '')}"
    desenho.text((x0 + margem, altura - 32), rodape, fill=(140, 140, 140), font=fonte_pequena)
    return pil_para_bgr(tela)


# Imagem em branco para o painel quando a foto não pôde ser lida
def imagem_vazia():
    return np.full((ALTURA_MINIMA, ALTURA_MINIMA, 3), 235, dtype=np.uint8)


# Grava a imagem BGR em JPEG, aceitando caminhos com espaços ou acentos no Windows
def salvar_jpg(caminho, imagem_bgr):
    ok, codificada = cv2.imencode(".jpg", imagem_bgr, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not ok:
        raise RuntimeError(f"Falha ao gerar {caminho}")
    codificada.tofile(str(caminho))
