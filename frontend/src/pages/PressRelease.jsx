import { useState } from 'react';
import { pressReleaseApi } from '../services/api';

export default function PressRelease() {
  const [formData, setFormData] = useState({
    title: '',
    department: '',
    manager: '',
    paragraphs: '4개이상',
    length: '길게',
    content: '',
    additional: ''
  });
  
  const [result, setResult] = useState('');
  const [references, setReferences] = useState([]);
  const [searchMethod, setSearchMethod] = useState('');
  const [vectorstoreStatus, setVectorstoreStatus] = useState(null);
  const [generationTime, setGenerationTime] = useState(0);
  const [supabaseLogId, setSupabaseLogId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [expandedRef, setExpandedRef] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult('');
    setReferences([]);

    try {
      const response = await pressReleaseApi.generate(formData);
      const data = response.data;
      
      setResult(data.result);
      setReferences(data.references || []);
      setSearchMethod(data.search_method || '');
      setVectorstoreStatus(data.vectorstore_status || null);
      setGenerationTime(data.generation_time || 0);
      setSupabaseLogId(data.supabase_log_id || null);
    } catch (err) {
      setError(err.response?.data?.detail || '보도자료 생성에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const downloadResult = () => {
    const blob = new Blob([result], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
    link.download = `${formData.title || '보도자료'}_${timestamp}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const toggleReference = (index) => {
    setExpandedRef(expandedRef === index ? null : index);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-2xl font-bold mb-2 text-white">📰 보도자료 생성기</h1>
      <p className="text-slate-400 mb-6">
        충주시의 8,000여 건 보도자료를 학습한 AI가 충주시 스타일의 보도자료를 자동 생성합니다.
      </p>


      {/* 시스템 정보 */}
      {vectorstoreStatus && (
        <div className="mb-6 p-4 bg-cyan-500/10 border border-cyan-500/20 rounded-lg">
          <h3 className="font-semibold text-cyan-300 mb-2">🔧 시스템 정보</h3>
          <div className="text-sm text-slate-300 space-y-1">
            <div>
              • AI 검색: {vectorstoreStatus.loaded ? 
                <span className="text-green-400 font-semibold">✅ 활성화</span> : 
                <span className="text-orange-400">⚠️ 비활성화 (기본 검색 사용)</span>
              }
            </div>
            {vectorstoreStatus.loaded && (
              <>
                <div>• 문서 수: {vectorstoreStatus.document_count?.toLocaleString()}개</div>
                <div>• 모델: ko-sroberta-multitask</div>
                <div>• 벡터 저장소: FAISS</div>
              </>
            )}
            <div>• 텍스트 생성: OpenAI GPT-4o-mini</div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 입력 폼 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">입력 정보</h2>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* 제목 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                📝 보도자료 제목 *
              </label>
              <input
                type="text"
                name="title"
                value={formData.title}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500"
                placeholder="제목을 입력하세요"
              />
              <p className="text-xs text-gray-500 mt-1">
                제목은 참고용이며, AI가 내용에 맞게 새로 작성합니다
              </p>
            </div>

            {/* 담당부서 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                🏢 담당부서
              </label>
              <input
                type="text"
                name="department"
                value={formData.department}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500"
                placeholder="예: 자치행정과"
              />
              <p className="text-xs text-gray-500 mt-1">
                담당자 인용문에서 "[이름] [부서]장"으로 표기됩니다
              </p>
            </div>

            {/* 담당자 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                👤 담당자
              </label>
              <input
                type="text"
                name="manager"
                value={formData.manager}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500"
                placeholder="예: 김태균"
              />
            </div>

            {/* 문단수 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                📑 문단 수
              </label>
              <select
                name="paragraphs"
                value={formData.paragraphs}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500"
              >
                <option value="4개이상">4개 이상</option>
                <option value="3개">3개</option>
                <option value="2개">2개</option>
                <option value="1개">1개</option>
              </select>
            </div>

            {/* 길이 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                📏 보도자료 길이
              </label>
              <select
                name="length"
                value={formData.length}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500"
              >
                <option value="길게">길게 (~1,300자)</option>
                <option value="중간">중간 (~1,100자)</option>
                <option value="짧게">짧게 (~900자)</option>
              </select>
            </div>

            {/* 내용 포인트 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                📌 내용 포인트 *
              </label>
              <textarea
                name="content"
                value={formData.content}
                onChange={handleChange}
                required
                rows={6}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500"
                placeholder="한 줄에 하나씩 입력하세요&#10;예:&#10;2026년 예산 확정&#10;전년 대비 5% 증가&#10;복지 분야 중점 투자"
              />
            </div>

            {/* 기타 요청 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                🔧 기타 요청사항
              </label>
              <textarea
                name="additional"
                value={formData.additional}
                onChange={handleChange}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500"
                placeholder="추가 요청사항을 입력하세요 (선택)"
              />
            </div>

            {/* 생성 버튼 */}
            <button
              type="submit"
              disabled={loading}
              className={`w-full py-3 px-4 rounded-lg text-white font-semibold flex items-center justify-center gap-2 ${
                loading 
                  ? 'bg-gray-400 cursor-not-allowed' 
                  : 'bg-cyan-600 hover:bg-cyan-700'
              }`}
            >
              {loading ? '생성 중...' : '🚀 보도자료 생성하기'}
            </button>
          </form>
        </div>

        {/* 결과 */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">생성 결과</h2>
            {result && (
              <button
                onClick={downloadResult}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm"
              >
                📥 다운로드
              </button>
            )}
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
              ❌ {error}
            </div>
          )}

          {loading && (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-600 mb-4"></div>
              <p className="text-gray-600">🔍 유사 문서 검색 중...</p>
              <p className="text-gray-600 mt-2">✍️ AI가 보도자료를 작성하고 있습니다...</p>
              <p className="text-sm text-gray-500 mt-2">최대 1분 정도 소요됩니다</p>
            </div>
          )}

          {result && !loading && (
            <div className="space-y-4">
              {/* 성능 정보 */}
              <div className="grid grid-cols-2 gap-4 p-3 bg-gray-50 rounded-md text-sm">
                <div>
                  <span className="text-gray-600">검색 방식:</span>
                  <span className="ml-2 font-semibold">{searchMethod}</span>
                </div>
                <div>
                  <span className="text-gray-600">생성 시간:</span>
                  <span className="ml-2 font-semibold">{generationTime}초</span>
                </div>
                <div>
                  <span className="text-gray-600">참조 문서:</span>
                  <span className="ml-2 font-semibold">{references.length}개</span>
                </div>
                <div>
                  <span className="text-gray-600">글자 수:</span>
                  <span className="ml-2 font-semibold">{result.length}자</span>
                </div>
              </div>

              {/* 보도자료 본문 */}
              <div>
                <h3 className="font-semibold mb-2">📄 생성된 보도자료</h3>
                <textarea
                  value={result}
                  readOnly
                  rows={20}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500 font-mono text-sm"
                />
              </div>

              {/* 성공 메시지 */}
              <div className="p-3 bg-green-50 border border-green-200 rounded-md">
                <p className="text-green-800 font-semibold">
                  ✅ 생성 완료! 충주시 스타일의 보도자료가 준비되었습니다.
                </p>
                {supabaseLogId && (
                  <p className="text-sm text-green-700 mt-1">
                    📊 로그 ID: {supabaseLogId}
                  </p>
                )}
              </div>
            </div>
          )}

          {!result && !loading && !error && (
            <div className="flex items-center justify-center h-64 text-gray-400">
              <div className="text-center">
                <p className="text-lg mb-2">📝</p>
                <p>생성된 보도자료가 여기에 표시됩니다</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 참조한 보도자료 정보 */}
      {references.length > 0 && (
        <div className="mt-6 bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">📋 참조한 보도자료 정보</h3>
          <p className="text-sm text-gray-600 mb-4">
            AI가 유사한 보도자료를 검색하여 참고했습니다. 각 문서를 클릭하면 전체 내용을 볼 수 있습니다.
          </p>
          
          <div className="space-y-3">
            {references.map((ref, idx) => (
              <div key={idx} className="border border-gray-200 rounded-lg overflow-hidden">
                {/* 요약 정보 */}
                <div 
                  className="p-4 bg-gray-50 cursor-pointer hover:bg-gray-100"
                  onClick={() => toggleReference(idx)}
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <h4 className="font-semibold text-gray-900">
                        {ref.index}번째 참조 문서
                      </h4>
                      <div className="mt-2 space-y-1 text-sm">
                        <div>
                          <span className="text-gray-600">유사도 점수:</span>
                          <span className="ml-2 font-semibold text-cyan-600">
                            {(ref.similarity * 100).toFixed(2)}%
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-600">문서 ID:</span>
                          <span className="ml-2 text-gray-800">{ref.doc_id}</span>
                        </div>
                        <div className="mt-2">
                          <span className="text-gray-600">내용 미리보기:</span>
                          <p className="mt-1 text-gray-700">{ref.preview}</p>
                        </div>
                      </div>
                    </div>
                    <div className="ml-4">
                      {expandedRef === idx ? (
                        <span className="text-gray-500">▲</span>
                      ) : (
                        <span className="text-gray-500">▼</span>
                      )}
                    </div>
                  </div>
                </div>

                {/* 전체 내용 */}
                {expandedRef === idx && (
                  <div className="p-4 bg-white border-t border-gray-200">
                    <h5 className="font-semibold text-gray-700 mb-2">
                      📄 {ref.index}번 문서 전체 내용
                    </h5>
                    <textarea
                      value={ref.full_content}
                      readOnly
                      rows={12}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-sm font-mono"
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 안내 정보 */}
      <div className="mt-6 bg-cyan-500/10 border border-cyan-500/20 rounded-lg p-4">
        <h3 className="font-semibold text-cyan-300 mb-2">💡 사용 팁</h3>
        <ul className="text-sm text-slate-300 space-y-1">
          <li>• 제목은 참고용이며, AI가 내용에 맞게 새로 작성합니다</li>
          <li>• 담당자 인용문은 "[이름] [부서]장" 형식으로 자동 생성됩니다 (예: 김태균 자치행정과장)</li>
          <li>• 문체는 보도자료 스타일의 간접화법을 사용합니다 (~했다, ~라고 밝혔다)</li>
          <li>• 제목은 "[제목]" 형식으로 시작하고, 부제목은 "-"로 시작합니다</li>
          <li>• 내용 포인트는 구체적일수록 좋은 결과를 얻을 수 있습니다</li>
          <li>• AI 벡터 검색이 활성화되면 더 정확한 유사 문서를 찾아 품질이 향상됩니다</li>
        </ul>
      </div>
    </div>
  );
}
