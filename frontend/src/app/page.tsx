import Link from "next/link";
import type { Metadata } from "next";
import VerificationDocument from "@/components/VerificationDocument";

export const metadata: Metadata = {
  title: "TrustGuard — identity verification",
  description:
    "Checks a selfie, a voice sample and typing behaviour to decide whether a person is real — with every check, score and rule shown.",
};

const BENCHMARK_URL = "https://github.com/Ashmeet-21/trustguard/blob/master/benchmarks/RESULTS.md";
const COMPARISON_URL = "https://github.com/Ashmeet-21/trustguard/blob/master/benchmarks/MODEL_COMPARISON.md";

const CHECKS = [
  {
    name: "Face is not AI-generated",
    how: "Vision Transformer trained on images from thousands of generators",
    catches: "AI-generated and AI-edited faces",
    misses: "Face swaps onto real photos",
    weight: 30,
  },
  {
    name: "A live person",
    how: "Six image tests: face geometry, skin texture, screen moiré, colour, edges, sharpness",
    catches: "Printed photos and photos of screens",
    misses: "High-quality masks",
    weight: 25,
  },
  {
    name: "Human voice",
    how: "Spectral analysis of a phrase read aloud",
    catches: "Flat, monotone synthetic speech",
    misses: "Modern voice clones",
    weight: 25,
  },
  {
    name: "Human typing",
    how: "Time between keys, rhythm, mouse speed and path",
    catches: "Scripts and bots filling in forms",
    misses: "A person typing on someone else’s behalf",
    weight: 20,
  },
];

const STEPS = [
  {
    title: "Each check scores 0–100",
    body: "A check that can’t run is recorded as not run. It is never filled in with a guess.",
  },
  {
    title: "Scores are weighted into a trust score",
    body: "Face 30%, liveness 25%, voice 25%, typing 20%. If a check is missing, its weight is shared among the others.",
  },
  {
    title: "Rules set the decision",
    body: "Fail below 40, on any critical risk, or when two checks are flagged. Review below 70 or when one check is flagged. Otherwise pass.",
  },
  {
    title: "Quality gates can only make it stricter",
    body: "A photo already used in another session fails. Too few checks, or checks that disagree, turn a pass into a review. A crashed check can never produce a pass.",
  },
  {
    title: "Everything is written to an audit record",
    body: "Each score, rule and gate behind the decision is stored and can be read back by the account that ran it.",
  },
];

export default function Home() {
  return (
    <>
      {/* Hero */}
      <section className="max-w-6xl mx-auto px-6 pt-14 pb-20 md:pt-20 grid lg:grid-cols-[1fr_minmax(0,34rem)] gap-12 lg:gap-16 items-center">
        <div className="max-w-xl">
          <h1 className="text-[2.5rem] md:text-[3.25rem] leading-[1.05] font-bold tracking-[-0.02em] text-ink">
            Check that a person is real before you let them in.
          </h1>
          <p className="mt-6 text-lg text-ink-soft leading-relaxed">
            TrustGuard checks a selfie, a short voice recording and the way someone types. Four
            independent checks feed one decision — pass, review or fail — and every score and rule
            behind it is shown.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/verify" className="btn">
              Start a verification
            </Link>
            <a href="#accuracy" className="btn btn-quiet">
              See how accurate it is
            </a>
          </div>
        </div>

        <VerificationDocument
          specimen
          decision="PASS"
          trustScore={84}
          holder="Specimen holder"
          sessionId="00000000"
          issuedAt={new Date(2026, 9, 8)}
          checks={[
            { key: "image_agent", score: 92, risk: "LOW" },
            { key: "video_agent", score: 86, risk: "LOW" },
            { key: "voice_agent", score: 81, risk: "LOW" },
            { key: "behavior_agent", score: 74, risk: "MEDIUM" },
          ]}
        />
      </section>

      {/* Checks */}
      <section className="border-t border-rule bg-sheet">
        <div className="max-w-6xl mx-auto px-6 py-16 md:py-20">
          <h2 className="text-[1.75rem] md:text-[2rem] font-bold tracking-[-0.01em] text-ink max-w-2xl">
            Four checks, each looking for a different attack
          </h2>
          <p className="mt-3 text-ink-soft max-w-2xl">
            No single check is reliable on its own, so each one is listed with what it misses as well
            as what it catches.
          </p>

          {/* Small screens: one block per check */}
          <ul className="mt-8 md:hidden border-t-2 border-ink">
            {CHECKS.map((c) => (
              <li key={c.name} className="py-5 border-b border-rule">
                <div className="flex justify-between gap-4">
                  <h3 className="font-semibold text-ink">{c.name}</h3>
                  <span className="font-semibold figures">{c.weight}%</span>
                </div>
                <p className="mt-1 text-ink-soft text-[0.9375rem]">{c.how}</p>
                <dl className="mt-3 grid grid-cols-[6.5rem_1fr] gap-x-3 gap-y-1 text-[0.9375rem]">
                  <dt className="text-ink-faint">Catches</dt>
                  <dd className="text-ink">{c.catches}</dd>
                  <dt className="text-ink-faint">Doesn’t catch</dt>
                  <dd className="text-ink-soft">{c.misses}</dd>
                </dl>
              </li>
            ))}
          </ul>

          <div className="mt-10 hidden md:block">
            <table className="w-full text-left text-[0.9375rem]">
              <thead>
                <tr className="border-b-2 border-ink text-ink">
                  <th scope="col" className="py-3 pr-6 font-semibold w-[22%]">Check</th>
                  <th scope="col" className="py-3 pr-6 font-semibold w-[30%]">How it works</th>
                  <th scope="col" className="py-3 pr-6 font-semibold">Catches</th>
                  <th scope="col" className="py-3 pr-6 font-semibold">Doesn’t catch</th>
                  <th scope="col" className="py-3 font-semibold text-right">Weight</th>
                </tr>
              </thead>
              <tbody>
                {CHECKS.map((c) => (
                  <tr key={c.name} className="border-b border-rule align-top">
                    <th scope="row" className="py-4 pr-6 font-semibold text-ink">{c.name}</th>
                    <td className="py-4 pr-6 text-ink-soft">{c.how}</td>
                    <td className="py-4 pr-6 text-ink">{c.catches}</td>
                    <td className="py-4 pr-6 text-ink-soft">{c.misses}</td>
                    <td className="py-4 text-right font-semibold figures">{c.weight}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Decision process */}
      <section className="border-t border-rule">
        <div className="max-w-6xl mx-auto px-6 py-16 md:py-20 grid md:grid-cols-[18rem_1fr] gap-10 md:gap-16">
          <div>
            <h2 className="text-[1.75rem] md:text-[2rem] font-bold tracking-[-0.01em] text-ink">
              How a decision is made
            </h2>
            <p className="mt-3 text-ink-soft">
              The same inputs always give the same decision, and the reasons are part of the result.
            </p>
          </div>

          <ol className="border-l-2 border-ink">
            {STEPS.map((s, i) => (
              <li key={s.title} className="relative pl-8 pb-8 last:pb-0">
                <span
                  className="absolute -left-[0.9rem] top-0 w-7 h-7 rounded-full bg-paper border-2 border-ink text-sm font-bold flex items-center justify-center figures"
                  aria-hidden="true"
                >
                  {i + 1}
                </span>
                <h3 className="font-semibold text-ink text-lg leading-7">{s.title}</h3>
                <p className="mt-1 text-ink-soft max-w-[60ch]">{s.body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Accuracy */}
      <section id="accuracy" className="border-t border-rule bg-sheet scroll-mt-4">
        <div className="max-w-6xl mx-auto px-6 py-16 md:py-20 grid lg:grid-cols-2 gap-10 lg:gap-16">
          <div>
            <h2 className="text-[1.75rem] md:text-[2rem] font-bold tracking-[-0.01em] text-ink">
              Measured, not claimed
            </h2>
            <div className="mt-4 space-y-4 text-ink-soft max-w-[60ch]">
              <p>
                The first face model advertised 99% accuracy — on its own training data. On 199 faces
                from image generators it had never seen, it caught 1 fake out of 99.
              </p>
              <p>
                TrustGuard now uses the best of eight models tested on exactly the same images,
                compressed to run inside the server so photos never leave it. It is much better,
                and still not perfect: face swaps, where most of the photo is real,
                are almost never caught. That is why the other three checks exist.
              </p>
            </div>
            <p className="mt-6 flex flex-wrap gap-x-6 gap-y-2">
              <a className="link" href={BENCHMARK_URL} target="_blank" rel="noopener noreferrer">
                Full benchmark results
              </a>
              <a className="link" href={COMPARISON_URL} target="_blank" rel="noopener noreferrer">
                All eight models compared
              </a>
            </p>
          </div>

          <div className="self-start">
            <table className="w-full text-left text-[0.9375rem]">
              <caption className="text-left text-sm text-ink-faint pb-3">
                DeepFakeFace dataset, 100 real and 99 fake faces, not used in training.
              </caption>
              <thead>
                <tr className="border-b-2 border-ink">
                  <th scope="col" className="py-3 pr-4 font-semibold">Face check</th>
                  <th scope="col" className="py-3 pr-4 font-semibold text-right">First model</th>
                  <th scope="col" className="py-3 font-semibold text-right">Current model</th>
                </tr>
              </thead>
              <tbody className="figures">
                <tr className="border-b border-rule">
                  <th scope="row" className="py-3 pr-4 font-normal text-ink">Fakes caught</th>
                  <td className="py-3 pr-4 text-right text-ink-soft">1%</td>
                  <td className="py-3 text-right font-semibold">65%</td>
                </tr>
                <tr className="border-b border-rule">
                  <th scope="row" className="py-3 pr-4 font-normal text-ink">Real people wrongly flagged</th>
                  <td className="py-3 pr-4 text-right text-ink-soft">1%</td>
                  <td className="py-3 text-right font-semibold">0%</td>
                </tr>
                <tr className="border-b border-rule">
                  <th scope="row" className="py-3 pr-4 font-normal text-ink">
                    AUC <span className="text-ink-faint">(0.5 is guessing)</span>
                  </th>
                  <td className="py-3 pr-4 text-right text-ink-soft">0.41</td>
                  <td className="py-3 text-right font-semibold">0.87</td>
                </tr>
                <tr className="border-b border-rule">
                  <th scope="row" className="py-3 pr-4 font-normal text-ink">AI-generated faces caught</th>
                  <td className="py-3 pr-4 text-right text-ink-soft">3%</td>
                  <td className="py-3 text-right font-semibold">100%</td>
                </tr>
                <tr className="border-b border-rule">
                  <th scope="row" className="py-3 pr-4 font-normal text-ink">Face swaps caught</th>
                  <td className="py-3 pr-4 text-right text-ink-soft">0%</td>
                  <td className="py-3 text-right font-semibold text-fail">6%</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Closing */}
      <section className="border-t border-rule">
        <div className="max-w-6xl mx-auto px-6 py-16 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <h2 className="text-2xl font-bold text-ink">Try it with your own camera</h2>
            <p className="mt-1 text-ink-soft">It takes about a minute: one selfie, one sentence read aloud, one sentence typed.</p>
          </div>
          <Link href="/verify" className="btn self-start md:self-auto">
            Start a verification
          </Link>
        </div>
      </section>
    </>
  );
}
