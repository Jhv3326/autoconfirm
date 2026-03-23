import pandas as pd
import pywhatkit
import time

# Nombre de tu archivo de Excel. Asegúrate de que esté en la misma carpeta que tu script.
nombre_archivo = "invitados.xlsx"

try:
    # Intenta leer los datos del archivo de Excel
    # El parámetro 'dtype' asegura que los números de teléfono se lean como texto,
    # manteniendo el '+' y el formato completo.
    df = pd.read_excel(nombre_archivo, dtype={'Telefono': str})
except FileNotFoundError:
    print(f"Error: No se encontró el archivo '{nombre_archivo}'. Asegúrate de que está en la misma carpeta.")
    exit()
except Exception as e:
    print(f"Error al leer el archivo de Excel: {e}")
    print("Asegúrate de tener instalada la biblioteca 'openpyxl' y de que el archivo no esté abierto en otra aplicación.")
    exit()

print("Iniciando el envío de mensajes de WhatsApp...")

# 2. Iterar sobre cada fila (cada invitado) en el archivo de Excel
for index, row in df.iterrows():
    try:
        # Obtener los datos del invitado de la fila actual
        nombre_invitado = str(row['Nombre'])
        numero_telefono = str(row['Telefono'])
        
        # Opcional: Si el número en tu Excel no tiene el +, este código se lo agrega
        if not numero_telefono.startswith('+'):
            print(f"Advertencia: Se le agregó el código de país a {nombre_invitado}.")
            # Asegúrate de cambiar el '+52' por el código de tu país si es diferente
            numero_telefono = '+52' + numero_telefono
        
        # 3. Crear el mensaje personalizado
        mensaje = f"""¡Hola {nombre_invitado}!

Queremos confirmar su asistencia a la boda de Doris y Jonathan

🗓 Viernes, 12 de septiembre 2025

Las Nubes.
📍Carr Nacional, Los Rodríguez, 67318 Santiago, N.L.

Ceremonia Religiosa
⛪Capilla Santo Niño de Praga
⏰ 6:00 pm.
Recepción
🎇Salón Lunas
⏰ 7:00 pm

✉️

Confirma usted: __ Adultos

Código de vestimenta: Formal, traje completo y vestido largo, no se permiten colores claros.

Agradecemos confirmar su asistencia por este medio y compartirnos si consideramos alergias, intolerancias o desea algún platillo vegetariano o vegano.

Favor de tener el QR de la invitación para su acceso.

Esperamos pronto contar con su respuesta."""
        
        print(f"Preparando mensaje para {nombre_invitado} ({numero_telefono})...")
        
        # 4. Enviar el mensaje de WhatsApp.
        # El 'wait_time' es para que el programa espere a que se abra WhatsApp Web
        # 'tab_close' cierra la pestaña después de enviar el mensaje
        pywhatkit.sendwhatmsg_instantly(numero_telefono, mensaje, wait_time=15, tab_close=True)
        
        print(f"Mensaje enviado a {nombre_invitado}.")
        
        # 5. Pausa para evitar que WhatsApp te bloquee por actividad inusual
        # Es crucial agregar una pausa entre cada mensaje para una automatización segura
        time.sleep(15) 

    except KeyError:
        print("Error: El archivo de Excel debe tener las columnas 'Nombre' y 'Telefono'. Por favor, verifica los nombres de las columnas.")
        break
    except Exception as e:
        print(f"Error al enviar el mensaje a {nombre_invitado}: {e}")
        # Si un mensaje falla, el programa continúa con el siguiente
        continue

print("Proceso de envío finalizado.")