import { useState } from "react";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, FileText, Download, ChevronDown, ChevronUp } from "lucide-react";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface ReferenceDocument {
  순번: number;
  유사도점수: string;
  문서ID: string;
  내용미리보기: string;
  전체내용: string;
}

export default function PressReleasePage() {
  // 입력 필드
  const [title, setTitle] = useState("");
  const [department, setDepartment] = useState("");
  const [manager, setManager] = useState("");
  const [paragraphCount, setParagraphCount] = useState("4개이상");
  const [length, setLength] = useState("중간");
  const [keyPoints, setKeyPoints] = useState("");
  const [additionalRequest, setAdditionalRequest] = useState("");

  // 결과
  const [result, setResult] = useState("");
  const [references, setReferences] = useState<ReferenceDocument[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  // UI 상태
  const [expandedRefs, setExpandedRefs] = useState<Set<number>>(new Set());
  const [showReferences, setShowReferences] = useState(false);

  const toggleReference = (index: number) => {
    const newExpanded = new Set(expandedRefs);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedRefs(newExpanded);
  };

  const handleGenerate = async () => {
    if (!title.trim() || !keyPoints.trim()) {
      setError("제목과 내용 포인트는 필수입니다");
      return;
    }

    setIsLoading(true);
    setError("");
    setResult("");
    setReferences([]);

    try {
      const response = await fetch(`${API_BASE_URL}/api/press-release/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title,
          department,
          manager,
          paragraph_count: paragraphCount,
          length,
          key_points: keyPoints,
          additional_request: additionalRequest,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "보도자료 생성 실패");
      }

      if (data.success) {
        setResult(data.content);
        setReferences(data.references || []);
      } else {
        setError(data.error || "보도자료 생성 중 오류 발생");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "네트워크 오류");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownload = () => {
    const blob = new Blob([result], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `보도자료_${new Date().toISOString().split("T")[0]}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <main className="max-w-7xl mx-auto px-6 py-12">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground mb-2">
            📰 GPT 기반 보도자료 자동 생성기
          </h1>
          <p className="text-muted-foreground">
            충주시의 보도자료 8,000여건을 기반으로 학습한 AI가 충주시 스타일의 보도자료를 자동으로 생성합니다
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 입력 폼 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="w-5 h-5" />
                보도자료 정보 입력
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="title">제목 *</Label>
                <Input
                  id="title"
                  placeholder="보도자료 제목을 입력하세요"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="department">담당 부서명</Label>
                  <Input
                    id="department"
                    placeholder="예: 자치행정과"
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="manager">관리자 이름</Label>
                  <Input
                    id="manager"
                    placeholder="예: 김태균"
                    value={manager}
                    onChange={(e) => setManager(e.target.value)}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="paragraphCount">문단 수</Label>
                  <select
                    id="paragraphCount"
                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm"
                    value={paragraphCount}
                    onChange={(e) => setParagraphCount(e.target.value)}
                  >
                    <option value="4개이상">4개 이상</option>
                    <option value="3개">3개</option>
                    <option value="2개">2개</option>
                    <option value="1개">1개</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="length">보도자료 길이</Label>
                  <select
                    id="length"
                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-sm"
                    value={length}
                    onChange={(e) => setLength(e.target.value)}
                  >
                    <option value="길게">길게</option>
                    <option value="중간">중간</option>
                    <option value="짧게">짧게</option>
                  </select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="keyPoints">내용 포인트 (한 줄에 하나씩) *</Label>
                <Textarea
                  id="keyPoints"
                  placeholder="포함될 핵심 내용을 한 줄씩 입력하세요"
                  rows={6}
                  value={keyPoints}
                  onChange={(e) => setKeyPoints(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="additionalRequest">기타 요청사항 (선택)</Label>
                <Textarea
                  id="additionalRequest"
                  placeholder="추가 요청사항이 있으면 입력하세요"
                  rows={3}
                  value={additionalRequest}
                  onChange={(e) => setAdditionalRequest(e.target.value)}
                />
              </div>

              <Button
                onClick={handleGenerate}
                disabled={isLoading}
                className="w-full"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    생성 중...
                  </>
                ) : (
                  "🚀 보도자료 생성하기"
                )}
              </Button>

              {error && (
                <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md text-destructive text-sm">
                  {error}
                </div>
              )}
            </CardContent>
          </Card>

          {/* 결과 출력 */}
          <div className="space-y-4">
            {/* 참조 문서 정보 */}
            {references.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle 
                    className="flex items-center justify-between cursor-pointer"
                    onClick={() => setShowReferences(!showReferences)}
                  >
                    <span>📋 참조한 보도자료 정보 ({references.length}개)</span>
                    {showReferences ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                  </CardTitle>
                </CardHeader>
                {showReferences && (
                  <CardContent className="space-y-4">
                    {references.map((ref) => (
                      <div key={ref.순번} className="border-b border-border pb-4 last:border-0">
                        <div className="space-y-2">
                          <div className="font-semibold text-sm">
                            {ref.순번}번째 참조 문서
                          </div>
                          <div className="text-xs text-muted-foreground space-y-1">
                            <div>유사도 점수: {ref.유사도점수}</div>
                            <div>문서 ID: {ref.문서ID}</div>
                            <div className="pt-1">
                              <span className="font-medium">내용 미리보기:</span>
                              <p className="mt-1 text-foreground/80">{ref.내용미리보기}</p>
                            </div>
                          </div>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => toggleReference(ref.순번)}
                            className="w-full mt-2"
                          >
                            {expandedRefs.has(ref.순번) ? (
                              <>
                                <ChevronUp className="w-4 h-4 mr-1" />
                                전체 내용 접기
                              </>
                            ) : (
                              <>
                                <ChevronDown className="w-4 h-4 mr-1" />
                                전체 내용 보기
                              </>
                            )}
                          </Button>
                          {expandedRefs.has(ref.순번) && (
                            <div className="mt-2 p-3 bg-muted/30 rounded text-xs">
                              <pre className="whitespace-pre-wrap font-sans">
                                {ref.전체내용}
                              </pre>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </CardContent>
                )}
              </Card>
            )}

            {/* 생성된 보도자료 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>📄 생성된 보도자료</span>
                  {result && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleDownload}
                    >
                      <Download className="w-4 h-4 mr-2" />
                      다운로드
                    </Button>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {result ? (
                  <div className="bg-muted/50 p-4 rounded-md border border-border">
                    <pre className="whitespace-pre-wrap text-sm font-sans text-foreground leading-relaxed">
                      {result}
                    </pre>
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-96 text-muted-foreground">
                    보도자료가 여기에 표시됩니다
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}