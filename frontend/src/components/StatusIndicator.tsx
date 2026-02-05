import { Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { ProcessingStep, PROCESSING_STEPS } from "@/types";

interface StatusIndicatorProps {
  /** Current processing step */
  currentStep: ProcessingStep;
  /** Whether processing has completed */
  isComplete?: boolean;
}

/**
 * Visual indicator showing the current processing status
 */
export function StatusIndicator({ currentStep, isComplete = false }: StatusIndicatorProps) {
  const currentIndex = PROCESSING_STEPS.findIndex((s) => s.key === currentStep);

  return (
    <div className="glass-card rounded-xl p-6 space-y-4">
      <div className="flex items-center justify-center gap-3 mb-6">
        <div className="relative">
          {!isComplete && (
            <span className="pulse-ring" />
          )}
          <div className={cn(
            "relative w-10 h-10 rounded-full flex items-center justify-center transition-colors duration-300",
            isComplete ? "bg-primary" : "bg-primary/20"
          )}>
            {isComplete ? (
              <Check className="w-5 h-5 text-primary-foreground" />
            ) : (
              <Loader2 className="w-5 h-5 text-primary animate-spin" />
            )}
          </div>
        </div>
        
        <h3 className="text-lg font-medium text-foreground">
          {isComplete ? "Processing Complete" : "Processing Your Documents"}
        </h3>
      </div>
      
      <div className="space-y-3">
        {PROCESSING_STEPS.map((step, index) => {
          const isActive = step.key === currentStep && !isComplete;
          const isCompleted = index < currentIndex || isComplete;
          
          return (
            <div
              key={step.key}
              className={cn(
                "status-step",
                isActive && "active",
                isCompleted && "completed"
              )}
            >
              <div className={cn(
                "w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium transition-all duration-300",
                isCompleted
                  ? "bg-primary text-primary-foreground"
                  : isActive
                  ? "bg-primary/20 text-primary border border-primary"
                  : "bg-muted text-muted-foreground"
              )}>
                {isCompleted ? (
                  <Check className="w-3.5 h-3.5" />
                ) : (
                  index + 1
                )}
              </div>
              
              <span className={cn(
                "text-sm transition-colors duration-300",
                isActive && "font-medium"
              )}>
                {step.label}
              </span>
              
              {isActive && (
                <Loader2 className="w-4 h-4 text-primary animate-spin ml-auto" />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
