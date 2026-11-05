import { useState } from "react";
import { Courthouse } from "../../components/PixelArt";
import { Disclaimer } from "../../components/Common";

interface Props {
  onLogin: (name: string) => void;
}

// 로그인·가입은 관리형 OIDC 제공자가 처리한다 (API_SPEC 2절). 이 화면은 제공자로 이동하는 진입점이며,
// 비밀번호 같은 자격 증명을 앱 화면에서 받지 않는다. 지금은 목업이라 이동 대신 바로 입장한다.
export function LoginScreen({ onLogin }: Props) {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const isLogin = mode === "login";

  return (
    <main className="screen login">
      <div className="title-art" aria-hidden="true">
        <Courthouse className="courthouse" />
      </div>
      <h1 className="game-title">
        <span>미루기</span>
        <span>재판소</span>
      </h1>
      <p className="subtitle">미루는 이유를 공방으로 가리고, 판사가 처방을 내립니다.</p>

      <section className="px-box login-box" aria-labelledby="login-title">
        <div className="tabs" role="tablist" aria-label="로그인 방식">
          <button role="tab" aria-selected={isLogin} className={isLogin ? "tab on" : "tab"} onClick={() => setMode("login")}>
            로그인
          </button>
          <button role="tab" aria-selected={!isLogin} className={!isLogin ? "tab on" : "tab"} onClick={() => setMode("signup")}>
            회원 가입
          </button>
        </div>
        <h2 id="login-title" className="box-title">
          {isLogin ? "입장 등록" : "새 방청객 등록"}
        </h2>
        <p className="note">
          {isLogin
            ? "관리형 로그인 제공자 화면으로 이동해 로그인합니다."
            : "관리형 로그인 제공자 화면에서 계정을 만듭니다. 비밀번호는 이 앱이 받지 않습니다."}
        </p>
        <button className="px-btn primary big" onClick={() => onLogin("방청객")}>
          {isLogin ? "▶ 로그인하고 입장" : "★ 가입하고 입장"}
        </button>
        <p className="note small">목업 화면입니다. 실제 로그인은 서버와 연결한 뒤 동작합니다.</p>
      </section>
      <Disclaimer />
    </main>
  );
}
