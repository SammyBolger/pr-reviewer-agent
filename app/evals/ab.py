import asyncio
import statistics

from app.evals.dataset import CASES
from app.evals.judge import judge
from app.evals.prompt_variants import VARIANTS
from app.evals.schemas import Judgement
from app.llm.client import review_pr


async def _one(case, variant_name: str, system_prompt: str) -> Judgement:
    outcome = await review_pr(
        diff=case.diff,
        repo="local/eval",
        number=0,
        title=case.title,
        author="eval-runner",
        system_override=system_prompt,
    )
    return await judge(case, outcome.review)


async def run_ab(names: list[str] | None = None) -> None:
    variants = {n: VARIANTS[n] for n in names} if names else VARIANTS
    print(f"A/B eval: {len(variants)} variants x {len(CASES)} cases\n")

    scores: dict[str, list[Judgement]] = {name: [] for name in variants}

    for name, prompt in variants.items():
        print(f"--- {name} ---")
        for case in CASES:
            print(f"  {case.id}...", end=" ", flush=True)
            j = await _one(case, name, prompt)
            scores[name].append(j)
            print(j.verdict)

    print("\n=== Comparison ===")
    print("| variant       | detection | false-pos | usefulness | calibration | pass rate |")
    print("|---------------|-----------|-----------|------------|-------------|-----------|")
    for name, judgements in scores.items():
        det = statistics.mean(j.detection_score for j in judgements)
        fp = statistics.mean(j.false_positive_score for j in judgements)
        use = statistics.mean(j.usefulness_score for j in judgements)
        cal = statistics.mean(j.calibration_score for j in judgements)
        passes = sum(1 for j in judgements if j.verdict == "pass")
        print(
            f"| {name:<13} | {det:.2f}/5    | {fp:.2f}/5    | {use:.2f}/5     | "
            f"{cal:.2f}/5      | {passes}/{len(judgements)}       |"
        )


if __name__ == "__main__":
    asyncio.run(run_ab())
