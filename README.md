# Noni - Gestor Nocturno de PC 🌙

Noni es una herramienta de línea de comandos (CLI) diseñada para entornos Linux que automatiza y facilita la configuración del sistema para el consumo multimedia nocturno. 

El script permite programar apagados automáticos, ajustar perfiles de audio para evitar ruidos molestos, apagar pantallas auxiliares sin afectar el brillo base del sistema, y generar listas de reproducción dinámicas para VLC.

## ✨ Características Principales

* **Gestión de Energía:** Programación y cancelación de apagado automático del sistema.
* **Sistema de Perfiles (JSON):** Creación, edición y eliminación de múltiples perfiles de usuario guardados dinámicamente en formato JSON.
* **Audio Nocturno Avanzado:** Interacción nativa con el servidor de sonido mediante `pulsectl` para cambiar perfiles de tarjeta (HDMI/PC), desmutar y ajustar volumen.
* **Control de Ventanas y Reproducción:** Uso de `ewmh` para posicionar la ventana de VLC en monitores específicos y `Playerctl` (D-Bus) para controlar la reproducción de forma asíncrona.
* **Control de Pantallas:** Apagado de pantalla auxiliar mediante `screen_brightness_control`, con encendido automático sincronizado con el apagado del sistema.

## 🛠️ Requisitos del Sistema

Este script está diseñado para distribuciones GNU/Linux (X11) y requiere las siguientes dependencias y librerías de Python:

**Dependencias del sistema:**
* `python3`
* `vlc` (reproductor multimedia)
* Librerías de desarrollo de GObject Introspection (ej. `libgirepository1.0-dev` en Debian/Ubuntu)

**Librerías de Python:**
Puedes instalar todas las dependencias ejecutando:
```bash
pip install pulsectl ewmh natsort screeninfo screen-brightness-control pynput PyGObject
```

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
