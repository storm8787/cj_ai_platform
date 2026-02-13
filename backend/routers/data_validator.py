"""
공공데이터 제공표준 검증기 API
CSV/Excel 파일을 공공데이터 표준과 비교 검증
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import json
import pandas as pd
import io
import re
from pathlib import Path

router = APIRouter()

# ===========================================
# 📋 표준 데이터 로드
# ===========================================
STANDARDS_FILE = Path(__file__).parent.parent / "data" / "public_data_standards.json"
STANDARDS_DATA = []

def load_standards():
    """표준 데이터 로드"""
    global STANDARDS_DATA
    try:
        if STANDARDS_FILE.exists():
            with open(STANDARDS_FILE, 'r', encoding='utf-8') as f:
                STANDARDS_DATA = json.load(f)
            print(f"✅ 공공데이터 표준 {len(STANDARDS_DATA)}개 로드 완료")
        else:
            print(f"⚠️ 표준 데이터 파일 없음: {STANDARDS_FILE}")
    except Exception as e:
        print(f"❌ 표준 데이터 로드 실패: {e}")

# 서버 시작 시 로드
load_standards()


# ===========================================
# 📋 요청/응답 모델
# ===========================================
class StandardField(BaseModel):
    no: str
    field_name: str
    required: str
    description: str
    allowed_values: Optional[str] = ""
    format: Optional[str] = ""
    example: Optional[str] = ""


class StandardInfo(BaseModel):
    id: int
    name: str
    full_name: Optional[str] = ""
    provision_scope: Optional[str] = ""
    managing_org: Optional[str] = ""
    provision_org: Optional[str] = ""
    update_cycle: Optional[str] = ""
    field_count: int


class ValidationError(BaseModel):
    type: str  # 'error', 'warning', 'info'
    field: str
    row: Optional[int] = None
    msg: str
    detail: Optional[str] = ""


class ValidationResult(BaseModel):
    score: int
    total_rows: int
    checked_rows: int
    matched_fields: int
    total_fields: int
    errors: List[ValidationError]
    warnings: List[ValidationError]
    info: List[ValidationError]
    total_errors: int
    total_warnings: int


# ===========================================
# 🔧 검증 로직
# ===========================================
def levenshtein_distance(s1: str, s2: str) -> int:
    """레벤슈타인 거리 계산"""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def find_similar_field(target: str, candidates: List[str]) -> Optional[str]:
    """유사한 필드명 찾기"""
    t = target.replace(" ", "").replace("_", "")
    for c in candidates:
        cn = c.replace(" ", "").replace("_", "")
        if cn == t:
            return None
        if cn in t or t in cn:
            return c
        if levenshtein_distance(cn, t) <= 2:
            return c
    return None


def validate_data(df: pd.DataFrame, standard: dict, filename: str = "") -> ValidationResult:
    """데이터 검증 수행"""
    errors = []
    warnings = []
    info = []
    
    fields = standard.get('fields', [])
    headers = list(df.columns)
    header_set = set(headers)
    
    # 필드 정보 매핑
    field_map = {}
    for f in fields:
        field_map[f['field_name']] = {
            'required': f.get('required', '') == '필수',
            'allowed': f.get('allowed_values', ''),
            'format': f.get('format', ''),
            'example': f.get('example', ''),
            'description': f.get('description', '')
        }
    
    standard_field_names = list(field_map.keys())
    
    # ========== 0. 파일명 날짜 vs 데이터기준일자 검증 ==========
    filename_date = None
    if filename:
        # 파일명에서 날짜 추출: 충청북도_충주시_공연행사정보_YYYYMMDD.csv
        date_match = re.search(r'_(\d{8})\.', filename)
        if date_match:
            filename_date = date_match.group(1)  # YYYYMMDD
    
    # ========== 1. 중복 행 검사 ==========
    duplicate_rows = df.duplicated(keep=False)
    duplicate_count = duplicate_rows.sum()
    if duplicate_count > 0:
        # 중복된 행 번호 찾기 (첫 번째 발견된 것들만)
        dup_indices = df[df.duplicated(keep='first')].index.tolist()[:10]
        errors.append(ValidationError(
            type='error',
            field='전체',
            msg=f'중복 행 발견 ({duplicate_count}개)',
            detail=f'중복된 행: {", ".join([str(i+2) for i in dup_indices])}{"..." if len(dup_indices) >= 10 else ""}'
        ))
    
    # ========== 2. 헤더 검증 ==========
    required_fields = [f['field_name'] for f in fields if f.get('required') == '필수']
    missing_required = 0
    
    for rf in required_fields:
        if rf not in header_set:
            similar = find_similar_field(rf, headers)
            if similar:
                errors.append(ValidationError(
                    type='error',
                    field=rf,
                    msg='필수 항목 누락 (유사 항목 발견)',
                    detail=f'"{rf}" 항목이 없습니다. "{similar}"을(를) 의미하셨나요?'
                ))
            else:
                errors.append(ValidationError(
                    type='error',
                    field=rf,
                    msg='필수 항목 누락',
                    detail=f'필수 항목 "{rf}"이(가) 데이터에 없습니다.'
                ))
            missing_required += 1
    
    # 추가 필드 (표준에 없는 것) 정보
    for h in headers:
        if h not in standard_field_names:
            similar = find_similar_field(h, standard_field_names)
            if similar:
                info.append(ValidationError(
                    type='info',
                    field=h,
                    msg='표준에 없는 항목 (유사 항목 존재)',
                    detail=f'"{h}"은(는) 표준에 없습니다. "{similar}"을(를) 의미하셨나요?'
                ))
            else:
                info.append(ValidationError(
                    type='info',
                    field=h,
                    msg='표준에 없는 추가 항목',
                    detail=f'"{h}"은(는) 표준 항목에 포함되지 않은 추가 항목입니다.'
                ))
    
    # ========== 3. 조건부 필수 필드 파악 ==========
    # 설명에서 조건부 필수 패턴 찾기
    conditional_required = {}  # {필드명: {조건필드: [조건값들]}}
    
    for field_name, field_info in field_map.items():
        desc = field_info['description']
        
        # 패턴1: "도로종류가 '고속국도', '일반국도'인 경우 필수"
        match = re.search(r'([가-힣]+)(?:가|이)\s+(.+?)\s*인\s*경우', desc)
        if match and '필수' in desc:
            cond_field = match.group(1)
            values_part = match.group(2)
            cond_values = re.findall(r"'([^']+)'", values_part)
            
            if cond_values:
                conditional_required[field_name] = {
                    'condition_field': cond_field,
                    'condition_values': cond_values
                }
                continue
        
        # 패턴2: "인증(지정)여부가 예비인 경우 필수"
        match2 = re.search(r'([가-힣\(\)]+)(?:가|이)\s+([가-힣]+)인\s*경우\s*필수', desc)
        if match2:
            cond_field = match2.group(1)
            cond_value = match2.group(2)
            conditional_required[field_name] = {
                'condition_field': cond_field,
                'condition_values': [cond_value]
            }
            continue
        
        # 패턴3: "환승역인 경우 필수", "부처형일 경우 필수"
        match3 = re.search(r'([가-힣]+)(?:인|일)\s*경우\s*필수', desc)
        if match3:
            cond_value = match3.group(1)
            # 조건값만 있고 조건필드는 해당 필드의 연관 필드에서 찾아야 함
            # 환승역 → 환승여부, 부처형 → 부처형여부 등
            potential_cond_field = cond_value.replace('역', '여부').replace('형', '형여부')
            conditional_required[field_name] = {
                'condition_field': potential_cond_field,
                'condition_values': [cond_value, 'Y', 'O', '예']  # 다양한 긍정값
            }
            continue
        
        # 패턴4: "개찰결과구분명이 '개찰완료'일 경우 필수"
        match4 = re.search(r'([가-힣]+)(?:이|가)\s*["\']?([가-힣]+)["\']?(?:일|인)\s*경우\s*필수', desc)
        if match4:
            cond_field = match4.group(1)
            cond_value = match4.group(2)
            conditional_required[field_name] = {
                'condition_field': cond_field,
                'condition_values': [cond_value]
            }
    
    # 주소 필드명 찾기
    road_addr_col = None
    jibun_addr_col = None
    for col in headers:
        if '도로명' in col and '주소' in col:
            road_addr_col = col
        if '지번' in col and '주소' in col:
            jibun_addr_col = col
    
    # ========== 4. 데이터 검증 (최대 1000행) ==========
    max_rows = min(len(df), 1000)
    cell_errors = 0
    cell_warnings = 0
    
    for idx in range(max_rows):
        row = df.iloc[idx]
        
        # ========== 데이터기준일자 vs 파일명 날짜 검증 ==========
        if filename_date and '데이터기준일자' in header_set:
            data_date_val = str(row.get('데이터기준일자', '')).strip()
            if data_date_val and data_date_val.lower() not in ['nan', 'null', 'none', 'nat']:
                # YYYY-MM-DD -> YYYYMMDD 변환
                data_date_clean = data_date_val.replace('-', '')[:8]
                if data_date_clean != filename_date:
                    if cell_errors < 200:
                        errors.append(ValidationError(
                            type='error',
                            field='데이터기준일자',
                            row=idx + 2,
                            msg='파일명 날짜와 불일치',
                            detail=f'{idx + 2}행: 데이터기준일자({data_date_val})와 파일명 날짜({filename_date[:4]}-{filename_date[4:6]}-{filename_date[6:]})가 다릅니다.'
                        ))
                    cell_errors += 1
        
        # 주소 조건부 필수 검증: 도로명 없으면 지번 필수
        if road_addr_col and jibun_addr_col:
            road_val = str(row.get(road_addr_col, '')).strip()
            jibun_val = str(row.get(jibun_addr_col, '')).strip()
            road_empty = not road_val or road_val.lower() in ['nan', 'null', 'none', 'nat']
            jibun_empty = not jibun_val or jibun_val.lower() in ['nan', 'null', 'none', 'nat']
            
            if road_empty and jibun_empty:
                if cell_errors < 200:
                    errors.append(ValidationError(
                        type='error',
                        field='주소',
                        row=idx + 2,
                        msg='도로명주소와 지번주소 모두 비어있음',
                        detail=f'{idx + 2}행: 도로명주소 또는 지번주소 중 하나는 필수입니다.'
                    ))
                cell_errors += 1
            elif road_empty and not jibun_empty:
                # 도로명 없고 지번만 있으면 OK (단, 지번주소가 선택 필드여도 허용)
                pass
        
        # 모든 필드에 대해 공통 검증 (표준 필드 + 추가 필드)
        for col in headers:
            val = str(row.get(col, '')).strip()
            
            # 빈 값이면 공통 검증 스킵
            if not val or val.lower() in ['nan', 'null', 'none', 'nat']:
                # 필수 필드인 경우 에러 (단, 도로명/지번 주소는 별도 처리됨)
                if col in field_map and field_map[col]['required']:
                    # 도로명주소가 비어있어도 지번주소가 있으면 OK
                    if '도로명' in col and '주소' in col:
                        if jibun_addr_col:
                            jibun_val = str(row.get(jibun_addr_col, '')).strip()
                            if jibun_val and jibun_val.lower() not in ['nan', 'null', 'none', 'nat']:
                                continue  # 지번주소가 있으니 스킵
                    
                    # 조건부 필수 체크
                    if col in conditional_required:
                        cond_info = conditional_required[col]
                        cond_field = cond_info['condition_field']
                        cond_values = cond_info['condition_values']
                        
                        # 조건 필드 찾기
                        cond_col = None
                        for h in headers:
                            if cond_field in h:
                                cond_col = h
                                break
                        
                        if cond_col:
                            cond_val = str(row.get(cond_col, '')).strip()
                            # 조건값에 해당하지 않으면 필수 아님
                            if cond_val not in cond_values:
                                continue  # 조건 불충족이므로 필수 아님
                    
                    if cell_errors < 200:
                        errors.append(ValidationError(
                            type='error',
                            field=col,
                            row=idx + 2,
                            msg='필수 항목 값 비어있음',
                            detail=f'{idx + 2}행의 "{col}" 값이 비어있습니다.'
                        ))
                    cell_errors += 1
                continue
            
            # ========== 공통 검증 (모든 데이터에 적용) ==========
            
            # 3-1. 줄바꿈 검사
            if '\n' in val or '\r' in val:
                if cell_errors < 200:
                    errors.append(ValidationError(
                        type='error',
                        field=col,
                        row=idx + 2,
                        msg='줄바꿈 문자 포함',
                        detail=f'{idx + 2}행: 필드 내 줄바꿈이 포함되어 있습니다.'
                    ))
                cell_errors += 1
            
            # 3-2. 특수문자 검사 (?, !, @ 등 - 일부 허용 제외)
            # 허용: +, -, _, ., :, /, (, ), 공백, 한글, 영문, 숫자
            invalid_chars = re.findall(r'[?!@#$%^&*=\[\]{}|\\<>~`]', val)
            if invalid_chars:
                if cell_warnings < 200:
                    warnings.append(ValidationError(
                        type='warning',
                        field=col,
                        row=idx + 2,
                        msg='부적절한 특수문자 포함',
                        detail=f'{idx + 2}행: "{val}" (특수문자: {", ".join(set(invalid_chars))})'
                    ))
                cell_warnings += 1
            
            # 3-3. 도로명주소 형식 검사
            if '도로명' in col and '주소' in col:
                # 도로명주소 패턴: ~시/도 ~시/군/구 (~읍/면) ~로/길 숫자
                if not re.search(r'(시|도)\s+\S+(시|군|구)', val):
                    if cell_warnings < 200:
                        warnings.append(ValidationError(
                            type='warning',
                            field=col,
                            row=idx + 2,
                            msg='도로명주소 형식 불일치',
                            detail=f'{idx + 2}행: "{val}" (형식: OO시/도 OO시/군/구 OO로/길 번호)'
                        ))
                    cell_warnings += 1
                elif not re.search(r'(로|길)\s*\d+', val):
                    if cell_warnings < 200:
                        warnings.append(ValidationError(
                            type='warning',
                            field=col,
                            row=idx + 2,
                            msg='도로명주소에 도로명(로/길) 누락',
                            detail=f'{idx + 2}행: "{val}" (도로명과 번호 필요)'
                        ))
                    cell_warnings += 1
            
            # 3-4. 지번주소 형식 검사
            if '지번' in col and '주소' in col:
                # 지번주소 패턴: ~시/도 ~시/군/구 ~동/읍/면/리 번지
                if not re.search(r'(시|도)\s+\S+(시|군|구)', val):
                    if cell_warnings < 200:
                        warnings.append(ValidationError(
                            type='warning',
                            field=col,
                            row=idx + 2,
                            msg='지번주소 형식 불일치',
                            detail=f'{idx + 2}행: "{val}" (형식: OO시/도 OO시/군/구 OO동/읍/면 번지)'
                        ))
                    cell_warnings += 1
                # 지번주소인데 도로명(로/길) 형식으로 입력한 경우
                elif re.search(r'(로|길)\s*\d+', val) and not re.search(r'(동|읍|면|리)\s*\d+', val):
                    if cell_errors < 200:
                        errors.append(ValidationError(
                            type='error',
                            field=col,
                            row=idx + 2,
                            msg='지번주소에 도로명주소 형식 입력',
                            detail=f'{idx + 2}행: "{val}" (지번주소는 동/읍/면/리 + 번지 형식이어야 합니다)'
                        ))
                    cell_errors += 1
            
            # ========== 표준 필드 검증 ==========
            if col not in field_map:
                continue
                
            field_info = field_map[col]
            fmt = field_info['format']
            example = field_info['example']
            
            # 허용값 체크
            if field_info['allowed']:
                allowed_list = [v.strip() for v in field_info['allowed'].split('/') if v.strip()]
                if allowed_list and len(allowed_list) < 30:
                    val_norm = val.strip()
                    
                    # 엄격 매칭: 정확히 일치하는지 체크
                    exact_match = val_norm in allowed_list
                    
                    # 복수값 처리 (+로 구분된 경우)
                    if not exact_match and '+' in val_norm:
                        val_parts = [v.strip() for v in val_norm.split('+')]
                        exact_match = all(part in allowed_list for part in val_parts)
                    
                    if not exact_match:
                        # 유사 매칭 시도 (공백 제거)
                        loose_match = any(
                            val_norm.replace(' ', '') == a.replace(' ', '')
                            for a in allowed_list
                        )
                        
                        if not loose_match:
                            # 숫자 앞 0 문제 체크 (01 vs 1)
                            potential_match = None
                            for a in allowed_list:
                                # 허용값이 01, 02 형태이고 입력값이 1, 2 형태인 경우
                                if a.isdigit() and val_norm.isdigit():
                                    if int(a) == int(val_norm) and a != val_norm:
                                        potential_match = a
                                        break
                            
                            if potential_match:
                                if cell_errors < 200:
                                    errors.append(ValidationError(
                                        type='error',
                                        field=col,
                                        row=idx + 2,
                                        msg='허용값 형식 불일치',
                                        detail=f'{idx + 2}행: "{val}" → "{potential_match}"(으)로 수정 필요'
                                    ))
                                cell_errors += 1
                            else:
                                if cell_warnings < 200:
                                    warnings.append(ValidationError(
                                        type='warning',
                                        field=col,
                                        row=idx + 2,
                                        msg='허용값과 불일치',
                                        detail=f'{idx + 2}행: "{val}" (허용: {", ".join(allowed_list[:5])}{"..." if len(allowed_list) > 5 else ""})'
                                    ))
                                cell_warnings += 1
            
            # 형식 체크
            if fmt:
                # 날짜 형식 YYYY-MM-DD (전체 날짜)
                if 'YYYY-MM-DD' in fmt:
                    if not re.match(r'^\d{4}-\d{2}-\d{2}', val):
                        if cell_warnings < 200:
                            warnings.append(ValidationError(
                                type='warning',
                                field=col,
                                row=idx + 2,
                                msg='날짜 형식 불일치',
                                detail=f'{idx + 2}행: "{val}" (형식: YYYY-MM-DD)'
                            ))
                        cell_warnings += 1
                
                # 날짜 형식 YYYY-MM (년월만)
                elif 'YYYY-MM' in fmt and 'DD' not in fmt:
                    if not re.match(r'^\d{4}-\d{2}$', val):
                        if cell_warnings < 200:
                            warnings.append(ValidationError(
                                type='warning',
                                field=col,
                                row=idx + 2,
                                msg='년월 형식 불일치',
                                detail=f'{idx + 2}행: "{val}" (형식: YYYY-MM)'
                            ))
                        cell_warnings += 1
                
                # 시간 형식 HH24:MI
                if 'HH24:MI' in fmt or 'HH:MM' in fmt:
                    if not re.match(r'^\d{1,2}:\d{2}$', val):
                        if cell_warnings < 200:
                            warnings.append(ValidationError(
                                type='warning',
                                field=col,
                                row=idx + 2,
                                msg='시간 형식 불일치',
                                detail=f'{idx + 2}행: "{val}" (형식: HH:MM)'
                            ))
                        cell_warnings += 1
                
                # Y/N 체크
                if 'Y:' in fmt and 'N:' in fmt:
                    if val.upper() not in ['Y', 'N']:
                        if cell_warnings < 200:
                            warnings.append(ValidationError(
                                type='warning',
                                field=col,
                                row=idx + 2,
                                msg='Y/N 형식 불일치',
                                detail=f'{idx + 2}행: "{val}" (Y 또는 N만 허용)'
                            ))
                        cell_warnings += 1
                
                # 좌표 형식 (소수점)
                if '소수점' in fmt or ('위도' in col or '경도' in col):
                    try:
                        coord_val = float(val.replace(',', ''))
                        # 소수점 자릿수 체크 (6자리 이상 10자리 이하)
                        if '.' in val:
                            decimal_part = val.split('.')[1]
                            decimal_len = len(decimal_part)
                            if decimal_len < 6:
                                if cell_warnings < 200:
                                    warnings.append(ValidationError(
                                        type='warning',
                                        field=col,
                                        row=idx + 2,
                                        msg='좌표 소수점 자릿수 부족',
                                        detail=f'{idx + 2}행: "{val}" (소수점 6자리 이상 필요, 현재 {decimal_len}자리)'
                                    ))
                                cell_warnings += 1
                            elif decimal_len > 10:
                                if cell_warnings < 200:
                                    warnings.append(ValidationError(
                                        type='warning',
                                        field=col,
                                        row=idx + 2,
                                        msg='좌표 소수점 자릿수 초과',
                                        detail=f'{idx + 2}행: "{val}" (소수점 10자리 이하 필요, 현재 {decimal_len}자리)'
                                    ))
                                cell_warnings += 1
                        else:
                            # 소수점 없는 좌표
                            if cell_warnings < 200:
                                warnings.append(ValidationError(
                                    type='warning',
                                    field=col,
                                    row=idx + 2,
                                    msg='좌표에 소수점 없음',
                                    detail=f'{idx + 2}행: "{val}" (소수점 6자리 이상 필요)'
                                ))
                            cell_warnings += 1
                    except:
                        if cell_warnings < 200:
                            warnings.append(ValidationError(
                                type='warning',
                                field=col,
                                row=idx + 2,
                                msg='좌표 형식 불일치',
                                detail=f'{idx + 2}행: "{val}" (숫자 형식이어야 합니다)'
                            ))
                        cell_warnings += 1
                
                # 숫자 형식 (N/단위) - 객석수, 면적 등
                # 예: N/석, N/면, N/㎡, N/원, N/명
                unit_match = re.match(r'N/(.+)', fmt)
                if unit_match:
                    unit = unit_match.group(1)  # 석, 면, ㎡ 등
                    
                    # 천단위 콤마 검사
                    if ',' in val:
                        if cell_errors < 200:
                            errors.append(ValidationError(
                                type='error',
                                field=col,
                                row=idx + 2,
                                msg='숫자에 천단위 콤마 포함',
                                detail=f'{idx + 2}행: "{val}" (콤마 없이 숫자만 입력. 예: {example})'
                            ))
                        cell_errors += 1
                    
                    # 단위 문자 포함 검사 (숫자만 있어야 함)
                    val_clean = val.replace(',', '').replace(' ', '')
                    if not re.match(r'^-?\d+(\.\d+)?$', val_clean):
                        if cell_errors < 200:
                            errors.append(ValidationError(
                                type='error',
                                field=col,
                                row=idx + 2,
                                msg='숫자 형식 불일치',
                                detail=f'{idx + 2}행: "{val}" (숫자만 입력, 단위 제외. 예: {example})'
                            ))
                        cell_errors += 1
                
                # 전화번호 형식
                if 'NNN-NNNN-NNNN' in fmt or 'NNN-NNN-NNNN' in fmt or '전화' in col:
                    phone_clean = val.replace(' ', '').replace('-', '')
                    
                    # 휴대폰 번호 체크 (010, 011, 016, 017, 018, 019)
                    if re.match(r'^01[0-9]', phone_clean):
                        if cell_errors < 200:
                            errors.append(ValidationError(
                                type='error',
                                field=col,
                                row=idx + 2,
                                msg='휴대폰 번호 입력 (개인정보 위반)',
                                detail=f'{idx + 2}행: "{val}" (휴대폰 번호는 개인정보로 입력 불가)'
                            ))
                        cell_errors += 1
                    # 형식 체크: 00-000-0000, 000-0000-0000, 0000-0000-0000
                    elif not re.match(r'^(\d{2,4})-(\d{3,4})-(\d{4})$', val.replace(' ', '')):
                        if cell_warnings < 200:
                            warnings.append(ValidationError(
                                type='warning',
                                field=col,
                                row=idx + 2,
                                msg='전화번호 형식 불일치',
                                detail=f'{idx + 2}행: "{val}" (형식: 00-000-0000 또는 000-0000-0000)'
                            ))
                        cell_warnings += 1
    
    # 점수 계산
    matched_fields = len([f for f in standard_field_names if f in header_set])
    total_fields = len(fields)
    total_checks = len(required_fields) + (max_rows * matched_fields)
    pass_checks = total_checks - cell_errors - missing_required
    score = round((pass_checks / total_checks) * 100) if total_checks > 0 else 0
    score = max(0, min(100, score))
    
    return ValidationResult(
        score=score,
        total_rows=len(df),
        checked_rows=max_rows,
        matched_fields=matched_fields,
        total_fields=total_fields,
        errors=errors[:200],
        warnings=warnings[:200],
        info=info,
        total_errors=cell_errors + missing_required,
        total_warnings=cell_warnings
    )


# ===========================================
# 🌐 API 엔드포인트
# ===========================================
@router.get("/standards")
async def get_standards(search: Optional[str] = None):
    """표준 목록 조회"""
    if not STANDARDS_DATA:
        load_standards()
    
    result = []
    for s in STANDARDS_DATA:
        if search:
            if search.lower() not in s.get('name', '').lower():
                continue
        
        result.append({
            'id': s.get('id'),
            'name': s.get('name'),
            'full_name': s.get('full_name', ''),
            'managing_org': s.get('managing_org', ''),
            'field_count': len(s.get('fields', []))
        })
    
    return {'standards': result, 'total': len(result)}


@router.get("/standards/{standard_id}")
async def get_standard_detail(standard_id: int):
    """표준 상세 조회"""
    if not STANDARDS_DATA:
        load_standards()
    
    for s in STANDARDS_DATA:
        if s.get('id') == standard_id:
            return {
                'id': s.get('id'),
                'name': s.get('name'),
                'full_name': s.get('full_name', ''),
                'provision_scope': s.get('provision_scope', ''),
                'managing_org': s.get('managing_org', ''),
                'provision_org': s.get('provision_org', ''),
                'update_cycle': s.get('update_cycle', ''),
                'fields': s.get('fields', [])
            }
    
    raise HTTPException(status_code=404, detail="표준을 찾을 수 없습니다.")


@router.post("/validate/{standard_id}")
async def validate_file(
    standard_id: int,
    file: UploadFile = File(...)
):
    """파일 검증"""
    if not STANDARDS_DATA:
        load_standards()
    
    # 표준 찾기
    standard = None
    for s in STANDARDS_DATA:
        if s.get('id') == standard_id:
            standard = s
            break
    
    if not standard:
        raise HTTPException(status_code=404, detail="표준을 찾을 수 없습니다.")
    
    # 파일 읽기
    try:
        content = await file.read()
        filename = file.filename.lower()
        
        if filename.endswith('.csv'):
            # CSV 인코딩 시도
            for encoding in ['utf-8', 'cp949', 'euc-kr', 'utf-8-sig']:
                try:
                    df = pd.read_csv(io.BytesIO(content), encoding=encoding)
                    break
                except:
                    continue
            else:
                raise HTTPException(status_code=400, detail="CSV 파일을 읽을 수 없습니다.")
        
        elif filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(content))
        
        else:
            raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다. (CSV, XLSX, XLS만 지원)")
        
        if df.empty:
            raise HTTPException(status_code=400, detail="파일에 데이터가 없습니다.")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"파일 처리 오류: {str(e)}")
    
    # 검증 수행 (파일명 전달)
    result = validate_data(df, standard, file.filename)
    
    return {
        'standard_name': standard.get('name'),
        'file_name': file.filename,
        'result': result.dict()
    }


@router.get("/status")
async def get_status():
    """서비스 상태"""
    return {
        'status': 'active',
        'standards_loaded': len(STANDARDS_DATA),
        'service': '공공데이터 제공표준 검증기'
    }