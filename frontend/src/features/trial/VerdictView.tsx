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
          지금 시작할 맞춤 방안 <AiBadge />
        </h1>
        <p className="paper-case">사건: {input.title}</p>
        <p>
          미루는 데 영향을 준 이유(추정): <span className="cause">{verdict.cause}</span>
        </p>
        <h2>공방 정리</h2>
        <p>{verdict.summary}</p>
        <h2>추천 실행 방안</h2>
        {verdict.prescriptions.map((p, i) => (
          <section key={p.title} className="presc">
            <h3>
              방안 {i + 1}. {p.title} <small>({p.minutes}분)</small>
            </h3>
            <ol>
              {p.steps.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ol>
            <p className="hint">이유: {p.reason}</p>
          </section>
        ))}
        <p className="hint">참고한 공방 발언: {verdict.evidence.map((n) => `${n}번`).join(", ")}</p>
        <div className="seal" aria-hidden="true">추천</div>
      </article>

      <div className="row decision">
        <button className="px-btn primary big" onClick={onAccept}>이 방안으로 시작</button>
        <button className="px-btn big" onClick={onReject}>다른 방안 찾기</button>
      </div>
      <p className="note small center">시작을 선택한 방안은 내 기록에 추가됩니다. 다시 찾기를 선택하면 기록하지 않습니다.</p>
      <Disclaimer />
    </main>
  );
}
