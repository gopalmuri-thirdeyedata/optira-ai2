import { ALLOWED_EXTENSIONS, MAX_FILE_SIZE, ValidationResult } from "@/types";

/**
 * Validate a file for upload
 * 
 * @param file - The file to validate
 * @returns Validation result with error message if invalid
 */
export function validateFile(file: File): ValidationResult {
  // Check file size
  if (file.size > MAX_FILE_SIZE) {
    const maxSizeMB = MAX_FILE_SIZE / (1024 * 1024);
    return {
      valid: false,
      error: `File size exceeds ${maxSizeMB}MB limit`,
    };
  }

  // Check file extension
  const extension = `.${file.name.split(".").pop()?.toLowerCase()}`;
  if (!ALLOWED_EXTENSIONS.includes(extension)) {
    return {
      valid: false,
      error: `Invalid file type. Allowed: ${ALLOWED_EXTENSIONS.join(", ")}`,
    };
  }

  return { valid: true };
}

/**
 * Format file size for display
 * 
 * @param bytes - File size in bytes
 * @returns Formatted string (e.g., "2.5 MB")
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 Bytes";
  
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

/**
 * Get file icon based on extension
 * 
 * @param filename - Name of the file
 * @returns Icon identifier
 */
export function getFileIcon(filename: string): "pdf" | "doc" | "ppt" {
  const extension = filename.split(".").pop()?.toLowerCase();
  
  switch (extension) {
    case "pdf":
      return "pdf";
    case "docx":
      return "doc";
    case "pptx":
      return "ppt";
    default:
      return "doc";
  }
}
