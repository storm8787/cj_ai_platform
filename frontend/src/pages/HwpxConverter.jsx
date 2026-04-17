import { useState, useCallback, useRef } from "react";
import {
  FileText, Upload, Download, Eye, Copy, Check,
  Loader2, AlertCircle, Image, Table, Type,
  RefreshCw, X, FileDown
} from "lucide-react";
import api from "../services/api";

export default function HwpxConverter() {
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [converting, setConverting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [imageMode, setImageMode] = useState("inline");
  const [showPreview, setShowPreview] = useState(true);
  const [copied, setCopied] = useState(false);
  const fileInputRef = useRef(null);

  var HWPX_EXT = ".hwpx";
  var MD_EXT = ".md";

  var handleDragOver = useCallback(function(e) {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  var handleDragLeave = useCallback(function(e) {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  var handleDrop = useCallback(function(e) {
    e.preventDefault();
    setIsDragging(false);
    var droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.name.toLowerCase().endsWith(HWPX_EXT)) {
      setFile(droppedFile);
      setError(null);
      setResult(null);
    } else {
      setError("HWPX \ud30c\uc77c\ub9cc \uc9c0\uc6d0\ud569\ub2c8\ub2e4.");
    }
  }, []);

  var handleFileSelect = function(e) {
    var selectedFile = e.target.files[0];
    if (selectedFile) {
      if (selectedFile.name.toLowerCase().endsWith(HWPX_EXT)) {
        setFile(selectedFile);
        setError(null);
        setResult(null);
      } else {
        setError("HWPX \ud30c\uc77c\ub9cc \uc9c0\uc6d0\ud569\ub2c8\ub2e4.");
      }
    }
  };

  var handleConvert = async function() {
    if (!file) return;
    setConverting(true);
    setError(null);
    setResult(null);
    try {
      var formData = new FormData();
      formData.append("file", file);
      formData.append("image_mode", imageMode);
      var response = await api.post("/api/hwpx-converter/convert", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(response.data);
    } catch (err) {
      var detail = (err.response && err.response.data && err.response.data.detail) || "\ubcc0\ud658 \uc911 \uc624\ub958\uac00 \ubc1c\uc0dd\ud588\uc2b5\ub2c8\ub2e4.";
      setError(detail);
    } finally {
      setConverting(false);
    }
  };

  var handleDownload = function() {
    if (!result || !result.markdown) return;
    var blob = new Blob([result.markdown], { type: "text/markdown;charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    var dlName = file && file.name ? file.name.replace(/\.hwpx$/i, MD_EXT) : "converted.md";
    a.download = dlName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  var handleCopy = async function() {
    if (!result || !result.markdown) return;
    try {
      await navigator.clipboard.writeText(result.markdown);
      setCopied(true);
      setTimeout(function() { setCopied(false); }, 2000);
    } catch (e) {
      var textarea = document.createElement("textarea");
      textarea.value = result.markdown;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(function() { setCopied(false); }, 2000);
    }
  };

  var handleReset = function() {
    setFile(null);
    setResult(null);
    setError(null);
    setCopied(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  var formatSize = function(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  var dropzoneClass = "relative border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-200 ";
  if (isDragging) {
    dropzoneClass += "border-cyan-400 bg-cyan-500/10";
  } else if (file) {
    dropzoneClass += "border-green-500/50 bg-green-500/5";
  } else {
    dropzoneClass += "border-slate-700 hover:border-slate-500 bg-slate-900/50";
  }

  var convertBtnClass = "w-full py-3 rounded-xl font-medium text-sm transition-all flex items-center justify-center gap-2 ";
  if (!file || converting) {
    convertBtnClass += "bg-slate-800 text-gray-500 cursor-not-allowed";
  } else {
    convertBtnClass += "bg-cyan-600 hover:bg-cyan-500 text-white";
  }

  var inlineOptClass = "flex items-center gap-2 px-4 py-2 rounded-lg cursor-pointer transition-all ";
  inlineOptClass += imageMode === "inline"
    ? "bg-cyan-500/10 border border-cyan-500/30 text-cyan-300"
    : "bg-slate-800 border border-slate-700 text-gray-400 hover:text-gray-300";

  var separateOptClass = "flex items-center gap-2 px-4 py-2 rounded-lg cursor-pointer transition-all ";
  separateOptClass += imageMode === "separate"
    ? "bg-cyan-500/10 border border-cyan-500/30 text-cyan-300"
    : "bg-slate-800 border border-slate-700 text-gray-400 hover:text-gray-300";

  var previewBtnClass = "px-4 py-2.5 rounded-xl font-medium text-sm transition-all flex items-center gap-2 border ";
  previewBtnClass += showPreview
    ? "bg-cyan-500/10 border-cyan-500/30 text-cyan-300"
    : "bg-slate-800 border-slate-700 text-gray-400 hover:text-gray-300";

  var mdFilename = file && file.name ? file.name.replace(/\.hwpx$/i, MD_EXT) : "output.md";
  var charCount = result && result.markdown ? result.markdown.length.toLocaleString() : "0";

  return (
    <div className="min-h-screen bg-slate-950 text-gray-200 p-4 md:p-8">
      <div className="max-w-5xl mx-auto">

        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-cyan-500/10 rounded-lg">
              <FileText className="w-6 h-6 text-cyan-400" />
            </div>
            <h1 className="text-2xl font-bold text-white">HWPX Markdown Converter</h1>
          </div>
          <p className="text-gray-400 ml-12">
            HWPX to Markdown. Supports text, tables, and images.
          </p>
        </div>

        {!result && (
          <div className="space-y-6">

            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={function() { fileInputRef.current && fileInputRef.current.click(); }}
              className={dropzoneClass}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".hwpx"
                onChange={handleFileSelect}
                className="hidden"
              />

              {file ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-center gap-2">
                    <FileText className="w-8 h-8 text-green-400" />
                    <div className="text-left">
                      <p className="text-white font-medium">{file.name}</p>
                      <p className="text-gray-400 text-sm">{formatSize(file.size)}</p>
                    </div>
                    <button
                      onClick={function(e) { e.stopPropagation(); handleReset(); }}
                      className="ml-4 p-1 hover:bg-slate-700 rounded-lg transition-colors"
                    >
                      <X className="w-4 h-4 text-gray-400" />
                    </button>
                  </div>
                  <p className="text-gray-500 text-sm">Click to select another file</p>
                </div>
              ) : (
                <div className="space-y-3">
                  <Upload className={"w-10 h-10 mx-auto " + (isDragging ? "text-cyan-400" : "text-gray-500")} />
                  <div>
                    <p className="text-gray-300">Drag HWPX file here or click to select</p>
                    <p className="text-gray-500 text-sm mt-1">Max 50MB</p>
                  </div>
                </div>
              )}
            </div>

            <div className="bg-slate-900/50 rounded-xl border border-slate-800 p-5">
              <h3 className="text-sm font-medium text-gray-300 mb-3">Options</h3>
              <div className="flex gap-4">
                <label className={inlineOptClass}>
                  <input
                    type="radio"
                    name="imageMode"
                    value="inline"
                    checked={imageMode === "inline"}
                    onChange={function(e) { setImageMode(e.target.value); }}
                    className="hidden"
                  />
                  <Image className="w-4 h-4" />
                  <span className="text-sm">Image Inline (Base64)</span>
                </label>
                <label className={separateOptClass}>
                  <input
                    type="radio"
                    name="imageMode"
                    value="separate"
                    checked={imageMode === "separate"}
                    onChange={function(e) { setImageMode(e.target.value); }}
                    className="hidden"
                  />
                  <FileDown className="w-4 h-4" />
                  <span className="text-sm">Image Separate Files</span>
                </label>
              </div>
              <p className="text-gray-500 text-xs mt-2">
                {imageMode === "inline"
                  ? "Images embedded as Base64 inside the Markdown file."
                  : "Images extracted as separate files. Smaller file size."
                }
              </p>
            </div>

            <button
              onClick={handleConvert}
              disabled={!file || converting}
              className={convertBtnClass}
            >
              {converting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Converting...</span>
                </>
              ) : (
                <>
                  <RefreshCw className="w-4 h-4" />
                  <span>Convert to Markdown</span>
                </>
              )}
            </button>
          </div>
        )}

        {error && (
          <div className="mt-4 flex items-start gap-3 p-4 bg-red-500/10 border border-red-500/20 rounded-xl">
            <AlertCircle className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-red-300 font-medium">Conversion Failed</p>
              <p className="text-red-400/80 text-sm mt-1">{error}</p>
            </div>
          </div>
        )}

        {result && (
          <div className="space-y-6">

            <div className="grid grid-cols-3 gap-4">
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 text-center">
                <Type className="w-5 h-5 text-cyan-400 mx-auto mb-1" />
                <p className="text-2xl font-bold text-white">{(result.stats && result.stats.paragraphs) || 0}</p>
                <p className="text-gray-500 text-xs">Paragraphs</p>
              </div>
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 text-center">
                <Table className="w-5 h-5 text-emerald-400 mx-auto mb-1" />
                <p className="text-2xl font-bold text-white">{(result.stats && result.stats.tables) || 0}</p>
                <p className="text-gray-500 text-xs">Tables</p>
              </div>
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 text-center">
                <Image className="w-5 h-5 text-purple-400 mx-auto mb-1" />
                <p className="text-2xl font-bold text-white">{(result.stats && result.stats.images) || 0}</p>
                <p className="text-gray-500 text-xs">Images</p>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleDownload}
                className="flex-1 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl font-medium text-sm transition-all flex items-center justify-center gap-2"
              >
                <Download className="w-4 h-4" />
                <span>.md Download</span>
              </button>
              <button
                onClick={handleCopy}
                className="flex-1 py-2.5 bg-slate-800 hover:bg-slate-700 text-gray-300 rounded-xl font-medium text-sm transition-all flex items-center justify-center gap-2 border border-slate-700"
              >
                {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
                <span>{copied ? "Copied!" : "Copy to Clipboard"}</span>
              </button>
              <button
                onClick={function() { setShowPreview(!showPreview); }}
                className={previewBtnClass}
              >
                <Eye className="w-4 h-4" />
                <span>Preview</span>
              </button>
              <button
                onClick={handleReset}
                className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-gray-400 rounded-xl text-sm transition-all border border-slate-700"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>

            <div className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-cyan-400" />
                  <span className="text-sm text-gray-300">{mdFilename}</span>
                </div>
                <span className="text-xs text-gray-500">{charCount + " chars"}</span>
              </div>

              <div className="max-h-[600px] overflow-y-auto">
                {showPreview ? (
                  <div
                    className="p-6 prose prose-invert prose-sm max-w-none prose-headings:text-white prose-p:text-gray-300 prose-strong:text-white prose-a:text-cyan-400 prose-table:border-slate-700 prose-th:text-gray-300 prose-td:text-gray-400 prose-td:border-slate-700 prose-th:border-slate-700"
                    dangerouslySetInnerHTML={{
                      __html: simpleMarkdownToHtml(result.markdown || "")
                    }}
                  />
                ) : (
                  <pre className="p-6 text-sm text-gray-300 whitespace-pre-wrap break-words font-mono leading-relaxed">
                    {result.markdown}
                  </pre>
                )}
              </div>
            </div>

            {imageMode === "separate" && result.images && result.images.length > 0 && (
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-5">
                <h3 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
                  <Image className="w-4 h-4 text-purple-400" />
                  <span>{"Extracted Images (" + result.images.length + ")"}</span>
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {result.images.map(function(img, idx) {
                    return (
                      <div key={idx} className="bg-slate-800 rounded-lg p-2 text-center">
                        <img
                          src={"data:" + img.mime + ";base64," + img.data}
                          alt={img.name}
                          className="w-full h-24 object-contain rounded mb-2"
                        />
                        <p className="text-xs text-gray-500 truncate">{img.name}</p>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}


function simpleMarkdownToHtml(md) {
  var html = md
    .replace(/```(\w*)\n([\s\S]*?)```/g, "<pre class=\"bg-slate-800 p-3 rounded-lg overflow-x-auto\"><code>$2</code></pre>")
    .replace(/^###### (.+)$/gm, "<h6>$1</h6>")
    .replace(/^##### (.+)$/gm, "<h5>$1</h5>")
    .replace(/^#### (.+)$/gm, "<h4>$1</h4>")
    .replace(/^### (.+)$/gm, "<h3>$1</h3>")
    .replace(/^## (.+)$/gm, "<h2>$1</h2>")
    .replace(/^# (.+)$/gm, "<h1>$1</h1>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, "<img src=\"$2\" alt=\"$1\" class=\"max-w-full rounded-lg my-2\" />")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, "<a href=\"$2\" class=\"text-cyan-400 hover:underline\">$1</a>")
    .replace(/^---$/gm, "<hr class=\"border-slate-700 my-4\" />")
    .replace(/\n\n/g, "</p><p>")
    .replace(/\n/g, "<br />");

  html = html.replace(
    /(\|.+\|\s*<br \/>)+/g,
    function(match) {
      var rows = match.split("<br />").filter(function(r) { return r.trim(); });
      if (rows.length < 2) return match;
      var tableHtml = "<table class=\"w-full border-collapse my-4\">";
      rows.forEach(function(row, idx) {
        var cells = row.split("|").filter(function(c) { return c.trim() !== ""; });
        if (cells.every(function(c) { return /^[\s\-:]+$/.test(c); })) return;
        var tag = idx === 0 ? "th" : "td";
        var rowClass = idx === 0 ? "bg-slate-800 text-gray-300" : "text-gray-400";
        tableHtml += "<tr class=\"" + rowClass + "\">";
        cells.forEach(function(cell) {
          tableHtml += "<" + tag + " class=\"border border-slate-700 px-3 py-2 text-sm\">" + cell.trim() + "</" + tag + ">";
        });
        tableHtml += "</tr>";
      });
      tableHtml += "</table>";
      return tableHtml;
    }
  );

  return "<p>" + html + "</p>";
}