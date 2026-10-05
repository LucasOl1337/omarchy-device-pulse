# Auditoria: DevicePulse v1.1.1

Data: 05/10/2026.

## Base e candidato

Primeiro GitHub Release do projeto. Não havia tags, releases ou PRs publicados para esta linha. Base editorial: início do histórico, incluindo todas as capacidades presentes no candidato.

Candidato de código validado: `9114aea22cfda24eca99d2ab7ebee4659dfad5bb`. A tag `v1.1.1` inclui esse código e o commit seguinte apenas com notas, arte e esta auditoria. O SHA final da tag é conferido no remoto após o push.

Remoto oficial: https://github.com/LucasOl1337/omarchy-device-pulse. Branch `main`, uma worktree, limpa e sincronizada com `origin/main` antes da preparação. `git fetch --tags origin` executado. Nenhuma branch paralela ou PR a integrar.

## Matriz de evidências

| Resultado | Evidência | Situação e validação |
| --- | --- | --- |
| Baterias, Bluetooth, histórico e avisos | `a519d14`, collect.py, Content.qml | Integrado; testes de estados, histórico e faixas de aviso |
| X9 informa bateria | `67a5714`, decode_x9_reply, consulta HID | Integrado; receptor real retornou 90%, respostas inválidas rejeitadas |
| DPI e polling do K7 | `67a5714`, mouse.py, control.py, Content.qml | Integrado; testes de bytes preservados, confirmação e backups; hardware confirmou 800 DPI e 2000 Hz |
| Painel compacto e edição preservada | `67a5714`, Panel.qml, Content.qml | Integrado; preview nativo na bancada e edição por Enter verificados nesta sessão |
| Barra deixa de carregar interface antiga | `9114aea`, install.py | Integrado; 2 testes de geração por hash e IPC da barra comprovam URL nova |

## Validações e implantação

`python3 -m unittest discover -s tests -v`: 20 testes passaram. `omarchy-plugin-validate .`: passou. `git diff --check`: passou. A versão 1.1.1 foi instalada na máquina por `python3 install.py`; timer ativo e diagnóstico IPC retornou `compact-device-settings`, versão 1.1.1 e cinco dispositivos. Não houve mudança de configuração de mouse neste release.

## Agentes e sessões

- Codex: esta conversa, sessão `01a10b89-ddb6-7973-a1f9-fef9dd71f84c`, implementou e publicou as duas entregas. Confiança alta, com código, comandos de teste e diagnóstico da barra nesta sessão.
- Codex: índices locais de 05/10 também apontaram referências nas sessões `01a10b9c-424f-7e91-843e-de132fe576b5` e `01a10bd8-99c2-7801-b6ed-0f8b6889fecd`. Referência ao caminho não comprova contribuição; nenhuma entrega foi atribuída a elas.
- Claude: índice de diretórios em `.claude/projects`, nenhuma sessão com caminho de projeto relacionado encontrada nessa fonte.
- Hermes: índice `.hermes/sessions/sessions.json`, nenhum caminho alvo encontrado.
- Grok: índice de diretórios em `.grok/sessions`, nenhum caminho alvo encontrado.
- Pi: índice de diretórios em `.pi/agent/sessions`, nenhum caminho alvo encontrado.
- Orca: fonte local indisponível, nenhum diretório de histórico identificado.

A consulta ficou nos índices e nas referências aos caminhos dos dois projetos. Ausência nesses índices não prova ausência de trabalho de outro agente. Transcrições brutas não entram no release.

## Publicação, exclusões e limites

Notas e arte incluídas no candidato, sob docs/releases. Código licenciado em MIT. Pacote de fontes gerado com git archive da tag e anexado ao GitHub Release com PNG e SVG. Sem credenciais, caches Python, estado local ou dados de runtime nos commits.

Migrations de banco remoto: não aplicável. Deploy em servidor/cloud: não aplicável, plugin desktop; a implantação aplicável é a instalação local verificada. CI remoto obrigatório: não existe neste projeto. Sem tarefas pendentes de integração no escopo.

As limitações de hardware/provedor constam nas notas e no README. A leitura de quotas segue a API do 9Router; a edição de mouse fica restrita ao modelo validado. A verificação remota confere tag, SHA, release publicado e assets depois de cada operação.
