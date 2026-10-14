# Conferência visual de ferramentas — MVP do Desafio Renault

> **Registro histórico:** este arquivo descreve a construção inicial e foi o `CLAUDE.md` da raiz até 13/10/2026. Suas instruções técnicas (modelo proelec3, limiar 0,5, câmera como extra) não valem mais. O estado atual está em `CONTINUIDADE.md`; as regras para agentes, em `AGENTS.md`; a apresentação pública, em `README.md`.

Este arquivo orienta o Claude Code na construção do MVP. Leia-o inteiro antes de começar e siga a ordem de implementação, parando nos portões indicados.

## 1. Contexto

O desafio trata do recebimento de materiais na Renault. Na etapa que cabe a esta equipe, o sistema confere se os itens fisicamente recebidos batem com a nota fiscal e aponta divergências.

Este MVP prova essa conferência com **ferramentas manuais** no lugar das peças automotivas. O fluxo é este:

1. Uma foto, ou um quadro da câmera, mostra as ferramentas recebidas.
2. Um modelo YOLO pré-treinado, hospedado no Roboflow, detecta e conta cada ferramenta.
3. O programa compara as contagens com uma nota fiscal simulada em JSON.
4. O OpenCV gera a evidência: a imagem anotada com as caixas e um painel "esperado × detectado × situação".

Em produção, o modelo seria treinado com as peças reais; aqui, a arquitetura é o que se valida.

- **Apresentação:** pitch ao vivo em **[DATA A DEFINIR]**. A demonstração precisa ser previsível.
- **Divisão do trabalho:** Enzo constrói este alicerce. Depois, Rafael dá continuidade (modo câmera refinado, interface de apresentação, integração com a nota real) a partir de um guia de passagem.

## 2. Decisões fechadas

- **Modelo:** "Tools Classification" (autor: proelec3, Roboflow Universe), arquitetura YOLOv8s, `model_id` = `tools-classification-byznk/2`. Inferência hospedada pelo `inference-sdk`. **Não há treino neste projeto.**
- **Classes do modelo:** `Hammer`, `Screwdriver`, `Wrench`, `Pliers`, `Fasteners`. A classe `Fasteners` é ignorada na conferência.
- **Stack:** Python, `inference-sdk`, `opencv-python`, `python-dotenv`, `Pillow` (para texto com acentos) e `pytest`. Interface por linha de comando.
- **Ambiente:** Windows. Use um ambiente virtual em `.venv` e uma versão de Python compatível com o `inference-sdk` (verifique antes de instalar).
- **Chave:** a variável `ROBOFLOW_API_KEY` fica no `.env`. O `.env` vai no `.gitignore`, e um `.env.example` leva só o nome da variável. A chave nunca aparece no código, em logs ou em saídas.
- **Licença:** o modelo é CC BY 4.0. O README dá crédito ao autor e traz o link: https://universe.roboflow.com/proelec3/tools-classification-byznk

## 3. Fora de escopo

Não implemente: treino ou ajuste fino de modelo, Streamlit, API web, banco de dados, leitura (OCR) da nota fiscal, vídeo contínuo com contagem acumulada, catálogos com unidades e kits, schemas versionados. Se algo disso parecer necessário, pergunte antes.

## 4. Configuração e contratos

### 4.1 `config.json`

```json
{
  "model_id": "tools-classification-byznk/2",
  "api_url": "https://serverless.roboflow.com",
  "limiar_confianca": 0.5,
  "classes_ignoradas": ["Fasteners"],
  "de_para": {
    "FER-001": "Pliers",
    "FER-002": "Screwdriver",
    "FER-003": "Wrench",
    "FER-004": "Hammer"
  },
  "nomes_exibicao": {
    "Pliers": "Alicate",
    "Screwdriver": "Chave de fenda",
    "Wrench": "Chave inglesa",
    "Hammer": "Martelo"
  }
}
```

O limiar de 0,5 é provisório e será calibrado com as imagens de teste.

### 4.2 Nota fiscal simulada (`notas/*.json`)

```json
{
  "nota_id": "NF-DEMO-001",
  "fornecedor": "Fornecedor Exemplo Ltda.",
  "itens": [
    {"codigo": "FER-001", "descricao": "Alicate universal", "quantidade": 2},
    {"codigo": "FER-002", "descricao": "Chave de fenda", "quantidade": 1}
  ]
}
```

Regras de leitura:

- O código é tratado como texto.
- A quantidade deve ser um inteiro positivo.
- Linhas repetidas com o mesmo código são somadas.
- Um código ausente do `de_para` gera erro de entrada explícito, nunca é ignorado em silêncio.
- JSON malformado gera erro de entrada.

### 4.3 Detecção (formato interno)

O adaptador do detector converte a resposta do Roboflow para:

```json
{"classe": "Pliers", "confianca": 0.93, "caixa_xyxy": [x1, y1, x2, y2]}
```

**Não presuma o formato da resposta.** Na primeira chamada real, salve a resposta bruta em `fixtures/resposta_roboflow.json` e construa o adaptador a partir dela. O formato esperado traz centro (`x`, `y`), `width` e `height` em pixels, mas confirme.

Para aceitar quadros do OpenCV, confirme também que o SDK recebe um array numpy e em qual ordem de canais.

### 4.4 Comparação

Para cada classe na **união** das esperadas (vindas da nota) e das detectadas (acima do limiar e fora de `classes_ignoradas`), calcule `delta = detectado − esperado`. A situação de cada linha é:

| Condição | Situação |
|---|---|
| delta = 0 | `igual` |
| delta < 0 | `falta` |
| delta > 0 e esperado > 0 | `excesso` |
| detectado > 0 e esperado = 0 | `nao_previsto` |

O status global é:

- `erro`: falha de rede, chave inválida, imagem ilegível ou nota inválida. **Uma falha técnica nunca resulta em `conforme`.**
- `conforme`: todas as linhas são `igual`.
- `divergente`: qualquer outra situação. Se não houver nenhuma detecção e a nota tiver itens, o relatório inclui o aviso "nenhuma ferramenta detectada — verifique a captura".

Detecções abaixo do limiar não entram na contagem. Elas aparecem no relatório em `descartadas` e são desenhadas em cinza na imagem.

### 4.5 Relatório (`saidas/<execucao>/relatorio.json`)

```json
{
  "nota_id": "NF-DEMO-001",
  "imagem": "imagens/teste/cena01.jpg",
  "status": "divergente",
  "linhas": [
    {"codigo": "FER-001", "item": "Alicate", "classe": "Pliers", "esperado": 2, "detectado": 1, "delta": -1, "situacao": "falta"}
  ],
  "descartadas": [{"classe": "Wrench", "confianca": 0.31}],
  "avisos": [],
  "modelo_id": "tools-classification-byznk/2",
  "limiar_confianca": 0.5,
  "gerado_em": "2026-10-12T10:00:00-03:00"
}
```

A mesma pasta guarda `imagem_anotada.jpg`.

## 5. Estrutura do projeto

```text
CLAUDE.md
README.md
requirements.txt
.env.example
.gitignore            # .env, .venv/, saidas/
config.json
notas/                # nota_conforme.json, nota_divergente.json
imagens/teste/        # imagens fornecidas pelo Enzo
fixtures/             # resposta bruta do Roboflow
saidas/               # resultados por execução (fora do Git)
src/
  detector.py         # chamada ao Roboflow e conversão para o formato interno
  nota.py             # leitura e validação da nota; contagem esperada
  comparador.py       # linhas, situações e status global
  visualizacao.py     # caixas (OpenCV) e painel (Pillow, por causa dos acentos)
  conferir.py         # CLI: imagem + nota → relatório e imagem anotada
  testar_modelo.py    # teste de fumaça do modelo
  camera.py           # extra: webcam; espaço captura o quadro, Q sai
tests/
  test_nota.py
  test_comparador.py
```

## 6. Ordem de implementação

**Etapa 0 — ambiente.** Crie o `.venv`, o `requirements.txt` com as versões fixadas após a instalação, o `.env.example` e o `.gitignore`. Confirme que a chave carrega do `.env` sem imprimi-la.

**Etapa 1 — teste de fumaça do modelo.** `testar_modelo.py` roda o modelo em todas as imagens de `imagens/teste/`. Para cada uma, salva a imagem anotada em `saidas/fumaca/` e imprime as classes detectadas com a confiança. Salve a primeira resposta bruta em `fixtures/`.

> **PORTÃO: pare aqui.** Mostre ao Enzo um resumo por imagem e aguarde a avaliação dele antes de seguir. Se o modelo errar demais, não avance.

**Etapa 2 — nota e comparador.** Implemente `nota.py` e `comparador.py` com testes em `pytest`, usando contagens simuladas e sem rede. Cubra os casos:

- igualdade;
- falta;
- excesso;
- item não previsto;
- linhas repetidas;
- código fora do de-para;
- quantidade inválida;
- nenhuma detecção;
- classe ignorada.

**Etapa 3 — adaptador do detector.** Construa o adaptador a partir da fixture e teste a conversão sem rede. Trate exceções da chamada como `erro`.

**Etapa 4 — conferência ponta a ponta.**

```text
python src/conferir.py --imagem imagens/teste/cena01.jpg --nota notas/nota_divergente.json
```

A execução gera o relatório e a imagem anotada.

O painel mostra:

- o status global em destaque (verde para `CONFORME`, vermelho para `DIVERGENTE`, cinza para `ERRO`);
- uma linha por item, com nome em português, esperado, detectado e situação.

As caixas usam o nome em português e a confiança.

**Etapa 5 — cenários do pitch.** Com o Enzo, escolha duas imagens validadas na etapa 1 e escreva `nota_conforme.json` e `nota_divergente.json` coerentes com elas. A nota divergente deve declarar uma unidade a mais de uma ferramenta do que a imagem mostra. Gere e guarde as saídas dos dois cenários como reserva para o caso de falha de internet no dia.

**Etapa 6 — câmera (extra).** Execute esta etapa só se houver webcam. `camera.py` mostra o vídeo ao vivo. A tecla espaço congela o quadro e roda exatamente o mesmo fluxo da etapa 4. Os quadros nunca são somados.

**Etapa 7 — documentação.** Escreva o README com instalação, execução, crédito do modelo e limitações. Depois, prepare o guia de passagem para o Rafael: estado atual, o que está pronto, o que falta, decisões tomadas e prompts prontos para o Claude dele continuar.

## 7. Convenções de código

- Em Python, cada função leva um **comentário breve acima do `def`** descrevendo o que faz. **Não use docstrings.**
- Nomes de variáveis, funções e mensagens ficam em português.
- `cv2.putText` não renderiza acentos. Todo texto do painel e dos rótulos é desenhado com Pillow, usando uma fonte TTF do sistema.
- Mensagens de erro dizem o que falhou e o que fazer, por exemplo: "Chave do Roboflow ausente — defina ROBOFLOW_API_KEY no arquivo .env".
- Não invente formato de resposta, versões de biblioteca ou resultados. Verifique.

## 8. Riscos conhecidos

- **Desempenho real do modelo:** a métrica publicada (mAP@50 de 98,7%) foi medida no próprio conjunto do autor e pode cair em imagens de outra origem. A etapa 1 existe para isso.
- **Dependência de internet e do plano gratuito:** a inferência é hospedada. Por isso as saídas de reserva da etapa 5 existem.
- **Imagens do dataset do modelo:** dão acerto garantido na demo, mas o modelo provavelmente as viu no treino. Use-as só como rede de segurança e nunca as apresente como validação.
