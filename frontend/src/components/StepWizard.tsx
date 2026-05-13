"use client";

interface Step {
  label: string;
  icon: string;
}

interface Props {
  steps: Step[];
  currentStep: number;
}

export default function StepWizard({ steps, currentStep }: Props) {
  return (
    <div className="flex items-center justify-center gap-1.5 mb-10">
      {steps.map((step, i) => {
        const isActive = i === currentStep;
        const isDone = i < currentStep;

        return (
          <div key={i} className="flex items-center gap-1.5">
            <div
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-[12px] transition-all duration-300 ${
                isActive
                  ? "bg-white/[0.08] text-white/80 border border-white/[0.1] font-medium"
                  : isDone
                  ? "bg-[#4ade80]/[0.05] text-[#4ade80]/60 border border-[#4ade80]/10"
                  : "text-white/15 border border-transparent"
              }`}
            >
              <span className="font-mono text-[10px]">
                {isDone ? (
                  <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M3.5 8.5l3 3 6-7" />
                  </svg>
                ) : (
                  step.icon
                )}
              </span>
              <span className="hidden sm:inline">{step.label}</span>
            </div>
            {i < steps.length - 1 && (
              <div className={`w-6 h-px transition-colors duration-300 ${isDone ? "bg-[#4ade80]/20" : "bg-white/[0.04]"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}
