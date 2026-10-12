# Guia de passagem — conferência visual de ferramentas

Para quem vai integrar este módulo ao restante do sistema. Leia também o `README.md` (uso) e o `CLAUDE.md` (decisões e contratos).

## Estado atual (12/10/2026)

**Pronto e testado**

- Fluxo completo: imagem + nota JSON → `relatorio.json` + `imagem_anotada.jpg` (`src/conferir.py`).
- Leitura e validação da nota (`src/nota.py`), comparação e status (`src/comparador.py`), adaptador do Roboflow (`src/detector.py`), caixas e painel com acentos (`src/visualizacao.py`).
- 38 testes `pytest`, todos sem rede (`tests/`).
- Respostas reais do Roboflow guardadas em `fixtures/` (o formato bate com o previsto: centro `x`, `y`, `width`, `height` em pixels, `confidence`, `class`).
- Notas de exemplo em `notas/` (feitas para a `Img 16.jpg`: 1 chave inglesa → conforme; 2 → divergente).

**Não feito**

- Etapa 6 (câmera): não implementada — não havia webcam nem ferramentas físicas.
- Cenários de pitch definitivos (etapa 5): ficaram só os exemplos com a `Img 16`.

## Ponto de atenção: o modelo

O código funciona; o modelo pré-treinado é que reconhece mal fotos fora do seu conjunto. Em 21 imagens de teste, só a `Img 7`, a `Img 15` e a `Img 16` tiveram detecções acima de 0,5, e mesmo assim com erros (ex.: duas chaves de fenda marcadas como martelo na `Img 7`; 3 de 4 chaves inglesas na `Img 15`). Resultados por imagem em `saidas/fumaca/resumo.json` (gere de novo com `src/testar_modelo.py`).

Trocar de modelo é simples: basta mudar `model_id` (e, se as classes forem outras, `de_para` e `nomes_exibicao`) no `config.json`. Nada no código depende das classes atuais.

## Como integrar

Escolha uma das três formas; todas produzem o mesmo relatório.

**1. Função Python** (mesmo processo)

```python
import sys; sys.path.insert(0, "caminho/do/projeto/src")
from conferir import conferir
relatorio, pasta = conferir("foto.jpg", "nota.json")            # grava em saidas/<execucao>/
relatorio, pasta = conferir("foto.jpg", "nota.json", "minha/pasta")
```

Para quadros em memória (array numpy BGR, como vem do OpenCV) e uma nota já em dicionário:

```python
from conferir import carregar_config, conferir_quadro
from nota import validar_nota
config = carregar_config()
nota = validar_nota(dados_da_nota, config["de_para"])          # lança nota.ErroEntrada se inválida
relatorio, evidencia_bgr = conferir_quadro(quadro_bgr, nota, config)  # não grava nada em disco
```

**2. Linha de comando** (outro processo ou outra linguagem)

```bash
.venv\Scripts\python.exe src\conferir.py --imagem foto.jpg --nota nota.json --saida pasta --json
```

Saída padrão: o relatório em JSON, com `pasta_saida` acrescentado. Código de saída: `0` conforme, `1` divergente, `2` erro.

**3. Arquivos** — leia `relatorio.json` e `imagem_anotada.jpg` da pasta de saída.

### Contrato do relatório

```json
{
  "nota_id": "NF-DEMO-002",
  "imagem": "imagens/teste/Img 16.jpg",
  "status": "divergente",
  "linhas": [
    {"codigo": "FER-003", "item": "Chave inglesa", "classe": "Wrench",
     "esperado": 2, "detectado": 1, "delta": -1, "situacao": "falta"}
  ],
  "descartadas": [{"classe": "Hammer", "confianca": 0.31}],
  "avisos": [],
  "modelo_id": "tools-classification-byznk/2",
  "limiar_confianca": 0.5,
  "gerado_em": "2026-10-12T01:49:13-03:00"
}
```

- `status`: `conforme` | `divergente` | `erro`. Em `erro`, `linhas` vem vazia e a causa está em `avisos[0]`, com o que fazer.
- `situacao`: `igual` | `falta` | `excesso` | `nao_previsto`.
- `codigo` de uma linha `nao_previsto` vem do `de_para` (ou `null` se a classe não tiver código).
- As funções `conferir` e `conferir_quadro` não lançam exceção por falha técnica: devolvem `status: "erro"`.

## Decisões tomadas

- Python 3.12.10 em `.venv`; versões fixadas em `requirements.txt` (`inference-sdk` 1.7.4).
- A chave vai no cabeçalho `Authorization` (`api_key_transport="header"`), não na URL.
- O servidor devolve detecções a partir de 0,1 de confiança, para o relatório listar as descartadas; o corte real é o `limiar_confianca` do `config.json`.
- Confiança exatamente igual ao limiar conta.
- `Fasteners` é descartada por completo: não conta, não vira linha, não aparece em `descartadas` nem na imagem.
- Imagens com menos de 560 px de altura são ampliadas só na evidência, para o painel ficar legível; as coordenadas do relatório são da imagem original.
- `saidas/` está no `.gitignore`. Se quiser versionar saídas de reserva, copie-as para outra pasta.

## Prompts prontos para o Claude

1. Integração:
   > Leia CLAUDE.md, README.md e GUIA_PASSAGEM.md. Quero chamar a conferência a partir de [descreva o seu sistema]. Use `conferir_quadro` ou a CLI com `--json`, sem alterar o contrato do relatório. Escreva um teste de integração que use um cliente falso (veja `tests/test_conferir.py`).

2. Câmera (etapa 6):
   > Leia CLAUDE.md e GUIA_PASSAGEM.md. Implemente `src/camera.py`: vídeo ao vivo com OpenCV; espaço congela o quadro e chama `conferir_quadro` com a nota passada em `--nota`; mostra a evidência e grava `relatorio.json` e `imagem_anotada.jpg` numa pasta nova de `saidas/`; Q sai. Os quadros nunca são somados.

3. Trocar de modelo:
   > Leia CLAUDE.md e GUIA_PASSAGEM.md. Quero testar o modelo `<model_id>`. Atualize `config.json` (classes, `de_para`, `nomes_exibicao`), rode `src/testar_modelo.py`, salve uma resposta bruta nova em `fixtures/` e me mostre um resumo por imagem antes de mudar qualquer outra coisa.
