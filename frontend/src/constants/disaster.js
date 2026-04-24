/**
 * 재난상황 대시보드 공통 상수
 *
 * 내부 코드 ↔ 화면 표시 라벨 매핑.
 * 백엔드 disaster_constants.py와 동일해야 함.
 * 변경 시 양쪽 모두 업데이트 필요.
 */

export const INCIDENT_TYPE_LABELS = {
  road_control: "도로통제",
  landslide: "산사태·토사유출",
  tree_fall: "나무전도",
  flood: "침수·범람",
  sinkhole: "싱크홀·노면파손",
  drainage: "배수·맨홀·양수",
  facility: "시설물 이상",
  inspection: "기타/미분류",
};

export const STATUS_LABELS = {
  reported: "발생",
  in_progress: "조치중",
  completed: "조치완료",
  monitoring: "모니터링",
  no_issue: "이상없음",
  closed: "해제·종결",
};

/** 유형 코드를 한글 라벨로 변환. 미등록 코드는 원본 반환. */
export const incidentLabel = (code) =>
  INCIDENT_TYPE_LABELS[code] || code || "미분류";

/** 상태 코드를 한글 라벨로 변환. 미등록 코드는 원본 반환. */
export const statusLabel = (code) => STATUS_LABELS[code] || code || "미분류";

/** sessionStorage 키 */
export const DISASTER_SESSION_KEYS = {
  UPLOAD_ID: "disaster_active_upload_id",
  UPLOAD_NAME: "disaster_active_upload_name",
};

/** 커스텀 이벤트명 - sessionStorage 변경을 동일 탭 내 컴포넌트에 알림 */
export const DISASTER_SESSION_EVENT = "disaster-session-changed";

/**
 * 현재 세션의 업로드 정보 설정 + 커스텀 이벤트 발행.
 * useDisasterSession 훅이 이 이벤트를 수신해 재렌더링함.
 */
export function setDisasterSession(uploadId, fileName = "") {
  if (uploadId) {
    sessionStorage.setItem(DISASTER_SESSION_KEYS.UPLOAD_ID, uploadId);
    sessionStorage.setItem(DISASTER_SESSION_KEYS.UPLOAD_NAME, fileName);
  } else {
    sessionStorage.removeItem(DISASTER_SESSION_KEYS.UPLOAD_ID);
    sessionStorage.removeItem(DISASTER_SESSION_KEYS.UPLOAD_NAME);
  }
  window.dispatchEvent(new Event(DISASTER_SESSION_EVENT));
}

/** 현재 세션의 업로드 정보 조회 (read-only 헬퍼) */
export function getDisasterSession() {
  return {
    uploadId: sessionStorage.getItem(DISASTER_SESSION_KEYS.UPLOAD_ID) || "",
    fileName: sessionStorage.getItem(DISASTER_SESSION_KEYS.UPLOAD_NAME) || "",
  };
}