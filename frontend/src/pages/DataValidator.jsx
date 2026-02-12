import { useState, useEffect, useRef } from 'react';
import { 
  Search, Upload, FileSpreadsheet, CheckCircle2, XCircle, AlertTriangle, 
  Info, ChevronRight, Database, RefreshCw, Download
} from 'lucide-react';
import api from '../services/api';

export default function DataValidator() {
  // 상태
  const [standards, setStandards] = useState([]);
  const [filteredStandards, setFilteredStandards] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedStandard, setSelectedStandard] = useState(null);
  const [standardDetail, setStandardDetail] = useState(null);
  const [file, setFile] = useState(null);
  const [validating, setValidating] = useState(false);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const fileInputRef = useRef(null);

  // 표준 목록 로드
  useEffect(() => {
    loadStandards();
  }, []);

  // 검색 필터링
  useEffect(() => {
    if (!searchTerm) {
      setFilteredStandards(standards);
    } else {
      const filtered = standards.filter(s => 
        s.name.toLowerCase().includes(searchTerm.toLowerCase())
      );
      setFilteredStandards(filtered);
    }
  }, [searchTerm, standards]);

  const loadStandards = async () => {
    try {
      const response = await api.get('/api/data-validator/standards');
      setStandards(response.data.standards);
      setFilteredStandards(response.data.standards);
    } catch (error) {
      console.error('표준 목록 로드 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  // 표준 선택
  const handleSelectStandard = async (standard) => {
    setSelectedStandard(standard);
    setResult(null);
    setFile(null);
    
    try {
      const response = await api.get(`/api/data-validator/standards/${standard.id}`);
      setStandardDetail(response.data);
    } catch (error) {
      console.error('표준 상세 로드 실패:', error);
    }
  };

  // 파일 선택
  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setResult(null);
    }
  };

  // 드래그 앤 드롭
  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      setFile(droppedFile);
      setResult(null);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  // 검증 실행
  const handleValidate = async () => {
    if (!file || !selectedStandard) return;
    
    setValidating(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await api.post(
        `/api/data-validator/validate/${selectedStandard.id}`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      
      setResult(response.data);
    } catch (error) {
      console.error('검증 실패:', error);
      alert(error.response?.data?.detail || '검증 중 오류가 발생했습니다.');
    } finally {
      setValidating(false);
    }
  };

  // 점수 색상
  const getScoreColor = (score) => {
    if (score >= 80) return 'text-green-400';
    if (score >= 50) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getScoreBg = (score) => {
    if (score >= 80) return 'from-green-500/20 to-green-600/10 border-green-500/30';
    if (score >= 50) return 'from-yellow-500/20 to-yellow-600/10 border-yellow-500/30';
    return 'from-red-500/20 to-red-600/10 border-red-500/30';
  };

  return (
    <div className="min-h-[calc(100vh-64px)] bg-slate-950 p-6">
      <div className="max-w-7xl mx-auto">
        {/* 헤더 */}
        <div className="flex items-center gap-4 mb-6">
          <div className="p-3 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl">
            <Database className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">공공데이터 제공표준 검증기</h1>
            <p className="text-slate-400 text-sm">CSV/Excel 파일이 공공데이터 표준에 적합한지 검증합니다</p>
          </div>
        </div>

        <div className="grid grid-cols-12 gap-6">
          {/* 좌측: 표준 목록 */}
          <div className="col-span-4 space-y-4">
            {/* 검색 */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center gap-2 text-cyan-400 text-sm font-medium mb-3">
                <Search size={16} />
                표준 검색
              </div>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="표준명 검색..."
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
                />
              </div>
            </div>

            {/* 표준 목록 */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between text-sm mb-3">
                <span className="text-cyan-400 font-medium">표준 목록</span>
                <span className="text-slate-500">{filteredStandards.length}개</span>
              </div>
              
              <div className="max-h-[500px] overflow-y-auto space-y-1 pr-2 custom-scrollbar">
                {loading ? (
                  <div className="text-center py-8 text-slate-500">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
                    로딩 중...
                  </div>
                ) : filteredStandards.length === 0 ? (
                  <div className="text-center py-8 text-slate-500">
                    검색 결과가 없습니다
                  </div>
                ) : (
                  filteredStandards.map((s, idx) => (
                    <button
                      key={s.id}
                      onClick={() => handleSelectStandard(s)}
                      className={`w-full text-left px-3 py-2.5 rounded-lg transition-all flex items-center gap-2 ${
                        selectedStandard?.id === s.id 
                          ? 'bg-cyan-500/10 border border-cyan-500/50 text-white' 
                          : 'hover:bg-slate-800 text-slate-300 border border-transparent'
                      }`}
                    >
                      <span className="text-slate-500 text-xs w-8">{idx + 1}</span>
                      <span className="flex-1 truncate text-sm">{s.name}</span>
                      <span className="text-xs text-slate-500 bg-slate-800 px-2 py-0.5 rounded">
                        {s.field_count}
                      </span>
                    </button>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* 우측: 검증 영역 */}
          <div className="col-span-8 space-y-4">
            {!selectedStandard ? (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
                <Database className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-white mb-2">표준을 선택하세요</h3>
                <p className="text-slate-500 text-sm">좌측 목록에서 검증할 공공데이터 표준을 선택해주세요</p>
              </div>
            ) : (
              <>
                {/* 선택된 표준 정보 */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                  <h3 className="text-lg font-semibold text-white mb-1">{selectedStandard.name}</h3>
                  {standardDetail && (
                    <>
                      <p className="text-slate-400 text-sm mb-4">
                        {standardDetail.managing_org} · {standardDetail.field_count || standardDetail.fields?.length}개 항목
                      </p>
                      
                      {/* 필드 테이블 */}
                      <div className="max-h-[250px] overflow-y-auto border border-slate-700 rounded-lg">
                        <table className="w-full text-sm">
                          <thead className="bg-slate-800 sticky top-0">
                            <tr>
                              <th className="text-left px-3 py-2 text-slate-400 font-medium w-10">NO</th>
                              <th className="text-left px-3 py-2 text-slate-400 font-medium w-32">항목명</th>
                              <th className="text-left px-3 py-2 text-slate-400 font-medium w-16">구분</th>
                              <th className="text-left px-3 py-2 text-slate-400 font-medium">설명</th>
                              <th className="text-left px-3 py-2 text-slate-400 font-medium w-24">형식</th>
                            </tr>
                          </thead>
                          <tbody>
                            {standardDetail.fields?.map((f, i) => (
                              <tr key={i} className="border-t border-slate-800 hover:bg-slate-800/50">
                                <td className="px-3 py-2 text-slate-500">{f.no || i + 1}</td>
                                <td className="px-3 py-2 text-white font-medium">{f.field_name}</td>
                                <td className="px-3 py-2">
                                  <span className={`px-2 py-0.5 rounded text-xs ${
                                    f.required === '필수' 
                                      ? 'bg-cyan-500/20 text-cyan-400' 
                                      : 'bg-slate-700 text-slate-400'
                                  }`}>
                                    {f.required}
                                  </span>
                                </td>
                                <td className="px-3 py-2 text-slate-400 text-xs truncate max-w-xs">{f.description}</td>
                                <td className="px-3 py-2 text-cyan-400 text-xs">{f.format || 'text'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </>
                  )}
                </div>

                {/* 파일 업로드 */}
                {!result && (
                  <div
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    onClick={() => fileInputRef.current?.click()}
                    className={`bg-slate-900 border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                      file ? 'border-cyan-500 bg-cyan-500/5' : 'border-slate-700 hover:border-slate-600'
                    }`}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".csv,.xlsx,.xls"
                      onChange={handleFileChange}
                      className="hidden"
                    />
                    {file ? (
                      <>
                        <FileSpreadsheet className="w-12 h-12 text-cyan-400 mx-auto mb-3" />
                        <p className="text-white font-medium">{file.name}</p>
                        <p className="text-slate-500 text-sm mt-1">
                          {(file.size / 1024).toFixed(1)} KB · 다른 파일을 선택하려면 클릭
                        </p>
                      </>
                    ) : (
                      <>
                        <Upload className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                        <p className="text-white font-medium">파일을 드래그하거나 클릭하여 업로드</p>
                        <p className="text-slate-500 text-sm mt-1">CSV, XLSX, XLS 파일 지원</p>
                      </>
                    )}
                  </div>
                )}

                {/* 검증 버튼 */}
                {file && !result && (
                  <button
                    onClick={handleValidate}
                    disabled={validating}
                    className="w-full py-3 bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-medium rounded-xl hover:from-cyan-600 hover:to-blue-700 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {validating ? (
                      <>
                        <RefreshCw className="w-5 h-5 animate-spin" />
                        검증 중...
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="w-5 h-5" />
                        검증 시작
                      </>
                    )}
                  </button>
                )}

                {/* 검증 결과 */}
                {result && (
                  <div className="space-y-4">
                    {/* 점수 */}
                    <div className={`bg-gradient-to-br ${getScoreBg(result.result.score)} border rounded-xl p-6 text-center`}>
                      <div className={`text-6xl font-bold ${getScoreColor(result.result.score)} mb-2`}>
                        {result.result.score}
                      </div>
                      <div className="text-slate-300">적합도 점수</div>
                      <div className="text-slate-500 text-sm mt-2">
                        {result.file_name} · {result.result.total_rows}행 검증
                        {result.result.checked_rows < result.result.total_rows && ` (최대 ${result.result.checked_rows}행)`}
                      </div>
                    </div>

                    {/* 요약 통계 */}
                    <div className="grid grid-cols-4 gap-3">
                      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 text-center">
                        <div className="text-2xl font-bold text-white">
                          {result.result.matched_fields}/{result.result.total_fields}
                        </div>
                        <div className="text-slate-500 text-sm">항목 일치</div>
                      </div>
                      <div className="bg-slate-900 border border-red-500/30 rounded-xl p-4 text-center">
                        <div className="text-2xl font-bold text-red-400">
                          {result.result.total_errors}
                        </div>
                        <div className="text-slate-500 text-sm">오류</div>
                      </div>
                      <div className="bg-slate-900 border border-yellow-500/30 rounded-xl p-4 text-center">
                        <div className="text-2xl font-bold text-yellow-400">
                          {result.result.total_warnings}
                        </div>
                        <div className="text-slate-500 text-sm">경고</div>
                      </div>
                      <div className="bg-slate-900 border border-cyan-500/30 rounded-xl p-4 text-center">
                        <div className="text-2xl font-bold text-cyan-400">
                          {result.result.info.length}
                        </div>
                        <div className="text-slate-500 text-sm">참고</div>
                      </div>
                    </div>

                    {/* 상세 결과 */}
                    {(result.result.errors.length > 0 || result.result.warnings.length > 0 || result.result.info.length > 0) && (
                      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                        <h4 className="text-sm font-medium text-cyan-400 mb-4">상세 검증 결과</h4>
                        <div className="max-h-[300px] overflow-y-auto space-y-2">
                          {[...result.result.errors, ...result.result.warnings, ...result.result.info].map((item, idx) => (
                            <div 
                              key={idx} 
                              className={`flex items-start gap-3 p-3 rounded-lg ${
                                item.type === 'error' ? 'bg-red-500/10 border border-red-500/20' :
                                item.type === 'warning' ? 'bg-yellow-500/10 border border-yellow-500/20' :
                                'bg-cyan-500/10 border border-cyan-500/20'
                              }`}
                            >
                              {item.type === 'error' ? <XCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" /> :
                               item.type === 'warning' ? <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" /> :
                               <Info className="w-5 h-5 text-cyan-400 flex-shrink-0 mt-0.5" />}
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <span className="font-medium text-white">{item.field}</span>
                                  {item.row && <span className="text-slate-500 text-sm">· {item.row}행</span>}
                                  <span className="text-slate-400 text-sm">— {item.msg}</span>
                                </div>
                                {item.detail && (
                                  <div className="text-slate-500 text-sm mt-1">{item.detail}</div>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* 다시 검증 버튼 */}
                    <button
                      onClick={() => {
                        setResult(null);
                        setFile(null);
                      }}
                      className="w-full py-3 bg-slate-800 text-white font-medium rounded-xl hover:bg-slate-700 transition-all flex items-center justify-center gap-2"
                    >
                      <RefreshCw className="w-5 h-5" />
                      다른 파일 검증하기
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}