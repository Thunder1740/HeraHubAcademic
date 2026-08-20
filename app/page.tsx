"use client";

/* eslint-disable @typescript-eslint/no-explicit-any, react-hooks/set-state-in-effect */

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Image from "next/image";

const API = "/api";
type Row = Record<string, any>;
type View =
  | "dashboard"
  | "import"
  | "students"
  | "matrices"
  | "demand"
  | "graduating"
  | "stages"
  | "simulation"
  | "schedule"
  | "reports"
  | "settings";

const NAV: { id: View; label: string; icon: string }[] = [
  { id: "dashboard", label: "Visão Geral", icon: "⌂" },
  { id: "import", label: "Importar Históricos", icon: "⇧" },
  { id: "students", label: "Estudantes", icon: "◉" },
  { id: "matrices", label: "Matrizes Curriculares", icon: "▦" },
  { id: "demand", label: "Disciplinas e Demanda", icon: "↗" },
  { id: "graduating", label: "Formandos", icon: "✓" },
  { id: "stages", label: "Estágios", icon: "◇" },
  { id: "simulation", label: "Simulador de Turmas", icon: "◎" },
  { id: "schedule", label: "Planejamento de Grade", icon: "▤" },
  { id: "reports", label: "Relatórios", icon: "⇩" },
  { id: "settings", label: "Configurações", icon: "⚙" },
];

function tone(value?: string) {
  if (["Aprovado", "Ativo", "Apto"].includes(value || "")) return "success";
  if (["Dispensado", "Interesse confirmado"].includes(value || ""))
    return "info";
  if (["Em Curso", "Potencialmente apto", "Estágio"].includes(value || ""))
    return "progress";
  if (["A Cursar", "Indeterminada"].includes(value || "")) return "warning";
  if (["Formando", "Não apto"].includes(value || "")) return "critical";
  return "neutral";
}

function Pill({
  children,
  kind = "neutral",
}: {
  children: React.ReactNode;
  kind?: string;
}) {
  return <span className={`pill ${kind}`}>{children}</span>;
}

function Empty({
  title,
  text,
  children,
}: {
  title: string;
  text: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="empty">
      <div>+</div>
      <h3>{title}</h3>
      <p>{text}</p>
      {children}
    </div>
  );
}

function Spinner() {
  return (
    <div className="spinner">
      <i />
      <i />
      <i />
    </div>
  );
}

export default function Home() {
  const [view, setView] = useState<View>("dashboard");
  const [dashboard, setDashboard] = useState<Row | null>(null);
  const [students, setStudents] = useState<Row[]>([]);
  const [matrices, setMatrices] = useState<Row[]>([]);
  const [demand, setDemand] = useState<Row[]>([]);
  const [classes, setClasses] = useState<Row[]>([]);
  const [conflicts, setConflicts] = useState<Row[]>([]);
  const [settings, setSettings] = useState<Row>({});
  const [student, setStudent] = useState<Row | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const api = useCallback(async (path: string, options?: RequestInit) => {
    const response = await fetch(`${API}${path}`, options);
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || "Não foi possível concluir a operação.");
    }
    return response.json();
  }, []);

  const refresh = useCallback(async () => {
    try {
      setError("");
      const values = await Promise.all([
        api("/dashboard"),
        api("/students"),
        api("/matrices"),
        api("/demand"),
        api("/classes"),
        api("/conflicts"),
        api("/settings"),
      ]);
      setDashboard(values[0]);
      setStudents(values[1]);
      setMatrices(values[2]);
      setDemand(values[3]);
      setClasses(values[4]);
      setConflicts(values[5]);
      setSettings(values[6]);
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "O serviço local não está respondendo.",
      );
    }
  }, [api]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function openStudent(id: number) {
    setLoading(true);
    try {
      setStudent(await api(`/students/${id}`));
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Erro ao abrir estudante.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function changed(note?: string) {
    await refresh();
    if (note) setMessage(note);
  }
  const title = NAV.find((item) => item.id === view)?.label;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Image
              src="/farmahub-logo.png"
              alt="Símbolo do curso de Farmácia da ULBRA"
              width={48}
              height={48}
              priority
            />
          </div>
          <p>
            <strong>FarmaHub</strong>
            <span>Acadêmico</span>
          </p>
        </div>
        <div className="workspace">
          <span>ESPAÇO DE TRABALHO</span>
          <strong>Farmácia · ULBRA Canoas</strong>
        </div>
        <nav>
          {NAV.map((item) => (
            <button
              key={item.id}
              className={view === item.id ? "active" : ""}
              onClick={() => setView(item.id)}
            >
              <i>{item.icon}</i>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="user">
          <div>FA</div>
          <p>
            <strong>{settings.display_user || "Farma"}</strong>
            <span>Coordenação do curso</span>
          </p>
          <em>Local</em>
        </div>
      </aside>
      <main className="main">
        <header>
          <div>
            <p>FARMAHUB ACADÊMICO</p>
            <h1>{title}</h1>
          </div>
          <div className="header-actions">
            <span className="local">
              <i /> Dados neste computador
            </span>
            <button className="icon-button" onClick={refresh}>
              ↻
            </button>
          </div>
        </header>
        {error && (
          <div className="alert error">
            <strong>Atenção</strong>
            <span>{error}</span>
            <button onClick={() => setError("")}>×</button>
          </div>
        )}
        {message && (
          <div className="alert ok">
            <strong>Concluído</strong>
            <span>{message}</span>
            <button onClick={() => setMessage("")}>×</button>
          </div>
        )}
        <section className="content">
          {view === "dashboard" && <Dashboard data={dashboard} go={setView} />}
          {view === "import" && (
            <ImportPanel
              matrices={matrices}
              settings={settings}
              api={api}
              done={() =>
                changed("Histórico confirmado e indicadores recalculados.")
              }
            />
          )}
          {view === "students" && (
            <StudentsPanel rows={students} open={openStudent} go={setView} />
          )}
          {view === "matrices" && (
            <MatricesPanel
              rows={matrices}
              api={api}
              done={() => changed("Matriz curricular atualizada.")}
            />
          )}
          {view === "demand" && <DemandPanel rows={demand} />}
          {view === "graduating" && (
            <GraduatingPanel
              rows={students}
              settings={settings}
              open={openStudent}
            />
          )}
          {view === "stages" && (
            <StagePanel
              rows={demand.filter((row) => row.category === "Estágio")}
            />
          )}
          {view === "simulation" && <SimulationPanel rows={demand} api={api} />}
          {view === "schedule" && (
            <SchedulePanel
              demand={demand}
              rows={classes}
              conflicts={conflicts}
              settings={settings}
              api={api}
              done={() => changed("Grade atualizada.")}
            />
          )}
          {view === "reports" && (
            <ReportsPanel students={students.length} demand={demand.length} />
          )}
          {view === "settings" && (
            <SettingsPanel
              value={settings}
              setValue={setSettings}
              api={api}
              done={() => changed("Configurações atualizadas.")}
            />
          )}
        </section>
      </main>
      {loading && (
        <div className="overlay">
          <Spinner />
        </div>
      )}
      {student && (
        <StudentDrawer
          value={student}
          api={api}
          close={() => setStudent(null)}
          done={async () => {
            await changed();
            setStudent(await api(`/students/${student.id}`));
          }}
          removed={async (name: string) => {
            setStudent(null);
            await changed(`${name} foi removido de toda a base acadêmica.`);
          }}
        />
      )}
    </div>
  );
}

function Dashboard({
  data,
  go,
}: {
  data: Row | null;
  go: (view: View) => void;
}) {
  if (!data) return <Spinner />;
  if (!data.students)
    return (
      <div className="dashboard-empty">
        <div>
          <Pill kind="info">BASE PRONTA</Pill>
          <h2>Transforme históricos em decisões acadêmicas.</h2>
          <p>
            Importe o primeiro PDF oficial. O sistema extrai e organiza os
            dados, mas só salva após sua revisão.
          </p>
          <button className="primary" onClick={() => go("import")}>
            Importar primeiro histórico →
          </button>
        </div>
        <div className="flow">
          <span>
            <b>01</b>PDF oficial
          </span>
          <i>→</i>
          <span>
            <b>02</b>Revisão humana
          </span>
          <i>→</i>
          <span>
            <b>03</b>Demanda confiável
          </span>
        </div>
      </div>
    );
  const cards = [
    ["Estudantes ativos", data.active, `${data.students} cadastrados`, "◉"],
    ["Formandos prioritários", data.graduating, "Prioridade máxima", "✓"],
    [
      "Necessidades pendentes",
      data.pending,
      `${data.stage_pending} estágios`,
      "↗",
    ],
    [
      "Integralização média",
      `${data.integralization_average}%`,
      "Carga horária",
      "◒",
    ],
  ];
  const top = Math.max(...data.demand.map((row: Row) => row.total), 1);
  return (
    <div className="stack">
      <div className="hero">
        <div>
          <Pill kind="success">PLANEJAMENTO ATIVO</Pill>
          <h2>Decisões curriculares com dados revisados.</h2>
          <p>
            Priorize formandos, enxergue a demanda real e compare ofertas de
            turmas.
          </p>
        </div>
        <button className="primary" onClick={() => go("import")}>
          ⇧ Importar históricos
        </button>
      </div>
      <div className="metric-grid">
        {cards.map((card) => (
          <article className="metric" key={String(card[0])}>
            <div>{card[3]}</div>
            <p>{card[0]}</p>
            <strong>{card[1]}</strong>
            <span>{card[2]}</span>
          </article>
        ))}
      </div>
      <div className="dashboard-grid">
        <article className="panel">
          <div className="panel-title">
            <div>
              <span>PRIORIDADE DE OFERTA</span>
              <h3>Disciplinas com maior demanda</h3>
            </div>
            <button className="link" onClick={() => go("demand")}>
              Análise completa →
            </button>
          </div>
          {data.demand.length ? (
            <div className="rank-list">
              {data.demand.slice(0, 7).map((row: Row, index: number) => (
                <div key={row.subject_id}>
                  <b>{String(index + 1).padStart(2, "0")}</b>
                  <p>
                    <strong>{row.name}</strong>
                    <span>
                      {row.code} · {row.semester}º semestre
                    </span>
                  </p>
                  <div className="bar">
                    <i style={{ width: `${(row.total / top) * 100}%` }} />
                  </div>
                  <em>{row.total}</em>
                  {row.graduating > 0 && (
                    <Pill kind="critical">
                      {row.graduating} formando{row.graduating > 1 ? "s" : ""}
                    </Pill>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <Empty
              title="Sem demanda"
              text="Confirme o primeiro histórico para calcular a demanda."
            />
          )}
        </article>
        <article className="panel">
          <div className="panel-title">
            <div>
              <span>DISTRIBUIÇÃO</span>
              <h3>Estudantes por semestre</h3>
            </div>
          </div>
          <div className="semester-chart">
            {Object.entries(data.semester_distribution).map(
              ([key, value]: any) => (
                <div key={key}>
                  <div style={{ height: `${Math.max(18, value * 18)}px` }}>
                    <span>{value}</span>
                  </div>
                  <b>{key === "Não informado" ? "N/I" : `${key}º`}</b>
                </div>
              ),
            )}
          </div>
          <div className="trust-note">
            <i>i</i>
            <p>
              <strong>Leitura responsável</strong>
              <span>
                Estimativas são identificadas e sempre podem ser corrigidas
                manualmente.
              </span>
            </p>
          </div>
        </article>
      </div>
    </div>
  );
}

function ImportPanel({ matrices, settings, api, done }: any) {
  const [files, setFiles] = useState<File[]>([]);
  const [matrix, setMatrix] = useState("");
  const [period, setPeriod] = useState(settings.reference_period || "2026/2");
  const [results, setResults] = useState<Row[]>([]);
  const [review, setReview] = useState<Row | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!matrix && matrices[0]) setMatrix(String(matrices[0].id));
  }, [matrix, matrices]);
  async function process() {
    if (!files.length) return;
    setBusy(true);
    setError("");
    const form = new FormData();
    files.forEach((file) => form.append("files", file));
    try {
      const response = await fetch(
        `${API}/imports/review?matrix_id=${matrix}&reference_period=${encodeURIComponent(period)}`,
        { method: "POST", body: form },
      );
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail);
      setResults(body.results);
      setReview(body.results.find((r: Row) => r.ok)?.data || null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao processar");
    } finally {
      setBusy(false);
    }
  }
  async function confirm() {
    if (!review) return;
    setBusy(true);
    try {
      await api("/imports/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(review),
      });
      setReview(null);
      setResults([]);
      setFiles([]);
      done();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao confirmar");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="stack">
      <div className="section-intro">
        <div>
          <h2>Importação segura e revisável</h2>
          <p>
            Os PDFs são processados localmente e só entram no banco depois da
            confirmação.
          </p>
        </div>
        <Pill kind="info">PDF DIGITAL · LOTE DE ATÉ 300</Pill>
      </div>
      <div className="import-layout">
        <article className="panel">
          <label className="drop-zone">
            <input
              type="file"
              accept="application/pdf"
              multiple
              onChange={(e) => setFiles(Array.from(e.target.files || []))}
            />
            <div>⇧</div>
            <h3>Arraste os históricos para cá</h3>
            <p>ou clique para selecionar PDFs oficiais da ULBRA</p>
            <span>Limite de 12 MB por arquivo</span>
          </label>
          {files.length > 0 && (
            <div className="file-list">
              {files.slice(0, 7).map((file) => (
                <div key={file.name}>
                  <b>PDF</b>
                  <p>
                    <strong>{file.name}</strong>
                    <span>{Math.round(file.size / 1024)} KB</span>
                  </p>
                  <em>Pronto</em>
                </div>
              ))}
              {files.length > 7 && <small>+{files.length - 7} arquivos</small>}
            </div>
          )}
        </article>
        <aside className="panel import-config">
          <div className="panel-title">
            <div>
              <span>CONFIGURAÇÃO</span>
              <h3>Como interpretar o lote</h3>
            </div>
          </div>
          <label>
            Matriz curricular
            <select value={matrix} onChange={(e) => setMatrix(e.target.value)}>
              {matrices.map((row: Row) => (
                <option value={row.id} key={row.id}>
                  {row.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Semestre de referência
            <input value={period} onChange={(e) => setPeriod(e.target.value)} />
          </label>
          <div className="privacy">
            <i>✓</i>
            <p>
              <strong>Minimização de dados ativa</strong>
              <span>CPF, RG e nascimento não serão armazenados.</span>
            </p>
          </div>
          <button
            className="primary wide"
            disabled={!files.length || busy}
            onClick={process}
          >
            {busy
              ? "Processando…"
              : `Processar ${files.length || ""} arquivo${files.length === 1 ? "" : "s"}`}
          </button>
          {error && <p className="form-error">{error}</p>}
        </aside>
      </div>
      {results.length > 0 && (
        <article className="panel">
          <div className="panel-title">
            <div>
              <span>RESULTADO DO LOTE</span>
              <h3>
                {results.filter((r) => r.ok).length} processados ·{" "}
                {results.filter((r) => !r.ok).length} com erro
              </h3>
            </div>
          </div>
          <div className="result-list">
            {results.map((result, index) => (
              <button
                key={index}
                onClick={() => result.ok && setReview(result.data)}
                className={
                  review?.file_hash === result.data?.file_hash ? "selected" : ""
                }
              >
                <Pill kind={result.ok ? "success" : "critical"}>
                  {result.ok ? "Revisar" : "Erro"}
                </Pill>
                <span>{result.data?.file_name || result.file_name}</span>
                <em>
                  {result.ok
                    ? `${result.data.summary.total} disciplinas`
                    : result.error}
                </em>
              </button>
            ))}
          </div>
        </article>
      )}
      {review && (
        <Review
          data={review}
          setData={setReview}
          busy={busy}
          confirm={confirm}
        />
      )}
    </div>
  );
}

function Review({ data, setData, busy, confirm }: any) {
  return (
    <article className="panel review">
      <div className="review-head">
        <div>
          <Pill kind={data.warnings.length ? "warning" : "success"}>
            {data.warnings.length
              ? "REVISÃO NECESSÁRIA"
              : "EXTRAÇÃO CONSISTENTE"}
          </Pill>
          <h3>{data.file_name}</h3>
          <p>
            {data.matrix_name} · {data.summary.duplicates_consolidated}{" "}
            duplicidades consolidadas
          </p>
        </div>
        <div>
          <button className="secondary" onClick={() => setData(null)}>
            Cancelar
          </button>
          <button className="primary" disabled={busy} onClick={confirm}>
            Confirmar no banco
          </button>
        </div>
      </div>
      <div className="profile-form">
        <label>
          Nome
          <input
            value={data.student.name || ""}
            onChange={(e) =>
              setData({
                ...data,
                student: { ...data.student, name: e.target.value },
              })
            }
          />
        </label>
        <label>
          Matrícula
          <input
            value={data.student.registration || ""}
            onChange={(e) =>
              setData({
                ...data,
                student: { ...data.student, registration: e.target.value },
              })
            }
          />
        </label>
        <label>
          Situação
          <select
            value={data.student.academic_status || "Ativo"}
            onChange={(e) =>
              setData({
                ...data,
                student: { ...data.student, academic_status: e.target.value },
              })
            }
          >
            <option>Ativo</option>
            <option>Formando</option>
            <option>Trancado</option>
            <option>Concluído</option>
          </select>
        </label>
        <label>
          Previsão
          <input
            placeholder="2027/2"
            value={data.student.expected_graduation || ""}
            onChange={(e) =>
              setData({
                ...data,
                student: {
                  ...data.student,
                  expected_graduation: e.target.value,
                  graduation_source: "Manual",
                },
              })
            }
          />
        </label>
      </div>
      <div className="review-metrics">
        <span>
          <b>{data.summary.total}</b>componentes
        </span>
        <span>
          <b>{data.summary.hours_filled_from_matrix}</b>CH pela matriz
        </span>
        <span>
          <b>{data.summary.unmatched}</b>sem correspondência
        </span>
        <span>
          <b>{data.student.completed_hours}</b>horas concluídas
        </span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Sem.</th>
              <th>Disciplina</th>
              <th>Status</th>
              <th>Nota</th>
              <th>Período</th>
              <th>CH</th>
              <th>Origem</th>
            </tr>
          </thead>
          <tbody>
            {data.records.map((row: Row) => (
              <tr key={row.normalized_name}>
                <td>{row.semester}º</td>
                <td>
                  <strong>{row.subject_name}</strong>
                  {row.elective_choice && (
                    <small>Integralizada por {row.elective_choice}</small>
                  )}
                </td>
                <td>
                  <Pill kind={tone(row.status)}>{row.status}</Pill>
                </td>
                <td>{row.grade ?? "—"}</td>
                <td>{row.academic_period || "—"}</td>
                <td>{row.hours || "—"}</td>
                <td>
                  <span className="source">{row.hours_source}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}

function StudentsPanel({ rows, open, go }: any) {
  const [search, setSearch] = useState("");
  const visible = useMemo(
    () =>
      rows.filter((r: Row) =>
        `${r.name} ${r.registration}`
          .toLowerCase()
          .includes(search.toLowerCase()),
      ),
    [rows, search],
  );
  return (
    <div className="stack">
      <div className="section-intro">
        <div>
          <h2>Base acadêmica consolidada</h2>
          <p>Consulte progresso, pendências e intenção de matrícula.</p>
        </div>
        <button className="primary" onClick={() => go("import")}>
          ⇧ Importar históricos
        </button>
      </div>
      <div className="toolbar">
        <label className="search">
          ⌕
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por nome ou matrícula"
          />
        </label>
        <span>{visible.length} estudantes</span>
      </div>
      {visible.length ? (
        <div className="student-grid">
          {visible.map((row: Row) => (
            <button
              className="student-card"
              key={row.id}
              onClick={() => open(row.id)}
            >
              <div className="avatar">
                {row.name
                  .split(" ")
                  .slice(0, 2)
                  .map((v: string) => v[0])
                  .join("")}
              </div>
              <div>
                <div>
                  <h3>{row.name}</h3>
                  <Pill kind={tone(row.academic_status)}>
                    {row.academic_status}
                  </Pill>
                </div>
                <p>
                  {row.registration} ·{" "}
                  {row.matrix_name || "Matriz não vinculada"}
                </p>
                <div className="progress">
                  <i style={{ width: `${row.progress}%` }} />
                </div>
                <span>
                  {row.progress}% integralizado ·{" "}
                  {row.counts?.["A Cursar"] || 0} pendências
                </span>
              </div>
              <b>→</b>
            </button>
          ))}
        </div>
      ) : (
        <Empty
          title="Nenhum estudante cadastrado"
          text="Importe os históricos oficiais para criar a base."
        >
          <button className="primary" onClick={() => go("import")}>
            Importar histórico
          </button>
        </Empty>
      )}
    </div>
  );
}

function StudentDrawer({ value, api, close, done, removed }: any) {
  const [student, setStudent] = useState(value);
  const [tab, setTab] = useState("history");
  const [busy, setBusy] = useState(false);
  async function save() {
    setBusy(true);
    await api(`/students/${student.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: student.name,
        current_semester: student.current_semester,
        academic_status: student.academic_status,
        expected_graduation: student.expected_graduation,
        preferred_shift: student.preferred_shift,
        complementary_completed: student.complementary_completed,
      }),
    });
    await done();
    setBusy(false);
  }
  async function intent(subject: number, intends: boolean) {
    await api(`/students/${student.id}/intents/${subject}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ intends }),
    });
    await done();
  }
  async function removeProfile() {
    if (
      !confirm(
        `Excluir definitivamente o perfil de ${student.name}?\n\nTodo o histórico, tentativas, intenções de matrícula e registros de importação deste estudante serão apagados. Esta ação não pode ser desfeita.`,
      )
    )
      return;
    setBusy(true);
    try {
      await api(`/students/${student.id}`, { method: "DELETE" });
      await removed(student.name);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div
      className="drawer-backdrop"
      onMouseDown={(e) => e.target === e.currentTarget && close()}
    >
      <aside className="drawer">
        <button className="drawer-close" onClick={close}>
          ×
        </button>
        <div className="drawer-hero">
          <div className="avatar large">
            {student.name
              .split(" ")
              .slice(0, 2)
              .map((v: string) => v[0])
              .join("")}
          </div>
          <div>
            <Pill kind={tone(student.academic_status)}>
              {student.academic_status}
            </Pill>
            <h2>{student.name}</h2>
            <p>
              {student.registration} · {student.matrix_name}
            </p>
          </div>
        </div>
        <div className="drawer-metrics">
          <span>
            <b>{student.progress}%</b>integralizado
          </span>
          <span>
            <b>{student.completed_hours}h</b>concluídas
          </span>
          <span>
            <b>{student.counts?.["A Cursar"] || 0}</b>pendências
          </span>
          <span>
            <b>{student.stage_pending}</b>estágios
          </span>
        </div>
        <div className="tabs">
          <button
            className={tab === "history" ? "active" : ""}
            onClick={() => setTab("history")}
          >
            Histórico consolidado
          </button>
          <button
            className={tab === "profile" ? "active" : ""}
            onClick={() => setTab("profile")}
          >
            Perfil e previsão
          </button>
          <button
            className={tab === "attempts" ? "active" : ""}
            onClick={() => setTab("attempts")}
          >
            Tentativas anteriores
          </button>
        </div>
        {tab === "history" && (
          <>
            <div className="drawer-actions">
              <a
                className="secondary"
                href={`${API}/reports/students/${student.id}.xlsx`}
              >
                Excel
              </a>
              <a
                className="secondary"
                href={`${API}/reports/students/${student.id}.pdf`}
              >
                PDF
              </a>
            </div>
            <div className="table-wrap drawer-table">
              <table>
                <thead>
                  <tr>
                    <th>Sem.</th>
                    <th>Disciplina</th>
                    <th>Status</th>
                    <th>Nota</th>
                    <th>CH</th>
                    <th>Interesse</th>
                  </tr>
                </thead>
                <tbody>
                  {student.records.map((row: Row) => (
                    <tr key={row.id}>
                      <td>{row.semester}º</td>
                      <td>
                        <strong>{row.display_name}</strong>
                        <small>{row.code || "Sem código"}</small>
                      </td>
                      <td>
                        <Pill kind={tone(row.status)}>{row.status}</Pill>
                      </td>
                      <td>{row.grade ?? "—"}</td>
                      <td>{row.hours ?? "—"}</td>
                      <td>
                        {row.status === "A Cursar" && row.subject_id ? (
                          <input
                            type="checkbox"
                            checked={row.intent}
                            onChange={(e) =>
                              intent(row.subject_id, e.target.checked)
                            }
                          />
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
        {tab === "profile" && (
          <div className="profile-edit">
            <div className="profile-delete">
              <div>
                <strong>Excluir perfil do estudante</strong>
                <span>
                  Remove permanentemente este perfil e todos os dados
                  acadêmicos vinculados.
                </span>
              </div>
              <button disabled={busy} onClick={removeProfile}>
                Excluir perfil definitivamente
              </button>
            </div>
            <label>
              Nome
              <input
                value={student.name}
                onChange={(e) =>
                  setStudent({ ...student, name: e.target.value })
                }
              />
            </label>
            <label>
              Situação
              <select
                value={student.academic_status}
                onChange={(e) =>
                  setStudent({ ...student, academic_status: e.target.value })
                }
              >
                <option>Ativo</option>
                <option>Formando</option>
                <option>Trancado</option>
                <option>Desistente</option>
                <option>Concluído</option>
                <option>Outro</option>
              </select>
            </label>
            <label>
              Semestre atual
              <input
                type="number"
                min="1"
                max="10"
                value={student.current_semester || ""}
                onChange={(e) =>
                  setStudent({
                    ...student,
                    current_semester: Number(e.target.value) || null,
                  })
                }
              />
              <small>Ao salvar, a origem passa a ser manual.</small>
            </label>
            <label>
              Previsão de conclusão
              <input
                value={student.expected_graduation || ""}
                placeholder="2027/2"
                onChange={(e) =>
                  setStudent({
                    ...student,
                    expected_graduation: e.target.value,
                  })
                }
              />
            </label>
            <label>
              Turno preferencial
              <select
                value={student.preferred_shift}
                onChange={(e) =>
                  setStudent({ ...student, preferred_shift: e.target.value })
                }
              >
                <option>Tarde</option>
                <option>Noite</option>
                <option>Indiferente</option>
              </select>
            </label>
            <label>
              Horas complementares
              <input
                type="number"
                min="0"
                value={student.complementary_completed}
                onChange={(e) =>
                  setStudent({
                    ...student,
                    complementary_completed: Number(e.target.value),
                  })
                }
              />
            </label>
            <button className="primary" disabled={busy} onClick={save}>
              {busy ? "Salvando…" : "Salvar alterações"}
            </button>
          </div>
        )}
        {tab === "attempts" && (
          <div className="attempts">
            {student.attempts.length ? (
              student.attempts.map((row: Row, index: number) => (
                <div key={index}>
                  <Pill kind="critical">{row.status}</Pill>
                  <p>
                    <strong>{row.subject_name}</strong>
                    <span>
                      {row.academic_period || "Período não identificado"} · Nota{" "}
                      {row.grade ?? "—"}
                    </span>
                  </p>
                </div>
              ))
            ) : (
              <Empty
                title="Sem reprovações registradas"
                text="Nenhuma tentativa anterior reprovada foi encontrada."
              />
            )}
          </div>
        )}
      </aside>
    </div>
  );
}

function MatricesPanel({ rows, api, done }: any) {
  const [selected, setSelected] = useState<number | null>(rows[0]?.id || null);
  const [newMatrix, setNewMatrix] = useState(false);
  const [ruleSubject, setRuleSubject] = useState("");
  const [rules, setRules] = useState<Row[]>([]);
  const matrix = rows.find((r: Row) => r.id === selected) || rows[0];
  useEffect(() => {
    if (!selected && rows[0]) setSelected(rows[0].id);
  }, [rows, selected]);
  async function createMatrix(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    await api("/matrices", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Object.fromEntries(new FormData(e.currentTarget))),
    });
    setNewMatrix(false);
    done();
  }
  async function createSubject(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    await api(`/matrices/${matrix.id}/subjects`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Object.fromEntries(new FormData(e.currentTarget))),
    });
    e.currentTarget.reset();
    done();
  }
  async function chooseRuleSubject(id: string) {
    setRuleSubject(id);
    setRules(id ? await api(`/subjects/${id}/prerequisites`) : []);
  }
  async function createRule(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const values = Object.fromEntries(new FormData(e.currentTarget));
    await api(`/subjects/${values.subject_id}/prerequisites`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ required_subject_id: values.required_subject_id }),
    });
    await chooseRuleSubject(String(values.subject_id));
    done();
  }
  async function removeRule(required: number) {
    await api(`/subjects/${ruleSubject}/prerequisites/${required}`, {
      method: "DELETE",
    });
    await chooseRuleSubject(ruleSubject);
    done();
  }
  async function removeMatrix() {
    if (!matrix) return;
    if (
      !confirm(
        `Remover definitivamente a matriz "${matrix.name}"?\n\nOs componentes e pré-requisitos desta matriz serão apagados. Os estudantes e seus históricos serão preservados, mas ficarão sem uma matriz vinculada até uma nova seleção. Esta ação não pode ser desfeita.`,
      )
    )
      return;
    await api(`/matrices/${matrix.id}`, { method: "DELETE" });
    setSelected(null);
    setRuleSubject("");
    setRules([]);
    await done();
  }
  return (
    <div className="stack">
      <div className="section-intro">
        <div>
          <h2>Fonte oficial das regras curriculares</h2>
          <p>
            Códigos e cargas foram conferidos. Pré-requisitos ficam vazios até
            confirmação institucional.
          </p>
        </div>
        <div className="matrix-actions">
          <button
            className="danger"
            onClick={removeMatrix}
            disabled={!matrix}
          >
            − Remover matriz
          </button>
          <button className="secondary" onClick={() => setNewMatrix(!newMatrix)}>
            + Nova matriz
          </button>
        </div>
      </div>
      {newMatrix && (
        <form className="panel inline-form" onSubmit={createMatrix}>
          <label>
            Nome
            <input name="name" required />
          </label>
          <label>
            Vigência
            <input name="valid_from" />
          </label>
          <label>
            Carga total
            <input name="total_hours" type="number" />
          </label>
          <button className="primary">Cadastrar</button>
        </form>
      )}
      <div className="matrix-tabs">
        {rows.map((row: Row) => (
          <button
            className={matrix?.id === row.id ? "active" : ""}
            key={row.id}
            onClick={() => setSelected(row.id)}
          >
            <strong>{row.name}</strong>
            <span>
              {row.subject_count} componentes · {row.total_hours}h
            </span>
          </button>
        ))}
      </div>
      {matrix ? (
        <>
          <div className="panel matrix-summary">
            <div>
              <span>MATRIZ ATIVA</span>
              <h3>{matrix.name}</h3>
              <p>
                {matrix.course} · {matrix.campus} · Vigência{" "}
                {matrix.valid_from || "não informada"}
              </p>
            </div>
            <div>
              <b>{matrix.subject_count - 1}</b>
              <span>disciplinas principais</span>
            </div>
            <div>
              <b>{matrix.total_hours}h</b>
              <span>carga total</span>
            </div>
          </div>
          <article className="panel">
            <div className="panel-title">
              <div>
                <span>COMPONENTES</span>
                <h3>Estrutura curricular cadastrada</h3>
              </div>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Seq.</th>
                    <th>Código</th>
                    <th>Componente</th>
                    <th>Sem.</th>
                    <th>CH</th>
                    <th>Créd.</th>
                    <th>Categoria</th>
                  </tr>
                </thead>
                <tbody>
                  {matrix.subjects.map((s: Row) => (
                    <tr key={s.id}>
                      <td>{s.sequence}</td>
                      <td>
                        <span className="code">{s.code}</span>
                      </td>
                      <td>
                        <strong>{s.name}</strong>
                      </td>
                      <td>{s.semester || "—"}</td>
                      <td>{s.hours}</td>
                      <td>{s.credits}</td>
                      <td>
                        <Pill kind={tone(s.category)}>{s.category}</Pill>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </article>
          <form className="panel subject-form" onSubmit={createSubject}>
            <div className="panel-title">
              <div>
                <span>CADASTRO MANUAL</span>
                <h3>Adicionar componente</h3>
              </div>
            </div>
            <label>
              Código
              <input name="code" required />
            </label>
            <label className="grow">
              Nome
              <input name="name" required />
            </label>
            <label>
              Semestre
              <input name="semester" type="number" min="0" max="15" required />
            </label>
            <label>
              CH
              <input name="hours" type="number" min="0" required />
            </label>
            <label>
              Créditos
              <input name="credits" type="number" min="0" />
            </label>
            <label>
              Categoria
              <select name="category">
                <option>Regular</option>
                <option>Estágio</option>
                <option>Optativa</option>
                <option>Atividade complementar</option>
              </select>
            </label>
            <button className="primary">Adicionar</button>
          </form>
          <form className="panel rule-form" onSubmit={createRule}>
            <div className="panel-title">
              <div>
                <span>ELEGIBILIDADE</span>
                <h3>Cadastrar pré-requisito confirmado</h3>
              </div>
              <Pill kind="warning">Não inventar regras</Pill>
            </div>
            <div className="rule-fields">
              <label>
                Disciplina que será cursada
                <select
                  name="subject_id"
                  required
                  value={ruleSubject}
                  onChange={(e) => chooseRuleSubject(e.target.value)}
                >
                  <option value="">Selecione</option>
                  {matrix.subjects
                    .filter((s: Row) => s.semester > 0)
                    .map((s: Row) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                </select>
              </label>
              <label>
                Exige a conclusão de
                <select name="required_subject_id" required>
                  <option value="">Selecione</option>
                  {matrix.subjects
                    .filter(
                      (s: Row) =>
                        s.semester > 0 && String(s.id) !== ruleSubject,
                    )
                    .map((s: Row) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                </select>
              </label>
              <button className="primary">Adicionar regra</button>
            </div>
            {ruleSubject && (
              <div className="rule-list">
                {rules.length ? (
                  rules.map((r: Row) => (
                    <span key={r.id}>
                      {r.name}
                      <button type="button" onClick={() => removeRule(r.id)}>
                        Remover
                      </button>
                    </span>
                  ))
                ) : (
                  <p>Nenhum pré-requisito cadastrado para esta disciplina.</p>
                )}
              </div>
            )}
          </form>
        </>
      ) : (
        <Empty
          title="Nenhuma matriz"
          text="Cadastre a primeira matriz curricular."
        />
      )}
    </div>
  );
}

function DemandPanel({ rows }: { rows: Row[] }) {
  const [expanded, setExpanded] = useState<number | null>(null);
  return (
    <div className="stack">
      <div className="section-intro">
        <div>
          <h2>Necessidade, elegibilidade e interesse</h2>
          <p>
            “Em curso” é projetado positivamente; somente “A cursar” entra como
            demanda futura.
          </p>
        </div>
        <div className="legend">
          <Pill kind="critical">Formandos primeiro</Pill>
          <Pill kind="warning">Sem regra = indeterminado</Pill>
        </div>
      </div>
      {rows.length ? (
        <article className="panel">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Disciplina</th>
                  <th>Necessitam</th>
                  <th>Aptos</th>
                  <th>Potenciais</th>
                  <th>Indeterm.</th>
                  <th>Interesse</th>
                  <th>Formandos</th>
                  <th>Turmas</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, index) => (
                  <DemandRows
                    key={row.subject_id}
                    row={row}
                    index={index}
                    open={expanded === row.subject_id}
                    toggle={() =>
                      setExpanded(
                        expanded === row.subject_id ? null : row.subject_id,
                      )
                    }
                  />
                ))}
              </tbody>
            </table>
          </div>
        </article>
      ) : (
        <Empty
          title="Sem demanda calculada"
          text="Confirme ao menos um histórico para visualizar as necessidades."
        />
      )}
    </div>
  );
}

function DemandRows({ row, index, open, toggle }: any) {
  return (
    <>
      <tr className="clickable" onClick={toggle}>
        <td>
          <b className="rank">{String(index + 1).padStart(2, "0")}</b>
        </td>
        <td>
          <strong>{row.name}</strong>
          <small>
            {row.code} · {row.semester}º · {row.category}
          </small>
        </td>
        <td>
          <b>{row.total}</b>
        </td>
        <td>{row.eligible}</td>
        <td>{row.potential}</td>
        <td>{row.indeterminate}</td>
        <td>{row.interested}</td>
        <td>
          {row.graduating ? <Pill kind="critical">{row.graduating}</Pill> : "0"}
        </td>
        <td>{row.estimated_classes}</td>
      </tr>
      {open && (
        <tr className="expanded">
          <td colSpan={9}>
            <StudentDemand rows={row.students} />
          </td>
        </tr>
      )}
    </>
  );
}
function StudentDemand({ rows }: { rows: Row[] }) {
  return (
    <div className="demand-students">
      <h4>Estudantes que precisam cursar</h4>
      {rows.map((row) => (
        <div key={row.id}>
          <span className="avatar small">{row.name[0]}</span>
          <p>
            <strong>{row.name}</strong>
            <span>
              {row.registration} · {row.preferred_shift}
            </span>
          </p>
          <Pill kind={tone(row.eligibility)}>{row.eligibility}</Pill>
          {row.interested && <Pill kind="info">Interesse</Pill>}
          {row.academic_status === "Formando" && (
            <Pill kind="critical">Formando</Pill>
          )}
        </div>
      ))}
    </div>
  );
}

function GraduatingPanel({ rows, settings, open }: any) {
  const selected = rows.filter(
    (r: Row) =>
      r.academic_status === "Formando" ||
      (settings.graduation_year &&
        r.expected_graduation?.startsWith(settings.graduation_year)),
  );
  return (
    <div className="stack">
      <div className="section-intro">
        <div>
          <h2>Prioridade máxima: conclusão do curso</h2>
          <p>
            Formandos ou estudantes com previsão no ano{" "}
            {settings.graduation_year || "não definido"}.
          </p>
        </div>
      </div>
      {selected.length ? (
        <div className="student-grid">
          {selected.map((row: Row) => (
            <button
              className="student-card critical-card"
              key={row.id}
              onClick={() => open(row.id)}
            >
              <div className="avatar">{row.name[0]}</div>
              <div>
                <div>
                  <h3>{row.name}</h3>
                  <Pill kind="critical">
                    {row.expected_graduation || "Em análise"}
                  </Pill>
                </div>
                <p>{row.registration}</p>
                <span>
                  {row.counts?.["A Cursar"] || 0} disciplinas ·{" "}
                  {row.stage_pending} estágios ·{" "}
                  {Math.max(
                    0,
                    row.complementary_required - row.complementary_completed,
                  )}
                  h complementares
                </span>
              </div>
              <b>→</b>
            </button>
          ))}
        </div>
      ) : (
        <Empty
          title="Nenhum formando identificado"
          text="Marque a situação ou informe a previsão no perfil do estudante."
        />
      )}
    </div>
  );
}

function StagePanel({ rows }: { rows: Row[] }) {
  const [open, setOpen] = useState<number | null>(null);
  return (
    <div className="stack">
      <div className="section-intro">
        <div>
          <h2>Estágios obrigatórios em foco</h2>
          <p>
            Capacidade própria, prioridade de formandos e impacto direto na
            integralização.
          </p>
        </div>
        <Pill kind="progress">CAPACIDADE CONFIGURÁVEL</Pill>
      </div>
      {rows.length ? (
        <div className="stage-grid">
          {rows.map((row) => (
            <article className="panel stage-card" key={row.subject_id}>
              <div>
                <Pill kind="progress">{row.semester}º SEMESTRE</Pill>
                <span>{row.hours}h</span>
              </div>
              <h3>{row.name.replace("ESTÁGIO: ", "")}</h3>
              <p>{row.total} estudantes precisam deste campo.</p>
              <div className="stage-numbers">
                <span>
                  <b>{row.graduating}</b>formandos
                </span>
                <span>
                  <b>{row.interested}</b>interessados
                </span>
                <span>
                  <b>{row.estimated_classes}</b>turmas
                </span>
              </div>
              <button
                className="secondary wide"
                onClick={() =>
                  setOpen(open === row.subject_id ? null : row.subject_id)
                }
              >
                {open === row.subject_id ? "Ocultar" : "Ver estudantes"}
              </button>
              {open === row.subject_id && <StudentDemand rows={row.students} />}
            </article>
          ))}
        </div>
      ) : (
        <Empty
          title="Sem estágios pendentes"
          text="Os estágios a cursar aparecerão aqui após as importações."
        />
      )}
    </div>
  );
}

function SimulationPanel({ rows, api }: any) {
  const [selected, setSelected] = useState<number[]>([]);
  const [result, setResult] = useState<Row | null>(null);
  const [busy, setBusy] = useState(false);
  const toggle = (id: number) =>
    setSelected((value) =>
      value.includes(id) ? value.filter((v) => v !== id) : [...value, id],
    );
  async function run(auto = false) {
    setBusy(true);
    const response = auto
      ? await api("/recommendations?limit=8")
      : await api("/simulations", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ subject_ids: selected }),
        });
    if (auto)
      setSelected(response.recommendation.map((r: Row) => r.subject_id));
    setResult(response);
    setBusy(false);
  }
  return (
    <div className="stack">
      <div className="section-intro">
        <div>
          <h2>Se abrirmos estas turmas, quem será atendido?</h2>
          <p>
            Compare estudantes únicos, necessidades curriculares e formandos
            beneficiados.
          </p>
        </div>
        <button
          className="secondary"
          disabled={!rows.length || busy}
          onClick={() => run(true)}
        >
          ◎ Gerar recomendação
        </button>
      </div>
      <div className="simulation-layout">
        <article className="panel">
          <div className="panel-title">
            <div>
              <span>SELEÇÃO</span>
              <h3>Disciplinas candidatas</h3>
            </div>
            <Pill kind="info">{selected.length} selecionadas</Pill>
          </div>
          <div className="check-list">
            {rows.map((row: Row) => (
              <label
                className={selected.includes(row.subject_id) ? "checked" : ""}
                key={row.subject_id}
              >
                <input
                  type="checkbox"
                  checked={selected.includes(row.subject_id)}
                  onChange={() => toggle(row.subject_id)}
                />
                <p>
                  <strong>{row.name}</strong>
                  <span>
                    {row.total} estudantes · {row.graduating} formandos
                  </span>
                </p>
                <Pill kind={row.graduating ? "critical" : "neutral"}>
                  {row.category}
                </Pill>
              </label>
            ))}
          </div>
          <button
            className="primary wide"
            disabled={!selected.length || busy}
            onClick={() => run()}
          >
            {busy ? "Calculando…" : "Simular cenário"}
          </button>
        </article>
        <aside>
          {result ? (
            <div className="panel simulation-result">
              <Pill kind="success">CENÁRIO CALCULADO</Pill>
              <h3>Impacto desta oferta</h3>
              <div className="impact-main">
                <strong>{result.unique_students}</strong>
                <span>estudantes únicos atendidos</span>
              </div>
              <div className="impact-grid">
                <span>
                  <b>{result.curricular_needs}</b>necessidades
                </span>
                <span>
                  <b>{result.graduating_students}</b>formandos
                </span>
                <span>
                  <b>{result.classes}</b>turmas
                </span>
                <span>
                  <b>{result.occupancy}%</b>ocupação
                </span>
                <span>
                  <b>{result.eligible}</b>aptos
                </span>
                <span>
                  <b>{result.potential}</b>potenciais
                </span>
              </div>
              <div className="method">
                <i>i</i>
                <p>{result.method}</p>
              </div>
            </div>
          ) : (
            <div className="panel simulation-placeholder">
              <div>◎</div>
              <h3>Monte um cenário</h3>
              <p>Selecione disciplinas ou peça uma recomendação automática.</p>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

function SchedulePanel({ demand, rows, conflicts, settings, api, done }: any) {
  async function create(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    await api("/classes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Object.fromEntries(new FormData(e.currentTarget))),
    });
    e.currentTarget.reset();
    done();
  }
  async function remove(id: number) {
    await api(`/classes/${id}`, { method: "DELETE" });
    done();
  }
  return (
    <div className="stack">
      <div className="section-intro">
        <div>
          <h2>Grade preliminar do semestre</h2>
          <p>
            Conflitos só são apontados quando dias e horários estão informados.
          </p>
        </div>
        <Pill kind={conflicts.length ? "critical" : "success"}>
          {conflicts.length} conflito{conflicts.length === 1 ? "" : "s"}
        </Pill>
      </div>
      <form className="panel class-form" onSubmit={create}>
        <label className="grow">
          Disciplina
          <select name="subject_id" required>
            <option value="">Selecione</option>
            {demand.map((r: Row) => (
              <option value={r.subject_id} key={r.subject_id}>
                {r.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Período
          <input
            name="planning_period"
            defaultValue={settings.reference_period}
          />
        </label>
        <label>
          Turma
          <input name="label" defaultValue="Turma A" />
        </label>
        <label>
          Vagas
          <input
            name="capacity"
            type="number"
            defaultValue={settings.default_capacity || 30}
          />
        </label>
        <label>
          Turno
          <select name="shift">
            <option>Noite</option>
            <option>Tarde</option>
          </select>
        </label>
        <label>
          Dia
          <select name="weekday">
            <option value="">A definir</option>
            <option>Segunda-feira</option>
            <option>Terça-feira</option>
            <option>Quarta-feira</option>
            <option>Quinta-feira</option>
            <option>Sexta-feira</option>
            <option>Sábado</option>
          </select>
        </label>
        <label>
          Início
          <input name="start_time" type="time" />
        </label>
        <label>
          Fim
          <input name="end_time" type="time" />
        </label>
        <label>
          Professor
          <input name="professor" />
        </label>
        <label>
          Sala
          <input name="room" />
        </label>
        <button className="primary">Adicionar à grade</button>
      </form>
      {conflicts.length > 0 && (
        <div className="alert error static">
          <strong>Conflitos detectados</strong>
          <span>
            {conflicts
              .map(
                (c: Row) =>
                  `Turmas ${c.class_a}/${c.class_b}: ${c.reasons.join(", ")}`,
              )
              .join(" · ")}
          </span>
        </div>
      )}
      {rows.length ? (
        <article className="panel">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Dia</th>
                  <th>Horário</th>
                  <th>Disciplina</th>
                  <th>Turno</th>
                  <th>Vagas</th>
                  <th>Professor</th>
                  <th>Sala</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {rows.map((row: Row) => (
                  <tr key={row.id}>
                    <td>{row.weekday || "A definir"}</td>
                    <td>
                      {row.start_time && row.end_time
                        ? `${row.start_time}–${row.end_time}`
                        : "A definir"}
                    </td>
                    <td>
                      <strong>{row.subject_name}</strong>
                      <small>
                        {row.label} · {row.planning_period}
                      </small>
                    </td>
                    <td>
                      <Pill kind="progress">{row.shift}</Pill>
                    </td>
                    <td>{row.capacity}</td>
                    <td>{row.professor || "—"}</td>
                    <td>{row.room || "—"}</td>
                    <td>
                      <button
                        className="danger-link"
                        onClick={() => remove(row.id)}
                      >
                        Remover
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      ) : (
        <Empty
          title="A grade ainda está vazia"
          text="Adicione disciplinas e horários para construir o cenário."
        />
      )}
    </div>
  );
}

function ReportsPanel({ students, demand }: any) {
  return (
    <div className="stack">
      <div className="section-intro">
        <div>
          <h2>Relatórios prontos para decisão</h2>
          <p>Arquivos gerados no download, sem CPF, RG ou nascimento.</p>
        </div>
      </div>
      <div className="report-grid">
        <article className="panel report-card">
          <div>⇩</div>
          <h3>Demanda consolidada</h3>
          <p>{demand} disciplinas com necessidade futura calculada.</p>
          <span>
            <a className="primary" href={`${API}/reports/demand.xlsx`}>
              Baixar Excel
            </a>
            <a className="secondary" href={`${API}/reports/demand.pdf`}>
              Baixar PDF
            </a>
          </span>
        </article>
        <article className="panel report-card">
          <div>◉</div>
          <h3>Históricos individuais</h3>
          <p>{students} perfis disponíveis. Abra um estudante para exportar.</p>
          <span>
            <button className="secondary" disabled>
              Disponível no perfil
            </button>
          </span>
        </article>
      </div>
      <article className="panel report-note">
        <i>i</i>
        <div>
          <h3>Padrão preservado</h3>
          <p>
            A planilha individual mantém Semestre, Disciplina, Status, Nota,
            Ano/Semestre e CH, com uma aba adicional de resumo.
          </p>
        </div>
      </article>
    </div>
  );
}

function SettingsPanel({ value, setValue, api, done }: any) {
  async function save(e: FormEvent) {
    e.preventDefault();
    await api("/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(value),
    });
    done();
  }
  async function restore(file?: File) {
    if (
      !file ||
      !confirm("Este backup substituirá a base atual. Deseja continuar?")
    )
      return;
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(`${API}/backup/restore`, {
      method: "POST",
      body: form,
    });
    if (!response.ok) alert((await response.json()).detail);
    else window.location.reload();
  }
  return (
    <div className="settings-layout">
      <form className="panel settings-form" onSubmit={save}>
        <div className="panel-title">
          <div>
            <span>PLANEJAMENTO</span>
            <h3>Parâmetros do semestre</h3>
          </div>
        </div>
        <label>
          Semestre de referência
          <input
            value={value.reference_period || ""}
            onChange={(e) =>
              setValue({ ...value, reference_period: e.target.value })
            }
          />
        </label>
        <label>
          Ano dos formandos
          <input
            value={value.graduation_year || ""}
            onChange={(e) =>
              setValue({ ...value, graduation_year: e.target.value })
            }
          />
        </label>
        <label>
          Capacidade das turmas
          <input
            type="number"
            value={value.default_capacity || ""}
            onChange={(e) =>
              setValue({ ...value, default_capacity: e.target.value })
            }
          />
        </label>
        <label>
          Capacidade dos estágios
          <input
            type="number"
            value={value.stage_capacity || ""}
            onChange={(e) =>
              setValue({ ...value, stage_capacity: e.target.value })
            }
          />
        </label>
        <label>
          Turno predominante
          <select
            value={value.default_shift || "Noite"}
            onChange={(e) =>
              setValue({ ...value, default_shift: e.target.value })
            }
          >
            <option>Noite</option>
            <option>Tarde</option>
          </select>
        </label>
        <label>
          Nome do usuário
          <input
            value={value.display_user || ""}
            onChange={(e) =>
              setValue({ ...value, display_user: e.target.value })
            }
          />
        </label>
        <button className="primary">Salvar configurações</button>
      </form>
      <div className="stack">
        <article className="panel backup-card">
          <div className="panel-title">
            <div>
              <span>PROTEÇÃO DOS DADOS</span>
              <h3>Backup e restauração</h3>
            </div>
          </div>
          <p>O backup contém estudantes, matrizes, intenções e grade.</p>
          <span>
            <a className="primary" href={`${API}/backup`}>
              Baixar backup
            </a>
            <label className="secondary file-button">
              Restaurar backup
              <input
                type="file"
                accept=".db"
                onChange={(e) => restore(e.target.files?.[0])}
              />
            </label>
          </span>
        </article>
        <article className="panel safety-card">
          <Pill kind="success">LOCALHOST</Pill>
          <h3>Execução restrita ao computador</h3>
          <p>
            Os históricos não são enviados a serviços externos e os PDFs não são
            retidos por padrão.
          </p>
          <ul>
            <li>Dados pessoais desnecessários não são armazenados</li>
            <li>Uploads validados e limitados</li>
            <li>Atualizações transacionais</li>
          </ul>
        </article>
      </div>
    </div>
  );
}
