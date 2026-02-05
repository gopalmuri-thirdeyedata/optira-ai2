import { useState, useCallback } from "react";
import { processDocuments } from "@/services/api";
import { AppState, ProcessingStep } from "@/types";

interface UseDocumentProcessorResult {
  /** Current application state */
  state: AppState;
  /** Current processing step (when state is 'processing') */
  currentStep: ProcessingStep;
  /** Download URL for the processed document */
  downloadUrl: string | null;
  /** Error message (when state is 'error') */
  error: string | null;
  /** Start processing the documents */
  processFiles: (normalFile: File, targetFile: File, outputFormat?: "docx" | "pdf") => Promise<void>;
  /** Reset to initial state */
  reset: () => void;
}

/**
 * Hook to manage document processing state and API calls
 */
export function useDocumentProcessor(): UseDocumentProcessorResult {
  const [state, setState] = useState<AppState>("idle");
  const [currentStep, setCurrentStep] = useState<ProcessingStep>("uploading");
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const processFiles = useCallback(async (normalFile: File, targetFile: File, outputFormat: "docx" | "pdf" = "docx") => {
    setState("processing");
    setCurrentStep("uploading");
    setError(null);
    setDownloadUrl(null);

    // Simulate progress through steps
    // In a real implementation, this could be driven by WebSocket updates from the backend
    const steps: ProcessingStep[] = ["uploading", "analyzing", "formatting", "generating"];
    
    let stepIndex = 0;
    const progressInterval = setInterval(() => {
      stepIndex++;
      if (stepIndex < steps.length) {
        setCurrentStep(steps[stepIndex]);
      }
    }, 2000);

    try {
      const result = await processDocuments(normalFile, targetFile, outputFormat);
      
      clearInterval(progressInterval);
      
      if (result.success && result.downloadUrl) {
        setCurrentStep("generating");
        // Small delay to show completion
        await new Promise((resolve) => setTimeout(resolve, 500));
        setDownloadUrl(result.downloadUrl);
        setState("success");
      } else {
        setError(result.error || "Failed to process documents");
        setState("error");
      }
    } catch (err) {
      clearInterval(progressInterval);
      setError(err instanceof Error ? err.message : "An unexpected error occurred");
      setState("error");
    }
  }, []);

  const reset = useCallback(() => {
    setState("idle");
    setCurrentStep("uploading");
    setDownloadUrl(null);
    setError(null);
  }, []);

  return {
    state,
    currentStep,
    downloadUrl,
    error,
    processFiles,
    reset,
  };
}
