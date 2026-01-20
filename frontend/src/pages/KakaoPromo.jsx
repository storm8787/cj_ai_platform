import { useState, useRef, useCallback, useEffect } from 'react';
import { 
  MessageSquare, Upload, Loader2, Image, Copy, Check, RefreshCw 
} from 'lucide-react';
import { kakaoPromoApi } from '../services/api';

function KakaoPromo() {
  const [category, setCategory] = useState('시정홍보');
  const [content, setContent] = useState('');
  const [image, setImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [result, setResult] = useState('');
  const [extractedText, setExtractedText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [categories, setCategories] = useState([]);
  
  const fileInputRef = useRef(null);
  const dropZoneRef = useRef(null);

  // 카테고리 로드
  useEffect(() => {
    loadCategories();
  }, []);

  const loadCategories = async () => {
    try {
      const response = await kakaoPromoApi.getCategories();
      setCategories(response.data.categories);
    } catch (err) {
      // 기본 카테고리 사용
      setCategories([
        { value: '시정홍보', label: '🏛️ 시정홍보' },
        { value: '정책공지', label: '📢 정책공지' },
        { value: '문화행사', label: '🎭 문화행사' },
        { value: '축제', label: '🎊 축제' },
        { value: '이벤트', label: '🎁 이벤트' },
        { value: '재난알림', label: '⚠️ 재난알림' },
        { value: '기타', label: '📝 기타' },
      ]);
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
      validateAndSetImage(droppedFile);
    }
  }, []);

  const validateAndSetImage = (file) => {
    const validTypes = ['image/png', 'image/jpeg', 'image/jpg'];
    
    if (!validTypes.includes(file.type)) {
      setError('PNG, JPG, JPEG 이미지만 지원합니다.');
      return;
    }
    
    if (file.size > 5 * 1024 * 1024) {
      setError('이미지 크기는 5MB 이하만 가능합니다.');
      return;
    }
    
    setImage(file);
    setError('');
    
    // 미리보기 생성
    const reader = new FileReader();
    reader.onloadend = () => {
      setImagePreview(reader.result);
    };
    reader.readAsDataURL(file);
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      validateAndSetImage(file);
    }
  };

  const removeImage = () => {
    setImage(null);
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // 홍보문구 생성
  const handleGenerate = async () => {
    if (!content.trim() && !image) {
      setError('텍스트 또는 이미지를 입력해주세요.');
      return;
    }
    
    setLoading(true);
    setError('');
    setResult('');
    setExtractedText('');
    
    try {
      let response;
      
      if (image) {
        // 이미지 포함 생성
        const formData = new FormData();
        formData.append('category', category);
        formData.append('content', content);
        formData.append('image', image);
        
        response = await kakaoPromoApi.generateWithImage(formData);
        
        if (response.data.extracted_text) {
          setExtractedText(response.data.extracted_text);
        }
      } else {
        // 텍스트만 생성
        response = await kakaoPromoApi.generate({
          category,
          content
        });
      }
      
      setResult(response.data.result);
      
    } catch (err) {
      setError(err.response?.data?.detail || '생성에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // 복사 기능
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(result);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      setError('복사에 실패했습니다.');
    }
  };

  // 초기화
  const handleReset = () => {
    setContent('');
    setImage(null);
    setImagePreview(null);
    setResult('');
    setExtractedText('');
    setError('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* 헤더 */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <MessageSquare className="text-cyan-400" size={28} />
          <h1 className="text-2xl font-bold text-white">카카오채널 홍보문구 생성기</h1>
        </div>
        <p className="text-slate-400">
          텍스트 또는 이미지를 입력하면 카카오톡 채널용 홍보 문구를 생성합니다
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 입력 영역 */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">📝 입력</h2>
          
          {/* 카테고리 선택 */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              홍보 카테고리
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500"
            >
              {categories.map((cat) => (
                <option key={cat.value} value={cat.value}>{cat.label}</option>
              ))}
            </select>
          </div>

          {/* 텍스트 입력 */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              📥 텍스트 입력 (선택)
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="홍보할 내용을 입력하세요..."
              rows={5}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 resize-none"
            />
          </div>

          {/* 이미지 업로드 - 드래그앤드롭 */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              🖼️ 이미지 업로드 (선택)
            </label>
            
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg,image/jpg"
              onChange={handleFileChange}
              className="hidden"
            />
            
            {imagePreview ? (
              <div className="relative">
                <img 
                  src={imagePreview} 
                  alt="Preview" 
                  className="w-full h-40 object-cover rounded-lg"
                />
                <button
                  onClick={removeImage}
                  className="absolute top-2 right-2 px-3 py-1 bg-red-500 text-white rounded-lg text-sm hover:bg-red-600"
                >
                  삭제
                </button>
              </div>
            ) : (
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
                    ? 'border-cyan-500 bg-cyan-50 scale-[1.02]'
                    : 'border-gray-300 hover:border-cyan-400 hover:bg-cyan-50'}
                `}
              >
                {isDragging ? (
                  <div>
                    <Upload size={28} className="mx-auto text-cyan-600 mb-2 animate-bounce" />
                    <p className="text-cyan-700 font-medium">여기에 이미지를 놓으세요!</p>
                  </div>
                ) : (
                  <div>
                    <Image size={28} className="mx-auto text-gray-400 mb-2" />
                    <p className="text-gray-600">이미지를 드래그하거나 클릭</p>
                    <p className="text-xs text-gray-400 mt-1">PNG, JPG (최대 5MB)</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* 에러 메시지 */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
              ❌ {error}
            </div>
          )}

          {/* 버튼 */}
          <div className="flex gap-2">
            <button
              onClick={handleGenerate}
              disabled={loading || (!content.trim() && !image)}
              className={`
                flex-1 py-3 px-6 rounded-lg text-white font-semibold
                flex items-center justify-center gap-2 transition-colors
                ${loading || (!content.trim() && !image)
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-cyan-600 hover:bg-cyan-700'}
              `}
            >
              {loading ? (
                <>
                  <Loader2 size={20} className="animate-spin" />
                  생성 중...
                </>
              ) : (
                <>
                  <MessageSquare size={20} />
                  홍보문구 생성
                </>
              )}
            </button>
            
            <button
              onClick={handleReset}
              className="px-4 py-3 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg transition-colors"
            >
              <RefreshCw size={20} />
            </button>
          </div>
        </div>

        {/* 결과 영역 */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">✨ 생성 결과</h2>
            {result && (
              <button
                onClick={handleCopy}
                className="flex items-center gap-1 px-3 py-1.5 bg-cyan-100 hover:bg-cyan-200 text-cyan-700 rounded-lg text-sm transition-colors"
              >
                {copied ? <Check size={16} /> : <Copy size={16} />}
                {copied ? '복사됨!' : '복사'}
              </button>
            )}
          </div>

          {/* OCR 추출 텍스트 */}
          {extractedText && (
            <div className="mb-4 p-3 bg-gray-50 rounded-lg">
              <p className="text-xs font-medium text-gray-500 mb-1">🔍 이미지에서 추출된 텍스트</p>
              <p className="text-sm text-gray-700 whitespace-pre-wrap">{extractedText}</p>
            </div>
          )}

          {/* 생성 결과 */}
          <div className={`
            min-h-[300px] p-4 rounded-lg border
            ${result 
              ? 'bg-cyan-50 border-cyan-200' 
              : 'bg-gray-50 border-gray-200'}
          `}>
            {result ? (
              <div className="whitespace-pre-wrap text-gray-800">{result}</div>
            ) : (
              <div className="h-full flex items-center justify-center text-gray-400">
                <div className="text-center">
                  <MessageSquare size={48} className="mx-auto mb-2 opacity-50" />
                  <p>텍스트 또는 이미지를 입력하고</p>
                  <p>홍보문구를 생성해보세요!</p>
                </div>
              </div>
            )}
          </div>

          {result && (
            <p className="mt-3 text-xs text-gray-500 text-center">
              ✨ 충주시 홍보부서의 톤앤매너를 기반으로 작성되었습니다
            </p>
          )}
        </div>
      </div>

      {/* 안내 */}
      <div className="mt-6 bg-cyan-500/10 border border-cyan-500/20 rounded-xl p-4">
        <h3 className="font-semibold text-cyan-300 mb-2">💡 사용 안내</h3>
        <ul className="text-sm text-slate-300 space-y-1">
          <li>• 텍스트만, 이미지만, 또는 둘 다 입력 가능합니다</li>
          <li>• 이미지 업로드 시 GPT Vision으로 텍스트를 추출합니다</li>
          <li>• 카테고리에 맞는 톤앤매너로 홍보문구가 생성됩니다</li>
          <li>• 생성된 문구는 복사하여 카카오톡 채널에 바로 사용하세요</li>
        </ul>
      </div>
    </div>
  );
}

export default KakaoPromo;
