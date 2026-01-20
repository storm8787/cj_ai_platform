import { useState } from 'react';
import { Award, FileText, Loader2, Download, User, Building2, Calendar } from 'lucide-react';
import { meritReportApi } from '../services/api';

function MeritReport() {
  const [formData, setFormData] = useState({
    name: '',
    position: '',
    department: '',
    start_date: '',
    award_type: '',
    achievement_area: '',
    merit_points_raw: ''
  });
  
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [generationTime, setGenerationTime] = useState(0);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult('');

    // 공적요지 파싱
    const merit_points = formData.merit_points_raw
      .split('\n')
      .map(line => line.trim())
      .filter(line => line);

    if (merit_points.length === 0) {
      setError('공적요지를 1개 이상 입력해주세요.');
      setLoading(false);
      return;
    }

    try {
      const response = await meritReportApi.generate({
        name: formData.name,
        position: formData.position,
        department: formData.department,
        start_date: formData.start_date,
        award_type: formData.award_type,
        achievement_area: formData.achievement_area,
        merit_points: merit_points
      });

      setResult(response.data.result);
      setGenerationTime(response.data.generation_time);
    } catch (err) {
      setError(err.response?.data?.detail || '공적조서 생성에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const downloadResult = () => {
    const blob = new Blob([result], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    const timestamp = new Date().toISOString().slice(0, 10);
    link.download = `${formData.name}_공적조서_${timestamp}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* 헤더 */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <Award className="text-cyan-400" size={28} />
          <h1 className="text-2xl font-bold text-white">공적조서 생성기</h1>
        </div>
        <p className="text-slate-400">
          공무원 정보를 입력하면 GPT가 공적조서를 자동으로 생성합니다.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 입력 폼 */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <User size={20} />
            입력 정보
          </h2>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* 성명 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                성명 *
              </label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500"
                placeholder="홍길동"
              />
            </div>

            {/* 직급 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                직급 *
              </label>
              <input
                type="text"
                name="position"
                value={formData.position}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500"
                placeholder="주사보"
              />
            </div>

            {/* 소속부서 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                소속부서 *
              </label>
              <input
                type="text"
                name="department"
                value={formData.department}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500"
                placeholder="자치행정과"
              />
            </div>

            {/* 임용일 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                임용일 *
              </label>
              <input
                type="text"
                name="start_date"
                value={formData.start_date}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500"
                placeholder="2020년 01월 01일"
              />
            </div>

            {/* 표창 종류 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                표창 종류 *
              </label>
              <input
                type="text"
                name="award_type"
                value={formData.award_type}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500"
                placeholder="대통령 표창, 국무총리 표창 등"
              />
            </div>

            {/* 공적 분야 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                공적 분야 *
              </label>
              <input
                type="text"
                name="achievement_area"
                value={formData.achievement_area}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500"
                placeholder="공공데이터 활용, 개인정보보호 등"
              />
            </div>

            {/* 공적요지 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                공적요지 * (한 줄에 하나씩)
              </label>
              <textarea
                name="merit_points_raw"
                value={formData.merit_points_raw}
                onChange={handleChange}
                required
                rows={6}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500"
                placeholder="데이터기반행정 우수 등급 획득(공유데이터 등록, 교육 실시)&#10;개인정보보호 우수사례 발표&#10;업무 프로세스 개선"
              />
              <p className="text-xs text-gray-500 mt-1">
                괄호 안에 구체 사례를 입력하면 더 상세한 내용이 작성됩니다.
              </p>
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
              {loading ? (
                <>
                  <Loader2 size={20} className="animate-spin" />
                  생성 중...
                </>
              ) : (
                <>
                  <FileText size={20} />
                  공적조서 생성하기
                </>
              )}
            </button>
          </form>
        </div>

        {/* 결과 */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-900">생성 결과</h2>
            {result && (
              <button
                onClick={downloadResult}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm flex items-center gap-2"
              >
                <Download size={16} />
                다운로드
              </button>
            )}
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
              ❌ {error}
            </div>
          )}

          {loading && (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 size={48} className="animate-spin text-cyan-600 mb-4" />
              <p className="text-gray-600">GPT가 공적조서를 작성하고 있습니다...</p>
              <p className="text-sm text-gray-500 mt-2">최대 1분 정도 소요됩니다</p>
            </div>
          )}

          {result && !loading && (
            <div className="space-y-4">
              {/* 생성 시간 */}
              <div className="p-3 bg-cyan-50 rounded-lg text-sm">
                <span className="text-gray-600">생성 시간:</span>
                <span className="ml-2 font-semibold text-cyan-700">{generationTime}초</span>
              </div>

              {/* 결과 텍스트 */}
              <textarea
                value={result}
                readOnly
                rows={20}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm font-mono"
              />

              {/* 성공 메시지 */}
              <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                <p className="text-green-800 font-semibold">
                  ✅ 생성 완료! 공적조서가 준비되었습니다.
                </p>
              </div>
            </div>
          )}

          {!result && !loading && !error && (
            <div className="flex items-center justify-center h-64 text-gray-400">
              <div className="text-center">
                <Award size={48} className="mx-auto mb-4 opacity-50" />
                <p>생성된 공적조서가 여기에 표시됩니다</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 안내 */}
      <div className="mt-6 bg-cyan-500/10 border border-cyan-500/20 rounded-xl p-4">
        <h3 className="font-semibold text-cyan-300 mb-2">💡 사용 팁</h3>
        <ul className="text-sm text-slate-300 space-y-1">
          <li>• 공적요지는 구체적으로 작성할수록 좋은 결과를 얻을 수 있습니다</li>
          <li>• 괄호 안에 구체 사례를 입력하면 해당 내용으로 상세 문단이 작성됩니다</li>
          <li>• 생성된 내용은 검토 후 필요에 따라 수정해주세요</li>
        </ul>
      </div>
    </div>
  );
}

export default MeritReport;
