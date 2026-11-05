import { useEffect, useState } from "react";
import type { CaseInput, Sample } from "../../types";
import { charCount } from "../../api/verdict";
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
    onSubmit({ title: t, caseText: c, reason: r, deadline: deadline || null });
  };

  return (
    <main className="screen scroll">
      <header className="intro">
        <p className="eyebrow">미루기 재판소</p>
        <h1 className="page-title">잘잘못 대신, 시작할 방법을 찾습니다</h1>
        <p className="intro-copy">미루고 있는 일을 적으면 세 AI가 서로 다른 관점에서 살펴보고, 판사가 지금 할 수 있는 맞춤 실행안을 제안합니다.</p>
      </header>

      <section className="px-box roles" aria-label="AI 역할 안내">
        <div><strong>변호인 AI</strong><span>미루는 마음과 이유를 살핍니다</span></div>
        <div><strong>검사 AI</strong><span>미룰 때 생기는 현실적인 비용을 짚습니다</span></div>
        <div><strong>판사 AI</strong><span>공방을 읽고 실행 방안을 정리합니다</span></div>
      </section>

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
        <h2 className="box-title">어떤 일을 미루고 있나요?</h2>
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
        <p className="note small">AI 토큰을 설정한 뒤 재판을 시작하면 사건 내용과 미룬 이유가 AI 제공자에게 전송됩니다. 현재 기록은 브라우저에서만 유지되며 새로고침하면 사라집니다.</p>
        <button type="submit" className="px-btn primary big">⚖ 세 AI의 공방 시작</button>
      </form>
      <Disclaimer />
    </main>
  );
}
