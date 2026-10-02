# Guion de demo de AutoConfirm (uso interno)

Duración objetivo: 10–15 minutos, con una wedding planner o responsable de eventos.

## Antes de la reunión

- [ ] Abre `https://autoconfirm.onrender.com` unos minutos antes: el servicio gratis de Render tarda ~50 s en despertar tras estar inactivo.
- [ ] Ten tu usuario de demo y un evento de ejemplo ya cargado, con invitados ficticios.
- [ ] Ten tu propio teléfono unido al sandbox de Twilio (`join ...`). **Importante:** el sandbox solo entrega a números que hicieron `join` y la sesión expira a los ~3 días. Haz el `join` el mismo día de la demo.
- [ ] Ten abierto un Excel de ejemplo con nombre y teléfono (formato 10 dígitos, el prefijo `52` se agrega solo).

## Flujo de la demo

1. **El problema (1 min).** Pregunta cómo confirma hoy a sus invitados y cuánto tiempo le toma. Escucha antes de mostrar nada.
2. **Crear evento y cargar lista (2 min).** Crea "Boda de ejemplo", sube el Excel. Muestra que no hay que instalar nada.
3. **Envío (2 min).** Manda la invitación y deja que el invitado de prueba sea **tu propio teléfono**. Muéstrale el mensaje que llega.
4. **Confirmación del invitado (2 min).** Abre el enlace en tu teléfono, confirma con 2 acompañantes y una nota. Enfatiza que el invitado no crea cuenta.
5. **Panel (2 min).** Regresa al panel: ya cambió el estado, los totales y los acompañantes. Muestra búsqueda, editar invitado, reenviar a uno y exportar CSV.
6. **Equipo (2 min).** Comparte el evento con otro usuario; muestra que el administrador ve todo y cada planner solo lo suyo.
7. **Requisitos y precio (2 min).** Explica lo que necesita de su parte (ver abajo) y presenta la propuesta de una página.

## Lo que hay que decir con honestidad

- Necesita **su propia cuenta de Twilio y un número de WhatsApp Business** con una **plantilla aprobada por WhatsApp**. Eso puede tardar días o semanas en aprobarse; no se activa el mismo día.
- El costo de los mensajes lo paga a Twilio/Meta, aparte de lo que cobres tú.
- El alta de cuentas es manual y personalizada por ahora; no hay registro público.
- Es una herramienta nueva: no prometas funciones que no están (recordatorios automáticos, encuestas, mesas, integraciones con otros sistemas).

## Preguntas frecuentes

- **¿Mis invitados necesitan instalar algo?** No, solo abren el enlace desde WhatsApp.
- **¿Puedo usar mi número actual de WhatsApp?** No si ya está activo en la app de WhatsApp o WhatsApp Business: debe ser un número dedicado para esto.
- **¿Mis datos y los de mis invitados están separados de otras empresas?** Sí, cada empresa tiene su cuenta aislada.
- **¿Qué pasa si un invitado no responde?** Queda como pendiente y puedes reenviarle el mensaje desde el panel.

## Después de la reunión

- Manda la propuesta en PDF (`propuesta_una_pagina.html` → Imprimir → Guardar como PDF) con el precio ya completado.
- Si acepta: crear su organización y usuarios con `crear_cliente.py` y guiarlo para crear su cuenta de Twilio, su número y su plantilla.
