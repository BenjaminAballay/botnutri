# BotNutri - Asistente Nutricional para Discord

## Requisitos
- Python 3.10+
- Token de bot de Discord
- API key de OpenRouter

## Instalacion

```bash
pip install -r requirements.txt
```

## Configuracion

1. Crear archivo `.env` basado en `.env.example`:
```bash
cp .env.example .env
```

2. Editar `.env` con tus credenciales.

### Obtener Token de Discord
1. Ir a https://discord.com/developers/applications
2. Crear una nueva aplicacion
3. Ir a "Bot" en el menu lateral
4. Click "Add Bot"
5. Copiar el token

### Obtener API Key de OpenRouter
1. Ir a https://openrouter.ai/
2. Crear cuenta
3. Ir a Keys y generar una nueva

## Ejecucion

```bash
python main.py
```

## Comandos (en mensaje directo al bot)

- `!start` - Saludo y estado general
- `!estado` - Ver calorias consumidas y restantes

## Estructura de Archivos

```
botnutri/
├── main.py
├── requirements.txt
├── .env
├── .env.example
├── diario.json
└── README.md
```

## Notas

- El bot solo responde a mensajes directos (DM)
- Usa OpenRouter con DeepSeek como modelo LLM
- El archivo `diario.json` se reinicia automaticamente cada dia
- El LLM responde en JSON estructurado para parsing confiable