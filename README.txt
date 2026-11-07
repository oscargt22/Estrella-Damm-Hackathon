DAMM · PANEL SIMPLE TYPEFORM

1. Instala Python 3.10+ si no lo tienes.
2. En esta carpeta, copia .env.example y renombra la copia a .env
   (en Windows activa "Ver > Extensiones de nombre de archivo" si es necesario).
3. Sustituye PEGA_AQUI_TU_TOKEN_NUEVO por un token de Typeform.
   Debe tener forms:read, forms:write y responses:read. NO SUBAS .env A GITHUB.
4. Ejecuta INICIAR_WINDOWS.bat, o en VS Code abre terminal y ejecuta: python server.py
5. Abre http://127.0.0.1:5000
6. Para ver porcentajes, pulsa Editar objetivo y escribe cuántas personas
   deberían responder cada encuesta. Hasta entonces se ve solo el número de respuestas.

CREAR CAMPAÑA:
- Pulsa "+ Crear nueva campaña" arriba a la derecha.
- Escribe título, objetivo de la consulta, colectivo y cuántas personas deben responder.
- Pulsa "Generar preguntas", revísalas y edítalas si hace falta.
- Pulsa "Crear en Typeform" para crear el formulario en tu cuenta.
- El nuevo Typeform tendrá 4 preguntas (2 escalas de 1 a 5 y 2 abiertas),
  pantalla de bienvenida y agradecimiento. Después aparecerá al actualizar.
- Las preguntas se proponen mediante plantillas, no mediante IA generativa.
- La población objetivo es una referencia para calcular porcentaje; NO es un
  límite de respuestas ni impide que otras personas abran el enlace.

IMPORTANTE:
- La app NO contiene el token y escucha SOLO en tu ordenador (127.0.0.1).
- Creación comprobada mediante API simulada; no se ha probado con tu cuenta real.
- Este prototipo cuenta respuestas agregadas; no declara que las encuestas estén
  activas, ya que el listado de formularios no prueba su disponibilidad real.
- Por privacidad no muestra textos/respuestas individuales.
- Si pegaste un token en un chat, revócalo y genera otro antes de usarlo.
- La API Responses de Typeform puede demorar ~30 min al mostrar envíos recientes.
- Lee la API indicada por _links.responses para elegir el centro de datos correcto.
