/**
 * VerificationDocument — the result rendered as an identity-document data page:
 * photo, holder, decision, one reading per check, and a 2-line machine-readable zone (MRZ)
 * that encodes the same result, like the code strip at the bottom of a passport.
 */

export type Decision = "PASS" | "REVIEW" | "FAIL";

export interface DocumentCheck {
  key: string;            // image_agent, video_agent, voice_agent, behavior_agent
  score: number | null;   // 0-100, null = not run
  risk?: string;          // LOW / MEDIUM / HIGH / CRITICAL
}

interface Props {
  decision: Decision;
  trustScore: number;
  checks: DocumentCheck[];
  photoUrl?: string | null;
  holder?: string;
  sessionId?: string;
  issuedAt?: Date;
  specimen?: boolean;   // landing-page example
  animate?: boolean;    // print the MRZ in (results screen only)
}

const CHECK_INFO: Record<string, { label: string; code: string }> = {
  image_agent: { label: "Face is not AI-generated", code: "IMG" },
  video_agent: { label: "A live person, not a photo of one", code: "LIV" },
  voice_agent: { label: "Voice is human, not synthetic", code: "VOI" },
  behavior_agent: { label: "Typing is human, not scripted", code: "BEH" },
};

const DECISION_STYLE: Record<Decision, { word: string; color: string; meaning: string }> = {
  PASS: { word: "Pass", color: "var(--color-pass)", meaning: "Verified as a real person" },
  REVIEW: { word: "Review", color: "var(--color-review)", meaning: "Needs a person to review" },
  FAIL: { word: "Fail", color: "var(--color-fail)", meaning: "Not verified" },
};

const RISK_WORD: Record<string, string> = { LOW: "Low", MEDIUM: "Medium", HIGH: "High", CRITICAL: "Critical" };
const RISK_COLOR: Record<string, string> = {
  LOW: "var(--color-pass)",
  MEDIUM: "var(--color-review)",
  HIGH: "var(--color-fail)",
  CRITICAL: "var(--color-fail)",
};

// ── MRZ ──────────────────────────────────────────────────
const MRZ_WIDTH = 44; // passports use two lines of 44 characters

function mrzField(text: string): string {
  return text.toUpperCase().replace(/[^A-Z0-9]+/g, "<");
}

function mrzLine(text: string): string {
  return mrzField(text).padEnd(MRZ_WIDTH, "<").slice(0, MRZ_WIDTH);
}

export function buildMrz(p: Pick<Props, "decision" | "trustScore" | "checks" | "holder" | "sessionId" | "issuedAt">): [string, string] {
  const score = String(Math.round(p.trustScore)).padStart(3, "0");
  const line1 = mrzLine(`TGV<${p.decision}<<SCORE<${score}<<${p.holder || "ANONYMOUS"}`);

  const readings = ["image_agent", "video_agent", "voice_agent", "behavior_agent"].map((key) => {
    const c = p.checks.find((x) => x.key === key);
    const value = c && c.score !== null ? String(Math.round(c.score)).padStart(3, "0") : "<<<";
    return CHECK_INFO[key].code + value;
  });
  const d = p.issuedAt || new Date();
  const yymmdd = `${String(d.getFullYear()).slice(2)}${String(d.getMonth() + 1).padStart(2, "0")}${String(d.getDate()).padStart(2, "0")}`;
  const line2 = mrzLine(`${readings.join("<")}<<${(p.sessionId || "").replace(/-/g, "").slice(0, 8)}<<${yymmdd}`);
  return [line1, line2];
}

// ── Guilloche: the fine interlaced line pattern printed on banknotes and passports ──
function Guilloche() {
  const paths: string[] = [];
  for (let k = 0; k < 14; k++) {
    let d = "";
    for (let x = 0; x <= 600; x += 6) {
      const y = 18 + k * 13 + 7 * Math.sin(x / 23 + k * 0.7) + 3 * Math.sin(x / 9 - k);
      d += `${x === 0 ? "M" : "L"}${x},${y.toFixed(1)} `;
    }
    paths.push(d);
  }
  return (
    <svg
      className="absolute inset-0 w-full h-full pointer-events-none"
      viewBox="0 0 600 210"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      {paths.map((d, i) => (
        <path key={i} d={d} fill="none" stroke="var(--color-guilloche)" strokeWidth="0.5" opacity="0.45" />
      ))}
    </svg>
  );
}

function PortraitPlaceholder() {
  return (
    <svg viewBox="0 0 90 110" className="w-full h-full" aria-hidden="true">
      <rect width="90" height="110" fill="#e4e9e6" />
      <circle cx="45" cy="42" r="17" fill="#c3ccc8" />
      <path d="M12 110c2-24 16-36 33-36s31 12 33 36z" fill="#c3ccc8" />
    </svg>
  );
}

export default function VerificationDocument(props: Props) {
  const { decision, trustScore, checks, photoUrl, holder, sessionId, issuedAt, specimen, animate } = props;
  const style = DECISION_STYLE[decision];
  const [mrz1, mrz2] = buildMrz(props);
  const issued = (issuedAt || new Date()).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });

  return (
    <article className="sheet relative overflow-hidden" aria-label="Verification record">
      {/* Header band with guilloche */}
      <div className="relative border-b border-rule px-5 sm:px-6 py-3 flex items-center justify-between gap-4 bg-[#f1f4f2]">
        <Guilloche />
        <p className="relative font-semibold text-ink">Verification record</p>
        <p className="relative text-sm text-ink-soft figures">
          {specimen ? "Specimen" : <>No. <span className="font-mono">{(sessionId || "").slice(0, 8)}</span></>}
        </p>
      </div>

      {/* Identity block */}
      <div className="px-5 sm:px-6 pt-5 pb-4 grid grid-cols-[5.5rem_1fr] sm:grid-cols-[6.5rem_1fr_auto] gap-x-5 gap-y-4 items-start">
        <div className="aspect-[9/11] rounded-[3px] overflow-hidden border border-rule bg-[#e4e9e6] row-span-2 sm:row-span-1">
          {photoUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={photoUrl} alt="Submitted selfie" className="w-full h-full object-cover" />
          ) : (
            <PortraitPlaceholder />
          )}
        </div>

        <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm min-w-0">
          <div className="col-span-2">
            <dt className="text-ink-faint">Holder</dt>
            <dd className="text-ink font-medium truncate">{holder || "Anonymous"}</dd>
          </div>
          <div>
            <dt className="text-ink-faint">Trust score</dt>
            <dd className="text-ink font-semibold text-lg leading-tight figures">
              {Math.round(trustScore)}
              <span className="text-ink-faint font-normal text-sm"> / 100</span>
            </dd>
          </div>
          <div>
            <dt className="text-ink-faint">Issued</dt>
            <dd className="text-ink figures">{issued}</dd>
          </div>
        </dl>

        {/* Decision — set like an ink stamp */}
        <div
          className="col-span-2 sm:col-span-1 justify-self-start sm:justify-self-end self-center px-4 py-2 border-2 rounded-[3px] text-center -rotate-2"
          style={{ color: style.color, borderColor: style.color, boxShadow: `inset 0 0 0 2px var(--color-sheet), inset 0 0 0 3px ${style.color}` }}
        >
          <p className="text-2xl font-bold leading-none tracking-wide">{style.word}</p>
          <p className="text-xs mt-1 font-medium">{style.meaning}</p>
        </div>
      </div>

      {/* Readings */}
      <table className="w-full text-sm border-t border-rule">
        <caption className="sr-only">Result of each check</caption>
        <thead>
          <tr className="text-left text-ink-faint">
            <th scope="col" className="font-normal px-5 sm:px-6 pt-3 pb-1">Check</th>
            <th scope="col" className="font-normal pt-3 pb-1 w-16 text-right">Score</th>
            <th scope="col" className="font-normal pt-3 pb-1 pl-5 pr-5 sm:pr-6 w-24 sm:w-40">Risk</th>
          </tr>
        </thead>
        <tbody>
          {["image_agent", "video_agent", "voice_agent", "behavior_agent"].map((key) => {
            const c = checks.find((x) => x.key === key);
            const ran = c && c.score !== null;
            return (
              <tr key={key} className="border-t border-rule/70">
                <td className="px-5 sm:px-6 py-2.5 text-ink">{CHECK_INFO[key].label}</td>
                <td className="py-2.5 text-right font-semibold figures">{ran ? Math.round(c!.score!) : "—"}</td>
                <td className="py-2.5 pl-5 pr-5 sm:pr-6">
                  {ran ? (
                    <span className="flex items-center gap-2">
                      <span className="hidden sm:block flex-1 h-1.5 bg-rule/60 rounded-full overflow-hidden">
                        <span
                          className="block h-full rounded-full"
                          style={{ width: `${Math.max(3, c!.score!)}%`, background: RISK_COLOR[c!.risk || ""] || "var(--color-ink-soft)" }}
                        />
                      </span>
                      <span style={{ color: RISK_COLOR[c!.risk || ""] }}>{RISK_WORD[c!.risk || ""] || c!.risk}</span>
                    </span>
                  ) : (
                    <span className="text-ink-faint">Not run</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* Machine-readable zone */}
      <div className="border-t border-rule bg-[#f1f4f2] px-5 sm:px-6 py-3">
        <p className={`mrz ${animate ? "mrz-print" : ""}`} aria-label="Machine-readable summary">
          <span>{mrz1}</span>
          {"\n"}
          <span>{mrz2}</span>
        </p>
      </div>
    </article>
  );
}
