# Verificação final do Hera

Data da verificação: 22/08/2026.

## Caso documental real

O extrator foi executado contra o histórico oficial fornecido, sem copiar o documento ou seus dados pessoais para o projeto distribuído.

Resultado consolidado:

| Indicador | Resultado |
|---|---:|
| Disciplinas principais | 49 |
| Aprovadas | 26 |
| Dispensadas | 4 |
| Em curso | 8 |
| A cursar | 11 |
| Registros repetidos consolidados | 4 |
| Cargas preenchidas pela matriz | 19 |
| Disciplinas sem correspondência | 0 |
| Carga horária exigida | 4.148 h |
| Carga horária cumprida | 2.432 h |
| Atividades complementares exigidas | 82 h |
| Atividades complementares concluídas | 0 h |
| IRA | 7,1250 |

Também foi verificado que LIBRAS é associada à Optativa I e não cria uma segunda exigência curricular.

## Testes executados

- 10 testes automatizados do extrator, banco e API: aprovados.
- 2 regressões documentais opcionais: não executadas por dependerem de um histórico externo específico.
- Build de produção do frontend: aprovado.
- Verificação estática do frontend: aprovada.
- Teste da interface HTML compilada: aprovado.
- PDF real de matriz: 60 disciplinas e 4.000 horas, sem avisos nem caracteres corrompidos.
- Revisão, edição, confirmação e exclusão de matriz importada: aprovadas.
- Edição de disciplinas antes e depois da confirmação: aprovada.
- Importação e confirmação transacional em banco temporário: aprovada.
- Edição e exclusão integral de estudante: aprovadas.
- Demanda, formandos, simulação, recomendações, turmas e conflitos: aprovados.
- Exportações individuais e de demanda para Excel e PDF: aprovadas.
- Criação de backup SQLite: aprovada.
- Exclusão controlada e restauração do backup SQLite: aprovadas.
- Executável portátil real: inicialização, API, interface, banco atual e relatórios aprovados.
- Busca pelo nome anterior em código, interface e artefatos ativos: nenhuma ocorrência.

## Executável verificado

- Arquivo: `dist\Hera.exe`
- Tamanho: 45.614.016 bytes
- SHA-256: `64362390433210730AB5B43D38DC2694348A7718811F32E4EBD6BC629C76E75E`
- Assinatura digital: ainda não aplicada; será uma etapa separada de publicação.

## Dados deliberadamente não inventados

- Segunda matriz curricular.
- Pré-requisitos oficiais.
- Equivalências entre matrizes.
- Professores disponíveis.
- Salas, laboratórios e campos de estágio.
- Intenção de matrícula dos estudantes.

Esses dados permanecem configuráveis ou são indicados como indeterminados até validação da coordenação.
