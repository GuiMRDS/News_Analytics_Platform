"""Medidor de uso de tokens do Groq (para o card da sidebar).

O Groq não tem API de consumo no plano gratuito, mas cada resposta traz:
- cabeçalhos `x-ratelimit-*`: limite/restante de tokens por MINUTO (TPM) e de
  REQUISIÇÕES por dia (RPD);
- corpo com `usage.total_tokens` (tokens gastos naquela chamada);
- nos erros 429 de cota diária: "Limit 200000, Used 198392" (valor oficial do TPD).

O total de tokens das últimas 24 h (TPD, janela móvel) é contado pelo app e
corrigido pelo valor oficial sempre que o Groq o informa num 429. O histórico
fica em output/.uso_groq.json para sobreviver a reinícios do servidor.
"""

import json
import re
import threading
import time
from pathlib import Path
from typing import Any

import httpx

JANELA_S = 24 * 3600
TPD_PADRAO = 200_000  # cota diária do plano gratuito por modelo (confirmada nas mensagens 429)
_PADRAO_TPD = re.compile(r"tokens per day \(TPD\): Limit (\d+), Used (\d+)")


class MedidorGroq:
    def __init__(self, arquivo: Path | None = None) -> None:
        self._trava = threading.Lock()
        self._arquivo = arquivo
        self._modelos: dict[str, dict[str, Any]] = {}
        self._ultimo_salvamento = 0.0
        self._carregar()

    # ------------------------------------------------------------------ registro
    def _modelo(self, nome: str) -> dict[str, Any]:
        return self._modelos.setdefault(nome, {"eventos": [], "oficial": None})

    def registrar(self, modelo: str, status: int, cabecalhos: dict[str, str], corpo: dict | None) -> None:
        agora = time.time()
        with self._trava:
            m = self._modelo(modelo)
            lim = {k: cabecalhos.get(f"x-ratelimit-{k}") for k in
                   ("limit-tokens", "remaining-tokens", "limit-requests", "remaining-requests", "reset-tokens")}
            if any(lim.values()):
                m["tpm_limite"] = _int(lim["limit-tokens"])
                m["tpm_restante"] = _int(lim["remaining-tokens"])
                m["rpd_limite"] = _int(lim["limit-requests"])
                m["rpd_restante"] = _int(lim["remaining-requests"])
                m["limites_em"] = agora
            if status == 200 and corpo:
                tokens = ((corpo.get("usage") or {}).get("total_tokens")) or 0
                if tokens:
                    m["eventos"].append([agora, int(tokens)])
            elif status == 429 and corpo:
                texto = json.dumps(corpo, ensure_ascii=False)
                achado = _PADRAO_TPD.search(texto)
                if achado:  # valor oficial do Groq para as últimas 24 h
                    m["oficial"] = [agora, int(achado.group(1)), int(achado.group(2))]
            self._podar(m, agora)
        self._salvar()

    # ------------------------------------------------------------------ leitura
    def uso(self, modelo: str) -> dict[str, Any]:
        agora = time.time()
        with self._trava:
            m = self._modelo(modelo)
            self._podar(m, agora)
            contados = sum(t for _, t in m["eventos"])
            limite, fonte = TPD_PADRAO, "contagem do app"
            if m["oficial"]:
                quando, limite, usado = m["oficial"]
                depois = sum(t for ts, t in m["eventos"] if ts > quando)
                if usado + depois > contados:
                    contados, fonte = usado + depois, "Groq (429) + contagem do app"
            limites_validos = m.get("limites_em") and agora - m["limites_em"] < 120
            return {
                "modelo": modelo,
                "tokens_24h": contados,
                "tpd_limite": limite,
                "tpd_restante": max(0, limite - contados),
                "fonte_24h": fonte,
                "chamadas_24h": len(m["eventos"]),
                # TPM só vale por ~1 min; depois disso o balde já recarregou
                "tpm_limite": m.get("tpm_limite"),
                "tpm_restante": m.get("tpm_restante") if limites_validos else m.get("tpm_limite"),
                "rpd_limite": m.get("rpd_limite"),
                "rpd_restante": m.get("rpd_restante"),
                "limites_atualizados_em": m.get("limites_em"),
            }

    # ------------------------------------------------------------------ util
    @staticmethod
    def _podar(m: dict[str, Any], agora: float) -> None:
        m["eventos"] = [e for e in m["eventos"] if agora - e[0] < JANELA_S]
        if m["oficial"] and agora - m["oficial"][0] >= JANELA_S:
            m["oficial"] = None

    def _carregar(self) -> None:
        if not self._arquivo or not self._arquivo.exists():
            return
        try:
            self._modelos = json.loads(self._arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self._modelos = {}

    def _salvar(self, forcar: bool = False) -> None:
        if not self._arquivo:
            return
        agora = time.time()
        if not forcar and agora - self._ultimo_salvamento < 5:
            return
        self._ultimo_salvamento = agora
        with self._trava:
            dados = json.dumps(self._modelos)
        try:
            self._arquivo.parent.mkdir(parents=True, exist_ok=True)
            self._arquivo.write_text(dados, encoding="utf-8")
        except OSError:
            pass  # o medidor é informativo: nunca derruba a execução

    # ------------------------------------------------------------------ httpx
    def hook_resposta(self, resposta: httpx.Response) -> None:
        """Event hook do httpx: lê limites e consumo de cada resposta de /chat/completions."""
        try:
            if "/chat/completions" not in str(resposta.request.url):
                return
            modelo = json.loads(resposta.request.content or b"{}").get("model") or "?"
            corpo = None
            if "text/event-stream" not in resposta.headers.get("content-type", ""):
                resposta.read()  # o SDK do Groq reaproveita o conteúdo já lido
                corpo = resposta.json()
            self.registrar(modelo, resposta.status_code, dict(resposta.headers), corpo)
        except Exception:  # noqa: BLE001 - o medidor nunca pode quebrar uma chamada
            pass

    def cliente_http(self) -> httpx.Client:
        return httpx.Client(timeout=httpx.Timeout(120.0, connect=10.0), event_hooks={"response": [self.hook_resposta]})


def _int(valor: str | None) -> int | None:
    try:
        return int(float(valor)) if valor not in (None, "") else None
    except ValueError:
        return None
