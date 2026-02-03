import { useCallback, useState } from "react";
import { FileText, Upload, X, FileType, Presentation } from "lucide-react";
import { cn } from "@/lib/utils";
import { validateFile, formatFileSize, getFileIcon } from "@/utils/validation";
import { ALLOWED_EXTENSIONS } from "@/types";

interface FileUploadProps {
  /** Label displayed above the upload zone */
  label: string;
  /** Description text for the upload zone */
  description: string;
  /** Currently selected file */
  file: File | null;
  /** Callback when file is selected or cleared */
  onFileChange: (file: File | null) => void;
  /** Whether the upload is disabled */
  disabled?: boolean;
}

/**
 * File upload component with drag-and-drop support
 */
export function FileUpload({
  label,
  description,
  file,
  onFileChange,
  disabled = false,
}: FileUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = useCallback(
    (selectedFile: File) => {
      const validation = validateFile(selectedFile);
      
      if (!validation.valid) {
        setError(validation.error || "Invalid file");
        return;
      }
      
      setError(null);
      onFileChange(selectedFile);
    },
    [onFileChange]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragOver(false);
      
      if (disabled) return;
      
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile) {
        handleFile(droppedFile);
      }
    },
    [disabled, handleFile]
  );

  const handleDragOver = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      if (!disabled) {
        setIsDragOver(true);
      }
    },
    [disabled]
  );

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selectedFile = e.target.files?.[0];
      if (selectedFile) {
        handleFile(selectedFile);
      }
    },
    [handleFile]
  );

  const handleClear = useCallback(() => {
    setError(null);
    onFileChange(null);
  }, [onFileChange]);

  const FileIcon = file
    ? getFileIcon(file.name) === "pdf"
      ? FileType
      : getFileIcon(file.name) === "ppt"
      ? Presentation
      : FileText
    : Upload;

  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium text-foreground">
        {label}
      </label>
      
      <div
        className={cn(
          "upload-zone cursor-pointer",
          isDragOver && "drag-over",
          file && "has-file",
          disabled && "opacity-50 cursor-not-allowed"
        )}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => !disabled && document.getElementById(`file-input-${label}`)?.click()}
      >
        <input
          id={`file-input-${label}`}
          type="file"
          accept={ALLOWED_EXTENSIONS.join(",")}
          onChange={handleInputChange}
          disabled={disabled}
          className="hidden"
        />
        
        {file ? (
          <div className="flex items-center gap-4 w-full">
            <div className="flex-shrink-0 w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
              <FileIcon className="w-6 h-6 text-primary" />
            </div>
            
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate">
                {file.name}
              </p>
              <p className="text-xs text-muted-foreground">
                {formatFileSize(file.size)}
              </p>
            </div>
            
            {!disabled && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handleClear();
                }}
                className="flex-shrink-0 p-2 rounded-lg hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                aria-label="Remove file"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        ) : (
          <>
            <div className="w-12 h-12 rounded-full bg-secondary flex items-center justify-center">
              <Upload className="w-5 h-5 text-muted-foreground" />
            </div>
            
            <div className="text-center">
              <p className="text-sm text-foreground">
                <span className="text-primary font-medium">Click to upload</span>
                {" "}or drag and drop
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {description}
              </p>
            </div>
            
            <p className="text-xs text-muted-foreground">
              PDF, DOCX, or PPTX (max 50MB)
            </p>
          </>
        )}
      </div>
      
      {error && (
        <p className="text-sm text-destructive flex items-center gap-2">
          <span className="w-1 h-1 rounded-full bg-destructive" />
          {error}
        </p>
      )}
    </div>
  );
}
