import { useEffect, useRef, useState } from "react";
import type { TrialRecord } from "../../types";
import { AiBadge } from "../../components/Common";

const clock = (sec: number): string => `${String(Math.floor(sec / 60)).padStart(2, "0")}:${String(sec % 60).padStart(2, "0")}`;

function Timer({ minutes }: { minutes: number }) {
  const total = minutes * 60;
  const [left, setLeft] = useState(total);
  const [running, setRunning] = useState(false);
  const ref = useRef<number | null>(null);

  useEffect(() => {
    if (!running) return;
    ref.current = window.setInterval(() => {
      setLeft((v) => {
        if (v <= 1) {
          setRunning(false);
          return 0;
        }
        return v - 1;
      });
    }, 1000);
    return () => {
      if (ref.current !== null) window.clearInterval(ref.current);
    };
  }, [running]);

  return (
    <div className="timer-row">
      <span className="timer" role="timer">{left === 0 ? "00:00 종료" : clock(left)}</span>
      <button className="px-btn small" onClick={() => (left === 0 ? (setLeft(total), setRunning(true)) : setRunning(!running))}>
        {running ? "멈춤" : "시작"}
      </button>
      <button className="px-btn small" onClick={() => { setRunning(false); setLeft(total); }}>초기화</button>
    </div>
  );
}

interface Props {
  record: TrialRecord;
  onChecks: (checks: boolean[][]) => void;
}

export function Execution({ record, onChecks }: Props) {
  const toggle = (i: number, j: number) => {
    const next = record.checks.map((row) => row.slice());
    next[i][j] = !next[i][j];
    onChecks(next);
  };

  return (
    <section className="px-box" aria-labelledby="exec-title">
      <h2 id="exec-title" className="box-title">집행: {record.title}</h2>
      {record.verdict.prescriptions.map((p, i) => (
        <div key={p.title} className="presc dark">
          <h3>{p.title} <small>({p.minutes}분)</small> <AiBadge /></h3>
          <ul className="checks">
            {p.steps.map((s, j) => (
              <li key={s}>
                <label className="check">
                  <input type="checkbox" checked={record.checks[i][j]} onChange={() => toggle(i, j)} />
                  <span>{s}</span>
                </label>
              </li>
            ))}
          </ul>
          <Timer minutes={p.minutes} />
        </div>
      ))}
      {record.completedAt && <p className="done" role="status">★ 모든 단계를 마쳤습니다. 집행 완료!</p>}
    </section>
  );
}
