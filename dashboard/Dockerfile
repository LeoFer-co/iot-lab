FROM python:3.9-slim

# Instalar Flask y otras dependencias
RUN pip install flask

# Establecer directorio de trabajo
WORKDIR /app

# Copiar el código del dashboard
COPY . .

# Exponer el puerto 5000
EXPOSE 5000

# Comando para iniciar la aplicación
CMD ["python", "-u", "app.py"]
