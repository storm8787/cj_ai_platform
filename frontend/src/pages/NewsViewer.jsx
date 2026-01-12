import { useState, useEffect } from 'react';
import { Newspaper, RefreshCw, Sparkles, ExternalLink, Loader2, Calendar } from 'lucide-react';
import { newsApi } from '../services/api';

function NewsViewer() {
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedNews, setSelectedNews] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaries, setSummaries] = useState({});
  const [error, setError] = useState('');

  // 뉴스 목록 로드
  useEffect(() => {
    loadNews();
  }, []);

  const loadNews = async () => {
    try {
      const response = await newsApi.getList();
      setNews(response.data.news || []);
    } catch (err) {
      setError('뉴스를 불러오는데 실패했습니다.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // 뉴스 새로고침
  const handleRefresh = async () => {
    setRefreshing(true);
    setError('');
    
    try {
      await newsApi.refresh();
      // 새로고침 트리거 후 잠시 대기
      await new Promise(resolve => setTimeout(resolve, 3000));
      await loadNews();
    } catch (err) {
      setError('뉴스 새로고침에 실패했습니다.');
      console.error(err);
    } finally {
      setRefreshing(false);
    }
  };

  // AI 요약 생성
  const handleSummarize = async (newsItem) => {
    if (summaries[newsItem.link]) {
      return; // 이미 요약이 있으면 스킵
    }

    setSummaryLoading(true);
    
    try {
      const response = await newsApi.summarize({
        title: newsItem.title,
        content: newsItem.content,
        link: newsItem.link,
      });
      
      setSummaries(prev => ({
        ...prev,
        [newsItem.link]: response.data.summary
      }));
    } catch (err) {
      console.error('요약 생성 실패:', err);
    } finally {
      setSummaryLoading(false);
    }
  };

  // 날짜 포맷
  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 size={32} className="animate-spin text-primary-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Newspaper className="text-green-600" size={24} />
          <h2 className="text-xl font-semibold text-gray-900">충주시 뉴스</h2>
          <span className="text-sm text-gray-500">({news.length}건)</span>
        </div>
        
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="btn-secondary flex items-center gap-2"
        >
          <RefreshCw size={18} className={refreshing ? 'animate-spin' : ''} />
          새로고침
        </button>
      </div>

      {/* 에러 메시지 */}
      {error && (
        <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* 뉴스 그리드 */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {news.map((item, index) => (
          <div
            key={item.link || index}
            className={`card cursor-pointer hover:shadow-md transition-shadow
              ${selectedNews === index ? 'ring-2 ring-green-500' : ''}`}
            onClick={() => setSelectedNews(selectedNews === index ? null : index)}
          >
            {/* 뉴스 이미지 */}
            {item.image && (
              <img
                src={item.image}
                alt={item.title}
                className="w-full h-40 object-cover rounded-lg mb-3"
                onError={(e) => { e.target.style.display = 'none'; }}
              />
            )}
            
            {/* 뉴스 제목 */}
            <h3 className="font-semibold text-gray-900 line-clamp-2 mb-2">
              {item.title}
            </h3>
            
            {/* 메타 정보 */}
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
              <Calendar size={14} />
              <span>{formatDate(item.date)}</span>
              {item.source && (
                <>
                  <span>•</span>
                  <span>{item.source}</span>
                </>
              )}
            </div>

            {/* 미리보기 */}
            <p className="text-sm text-gray-600 line-clamp-3">
              {item.description || item.content?.substring(0, 150)}
            </p>

            {/* 확장 영역 */}
            {selectedNews === index && (
              <div className="mt-4 pt-4 border-t border-gray-100 space-y-3">
                {/* 전체 내용 */}
                {item.content && (
                  <p className="text-sm text-gray-700 leading-relaxed">
                    {item.content}
                  </p>
                )}

                {/* AI 요약 */}
                <div className="space-y-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSummarize(item);
                    }}
                    disabled={summaryLoading || summaries[item.link]}
                    className="flex items-center gap-2 text-sm text-green-600 hover:text-green-700"
                  >
                    {summaryLoading ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : (
                      <Sparkles size={16} />
                    )}
                    {summaries[item.link] ? '요약 완료' : 'AI 요약'}
                  </button>
                  
                  {summaries[item.link] && (
                    <div className="p-3 bg-green-50 rounded-lg text-sm text-gray-700">
                      {summaries[item.link]}
                    </div>
                  )}
                </div>

                {/* 원문 링크 */}
                <a
                  href={item.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700"
                >
                  <ExternalLink size={14} />
                  원문 보기
                </a>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* 빈 상태 */}
      {news.length === 0 && !loading && (
        <div className="text-center py-12">
          <Newspaper size={48} className="mx-auto text-gray-300 mb-4" />
          <p className="text-gray-500">뉴스가 없습니다.</p>
          <button
            onClick={handleRefresh}
            className="mt-4 btn-primary"
          >
            뉴스 새로고침
          </button>
        </div>
      )}
    </div>
  );
}

export default NewsViewer;
