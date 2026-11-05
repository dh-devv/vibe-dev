export type Cause = "막막함" | "완벽주의" | "흥미 상실" | "시간 부족" | "피로";

export interface Prescription {
  title: string;
  steps: string[];
  minutes: number;
  reason: string;
}

export interface Verdict {
  summary: string;
  cause: Cause;
  prescriptions: Prescription[];
  evidence: number[];
}

export type Speaker = "judge" | "jury" | "defense" | "prosecution" | "user";

export interface CaseInput {
  title: string;
  caseText: string;
  reason: string;
  deadline: string | null;
}

export interface TrialRecord {
  id: string;
  title: string;
  caseText: string;
  deadline: string | null;
  submittedAt: string;
  acceptedAt: string;
  verdict: Verdict;
  checks: boolean[][];
  firstCheckedAt: string | null;
  completedAt: string | null;
}

export interface Sample extends CaseInput {
  id: string;
  label: string;
  case: string;
}
