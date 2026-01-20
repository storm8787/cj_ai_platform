import { useState, useEffect, useCallback, useRef } from 'react';
import { Languages, Upload, Download, Loader2, FileText, Settings } from 'lucide-react';
import { translatorApi } from '../services/api';

function Translator() {
  const [file, setFile] = useState(null);
  const [targetLang, setTargetLang] = useState('EN-US');
  const [fontMode, setFontMode] = useState('all');
  const [languages, setLanguages] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isDragging, setIsDragging] = useState(false);

  const fileInputRef = useRef(null);
  const dropZoneRef = useRef(null);

  // 지원 언어 로드
  useEffect(() => {
    loadLanguages();
  }, []);

  const loadLanguages = async () => {
    try {
      const response = await translatorApi.getLanguages();
      setLanguages(response.data.languages);
    } catch (err) {
      // 기본 언어 목록 사용 - {코드: 이름} 형태 유지!
      setLanguages({
        "KO": "한국어",
        "EN-US": "영어 (미국)",
        "EN-GB": "영어 (영국)",
        "JA": "일본어",
        "ZH-HANS": "중국어 (간체)",
        "ZH-HANT": "중국어 (번체)",
        "VI": "베트남어",
        "TH": "태국어",
        "RU": "러시아어",
        "AR": "아랍어",
        "HE": "히브리어",
        "ES": "스페인어",
        "DE": "독일어",
        "FR": "프랑스어",
        "ID": "인도네시아어",
        "IT": "이탈리아어",
        "PT": "포르투갈어",
        "PT-BR": "포르투갈어 (브라질)",
        "PL": "폴란드어",
        "NL": "네덜란드어",
        "TR": "터키어",
        "UK": "우크라이나어"
      });
    }
  };

  // 드래그 이벤트 핸들러
  const handleDragEnter = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (dropZoneRef.current && !dropZoneRef.current.contains(e.relatedTarget)) {
      setIsDragging(false);
    }
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      validateAndSetFile(droppedFile);
    }
  }, []);

  // 파일 유효성 검사 및 설정
  const validateAndSetFile = (selectedFile) => {
    if (!selectedFile.name.endsWith('.hwpx')) {
      setError('HWPX 파일만 지원합니다.');
      setFile(null);
      return;
    }
    
    // 파일 크기 제한 (50MB)
    if (selectedFile.size > 50 * 1024 * 1024) {
      setError('파일 크기는 50MB 이하만 가능합니다.');
      return;
    }
    
    setFile(selectedFile);
    setError('');
    setSuccess('');
  };

  // 파일 선택 (input 이벤트)
  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      validateAndSetFile(selectedFile);
    }
  };

  // 번역 실행
  const handleTranslate = async () => {
    if (!file) {
      setError('파일을 선택해주세요.');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('target_lang', targetLang);
    formData.append('font_mode', fontMode);

    try {
      const response = await translatorApi.translate(formData);
      
      // Blob으로 다운로드
      const blob = new Blob([response.data], { type: 'application/zip' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const originalName = file.name.replace('.hwpx', '');
      link.download = `${originalName}_translated_${targetLang}.hwpx`;
      link.click();
      URL.revokeObjectURL(url);

      setSuccess('번역이 완료되었습니다! 파일이 다운로드됩니다.');
    } catch (err) {
      setError(err.response?.data?.detail || '번역에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const fontModeOptions = [
    { value: 'all', label: '전체 통일 (맑은 고딕)' },
    { value: 'hangul_only', label: '한글만 맑은 고딕' },
    { value: 'none', label: '변경 안 함' }
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* 헤더 */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Languages className="text-cyan-400" size={28} />
          <h1 className="text-2xl font-bold text-white">다국어 번역기</h1>
        </div>
        <p className="text-slate-400">
          HWPX 문서를 DeepL + GPT로 고품질 번역합니다
        </p>
      </div>

      <div className="bg-white rounded-xl shadow-lg p-8">
        {/* 파일 업로드 - 드래그앤드롭 지원 */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            📄 HWPX 파일 선택
          </label>
          
          <input
            ref={fileInputRef}
            type="file"
            accept=".hwpx"
            onChange={handleFileChange}
            className="hidden"
          />
          
          <div
            ref={dropZoneRef}
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`
              border-2 border-dashed rounded-xl p-8 text-center cursor-pointer
              transition-all duration-200
              ${file 
                ? 'border-cyan-400 bg-cyan-50' 
                : isDragging
                  ? 'border-cyan-500 bg-cyan-100 scale-[1.02] shadow-lg'
                  : 'border-gray-300 hover:border-cyan-400 hover:bg-cyan-50'}
            `}
          >
            {file ? (
              <div className="flex items-center justify-center gap-3">
                <FileText size={32} className="text-cyan-600" />
                <div className="text-left">
                  <p className="font-medium text-gray-900">{file.name}</p>
                  <p className="text-sm text-gray-500">
                    {(file.size / 1024).toFixed(1)} KB
                  </p>
                </div>
              </div>
            ) : isDragging ? (
              <div>
                <Upload size={32} className="mx-auto text-cyan-600 mb-2 animate-bounce" />
                <p className="text-cyan-700 font-medium">여기에 파일을 놓으세요!</p>
              </div>
            ) : (
              <div>
                <Upload size={32} className="mx-auto text-gray-400 mb-2" />
                <p className="text-gray-600 font-medium">파일을 드래그하거나 클릭</p>
                <p className="text-sm text-gray-400 mt-1">HWPX 파일만 지원 (최대 50MB)</p>
              </div>
            )}
          </div>
        </div>

        {/* 옵션 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {/* 대상 언어 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              🌐 번역 언어
            </label>
            <select
              value={targetLang}
              onChange={(e) => setTargetLang(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg 
                       focus:outline-none focus:ring-2 focus:ring-cyan-500"
            >
              {Object.entries(languages).map(([code, name]) => (
                <option key={code} value={code}>{name}</option>
              ))}
            </select>
          </div>

          {/* 폰트 모드 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              🔤 폰트 보정
            </label>
            <select
              value={fontMode}
              onChange={(e) => setFontMode(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg 
                       focus:outline-none focus:ring-2 focus:ring-cyan-500"
            >
              {fontModeOptions.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        </div>

        {/* 파일 정보 표시 */}
        {file && (
          <div className="grid grid-cols-3 gap-4 mb-6 p-4 bg-gray-50 rounded-lg">
            <div className="text-center">
              <p className="text-sm text-gray-500">파일 형식</p>
              <p className="font-semibold text-gray-900">📄 HWPX</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-500">대상 언어</p>
              <p className="font-semibold text-cyan-600">{targetLang}</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-500">폰트 모드</p>
              <p className="font-semibold text-gray-900">
                {fontModeOptions.find(o => o.value === fontMode)?.label}
              </p>
            </div>
          </div>
        )}

        {/* 에러/성공 메시지 */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
            ❌ {error}
          </div>
        )}

        {success && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 text-green-700 rounded-lg">
            ✅ {success}
          </div>
        )}

        {/* 번역 버튼 */}
        <button
          onClick={handleTranslate}
          disabled={loading || !file}
          className={`
            w-full py-4 px-6 rounded-xl text-white font-semibold text-lg
            flex items-center justify-center gap-3 transition-colors
            ${loading || !file
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-cyan-600 hover:bg-cyan-700'}
          `}
        >
          {loading ? (
            <>
              <Loader2 size={24} className="animate-spin" />
              번역 중... (DeepL + GPT 처리)
            </>
          ) : (
            <>
              <Languages size={24} />
              번역 시작
            </>
          )}
        </button>

        {/* 안내 */}
        {loading && (
          <div className="mt-4 p-4 bg-cyan-50 rounded-lg">
            <p className="text-cyan-800 text-sm">
              ⏳ 문서 크기에 따라 1~5분 정도 소요될 수 있습니다.
            </p>
          </div>
        )}
      </div>

      {/* 사용 안내 */}
      <div className="mt-6 bg-cyan-500/10 border border-cyan-500/20 rounded-xl p-4">
        <h3 className="font-semibold text-cyan-300 mb-2">💡 번역 안내</h3>
        <ul className="text-sm text-slate-300 space-y-1">
          <li>• DeepL로 1차 번역 후, 한글 잔존 시 GPT가 2차 번역합니다</li>
          <li>• 표, 그림 등 레이아웃은 최대한 보존됩니다</li>
          <li>• 폰트 보정을 통해 번역 후 글자 깨짐을 방지합니다</li>
          <li>• 번역 품질 향상을 위해 원본 문서의 맞춤법을 확인해주세요</li>
        </ul>
      </div>
    </div>
  );
}

export default Translator;