import { useState, useCallback } from "react";
import { ArrowRight, Sparkles, FileOutput, Layers } from "lucide-react";
import { Button } from "@/components/ui/button";
import { FileUpload } from "@/components/FileUpload";
import { StatusIndicator } from "@/components/StatusIndicator";
import { ResultDownload } from "@/components/ResultDownload";
import { ErrorState } from "@/components/ErrorState";
import { useDocumentProcessor } from "@/hooks/useDocumentProcessor";

/**
 * Main page component for the document style transfer platform
 */
const Index = () => {
  const [normalFile, setNormalFile] = useState<File | null>(null);
  const [targetFile, setTargetFile] = useState<File | null>(null);
  
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
      processFiles(normalFile, targetFile);
    }
  }, [normalFile, targetFile, processFiles]);

  const handleReset = useCallback(() => {
    setNormalFile(null);
    setTargetFile(null);
    reset();
  }, [reset]);

  const canSubmit = normalFile !== null && targetFile !== null && state === "idle";
  const isProcessing = state === "processing";

  return (
    <div className="min-h-screen bg-background">
      {/* Background decoration */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl animate-float" />
        <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-primary/3 rounded-full blur-3xl animate-float" style={{ animationDelay: "-3s" }} />
      </div>
      
      <div className="relative container max-w-4xl mx-auto px-4 py-12 md:py-20">
        {/* Header */}
        <header className="text-center mb-12 md:mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-secondary/50 border border-border mb-6">
            <Sparkles className="w-4 h-4 text-primary" />
            <span className="text-sm text-muted-foreground">AI-Powered Style Transfer</span>
          </div>
          
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight mb-4">
            <span className="gradient-text">StyleSync</span>
            <span className="text-foreground"> Documents</span>
          </h1>
          
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Transform any document to match the style and formatting of your reference. 
            Upload your raw content and target template — we'll handle the rest.
          </p>
        </header>

        {/* Features */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-12">
          {[
            { icon: FileOutput, title: "Multiple Formats", desc: "PDF, DOCX, PPTX" },
            { icon: Layers, title: "Smart Analysis", desc: "AI-powered structure detection" },
            { icon: Sparkles, title: "Instant Results", desc: "Fast processing" },
          ].map((feature) => (
            <div key={feature.title} className="flex items-center gap-3 p-4 rounded-lg bg-secondary/30 border border-border/50">
              <feature.icon className="w-5 h-5 text-primary flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-foreground">{feature.title}</p>
                <p className="text-xs text-muted-foreground">{feature.desc}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Main Content */}
        <main className="space-y-8">
          {state === "idle" && (
            <>
              {/* Upload Section */}
              <div className="grid md:grid-cols-2 gap-6">
                <FileUpload
                  label="Source Document"
                  description="Your raw content that needs formatting"
                  file={normalFile}
                  onFileChange={setNormalFile}
                  disabled={isProcessing}
                />
                
                <FileUpload
                  label="Style Template"
                  description="Reference document with desired formatting"
                  file={targetFile}
                  onFileChange={setTargetFile}
                  disabled={isProcessing}
                />
              </div>

              {/* Submit Button */}
              <div className="flex justify-center pt-4">
                <Button
                  onClick={handleSubmit}
                  disabled={!canSubmit}
                  size="lg"
                  variant="gradient"
                  className="gap-2 min-w-[240px]"
                >
                  Generate Styled Document
                  <ArrowRight className="w-4 h-4" />
                </Button>
              </div>
              
              {!canSubmit && (normalFile || targetFile) && (
                <p className="text-center text-sm text-muted-foreground">
                  Please upload both documents to continue
                </p>
              )}
            </>
          )}

          {state === "processing" && (
            <StatusIndicator currentStep={currentStep} />
          )}

          {state === "success" && downloadUrl && (
            <ResultDownload downloadUrl={downloadUrl} onReset={handleReset} />
          )}

          {state === "error" && error && (
            <ErrorState message={error} onRetry={handleReset} />
          )}
        </main>

        {/* Footer */}
        <footer className="mt-16 text-center">
          <p className="text-xs text-muted-foreground">
            Supported formats: PDF, DOCX, PPTX • Max file size: 50MB
          </p>
        </footer>
      </div>
    </div>
  );
};

export default Index;
