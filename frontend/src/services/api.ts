import { ProcessResponse } from "@/types";

/**
 * Base API URL - update this to match your backend
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Process documents by uploading to the backend
 * 
 * @param normalFile - The raw/unstructured document
 * @param targetFile - The well-formatted reference document (template with {{PLACEHOLDERS}})
 * @param onProgress - Optional callback for progress updates
 * @returns Promise with download URL or error
 */
export async function processDocuments(
  normalFile: File,
  targetFile: File,
  outputFormat: "docx" | "pdf" = "docx",
  onProgress?: (step: "uploading" | "analyzing" | "formatting" | "generating") => void
): Promise<ProcessResponse> {
  const formData = new FormData();
  formData.append("normal_file", normalFile);
  formData.append("target_file", targetFile);
  formData.append("output_format", outputFormat);

  try {
    // Notify upload started
    onProgress?.("uploading");

    const response = await fetch(`${API_BASE_URL}/api/process`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Server error: ${response.status}`);
    }

    const data = await response.json();
    
    // Backend returns relative URL like /api/download/{job_id}/{filename}
    // Construct full URL
    const downloadPath = data.download_url || data.downloadUrl;
    const fullDownloadUrl = downloadPath 
      ? `${API_BASE_URL}${downloadPath}` 
      : undefined;
    
    return {
      success: true,
      downloadUrl: fullDownloadUrl,
    };
  } catch (error) {
    console.error("API Error:", error);
    return {
      success: false,
      error: error instanceof Error ? error.message : "An unexpected error occurred",
    };
  }
}

/**
 * Download the processed file
 * 
 * @param downloadUrl - Full URL to download the file from
 * @param filename - Optional custom filename
 */
export async function downloadFile(downloadUrl: string, filename?: string): Promise<void> {
  try {
    const response = await fetch(downloadUrl);
    
    if (!response.ok) {
      throw new Error("Failed to download file");
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename || "styled-document.docx";
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  } catch (error) {
    console.error("Download Error:", error);
    throw error;
  }
}

