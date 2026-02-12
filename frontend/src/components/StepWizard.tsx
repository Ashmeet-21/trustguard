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
    <div className="flex items-center justify-center gap-2 mb-8">
      {steps.map((step, i) => {
        const isActive = i === currentStep;
        const isDone = i < currentStep;

        return (
          <div key={i} className="flex items-center gap-2">
            <div
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-all ${
                isActive
                  ? "gradient-bg text-white font-medium"
                  : isDone
                  ? "bg-[#0d2e1a] text-[#4ade80] border border-[#166534]"
                  : "bg-[#111] text-[#555] border border-[#222]"
              }`}
            >
              <span>{isDone ? "✓" : step.icon}</span>
              <span className="hidden sm:inline">{step.label}</span>
            </div>
            {i < steps.length - 1 && (
              <div className={`w-8 h-0.5 ${isDone ? "bg-[#4ade80]" : "bg-[#222]"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}
