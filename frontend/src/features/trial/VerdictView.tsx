import type { CaseInput, Verdict } from "../../types";
import { AiBadge, Disclaimer } from "../../components/Common";

interface Props {
  input: CaseInput;
  verdict: Verdict;
  onAccept: () => void;
  onReject: () => void;
}

export function VerdictView({ input, verdict, onAccept, onReject }: Props) {
  return (
    <main className="screen scroll">
      <article className="paper" aria-labelledby="verdict-title">
        <h1 id="verdict-title" className="paper-title">
          판 결 문 <AiBadge />
        </h1>
        <p className="paper-case">사건: {input.title}</p>
        <p>
          미룬 원인(추정): <span className="cause">{verdict.cause}</span>
        </p>
        <h2>판결 요지</h2>
        <p>{verdict.summary}</p>
        <h2>처방</h2>
        {verdict.prescriptions.map((p, i) => (
          <section key={p.title} className="presc">
            <h3>
              처방 {i + 1}. {p.title} <small>({p.minutes}분)</small>
            </h3>
            <ol>
              {p.steps.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ol>
            <p className="hint">이유: {p.reason}</p>
          </section>
        ))}
        <p className="hint">근거 발언: {verdict.evidence.map((n) => `${n}번`).join(", ")}</p>
        <div className="seal" aria-hidden="true">판결</div>
      </article>

      <div className="row decision">
        <button className="px-btn primary big" onClick={onAccept}>✔ 수용</button>
        <button className="px-btn big" onClick={onReject}>✖ 기각</button>
      </div>
      <p className="note small center">수용한 판결은 이 화면의 기록에 담깁니다. 새로고침하면 사라집니다. 기각하면 담지 않습니다.</p>
      <Disclaimer />
    </main>
  );
}
