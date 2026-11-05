import { useState } from "react";
import type { CaseInput, TrialRecord, Verdict } from "../types";
import { CaseForm } from "../features/trial/CaseForm";
import { Courtroom } from "../features/trial/Courtroom";
import { VerdictView } from "../features/trial/VerdictView";
import { RecordsScreen } from "../features/records/RecordsScreen";
import { Scales } from "../components/PixelArt";

type Screen = "new" | "trial" | "verdict" | "records";

interface Trial {
  input: CaseInput;
  submittedAt: string;
  verdict: Verdict | null;
}

export function App() {
  const [screen, setScreen] = useState<Screen>("new");
  const [trial, setTrial] = useState<Trial | null>(null);
  const [records, setRecords] = useState<TrialRecord[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const accept = () => {
    if (!trial?.verdict) return;
    const now = new Date().toISOString();
    const rec: TrialRecord = {
      id: crypto.randomUUID(),
      title: trial.input.title,
      caseText: trial.input.caseText,
      deadline: trial.input.deadline,
      submittedAt: trial.submittedAt,
      acceptedAt: now,
      verdict: trial.verdict,
      checks: trial.verdict.prescriptions.map((p) => p.steps.map(() => false)),
      firstCheckedAt: null,
      completedAt: null
    };
    setRecords([rec, ...records].slice(0, 50));
    setSelectedId(rec.id);
    setTrial(null);
    setScreen("records");
  };

  const updateChecks = (id: string, checks: boolean[][]) => {
    const now = new Date().toISOString();
    setRecords((rs) =>
      rs.map((r) => {
        if (r.id !== id) return r;
        const all = checks.every((row) => row.every(Boolean));
        const any = checks.some((row) => row.some(Boolean));
        return {
          ...r,
          checks,
          firstCheckedAt: r.firstCheckedAt ?? (any ? now : null),
          completedAt: all ? r.completedAt ?? now : null
        };
      })
    );
  };

  return (
    <div className="app">
      <header className="topbar">
        <Scales className="logo" />
        <span className="brand">미루기 재판소</span>
        <span className="brand-note">나에게 맞는 시작 방법 찾기</span>
      </header>

      {screen === "new" && (
        <CaseForm
          onSubmit={(input) => {
            setTrial({ input, submittedAt: new Date().toISOString(), verdict: null });
            setScreen("trial");
          }}
        />
      )}
      {screen === "trial" && trial && (
        <Courtroom
          input={trial.input}
          onFinish={(verdict, submittedAt) => {
            setTrial({ ...trial, submittedAt, verdict });
            setScreen("verdict");
          }}
          onExit={() => { setTrial(null); setScreen("new"); }}
        />
      )}
      {screen === "verdict" && trial?.verdict && (
        <VerdictView
          input={trial.input}
          verdict={trial.verdict}
          onAccept={accept}
          onReject={() => {
            setTrial(null);
            setScreen("new");
          }}
        />
      )}
      {screen === "records" && (
        <RecordsScreen
          records={records}
          selectedId={selectedId}
          onSelect={setSelectedId}
          onChecks={updateChecks}
          onDelete={(id) => {
            setRecords((rs) => rs.filter((r) => r.id !== id));
            if (selectedId === id) setSelectedId(null);
          }}
          onDeleteAll={() => { setRecords([]); setSelectedId(null); }}
        />
      )}

      <nav className="bottomnav" aria-label="메뉴">
        <button className={screen === "new" || screen === "trial" || screen === "verdict" ? "on" : ""} onClick={() => { setTrial(null); setScreen("new"); }}>
          <span aria-hidden="true">⚖</span>재판 열기
        </button>
        <button className={screen === "records" ? "on" : ""} onClick={() => setScreen("records")}>
          <span aria-hidden="true">📜</span>실행 기록
        </button>
      </nav>
    </div>
  );
}
