import { Download, RefreshCw, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ResultDownloadProps {
  /** URL to download the processed file */
  downloadUrl: string;
  /** Callback when user wants to start over */
  onReset: () => void;
}

/**
 * Success state component with download button and reset option
 */
export function ResultDownload({ downloadUrl, onReset }: ResultDownloadProps) {
  const handleDownload = () => {
    // Open download URL in new tab
    window.open(downloadUrl, "_blank");
  };

  return (
    <div className="glass-card rounded-xl p-8 text-center space-y-6">
      <div className="flex justify-center">
        <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
          <CheckCircle2 className="w-8 h-8 text-primary" />
        </div>
      </div>
      
      <div className="space-y-2">
        <h3 className="text-xl font-semibold text-foreground">
          Document Ready!
        </h3>
        <p className="text-muted-foreground text-sm max-w-sm mx-auto">
          Your styled document has been generated successfully. 
          Click below to download your file.
        </p>
      </div>
      
      <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
        <Button
          onClick={handleDownload}
          size="lg"
          className="w-full sm:w-auto gap-2"
        >
          <Download className="w-4 h-4" />
          Download Document
        </Button>
        
        <Button
          onClick={onReset}
          variant="outline"
          size="lg"
          className="w-full sm:w-auto gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          Process Another
        </Button>
      </div>
    </div>
  );
}
