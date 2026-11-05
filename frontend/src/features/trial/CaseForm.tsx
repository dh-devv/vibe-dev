import { useEffect, useState } from "react";
import type { CaseInput, Sample } from "../../types";
import { charCount } from "../../api/verdict";
import { HELPLINES, mockCrisisCheck } from "../../mock/trial";
import { Disclaimer } from "../../components/Common";

interface Props {
  onSubmit: (input: CaseInput) => void;
}

const today = (offset: number): string => {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() + offset);
  return d.toISOString().slice(0, 10);
};

export function CaseForm({ onSubmit }: Props) {
  const [title, setTitle] = useState("");
  const [caseText, setCaseText] = useState("");
  const [reason, setReason] = useState("");
  const [deadline, setDeadline] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [crisis, setCrisis] = useState(false);
  const [samples, setSamples] = useState<Sample[]>([]);

  useEffect(() => {
    fetch("/samples.json")
      .then((r) => (r.ok ? r.json() : []))
      .then((data: Sample[]) => setSamples(Array.isArray(data) ? data : []))
      .catch(() => setSamples([]));
  }, []);

  const fillSample = (s: Sample) => {
    setTitle(s.title);
    setCaseText(s.case);
    setReason(s.reason);
    setDeadline(s.deadline ?? "");
    setErrors({});
    setCrisis(false);
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const next: Record<string, string> = {};
    const t = title.trim();
    const c = caseText.trim();
    const r = reason.trim();
    if (charCount(t) < 1 || charCount(t) > 30) next.title = "재판 이름은 1자 이상 30자 이하로 적어 주세요.";
    if (charCount(c) < 5 || charCount(c) > 300) next.caseText = "미룬 내용은 5자 이상 300자 이하로 적어 주세요.";
    if (charCount(r) < 5 || charCount(r) > 200) next.reason = "미룬 사유는 5자 이상 200자 이하로 적어 주세요.";
    if (deadline && (deadline < today(0) || deadline > today(365))) next.deadline = "마감일은 오늘부터 365일 이내로 골라 주세요.";
    setErrors(next);
    if (Object.keys(next).length) return;
    if (mockCrisisCheck(`${t} ${c} ${r}`)) {
      setCrisis(true);
      return;
    }
    setCrisis(false);
    onSubmit({ title: t, caseText: c, reason: r, deadline: deadline || null });
  };

  return (
    <main className="screen scroll">
      <h1 className="page-title">재판 열기</h1>

      {crisis && (
        <section className="px-box crisis" role="alert" aria-labelledby="crisis-title">
          <h2 id="crisis-title" className="box-title">지금은 재판보다 도움이 먼저입니다</h2>
          <p>아래 상담 전화로 바로 연락해 주세요.</p>
          <ul>
            {HELPLINES.map((h) => (
              <li key={h.phone}>
                {h.name}: <strong>{h.phone}</strong> ({h.hours})
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="px-box" aria-labelledby="sample-title">
        <h2 id="sample-title" className="box-title">예시 사건</h2>
        <div className="chips">
          {samples.map((s) => (
            <button key={s.id} type="button" className="px-btn small" onClick={() => fillSample(s)}>
              {s.label}
            </button>
          ))}
        </div>
      </section>

      <form className="px-box" onSubmit={submit} noValidate>
        <div className="field">
          <label htmlFor="c-title">재판 이름</label>
          <input id="c-title" className="px-input" value={title} maxLength={60} onChange={(e) => setTitle(e.target.value)} aria-describedby="e-title" placeholder="예) 보고서 미루기 사건" />
          <p id="e-title" className="err" role="alert">{errors.title}</p>
        </div>
        <div className="field">
          <label htmlFor="c-case">미루고 있는 내용</label>
          <textarea id="c-case" className="px-input" rows={4} value={caseText} onChange={(e) => setCaseText(e.target.value)} aria-describedby="h-case e-case" placeholder="예) 교양 보고서를 3일째 못 쓰고 있다." />
          <p id="h-case" className="hint">{charCount(caseText)}/300</p>
          <p id="e-case" className="err" role="alert">{errors.caseText}</p>
        </div>
        <div className="field">
          <label htmlFor="c-reason">미룬 사유</label>
          <textarea id="c-reason" className="px-input" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} aria-describedby="h-reason e-reason" placeholder="예) 무엇부터 써야 할지 몰라서 막막하다." />
          <p id="h-reason" className="hint">{charCount(reason)}/200</p>
          <p id="e-reason" className="err" role="alert">{errors.reason}</p>
        </div>
        <div className="field">
          <label htmlFor="c-deadline">마감일 (선택)</label>
          <input id="c-deadline" type="date" className="px-input" value={deadline} min={today(0)} max={today(365)} onChange={(e) => setDeadline(e.target.value)} aria-describedby="e-deadline" />
          <p id="e-deadline" className="err" role="alert">{errors.deadline}</p>
        </div>
        <p className="note small">접수하면 입력한 내용이 AI 제공자에게 전송됩니다. 판결을 수용하면 이 화면의 기록에 담기고, 기각하면 담지 않습니다. 새로고침하면 기록은 사라집니다.</p>
        <button type="submit" className="px-btn primary big">⚖ 재판 시작</button>
      </form>
      <Disclaimer />
    </main>
  );
}
