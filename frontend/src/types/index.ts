/**
 * Supported file types for document upload
 */
export const ALLOWED_FILE_TYPES = {
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
} as const;

export const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".pptx"];

/**
 * Maximum file size in bytes (50MB)
 */
export const MAX_FILE_SIZE = 50 * 1024 * 1024;

/**
 * Processing status steps
 */
export type ProcessingStep = "uploading" | "analyzing" | "formatting" | "generating";

export const PROCESSING_STEPS: { key: ProcessingStep; label: string }[] = [
  { key: "uploading", label: "Uploading documents" },
  { key: "analyzing", label: "Analyzing structure" },
  { key: "formatting", label: "Applying style transfer" },
  { key: "generating", label: "Generating output" },
];

/**
 * Application state
 */
export type AppState = "idle" | "processing" | "success" | "error";

/**
 * API response types
 */
export interface ProcessResponse {
  success: boolean;
  downloadUrl?: string;
  error?: string;
}

/**
 * File validation result
 */
export interface ValidationResult {
  valid: boolean;
  error?: string;
}
