from typing import Dict, Any, List, AsyncGenerator, Optional
import json
import logging
from app.domain.models.plan import Plan, Step
from app.domain.services.agents.base import BaseAgent
from app.domain.models.memory import Memory
from app.domain.external.llm import LLM
from app.domain.services.prompts.planner import (
    PLANNER_SYSTEM_PROMPT, 
    CREATE_PLAN_PROMPT, 
    UPDATE_PLAN_PROMPT
)
from app.domain.models.event import (
    AgentEvent,
    PlanCreatedEvent,
    PlanUpdatedEvent,
    MessageEvent
)
from app.domain.external.sandbox import Sandbox
from app.domain.services.tools.file import FileTool
from app.domain.services.tools.shell import ShellTool

logger = logging.getLogger(__name__)

class PlannerAgent(BaseAgent):
    """
    Planner agent class, defining the basic behavior of planning
    """

    system_prompt: str = PLANNER_SYSTEM_PROMPT
    format: Optional[str] = "json_object"

    def __init__(
        self,
        memory: Memory,
        llm: LLM,
    ):
        super().__init__(memory, llm)


    async def create_plan(self, message: Optional[str] = None) -> AsyncGenerator[AgentEvent, None]:
        message = CREATE_PLAN_PROMPT.format(user_message=message) if message else None
        async for event in self.execute(message):
            if isinstance(event, MessageEvent):
                logger.info(event.message)
                parsed_response = json.loads(event.message)
                steps = [Step(id=step["id"], description=step["description"]) for step in parsed_response["steps"]]
                plan = Plan(id=f"plan_{len(steps)}", goal=parsed_response["goal"], title=parsed_response["title"], steps=steps, message=parsed_response["message"], todo=parsed_response.get("todo", ""))
                yield PlanCreatedEvent(plan=plan)
            else:
                yield event

    async def update_plan(self, plan: Plan) -> AsyncGenerator[AgentEvent, None]:
        message = UPDATE_PLAN_PROMPT.format(plan=plan.model_dump_json(include={"steps"}), goal=plan.goal)
        async for event in self.execute(message):
            if isinstance(event, MessageEvent):
                parsed_response = json.loads(event.message)
                new_steps = [Step(id=step["id"], description=step["description"]) for step in parsed_response["steps"]]
                
                # Find the index of the first pending step
                first_pending_index = None
                for i, step in enumerate(plan.steps):
                    if not step.is_done():
                        first_pending_index = i
                        break
                
                # If there are pending steps, replace all pending steps
                if first_pending_index is not None:
                    # Keep completed steps
                    updated_steps = plan.steps[:first_pending_index]
                    # Add new steps
                    updated_steps.extend(new_steps)
                    # Update steps in plan
                    plan.steps = updated_steps
                
                yield PlanUpdatedEvent(plan=plan)
            else:
                yield event