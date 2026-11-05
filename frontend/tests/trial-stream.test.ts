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

  it("발언 조각을 도착하는 대로 화면 이벤트로 전달한다", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      sse([
        ["stage", { stage: "defense", n: 1 }],
        ["statement", { n: 1, role: "defense", delta: "원문 " }],
        ["statement", { n: 1, role: "defense", delta: "그대로 " }],
        ["statement_done", { n: 1, role: "defense", text: "원문 그대로 " }]
      ])
    ));
    const out = (await collect(runTrial(input, { signal: new AbortController().signal }))) as {
      type: string;
      delta?: string;
      n?: number;
    }[];
    expect(out.map((e) => e.type)).toEqual(["beat_delta", "beat_delta", "beat_finish"]);
    expect(out.filter((e) => e.type === "beat_delta").map((e) => e.delta).join("")).toBe("원문 그대로 ");
    expect(out.at(-1)).toEqual({ type: "beat_finish", n: 1 });
  });

  it("사용자가 입력한 사건과 사유를 자르지 않고 API에 전달한다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(sse([]));
    vi.stubGlobal("fetch", fetchMock);
    const fullInput = { ...input, caseText: "가".repeat(300), reason: "나".repeat(200) };
    await collect(runTrial(fullInput, { signal: new AbortController().signal }));

    expect(JSON.parse(fetchMock.mock.calls[0][1].body as string)).toEqual({
      case: fullInput.caseText,
      reason: fullInput.reason,
      deadline: fullInput.deadline
    });
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
