FROM ubuntu:22.04

# Instalar dependencias necesarias
RUN apt-get update && apt-get install -y \
    cmake \
    git \
    build-essential \
    libjpeg8-dev \
    v4l-utils \
    && rm -rf /var/lib/apt/lists/*

# Clonar y compilar mjpg-streamer
WORKDIR /opt
RUN git clone https://github.com/jacksonliam/mjpg-streamer.git
WORKDIR /opt/mjpg-streamer/mjpg-streamer-experimental
RUN make && make install

# Directorio web (por defecto, los archivos estáticos que vienen con mjpg-streamer)
RUN mkdir -p /usr/local/share/mjpg-streamer/www

# Copia (si deseas) archivos web personalizados en /usr/local/share/mjpg-streamer/www
# COPY www/ /usr/local/share/mjpg-streamer/www/

# Exponer el puerto 8080 para el stream
EXPOSE 8080

# Comando para iniciar mjpg-streamer
CMD ["mjpg_streamer", "-i", "input_uvc.so -d /dev/video0 -r 640x480 -f 25", "-o", "output_http.so -p 8080 -w /usr/local/share/mjpg-streamer/www"]
