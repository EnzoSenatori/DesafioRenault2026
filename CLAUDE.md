# Desafio Renault 2026 — instruções para o Claude Code

As regras de trabalho valem para qualquer agente (Claude ou Codex) e ficam no `AGENTS.md`, importado abaixo. Este arquivo só acrescenta onde encontrar cada informação.

@AGENTS.md

## Onde está cada coisa

- **Estado técnico vigente:** `CONTINUIDADE.md`. É a fonte única de modelo, limiar, contratos, validações e pendências. Leia antes de editar código.
- **Apresentação pública:** `README.md` (instalação, execução, resultados e créditos).
- **Registros datados de passagem:** `docs/passagens/`. Servem como histórico; em caso de divergência, vale o `CONTINUIDADE.md`.
- **Histórico:** `docs/historico/` guarda o briefing da construção inicial e o guia de prompts de 12/10. É apenas registro: o modelo proelec3, o limiar 0,5 e a câmera como extra foram substituídos.

Ao mudar o estado do projeto, atualize o `CONTINUIDADE.md` e, se a mudança afetar o uso, o `README.md`; não crie outro documento de estado.
