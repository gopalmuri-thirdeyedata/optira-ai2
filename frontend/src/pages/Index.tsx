import { useState, useCallback } from "react";
import { FileText, FileType, ArrowRight, Sparkles, Check, ChevronDown, Download, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { FileUpload } from "@/components/FileUpload";
import { StatusIndicator } from "@/components/StatusIndicator";
import { useDocumentProcessor } from "@/hooks/useDocumentProcessor";

const Index = () => {
  const [normalFile, setNormalFile] = useState<File | null>(null);
  const [targetFile, setTargetFile] = useState<File | null>(null);
  const [outputFormat, setOutputFormat] = useState<"docx" | "pdf">("docx");

  const {
    state,
    currentStep,
    downloadUrl,
    error,
    processFiles,
    reset,
  } = useDocumentProcessor();

  const handleSubmit = useCallback(() => {
    if (normalFile && targetFile) {
      processFiles(normalFile, targetFile, outputFormat);
    }
  }, [normalFile, targetFile, outputFormat, processFiles]);

  const handleReset = useCallback(() => {
    setNormalFile(null);
    setTargetFile(null);
    reset();
  }, [reset]);

  const canSubmit = normalFile !== null && targetFile !== null && state === "idle";
  const isProcessing = state === "processing";

  return (
    <div className="min-h-screen flex flex-col bg-background font-sans">
      {/* 1. Header */}
      <header className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container px-6 h-16 flex items-center mx-auto max-w-[1400px]">
          <div className="flex items-center gap-3">
            <img 
              src="/thirdeye-logo.webp" 
              alt="ThirdEye Data" 
              className="h-8 object-contain"
            />
            <div className="h-6 w-px mt-3 bg-border" />
            <span className="font-semibold tracking-tight text-lg mt-3.5">Format Hub</span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 container px-6 py-8 mx-auto max-w-[1400px] flex flex-col gap-10">
        
        {/* 2. Project Title & Info */}
        <section className="space-y-4 max-w-2xl mx-auto text-center">
          <div className="inline-flex items-center justify-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-semibold uppercase tracking-wide">
            <Sparkles className="w-3 h-3" />
            AI-Powered Transformation
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-foreground tracking-tight">
            Thirdeyedata <span className="text-primary">Format Hub</span>
          </h1>
          <p className="text-lg text-muted-foreground leading-relaxed">
            Standardize your documents instantly. Upload your content and a template to generate perfectly formatted reports, proposals, and presentations that match your corporate identity.
          </p>
        </section>

        {/* 3. Grid Layout (3 Columns) */}
        <section className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
          
          {/* Column 1: Source Upload */}
          <div className="bg-card rounded-xl border border-border shadow-sm p-5 flex flex-col gap-3">
            <div className="flex items-center justify-between mb-1">
              <h3 className="font-semibold text-foreground">1. Source Document</h3>
              <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">Raw Content</span>
            </div>
            <div className="flex-1 min-h-[140px]">
              <FileUpload
                label="Raw File"
                description="Upload the document containing your content"
                file={normalFile}
                onFileChange={setNormalFile}
                disabled={isProcessing}
              />
            </div>
          </div>

          {/* Column 2: Target Upload */}
          <div className="bg-card rounded-xl border border-border shadow-sm p-5 flex flex-col gap-3">
            <div className="flex items-center justify-between mb-1">
              <h3 className="font-semibold text-foreground">2. Style Template</h3>
              <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">Formatting</span>
            </div>
            <div className="flex-1 min-h-[140px]">
              <FileUpload
                label="Template File"
                description="Upload the document with desired styles"
                file={targetFile}
                onFileChange={setTargetFile}
                disabled={isProcessing}
              />
            </div>
          </div>

            {/* Column 3: Format & Action */}
          <div className="bg-card rounded-xl border border-border shadow-sm p-5 flex flex-col justify-between gap-5 relative overflow-hidden">
            {/* Background decoration */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-full blur-2xl -mr-10 -mt-10 pointer-events-none"></div>

            <div className="space-y-4 relative z-10">
              <div className="flex items-center justify-between mb-1">
                <h3 className="font-semibold text-foreground">3. Output Options</h3>
                <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">Generate</span>
              </div>
              
              <div className="space-y-2">
                <label className="text-sm font-medium text-foreground">Output Format</label>
                <div className="relative">
                  <select
                    value={outputFormat}
                    onChange={(e) => setOutputFormat(e.target.value as "docx" | "pdf")}
                    disabled={isProcessing}
                    className="w-full appearance-none bg-background border border-border hover:border-primary/50 rounded-lg px-4 py-3 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all cursor-pointer disabled:opacity-50"
                  >
                    <option value="docx">Word Document (.docx)</option>
                    <option value="pdf">PDF Document (.pdf)</option>
                  </select>
                  <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-muted-foreground">
                    <ChevronDown className="w-4 h-4" />
                  </div>
                </div>
              </div>
            </div>

            <div className="relative z-10 pt-4 border-t border-border mt-auto">
              {state === "idle" ? (
                <Button
                  onClick={handleSubmit}
                  disabled={!canSubmit}
                  className="w-full h-12 text-base font-semibold shadow-sm hover:shadow-md transition-all bg-primary hover:bg-primary/90"
                >
                  Generate Document
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              ) : state === "processing" ? (
                <div className="bg-muted/30 rounded-lg p-4 text-center">
                  <StatusIndicator currentStep={currentStep} />
                </div>
              ) : state === "success" && downloadUrl ? (
                 <div className="flex flex-col gap-3">
                    <a 
                      href={downloadUrl}
                      className="inline-flex items-center justify-center w-full h-12 rounded-md bg-primary text-primary-foreground font-semibold shadow-sm hover:bg-primary/90 transition-all"
                    >
                      <Download className="w-4 h-4 mr-2" />
                      Download {outputFormat.toUpperCase()}
                    </a>
                    <Button variant="ghost" size="sm" onClick={handleReset} className="w-full text-muted-foreground hover:text-foreground">
                      Start New Conversion
                    </Button>
                 </div>
              ) : (
                <div className="bg-destructive/5 border border-destructive/20 rounded-lg p-3 flex flex-col gap-2">
                  <div className="flex items-center gap-2 text-destructive text-sm font-medium">
                    <AlertCircle className="w-4 h-4" />
                    <span>Processing Failed</span>
                  </div>
                  <p className="text-xs text-muted-foreground">{error || "An unknown error occurred"}</p>
                   <Button variant="outline" size="sm" onClick={handleReset} className="w-full bg-white">
                      Try Again
                    </Button>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* 4. More Info */}
        <section className="grid md:grid-cols-2 gap-12 pt-8 border-t border-border">
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-foreground">Data Privacy & Security</h3>
            <p className="text-muted-foreground text-sm leading-relaxed">
              We prioritize the protection of your intellectual property. All documents are processed in an encrypted environment and are permanently deleted from our servers immediately upon completion. We do not store, train on, or share your proprietary data.
            </p>
          </div>
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-foreground">Supported Formats</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-start gap-3">
                <FileText className="w-5 h-5 text-primary mt-0.5" />
                <div>
                  <p className="text-sm font-medium">Input Format</p>
                  <p className="text-xs text-muted-foreground">DOCX (Word Document)</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <FileType className="w-5 h-5 text-secondary mt-0.5" />
                <div>
                  <p className="text-sm font-medium">Output Format</p>
                  <p className="text-xs text-muted-foreground">DOCX (Word) & PDF</p>
                </div>
              </div>
            </div>
            
            <div className="bg-amber-50 border border-amber-200 rounded-md p-3 mt-2">
               <div className="flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
                  <p className="text-xs text-amber-700 leading-snug">
                    <span className="font-semibold">Disclaimer:</span> While our AI strives for high accuracy, it may occasionally make formatting errors. We recommend reviewing the generated document.
                  </p>
               </div>
            </div>
            <p className="text-xs text-muted-foreground pt-1">Maximum file size: 50MB per document</p>
          </div>
        </section>

      </main>

      {/* 5. Footer */}
      <footer className="border-t border-border bg-muted/30 mt-auto">
        <div className="container px-6 py-8 mx-auto max-w-[1400px]">
           <div className="flex items-center gap-2">
              <img src="/thirdeye-logo.webp" alt="ThirdEye Data" className="h-6 opacity-50 grayscale hover:grayscale-0 hover:opacity-100 transition-all" />
              <span className="text-sm text-muted-foreground mt-2">© 2026 ThirdEye Data Inc.</span>
           </div>
        </div>
      </footer>
    </div>
  );
};

export default Index;
