# Orientações para continuar o Desafio Renault 2026

Estas regras valem para qualquer agente que trabalhe no repositório (Codex, Claude Code ou outro). O `CLAUDE.md` importa este arquivo.

## Colaboração com Rafael

Rafael decide as questões importantes; o agente implementa e testa. Perguntar antes de trocar modelo ou limiar, ampliar escopo, criar serviços pagos, publicar, mudar contratos ou escolher a forma de integração. Preparação local, inspeção e testes podem avançar. Não exigir que Rafael escreva código.

## Contexto e contratos

Leia CONTINUIDADE.md e README.md. CONTINUIDADE.md descreve o estado mais recente; instruções atuais de Rafael prevalecem. O MVP usa ferramentas como substitutas de peças automotivas. Não quebrar o relatório (seção “Contratos” do CONTINUIDADE.md, numerada 3.6 na versão de 12/10): não remover/renomear campos nem mudar os status conforme, divergente e erro. Campos adicionais exigem avaliar consumidores/testes.

## Convenções

- Cada função Python tem comentário breve acima de def; não usar docstrings.
- Variáveis, funções e mensagens em português.
- Texto de imagens via Pillow com fonte TTF para suportar acentos.
- Erros devem explicar o problema e a ação necessária.
- Não inventar respostas de API, versões, métricas ou resultados. Distinguir simulação e execução real.
- Testes novos sem rede, usando clientes falsos.
- Não inventar gabarito: contagens de referência precisam de validação humana.
- Nunca imprimir, registrar, copiar para artefatos ou versionar ROBOFLOW_API_KEY. O usuário pode configurá-la no .env local ignorado; verificar presença sem mostrar valor.

## Escopo

Treino/ajuste fino, Streamlit, banco, OCR de nota, vídeo com contagem acumulada, catálogos com kits e schemas versionados estão fora do escopo acordado. API web depende de decisão de Rafael/equipe. Não executar os prompts futuros automaticamente só porque estão na documentação.

## Windows

- Python compatível: 3.10 a 3.13; usar .venv\Scripts\python.exe após criar o ambiente.
- Imagens: np.fromfile + cv2.imdecode e cv2.imencode + tofile para caminhos com acentos/espaços.
- load_dotenv recebe caminho explícito do .env.
- Não somar quadros da câmera; captura é uma conferência independente.
- Não suprimir avisos globalmente por padrão; tratar aviso conhecido apenas quando necessário.

## Comandos na raiz

```powershell
# Criação inicial com um executável Python compatível verificado
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe src\conferir.py --imagem "imagens/teste/Img 16.jpg" --nota notas/nota_divergente.json
.venv\Scripts\python.exe src\conferir.py --imagem "imagens/teste/Img 16.jpg" --nota notas/nota_divergente.json --json
.venv\Scripts\python.exe src\testar_modelo.py
```

Inferência real requer chave e acesso ao Roboflow; testes automatizados usam clientes falsos. Saídas CLI: 0 conforme, 1 divergente, 2 erro. Preservar .env, .venv e saidas fora do versionamento.

## Repositório e documentação

O repositório canônico é github.com/enzosenatori/desafiorenault2026. A base de Rafael, desenvolvida a partir de um ZIP sem histórico Git, foi incorporada em 13/10/2026 na branch `integracao-rafael-2026-10-13`. Trabalhar em branch; publicar (push, PR) segue a regra de perguntar antes.

- `CONTINUIDADE.md`: fonte única do estado técnico. Atualizar a cada mudança de estado; não criar outro documento de estado.
- `README.md`: face pública (instalação, execução, resultados e créditos).
- `docs/passagens/`: registros datados de passagem, apenas histórico.
- `docs/historico/`: briefing da construção inicial (`briefing_inicial_claude.md`, antigo `CLAUDE.md`) e guia de prompts de 12/10 (`guia_prompts_codex_2026-10-12.pdf`); suas instruções técnicas e numerações de seção não valem mais.
