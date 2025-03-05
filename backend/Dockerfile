# Usamos una imagen base ligera de Python
FROM python:3.9-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia el archivo de requerimientos y luego instálalo
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de los archivos (incluyendo mqtt_subscriber.py)
COPY . .

# Indica el comando para iniciar el backend
CMD ["python", "mqtt_subscriber.py"]
