from fastapi import APIRouter, File, HTTPException, UploadFile
from collections import Counter
from datetime import datetime

from services.supabase_service import get_supabase_client
from services.disaster_parser_service import (
    parse_kakao_txt,
    extract_emd,
    extract_location_raw,
    infer_incident_type,
    infer_status,
    extract_related_agency,
    normalize_summary,
)
from services.disaster_incident_service import build_incidents
from services.disaster_report_service import generate_daily_report

router = APIRouter()
#supabase = get_supabase_client()


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

    upload_res = supabase.table("disaster_uploads").insert(
        {
            "file_name": file.filename,
            "source_type": "kakao_txt",
            "analysis_status": "uploaded",
        }
    ).execute()

    upload_row = upload_res.data[0]
    upload_id = upload_row["id"]

    parsed_messages = parse_kakao_txt(content)

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
    supabase = get_supabase_client()
    msg_res = (
        supabase.table("disaster_raw_messages")
        .select("*")
        .eq("upload_id", upload_id)
        .order("message_time")
        .execute()
    )

    if not msg_res.data:
        raise HTTPException(status_code=404, detail="업로드된 메시지가 없습니다.")

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

    incidents = build_incidents(parsed_messages)

    # 기존 incident_messages 삭제
    existing_incidents_res = (
        supabase.table("disaster_incidents")
        .select("id")
        .eq("upload_id", upload_id)
        .execute()
    )
    existing_ids = [r["id"] for r in (existing_incidents_res.data or [])]
    if existing_ids:
        supabase.table("disaster_incident_messages").delete().in_("incident_id", existing_ids).execute()

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

    incident_insert_res = supabase.table("disaster_incidents").insert(incident_rows).execute()
    inserted_incidents = incident_insert_res.data or []

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

    supabase.table("disaster_uploads").update(
        {
            "incident_count": len(incidents),
            "analysis_status": "analyzed",
        }
    ).eq("id", upload_id).execute()

    return {
        "success": True,
        "upload_id": upload_id,
        "incident_count": len(incidents),
    }


@router.get("/upload/{upload_id}/summary")
def get_upload_summary(upload_id: str):
    supabase = get_supabase_client()
    upload_res = supabase.table("disaster_uploads").select("*").eq("id", upload_id).single().execute()
    if not upload_res.data:
        raise HTTPException(status_code=404, detail="업로드 정보가 없습니다.")
    return upload_res.data


@router.get("/incidents")
def get_incidents(upload_id: str = None, status: str = None, incident_type: str = None, emd: str = None):
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
    incident_res = supabase.table("disaster_incidents").select("*").eq("id", incident_id).single().execute()
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
        .select("id, incident_type, status, emd, incident_time")
        .eq("upload_id", upload_id)
        .execute()
    )
    rows = res.data or []

    type_counter = Counter(r["incident_type"] for r in rows if r.get("incident_type"))
    status_counter = Counter(r["status"] for r in rows if r.get("status"))
    emd_counter = Counter((r.get("emd") or "미분류") for r in rows)

    hour_counter = Counter()
    for r in rows:
        if r.get("incident_time"):
            dt = datetime.fromisoformat(r["incident_time"].replace("Z", "+00:00"))
            hour_counter[dt.hour] += 1

    return {
        "total": len(rows),
        "by_type": dict(type_counter),
        "by_status": dict(status_counter),
        "by_emd": dict(emd_counter),
        "by_hour": dict(sorted(hour_counter.items())),
    }


@router.post("/reports/daily/generate")
def create_daily_report(payload: dict):
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

    report = generate_daily_report(report_date, incidents)

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

    return {
        "success": True,
        "report": insert_res.data[0],
    }


@router.get("/reports")
def get_reports(upload_id: str = None):
    supabase = get_supabase_client()
    query = supabase.table("disaster_daily_reports").select("*").order("created_at", desc=True)
    if upload_id:
        query = query.eq("upload_id", upload_id)
    res = query.execute()
    return {"items": res.data or []}