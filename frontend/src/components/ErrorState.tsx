import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ErrorStateProps {
  /** Error message to display */
  message: string;
  /** Callback when user wants to retry */
  onRetry: () => void;
}

/**
 * Error state component with retry option
 */
export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="glass-card rounded-xl p-8 text-center space-y-6">
      <div className="flex justify-center">
        <div className="w-16 h-16 rounded-full bg-destructive/10 flex items-center justify-center">
          <AlertTriangle className="w-8 h-8 text-destructive" />
        </div>
      </div>
      
      <div className="space-y-2">
        <h3 className="text-xl font-semibold text-foreground">
          Something Went Wrong
        </h3>
        <p className="text-muted-foreground text-sm max-w-sm mx-auto">
          {message}
        </p>
      </div>
      
      <Button
        onClick={onRetry}
        variant="outline"
        size="lg"
        className="gap-2"
      >
        <RefreshCw className="w-4 h-4" />
        Try Again
      </Button>
    </div>
  );
}
