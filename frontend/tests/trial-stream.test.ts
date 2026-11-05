import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, runTrial } from "../src/api/trial";
import type { CaseInput } from "../src/types";

const input: CaseInput = { title: "t", caseText: "보고서를 못 쓴다", reason: "막막하다", deadline: null };

const verdict = {
  summary: "요지",
  cause: "막막함",
  prescriptions: [{ title: "제목", steps: ["하나", "둘"], minutes: 10, reason: "이유" }],
  evidence: [1]
};

const sse = (events: [string, unknown][]) =>
  new Response(events.map(([e, d]) => `event: ${e}\ndata: ${JSON.stringify(d)}\n\n`).join(""), {
    headers: { "Content-Type": "text/event-stream" }
  });

async function collect(gen: AsyncGenerator<unknown>) {
  const out: unknown[] = [];
  for await (const e of gen) out.push(e);
  return out;
}

afterEach(() => vi.unstubAllGlobals());

describe("서버 재판 스트림", () => {
  it("API_SPEC 이벤트를 화면용 이벤트로 바꾼다", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      sse([
        ["trial_started", { submittedAt: "2026-11-05T05:00:00Z" }],
        ["stage", { stage: "defense", n: 1 }],
        ["statement_done", { n: 1, role: "defense", text: "변론입니다" }],
        ["verdict", verdict],
        ["done", {}]
      ])
    ));
    const out = (await collect(runTrial(input, { signal: new AbortController().signal }))) as { type: string }[];
    expect(out.map((e) => e.type)).toEqual(["started", "beat", "verdict"]);
  });

  it("형식이 틀린 판결문은 오류로 처리한다", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(sse([["verdict", { ...verdict, evidence: [9] }]])));
    await expect(collect(runTrial(input, { signal: new AbortController().signal }))).rejects.toMatchObject({ code: "VERDICT_INVALID" });
  });

  it("위기 신호 응답은 상담 전화 목록과 함께 오류로 던진다", async () => {
    const body = { code: "CRISIS_SIGNAL", message: "도움이 먼저입니다", retryable: false, helplines: [{ name: "a", phone: "109", hours: "24시간" }] };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status: 422 })));
    const err = await collect(runTrial(input, { signal: new AbortController().signal })).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.helplines).toHaveLength(1);
  });
});
