import { useState, useRef, useCallback } from 'react';
import { 
  Table2, Upload, Download, Loader2, FileSpreadsheet, 
  Trash2, Plus, CheckCircle 
} from 'lucide-react';
import { excelMergerApi } from '../services/api';

function ExcelMerger() {
  const [files, setFiles] = useState([]);
  const [headerRow, setHeaderRow] = useState(1);
  const [sheetOption, setSheetOption] = useState('1');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [resultInfo, setResultInfo] = useState(null);
  
  const fileInputRef = useRef(null);
  const dropZoneRef = useRef(null);

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
    
    const droppedFiles = Array.from(e.dataTransfer.files);
    validateAndAddFiles(droppedFiles);
  }, [files]);

  const validateAndAddFiles = (newFiles) => {
    const validExtensions = ['.xlsx', '.xls', '.csv'];
    const validFiles = [];
    const errors = [];
    
    newFiles.forEach(file => {
      const ext = file.name.toLowerCase().slice(file.name.lastIndexOf('.'));
      
      if (!validExtensions.includes(ext)) {
        errors.push(`${file.name}: 지원하지 않는 형식`);
        return;
      }
      
      if (file.size > 50 * 1024 * 1024) {
        errors.push(`${file.name}: 50MB 초과`);
        return;
      }
      
      // 중복 체크
      if (files.some(f => f.name === file.name && f.size === file.size)) {
        errors.push(`${file.name}: 이미 추가됨`);
        return;
      }
      
      validFiles.push(file);
    });
    
    if (errors.length > 0) {
      setError(errors.join(', '));
    } else {
      setError('');
    }
    
    if (validFiles.length > 0) {
      setFiles(prev => [...prev, ...validFiles]);
      setSuccess('');
      setResultInfo(null);
    }
  };

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files);
    if (selectedFiles.length > 0) {
      validateAndAddFiles(selectedFiles);
    }
    // 같은 파일 다시 선택 가능하도록 초기화
    e.target.value = '';
  };

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
    setSuccess('');
    setResultInfo(null);
  };

  const clearAllFiles = () => {
    setFiles([]);
    setError('');
    setSuccess('');
    setResultInfo(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // 엑셀 병합
  const handleMerge = async () => {
    if (files.length === 0) {
      setError('파일을 추가해주세요.');
      return;
    }
    
    if (files.length < 2) {
      setError('2개 이상의 파일을 추가해주세요.');
      return;
    }
    
    setLoading(true);
    setError('');
    setSuccess('');
    setResultInfo(null);
    
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });
    formData.append('header_row', headerRow.toString());
    formData.append('sheet_option', sheetOption);
    
    try {
      const response = await excelMergerApi.merge(formData);
      
      // 결과 정보 추출
      const processedCount = response.headers['x-processed-count'] || files.length;
      const totalRows = response.headers['x-total-rows'] || '?';
      const totalCols = response.headers['x-total-cols'] || '?';
      
      setResultInfo({
        processedCount,
        totalRows,
        totalCols
      });
      
      // 파일 다운로드
      const blob = new Blob([response.data], { 
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `통합결과_${new Date().toISOString().slice(0, 10)}.xlsx`;
      link.click();
      URL.revokeObjectURL(url);
      
      setSuccess('병합이 완료되었습니다! 파일이 다운로드됩니다.');
      
    } catch (err) {
      setError(err.response?.data?.detail || '병합에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // 총 파일 크기 계산
  const totalSize = files.reduce((sum, file) => sum + file.size, 0);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* 헤더 */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Table2 className="text-cyan-400" size={28} />
          <h1 className="text-2xl font-bold text-white">엑셀 취합기</h1>
        </div>
        <p className="text-slate-400">
          여러 엑셀 파일을 하나로 병합합니다
        </p>
      </div>

      <div className="bg-white rounded-xl shadow-lg p-8">
        {/* 옵션 설정 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {/* 제목행 설정 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              📌 제목행은 몇 번째 행인가요?
            </label>
            <input
              type="number"
              min={1}
              max={20}
              value={headerRow}
              onChange={(e) => setHeaderRow(parseInt(e.target.value) || 1)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500"
            />
            <p className="mt-1 text-xs text-gray-500">1부터 시작 (기본값: 1)</p>
          </div>

          {/* 시트 선택 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              📄 병합할 시트 선택
            </label>
            <select
              value={sheetOption}
              onChange={(e) => setSheetOption(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500"
            >
              {[...Array(10)].map((_, i) => (
                <option key={i + 1} value={String(i + 1)}>{i + 1}번째 시트</option>
              ))}
              <option value="all">모든 시트</option>
            </select>
          </div>
        </div>

        {/* 파일 업로드 - 드래그앤드롭 */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-gray-700">
              📂 엑셀 파일 업로드
            </label>
            {files.length > 0 && (
              <button
                onClick={clearAllFiles}
                className="text-sm text-red-500 hover:text-red-700 flex items-center gap-1"
              >
                <Trash2 size={14} />
                전체 삭제
              </button>
            )}
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xls,.csv"
            multiple
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
              border-2 border-dashed rounded-xl p-6 text-center cursor-pointer
              transition-all duration-200
              ${isDragging
                ? 'border-cyan-500 bg-cyan-50 scale-[1.01]'
                : 'border-gray-300 hover:border-cyan-400 hover:bg-cyan-50'}
            `}
          >
            {isDragging ? (
              <div>
                <Upload size={32} className="mx-auto text-cyan-600 mb-2 animate-bounce" />
                <p className="text-cyan-700 font-medium">여기에 파일을 놓으세요!</p>
              </div>
            ) : (
              <div>
                <Plus size={32} className="mx-auto text-gray-400 mb-2" />
                <p className="text-gray-600 font-medium">파일을 드래그하거나 클릭하여 추가</p>
                <p className="text-sm text-gray-400 mt-1">xlsx, xls, csv (여러 파일 선택 가능)</p>
              </div>
            )}
          </div>
        </div>

        {/* 파일 목록 */}
        {files.length > 0 && (
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium text-gray-700">
                📋 업로드된 파일 ({files.length}개)
              </p>
              <p className="text-xs text-gray-500">
                총 {(totalSize / 1024).toFixed(1)} KB
              </p>
            </div>
            
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {files.map((file, index) => (
                <div 
                  key={`${file.name}-${index}`}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <FileSpreadsheet size={20} className="text-cyan-600" />
                    <div>
                      <p className="text-sm font-medium text-gray-800 truncate max-w-[200px]">
                        {file.name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {(file.size / 1024).toFixed(1)} KB
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => removeFile(index)}
                    className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              ))}
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
            <div className="flex items-center gap-2">
              <CheckCircle size={20} />
              {success}
            </div>
            {resultInfo && (
              <div className="mt-2 text-sm">
                <span className="font-medium">처리 결과:</span> {resultInfo.processedCount}개 파일, 
                {resultInfo.totalRows}행 × {resultInfo.totalCols}열
              </div>
            )}
          </div>
        )}

        {/* 병합 버튼 */}
        <button
          onClick={handleMerge}
          disabled={loading || files.length < 2}
          className={`
            w-full py-4 px-6 rounded-xl text-white font-semibold text-lg
            flex items-center justify-center gap-3 transition-colors
            ${loading || files.length < 2
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-cyan-600 hover:bg-cyan-700'}
          `}
        >
          {loading ? (
            <>
              <Loader2 size={24} className="animate-spin" />
              병합 중...
            </>
          ) : (
            <>
              <Download size={24} />
              엑셀 파일 병합 ({files.length}개)
            </>
          )}
        </button>

        {files.length > 0 && files.length < 2 && (
          <p className="mt-2 text-center text-sm text-orange-600">
            ⚠️ 2개 이상의 파일을 추가해주세요
          </p>
        )}
      </div>

      {/* 안내 */}
      <div className="mt-6 bg-cyan-500/10 border border-cyan-500/20 rounded-xl p-4">
        <h3 className="font-semibold text-cyan-300 mb-2">💡 사용 안내</h3>
        <ul className="text-sm text-slate-300 space-y-1">
          <li>• 여러 엑셀 파일을 하나의 시트로 통합합니다</li>
          <li>• 제목행(헤더)을 기준으로 데이터를 병합합니다</li>
          <li>• 컬럼 구조가 동일한 파일끼리 병합하면 좋습니다</li>
          <li>• 파일명에 한글이 포함되어도 정상 처리됩니다</li>
        </ul>
      </div>
    </div>
  );
}

export default ExcelMerger;
