from dataclasses import dataclass
from datetime import datetime
from time import perf_counter
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

from models import MODEL_REGISTRY, build_model
from pricing import cost_usd
from prompts import EXTRACT_REQUIREMENTS_PROMPT, SCORE_MATCH_PROMPT, TAILOR_CV_PROMPT
from schemas import JobLabel, MatchScore, RequirementsExtraction, RunRecord, TailoredCV

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.messages import AIMessage

from pathlib import Path

HERE = Path(__file__).parent

JDS = HERE / "datasets" / "jds"
PROFILE = HERE / "datasets" / "cvs" / "profile.json"
JOBS = HERE / "datasets" / "jobs.jsonl"
RESULTS = HERE / "results"


@dataclass(frozen=True)
class TaskSpec:
    prompt: str
    schema: type[BaseModel]
    needs_profile: bool


TASK_REGISTRY: dict[str, TaskSpec] = {
    "extract_requirements": TaskSpec(
        prompt=EXTRACT_REQUIREMENTS_PROMPT,
        schema=RequirementsExtraction,
        needs_profile=False,
    ),
    "score_match": TaskSpec(
        prompt=SCORE_MATCH_PROMPT,
        schema=MatchScore,
        needs_profile=True,
    ),
    "tailor_cv": TaskSpec(
        prompt=TAILOR_CV_PROMPT,
        schema=TailoredCV,
        needs_profile=True,
    ),
}

ASSIGNMENT_LIST = [
    ("extract_requirements", "flash-nothink"),
    ("score_match", "pro-think"),
    ("tailor_cv", "pro-think"),
]


def run_once(
    llm: BaseChatModel,
    model: str,
    task: str,
    job_label: JobLabel,
    profile: str | None,
    repeat: int,
) -> RunRecord:
    task_spec = TASK_REGISTRY[task]
    jd = (JDS / job_label.jd_file).read_text(encoding="utf-8")

    if task_spec.needs_profile:
        content = f"Candidate profile:\n{profile}\n\nJob description:\n{jd}"
    else:
        content = f"Job description:\n{jd}"

    # tool_choice="auto", not a forced choice: DeepSeek thinking mode (V4 Pro) rejects
    # forced tool_choice ("required" or a specific tool name both 400). With one tool bound
    # and a directive prompt the model still calls it; a decline is recorded as a no-tool-call
    # failure (output=None) rather than crashing, and shows up in the validity rate.
    bound = llm.bind_tools([task_spec.schema], tool_choice="auto")
    messages = [
        SystemMessage(content=task_spec.prompt),
        HumanMessage(content=content),
    ]

    start = perf_counter()
    result = bound.invoke(messages)
    latency_s = perf_counter() - start

    if not isinstance(result, AIMessage):
        raise TypeError(
            f"Expected AIMessage from tool call, got {type(result).__name__}"
        )

    if not result.tool_calls:
        args = None
        schema_valid = False
        error = "No tool call returned."
    else:
        args = result.tool_calls[0]["args"]
        try:
            task_spec.schema.model_validate(args)
            schema_valid = True
            error = None
        except ValidationError as exc:
            schema_valid = False
            error = str(exc)

    usage: dict[str, Any] = dict(result.usage_metadata or {})
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    cached_input_tokens = (usage.get("input_token_details") or {}).get("cache_read", 0)
    # Pricing is per model tier, so key cost on the spec's model_name, not the config label.
    cost = cost_usd(
        MODEL_REGISTRY[model].model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached_input_tokens,
    )

    return RunRecord(
        model=model,
        task=task,
        job_id=job_label.id,
        repeat=repeat,
        output=args,
        schema_valid=schema_valid,
        error=error,
        latency_s=latency_s,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached_input_tokens,
        cost_usd=cost,
    )


def load_profile() -> str:
    """The frozen candidate profile as raw JSON text, embedded verbatim into the prompt."""
    return PROFILE.read_text(encoding="utf-8")


def load_jobs() -> list[JobLabel]:
    """Parse datasets/jobs.jsonl into JobLabel ground-truth records (skipping blank lines)."""
    jobs: list[JobLabel] = []
    for line in JOBS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            jobs.append(JobLabel.model_validate_json(line))
    return jobs


def run_eval() -> None:
    profile = load_profile()
    jobs = load_jobs()

    timestamp = datetime.now().strftime("%Y-%m-%dT%H%M")
    out_path = RESULTS / f"run-{timestamp}.jsonl"

    with out_path.open("w", encoding="utf-8") as f:
        for task, model in ASSIGNMENT_LIST:
            llm = build_model(model)
            for job in jobs:
                for repeat in range(3):
                    record = run_once(llm, model, task, job, profile, repeat)
                    f.write(record.model_dump_json() + "\n")


def main() -> None:
    load_dotenv(HERE.parent / "backend" / ".env")
    run_eval()


if __name__ == "__main__":
    main()
