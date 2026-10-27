"""Capa 0.5 — simulación IA-vs-IA: un LLM hace de cliente según un escenario y se evalúa al agente."""

import uuid
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session, sessionmaker

from src.channels.base import InboundEvent
from src.core.dispatcher import turn_input
from src.core.prompt_catalog import PromptStore
from src.db.models import ConversationOutcome
from src.eval.judge import format_transcript, judge_outcome
from src.eval.recorder import OutcomeRecorder
from src.llm.base import LLMProvider


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    persona: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    opening: str | None = None  # primer mensaje fijo; si falta lo escribe el simulador
    max_turns: int = Field(default=6, gt=0, le=30)


def load_scenarios(path: str | Path) -> list[Scenario]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return [Scenario.model_validate(s) for s in data["scenarios"]]


def _customer_message(llm: LLMProvider, prompts: PromptStore, sc: Scenario, transcript: list[dict]) -> str:
    system = prompts.get("simulated_customer").replace("{{persona}}", sc.persona).replace("{{goal}}", sc.goal)
    user = f"<conversation>\n{format_transcript(transcript)}\n</conversation>" if transcript else "(la conversación aún no empezó)"
    return llm.complete(system, user).strip()


def run_scenario(
    graph, llm: LLMProvider, prompts: PromptStore, recorder: OutcomeRecorder,
    session_factory: sessionmaker[Session], scenario: Scenario, judge: bool = True,
) -> int:
    """Corre un escenario completo contra el grafo y devuelve el id del outcome (source=simulation)."""
    user_id = f"sim-{scenario.id}-{uuid.uuid4().hex[:8]}"
    thread_id = f"sim:{user_id}"
    config = {"configurable": {"thread_id": thread_id}}
    transcript: list[dict] = []
    outcome_id = None
    for n in range(scenario.max_turns):
        text = scenario.opening if (n == 0 and scenario.opening) else _customer_message(llm, prompts, scenario, transcript)
        if not text or text.strip().upper().startswith("FIN"):
            break
        out = graph.invoke(turn_input(InboundEvent("sim", user_id, f"{user_id}-{n}", text)), config)
        transcript += [{"role": "user", "content": text}, {"role": "assistant", "content": out["reply"]}]
        outcome_id = recorder.record_turn(thread_id, "sim", user_id, text, out, source="simulation", scenario=scenario.id)
    if outcome_id is not None and judge:
        with session_factory() as db:
            judge_outcome(db, llm, prompts, db.get(ConversationOutcome, outcome_id))
    return outcome_id
