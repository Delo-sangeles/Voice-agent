# Voice Agent — Agencia Inmobiliaria

Agente de voz construido con [LiveKit Agents](https://docs.livekit.io/agents/) que atiende llamadas telefónicas/web de una agencia inmobiliaria y responde preguntas sobre un catálogo de propiedades.

## Índice

- [Voice Agent — Agencia Inmobiliaria](#voice-agent--agencia-inmobiliaria)
  - [Índice](#índice)
  - [Arquitectura](#arquitectura)
  - [Requisitos previos](#requisitos-previos)
  - [Configuración local](#configuración-local)
  - [Ejecutar en desarrollo](#ejecutar-en-desarrollo)
  - [Probar el agente](#probar-el-agente)
  - [Estructura del proyecto](#estructura-del-proyecto)
  - [La knowledge base (propiedades)](#la-knowledge-base-propiedades)
  - [Despliegue en Azure](#despliegue-en-azure)
  - [Costos esperados](#costos-esperados)
  - [Troubleshooting](#troubleshooting)

## Arquitectura

```
Llamada / navegador
        │
        ▼
   LiveKit Cloud (SFU + dispatch)
        │
        ▼
  agent.py (worker Python, siempre corriendo)
        │
        ├── STT   → LiveKit Inference (Deepgram nova-3)
        ├── LLM   → LiveKit Inference (OpenAI gpt-4.1-mini) + function_tool
        ├── TTS   → LiveKit Inference (Cartesia sonic-3)
        └── Turn detection → LiveKit Inference (modelo cloud, fallback local)
        │
        ▼
  properties.json (local) o Azure Blob Storage (producción)
```

Todo el pipeline de voz (STT/LLM/TTS/turn detection) corre a través de **LiveKit Inference**, sin credenciales de terceros (Google, OpenAI, etc.) — se factura contra el proyecto de LiveKit Cloud.

## Requisitos previos

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) como gestor de paquetes
- Una cuenta de [LiveKit Cloud](https://cloud.livekit.io) (free tier)
- (Opcional, solo para producción) Cuenta de Azure

## Configuración local

1. Clona el repo e instala dependencias:
   ```bash
   uv sync
   ```

2. Copia el archivo de variables de entorno y complétalo:
   ```bash
   cp .env.example .env
   ```
   ```
   LIVEKIT_URL=wss://tu-proyecto.livekit.cloud
   LIVEKIT_API_KEY=...
   LIVEKIT_API_SECRET=...
   ```
   Estas tres las obtienes en [cloud.livekit.io](https://cloud.livekit.io) → tu proyecto → Settings → Keys.

   Deja `AZURE_STORAGE_CONNECTION_STRING` vacío para desarrollo local — el agente usará automáticamente el `properties.json` del repo.

3. Descarga los modelos locales (VAD / turn detector de respaldo):
   ```bash
   uv run -m livekit.agents download-files
   ```

## Ejecutar en desarrollo

```bash
uv run agent.py dev
```

Espera a ver `registered worker` en los logs — eso confirma que el worker está listo y escuchando.

## Probar el agente

1. Ve al [Console de LiveKit Cloud](https://cloud.livekit.io) → Agents → tu agente.
2. Click en **Start session**.
3. Habla con el agente. Preguntas de prueba sugeridas:
   - "¿Qué propiedades tienes en Madrid?"
   - "Busco un piso, no me importa la ciudad"
   - "¿Tienes chalets en Ocaña?"
   - "¿Qué tienes en Barcelona?" (debe decir que no hay resultados, no inventar)
4. Revisa la pestaña **Events** del Console para ver en tiempo real las llamadas a la tool `buscar_propiedades` y sus resultados.

## Estructura del proyecto

```
.
├── agent.py                     # Lógica del agente + tool de búsqueda
├── properties.json              # Knowledge base de propiedades (dev/fallback)
├── pyproject.toml / uv.lock     # Dependencias
├── Dockerfile                   # Imagen del worker para producción
├── .env.example                 # Plantilla de variables de entorno
├── .github/workflows/deploy.yml # CI/CD: build + deploy a Azure en cada push a main
└── README_DEPLOY.md             # Comandos detallados de Azure CLI
```

## La knowledge base (propiedades)

`properties.json` contiene un array de objetos con esta forma:

```json
{
  "id": 1,
  "ciudad": "Madrid",
  "tipo": "piso",
  "habitaciones": 2,
  "precio": 210000,
  "descripcion": "Piso reformado de 2 habitaciones cerca del metro Sol."
}
```

- **En local**: edita el archivo directamente.
- **En producción**: se sube a Azure Blob Storage y el agente lo relee automáticamente (caché de 60s) sin necesidad de redeploy — ver `README_DEPLOY.md`, sección 3.

## Despliegue en Azure

Ver [`README_DEPLOY.md`](./README_DEPLOY.md) para los comandos completos de `az cli` (creación de resource group, Container Registry, Storage Account, y Container App) y la configuración de secrets en GitHub para el pipeline de CI/CD.

Resumen del flujo automatizado:
```
git push origin main
        │
        ▼
GitHub Actions (.github/workflows/deploy.yml)
        │
        ├── docker build
        ├── push a Azure Container Registry
        └── deploy a Azure Container Apps
```

## Costos esperados

| Escenario | Costo |
|---|---|
| Desarrollo local (`uv run agent.py dev`) | $0 |
| Primeros 30 días en Azure (crédito de bienvenida) | $0 |
| Producción en Azure Container Apps (worker 24/7, tras el mes de crédito) | ~$10-13 USD/mes |

El worker necesita `minReplicas ≥ 1` (no puede escalar a cero) porque debe mantenerse siempre registrado con LiveKit Cloud para recibir llamadas — por eso no cabe completo en la cuota "always free" de Azure.

## Troubleshooting

| Síntoma | Causa probable | Solución |
|---|---|---|
| `ModuleNotFoundError: livekit.plugins.turn_detector` | Plugin deprecado | Usar `from livekit.agents.inference import TurnDetector` |
| `429 RESOURCE_EXHAUSTED` en LLM | Cuota de proveedor externo agotada | Usamos LiveKit Inference, no aplica ya |
| `LiveKit Inference STT connection timed out` | Cold start / modelos locales no descargados | Correr `uv run -m livekit.agents download-files` antes del primer arranque |
| Console no detecta ningún agente | El worker local no está corriendo | Verificar que `uv run agent.py dev` esté activo en una terminal |
| `az login` → "no estás suscrito" | Falta activar la suscripción free de Azure | Completar el registro en [azure.microsoft.com/free](https://azure.microsoft.com/free) |