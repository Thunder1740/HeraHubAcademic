# FarmaHub Acadêmico

Sistema local de inteligência acadêmica para a coordenação do curso de Farmácia da ULBRA Canoas. O FarmaHub lê históricos escolares oficiais em PDF, apresenta os dados para conferência, mantém uma base SQLite e transforma as pendências curriculares em indicadores de demanda, simulações e relatórios.

## O que já funciona

- Importação individual ou em lote de históricos digitais da ULBRA.
- Revisão antes da confirmação.
- Extração de nome, matrícula, curso, disciplinas, notas, frequências, períodos, carga horária e situação.
- Consolidação de reprovações antigas, dispensas repetidas e optativas.
- Cruzamento com a matriz curricular fornecida, contendo 50 componentes, incluindo atividades complementares.
- Perfil individual e atualização de estudantes existentes pela matrícula.
- Dashboard, ranking de demanda, formandos e estágios.
- Cadastro de novas matrizes e componentes.
- Registro manual de situação, previsão, semestre, turno e intenção de matrícula.
- Simulação de turmas e recomendação com prioridade lexicográfica para formandos.
- Grade preliminar e detecção de conflitos de estudantes, professores e salas.
- Exportação de históricos e demanda em Excel e PDF.
- Backup e restauração do banco SQLite.
- Execução restrita a `127.0.0.1`, sem login na versão beta.

## Requisitos do computador

### Usando o executável (recomendado no Windows)

Abra `dist\FarmaHub Academico.exe` com dois cliques. O navegador será aberto automaticamente e não é necessário ter Python ou Node.js para usar esse arquivo.

O Windows pode exibir um aviso de aplicativo não reconhecido porque esta versão acadêmica não possui certificado de assinatura digital. Nesse caso, confira se o arquivo veio desta pasta e use **Mais informações > Executar assim mesmo**.

Os dados do executável ficam em `%LOCALAPPDATA%\FarmaHub Academico\data\farmahub.db` e permanecem salvos entre as execuções.

### Usando o código-fonte

Instale:

1. Python 3.12 ou mais recente: <https://www.python.org/downloads/>
2. Node.js 22 ou mais recente: <https://nodejs.org/>
3. Um navegador atualizado, preferencialmente Chrome, Edge ou Firefox.

No instalador do Python para Windows, marque **Add Python to PATH**.

## Inicialização simples

### Windows

Clique duas vezes em:

`scripts\iniciar.bat`

Na primeira execução, o computador instalará as dependências gratuitas. Quando aparecer a mensagem de confirmação, abra:

<http://127.0.0.1:3000>

Mantenha as janelas abertas enquanto estiver usando o sistema.

### Linux ou macOS

Abra o terminal na pasta do FarmaHub e execute:

```bash
chmod +x scripts/iniciar.sh
./scripts/iniciar.sh
```

Depois, abra <http://127.0.0.1:3000>.

## Inicialização manual

Crie o ambiente Python e instale as dependências:

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
npm install
```

No primeiro terminal:

```bash
cd backend
../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

No segundo terminal, na pasta principal:

```bash
npm run dev -- --host 127.0.0.1 --port 3000
```

## Primeiro uso

1. Abra **Configurações**.
2. Confira o semestre de referência, a capacidade padrão e o ano dos formandos.
3. Abra **Matrizes Curriculares** e confira a matriz de 2021.
4. Abra **Importar Históricos**.
5. Selecione a matriz e o semestre de referência.
6. Envie um ou mais PDFs.
7. Revise nome, matrícula, situação, previsão e disciplinas.
8. Confirme a importação.

O banco só é atualizado após a confirmação. Um novo histórico com a mesma matrícula atualiza o perfil existente.

## Como interpretar a demanda

- **Necessita cursar:** a disciplina está como “A Cursar”.
- **Apto:** todos os pré-requisitos cadastrados foram concluídos.
- **Potencialmente apto:** um pré-requisito está em curso e pode ser concluído.
- **Não apto:** há pré-requisito conhecido ainda pendente.
- **Indeterminada:** não existem regras de pré-requisito suficientes. Esta é a situação padrão enquanto as regras oficiais não forem fornecidas.
- **Interesse:** a coordenadora marcou que o estudante pretende cursar a disciplina.

Disciplinas “Em Curso” não entram como demanda futura, pois o sistema adota a projeção otimista solicitada. Reprovações antigas permanecem nas tentativas, mas uma aprovação posterior prevalece no histórico consolidado.

## Formandos

Abra o perfil do estudante e altere a situação para **Formando**, ou informe uma previsão de conclusão que comece com o ano definido em Configurações. A recomendação automática sempre ordena primeiro as disciplinas que afetam formandos.

## Pré-requisitos

A documentação fornecida não contém pré-requisitos. Por segurança, o sistema não os inventa. Em **Matrizes Curriculares**, use a seção **Cadastrar pré-requisito confirmado** apenas depois de consultar a regra institucional. A elegibilidade permanece “Indeterminada” enquanto nenhuma regra oficial estiver cadastrada.

## Relatórios

Em **Relatórios**, baixe a demanda consolidada em Excel ou PDF. Para relatórios individuais, abra o perfil do estudante e use os botões **Excel** ou **PDF**.

Os relatórios não incluem CPF, RG nem data de nascimento.

## Backup

Abra **Configurações** e clique em **Baixar backup**. Guarde o arquivo `.db` em local institucional protegido.

Para restaurar:

1. Clique em **Restaurar backup**.
2. Selecione um backup criado pelo FarmaHub.
3. Confirme a substituição.
4. Recarregue a página.

Faça um backup antes de importações em grande lote e antes de qualquer atualização do sistema.

## Onde ficam os dados

O banco local fica em:

`data/farmahub.db`

Os PDFs originais não são preservados por padrão. O sistema guarda apenas os dados acadêmicos estruturados necessários. CPF, RG e nascimento não são armazenados.

## Testes

Para testar o backend:

```bash
cd backend
../.venv/bin/pytest -q
```

Para executar também a regressão com um histórico oficial, indique o arquivo:

```bash
FARMAHUB_REFERENCE_PDF="/caminho/historico.pdf" ../.venv/bin/pytest -q
```

Para verificar o frontend:

```bash
npm run build
```

## Solução de problemas

### A tela informa que o serviço local não responde

Verifique se a janela do backend continua aberta e se <http://127.0.0.1:8000/api/health> mostra `status: ok`.

### A porta 3000 ou 8000 já está em uso

Feche outra execução do FarmaHub. Se necessário, reinicie o computador.

### O PDF não foi reconhecido

Confirme que é um PDF oficial digital e não apenas uma fotografia. O extrator foi validado para o modelo fornecido. PDFs com outro formato devem aparecer como erro sem interromper os demais arquivos do lote.

### Uma disciplina ficou sem correspondência

Confira a matriz escolhida e o nome da disciplina na tela de revisão. Não confirme uma equivalência entre matrizes sem validação da coordenação.

### A elegibilidade aparece como indeterminada

Isso é esperado enquanto os pré-requisitos oficiais não forem cadastrados. O FarmaHub não presume que uma disciplina seja requisito apenas por estar em semestre anterior.

## Limitações conhecidas da versão beta

- A segunda matriz curricular ainda não foi fornecida.
- Pré-requisitos e equivalências oficiais ainda dependem de dados institucionais; o sistema oferece cadastro manual e endpoints de equivalência confirmada.
- A disponibilidade de professores, salas, laboratórios e campos de estágio precisa ser informada manualmente.
- O OCR de fotografias não é necessário para a matriz já transcrita e validada; outras imagens exigirão revisão humana.
- A recomendação é determinística e explicável, mas não substitui decisões institucionais.
- O sistema é local e destinado a uma única coordenadora nesta fase.

## Estrutura técnica

- `app/`: interface React e TypeScript.
- `backend/app/`: API FastAPI, modelos SQLAlchemy, extrator e serviços.
- `backend/tests/`: testes do extrator e da API.
- `data/`: banco SQLite criado localmente.
- `scripts/`: iniciadores para Windows, Linux e macOS.

O backend só escuta em `127.0.0.1`. Não altere para `0.0.0.0` sem autenticação, revisão de segurança e autorização institucional.
