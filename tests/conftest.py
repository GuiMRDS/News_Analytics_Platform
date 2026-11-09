"""Configuração global dos testes.

Nenhum teste chama o LLM ou faz buscas na web: os agentes são apenas
instanciados (o que não exige rede) e a UI usa workflows falsos.
"""

import os

# Chave fictícia: permite importar os módulos sem .env. Definida antes de
# qualquer import de `agente`, pois `comum` chama load_dotenv no import
# (load_dotenv não sobrescreve variáveis já definidas).
os.environ.setdefault("GROQ_API_KEY", "chave-de-teste")
