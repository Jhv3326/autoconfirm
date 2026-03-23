import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

mi_correo = "javierhernandezvargas332@gmail.com"
mi_contraseña = "sbiv tvvn spfu isxv" \
""

destinatario = "jhvj184@gmail.com"

# Crear el mensaje sin caracteres especiales
mensaje = MIMEMultipart()
mensaje["From"] = mi_correo
mensaje["To"] = destinatario
mensaje["Subject"] = "Confirmacion de evento"

# Cuerpo del mensaje sin acentos, ñ ni emojis
cuerpo = "Hola, esta es la confirmacion de tu asistencia al evento. Nos vemos pronto!"
mensaje.attach(MIMEText(cuerpo, "plain"))

try:
    with smtplib.SMTP("smtp.gmail.com", 587) as servidor:
        servidor.ehlo()
        servidor.starttls()
        servidor.ehlo()
        servidor.login(mi_correo, mi_contraseña)
        servidor.sendmail(mi_correo, destinatario, mensaje.as_string())
    print("Correo enviado con exito")
except Exception as e:
    print("Error al enviar:", e)