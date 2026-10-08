interface Step {
  label: string;
  detail: string;
}

interface Props {
  steps: Step[];
  currentStep: number;
}

/** Vertical list of steps (horizontal and compact on small screens). */
export default function StepWizard({ steps, currentStep }: Props) {
  return (
    <ol className="flex md:flex-col gap-2 md:gap-0" aria-label="Verification steps">
      {steps.map((step, i) => {
        const done = i < currentStep;
        const active = i === currentStep;
        return (
          <li
            key={step.label}
            aria-current={active ? "step" : undefined}
            className="flex-1 md:flex-none flex md:gap-3 md:pb-6 md:last:pb-0 relative"
          >
            {/* connector line between steps (desktop) */}
            {i < steps.length - 1 && (
              <span
                className={`hidden md:block absolute left-[0.8rem] top-7 bottom-0 w-px ${done ? "bg-ink" : "bg-rule"}`}
                aria-hidden="true"
              />
            )}
            <span
              className={`hidden md:flex shrink-0 w-[1.625rem] h-[1.625rem] rounded-full items-center justify-center text-[0.8125rem] font-bold figures border-2 ${
                done
                  ? "bg-ink border-ink text-paper"
                  : active
                  ? "bg-paper border-seal text-seal"
                  : "bg-paper border-rule-strong text-ink-faint"
              }`}
              aria-hidden="true"
            >
              {done ? (
                <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3.5 8.5l3 3 6-7" />
                </svg>
              ) : (
                i + 1
              )}
            </span>

            {/* mobile: a bar per step */}
            <span className="md:hidden w-full">
              <span className={`block h-1 rounded-full ${done || active ? "bg-seal" : "bg-rule"}`} aria-hidden="true" />
              <span className={`block mt-1.5 text-xs ${active ? "text-ink font-semibold" : "text-ink-faint"}`}>{step.label}</span>
            </span>

            <span className="hidden md:block">
              <span className={`block leading-[1.625rem] ${active ? "font-semibold text-ink" : done ? "text-ink" : "text-ink-faint"}`}>
                {step.label}
                {done && <span className="sr-only"> (done)</span>}
              </span>
              <span className="block text-sm text-ink-faint">{step.detail}</span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}
