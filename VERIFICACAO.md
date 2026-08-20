# Verificação da versão beta

Data da verificação: 20/08/2026.

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

- 7 testes automatizados do extrator e da API: aprovados.
- Build de produção do frontend: aprovado.
- Verificação estática do frontend: aprovada.
- Importação e confirmação transacional em banco temporário: aprovada.
- Geração de 11 linhas de demanda a partir do caso real: aprovada.
- Exportação individual para Excel: aprovada.
- Exportação da demanda para PDF: aprovada.
- Criação de backup SQLite: aprovada.
- Exclusão controlada e restauração do backup SQLite: aprovadas.
- Busca por CPF, RG, matrícula e nome pessoal nos arquivos distribuídos: nenhuma ocorrência.

## Dados deliberadamente não inventados

- Segunda matriz curricular.
- Pré-requisitos oficiais.
- Equivalências entre matrizes.
- Professores disponíveis.
- Salas, laboratórios e campos de estágio.
- Intenção de matrícula dos estudantes.

Esses dados permanecem configuráveis ou são indicados como indeterminados até validação da coordenação.
