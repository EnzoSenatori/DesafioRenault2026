# Desafio Renault 2026 — guia de continuidade para Enzo

> **Registro datado de passagem**, recebido de Rafael em 13/10/2026 (arquivo original na raiz: `GUIA_CONTINUIDADE_ENZO.md`). Foi movido para `docs/passagens/` na incorporação ao repositório e não é mais atualizado. O estado vigente está em `CONTINUIDADE.md`. A incorporação já foi feita na branch `integracao-rafael-2026-10-13`; as instruções de receber o ZIP e comparar com o repositório ficam como histórico.

**De:** Rafael / trabalho local no Codex  
**Para:** Enzo Senatori  
**Data:** 13/10/2026  
**Referência:** `GUIA_PROMPTS_CODEX.pdf` (hoje em `docs/historico/guia_prompts_codex_2026-10-12.pdf`) enviado por Enzo em 12/10/2026, mais o código e as execuções reais posteriores.

Este documento é o estado atual para você retomar a base e a documentação do projeto. O PDF original estabeleceu a sequência **preparar → avaliar modelos → adotar um modelo → câmera → integração**. Os quatro primeiros passos foram executados; o quinto ainda precisa de decisões conjuntas. Rafael continua responsável pelo desenvolvimento com auxílio do Codex e decide mudanças importantes. A pasta local veio do ZIP `DesafioRenault2026-main.zip`, sem histórico Git; as mudanças descritas aqui ainda precisam ser incorporadas ao repositório canônico.

**Como receber a entrega:** descompacte `DesafioRenault2026_para_Enzo_2026-10-13.zip`. Este guia, o código, `requirements.txt`, configuração, notas de exemplo, testes, gabarito e três capturas diagnósticas selecionadas estão dentro dele. As capturas estão em `evidencias_capturas/`, com somente o quadro analisado, resultado visual e JSONs; a foto completa da webcam não foi incluída. O ZIP também não contém `.env`, chave, `.venv` nem todas as saídas locais. Para executar inferência real, crie um `.env` próprio a partir de `.env.example` e use uma chave do Roboflow autorizada para sua conta. Para documentação e testes automáticos, a chave não é necessária.

**Prioridade imediata:** incorporar esta base ao repositório canônico, preservar os contratos abaixo e validar o recorte interno da caixa numa nova imagem real. A última alteração foi verificada por testes automáticos, mas Rafael informou que não terá tempo de fazer essa nova captura agora. Não registre melhora de precisão como comprovada. Antes de mudar modelo, limiar, treinamento ou forma de integração, alinhe a decisão com Rafael.

## 1. O que o sistema faz

O MVP recebe uma foto (arquivo ou captura da câmera) e uma nota fiscal **simulada em JSON**. Consulta um modelo de detecção hospedado no Roboflow, normaliza as classes, conta ferramentas, compara com as quantidades da nota e produz `relatorio.json` e `imagem_anotada.jpg`. As ferramentas substituem peças automotivas apenas para demonstrar o fluxo; **não há detector validado para peças Renault nem OCR de NF-e**.

O status final é `conforme` se todos os itens batem, `divergente` se há falta/excesso/item não previsto e `erro` se a entrada ou a inferência falha. O código não converte falha técnica em conformidade.

## 2. Estado de cada etapa do PDF

| Etapa do guia de 12/10 | Estado em 13/10 | Evidência |
|---|---|---|
| Preparação e `AGENTS.md` | Concluída | Python 3.12 local, dependências instaladas, chave no `.env` ignorado e testes automatizados. |
| Prompt 1: avaliar modelos | Concluído para **4 fotos com gabarito humano** | `src/avaliar_modelos.py`, `modelos_avaliacao.json`, `imagens/teste/gabarito.json`, resultados em `saidas/avaliacao/`. |
| Prompt 1b: adotar modelo | Concluído por decisão de Rafael | `config.json`, notas de exemplo, `docs/` e README atualizados. |
| Prompt 2: câmera | Implementado e exercitado em capturas reais com área verde | `src/camera.py`, `tests/test_camera.py`; as capturas revelaram duplicações que motivaram o filtro geométrico. |
| Expansão solicitada por Rafael: caixas abertas | Dois modelos ativos; caixa aceita em 7 capturas posteriores; recorte interno implementado, aguardando teste real | `src/caixas.py`, `tests/test_caixas.py`; Rafael aprovou `open-closed-cardbox/2` como candidato para teste. |
| Prompt 3a/3b: integração | Pendente | A forma depende das cinco respostas da seção 8 abaixo. Nenhuma API foi criada. |

**Validação automatizada atual:** 66 testes passaram em 13/10/2026, sem rede nem webcam. Rafael usou a borda verde e os dois modelos em várias capturas; a caixa foi aceita nas sete últimas, mas o modelo de ferramentas errou o martelo parcialmente encoberto. O recorte interno foi testado com respostas simuladas e precisa de captura real. As métricas de modelos e as imagens em `docs/` foram produzidas antes da alteração do limiar, com 0,5; não devem ser apresentadas como medição do fluxo atual a 0,6.

## 3. Modelo e resultados observados

Rafael escolheu **Tool Detection**, de GantrySystem, ID `tool-detection-4u0yd/15`, publicado no [Roboflow Universe](https://universe.roboflow.com/gantrysystem/tool-detection-4u0yd) sob CC BY 4.0. A escolha preserva a distinção que Rafael exigiu: **chave inglesa ajustável** (`Wrench`) e **chave de grifo** (`PipeWrench`) são classes diferentes. A versão inicial de proelec3 não distinguia as duas nas fotos do projeto.

No gabarito de quatro imagens confirmado por Rafael, com limiar **0,5**:

| Modelo | Fotos com contagem exata | Itens corretos | Faltas | Excessos |
|---|---:|---:|---:|---:|
| proelec3 `tools-classification-byznk/2` | 0/4 | 4 | 4 | 0 |
| Ruri `mechanical-tools-83ynn/2` | 3/4 | 7 | 1 | 0 |
| GantrySystem `tool-detection-4u0yd/15` | **3/4** | **8** | **0** | 1 |
| CETI `tools-v1/1` | 2/4 | 7 | 1 | 1 |

O excesso do GantrySystem foi um martelo contado duas vezes na `Img 8.jpeg`. A `Img 15.jpg` teve quatro chaves ajustáveis corretamente e resultou `conforme` contra `nota_conforme.json`. A `Img 16.jpg` teve uma ajustável e uma de grifo corretamente; contra `nota_divergente.json` (que pede apenas a ajustável), resultou `divergente` por uma chave de grifo não prevista. As evidências reais estão em `docs/exemplo_conforme.jpg`, `docs/exemplo_divergente.jpg` e `docs/exemplo_relatorio.json`.

**Diferença em relação ao Prompt 1b do PDF:** ele sugeria uma nota divergente com quantidade declarada maior que a foto. Rafael escolheu uma demonstração mais importante para este projeto: a **peça de outro tipo** presente na imagem e ausente da nota. O contrato do relatório permaneceu igual.

## 4. Câmera: o que funcionou e o que mudou agora

Rafael abriu a webcam física, fez várias capturas e conferiu ferramentas reais. Com a nota de um martelo, uma captura deu **`conforme`**: 1 martelo detectado com confiança 0,73. Outras capturas tiveram falsos positivos no entorno da ferramenta: uma “chave de fenda” 0,52 no teclado e uma “trena” 0,91 na parte superior da foto. Uma foto com martelo e chave de fenda contou o mesmo martelo duas vezes, com 0,98 e 0,78. Esses resultados mostram que uma boa pontuação individual **não garante** uma identificação correta nem uma contagem exata.

Rafael decidiu elevar o limiar de **0,5 para 0,6**. Isso retira a falsa chave de fenda 0,52 e preserva o martelo real 0,73. Não retira a falsa trena 0,91 nem a segunda caixa do martelo 0,78. Ele também pediu uma **área de leitura** na webcam. Ela já foi implementada:

- a prévia mostra uma borda verde (área proporcional x=25%-100%, y=16%-92%);
- o detector recebe **somente** os pixels dentro da borda;
- cada captura guarda `quadro_original.jpg` (foto inteira), `quadro_analisado.jpg` (recorte enviado ao modelo), `relatorio.json` e `imagem_anotada.jpg` (evidência sobre o recorte);
- o campo `imagem` do relatório continua apontando para a foto inteira; os campos existentes do relatório não foram removidos nem renomeados;
- a área verde foi inspecionada numa foto anterior e depois testada por Rafael em capturas reais de caixa aberta e ferramentas.

Não devemos dizer que a área verde “resolveu a acurácia” antes do teste prático. Também não devemos ignorar silenciosamente todas as classes fora da nota: detectar um item não previsto é parte do objetivo da conferência.

### Expansão aprovada em 13/10: caixas abertas

Rafael decidiu manter a área verde e **não aumentar o limiar** (continua 0,6). A primeira etapa usa as ferramentas atuais como produtos visíveis. `src/caixas.py` chama o detector de caixas no recorte verde inteiro e o GantrySystem tanto no recorte inteiro quanto na parte superior de cada abertura detectada. Se o recorte interno encontra ferramentas aceitas, substitui as detecções gerais atribuídas àquela caixa; itens externos continuam na análise geral. Cada ferramenta aceita é associada a uma caixa ou a `produtos_fora` e entra uma vez na comparação. A evidência marca as caixas em azul com rótulo visível na borda. `analise_caixas.json` inclui `recortes_internos` e cada `caixa_N_interior.jpg` mostra o que foi enviado ao segundo detector; `relatorio.json` preserva seus campos e status. Se um dos serviços falhar, a conferência retorna `erro`.

Rafael aprovou o candidato público [Open/closed cardbox](https://universe.roboflow.com/ssh-6xfsh/open-closed-cardbox), versão `open-closed-cardbox/2`, para o primeiro teste. Ele está ativo em `modelo_caixas_id` no `config.json`; apenas `Open Cardboard Box` entra na associação. Nas capturas `_205602` e `_205632`, a caixa não passou pelo limiar: na primeira, o modelo sugeriu `Closed Cardboard Box` a 0,52; na segunda, `Open Cardboard Box` a 0,34. Nas sete capturas seguintes `_205647` a `_205725`, a caixa aberta passou com 0,70–0,86. Ainda não há medida confiável de acerto nesse cenário. A regra geométrica por centro é inicial e não confirma profundidade física quando objetos ou caixas se sobrepõem.

O ZIP traz três casos para reproduzir e discutir, sem as fotos completas: `202532` mostra um martelo na caixa e uma chave de fenda externa; o detector gerou 3+3 caixas antes do filtro. `205632` mostra uma caixa aberta que ficou abaixo de 0,6 e um martelo parcialmente coberto; o modelo misturou `Hammer` e `Mallet`. `205725` mostra uma caixa aceita a 0,75, mas o martelo muito encoberto foi classificado como `Mallet` a 0,84 e a chave de fenda exigida pela nota não está no quadro analisado. O rótulo azul da evidência antiga ficou cortado pela borda; isso foi corrigido no código, mas as evidências salvas são históricas. Não mapear `Mallet` automaticamente para `Hammer`, pois são tipos diferentes de ferramenta. Um recorte da caixa não revela partes escondidas: caso o erro persista com a ferramenta inteira visível, a melhoria provável exige fotos anotadas representativas e avaliação de treino/modelo, decisão de Rafael.

Na captura `camera_20261013_202532`, o detector de ferramentas produziu **3 martelos e 3 chaves de fenda** apesar de haver apenas **um de cada**. As coordenadas mostram caixas fragmentadas sobre o mesmo objeto e uma falsa caixa de martelo no canto. `src/posprocessamento.py` passou a consolidar caixas muito sobrepostas ou partes alinhadas de objetos longos e a retirar um fragmento pequeno no canto quando outra detecção maior e mais forte da mesma classe está próxima. A reprodução **sem rede** dessa captura passou para 1 martelo, 1 chave de fenda e `conforme`, com quatro detecções registradas como suprimidas. Isso precisa de nova inferência real. O relatório agora avisa quando nenhuma caixa aberta foi detectada; `analise_caixas.json` lista as detecções suprimidas e as caixas ignoradas. O limiar permanece **0,6**. Segmentar não foi adotado: um modelo de máscaras exigiria dados/modelo próprios e não garante resolver duplicações que começam na detecção.

## 5. Arquitetura e contratos que devem ser preservados

`src/detector.py` usa `inference-sdk` para obter predições do Roboflow e converter centro/largura/altura em caixas `xyxy`. `src/posprocessamento.py` consolida detecções fragmentadas antes da contagem. `src/caixas.py` separa o resultado de embalagens e ferramentas, faz a segunda inferência da abertura e associa produtos à caixa ou à área externa. `aliases_classes` no `config.json` traduz nomes brutos das ferramentas, incluindo `Adjustable Wrench → Wrench` e `Pipe Wrench → PipeWrench`. `src/nota.py` valida e agrega itens; `src/comparador.py` calcula diferenças; `src/visualizacao.py` desenha ferramentas e painel; `src/conferir.py` orquestra arquivo ou quadro BGR; `src/camera.py` seleciona o quadro e o recorte.

O `de_para` atual associa: FER-001 `Pliers`, FER-002 `Screwdriver`, FER-003 `Wrench`, FER-004 `Hammer`, FER-005 `PipeWrench`. O limiar atual em `config.json` é **0,6**. A confiança mínima pedida ao servidor é 0,1, para que predições abaixo do limiar ainda apareçam em `descartadas`. `classes_ignoradas` está vazio.

Nota simulada (exemplo):

```json
{
  "nota_id": "NF-CAMERA-MARTELO",
  "fornecedor": "Demonstração da câmera",
  "itens": [
    {"codigo": "FER-004", "descricao": "Martelo", "quantidade": 1}
  ]
}
```

Quantidade deve ser inteiro positivo. Códigos desconhecidos e JSON inválido produzem `erro`. Linhas repetidas do mesmo código são somadas. Se uma NF-e real tiver outro formato, criar um **conversor de entrada** em vez de alterar esse contrato.

Campos atuais de `relatorio.json`: `nota_id`, `imagem`, `status`, `linhas`, `descartadas`, `avisos`, `modelo_id`, `limiar_confianca`, `gerado_em`. Cada linha traz `codigo`, `item`, `classe`, `esperado`, `detectado`, `delta` e `situacao` (`igual`, `falta`, `excesso` ou `nao_previsto`). O guia em PDF e o `CONTINUIDADE.md` exigem preservar esses campos e os três status.

## 6. Como reproduzir localmente

Na raiz da pasta do projeto:

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe src\conferir.py --imagem "imagens/teste/Img 15.jpg" --nota notas/nota_conforme.json
.venv\Scripts\python.exe src\conferir.py --imagem "imagens/teste/Img 16.jpg" --nota notas/nota_divergente.json
.venv\Scripts\python.exe src\camera.py --nota notas/nota_martelo_camera.json --camera 0
.venv\Scripts\python.exe src\camera.py --nota notas/nota_caixa_aberta_demo.json --camera 0
```

No Windows, usar Python 3.10–3.13 e o `.venv`. A chave `ROBOFLOW_API_KEY` fica no `.env` local, fora do Git; não copiá-la para documentação, relatórios ou logs. Inferência real depende da rede/Roboflow. Num computador específico houve necessidade de um conjunto local de certificados para a conexão TLS; a verificação TLS ficou ativa. Não incorporar caminhos pessoais desse computador ao repositório.

**Próximo teste prático, quando houver alguém disponível:** fechar qualquer janela antiga de câmera, abrir o comando de câmera com `nota_caixa_aberta_demo.json`, posicionar **uma caixa aberta e ferramentas inteiras dentro da borda verde** e pressionar espaço. Conferir `quadro_analisado.jpg`, `caixa_1_interior.jpg`, `analise_caixas.json` e `relatorio.json` na pasta nova de `saidas/`. Repetir com martelo em outra orientação e com caixa vazia para observar falsos positivos. Se a borda cortar a ferramenta, reposicioná-la; só alterar a geometria do recorte após revisar as fotos. Fotos completas da webcam permanecem locais; o ZIP contém apenas os três recortes diagnósticos selecionados.

**Próxima validação após o recorte interno:** usar o segundo comando da câmera, uma caixa aberta com **um martelo dentro** e **uma chave de fenda fora da caixa**, todos inteiros na área verde e com a abertura vista ligeiramente de cima. Conferir `relatorio.json`, a caixa azul na evidência, `caixa_1_interior.jpg`, `produtos_fora`, `recortes_internos`, `deteccoes_suprimidas` e `caixas_ignoradas` em `analise_caixas.json`. Repetir com **dois martelos reais separados** para verificar que o filtro preserva a quantidade dois. A reprodução local anterior não substitui essas capturas.

O ambiente automatizado do agente não alcançou o Roboflow e recebeu `HTTPClientError` mesmo depois de liberar a rede. Rafael, porém, conseguiu executar os dois modelos no terminal normal e gerou as capturas reais citadas acima. Os **66 testes automatizados** passaram sem rede; a correção de recorte foi validada com respostas simuladas, não numa nova chamada real ao serviço.

## 7. Próximos pontos para qualidade

1. **Medir o fluxo atual** com imagens de câmera rotuladas por pessoa, incluindo martelo, chave de fenda, inglesa, grifo, combinações e área vazia. Registrar contagem exata por imagem, faltas e excessos. Quatro fotos de produto não estimam desempenho da webcam.
2. **Ajustar enquadramento e iluminação** antes de mexer novamente no limiar. Fundo simples, ferramenta inteira na área verde e câmera estável reduzem distrações.
3. **Validar o filtro geométrico** com novos quadros, incluindo dois objetos da mesma classe próximos; contar suprimidas e revisar cada caixa para não fundir ferramentas reais.
4. **Investigar o modelo de caixas** nas fotos em que confundiu aberta/fechada ou ficou abaixo de 0,6. Inspecionar `caixas_ignoradas` e enquadramento antes de propor limiar próprio, outro modelo ou treino. As capturas seguintes mostram que ele pode detectar essa caixa quando a posição muda.
5. **Considerar treino/ajuste fino** em fotos reais, inclusive “negativos difíceis” como teclado, se os erros persistirem. Rafael decide esse investimento depois da avaliação.

Riscos: falsos positivos com confiança alta (trena 0,91), duplicação do martelo, perda de ferramentas em recortes mal posicionados, mudança de luz/ângulo e dependência de serviço externo.

## 8. O que precisamos decidir juntos para a integração

O **Prompt 3a/3b do PDF ainda não foi executado**. Antes dele, responder com Rafael:

1. Em que linguagem e ambiente o outro sistema roda? Mesma máquina?
2. A imagem chega como caminho de arquivo, bytes, URL ou quadro da câmera?
3. A nota chega como JSON de arquivo/objeto ou outro formato (ex.: XML de NF-e)?
4. O orquestrador precisa de status, relatório inteiro e/ou imagem de evidência?
5. A chamada é síncrona ou por fila/pasta?

Se for Python no mesmo processo, já existem `conferir()` e `conferir_quadro()`. Para outra linguagem na mesma máquina, a CLI `--json` devolve relatório e códigos 0/1/2; `--saida` permite troca por arquivos. Uma API HTTP só deve ser construída se a arquitetura exigir comunicação entre máquinas **e Rafael/equipe aprovarem**. O teste de integração deve cobrir `conforme`, `divergente` e `erro` sem rede.

## 9. Arquivos alterados e responsabilidades

Principais arquivos adicionados: `AGENTS.md`, `src/avaliar_modelos.py`, `src/camera.py`, `src/caixas.py`, `src/posprocessamento.py`, `modelos_avaliacao.json`, `imagens/teste/gabarito.json`, `tests/test_avaliar_modelos.py`, `tests/test_camera.py`, `tests/test_caixas.py`, `tests/test_posprocessamento.py`, `notas/nota_martelo_camera.json`, `notas/nota_chave_fenda_camera.json` e `notas/nota_caixa_aberta_demo.json`. Principais arquivos atualizados: `config.json`, `src/detector.py`, `src/conferir.py`, `src/visualizacao.py`, `tests/test_conferir.py`, as duas notas de demonstração, `README.md`, `CONTINUIDADE.md`, `CLAUDE.md` e os exemplos de `docs/`.

`saidas/`, `.env` e `.venv/` são locais/ignorados; não devem entrar no repositório. Como a origem foi um ZIP sem `.git`, a comparação e o commit no repositório do Enzo ainda não aconteceram. Enzo pode revisar e incorporar a base/documentação; Rafael conduz o desenvolvimento e decide os ajustes de modelo, limiar, escopo e integração.

**Prompt sugerido para Claude/Codex na máquina do Enzo:** “Leia `AGENTS.md`, `docs/passagens/2026-10-13_guia_continuidade_enzo.md`, `CONTINUIDADE.md` e `README.md` antes de editar. Recebi um ZIP sem `.git` nem chave do Roboflow. Compare seus arquivos com o repositório canônico antes de incorporar mudanças. Execute os testes sem rede e analise os três casos em `evidencias_capturas/`. O modelo de caixa foi aceito em fotos posteriores, mas o martelo parcialmente oculto foi chamado de `Mallet`; a alteração que recorta o interior ainda não foi testada com inferência real. Preserve `relatorio.json`, os status e a distinção `Wrench`/`PipeWrench`; não mude limiar 0,6 ou modelos sem decisão de Rafael. Prepare documentação e integração somente após confirmar os cinco pontos da seção 8 com Rafael. Registre separadamente fatos observados, hipóteses e validações pendentes.”
