import { useState } from 'react';
import { FileText, Search, Sparkles, Copy, Download, Loader2 } from 'lucide-react';
import { pressReleaseApi } from '../services/api';

const DEPARTMENTS = [
  '기획예산과', '자치행정과', '세무과', '회계과', '정보통신과',
  '문화관광과', '체육진흥과', '환경과', '건설과', '도시과',
  '복지정책과', '보건소', '농업기술센터', '교육지원과'
];

const PARAGRAPH_OPTIONS = ['1개', '2개', '3개', '4개 이상'];
const LENGTH_OPTIONS = ['짧게', '중간', '길게'];

function PressRelease() {
  const [formData, setFormData] = useState({
    title: '',
    department: DEPARTMENTS[0],
    manager: '',
    paragraphs: '2개',
    length: '중간',
    content: '',
    additional: '',
  });
  
  const [similarDocs, setSimilarDocs] = useState([]);
  const [generatedText, setGeneratedText] = useState('');
  const [loading, setLoading] = useState({ search: false, generate: false });
  const [error, setError] = useState('');

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  // 유사 문서 검색
  const handleSearchSimilar = async () => {
    if (!formData.title.trim()) {
      setError('제목을 입력해주세요.');
      return;
    }

    setLoading(prev => ({ ...prev, search: true }));
    setError('');
    
    try {
      const response = await pressReleaseApi.searchSimilar({
        query: formData.title,
        top_k: 3
      });
      setSimilarDocs(response.data.documents || []);
    } catch (err) {
      setError('유사 문서 검색에 실패했습니다.');
      console.error(err);
    } finally {
      setLoading(prev => ({ ...prev, search: false }));
    }
  };

  // 보도자료 생성
  const handleGenerate = async () => {
    if (!formData.title.trim() || !formData.content.trim()) {
      setError('제목과 내용 포인트를 입력해주세요.');
      return;
    }

    setLoading(prev => ({ ...prev, generate: true }));
    setError('');

    try {
      const response = await pressReleaseApi.generate({
        title: formData.title,
        department: formData.department,
        manager: formData.manager,
        paragraphs: formData.paragraphs,
        length: formData.length,
        content: formData.content,
        additional: formData.additional,
      });
      setGeneratedText(response.data.result || '');
    } catch (err) {
      setError('보도자료 생성에 실패했습니다.');
      console.error(err);
    } finally {
      setLoading(prev => ({ ...prev, generate: false }));
    }
  };

  // 클립보드 복사
  const handleCopy = () => {
    navigator.clipboard.writeText(generatedText);
  };

  // 다운로드
  const handleDownload = () => {
    const blob = new Blob([generatedText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `보도자료_${formData.title}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-fadeIn">
      {/* 입력 폼 */}
      <div className="card">
        <div className="flex items-center gap-2 mb-6">
          <FileText className="text-primary-600" size={24} />
          <h2 className="text-xl font-semibold text-gray-900">보도자료 정보 입력</h2>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          {/* 제목 */}
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              보도자료 제목 *
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                className="input-field flex-1"
                placeholder="예: 충주시, 사과 축제 개최"
                value={formData.title}
                onChange={(e) => handleChange('title', e.target.value)}
              />
              <button
                onClick={handleSearchSimilar}
                disabled={loading.search}
                className="btn-secondary flex items-center gap-2 whitespace-nowrap"
              >
                {loading.search ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : (
                  <Search size={18} />
                )}
                유사문서
              </button>
            </div>
          </div>

          {/* 담당부서 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              담당부서
            </label>
            <select
              className="input-field"
              value={formData.department}
              onChange={(e) => handleChange('department', e.target.value)}
            >
              {DEPARTMENTS.map(dept => (
                <option key={dept} value={dept}>{dept}</option>
              ))}
            </select>
          </div>

          {/* 담당자 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              담당자명
            </label>
            <input
              type="text"
              className="input-field"
              placeholder="홍길동"
              value={formData.manager}
              onChange={(e) => handleChange('manager', e.target.value)}
            />
          </div>

          {/* 문단 수 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              문단 수
            </label>
            <select
              className="input-field"
              value={formData.paragraphs}
              onChange={(e) => handleChange('paragraphs', e.target.value)}
            >
              {PARAGRAPH_OPTIONS.map(opt => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          </div>

          {/* 길이 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              전체 길이
            </label>
            <select
              className="input-field"
              value={formData.length}
              onChange={(e) => handleChange('length', e.target.value)}
            >
              {LENGTH_OPTIONS.map(opt => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          </div>

          {/* 내용 포인트 */}
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              내용 포인트 *
            </label>
            <textarea
              className="input-field min-h-[120px]"
              placeholder="보도자료에 포함될 핵심 내용을 입력하세요..."
              value={formData.content}
              onChange={(e) => handleChange('content', e.target.value)}
            />
          </div>

          {/* 추가 요청 */}
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              추가 요청사항
            </label>
            <textarea
              className="input-field min-h-[80px]"
              placeholder="특별히 강조하거나 포함하고 싶은 내용이 있다면 입력하세요..."
              value={formData.additional}
              onChange={(e) => handleChange('additional', e.target.value)}
            />
          </div>
        </div>

        {/* 에러 메시지 */}
        {error && (
          <div className="mt-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* 생성 버튼 */}
        <div className="mt-6">
          <button
            onClick={handleGenerate}
            disabled={loading.generate}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {loading.generate ? (
              <>
                <Loader2 size={20} className="animate-spin" />
                생성 중...
              </>
            ) : (
              <>
                <Sparkles size={20} />
                보도자료 생성
              </>
            )}
          </button>
        </div>
      </div>

      {/* 유사 문서 결과 */}
      {similarDocs.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            유사 보도자료 ({similarDocs.length}건)
          </h3>
          <div className="space-y-3">
            {similarDocs.map((doc, index) => (
              <div key={index} className="p-3 bg-gray-50 rounded-lg">
                <div className="flex items-start justify-between">
                  <h4 className="font-medium text-gray-900">{doc.title || '제목 없음'}</h4>
                  <span className="text-xs text-gray-500 bg-gray-200 px-2 py-0.5 rounded">
                    유사도: {(doc.similarity * 100).toFixed(1)}%
                  </span>
                </div>
                <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                  {doc.content?.substring(0, 200)}...
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 생성 결과 */}
      {generatedText && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">생성된 보도자료</h3>
            <div className="flex gap-2">
              <button onClick={handleCopy} className="btn-secondary flex items-center gap-1">
                <Copy size={16} />
                복사
              </button>
              <button onClick={handleDownload} className="btn-secondary flex items-center gap-1">
                <Download size={16} />
                다운로드
              </button>
            </div>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg whitespace-pre-wrap text-gray-800 leading-relaxed">
            {generatedText}
          </div>
        </div>
      )}
    </div>
  );
}

export default PressRelease;
