import asyncio
import statistics

from app.evals.dataset import CASES
from app.evals.judge import judge
from app.evals.schemas import Judgement
from app.llm.client import review_pr
from app.review.schemas import Review


async def _one(case) -> tuple[Review, Judgement]:
    outcome = await review_pr(
        diff=case.diff,
        repo="local/eval",
        number=0,
        title=case.title,
        author="eval-runner",
    )
    j = await judge(case, outcome.review)
    return outcome.review, j


def _row(name: str, r: Review, j: Judgement) -> str:
    return (
        f"| {name:<20} | {j.detection_score}/5 | {j.false_positive_score}/5 | "
        f"{j.usefulness_score}/5 | {j.calibration_score}/5 | "
        f"{r.confidence:.2f} | {len(r.concerns)} | {j.verdict} |"
    )


async def main():
    print("Running eval on", len(CASES), "cases...\n")

    results: list[tuple[str, Review, Judgement]] = []
    for case in CASES:
        print(f"  running {case.id}...")
        review, j = await _one(case)
        results.append((case.id, review, j))

    print()
    print("| case                 | det | fp | use | cal | conf | #con | verdict |")
    print("|----------------------|-----|----|-----|-----|------|------|---------|")
    for name, r, j in results:
        print(_row(name, r, j))

    print("\n=== Aggregate ===")
    print(f"Mean detection:      {statistics.mean(j.detection_score for _, _, j in results):.2f} / 5")
    print(f"Mean false-positive: {statistics.mean(j.false_positive_score for _, _, j in results):.2f} / 5")
    print(f"Mean usefulness:     {statistics.mean(j.usefulness_score for _, _, j in results):.2f} / 5")
    print(f"Mean calibration:    {statistics.mean(j.calibration_score for _, _, j in results):.2f} / 5")
    passes = sum(1 for _, _, j in results if j.verdict == "pass")
    print(f"Pass rate:           {passes}/{len(results)}")

    print("\n=== Notes ===")
    for name, _, j in results:
        print(f"[{name}] {j.verdict}: {j.notes}")
        if j.missed_issues:
            print(f"  missed: {j.missed_issues}")
        if j.invalid_concerns:
            print(f"  invalid: {j.invalid_concerns}")


if __name__ == "__main__":
    asyncio.run(main())
