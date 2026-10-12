# Conferência visual de ferramentas — MVP do Desafio Renault

Confere se as ferramentas que aparecem numa foto batem com uma nota fiscal simulada (JSON) e aponta divergências. Um modelo YOLO hospedado no Roboflow detecta e conta as ferramentas; o programa compara com a nota e gera:

- `relatorio.json` — status (`conforme`, `divergente` ou `erro`) e uma linha por item;
- `imagem_anotada.jpg` — a foto com as caixas e um painel "esperado × detectado × situação".

As ferramentas manuais fazem o papel das peças automotivas. Em produção, o modelo seria treinado com as peças reais; aqui o que se valida é a arquitetura.

## Instalação (Windows)

Requer Python 3.10 a 3.13 (o `inference-sdk` 1.7.4 não suporta 3.14). Foi testado com 3.12.10.

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Copie `.env.example` para `.env` e preencha `ROBOFLOW_API_KEY` com a sua chave do Roboflow. O `.env` não vai para o Git.

## Execução

Conferência de uma imagem contra uma nota:

```bash
.venv\Scripts\python.exe src\conferir.py --imagem "imagens/teste/Img 16.jpg" --nota notas/nota_divergente.json
```

Opções:

- `--saida PASTA` — onde gravar os resultados (padrão: `saidas/<data_hora>_<imagem>/`);
- `--json` — imprime o relatório completo em JSON (com `pasta_saida`) em vez do resumo.

Código de saída do processo: `0` conforme, `1` divergente, `2` erro.

Uso como biblioteca (com `src/` no `sys.path`):

```python
from conferir import conferir
relatorio, pasta = conferir("foto.jpg", "nota.json")
```

Para um quadro já em memória (array BGR do OpenCV) e uma nota já validada, use `conferir_quadro(imagem_bgr, nota, config)`.

Teste de fumaça do modelo em todas as imagens de `imagens/teste/` (gera `saidas/fumaca/`):

```bash
.venv\Scripts\python.exe src\testar_modelo.py
```

Testes automatizados (sem rede):

```bash
.venv\Scripts\python.exe -m pytest
```

## Nota fiscal simulada

```json
{
  "nota_id": "NF-DEMO-001",
  "fornecedor": "Fornecedor Exemplo Ltda.",
  "itens": [
    {"codigo": "FER-003", "descricao": "Chave inglesa", "quantidade": 1}
  ]
}
```

Os códigos são associados às classes do modelo pelo `de_para` do `config.json` (`FER-001` alicate, `FER-002` chave de fenda, `FER-003` chave inglesa, `FER-004` martelo). Código desconhecido, quantidade que não seja inteiro positivo ou JSON malformado resultam em `erro`. Linhas repetidas são somadas.

## Regras da conferência

Para cada classe esperada ou detectada (confiança ≥ `limiar_confianca`, padrão 0,5), `delta = detectado − esperado`:

| Situação | Condição |
|---|---|
| `igual` | delta = 0 |
| `falta` | delta < 0 |
| `excesso` | delta > 0 e o item consta da nota |
| `nao_previsto` | detectado, mas não consta da nota |

O status é `conforme` só se todas as linhas forem `igual`. Falhas técnicas (rede, chave, imagem ou nota inválidas) dão `erro` e nunca `conforme`. Detecções abaixo do limiar vão para `descartadas` e aparecem em cinza na imagem. A classe `Fasteners` é ignorada.

## Limitações

- **Desempenho do modelo nas nossas imagens é baixo.** No teste de fumaça com 21 imagens da internet (fotos de produto, fundo branco, baixa resolução), só 3 tiveram detecções acima de 0,5 e nenhuma foi contada por completo. A métrica publicada (mAP@50 de 98,7%) foi medida no conjunto do próprio autor. O pipeline está correto; a precisão depende de um modelo treinado com imagens parecidas com as de uso real.
- Depende de internet e do plano gratuito do Roboflow (inferência hospedada).
- Uma imagem por vez; não há vídeo nem contagem acumulada.
- A nota é um JSON simulado; não há leitura (OCR) de nota real.

## Crédito do modelo

Modelo "Tools Classification", de **proelec3**, publicado no Roboflow Universe sob licença CC BY 4.0:
https://universe.roboflow.com/proelec3/tools-classification-byznk
(`model_id` `tools-classification-byznk/2`, arquitetura YOLOv8s).
