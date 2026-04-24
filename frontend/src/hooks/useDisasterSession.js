import { useEffect, useState } from "react";
import {
  DISASTER_SESSION_EVENT,
  DISASTER_SESSION_KEYS,
  getDisasterSession,
} from "../constants/disaster";

/**
 * 재난 대시보드 세션 상태 훅.
 *
 * sessionStorage를 리액티브하게 구독:
 * - focus 이벤트 (탭 전환 복귀 시)
 * - storage 이벤트 (다른 탭에서 변경 시)
 * - DISASTER_SESSION_EVENT 커스텀 이벤트 (같은 탭 내 setDisasterSession 호출 시)
 *
 * 반환값: { uploadId, fileName, refresh }
 */
export function useDisasterSession() {
  const [session, setSession] = useState(getDisasterSession());

  useEffect(() => {
    const refresh = () => {
      setSession(getDisasterSession());
    };

    // 1. 같은 탭 내 커스텀 이벤트 (setDisasterSession 호출 시)
    window.addEventListener(DISASTER_SESSION_EVENT, refresh);

    // 2. 탭 전환 복귀 (다른 곳에서 sessionStorage 변경 후 돌아올 때)
    window.addEventListener("focus", refresh);

    // 3. 다른 탭에서 sessionStorage 변경 (참고: sessionStorage는 탭 독립이라 거의 안 발생)
    window.addEventListener("storage", refresh);

    return () => {
      window.removeEventListener(DISASTER_SESSION_EVENT, refresh);
      window.removeEventListener("focus", refresh);
      window.removeEventListener("storage", refresh);
    };
  }, []);

  return {
    uploadId: session.uploadId,
    fileName: session.fileName,
    refresh: () => setSession(getDisasterSession()),
  };
}