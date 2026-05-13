import { useState, useEffect } from 'react';

const BACKEND_URL =
  import.meta.env.VITE_API_URL ||
  'https://cj-ai-backend.ashysky-a846c5bf.koreacentral.azurecontainerapps.io';

const MAX_RETRIES = 10;
const RETRY_INTERVAL_MS = 3000;

/**
 * 앱 최초 진입 시 백엔드 health check를 수행한다.
 * Azure Container Apps 콜드스타트 대응: 3초 간격으로 최대 10회 재시도.
 *
 * 반환값:
 *   'loading' — 아직 확인 중
 *   'ready'   — 서버 정상 응답
 *   'error'   — 최대 재시도 후에도 실패
 */
export function useBackendWakeup() {
  const [status, setStatus] = useState('loading');

  useEffect(() => {
    let cancelled = false;
    let attempt = 0;

    async function tryHealth() {
      while (attempt < MAX_RETRIES) {
        if (cancelled) return;
        try {
          const res = await fetch(`${BACKEND_URL}/api/health`, {
            method: 'GET',
            signal: AbortSignal.timeout(5000),
          });
          if (res.ok) {
            if (!cancelled) setStatus('ready');
            return;
          }
        } catch {
          // 네트워크 오류 또는 타임아웃 → 재시도
        }
        attempt += 1;
        if (attempt < MAX_RETRIES && !cancelled) {
          await new Promise((resolve) => setTimeout(resolve, RETRY_INTERVAL_MS));
        }
      }
      if (!cancelled) setStatus('error');
    }

    tryHealth();
    return () => {
      cancelled = true;
    };
  }, []);

  return status;
}
