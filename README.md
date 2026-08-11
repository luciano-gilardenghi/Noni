# Noni - Gestor Nocturno de PC 🌙

Noni es una herramienta de línea de comandos (CLI) diseñada para entornos Linux que automatiza y facilita la configuración del sistema para el consumo multimedia nocturno. 

El script permite programar apagados automáticos, ajustar perfiles de audio para evitar ruidos molestos, apagar pantallas auxiliares sin afectar el brillo base del sistema, y generar listas de reproducción dinámicas para VLC.

## ✨ Características Principales

* **Gestión de Energía:** Programación y cancelación de apagado automático del sistema.
* **Audio Nocturno:** Configuración automática del perfil de audio (HDMI Surround + Analog Stereo), desmutado y ajuste de volumen a niveles seguros (20%).
* **Control de Pantallas:** Apagado de pantalla auxiliar mediante la utilidad `light`, con encendido automático 15 segundos antes del apagado del sistema.
* **Gestor de Multimedia:** Escaneo de directorio local, filtrado de archivos de video (`.mkv`, `.mp4`) mediante expresiones regulares, y generación de listas de reproducción (`.m3u`) listas para reproducir en VLC.

## 🛠️ Requisitos del Sistema

Este script está diseñado para distribuciones GNU/Linux y requiere las siguientes dependencias instaladas en el sistema:
* `python3`
* `pulseaudio` (comandos `pactl` y `pacmd`)
* `light` (para el control de brillo de la pantalla)
* `vlc` (reproductor multimedia)

## 🚀 Instalación y Ejecución

1. Clonar el repositorio en tu máquina local:
```bash
   git clone https://github.com/tu-usuario/noni.git
   cd noni
```

2. Para ejecutar el código fuente directamente desde la terminal:
```bash
   python3 noni.py
```

## 📦 Crear Ejecutable e Integración al Escritorio (Opcional)

Si deseas utilizar Noni como una aplicación independiente sin necesidad de invocar a Python desde la terminal, puedes compilarlo utilizando **PyInstaller**:

```bash
pip install pyinstaller
pyinstaller --onefile noni.py
```
Esto generará un ejecutable en la carpeta `dist/`.

### Integración en Linux (Menú de Aplicaciones)
En este repositorio se incluyen los archivos `noni.sh` y `noni.desktop` a modo de plantilla para integrar el programa a tu entorno de escritorio.

1. Edita el archivo `noni.sh` y modifica la ruta para que apunte a la ubicación de tu ejecutable local.
2. Edita el archivo `noni.desktop` y actualiza las rutas de `Exec` (apuntando al `.sh`) y `Icon` (apuntando a la imagen del ícono).
3. Mueve el archivo `.desktop` al directorio de aplicaciones de tu usuario:
```bash
   mv noni.desktop ~/.local/share/applications/
```

## 📝 Créditos y Licencias

* El código fuente de este proyecto es de mi autoría.
* El ícono de la aplicación utilizado en el archivo `.desktop` fue obtenido de Flaticon: 
  [Pokemon iconos creados por Roundicons Freebies - Flaticon](https://www.flaticon.es/icono-gratis/zubat_188999)
