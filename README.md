# AutoConfirm

AplicaciÃ³n para enviar confirmaciones por WhatsApp y registrar respuestas.

## Archivos principales

- `main_app.py` â†’ aplicaciÃ³n de escritorio principal de AutoConfirm
- `app.py` â†’ servidor Flask para capturar confirmaciones

## Estructura

- `assets/` â†’ iconos y recursos visuales
- `data/` â†’ base de datos, Excel de ejemplo y archivos de apoyo
- `experimental/` â†’ pruebas o versiones futuras
- `legacy/` â†’ cÃ³digo viejo que ya no se usa, pero se conserva
- `packaging/` â†’ archivos `.spec` e instalador
- `release/` â†’ compilados, ejecutables y salidas de build

## Notas

- La versiÃ³n actual principal trabaja alrededor de WhatsApp Web.
- La parte de API/Twilio quedÃ³ separada para retomarla despuÃ©s.
- Si vas a venderla, usa `main_app.py` como base principal.

