"""
BotNutri - Asistente Nutricional Personalizado para Discord (Multi-usuario)
Usa OpenRouter (DeepSeek) como backend LLM.
"""

import os
import json
import datetime
import discord
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not OPENROUTER_API_KEY or not DISCORD_TOKEN:
    raise ValueError("Faltan OPENROUTER_API_KEY o DISCORD_TOKEN en el archivo .env")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

openrouter = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://botnutri.local",
        "X-Title": "BotNutri",
    },
)

LIMITE_DEFECTO = 2000
DIARIO_FILE = "diario.json"
PAUTA_FILE = "pauta.txt"


def cargar_pauta():
    if os.path.exists(PAUTA_FILE):
        with open(PAUTA_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


PAUTA = cargar_pauta()


def cargar_diario():
    if os.path.exists(DIARIO_FILE):
        try:
            with open(DIARIO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def guardar_diario(datos):
    with open(DIARIO_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def asegurar_usuario(user_id):
    datos = cargar_diario()
    uid = str(user_id)
    hoy = datetime.date.today().isoformat()

    if uid not in datos:
        datos[uid] = {
            "limite_calorias": LIMITE_DEFECTO,
            "fecha": hoy,
            "calorias_consumidas": 0,
            "log": []
        }
        guardar_diario(datos)
    else:
        if datos[uid].get("fecha") != hoy:
            datos[uid]["fecha"] = hoy
            datos[uid]["calorias_consumidas"] = 0
            datos[uid]["log"] = []
            guardar_diario(datos)

    return uid


def obtener_perfil(user_id):
    uid = asegurar_usuario(user_id)
    datos = cargar_diario()
    return datos[uid]


def restar_calorias(user_id, cantidad):
    uid = asegurar_usuario(user_id)
    datos = cargar_diario()
    datos[uid]["calorias_consumidas"] += cantidad
    guardar_diario(datos)


def obtener_calorias_restantes(user_id):
    perfil = obtener_perfil(user_id)
    return perfil["limite_calorias"] - perfil.get("calorias_consumidas", 0)


def agregar_log(user_id, texto, calorias):
    uid = asegurar_usuario(user_id)
    datos = cargar_diario()
    ahora = datetime.datetime.now().strftime("%H:%M")
    datos[uid]["log"].append({"hora": ahora, "descripcion": texto, "calorias": calorias})
    guardar_diario(datos)


def actualizar_limite(user_id, nuevo_limite):
    uid = asegurar_usuario(user_id)
    datos = cargar_diario()
    datos[uid]["limite_calorias"] = nuevo_limite
    guardar_diario(datos)
    return datos[uid]["limite_calorias"]


def construir_system_prompt(user_id):
    perfil = obtener_perfil(user_id)
    limite = perfil["limite_calorias"]

    return f"""Eres BotNutri, un asistente nutricional personalizado amable pero estricto.

CONTEXTO DEL USUARIO:
- Objetivo: Recorte de peso priorizando el mantenimiento de masa muscular.
- Limite calorico diario: {limite} calorias exactas.
- El usuario NO toma desayuno. Las porciones de carbohidratos y proteinas del desayuno se traspasan al almuerzo.
- Alimentos recurrentes: Yogurt de proteinas Soprole, batidos de proteina, sushi.
- Horarios sugeridos: Almuerzo (12:00-14:00), Cena (19:00-21:00).

PAUTA DE PORCIONES (1 PORCION EQUIVALE A):
{PAUTA}

Usa la PAUTA DE PORCIONES para calcular automaticamente cuantas porciones y gramos del total ha consumido el usuario. Por ejemplo, si el usuario dice "comi 240g de arroz integral cocido", y la pauta dice que 1 porcion de arroz integral cocido = 120g, entonces sabe que son 2 porciones.

REGLAS ESTRICTAS:
1. NUNCA proporciones menos de 150g de proteina al dia.
2. Las recetas deben calcular gramos exactos para encajar en las calorias restantes.
3. Si el usuario dice 'comi X' o 'me comi X', calcula las calorias usando la pauta de porciones y responde cuantas le quedan.
4. Si pide una receta, responde con la receta Y las calorias correspondientes.
5. Se directo y concreto con los numeros.

RESPUESTA OBLIGATORIA EN JSON VALIDO:
Siempre responde UNICAMENTE con un objeto JSON valido, sin texto adicional fuera del JSON.
El JSON debe tener exactamente estos campos:
{{
  "mensaje": "texto amigable para el usuario (receta, confirmacion, etc.)",
  "calorias": numero entero (calorias a descontar, o 0 si solo pidio receta/referencia)
}}

Ejemplo de respuesta para 'comi 240g de arroz integral con 150g de pechuga':
{{
  "mensaje": "Perfecto, 240g de arroz integral (2 porciones) + 150g de pechuga de pollo (3 porciones) = aproximadamente 580 kcal. Te quedan X kcal del dia.",
  "calorias": 580
}}

Ejemplo de respuesta para 'dame una receta para cenar':
{{
  "mensaje": "Salmon a la plancha con verduras: 200g salmon aproximadamente 208 kcal, 150g brocoli aproximadamente 55 kcal, 100g zapallo aproximadamente 30 kcal. Total aproximadamente 293 kcal. Te quedan X kcal disponibles.",
  "calorias": 0
}}
"""


@client.event
async def on_ready():
    print(f"BotNutri iniciado como {client.user}")
    print("Esperando mensajes directos...")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        uid = str(message.author.id)
        texto_usuario = message.content.strip()

        if texto_usuario.lower() == "!start":
            asegurar_usuario(uid)
            perfil = obtener_perfil(uid)
            limite = perfil["limite_calorias"]
            consumido = perfil.get("calorias_consumidas", 0)
            restante = limite - consumido

            texto = (
                f"Hola {message.author.name}!\n\n"
                f"Soy BotNutri, tu asistente nutricional personalizado.\n\n"
                f"Tu objetivo: recorte de peso priorizando masa muscular\n"
                f"Limite diario: {limite} kcal\n\n"
                f"Hoy has consumido: {consumido} kcal\n"
                f"Te quedan: {restante} kcal\n\n"
                f"Comandos disponibles:\n"
                f"!start - Ver este mensaje\n"
                f"!estado - Ver estado del dia\n"
                f"!limite <numero> - Cambiar tu limite calorico\n\n"
                f"Tambien puedes escribir cualquier cosa y te ayudo: recetas, registrar lo que comiste, o simplemente preguntar."
            )
            await message.reply(texto)
            return

        if texto_usuario.lower() == "!estado":
            asegurar_usuario(uid)
            perfil = obtener_perfil(uid)
            limite = perfil["limite_calorias"]
            consumido = perfil.get("calorias_consumidas", 0)
            restante = limite - consumido
            porcentaje = (consumido / limite) * 100 if limite > 0 else 0

            barra = "#" * int(porcentaje // 5) + "-" * (20 - int(porcentaje // 5))

            texto = (
                f"Estado de hoy - {perfil.get('fecha', 'N/A')}\n\n"
                f"Calorias consumidas: {consumido} / {limite} kcal\n"
                f"Restantes: {restante} kcal\n\n"
                f"[{barra}] {porcentaje:.1f}%\n\n"
            )

            if perfil.get("log"):
                texto += "Log de hoy:\n"
                for entrada in perfil["log"]:
                    texto += f"  {entrada['hora']} - {entrada['descripcion']} ({entrada['calorias']} kcal)\n"
            else:
                texto += "Aun no has registrado nada hoy."

            await message.reply(texto)
            return

        if texto_usuario.lower().startswith("!limite"):
            partes = texto_usuario.split()
            if len(partes) != 2:
                await message.reply("Uso correcto: !limite <numero>. Ejemplo: !limite 1800")
                return

            try:
                nuevo_limite = int(partes[1])
                if nuevo_limite < 500 or nuevo_limite > 5000:
                    await message.reply("El limite debe estar entre 500 y 5000 calorias.")
                    return

                actualizar_limite(uid, nuevo_limite)
                await message.reply(f"Tu limite calorico diario se actualizo a {nuevo_limite} kcal.")
            except ValueError:
                await message.reply("Debes ingresar un numero valido. Ejemplo: !limite 1800")
            return

        if texto_usuario.startswith("!"):
            await message.reply("Comando desconocido. Usa !start, !estado o !limite <numero>.")
            return

        await message.channel.typing()

        calorias_restantes = obtener_calorias_restantes(uid)
        system_prompt = construir_system_prompt(uid)

        prompt_usuario = (
            f"El usuario escribio: '{texto_usuario}'\n"
            f"Calorias restantes del dia: {calorias_restantes}\n\n"
            f"Responde SOLO con JSON valido segun las instrucciones del sistema."
        )

        try:
            respuesta = openrouter.chat.completions.create(
                model="deepseek/deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt_usuario},
                ],
                temperature=0.2,
                max_tokens=1024,
            )

            texto_respuesta = respuesta.choices[0].message.content.strip()

            if texto_respuesta.startswith("```json"):
                texto_respuesta = texto_respuesta[7:]
            if texto_respuesta.startswith("```"):
                texto_respuesta = texto_respuesta[3:]
            if texto_respuesta.endswith("```"):
                texto_respuesta = texto_respuesta[:-3]

            datos_json = json.loads(texto_respuesta.strip())

            mensaje_usuario = datos_json.get("mensaje", "No pude procesar tu mensaje.")
            calorias_descontar = datos_json.get("calorias", 0)

            calorias_descontar = max(0, int(calorias_descontar))

            if calorias_descontar > 0:
                if calorias_descontar > calorias_restantes:
                    mensaje_usuario += f"\nNota: {calorias_descontar} kcal exceden tus {calorias_restantes} kcal restantes. Se registraran de todos modos."

                restar_calorias(uid, calorias_descontar)
                agregar_log(uid, mensaje_usuario[:50], calorias_descontar)

            nuevo_restante = obtener_calorias_restantes(uid)
            mensaje_usuario = mensaje_usuario.replace("X", str(nuevo_restante))
            mensaje_final = f"{mensaje_usuario}\n\nCalorias restantes hoy: {nuevo_restante}"

            await message.reply(mensaje_final)

        except json.JSONDecodeError:
            await message.reply("Tuve un problema entendiendo la respuesta. Podrias intentarlo de nuevo?")
        except Exception as e:
            await message.reply(f"Error: {str(e)}")


def main():
    print("BotNutri iniciado (multi-usuario)...")
    print("Presiona Ctrl+C para detener.")
    client.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()