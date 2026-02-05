import React, { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, CheckCircle, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface FileUploadProps {
  label: string;
  description: string;
  file: File | null;
  onFileChange: (file: File | null) => void;
  disabled?: boolean;
}

export const FileUpload: React.FC<FileUploadProps> = ({
  label,
  description,
  file,
  onFileChange,
  disabled = false,
}) => {
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0) {
        onFileChange(acceptedFiles[0]);
      }
    },
    [onFileChange]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [
        ".docx",
      ],
    },
    maxFiles: 1,
    disabled,
  });

  const removeFile = (e: React.MouseEvent) => {
    e.stopPropagation();
    onFileChange(null);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-sm font-semibold text-foreground">{label}</label>
        {file && (
          <span className="text-xs text-secondary flex items-center gap-1">
            <CheckCircle className="w-3 h-3" />
            Ready
          </span>
        )}
      </div>
      
      <div
        {...getRootProps()}
        className={cn(
          "relative group cursor-pointer transition-all duration-200 ease-in-out",
          "border-2 border-dashed rounded-lg h-full min-h-[128px] flex flex-col items-center justify-center p-4",
          "bg-muted/30 hover:bg-muted/60",
          isDragActive ? "border-primary bg-primary/5" : "border-border",
          file ? "border-primary/50 bg-primary/5" : "hover:border-primary/50",
          disabled && "opacity-50 cursor-not-allowed hover:bg-muted/30 hover:border-border"
        )}
      >
        <input {...getInputProps()} />
        
        {file ? (
          <div className="w-full h-full flex items-center gap-3 animate-in fade-in zoom-in-95 duration-200">
            <div className="h-10 w-10 rounded-lg bg-background flex items-center justify-center border border-border shrink-0 shadow-sm">
              <FileText className="w-5 h-5 text-primary" />
            </div>
            <div className="flex-1 min-w-0 text-left">
              <p className="text-sm font-medium text-foreground truncate">
                {file.name}
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">
                {(file.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
            <button
              onClick={removeFile}
              className="p-1.5 rounded-full hover:bg-destructive/10 hover:text-destructive text-muted-foreground transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="text-center space-y-2">
            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center mx-auto group-hover:scale-110 transition-transform duration-200">
              <Upload className="w-4 h-4 text-primary" />
            </div>
            <div className="space-y-0.5">
              <p className="text-sm font-medium text-foreground">
                <span className="text-primary hover:underline">Click to upload</span>
                <span className="hidden sm:inline"> or drag and drop</span>
              </p>
              <p className="text-xs text-muted-foreground">{description}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
