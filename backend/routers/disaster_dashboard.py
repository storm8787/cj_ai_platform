"""
재난상황 대시보드 라우터

변경사항 (v7.1):
- analyze 엔드포인트에 중복 실행 방지 락 추가 (analysis_status 기반)
- print → logging 전환, PII 출력 최소화
- incident_rows가 비어 있을 때 .insert([]) 호출 방지
- analyze 실패 시 analysis_status='failed'로 롤백
"""

import logging
from collections import Counter
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, UploadFile

from services.disaster_incident_service import build_incidents
from services.disaster_parser_service import (
    extract_emd,
    extract_location_raw,
    extract_related_agency,
    infer_incident_type,
    infer_status,
    normalize_summary,
    parse_kakao_txt,
)
from services.disaster_constants import INCIDENT_TYPE_LABELS, STATUS_LABELS
from services.disaster_report_service import generate_daily_report
from services.supabase_service import get_supabase_client

# 충주시 읍면동 중심 좌표 (Kakao Maps fallback용 좌표 데이터)
EMD_COORDS: dict = {
    "더덕읍":    {"lat": 36.9614, "lng": 127.9052},
    "살미면":    {"lat": 36.9246, "lng": 127.9573},
    "수안보면":  {"lat": 36.8447, "lng": 127.9753},
    "대소원면":  {"lat": 36.9938, "lng": 127.8543},
    "신니면":    {"lat": 36.9673, "lng": 127.8237},
    "노은면":    {"lat": 37.0203, "lng": 127.8640},
    "앙성면":    {"lat": 36.9948, "lng": 127.9673},
    "중앙탑면":  {"lat": 37.0185, "lng": 127.9498},
    "금가면":    {"lat": 37.0397, "lng": 127.8867},
    "동량면":    {"lat": 36.9104, "lng": 127.8621},
    "산척면":    {"lat": 36.9023, "lng": 127.9156},
    "엄정면":    {"lat": 37.0648, "lng": 127.9843},
    "소태면":    {"lat": 36.8738, "lng": 127.8735},
    "성내충인동": {"lat": 36.9917, "lng": 127.9281},
    "교현안림동": {"lat": 36.9854, "lng": 127.9235},
    "교현2동":   {"lat": 36.9830, "lng": 127.9280},
    "용산동":    {"lat": 37.0011, "lng": 127.9212},
    "지현동":    {"lat": 36.9938, "lng": 127.9305},
    "문화동":    {"lat": 37.0052, "lng": 127.9273},
    "호암직동":  {"lat": 36.9723, "lng": 127.9234},
    "달천동":    {"lat": 36.9601, "lng": 127.9142},
    "봉방동":    {"lat": 36.9814, "lng": 127.9371},
    "칠금금릉동": {"lat": 36.9774, "lng": 127.9406},
    "연수동":    {"lat": 36.9878, "lng": 127.9498},
    "목행용탄동": {"lat": 37.0027, "lng": 127.9546},
}

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload")
async def upload_disaster_chat(file: UploadFile = File(...)):
    supabase = get_supabase_client()

    if not file.filename:
        raise HTTPException(status_code=400, detail="파일이 없습니다.")
    if not file.filename.lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="txt 파일만 업로드 가능합니다.")

    raw = await file.read()

    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            content = raw.decode("cp949")
        except Exception:
            raise HTTPException(status_code=400, detail="파일 인코딩을 읽을 수 없습니다.")

    # 업로드 레코드 생성
    upload_res = supabase.table("disaster_uploads").insert(
        {
            "file_name": file.filename,
            "source_type": "kakao_txt",
            "analysis_status": "uploaded",
        }
    ).execute()

    upload_row = upload_res.data[0]
    upload_id = upload_row["id"]

    logger.info("upload created: upload_id=%s, file=%s", upload_id, file.filename)

    # 메시지 파싱 (실패 시에도 upload는 보존)
    try:
        parsed_messages = parse_kakao_txt(content)
    except Exception as e:
        logger.exception("parse failed: upload_id=%s", upload_id)
        supabase.table("disaster_uploads").update(
            {"analysis_status": "parse_failed"}
        ).eq("id", upload_id).execute()
        raise HTTPException(
            status_code=500, detail=f"파일 파싱 실패: {type(e).__name__}"
        )

    rows = []
    for msg in parsed_messages:
        rows.append(
            {
                "upload_id": upload_id,
                "message_time": msg["message_time"],
                "sender_name": msg["sender_name"],
                "raw_text": msg["raw_text"],
                "message_type": msg["message_type"],
                "photo_count": msg["photo_count"],
                "is_system": msg["is_system"],
                "parsed_success": msg["parsed_success"],
            }
        )

    if rows:
        supabase.table("disaster_raw_messages").insert(rows).execute()

    valid_count = len([m for m in parsed_messages if m["message_type"] == "normal"])

    supabase.table("disaster_uploads").update(
        {
            "message_count": len(parsed_messages),
            "valid_message_count": valid_count,
            "analysis_status": "uploaded",
        }
    ).eq("id", upload_id).execute()

    logger.info(
        "upload parsed: upload_id=%s, total=%d, valid=%d",
        upload_id, len(parsed_messages), valid_count,
    )

    return {
        "success": True,
        "upload_id": upload_id,
        "file_name": file.filename,
        "message_count": len(parsed_messages),
        "valid_message_count": valid_count,
    }


@router.get("/uploads")
def get_disaster_uploads(limit: int = 20):
    supabase = get_supabase_client()
    res = (
        supabase.table("disaster_uploads")
        .select("*")
        .order("uploaded_at", desc=True)
        .limit(limit)
        .execute()
    )
    return {"items": res.data or []}


@router.post("/analyze/{upload_id}")
async def analyze_disaster_chat(upload_id: str):
    """
    업로드된 메시지를 사건 단위로 재구성.

    - analysis_status='analyzing' 상태면 409 반환 (중복 실행 방지)
    - 분석 중 실패하면 analysis_status='failed'로 롤백
    """
    supabase = get_supabase_client()

    # 1) 현재 상태 확인 및 락 획득
    upload_res = (
        supabase.table("disaster_uploads")
        .select("id, analysis_status")
        .eq("id", upload_id)
        .single()
        .execute()
    )
    if not upload_res.data:
        raise HTTPException(status_code=404, detail="업로드 정보를 찾을 수 없습니다.")

    current_status = upload_res.data.get("analysis_status")
    if current_status == "analyzing":
        raise HTTPException(
            status_code=409,
            detail="이미 분석 중인 업로드입니다. 잠시 후 다시 시도해주세요.",
        )

    # 락 획득: 상태를 analyzing으로 변경
    supabase.table("disaster_uploads").update(
        {"analysis_status": "analyzing"}
    ).eq("id", upload_id).execute()

    try:
        return _run_analysis(supabase, upload_id)
    except HTTPException:
        # 404 등 명시적 예외는 상태만 되돌리고 그대로 전파
        supabase.table("disaster_uploads").update(
            {"analysis_status": current_status or "uploaded"}
        ).eq("id", upload_id).execute()
        raise
    except Exception as e:
        logger.exception("analyze failed: upload_id=%s", upload_id)
        supabase.table("disaster_uploads").update(
            {"analysis_status": "failed"}
        ).eq("id", upload_id).execute()
        raise HTTPException(
            status_code=500, detail=f"분석 실패: {type(e).__name__}"
        )


def _run_analysis(supabase, upload_id: str) -> dict:
    """실제 분석 로직 (락 획득 후 호출)"""

    msg_res = (
        supabase.table("disaster_raw_messages")
        .select("*")
        .eq("upload_id", upload_id)
        .order("message_time")
        .execute()
    )

    raw_count = len(msg_res.data or [])
    logger.info("analyze start: upload_id=%s, raw_messages=%d", upload_id, raw_count)

    if not msg_res.data:
        raise HTTPException(status_code=404, detail="업로드된 메시지가 없습니다.")

    # 원본 메시지에 분류 메타데이터 부착
    parsed_messages = []
    for row in msg_res.data:
        text = row["raw_text"] or ""
        incident_type = infer_incident_type(text)

        parsed_messages.append(
            {
                "id": row["id"],
                "message_time": row["message_time"],
                "sender_name": row["sender_name"],
                "raw_text": text,
                "message_type": row["message_type"],
                "photo_count": row["photo_count"],
                "is_system": row["is_system"],
                "parsed_success": row["parsed_success"],
                "emd": extract_emd(text),
                "location_raw": extract_location_raw(text),
                "incident_type": incident_type,
                "status": infer_status(text, incident_type),
                "related_agency": extract_related_agency(text),
                "summary": normalize_summary(text),
            }
        )

    normal_count = len([m for m in parsed_messages if m.get("message_type") == "normal"])
    logger.info(
        "analyze parsed: upload_id=%s, parsed=%d, normal=%d",
        upload_id, len(parsed_messages), normal_count,
    )

    # 사건 재구성
    incidents = build_incidents(parsed_messages)
    logger.info("analyze incidents built: upload_id=%s, count=%d", upload_id, len(incidents))

    # 기존 incident_messages 삭제
    existing_incidents_res = (
        supabase.table("disaster_incidents")
        .select("id")
        .eq("upload_id", upload_id)
        .execute()
    )
    existing_ids = [r["id"] for r in (existing_incidents_res.data or [])]
    if existing_ids:
        supabase.table("disaster_incident_messages").delete().in_(
            "incident_id", existing_ids
        ).execute()

    # 기존 incidents 삭제
    supabase.table("disaster_incidents").delete().eq("upload_id", upload_id).execute()

    incident_rows = []
    for incident in incidents:
        incident_rows.append(
            {
                "upload_id": upload_id,
                "incident_time": incident["incident_time"],
                "first_report_time": incident["first_report_time"],
                "last_update_time": incident["last_update_time"],
                "emd": incident["emd"],
                "location_raw": incident["location_raw"],
                "location_normalized": incident["location_normalized"],
                "incident_type": incident["incident_type"],
                "severity": incident["severity"],
                "status": incident["status"],
                "summary": incident["summary"],
                "damage_text": incident["damage_text"],
                "action_text": incident["action_text"],
                "related_agency": incident["related_agency"],
                "reporter_name": incident["reporter_name"],
                "photo_count": incident["photo_count"],
                "message_count": incident["message_count"],
                "is_reportable": incident["is_reportable"],
            }
        )

    # 빈 배열 가드
    inserted_incidents = []
    if incident_rows:
        incident_insert_res = (
            supabase.table("disaster_incidents").insert(incident_rows).execute()
        )
        inserted_incidents = incident_insert_res.data or []

    logger.info(
        "analyze incidents inserted: upload_id=%s, count=%d",
        upload_id, len(inserted_incidents),
    )

    # raw_message ↔ incident 링크 테이블
    link_rows = []
    for idx, incident in enumerate(incidents):
        if idx >= len(inserted_incidents):
            continue

        incident_id = inserted_incidents[idx]["id"]

        for rm in incident["raw_messages"]:
            if rm.get("id"):
                relation_type = "photo" if rm["message_type"] == "photo" else "primary"
                link_rows.append(
                    {
                        "incident_id": incident_id,
                        "raw_message_id": rm["id"],
                        "relation_type": relation_type,
                    }
                )

    if link_rows:
        supabase.table("disaster_incident_messages").insert(link_rows).execute()

    logger.info(
        "analyze links inserted: upload_id=%s, count=%d",
        upload_id, len(link_rows),
    )

    # 분석 완료 상태로 변경 (락 해제)
    supabase.table("disaster_uploads").update(
        {
            "incident_count": len(incidents),
            "analysis_status": "analyzed",
        }
    ).eq("id", upload_id).execute()

    logger.info("analyze complete: upload_id=%s, incidents=%d", upload_id, len(incidents))

    return {
        "success": True,
        "upload_id": upload_id,
        "incident_count": len(incidents),
    }


@router.get("/upload/{upload_id}/summary")
def get_upload_summary(upload_id: str):
    supabase = get_supabase_client()
    upload_res = (
        supabase.table("disaster_uploads")
        .select("*")
        .eq("id", upload_id)
        .single()
        .execute()
    )
    if not upload_res.data:
        raise HTTPException(status_code=404, detail="업로드 정보가 없습니다.")
    return upload_res.data


@router.get("/incidents")
def get_incidents(
    upload_id: str = None,
    status: str = None,
    incident_type: str = None,
    emd: str = None,
):
    supabase = get_supabase_client()
    query = supabase.table("disaster_incidents").select("*").order("incident_time")

    if upload_id:
        query = query.eq("upload_id", upload_id)
    if status:
        query = query.eq("status", status)
    if incident_type:
        query = query.eq("incident_type", incident_type)
    if emd:
        query = query.eq("emd", emd)

    res = query.execute()
    return {"items": res.data or []}


@router.get("/incidents/{incident_id}")
def get_incident_detail(incident_id: str):
    supabase = get_supabase_client()
    incident_res = (
        supabase.table("disaster_incidents")
        .select("*")
        .eq("id", incident_id)
        .single()
        .execute()
    )
    incident = incident_res.data

    if not incident:
        raise HTTPException(status_code=404, detail="사건이 없습니다.")

    links_res = (
        supabase.table("disaster_incident_messages")
        .select("raw_message_id, relation_type")
        .eq("incident_id", incident_id)
        .execute()
    )
    links = links_res.data or []
    raw_ids = [l["raw_message_id"] for l in links]

    messages = []
    if raw_ids:
        messages_res = (
            supabase.table("disaster_raw_messages")
            .select("*")
            .in_("id", raw_ids)
            .order("message_time")
            .execute()
        )
        messages = messages_res.data or []

    return {
        "incident": incident,
        "messages": messages,
    }


@router.get("/dashboard/overview")
def get_dashboard_overview(upload_id: str):
    supabase = get_supabase_client()
    res = (
        supabase.table("disaster_incidents")
        .select(
            "id, incident_type, status, emd, incident_time, "
            "location_raw, summary, photo_count, message_count, last_update_time"
        )
        .eq("upload_id", upload_id)
        .order("incident_time")
        .execute()
    )
    rows = res.data or []

    type_counter = Counter(r["incident_type"] for r in rows if r.get("incident_type"))
    status_counter = Counter(r["status"] for r in rows if r.get("status"))
    emd_counter = Counter((r.get("emd") or "미분류") for r in rows)

    # 진행 중 / 종료 구분
    active_statuses = {"reported", "in_progress", "monitoring"}
    done_statuses = {"completed", "closed", "no_issue"}
    active_count = sum(1 for r in rows if r.get("status") in active_statuses)
    done_count = sum(1 for r in rows if r.get("status") in done_statuses)

    # 사고 발생 읍면동 수 (미분류 제외)
    affected_emds = {r["emd"] for r in rows if r.get("emd") and r["emd"] != "미분류"}

    # 최다 사고 유형
    top_type = type_counter.most_common(1)[0][0] if type_counter else None
    top_type_label = INCIDENT_TYPE_LABELS.get(top_type, top_type) if top_type else None

    # 시간대별 통계
    hour_counter = Counter()
    for r in rows:
        if r.get("incident_time"):
            try:
                dt = datetime.fromisoformat(r["incident_time"].replace("Z", "+00:00"))
                hour_counter[dt.hour] += 1
            except (ValueError, TypeError):
                continue

    # 최근 사고 목록 (최대 10건, 최신 순)
    recent_incidents = sorted(
        rows, key=lambda r: r.get("last_update_time") or r.get("incident_time") or "", reverse=True
    )[:10]
    recent_list = [
        {
            "id": r["id"],
            "incident_type": r.get("incident_type"),
            "incident_type_label": INCIDENT_TYPE_LABELS.get(r.get("incident_type"), r.get("incident_type")),
            "status": r.get("status"),
            "status_label": STATUS_LABELS.get(r.get("status"), r.get("status")),
            "emd": r.get("emd"),
            "location_raw": r.get("location_raw"),
            "summary": (r.get("summary") or "")[:80],
            "incident_time": r.get("incident_time"),
            "last_update_time": r.get("last_update_time"),
            "photo_count": r.get("photo_count", 0),
            "message_count": r.get("message_count", 0),
        }
        for r in recent_incidents
    ]

    # 지도용 읍면동 데이터 (좌표 포함)
    emd_map_data = []
    for emd, count in sorted(emd_counter.items(), key=lambda x: -x[1]):
        coord = EMD_COORDS.get(emd, {})
        emd_rows = [r for r in rows if (r.get("emd") or "미분류") == emd]
        active_in_emd = sum(1 for r in emd_rows if r.get("status") in active_statuses)
        emd_map_data.append({
            "emd": emd,
            "count": count,
            "active_count": active_in_emd,
            "lat": coord.get("lat"),
            "lng": coord.get("lng"),
            "has_coords": bool(coord),
        })

    # 유형별 라벨 포함 통계
    by_type_labeled = {
        INCIDENT_TYPE_LABELS.get(k, k): v
        for k, v in type_counter.items()
    }
    by_status_labeled = {
        STATUS_LABELS.get(k, k): v
        for k, v in status_counter.items()
    }

    return {
        "total": len(rows),
        "active_count": active_count,
        "done_count": done_count,
        "affected_emd_count": len(affected_emds),
        "top_type": top_type,
        "top_type_label": top_type_label,
        "by_type": dict(type_counter),
        "by_type_labeled": by_type_labeled,
        "by_status": dict(status_counter),
        "by_status_labeled": by_status_labeled,
        "by_emd": dict(emd_counter),
        "by_hour": dict(sorted(hour_counter.items())),
        "recent_incidents": recent_list,
        "emd_map_data": emd_map_data,
    }


@router.post("/reports/daily/generate")
async def create_daily_report(payload: dict):
    supabase = get_supabase_client()
    upload_id = payload.get("upload_id")
    report_date = payload.get("report_date")
    created_by = payload.get("created_by", "system")

    if not upload_id or not report_date:
        raise HTTPException(status_code=400, detail="upload_id와 report_date는 필수입니다.")

    incidents_res = (
        supabase.table("disaster_incidents")
        .select("*")
        .eq("upload_id", upload_id)
        .execute()
    )
    incidents = incidents_res.data or []

    report = await generate_daily_report(report_date, incidents)

    insert_res = supabase.table("disaster_daily_reports").insert(
        {
            "report_date": report_date,
            "upload_id": upload_id,
            "title": report["title"],
            "summary_text": report["summary_text"],
            "report_text": report["report_text"],
            "total_incident_count": report["total_incident_count"],
            "completed_count": report["completed_count"],
            "in_progress_count": report["in_progress_count"],
            "created_by": created_by,
        }
    ).execute()

    logger.info(
        "daily report created: upload_id=%s, date=%s, incidents=%d",
        upload_id, report_date, len(incidents),
    )

    return {
        "success": True,
        "report": insert_res.data[0],
    }


@router.get("/reports")
def get_reports(upload_id: str = None):
    supabase = get_supabase_client()
    query = (
        supabase.table("disaster_daily_reports").select("*").order("created_at", desc=True)
    )
    if upload_id:
        query = query.eq("upload_id", upload_id)
    res = query.execute()
    return {"items": res.data or []}