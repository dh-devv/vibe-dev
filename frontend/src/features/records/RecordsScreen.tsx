import { useState } from "react";
import type { TrialRecord } from "../../types";
import { Disclaimer } from "../../components/Common";
import { Execution } from "./Execution";

interface Props {
  records: TrialRecord[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  onChecks: (id: string, checks: boolean[][]) => void;
  onDelete: (id: string) => void;
  onDeleteAll: () => void;
}

function duration(ms: number): string {
  const sec = Math.max(0, Math.round(ms / 1000));
  if (sec < 60) return `${sec}초`;
  const min = Math.floor(sec / 60);
  return min < 60 ? `${min}분 ${sec % 60}초` : `${Math.floor(min / 60)}시간 ${min % 60}분`;
}

export function RecordsScreen({ records, selectedId, onSelect, onChecks, onDelete, onDeleteAll }: Props) {
  const [confirming, setConfirming] = useState<null | "all" | string>(null);
  const selected = records.find((r) => r.id === selectedId) ?? null;

  const done = records.filter((r) => r.completedAt).length;
  const gaps = records
    .filter((r) => r.firstCheckedAt)
    .map((r) => Date.parse(r.firstCheckedAt as string) - Date.parse(r.submittedAt))
    .filter((n) => Number.isFinite(n));
  const rate = records.length ? `${Math.round((done / records.length) * 100)}%` : "기록 없음";
  const start = gaps.length ? duration(gaps.reduce((a, b) => a + b, 0) / gaps.length) : "기록 없음";

  const confirmLabel = confirming === "all" ? "기록을 모두 지울까요?" : "이 기록을 지울까요?";

  const doConfirm = () => {
    if (confirming === "all") onDeleteAll();
    else if (confirming) onDelete(confirming);
    setConfirming(null);
  };

  return (
    <main className="screen scroll">
      <h1 className="page-title">내 기록</h1>
      <div className="stats">
        <div className="px-box stat"><b>{records.length}</b><span>수용 건수</span></div>
        <div className="px-box stat"><b>{rate}</b><span>이행률</span></div>
        <div className="px-box stat"><b>{start}</b><span>첫 체크까지</span></div>
      </div>

      {selected && <Execution record={selected} onChecks={(c) => onChecks(selected.id, c)} />}

      <section className="px-box" aria-labelledby="list-title">
        <h2 id="list-title" className="box-title">판결 목록</h2>
        {records.length === 0 ? (
          <p className="note">아직 수용한 판결이 없습니다. 재판을 열고 판결을 수용해 보세요.</p>
        ) : (
          <ul className="rec-list">
            {records.map((r) => (
              <li key={r.id} className={r.id === selectedId ? "on" : ""}>
                <div className="rec-text">
                  <strong>{r.title}</strong>
                  <span>{r.verdict.prescriptions[0].title}{r.completedAt ? " · 완료" : ""}</span>
                </div>
                <div className="row">
                  <button className="px-btn small" onClick={() => onSelect(r.id)}>집행 열기</button>
                  <button className="px-btn small danger" onClick={() => setConfirming(r.id)}>삭제</button>
                </div>
              </li>
            ))}
          </ul>
        )}
        <div className="row">
          <button className="px-btn small danger" disabled={records.length === 0} onClick={() => setConfirming("all")}>기록 모두 지우기</button>
        </div>
      </section>

      {confirming && (
        <div className="modal" role="alertdialog" aria-modal="true" aria-labelledby="confirm-text">
          <div className="px-box">
            <p id="confirm-text">{confirmLabel}</p>
            <div className="row">
              <button className="px-btn danger" onClick={doConfirm}>지우기</button>
              <button className="px-btn" onClick={() => setConfirming(null)}>취소</button>
            </div>
          </div>
        </div>
      )}
      <p className="note small center">목업: 지금은 새로고침하면 기록이 사라집니다.</p>
      <Disclaimer />
    </main>
  );
}
