import { useState, useRef, useCallback } from 'react';
import { 
  MapPin, Upload, Download, Loader2, FileSpreadsheet, 
  ArrowRightLeft, Search, Map 
} from 'lucide-react';
import { addressGeocoderApi } from '../services/api';

function AddressGeocoder() {
  // 변환 방향 & 모드
  const [direction, setDirection] = useState('address-to-coord'); // 'address-to-coord' | 'coord-to-address'
  const [mode, setMode] = useState('single'); // 'single' | 'file'
  
  // 단일 변환
  const [address, setAddress] = useState('');
  const [lat, setLat] = useState('');
  const [lon, setLon] = useState('');
  const [singleResult, setSingleResult] = useState(null);
  
  // 파일 변환
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  
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
    
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      validateAndSetFile(droppedFile);
    }
  }, []);

  const validateAndSetFile = (selectedFile) => {
    const validExtensions = ['.xlsx', '.xls', '.csv'];
    const fileExtension = selectedFile.name.toLowerCase().slice(selectedFile.name.lastIndexOf('.'));
    
    if (!validExtensions.includes(fileExtension)) {
      setError('xlsx, xls, csv 파일만 지원합니다.');
      return;
    }
    
    if (selectedFile.size > 10 * 1024 * 1024) {
      setError('파일 크기는 10MB 이하만 가능합니다.');
      return;
    }
    
    setFile(selectedFile);
    setError('');
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      validateAndSetFile(selectedFile);
    }
  };

  // 단일 주소 → 좌표 변환
  const handleSingleAddressToCoord = async () => {
    if (!address.trim()) {
      setError('주소를 입력해주세요.');
      return;
    }
    
    setLoading(true);
    setError('');
    setSingleResult(null);
    
    try {
      const response = await addressGeocoderApi.addressToCoord({ address });
      setSingleResult(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || '변환에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // 단일 좌표 → 주소 변환
  const handleSingleCoordToAddress = async () => {
    if (!lat || !lon) {
      setError('위도와 경도를 모두 입력해주세요.');
      return;
    }
    
    setLoading(true);
    setError('');
    setSingleResult(null);
    
    try {
      const response = await addressGeocoderApi.coordToAddress({ 
        lat: parseFloat(lat), 
        lon: parseFloat(lon) 
      });
      setSingleResult(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || '변환에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // 파일 변환
  const handleFileConvert = async () => {
    if (!file) {
      setError('파일을 선택해주세요.');
      return;
    }
    
    setLoading(true);
    setError('');
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const endpoint = direction === 'address-to-coord' 
        ? 'fileAddressToCoord' 
        : 'fileCoordToAddress';
      
      const response = await addressGeocoderApi[endpoint](formData);
      
      // 파일 다운로드
      const blob = new Blob([response.data], { 
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = direction === 'address-to-coord' 
        ? '결과_주소_좌표변환.xlsx' 
        : '결과_좌표_주소변환.xlsx';
      link.click();
      URL.revokeObjectURL(url);
      
    } catch (err) {
      setError(err.response?.data?.detail || '변환에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // 템플릿 다운로드
  const handleDownloadTemplate = async () => {
    try {
      const templateType = direction === 'address-to-coord' ? 'address' : 'coord';
      const response = await addressGeocoderApi.downloadTemplate(templateType);
      
      const blob = new Blob([response.data], { 
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = direction === 'address-to-coord' 
        ? 'template_주소_좌표.xlsx' 
        : 'template_좌표_주소.xlsx';
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError('템플릿 다운로드에 실패했습니다.');
    }
  };

  const resetFile = () => {
    setFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* 헤더 */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <MapPin className="text-cyan-400" size={28} />
          <h1 className="text-2xl font-bold text-white">주소-좌표 변환기</h1>
        </div>
        <p className="text-slate-400">
          카카오 API 기반 주소 ↔ 좌표 변환 (충주시 행정동 보정 지원)
        </p>
      </div>

      <div className="bg-white rounded-xl shadow-lg p-8">
        {/* 옵션 선택 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* 변환 방향 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              🔄 변환 방향
            </label>
            <div className="flex gap-2">
              <button
                onClick={() => { setDirection('address-to-coord'); setSingleResult(null); }}
                className={`flex-1 py-3 px-4 rounded-lg font-medium transition-colors ${
                  direction === 'address-to-coord'
                    ? 'bg-cyan-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                주소 → 좌표
              </button>
              <button
                onClick={() => { setDirection('coord-to-address'); setSingleResult(null); }}
                className={`flex-1 py-3 px-4 rounded-lg font-medium transition-colors ${
                  direction === 'coord-to-address'
                    ? 'bg-cyan-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                좌표 → 주소
              </button>
            </div>
          </div>

          {/* 처리 방식 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              🛠️ 처리 방식
            </label>
            <div className="flex gap-2">
              <button
                onClick={() => setMode('single')}
                className={`flex-1 py-3 px-4 rounded-lg font-medium transition-colors ${
                  mode === 'single'
                    ? 'bg-cyan-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                건별
              </button>
              <button
                onClick={() => setMode('file')}
                className={`flex-1 py-3 px-4 rounded-lg font-medium transition-colors ${
                  mode === 'file'
                    ? 'bg-cyan-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                파일별
              </button>
            </div>
          </div>
        </div>

        {/* 에러 메시지 */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
            ❌ {error}
          </div>
        )}

        {/* 단일 변환 모드 */}
        {mode === 'single' && (
          <div className="space-y-6">
            {direction === 'address-to-coord' ? (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  📍 주소 입력
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                    placeholder="예: 충청북도 충주시 봉방동 1234"
                    className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500"
                    onKeyPress={(e) => e.key === 'Enter' && handleSingleAddressToCoord()}
                  />
                  <button
                    onClick={handleSingleAddressToCoord}
                    disabled={loading}
                    className="px-6 py-3 bg-cyan-600 hover:bg-cyan-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
                  >
                    {loading ? <Loader2 className="animate-spin" size={20} /> : <Search size={20} />}
                  </button>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    📍 위도 (Latitude)
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={lat}
                    onChange={(e) => setLat(e.target.value)}
                    placeholder="예: 36.9910"
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    📍 경도 (Longitude)
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={lon}
                    onChange={(e) => setLon(e.target.value)}
                    placeholder="예: 127.9250"
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500"
                  />
                </div>
                <div className="col-span-2">
                  <button
                    onClick={handleSingleCoordToAddress}
                    disabled={loading}
                    className="w-full py-3 bg-cyan-600 hover:bg-cyan-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {loading ? <Loader2 className="animate-spin" size={20} /> : <Search size={20} />}
                    주소 조회
                  </button>
                </div>
              </div>
            )}

            {/* 단일 결과 표시 */}
            {singleResult && (
              <div className="p-4 bg-cyan-50 border border-cyan-200 rounded-lg">
                <h3 className="font-semibold text-cyan-800 mb-3">📍 변환 결과</h3>
                {direction === 'address-to-coord' ? (
                  <div className="space-y-2 text-sm">
                    <p><span className="font-medium">위도:</span> {singleResult.lat || '-'}</p>
                    <p><span className="font-medium">경도:</span> {singleResult.lon || '-'}</p>
                    <p><span className="font-medium">정확도:</span> {singleResult.accuracy || '-'}</p>
                    {singleResult.error && <p className="text-red-600">오류: {singleResult.error}</p>}
                  </div>
                ) : (
                  <div className="space-y-2 text-sm">
                    <p><span className="font-medium">지번주소:</span> {singleResult.jibun_address || '-'}</p>
                    <p><span className="font-medium">도로명주소:</span> {singleResult.road_address || '-'}</p>
                    {singleResult.error && <p className="text-red-600">오류: {singleResult.error}</p>}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* 파일 변환 모드 */}
        {mode === 'file' && (
          <div className="space-y-6">
            {/* 템플릿 다운로드 */}
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-600">
                📥 템플릿 형식: {direction === 'address-to-coord' ? "'주소' 컬럼 필요" : "'위도', '경도' 컬럼 필요"}
              </p>
              <button
                onClick={handleDownloadTemplate}
                className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
              >
                <Download size={16} />
                템플릿 다운로드
              </button>
            </div>

            {/* 파일 업로드 - 드래그앤드롭 */}
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls,.csv"
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
                  <FileSpreadsheet size={32} className="text-cyan-600" />
                  <div className="text-left">
                    <p className="font-medium text-gray-900">{file.name}</p>
                    <p className="text-sm text-gray-500">
                      {(file.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); resetFile(); }}
                    className="ml-4 px-3 py-1 bg-gray-200 hover:bg-gray-300 rounded text-sm"
                  >
                    변경
                  </button>
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
                  <p className="text-sm text-gray-400 mt-1">xlsx, xls, csv (최대 10MB)</p>
                </div>
              )}
            </div>

            {/* 변환 버튼 */}
            <button
              onClick={handleFileConvert}
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
                  변환 중...
                </>
              ) : (
                <>
                  <ArrowRightLeft size={24} />
                  변환 시작
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {/* 안내 */}
      <div className="mt-6 bg-cyan-500/10 border border-cyan-500/20 rounded-xl p-4">
        <h3 className="font-semibold text-cyan-300 mb-2">💡 변환 안내</h3>
        <ul className="text-sm text-slate-300 space-y-1">
          <li>• 카카오 API로 정확한 좌표를 검색합니다</li>
          <li>• 검색 실패 시 인근번지 → 행정동 → 시군구 순으로 보정합니다</li>
          <li>• 충주시 25개 행정동 중심좌표가 내장되어 있습니다</li>
          <li>• 파일 변환 시 최대 1,000건까지 처리 가능합니다</li>
        </ul>
      </div>
    </div>
  );
}

export default AddressGeocoder;
