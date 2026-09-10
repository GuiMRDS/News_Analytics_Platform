# ui/registry.py

from agente import agente_curador
from agente import agente_curador_v2
from agente import agente_curador_v3


WORKFLOWS = {
    "V1 - Básico": agente_curador,
    "V2 - Multi-Fonte": agente_curador_v2,
    "V3 - Fact Check": agente_curador_v3,
}