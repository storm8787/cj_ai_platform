import { useState, useEffect } from 'react';
import { 
  Newspaper, RefreshCw, Sparkles, ExternalLink, 
  Loader2, Calendar, Building2, X, ChevronDown 
} from 'lucide-react';
import { newsApi } from '../services/api';

function NewsViewer() {
  const [newsData, setNewsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedNewsId, setSelectedNewsId] = useState(null);
  const [summaries, setSummaries] = useState({});
  const [summaryLoading, setSummaryLoading] = useState(null);
  const [error, setError] = useState('');

  // 뉴스 목록 로드
  useEffect(() => {
    loadNews();
  }, []);

  const loadNews = async () => {
    setLoading(true);
    setError('');
    
    try {
      const response = await newsApi.getList();
      setNewsData(response.data);
    } catch (err) {
      console.error('뉴스 로드 실패:', err);
      setError('뉴스를 불러오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // 뉴스 새로고침 (GitHub Actions 트리거)
  const handleRefresh = async () => {
    setRefreshing(true);
    setError('');
    
    try {
      const response = await newsApi.refresh();
      alert(response.data.message || '뉴스 업데이트가 시작되었습니다.');
      
      // 1분 후 자동 새로고침
      setTimeout(() => {
        loadNews();
      }, 60000);
      
    } catch (err) {
      const message = err.response?.data?.detail || '새로고침 요청에 실패했습니다.';
      setError(message);
    } finally {
      setRefreshing(false);
    }
  };

  // AI 요약 생성
  const handleSummarize = async (news) => {
    if (summaries[news.id]) return; // 이미 요약이 있으면 스킵
    
    setSummaryLoading(news.id);
    
    try {
      const response = await newsApi.summarize({
        title: news.title,
        content: news.content
      });
      
      setSummaries(prev => ({
        ...prev,
        [news.id]: response.data.summary
      }));
    } catch (err) {
      console.error('AI 요약 실패:', err);
      setSummaries(prev => ({
        ...prev,
        [news.id]: '⚠️ AI 요약 생성에 실패했습니다.'
      }));
    } finally {
      setSummaryLoading(null);
    }
  };

  // 카드 클릭 핸들러
  const handleCardClick = (newsId) => {
    setSelectedNewsId(selectedNewsId === newsId ? null : newsId);
  };

  // HTML 엔티티 디코딩
  const decodeHtml = (text) => {
    if (!text) return '';
    const doc = new DOMParser().parseFromString(text, 'text/html');
    return doc.documentElement.textContent;
  };

  // 로딩 상태
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 size={32} className="animate-spin text-primary-600" />
      </div>
    );
  }

  const newsList = newsData?.news || [];

  // 3개씩 행으로 그룹화
  const newsRows = [];
  for (let i = 0; i < newsList.length; i += 3) {
    newsRows.push(newsList.slice(i, i + 3));
  }

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* 헤더 */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <Newspaper className="text-green-600" size={28} />
          <div>
            <h2 className="text-xl font-semibold text-gray-900">충주시 뉴스</h2>
            <p className="text-sm text-gray-500">
              {newsData?.last_updated && `마지막 업데이트: ${newsData.last_updated}`}
              {newsData?.total_count > 0 && ` · 총 ${newsData.total_count}건`}
            </p>
          </div>
        </div>
        
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="btn-secondary flex items-center gap-2"
        >
          <RefreshCw size={18} className={refreshing ? 'animate-spin' : ''} />
          {refreshing ? '업데이트 중...' : '뉴스 업데이트'}
        </button>
      </div>

      {/* 에러 메시지 */}
      {error && (
        <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* 뉴스 없음 */}
      {newsList.length === 0 && !loading && (
        <div className="text-center py-12">
          <Newspaper size={48} className="mx-auto text-gray-300 mb-4" />
          <p className="text-gray-500">수집된 뉴스가 없습니다.</p>
          <button onClick={handleRefresh} className="mt-4 btn-primary">
            뉴스 업데이트
          </button>
        </div>
      )}

      {/* 뉴스 그리드 (행 단위 처리) */}
      {newsRows.map((row, rowIndex) => {
        const rowIds = row.map(n => n.id);
        const selectedInRow = rowIds.includes(selectedNewsId);
        const selectedNews = selectedInRow ? row.find(n => n.id === selectedNewsId) : null;

        return (
          <div key={rowIndex}>
            {/* 카드 행 */}
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {row.map((news) => {
                const isSelected = news.id === selectedNewsId;
                const title = decodeHtml(news.title);
                const press = decodeHtml(news.press);
                const summary = decodeHtml(news.summary);

                return (
                  <div
                    key={news.id}
                    className={`
                      card cursor-pointer transition-all duration-200
                      ${isSelected 
                        ? 'ring-2 ring-green-500 bg-green-50' 
                        : 'hover:shadow-md hover:border-green-200'}
                    `}
                    onClick={() => handleCardClick(news.id)}
                  >
                    {/* 제목 */}
                    <h3 className="font-semibold text-gray-900 line-clamp-2 mb-2 min-h-[3rem]">
                      {isSelected && <span className="text-green-600 mr-1">▼</span>}
                      {title}
                    </h3>
                    
                    {/* 메타 정보 */}
                    <div className="flex items-center gap-3 text-sm text-gray-500 mb-2">
                      <span className="flex items-center gap-1">
                        <Building2 size={14} />
                        {press}
                      </span>
                      <span className="flex items-center gap-1">
                        <Calendar size={14} />
                        {news.date}
                      </span>
                    </div>

                    {/* 요약 미리보기 */}
                    <p className="text-sm text-gray-600 line-clamp-3">
                      {summary}
                    </p>

                    {/* 버튼 */}
                    <div className="mt-3 pt-3 border-t border-gray-100">
                      {isSelected ? (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedNewsId(null);
                          }}
                          className="w-full py-2 text-sm text-gray-600 hover:text-gray-800 
                                   flex items-center justify-center gap-1"
                        >
                          <X size={16} />
                          닫기
                        </button>
                      ) : (
                        <button
                          className="w-full py-2 text-sm text-green-600 hover:text-green-700 
                                   flex items-center justify-center gap-1"
                        >
                          <ChevronDown size={16} />
                          자세히 보기
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* 선택된 뉴스 상세 (해당 행 아래에 표시) */}
            {selectedNews && (
              <div className="mt-4 p-6 bg-white rounded-xl border-2 border-green-200 shadow-lg animate-fadeIn">
                {/* 상세 헤더 */}
                <div className="flex items-start justify-between mb-4">
                  <h3 className="text-xl font-bold text-gray-900 flex-1 pr-4">
                    📰 {decodeHtml(selectedNews.title)}
                  </h3>
                  <button
                    onClick={() => setSelectedNewsId(null)}
                    className="p-1 hover:bg-gray-100 rounded"
                  >
                    <X size={20} className="text-gray-400" />
                  </button>
                </div>

                {/* 메타 정보 */}
                <div className="flex items-center gap-4 text-sm text-gray-500 mb-4">
                  <span className="flex items-center gap-1">
                    <Building2 size={16} />
                    {decodeHtml(selectedNews.press)}
                  </span>
                  <span className="flex items-center gap-1">
                    <Calendar size={16} />
                    {selectedNews.date}
                  </span>
                </div>

                {/* AI 요약 버튼 & 결과 */}
                <div className="mb-4">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSummarize(selectedNews);
                    }}
                    disabled={summaryLoading === selectedNews.id || summaries[selectedNews.id]}
                    className={`
                      flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium
                      transition-colors duration-200
                      ${summaries[selectedNews.id]
                        ? 'bg-green-100 text-green-700'
                        : 'bg-purple-100 text-purple-700 hover:bg-purple-200'}
                    `}
                  >
                    {summaryLoading === selectedNews.id ? (
                      <>
                        <Loader2 size={16} className="animate-spin" />
                        AI 요약 생성 중...
                      </>
                    ) : summaries[selectedNews.id] ? (
                      <>
                        <Sparkles size={16} />
                        AI 요약 완료
                      </>
                    ) : (
                      <>
                        <Sparkles size={16} />
                        AI 요약 생성
                      </>
                    )}
                  </button>

                  {/* AI 요약 결과 */}
                  {summaries[selectedNews.id] && (
                    <div className="mt-3 p-4 bg-purple-50 rounded-lg border border-purple-100">
                      <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
                        {summaries[selectedNews.id]}
                      </p>
                    </div>
                  )}
                </div>

                {/* 본문 */}
                <div className="mb-4">
                  <h4 className="font-semibold text-gray-900 mb-2">📄 본문</h4>
                  <div className="p-4 bg-gray-50 rounded-lg max-h-64 overflow-y-auto">
                    <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                      {decodeHtml(selectedNews.content)}
                    </p>
                  </div>
                </div>

                {/* 원문 링크 */}
                <a
                  href={selectedNews.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 
                           text-sm font-medium"
                >
                  <ExternalLink size={16} />
                  원문 보기
                </a>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default NewsViewer;
