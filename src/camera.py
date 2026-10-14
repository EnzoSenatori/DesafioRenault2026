import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import cv2
from PIL import ImageDraw

from conferir import PASTA_SAIDAS, analisar_quadro, carregar_config, config_sem_caixas, imprimir_resumo
from caixas import salvar_recortes_internos
from nota import ErroEntrada, carregar_nota
from visualizacao import bgr_para_pil, carregar_fonte, pil_para_bgr, salvar_jpg


# Frações do quadro usadas na inferência; excluem bordas como teclado e mesa.
AREA_LEITURA = (0.25, 0.16, 1.0, 0.92)


# Reserva uma pasta diferente para cada captura, inclusive quando duas ocorrem no mesmo segundo.
def nova_pasta_captura(base=PASTA_SAIDAS):
    base = Path(base)
    nome = f"camera_{datetime.now():%Y%m%d_%H%M%S}"
    pasta = base / nome
    sufixo = 2
    while pasta.exists():
        pasta = base / f"{nome}_{sufixo}"
        sufixo += 1
    pasta.mkdir(parents=True)
    return pasta


# Converte a área proporcional em pixels para prévia e recorte usarem a mesma região.
def limites_area(quadro, area=AREA_LEITURA):
    altura, largura = quadro.shape[:2]
    esquerda, topo, direita, fundo = area
    if not (0 <= esquerda < direita <= 1 and 0 <= topo < fundo <= 1):
        raise ValueError("Área de leitura inválida — confira os limites proporcionais")
    x1 = max(0, min(largura - 1, round(esquerda * largura)))
    y1 = max(0, min(altura - 1, round(topo * altura)))
    x2 = max(x1 + 1, min(largura, round(direita * largura)))
    y2 = max(y1 + 1, min(altura, round(fundo * altura)))
    return x1, y1, x2, y2


# Recorta exatamente os pixels que serão enviados ao detector.
def recortar_area(quadro, area=AREA_LEITURA):
    x1, y1, x2, y2 = limites_area(quadro, area)
    return quadro[y1:y2, x1:x2].copy()


# Confere só a área marcada e grava o quadro inteiro, o recorte, relatório e evidência.
def processar_captura(quadro, nota, config, pasta, cliente=None):
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    if quadro is not None:
        salvar_jpg(pasta / "quadro_original.jpg", quadro)
        quadro_analisado = recortar_area(quadro)
        salvar_jpg(pasta / "quadro_analisado.jpg", quadro_analisado)
    else:
        quadro_analisado = None
    relatorio, evidencia, analise_caixas = analisar_quadro(
        quadro_analisado, nota, config, cliente=cliente,
        imagem_origem=str(pasta / "quadro_original.jpg"),
    )
    if analise_caixas is not None:
        (pasta / "analise_caixas.json").write_text(
            json.dumps(analise_caixas, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        salvar_recortes_internos(quadro_analisado, analise_caixas, pasta)
    (pasta / "relatorio.json").write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    salvar_jpg(pasta / "imagem_anotada.jpg", evidencia)
    return relatorio, evidencia


# Marca em verde os limites da região efetivamente analisada.
def marcar_area(quadro):
    imagem = bgr_para_pil(quadro)
    desenho = ImageDraw.Draw(imagem)
    x1, y1, x2, y2 = limites_area(quadro)
    desenho.rectangle((x1, y1, x2 - 1, y2 - 1), outline=(35, 205, 65), width=4)
    return pil_para_bgr(imagem)


# Acrescenta uma mensagem legível ao quadro de prévia, inclusive com acentos.
def mostrar_mensagem(quadro, mensagem):
    imagem = bgr_para_pil(quadro)
    desenho = ImageDraw.Draw(imagem)
    fonte = carregar_fonte(18, negrito=True)
    largura = int(desenho.textlength(mensagem, font=fonte)) + 24
    desenho.rectangle((0, 0, largura, 36), fill=(30, 30, 30))
    desenho.text((12, 8), mensagem, fill=(255, 255, 255), font=fonte)
    return pil_para_bgr(imagem)


# Reduz apenas a imagem exibida na janela; os arquivos preservam a resolução original.
def ajustar_janela(imagem, largura_maxima=1200, altura_maxima=750):
    altura, largura = imagem.shape[:2]
    escala = min(1.0, largura_maxima / largura, altura_maxima / altura)
    if escala == 1.0:
        return imagem
    return cv2.resize(imagem, None, fx=escala, fy=escala, interpolation=cv2.INTER_AREA)


# Abre a câmera, espera espaço para conferência independente e encerra com Q.
def executar_camera(nota, config, indice=0, base=PASTA_SAIDAS, captura_video=None):
    captura = captura_video or cv2.VideoCapture(indice, cv2.CAP_DSHOW)
    if not captura.isOpened():
        captura.release()
        print(f"Não foi possível abrir a câmera {indice} — verifique a conexão e a permissão de câmera no Windows.", file=sys.stderr)
        return 2
    print("Câmera aberta. Coloque os itens na área verde; espaço confere e Q sai.")
    try:
        while True:
            ok, quadro = captura.read()
            if not ok or quadro is None:
                print("A câmera não entregou um quadro — verifique a conexão e tente novamente.", file=sys.stderr)
                return 2
            previa = mostrar_mensagem(marcar_area(quadro), "Área verde: itens | ESPAÇO: conferir | Q: sair")
            cv2.imshow("Conferência ao vivo", ajustar_janela(previa))
            tecla = cv2.waitKey(1) & 0xFF
            if tecla in (ord("q"), ord("Q")):
                return 0
            if tecla != 32:
                continue
            congelado = quadro.copy()
            cv2.imshow("Conferência ao vivo", ajustar_janela(mostrar_mensagem(marcar_area(congelado), "Conferindo…")))
            cv2.waitKey(1)
            pasta = nova_pasta_captura(base)
            relatorio, evidencia = processar_captura(congelado, nota, config, pasta)
            imprimir_resumo(relatorio, pasta)
            cv2.imshow("Resultado da conferência", ajustar_janela(evidencia))
            cv2.waitKey(1)
    finally:
        captura.release()
        cv2.destroyAllWindows()


# Valida a configuração e a nota antes de acessar a webcam.
def main(argumentos=None):
    parser = argparse.ArgumentParser(description="Confere uma foto capturada pela câmera contra a nota fiscal simulada.")
    parser.add_argument("--nota", required=True, help="caminho do JSON da nota fiscal")
    parser.add_argument("--camera", type=int, default=0, help="índice da câmera (padrão: 0)")
    parser.add_argument("--sem-caixas", action="store_true",
                        help="confere só com o modelo de ferramentas, ignorando modelo_caixas_id do config")
    args = parser.parse_args(argumentos)
    if args.camera < 0:
        parser.error("--camera deve ser zero ou um inteiro positivo")
    try:
        config = carregar_config()
        if args.sem_caixas:
            config = config_sem_caixas(config)
        nota = carregar_nota(args.nota, config["de_para"])
    except (ErroEntrada, KeyError) as erro:
        print(f"Não foi possível iniciar a câmera: {erro}", file=sys.stderr)
        return 2
    return executar_camera(nota, config, indice=args.camera)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
