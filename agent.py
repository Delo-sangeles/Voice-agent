import json
from pathlib import Path
from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    RoomInputOptions,
)
from livekit.agents.llm import function_tool
from livekit.agents import inference
from livekit.agents.inference import TurnDetector

load_dotenv()

# --- Knowledge base: cargamos las propiedades desde JSON ---
PROPERTIES_FILE = Path(__file__).parent / "properties.json"


def cargar_propiedades() -> list[dict]:
    with open(PROPERTIES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


class RealEstateAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Eres un asistente de voz de una agencia inmobiliaria. "
                "Eres amable, profesional y conciso: recuerda que estás hablando "
                "por teléfono, así que evita respuestas largas o listas. "
                "Usa la herramienta 'buscar_propiedades' para consultar el "
                "inventario disponible antes de responder sobre propiedades; "
                "no inventes datos que no estén en la herramienta."
            )
        )
        # Cargamos una sola vez al iniciar el agente
        self._propiedades = cargar_propiedades()

    @function_tool
    async def buscar_propiedades(self, ciudad: str | None = None, tipo: str | None = None):
        """Busca propiedades disponibles filtrando opcionalmente por ciudad y/o tipo.

        Args:
            ciudad: Ciudad donde buscar (ej. "Madrid"). Opcional.
            tipo: Tipo de propiedad (ej. "piso", "casa", "ático", "chalet"). Opcional.
        """
        resultados = self._propiedades
        if ciudad:
            resultados = [p for p in resultados if p["ciudad"].lower() == ciudad.lower()]
        if tipo:
            resultados = [p for p in resultados if p["tipo"].lower() == tipo.lower()]
        return {"propiedades": resultados}


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    session = AgentSession(
        stt=inference.STT(model="deepgram/nova-3", language="es"),
        llm=inference.LLM(model="openai/gpt-4.1-mini"),
        tts=inference.TTS(model="cartesia/sonic-3", language="es"),
        turn_detection=TurnDetector(),
    )

    await session.start(
        room=ctx.room,
        agent=RealEstateAgent(),
        room_input_options=RoomInputOptions(),
    )

    await session.generate_reply(
        instructions=(
            "Saluda al usuario, preséntate como el asistente de la agencia "
            "inmobiliaria y pregúntale en qué ciudad está buscando vivienda."
        )
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))