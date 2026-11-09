# ui/registry.py

from agente.agente_curador import agente_noticias
from agente.agente_curador_v2 import workflow as workflow_v2
from agente.agente_curador_v3 import news_curator_workflow
from agente.agente_curador_v4 import research_pipeline_workflow

WORKFLOWS = {
    "V4 - Multi-Agent Research Pipeline": research_pipeline_workflow,
    "V3 - Loop + Fact Check": news_curator_workflow,
    "V2 - Workflow": workflow_v2,
    "V1 - Agent Único": agente_noticias,
}
