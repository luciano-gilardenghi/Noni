# Noni - Gestor Nocturno de PC (GUI Version) 🌙

Noni es una aplicación de escritorio desarrollada en Python y GTK3 para entornos Linux. Automatiza y facilita la configuración del sistema para el consumo multimedia nocturno, integrando control de energía, gestión de audio mediante PulseAudio y manejo de ventanas.

Esta versión representa una refactorización completa del proyecto original (CLI), implementando una arquitectura basada en Programación Orientada a Objetos (OOP), hilos (`threading`) para procesos asíncronos y una interfaz gráfica diseñada con Glade y CSS.

## ✨ Características Principales

* **Interfaz Gráfica (GTK3):** Navegación fluida mediante `Gtk.Stack`, con soporte para atajos de teclado y diseño estilizado vía CSS.
* **Gestión de Energía Asíncrona:** Programación de apagado del sistema con un reloj en tiempo real ejecutándose en un hilo en segundo plano.
* **Sistema de Perfiles (JSON):** Carga dinámica de configuraciones de usuario (directorios, extensiones, parámetros de audio y video).
* **Audio Nocturno Avanzado:** Interacción nativa con el servidor de sonido mediante `pulsectl` para cambiar perfiles de tarjeta (HDMI/PC), desmutar y ajustar volumen.
* **Control de Ventanas y Reproducción:** Uso de `ewmh` para posicionar la ventana de VLC en monitores específicos y `Playerctl` (D-Bus) para controlar la reproducción.
* **Control de Pantallas:** Apagado de pantalla auxiliar mediante `screen_brightness_control`, con encendido automático sincronizado.

## 🛠️ Requisitos del Sistema

Este script está diseñado para distribuciones GNU/Linux (X11) y requiere las siguientes dependencias y librerías de Python:

**Dependencias del sistema (Debian/Ubuntu/Mint):**
```bash
sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-playerctl-2.0 vlc light
```

**Librerías de Python:**
```bash
pip install pulsectl ewmh natsort screeninfo screen-brightness-control PyGObject
```

## 🚀 Instalación y Ejecución

1. Clonar el repositorio en tu máquina local:
```bash
   git clone https://github.com/luciano-gilardenghi/noni.git
   cd noni
```

2. Para ejecutar el código fuente directamente desde la terminal:
```bash
   python3 main.py
```

## 📦 Crear Ejecutable e Integración al Escritorio (Opcional)

Si deseas utilizar Noni como una aplicación independiente sin necesidad de invocar a Python desde la terminal, puedes compilarlo utilizando **PyInstaller**:

```bash
pip install pyinstaller
pyinstaller --onefile main.py
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
* El ícono principal de la aplicación (`zubat.png`) fue obtenido de Flaticon: 
  [Pokemon iconos creados por Roundicons Freebies - Flaticon](https://www.flaticon.es/iconos-gratis/pokemon)
* Los íconos de la interfaz de usuario (Light/Dark mode, User) pertenecen a **Google Material Symbols**, utilizados bajo la licencia Apache 2.0.

