import { useState, ChangeEvent } from "react";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, FileText, Download, Upload, Languages } from "lucide-react";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const LANGUAGES = {
  "한국어": "KO",
  "영어 (미국)": "EN-US",
  "영어 (영국)": "EN-GB",
  "일본어": "JA",
  "중국어 (간체)": "ZH-HANS",
  "중국어 (번체)": "ZH-HANT",
  "베트남어": "VI",
  "태국어": "TH",
  "러시아어": "RU",
  "아랍어": "AR",
  "히브리어": "HE",
  "스페인어": "ES",
  "독일어": "DE",
  "프랑스어": "FR",
  "인도네시아어": "ID",
  "이탈리아어": "IT",
  "포르투갈어": "PT",
  "포르투갈어 (브라질)": "PT-BR",
  "폴란드어": "PL",
  "네덜란드어": "NL",
  "터키어": "TR",
  "우크라이나어": "UK"
};

const FONT_MODES = {
  "전체 통일(맑은 고딕)": "all",
  "한글만 맑은 고딕": "hangul_only",
  "변경 안 함": "none"
};

export default function TranslatorPage() {
  const [file, setFile] = useState<File | null>(null);
  const [targetLang, setTargetLang] = useState("EN-US");
  const [fontMode, setFontMode] = useState("all");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [translatedFile, setTranslatedFile] = useState<{
    blob: Blob;
    filename: string;
  } | null>(null);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      
      // HWPX 파일만 허용
      if (!selectedFile.name.endsWith('.hwpx')) {
        setError("HWPX 파일만 업로드 가능합니다");
        setFile(null);
        return;
      }
      
      setFile(selectedFile);
      setError("");
      setTranslatedFile(null);
    }
  };

  const handleTranslate = async () => {
    if (!file) {
      setError("파일을 선택해주세요");
      return;
    }

    setIsLoading(true);
    setError("");
    setTranslatedFile(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('target_lang', targetLang);
      formData.append('font_mode', fontMode);

      const response = await fetch(`${API_BASE_URL}/api/translator/translate-hwpx`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "번역 실패");
      }

      // Blob으로 파일 받기
      const blob = await response.blob();
      const originalName = file.name.replace('.hwpx', '');
      const filename = `${originalName}_translated_${targetLang}.hwpx`;

      setTranslatedFile({ blob, filename });
    } catch (err) {
      setError(err instanceof Error ? err.message : "네트워크 오류");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownload = () => {
    if (!translatedFile) return;

    const url = URL.createObjectURL(translatedFile.blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = translatedFile.filename;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <main className="max-w-4xl mx-auto px-6 py-12">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground mb-2 flex items-center gap-2">
            <Languages className="w-8 h-8" />
            다국어 번역기 (HWPX)
          </h1>
          <p className="text-muted-foreground">
            한글문서(HWPX) 파일을 DeepL + GPT로 번역하며, 문서 구조와 서식을 완벽하게 보존합니다
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6">
          {/* 입력 폼 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="w-5 h-5" />
                번역 설정
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* 파일 업로드 */}
              <div className="space-y-2">
                <Label htmlFor="file">HWPX 파일 업로드 *</Label>
                <Input
                  id="file"
                  type="file"
                  accept=".hwpx"
                  onChange={handleFileChange}
                  className="cursor-pointer"
                />
                {file && (
                  <div className="text-sm text-muted-foreground flex items-center gap-2 mt-2">
                    <FileText className="w-4 h-4" />
                    선택된 파일: {file.name}
                  </div>
                )}
              </div>

              {/* 언어 선택 */}
              <div className="space-y-2">
                <Label htmlFor="targetLang">번역할 언어 *</Label>
                <select
                  id="targetLang"
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm"
                  value={targetLang}
                  onChange={(e) => setTargetLang(e.target.value)}
                >
                  {Object.entries(LANGUAGES).map(([name, code]) => (
                    <option key={code} value={code}>
                      {name}
                    </option>
                  ))}
                </select>
              </div>

              {/* 폰트 모드 */}
              <div className="space-y-2">
                <Label htmlFor="fontMode">폰트 보정 모드</Label>
                <select
                  id="fontMode"
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm"
                  value={fontMode}
                  onChange={(e) => setFontMode(e.target.value)}
                >
                  {Object.entries(FONT_MODES).map(([name, code]) => (
                    <option key={code} value={code}>
                      {name}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-muted-foreground">
                  번역 후 폰트를 맑은 고딕으로 통일하여 가독성을 높입니다
                </p>
              </div>

              {/* 파일 정보 */}
              {file && (
                <div className="grid grid-cols-3 gap-4 p-4 bg-muted/50 rounded-md">
                  <div>
                    <div className="text-xs text-muted-foreground">파일 형식</div>
                    <div className="text-sm font-medium">📄 HWPX</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">대상 언어</div>
                    <div className="text-sm font-medium">
                      {Object.entries(LANGUAGES).find(([_, code]) => code === targetLang)?.[0]}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">폰트 모드</div>
                    <div className="text-sm font-medium">
                      {Object.entries(FONT_MODES).find(([_, code]) => code === fontMode)?.[0]}
                    </div>
                  </div>
                </div>
              )}

              {/* 번역 버튼 */}
              <Button
                onClick={handleTranslate}
                disabled={isLoading || !file}
                className="w-full"
                size="lg"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    번역 중...
                  </>
                ) : (
                  <>
                    <Languages className="w-4 h-4 mr-2" />
                    번역 시작
                  </>
                )}
              </Button>

              {/* 에러 메시지 */}
              {error && (
                <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md text-destructive text-sm">
                  {error}
                </div>
              )}

              {/* 성공 메시지 + 다운로드 */}
              {translatedFile && (
                <div className="space-y-3">
                  <div className="p-3 bg-green-500/10 border border-green-500/20 rounded-md text-green-600 text-sm">
                    ✅ 번역 완료!
                  </div>
                  
                  <Button
                    onClick={handleDownload}
                    className="w-full"
                    variant="default"
                    size="lg"
                  >
                    <Download className="w-4 h-4 mr-2" />
                    번역된 HWPX 다운로드
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* 적용 내용 설명 */}
          <Card>
            <CardHeader>
              <CardTitle>📊 번역 적용 내용</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div>
                <div className="font-semibold mb-1">🔹 2단계 번역 시스템</div>
                <div className="text-muted-foreground">
                  1차: DeepL API로 고품질 번역<br />
                  2차: GPT-4o-mini로 한글 잔여 처리
                </div>
              </div>
              
              <div>
                <div className="font-semibold mb-1">🔹 문서 구조 완벽 보존</div>
                <div className="text-muted-foreground">
                  • fwSpace 공백 구조 유지<br />
                  • 특수 공백 정규화 (NO-BREAK SPACE 등)<br />
                  • 다중 공백 → 1칸 통일
                </div>
              </div>
              
              <div>
                <div className="font-semibold mb-1">🔹 자동 서식 보정</div>
                <div className="text-muted-foreground">
                  • 자간(charSpacing) 0으로 통일<br />
                  • 정렬(JUSTIFY → LEFT) 보정<br />
                  • 폰트 선택적 통일 (맑은 고딕)
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>

      <Footer />
    </div>
  );
}