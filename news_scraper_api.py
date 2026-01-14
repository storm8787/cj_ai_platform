"""
네이버 뉴스 스크랩 스크립트 (네이버 API 버전)
키워드: 충주시
최신 30개 뉴스 수집 (OpenAI 임베딩 기반 중복 제거)
"""

import requests
import json
from datetime import datetime, timedelta
import time
import os
import re
import numpy as np
from openai import OpenAI

# ============================================
# OpenAI 임베딩 기반 중복 제거
# ============================================

def get_embeddings(texts, client):
    """
    OpenAI 임베딩 API로 텍스트 벡터화
    
    Parameters:
    -----------
    texts : list
        임베딩할 텍스트 리스트
    client : OpenAI
        OpenAI 클라이언트
    
    Returns:
    --------
    tuple : (embeddings 리스트, response 객체)
    """
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )
    
    embeddings = [item.embedding for item in response.data]
    return embeddings, response

def cosine_similarity(vec1, vec2):
    """코사인 유사도 계산"""
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def remove_duplicates_with_embedding(news_list, threshold=0.85):
    """
    OpenAI 임베딩을 사용한 중복 뉴스 제거
    
    Parameters:
    -----------
    news_list : list
        뉴스 데이터 리스트
    threshold : float
        유사도 임계값 (기본값: 0.85, 85% 이상 유사하면 중복)
    
    Returns:
    --------
    list : 중복 제거된 뉴스 리스트
    """
    if not news_list:
        return []
    
    # OpenAI API 키 확인
    api_key = os.getenv('OPENAI_API_KEY', '')
    if not api_key:
        print("⚠️ OPENAI_API_KEY가 없어서 기본 중복 제거 사용")
        return remove_duplicates_simple(news_list)
    
    try:
        client = OpenAI(api_key=api_key)
        
        # 모든 제목 추출
        titles = [news['title'] for news in news_list]
        
        print(f"🔍 {len(titles)}개 뉴스 제목 임베딩 중...")
        
        # 임베딩 생성
        embeddings, response = get_embeddings(titles, client)
        
        # API 사용량 로깅
        try:
            from openai_usage_logger import log_openai_usage
            log_openai_usage(response, model="text-embedding-3-small", request_type="news_embedding")
            print("📊 임베딩 사용량 로깅 완료")
        except Exception as log_error:
            print(f"⚠️ 사용량 로깅 실패 (기능은 정상): {log_error}")
        
        # 중복 제거
        unique_news = []
        unique_embeddings = []
        
        for i, news in enumerate(news_list):
            is_duplicate = False
            
            # 기존 뉴스들과 유사도 비교
            for j, existing_emb in enumerate(unique_embeddings):
                similarity = cosine_similarity(embeddings[i], existing_emb)
                if similarity >= threshold:
                    print(f"⏭️ 중복 제거 (유사도 {similarity:.2f}): {news['title'][:30]}...")
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_news.append(news)
                unique_embeddings.append(embeddings[i])
        
        print(f"✅ 중복 제거 완료: {len(news_list)}개 → {len(unique_news)}개")
        return unique_news
    
    except Exception as e:
        print(f"❌ 임베딩 중복 제거 실패: {e}")
        print("⚠️ 기본 중복 제거로 대체합니다.")
        return remove_duplicates_simple(news_list)

def remove_duplicates_simple(news_list, threshold=0.7):
    """
    간단한 문자열 유사도 기반 중복 제거 (폴백용)
    """
    from difflib import SequenceMatcher
    
    unique_news = []
    seen_titles = []
    
    for news in news_list:
        is_duplicate = False
        for seen_title in seen_titles:
            similarity = SequenceMatcher(None, news['title'], seen_title).ratio()
            if similarity >= threshold:
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_news.append(news)
            seen_titles.append(news['title'])
    
    return unique_news

# ============================================
# 뉴스 스크래핑
# ============================================

def scrape_naver_news(keyword="충주시", max_results=30):
    """
    네이버 검색 API로 뉴스 수집
    
    Parameters:
    -----------
    keyword : str
        검색 키워드 (기본값: 충주시)
    max_results : int
        수집할 최대 뉴스 개수 (기본값: 30)
    
    Returns:
    --------
    list : 뉴스 데이터 리스트
    """
    
    # 환경 변수에서 API 인증 정보 가져오기
    client_id = os.getenv('NAVER_CLIENT_ID', '')
    client_secret = os.getenv('NAVER_CLIENT_SECRET', '')
    
    if not client_id or not client_secret:
        print("❌ 네이버 API 인증 정보가 없습니다.")
        print("NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET 환경 변수를 설정해주세요.")
        return []
    
    news_list = []
    
    # 네이버 검색 API URL
    url = "https://openapi.naver.com/v1/search/news.json"
    
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }
    
    print(f"🔍 '{keyword}' 뉴스 검색 시작...")
    
    try:
        # API는 한 번에 최대 100개까지 가능
        # 중복 제거 고려해서 2배 요청
        display = min(100, max_results * 2)
        
        params = {
            "query": keyword,
            "display": display,
            "start": 1,
            "sort": "date"  # 최신순
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        items = data.get('items', [])
        
        print(f"📥 API에서 {len(items)}개 뉴스 받음")
        
        for idx, item in enumerate(items):
            try:
                # HTML 태그 제거
                title = remove_html_tags(item.get('title', ''))
                description = remove_html_tags(item.get('description', ''))
                
                # 날짜 형식 변환
                pub_date = item.get('pubDate', '')
                formatted_date = format_date(pub_date)
                
                news_data = {
                    'id': idx + 1,
                    'title': title,
                    'link': item.get('originallink', item.get('link', '')),
                    'press': extract_press_name(item.get('link', '')),
                    'date': formatted_date,
                    'summary': description[:150] + "..." if len(description) > 150 else description,
                    'content': description,
                    'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                news_list.append(news_data)
                
            except Exception as e:
                print(f"❌ 뉴스 항목 처리 실패: {e}")
                continue
        
        print(f"📰 {len(news_list)}개 뉴스 수집됨, 중복 제거 시작...")
        
        # OpenAI 임베딩 기반 중복 제거
        unique_news = remove_duplicates_with_embedding(news_list, threshold=0.85)
        
        # max_results 개수로 제한
        unique_news = unique_news[:max_results]
        
        # ID 재정렬
        for i, news in enumerate(unique_news):
            news['id'] = i + 1
        
        print(f"\n✅ 최종 {len(unique_news)}개 뉴스 수집 완료!")
        return unique_news
    
    except requests.exceptions.RequestException as e:
        print(f"❌ API 요청 실패: {e}")
        return []
    except Exception as e:
        print(f"❌ 뉴스 수집 실패: {e}")
        return []

def remove_html_tags(text):
    """HTML 태그 제거 및 엔티티 디코딩"""
    import html as html_module
    # 1. HTML 태그 제거
    clean = re.compile('<.*?>')
    text = re.sub(clean, '', text)
    # 2. HTML 엔티티 디코딩 (&quot; → ", &amp; → &)
    text = html_module.unescape(text)
    return text

def extract_press_name(link):
    """
    URL에서 언론사 이름 추출
    """
    if 'n.news.naver.com' in link:
        parts = link.split('/')
        if len(parts) > 5:
            return parts[5]
    
    from urllib.parse import urlparse
    domain = urlparse(link).netloc
    
    press_mapping = {
        'chosun.com': '조선일보',
        'donga.com': '동아일보',
        'joongang.co.kr': '중앙일보',
        'joins.com': '중앙일보',
        'hani.co.kr': '한겨레',
        'khan.co.kr': '경향신문',
        'hankyung.com': '한국경제',
        'mk.co.kr': '매일경제',
        'yonhapnews.co.kr': '연합뉴스',
        'yna.co.kr': '연합뉴스',
        'kbs.co.kr': 'KBS',
        'sbs.co.kr': 'SBS',
        'mbc.co.kr': 'MBC',
        'jtbc.co.kr': 'JTBC',
        'news1.kr': '뉴스1',
        'newsis.com': '뉴시스',
        'edaily.co.kr': '이데일리',
        'mt.co.kr': '머니투데이',
        'inews24.com': '아이뉴스24',
        'zdnet.co.kr': 'ZDNet',
        'asiae.co.kr': '아시아경제',
        'sedaily.com': '서울경제',
        'fnnews.com': '파이낸셜뉴스',
        'etnews.com': '전자신문',
        'cjilbo.com': '충북일보',
        'cbinews.co.kr': '충북인뉴스',
        'ggilbo.com': '금강일보',
        'dynews.co.kr': '대전일보',
        'daejonilbo.com': '대전일보',
        'cctoday.co.kr': '충청투데이',
        'cctimes.kr': '충청타임즈',
        'chungnamilbo.com': '충남일보',
        'joongdo.co.kr': '중도일보',
        'jamill.kr' : '중앙매일',
        'dailycc.net' : '충청신문',
        'dynews.co.kr' : '동양일보',
        'jbnews.com' : '중부매일',        
    }
    
    for key, value in press_mapping.items():
        if key in domain:
            return value
    
    return domain.replace('www.', '').split('.')[0]

def format_date(pub_date):
    """
    네이버 API 날짜 형식 변환
    """
    try:
        dt = datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %z')
        return dt.strftime('%Y-%m-%d %H:%M')
    except:
        return pub_date

# ============================================
# 저장 함수
# ============================================

def save_to_json(news_list, filepath='data/news_data.json'):
    """
    뉴스 데이터를 JSON 파일로 저장 (로컬 테스트용)
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    kst_time = datetime.now() + timedelta(hours=9)
    
    data = {
        'keyword': '충주시',
        'total_count': len(news_list),
        'last_updated': kst_time.strftime('%Y-%m-%d %H:%M:%S'),
        'news': news_list
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 {filepath}에 저장 완료!")
    
    return data

def save_to_gist(news_list):
    """
    뉴스 데이터를 GitHub Gist에 저장
    """
    gist_token = os.getenv('GIST_TOKEN', '')
    gist_id = os.getenv('GIST_ID', '')
    
    if not gist_token:
        print("⚠️ GIST_TOKEN이 없어서 Gist 저장을 건너뜁니다.")
        return None
    
    kst_time = datetime.now() + timedelta(hours=9)
    
    data = {
        'keyword': '충주시',
        'total_count': len(news_list),
        'last_updated': kst_time.strftime('%Y-%m-%d %H:%M:%S'),
        'news': news_list
    }
    
    headers = {
        'Authorization': f'token {gist_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    gist_data = {
        'description': '충주시 뉴스 데이터 (자동 업데이트)',
        'public': False,
        'files': {
            'news_data.json': {
                'content': json.dumps(data, ensure_ascii=False, indent=2)
            }
        }
    }
    
    try:
        if gist_id:
            url = f'https://api.github.com/gists/{gist_id}'
            response = requests.patch(url, headers=headers, json=gist_data)
        else:
            url = 'https://api.github.com/gists'
            response = requests.post(url, headers=headers, json=gist_data)
        
        response.raise_for_status()
        result = response.json()
        
        gist_id = result['id']
        raw_url = result['files']['news_data.json']['raw_url']
        
        print(f"\n☁️ Gist 저장 완료!")
        print(f"   Gist ID: {gist_id}")
        print(f"   Raw URL: {raw_url}")
        
        return raw_url
    
    except Exception as e:
        print(f"❌ Gist 저장 실패: {e}")
        return None

# ============================================
# 메인 실행
# ============================================

if __name__ == "__main__":
    # 뉴스 스크랩 실행
    news_data = scrape_naver_news(keyword="충주시", max_results=30)
    
    if news_data:
        # 로컬 JSON 파일로 저장 (테스트/백업용)
        save_to_json(news_data)
        
        # GitHub Gist에 저장 (GIST_TOKEN이 있는 경우)
        save_to_gist(news_data)
        
        # 결과 미리보기
        print("\n📰 수집된 뉴스 미리보기:")
        for news in news_data[:5]:
            print(f"\n제목: {news['title']}")
            print(f"언론사: {news['press']}")
            print(f"날짜: {news['date']}")
            print(f"링크: {news['link'][:50]}...")
    else:
        print("❌ 수집된 뉴스가 없습니다.")