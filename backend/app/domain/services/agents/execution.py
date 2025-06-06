from typing import AsyncGenerator, Optional
import json
from app.domain.models.plan import Plan, Step, ExecutionStatus
from app.domain.services.agents.base import BaseAgent
from app.domain.models.memory import Memory
from app.domain.external.llm import LLM
from app.domain.external.sandbox import Sandbox
from app.domain.external.browser import Browser
from app.domain.external.search import SearchEngine
from app.domain.services.prompts.execution import EXECUTION_SYSTEM_PROMPT, EXECUTION_PROMPT
from app.domain.models.event import (
    AgentEvent,
    StepFailedEvent,
    StepCompletedEvent,
    MessageEvent,
    ErrorEvent,
    StepStartedEvent
)
from app.domain.services.tools.shell import ShellTool
from app.domain.services.tools.browser import BrowserTool
from app.domain.services.tools.search import SearchTool
from app.domain.services.tools.file import FileTool
from app.domain.services.tools.message import MessageTool


class ExecutionAgent(BaseAgent):
    """
    Execution agent class, defining the basic behavior of execution
    """

    system_prompt: str = EXECUTION_SYSTEM_PROMPT

    def __init__(
        self,
        memory: Memory,
        llm: LLM,
        sandbox: Sandbox,
        browser: Browser,
        search_engine: Optional[SearchEngine] = None,
    ):
        super().__init__(memory, llm, [   
            ShellTool(sandbox),
            BrowserTool(browser),
            FileTool(sandbox),
            MessageTool()
        ])
        
        # Only add search tool when search_engine is not None
        if search_engine:
            self.tools.append(SearchTool(search_engine))
    
    async def execute_step(self, plan: Plan, step: Step) -> AsyncGenerator[AgentEvent, None]:
        message = EXECUTION_PROMPT.format(goal=plan.goal, step=step.description)
        step.status = ExecutionStatus.RUNNING
        yield StepStartedEvent(step=step, plan=plan)
        async for event in self.execute(message):
            if isinstance(event, ErrorEvent):
                step.status = ExecutionStatus.FAILED
                step.error = event.error
                yield StepFailedEvent(step=step, plan=plan)
                return
            
            if isinstance(event, MessageEvent):
                step.status = ExecutionStatus.COMPLETED
                step.result = event.message
                yield StepCompletedEvent(step=step, plan=plan)
            yield event
        step.status = ExecutionStatus.COMPLETED

