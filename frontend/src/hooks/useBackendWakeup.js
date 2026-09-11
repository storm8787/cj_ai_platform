import { useState, useEffect } from 'react';

const BACKEND_URL =
  import.meta.env.VITE_API_URL ||
  'https://cj-ai-backend.ashysky-a846c5bf.koreacentral.azurecontainerapps.io';

// 백엔드는 Azure Container Apps 에서 min-replicas 0 (유휴 시 scale-to-zero)으로 운영한다.
// 요청이 한동안 없었다면 첫 요청이 replica 기동을 유발하고, 이미지 pull 이 남아 있으면
// 수 분까지 걸릴 수 있다. 그래서 재시도 창을 넉넉히 잡는다 (최대 약 6분).
// 폴링 요청 자체가 scale-from-zero 트리거이므로, 기동이 끝나면 즉시 'ready' 로 바뀐다.
const MAX_RETRIES = 40;
const RETRY_INTERVAL_MS = 5000;
const REQUEST_TIMEOUT_MS = 10000;

/**
 * 앱 최초 진입 시 백엔드 health check를 수행한다.
 * Azure Container Apps 콜드스타트 대응: 5초 간격으로 최대 40회 재시도.
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
            signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
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
