# Continuidade do projeto — Desafio Renault 2026

Atualizado em 13/10/2026. Este documento descreve o estado **depois** da escolha do modelo, do modo câmera, da área de leitura e da preparação do fluxo de dois modelos. O `CLAUDE.md` registra decisões históricas do protótipo inicial; para continuar o trabalho, use este documento e o `AGENTS.md`. Rafael decide mudanças importantes; o agente implementa e testa. O código local veio de um ZIP do repositório de Enzo e não tem histórico Git.

## Objetivo e escopo

O protótipo recebe uma foto ou um quadro capturado por webcam e uma nota simulada em JSON. Consulta um detector de objetos hospedado no Roboflow, traduz as classes do modelo para categorias internas, compara quantidades esperadas e detectadas e gera um relatório estruturado e uma imagem de evidência. Ferramentas manuais representam peças automotivas. O MVP valida o fluxo de conferência; peças reais, treino específico, OCR de NF-e, API web e integração com o orquestrador do colega dependem de decisões posteriores.

## Estado implementado e validado

- `src/conferir.py`: conferência de imagem, resultado `conforme`, `divergente` ou `erro`, saídas `relatorio.json` e `imagem_anotada.jpg`.
- `src/camera.py`: prévia ao vivo com área verde; espaço captura e confere um quadro isolado; Q sai. Salva `quadro_original.jpg` (foto inteira) e `quadro_analisado.jpg` (recorte enviado ao Roboflow), além do relatório e da evidência. A área padrão ocupa x=25%-100% e y=16%-92% do quadro. A nota é validada antes de abrir a câmera. Falha de rede produz `erro` e permite outra captura. A área já foi testada por Rafael em capturas reais com uma caixa aberta e ferramentas; a geometria do recorte precisa continuar sendo conferida em cada cenário.
- `src/caixas.py`: fluxo de dois modelos aprovado por Rafael. O modelo `open-closed-cardbox/2` localiza caixas abertas; o modelo de ferramentas examina o quadro inteiro e, quando há caixa aceita, também a parte superior da abertura. Se esse recorte encontra produtos acima do limiar, suas detecções substituem as atribuídas à mesma caixa no quadro geral, evitando dupla contagem. Ferramentas externas continuam no quadro geral. Cada `caixa_N_interior.jpg` mostra o recorte realmente enviado ao segundo modelo. A associação usa o centro de cada detecção. `analise_caixas.json` registra os recortes, caixas ignoradas e supressões; `relatorio.json` mantém o contrato. O limiar continua 0,6.
- `src/avaliar_modelos.py`: comparação dos modelos com gabarito conferido por Rafael em `imagens/teste/gabarito.json`.
- Modelo escolhido por Rafael: **GantrySystem Tool Detection** `tool-detection-4u0yd/15`, limiar atual **0,6** (decisão de 13/10/2026), licença CC BY 4.0: https://universe.roboflow.com/gantrysystem/tool-detection-4u0yd.
- Na avaliação original das quatro imagens do gabarito, com limiar 0,5, foram 3/4 imagens com contagem exata, 8 itens corretos, 0 faltas e 1 excesso. A `Img 8.jpeg` contém um martelo que o modelo contou duas vezes. A `Img 16.jpg` tem uma chave inglesa ajustável e uma chave de grifo, detectadas como classes distintas. A avaliação ainda precisa ser repetida com o novo limiar.
- Execuções reais no Roboflow: `Img 15.jpg` contra `nota_conforme.json` resultou em `conforme` (4/4 chaves ajustáveis). `Img 16.jpg` contra `nota_divergente.json` resultou em `divergente` por uma chave de grifo não prevista. Evidências em `docs/`.
- Testes automatizados: 66 passaram após a correção geométrica e o recorte interno das caixas, sem rede. Rafael abriu a webcam física e fez várias capturas antes da mudança mais recente. O sistema gravou fotos, relatórios e evidências e reconheceu martelo e chave de fenda. Com `nota_martelo_camera.json`, uma captura de 13/10/2026 retornou `conforme` (um martelo detectado; confiança 0,73). Outras capturas do mesmo cenário ficaram `divergente` por falsos positivos no teclado/entorno: `Screwdriver` 0,52 e `Tape Measure` 0,91. Numa captura anterior com martelo e chave de fenda, o martelo recebeu duas caixas (0,98 e 0,78), confirmando o risco de dupla contagem. Esses resultados foram obtidos antes do recorte interno; não são métricas do novo fluxo.

Em 13/10/2026, Rafael testou o fluxo com caixa aberta, martelo dentro e chave de fenda fora. Em `saidas/camera_20261013_202532`, o modelo de ferramentas gerou **3 caixas de martelo e 3 de chave de fenda** para dois objetos reais; o modelo de embalagens não encontrou caixa aberta aceita. `src/posprocessamento.py` consolida caixas muito sobrepostas, partes alinhadas de ferramentas longas e um fragmento pequeno no canto. Uma reprodução local das coordenadas salvas produziu **1 martelo, 1 chave de fenda e status `conforme`**; ela **não é uma nova inferência real**. Em novas fotos `camera_20261013_205602` a caixa foi chamada `Closed Cardboard Box` com 0,52; em `_205632`, `Open Cardboard Box` apareceu com 0,34, abaixo de 0,6. Nas sete capturas de `_205647` a `_205725`, a caixa aberta foi aceita com confiança entre 0,70 e 0,86. A caixa quase preenchia o recorte e o antigo rótulo azul caía fora da imagem; o desenho foi corrigido. Nessas fotos o martelo estava parcialmente coberto pela parede frontal, e o modelo de ferramentas frequentemente o chamou `Mallet` ou não o encontrou; a chave de fenda esperada também não estava claramente visível dentro do recorte. A nova análise interna tenta resolver a perda de escala e contexto, mas ainda precisa de teste real de Rafael. O ambiente do agente não conseguiu completar chamadas à API Roboflow, mesmo com rede liberada; **não declarar melhora de acurácia como validada**. Próximo teste: caixa inteira na área verde, abertura vista de cima, martelo e chave de fenda desobstruídos, nova captura e inspeção de `caixa_1_interior.jpg`, `analise_caixas.json` e `relatorio.json`.

## Arquitetura

```text
Imagem/quadros BGR ──> detector.py ──> aliases_classes ──> contagens
Nota JSON ────────────> nota.py ──────> de_para ──────────> comparador.py
                                                   ├──────> relatorio.json
                                                   └──────> visualizacao.py ──> imagem_anotada.jpg
```

Com `modelo_caixas_id` preenchido, o quadro vai aos dois modelos. Para cada caixa aberta aceita, a parte superior da caixa é recortada e enviada outra vez ao modelo de ferramentas. Detecções internas aceitas nesse recorte substituem as detecções gerais atribuídas àquela caixa; as externas permanecem. `src/posprocessamento.py` consolida detecções repetidas antes da contagem; `src/caixas.py` grava a distribuição em `analise_caixas.json`. Caixas não contam como itens da nota. A fração vertical de 78% do recorte é uma hipótese para evitar a parede frontal, não uma garantia de acurácia; objetos junto à frente ou muito encobertos exigem nova coleta e possivelmente dados rotulados/treino.

O arquivo `config.json` aponta o modelo e guarda `api_url`, `limiar_confianca`, `classes_ignoradas`, `aliases_classes`, `de_para` e `nomes_exibicao`. Classes brutas como `Adjustable Wrench` e `Pipe Wrench` são convertidas para `Wrench` e `PipeWrench`. O `de_para` mapeia FER-001 Pliers, FER-002 Screwdriver, FER-003 Wrench, FER-004 Hammer e FER-005 PipeWrench. Classes desconhecidas ficam visíveis como itens não previstos, em vez de serem descartadas silenciosamente.

O detector usa `inference-sdk` com array BGR e `model_id` de `config.json`. A chave fica no `.env` local e viaja no cabeçalho `Authorization`. A confiança mínima solicitada ao servidor é 0,1; o limiar de contagem atual é 0,6. Predições abaixo dele são listadas em `descartadas`. O formato interno de detecção é `{"classe":"Wrench","confianca":0.99,"caixa_xyxy":[x1,y1,x2,y2]}`.

## Contratos

Nota de entrada:

```json
{
  "nota_id": "NF-DEMO-002",
  "fornecedor": "Fornecedor Exemplo Ltda.",
  "itens": [{"codigo": "FER-003", "descricao": "Chave inglesa ajustável", "quantidade": 1}]
}
```

O código é texto; quantidade deve ser inteiro positivo. Códigos repetidos são somados. Código desconhecido, quantidade inválida ou JSON malformado geram `erro`. Quando a nota real tiver outro formato, criar um conversor de entrada sem mudar o formato interno.

Relatório estável:

```json
{
  "nota_id": "NF-DEMO-002",
  "imagem": "imagens/teste/Img 16.jpg",
  "status": "divergente",
  "linhas": [
    {"codigo": "FER-003", "item": "Chave inglesa ajustável", "classe": "Wrench", "esperado": 1, "detectado": 1, "delta": 0, "situacao": "igual"},
    {"codigo": "FER-005", "item": "Chave de grifo", "classe": "PipeWrench", "esperado": 0, "detectado": 1, "delta": 1, "situacao": "nao_previsto"}
  ],
  "descartadas": [],
  "avisos": [],
  "modelo_id": "tool-detection-4u0yd/15",
  "limiar_confianca": 0.5,
  "gerado_em": "2026-10-12T22:39:22-03:00"
}
```

O JSON acima é o relatório real anterior à mudança de limiar; o campo `limiar_confianca` das novas execuções será `0.6`.

`delta = detectado - esperado`. Situações: `igual`, `falta`, `excesso`, `nao_previsto`. `conforme` exige todas as linhas iguais; diferença dá `divergente`; falha técnica dá `erro` com causa em `avisos`. Não remova nem renomeie campos ou status. Em `nao_previsto`, `codigo` vem do `de_para` quando existir, senão é `null`. `conferir()` e `conferir_quadro()` retornam relatório `erro` nas falhas técnicas, sem transformar erro em conformidade.

Interfaces já disponíveis:

```python
from conferir import conferir, carregar_config, conferir_quadro
from nota import validar_nota

relatorio, pasta = conferir("foto.jpg", "nota.json")
config = carregar_config()
nota = validar_nota(dados_json, config["de_para"])
relatorio, evidencia_bgr = conferir_quadro(quadro_bgr, nota, config)
```

Para outra linguagem na mesma máquina, chamar `src/conferir.py --imagem ... --nota ... --json`. Códigos de saída: 0 conforme, 1 divergente, 2 erro. A CLI também grava relatório e evidência na pasta `--saida`.

## Execução local

```powershell
.venv\Scripts\python.exe src\conferir.py --imagem "imagens/teste/Img 15.jpg" --nota notas/nota_conforme.json
.venv\Scripts\python.exe src\conferir.py --imagem "imagens/teste/Img 16.jpg" --nota notas/nota_divergente.json
.venv\Scripts\python.exe src\camera.py --nota notas/nota_divergente.json --camera 0
.venv\Scripts\python.exe src\camera.py --nota notas/nota_caixa_aberta_demo.json --camera 0
.venv\Scripts\python.exe -m pytest
```

No teste com dois modelos, usar uma caixa aberta com um martelo dentro e uma chave de fenda fora dela, todos inteiros na área verde. `nota_caixa_aberta_demo.json` espera um de cada. Conferir a borda azul, `quadro_analisado.jpg`, `analise_caixas.json` e `relatorio.json`. O modelo de caixas é um candidato público aprovado para teste, ainda sem medição nas fotos do projeto: https://universe.roboflow.com/ssh-6xfsh/open-closed-cardbox.

Uma tentativa de conexão real a partir do ambiente automatizado desta sessão falhou com `HTTPClientError` **também no modelo anterior**, inclusive com o conjunto local de certificados e após liberar acesso à rede. Rafael executou os dois modelos no terminal normal e gerou várias capturas reais. O modelo de caixas aceitou a caixa aberta nas sete últimas; o recorte interno implementado depois ainda não foi testado nessa máquina.

O `.env` e o `.venv` são locais; nunca publique a chave. No Windows, usar o Python do `.venv`, `np.fromfile + cv2.imdecode` para ler imagens e `cv2.imencode + tofile` para gravar nomes com acentos. A prévia da câmera usa `cv2.VideoCapture(indice, cv2.CAP_DSHOW)`. O código de exibição usa Pillow para acentos.

## Próxima etapa: integração com o sistema do colega

Esta etapa precisa de cinco decisões de Rafael e do colega antes de implementar um adaptador:

1. Em que linguagem o orquestrador roda e se ele estará na mesma máquina.
2. Como a imagem chega: caminho, bytes, URL ou quadro de câmera.
3. Como a nota chega: arquivo JSON, objeto em memória ou formato de NF-e.
4. O que o orquestrador precisa de volta: status, relatório completo e/ou evidência.
5. Se a chamada espera resposta síncrona ou será por fila/pasta.

Se for Python no mesmo processo, usar `conferir()` ou `conferir_quadro()`. Se for outra linguagem na mesma máquina, usar a CLI `--json` e os códigos de saída. Se a troca for por arquivos, usar `--saida`. Para máquinas distintas, uma API HTTP é possível, mas ainda não foi decidida por Rafael. Após definir a interface, criar um teste de integração sem rede cobrindo `conforme`, `divergente` e `erro`.

## Critérios de aceite e riscos restantes

- [x] Gabarito de quatro imagens conferido por Rafael; modelo escolhido e configurado.
- [x] Uma foto conforme e outra divergente verificadas por inferência real e guardadas em `docs/`.
- [x] Câmera implementada, com saídas independentes por captura e testes sem webcam.
- [x] Testes automatizados passando (66 em 13/10/2026).
- [x] Webcam física abre e produz capturas, relatórios e evidências.
- [x] Prova manual de `conforme` pela webcam com nota correspondente a um martelo.
- [x] Área verde e dois modelos executados por Rafael em capturas reais.
- [ ] Nova prova real do filtro geométrico, inclusive com dois objetos iguais separados.
- [x] Modelo de caixas reconheceu a caixa aberta em sete capturas posteriores, embora tenha falhado nas primeiras.
- [ ] Recorte interno da caixa validado com uma nova inferência real.
- [ ] Interface com o sistema do colega definida e testada.
- [ ] Testes com fotos da câmera e peças/ferramentas no cenário real; quatro fotos de produto não bastam para garantir precisão.

Riscos principais: dupla contagem do martelo, falsos positivos no entorno, mudança de iluminação/fundo/ângulo, dependência de rede/serviço Roboflow e ausência de dados de peças automotivas. Nas capturas de 13/10, o limiar 0,60 retira a falsa chave de fenda 0,52 e preserva o martelo 0,73, mas não retira a falsa trena 0,91. Limiar 0,80 perderia esse martelo verdadeiro. A confiança 0,78 da segunda caixa em outra captura não mede probabilidade real de acerto. Rafael escolheu 0,60; não trocar modelo, treinar outro ou criar API sem decisão dele.

## Orientação para o próximo agente

Leia `AGENTS.md`, este documento, `README.md` e os testes. Preserve o contrato do relatório e a distinção `Wrench`/`PipeWrench`. Explique a Rafael cada etapa em linguagem simples e deixe as escolhas de produto e integração com ele. Não peça que Rafael programe. Primeiro valide numa nova captura o recorte interno da caixa; compare `caixa_1_interior.jpg` com o relatório e verifique se o martelo e a chave de fenda estão realmente visíveis. Não mude modelo, limiar ou treine sem decisão de Rafael. Depois reúna as cinco respostas de integração e implemente somente a forma escolhida. Nunca mostre ou copie `ROBOFLOW_API_KEY`.
