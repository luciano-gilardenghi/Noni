#!/usr/bin/env python3

import subprocess
from datetime import datetime
from screeninfo import get_monitors, Enumerator
import locale
import os
import json
import pulsectl
import time
from ewmh import EWMH
from natsort import natsorted
import screen_brightness_control as sbc
import gi
gi.require_version('Playerctl', '2.0')
from gi.repository import GLib, Playerctl
import utilidades as uti
from pathlib import Path
import logging
from pynput import mouse

logging.basicConfig(filename='registro.log', level=logging.INFO)

def cargar_configuracion(archivo): #error si no existe
    """Carga el archivo de configuracion."""
    with open(archivo, "r", encoding="utf-8") as a:
        return json.load(a)

def obtener_pantalla():
    """Devuelve 'HDMI-1' si hay una pantala conectada en dicha entrada, si no devuelve 'PC'."""
    if "HDMI-1" in [monitor.name for monitor in get_monitors(Enumerator.Xrandr)]:
        return "HDMI"
    return "PC"

def obtener_perfil_audio(pulse, indice_tarjeta):
    """Devuelve el perfil actual de la tarjeta de sonido."""
    return pulse.card_info(indice_tarjeta).profile_active.name

def muteado(sink):
    """Devuelve True si está activado el silencio, si no devuelve False."""
    return bool(sink.mute)

def obtener_volumen(sink):
    """Devuelve el volumen de salida actual como porcentaje."""
    return round(sink.volume.value_flat * 100)

def hay_playlist(configuracion):
    """Devuelve el contenido de la playlist del directorio dado en forma de lista.
    Si la playlist no existe o está vacía, devuelve None.
    """
    try:
        with open(f"{configuracion['directorio']}/{configuracion['nombre_playlist']}.m3u",
                "r", encoding="utf-8") as f:            
            playlist = [line.strip() for line in f]
            if playlist:
                return playlist
    except FileNotFoundError:
        pass
    return None

def obtener_apagado():
    """Devuelve la hora del apagado en formato datetime.
    Si no hay un apagado programado, devuelve None.
    """
    try:
        with open("/run/systemd/shutdown/scheduled", "r", encoding="utf-8") as apagado:
            fecha_usec = apagado.readline().split("USEC=")[1].strip()
    except FileNotFoundError:
        return None
    return datetime.fromtimestamp(float(fecha_usec) / 1e6)

def obtener_tipo_audio(configuracion):
    """Devuelve el perfil general (HDMI/PC) en el que está configurado el audio.
    Si este no coincide con ninguno de los dos, devuelve None."""
    with pulsectl.Pulse("Noni_obtener") as pulse:
        sink = pulse.get_sink_by_name(pulse.server_info().default_sink_name)
        if not muteado(sink):
            perfil = obtener_perfil_audio(pulse, sink.card)
            volumen = obtener_volumen(sink)
            for pantalla in ["HDMI", "PC"]:
                valor = configuracion[pantalla]
                if perfil == valor["perfil"] and volumen == valor["volumen"]:
                    return pantalla
        return None

def manejar_audio(pantalla, configuracion):
    """Devuelve una tupla con las listas de opciones para mostrar en el menu y las
    listas de los mensajes que se deben imprimir según la configuración del audio.
    """
    lista_opciones = []
    lista_impresion = []
    
    if pantalla == obtener_tipo_audio(configuracion):
        lista_impresion.append((imprimir_audio, ()))
    else:
        lista_opciones.append(("Configurar audio", configurar_audio_sistema,
                               (pantalla, configuracion)))

    return lista_opciones, lista_impresion

def manejar_apagado(apagado, configuracion):
    """Devuelve una tupla con las listas de opciones para mostrar en el menu y las
    listas de los mensajes que se deben imprimir según la configuración del apagado.
    """
    lista_opciones = []
    lista_impresion = []

    if configuracion["dia_noche"] == "noche":
        if apagado is not None:
            lista_opciones.extend((("Programar un nuevo apagado", apagar_sistema, ()),
                                   ("Cancelar el apagado programado", cancelar_apagado, ())))
            lista_impresion.append((imprimir_apagado, (apagado,)))
        else:
            lista_opciones.append(("Programar apagado", apagar_sistema, ()))

    return lista_opciones, lista_impresion

def manejar_playlist(playlist, configuracion):
    """Devuelve una tupla con las listas de opciones para mostrar en el menu y las
    listas de los mensajes que se deben imprimir según la configuración de la playlist.
    """
    lista_opciones = []
    lista_impresion = []

    if playlist is not None:
        lista_opciones.append(("Armar una nueva lista de reproducción", hacer_playlist,
                               (configuracion,)))
        lista_impresion.append((imprimir_playlist, (playlist,)))
    else:
        lista_opciones.append(("Armar una lista de reproducción", hacer_playlist, (configuracion,)))

    return lista_opciones, lista_impresion

def manejar_reproductor(playlist, pantalla, apagado, configuracion):
    """Devuelve una tupla con las listas de opciones para mostrar en el menu y las
    listas de los mensajes que se deben imprimir según la configuración de la pantalla.
    """
    lista_opciones = []
    lista_impresion = []

    if playlist is not None:
        if pantalla == "PC":
            lista_opciones.append(("Abrir reproductor", reproducir,
                                (pantalla, apagado, configuracion, False)))
        else:
            if apagado is None:
                lista_opciones.append(("Abrir reproductor", reproducir,
                                    (pantalla, apagado, configuracion, False)))
            lista_opciones.append(("Abrir reproductor y apagar la pantalla auxiliar",
                            reproducir, (pantalla, apagado, configuracion, True)))
            
    return lista_opciones, lista_impresion

def armar_listas(archivo_json, configuracion):
    """Devuelve una tupla con las listas de opciones para mostrar en el menu y las
    listas de los mensajes que se deben imprimir según todas las configuraciones.
    """
    apagado = obtener_apagado()
    pantalla = obtener_pantalla()
    playlist = hay_playlist(configuracion)

    lista_opciones = []
    lista_impresion = []

    for opciones, impresion in (manejar_apagado(apagado, configuracion),
                                manejar_audio(pantalla, configuracion),
                                manejar_playlist(playlist, configuracion),
                                manejar_reproductor(playlist, pantalla, apagado, configuracion)):
        lista_opciones.extend(opciones)
        lista_impresion.extend(impresion)
    lista_opciones += [("Configuración", configurar_programa, (archivo_json,)),
                       ("Salir", None, ())]
    
    return lista_opciones, lista_impresion #tengo que ver si puedo mejorarla

def imprimir_apagado(fecha):
    """Imprime un mensaje y la fecha formateada de un apagado programado."""
    print("¡Atención! Existe un apagado programado:")
    uti.imprimir_con_salto(formatear_fecha(fecha))

def formatear_fecha(fecha):
    """Devuelve una fecha como cadena con el formato adecuado."""
    return datetime.strftime(fecha, "%A %d de %B, %H:%M:%S").capitalize()

def configurar_region():
    """Establece la configuración regional a 'español (España)'
    con el conjunto de caracteres UTF-8.
    """
    locale.setlocale(locale.LC_TIME, "es_ES.utf8")

def imprimir_encabezado():
    """Limpia la consola y muestra el título del programa."""
    uti.limpiar_consola()
    uti.imprimir_con_salto("Apagado automático del pc")

def imprimir_mensajes(lista):
    """Imprime los mensajes de una lista de tuplas (funcion, argumentos)."""
    for mensaje, argumentos in lista:
        mensaje(*argumentos)

def obtener_brillo_auxiliar():
    """Devuelve el brillo de la pantalla auxiliar como porcentaje usando 'light'."""
    return sbc.get_brightness(method="light").pop()

def establecer_brillo_auxiliar(brillo):
    """Establece el brillo de la pantalla auxiliar en el porcentaje indicado usando 'light'."""
    sbc.set_brightness(value=brillo, method="light", force=True)

def apagar_sistema():
    """"Programa el apagado del sistema en el número de minutos ingresado por el usuario."""            
    minutos = obtener_minutos()
    uti.limpiar_consola()
    uti.llamar_terminal(f"shutdown -h +{minutos}")
    uti.imprimir_con_salto("Apagado programado exitosamente")
    input("Presione Enter para volver al menú principal")

def cancelar_apagado():
    """Cancela un apagado programado en el sistema."""
    uti.limpiar_consola()
    uti.llamar_terminal("shutdown -c")
    uti.imprimir_con_salto("Apagado cancelado exitosamente")
    input("Presione Enter para volver al menú principal")

def obtener_minutos():
    """Solicita el numero de minutos para programar el apagado."""
    while True:
        uti.limpiar_consola()
        try:
            return int(input("Establezca los minutos para programar el apagado: "))
        except ValueError:
            input("Error: Por favor, ingrese un valor válido de minutos")

def imprimir_audio():
    """Imprime un mensaje sobre el audio."""
    uti.imprimir_con_salto("El audio está configurado correctamente.")

def configurar_audio_sistema(pantalla, configuracion):
    """Selecciona el perfil indicado, desactiva el silencio y
    establece el volumen del sistema según la configuración."""
    with pulsectl.Pulse("Noni_sistema") as pulse:
        sink = pulse.get_sink_by_name(pulse.server_info().default_sink_name)
        uti.limpiar_consola()
        cambiar_perfil_audio(pulse, sink.card, configuracion[pantalla]["perfil"])
        try:
            desmutear_sistema(pulse, sink, configuracion) # no se por que falla
        except pulsectl.PulseOperationFailed:
            input("Ocurrió un error al configurar el audio. Inténtelo nuevamente")
            return
        establecer_volumen(pulse, sink, configuracion[pantalla]["volumen"])

    uti.imprimir_con_salto("Audio nocturno establecido.")
    input("Presione Enter para volver al menú principal")

def desmutear_sistema(pulse, sink, configuracion):
    intento = 0
    while intento < 300 * configuracion["factor_tiempo_limite"]:
        try:
            desmutear(pulse, sink)
            print(intento)
        except pulsectl.PulseOperationFailed as e:
            intento += 1
            error = e
        else:
            return
    raise error

def cambiar_perfil_audio(pulse, indice_tarjeta, perfil):
    """Establece el perfil de audio en el indicado según la pantalla."""
    pulse.card_profile_set_by_index(indice_tarjeta, perfil)

def desmutear(pulse, objeto):
    """Desactiva el silencio de un objeto en caso de estar activado."""
    pulse.mute(objeto, mute=False)

def establecer_volumen(pulse, objeto, volumen):
    """Establece el volumen de salida de un objeto en el porcentaje indicado."""
    pulse.volume_set_all_chans(objeto, volumen / 100)

def hacer_playlist(configuracion):
    """Crea una lista de contenidos según la elección del usuario y lo escribe en un archivo .m3u"""
    try:
        lista = elegir_contenidos(configuracion)
    except FileNotFoundError:
        uti.limpiar_consola()
        input(f"El directorio seleccionado no existe: '{configuracion['directorio']}'."
              " Compruebe la configuración del programa")
    except ValueError as e:
        uti.limpiar_consola()
        input(e)
    else:
        with open(f"{configuracion['directorio']}/{configuracion['nombre_playlist']}.m3u",
                  "w", encoding="utf-8") as f:
            f.write("\n".join(lista))
        uti.limpiar_consola()
        uti.imprimir_con_salto("Lista de reproducción creada exitosamente")
        input("Presione Enter para volver al menú principal")

def elegir_contenidos(configuracion):
    """Arma un menú de opciones con los contenidos presentes en
    el directorio y devuelve la selección del usuario como lista.
    """
    lista_mostrar = armar_opciones_playlist(configuracion)
    lista_guardar = []

    while True:
        uti.limpiar_consola()
        uti.imprimir_con_salto("Seleccione las películas o episodios que desea"
                               " agregar a la lista de reproducción:")
        mostrar_menu(lista_mostrar)
        eleccion = obtener_eleccion(lista_mostrar)
        if eleccion is not None:
            contenido = lista_mostrar.pop(eleccion)[1]
            if contenido is None: # None implica elección de salir
                break
            lista_guardar.append(contenido)

    return lista_guardar

def armar_opciones_playlist(configuracion):
    """Devuelve la lista de opciones de contenidos con las opciones globales."""
    lista = listar_videos(configuracion)
    lista_tuplas = list(zip([eliminar_extension(archivo) for archivo in lista], lista))
    return  lista_tuplas + [("Finalizar", None)]

def extension_permitida(archivo, configuracion):
    """Devuelve True si la extensión del archivo está permitida, si no devuelve False."""
    return any(archivo.endswith(ext) for ext in set(configuracion["extensiones"]))

def eliminar_extension(cadena):
    """Elimina la extension de una cadena de texto que representa un archivo"""
    return cadena.rsplit(".", 1)[0]

def listar_videos(configuracion):
    """Lista los archivos de video en la carpeta especificada ordenados alfabéticamente."""
    videos = [archivo for archivo in os.listdir(configuracion["directorio"]) if extension_permitida(
        archivo, configuracion)]
    if not videos:
        raise ValueError("No hay archivos de video con las extensiones seleccionadas en el"
                         f" directorio actual: '{configuracion['directorio']}'."
                         " Compruebe la configuración del programa")
    return natsorted(videos)

def imprimir_playlist(playlist):
    """Imprime el contenido de una lista de reproducción."""
    print("Lista de reproducción actual:")
    for contenido in playlist:
        print(" ·" + eliminar_extension(contenido))
    print()

def reproducir(pantalla, apagado, configuracion, apagar_auxiliar: bool):
    """Comprueba que no exista una instancia de VLC abierta, inica VLC, configura
    la ventana si es necesario, apaga la pantalla auxiliar según el parámetro, inicia
    la reproducción de VLC y espera el momento del apagado en caso de haber uno."""
    ewmh = EWMH()
    if hay_ventana(ewmh, "VLC"):
        uti.limpiar_consola()
        input("Una instancia del Reproductor Multimedia VLC ya se encuentra"
              " en ejecución. Ciérrela e intente nuevamente.")
        return

    try:
        abrir_vlc(pantalla, configuracion)
        if pantalla == "HDMI":
            configurar_ventana(ewmh, "VLC", pantalla, configuracion) # timeout
            if apagar_auxiliar:
                brillo_original = obtener_brillo_auxiliar()
                establecer_brillo_auxiliar(0)
        player = obtener_ventana_playerctl("vlc", configuracion) # timeout
        iniciar_vlc(player, configuracion)
        configurar_audio_reproductor("VLC", configuracion) # timeout
    except TimeoutError as e:
        uti.limpiar_consola()
        input(e)
        return
    except sbc.ScreenBrightnessError:
        uti.limpiar_consola()
        input("No se pudo apagar la pantalla auxiliar. Compruebe que"
              " el programa 'light' se encuentre instalado, así como las"
              " siguientes dependencias: 'screen_brightness_control'.")
        return

    if apagar_auxiliar:
        if apagado is not None:
            tiempo_restante = (apagado - datetime.now()).total_seconds()
            time.sleep(tiempo_restante - configuracion["tiempo_encendido"])
            establecer_brillo_auxiliar(brillo_original)
        else:
            loop = GLib.MainLoop()
            player.connect("exit", en_exit, brillo_original, loop)
            loop.run()
    uti.limpiar_consola()
    input("Presione Enter para volver al menú principal")

def abrir_vlc(pantalla, configuracion):
    comando = [
        "vlc",
        "--dbus",
        f"{configuracion['directorio']}/{configuracion['nombre_playlist']}.m3u",
        "--qt-fullscreen-screennumber", str(configuracion[pantalla]["indice"]),
        "-f",
        "--qt-minimal-view",
        "--qt-continue=0", 
        "--no-qt-start-minimized",
        "--no-qt-fs-controller",
        "--embedded-video",
        "--no-playlist-autostart",
        "--no-start-paused",
        "--no-loop",
        "--no-random"
        ]
    if configuracion["compresor"]["encendido"]:
        comando += [
            "--compressor-rms-peak", str(configuracion["compresor"]["rms_peak"]),
            "--compressor-attack", str(configuracion["compresor"]["attack"]),
            "--compressor-release", str(configuracion["compresor"]["release"]),
            "--compressor-threshold", str(configuracion["compresor"]["threshold"]),
            "--compressor-ratio", str(configuracion["compresor"]["ratio"]),
            "--compressor-knee", str(configuracion["compresor"]["knee"]),
            "--compressor-makeup-gain", str(configuracion["compresor"]["makeup_gain"])
            ]

    subprocess.Popen(comando, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def configurar_ventana(ewmh, nombre, pantalla, configuracion):
    """Obtiene la ventana a partir del nombre, la mueve según la
    configuración y aplica los cambios."""
    ventana = obtener_ventana_ewmh(ewmh, nombre, configuracion) # error: no se pudo abrir vlc
    mover_ventana(ewmh, ventana, pantalla, configuracion)
    ewmh.display.flush()

def obtener_ventana_ewmh(ewmh, nombre, configuracion):
    """Intenta obtener una ventana que contenga el nombre dado,
    si no lo logra levanta un error."""
    intento = 0
    while intento < 300 * configuracion["factor_tiempo_limite"]:
        ventanas = ewmh.getClientList()
        for ventana in ventanas:
            nombre_ventana = ewmh.getWmName(ventana)
            if nombre_ventana and nombre in nombre_ventana.decode():
                return ventana
        intento += 1
        time.sleep(0.1)
    raise TimeoutError("No se pudo iniciar el Reproductor Multimedia VLC. Compruebe"
                       " que el programa se encuentre instalado, así como las siguientes"
                       " dependencias: 'subprocess', 'ewmh'.")

def hay_ventana(ewmh, nombre):
    """Devuelve True si existe una ventana que contenga el
    nombre dado, si no devuelve False."""
    ventanas = ewmh.getClientList()
    for ventana in ventanas:
        nombre_ventana = ewmh.getWmName(ventana)
        if nombre_ventana and nombre in nombre_ventana.decode():
            return True
    return False

def mover_ventana(ewmh, ventana, pantalla, configuracion):
    """Para la ventana dada, desactiva la pantalla completa, desmaximiza,
    y mueve a una posición determinada según la configuración."""
    ewmh.setWmState(ventana, 0, '_NET_WM_STATE_FULLSCREEN')
    ewmh.setWmState(ventana, 0, '_NET_WM_STATE_MAXIMIZED_VERT', '_NET_WM_STATE_MAXIMIZED_HORZ')
    coordenada_x = configuracion[pantalla]["x"]
    coordenada_y = configuracion[pantalla]["y"]
    ewmh.setMoveResizeWindow(ventana, x=coordenada_x, y=coordenada_y, w=300, h=100)

def iniciar_vlc(player, configuracion):
    """Envía dos señales de inicio de reproducción del contenido
    al reproductor dado con un intervalo según la configuración."""
    for __ in range(2):
        time.sleep(0.3 * configuracion["factor_espera"])
        player.play()

def obtener_ventana_playerctl(nombre, configuracion):
    """Intenta obtener una reproductor con el nombre dado,
    si no lo logra levanta un error."""
    intento = 0
    while intento < 300 * configuracion["factor_tiempo_limite"]:
        for nombre_player in Playerctl.list_players():
            if nombre_player.name == nombre:
                ventana = Playerctl.Player.new_from_name(nombre_player)
                return ventana
        intento += 1
        time.sleep(0.1)
    raise TimeoutError("No se pudo iniciar el Reproductor Multimedia VLC. Compruebe"
                       " que el programa se encuentre instalado, así como las siguientes"
                       " dependencias: 'subprocess', 'PyGObject', 'Playerctl'.")

def configurar_audio_reproductor(nombre, configuracion):
    """Desactiva el silencio y establece el volumen del
    reproductor en su valor por defecto."""
    with pulsectl.Pulse(f"Noni_{nombre}") as pulse:
        ventana = obtener_ventana_pulse(pulse, nombre, configuracion)
        desmutear(pulse, ventana)
        establecer_volumen(pulse, ventana, 100)

def obtener_ventana_pulse(pulse, nombre, configuracion):
    """Intenta obtener una salida de Pulseaudio que contenga
    el nombre dado, si no lo logra levanta un error."""    
    intento = 0
    while intento < 300 * configuracion["factor_tiempo_limite"]:
        for ventana in pulse.sink_input_list():
            if nombre in ventana.proplist.get('application.name'):
                return ventana
        intento += 1
        time.sleep(0.1)
    raise TimeoutError("No se pudo configurar el audio del Reproductor Multimedia VLC."
                       " Compruebe que el programa PulseAudio se encuentre instalado,"
                       " así como las siguientes dependencias: 'Pulsectl'.")

def en_exit(player, brillo, loop):
    del player # Parámetro innecesario 
    establecer_brillo_auxiliar(brillo)
    loop.quit()

def menu_principal(lista_opciones, lista_impresion):
    while True:
        imprimir_encabezado()
        imprimir_mensajes(lista_impresion)
        mostrar_menu(lista_opciones)
        eleccion = obtener_eleccion(lista_opciones, "Seleccione una opción: ")
        if eleccion is not None: # None implica elección no válida
            break
    return ejecutar_y_devolver(lista_opciones, eleccion)

def obtener_eleccion(opciones_validas, mensaje=""):
    """Solicita una opción del menú y devuelve la elección si
    esta es un número, si no devuelve None."""
    print()
    entrada = input(mensaje)
    try:
        eleccion = int(entrada) - 1
    except ValueError:
        pass
    else:
        if 0 <= eleccion < len(opciones_validas):
            return eleccion
    input("Opción no válida. Por favor, elija una opción válida")
    return None

def mostrar_menu(opciones):
    """Genera un menú de opciones a partir de una lista/lista de tuplas e imprime
    el indice (empezando por 1) y el elemento/la primera componente de cada una.
    """
    for i, elemento in enumerate(opciones, start=1):
        opcion = elemento[0] if isinstance(elemento, tuple) else elemento
        print(f"{i}. {opcion}")

def ejecutar_y_devolver(lista_opciones, eleccion):
    funcion, argumentos = lista_opciones[eleccion][1:]
    if funcion is not None:
        funcion(*argumentos)
    return funcion

def configurar_programa(archivo_json):
    json_actual = archivo_json
    while True:

        lista_opciones = [("Seleccionar perfil", seleccionar_perfil, (json_actual,)),
                          ("Cambiar la configuración del perfil actual", ajustar_perfil, ()),
                          ("Crear un nuevo perfil", crear_perfil, (json_actual, )),
                          ("Eliminar un perfil", eliminar_perfil, (json_actual,)),
                          ("Volver al menú principal", None, ())]

        uti.limpiar_consola()
        uti.imprimir_con_salto("Configuración del programa")
        mostrar_menu(lista_opciones)
        eleccion = obtener_eleccion(lista_opciones)
        if eleccion is not None: # None implica elección no válida
            funcion, argumentos = lista_opciones[eleccion][1:]
            if funcion is not None: # None implica elección de salir
                json_actual = funcion(*argumentos)
            else:
                return

def seleccionar_perfil(archivo_json):
    lista_opciones = list(archivo_json["perfiles"])

    while True:
        uti.limpiar_consola()
        uti.imprimir_con_salto("Perfiles del Programa")
        uti.imprimir_con_salto("Seleccione un perfil:")
        mostrar_menu(lista_opciones)
        eleccion = obtener_eleccion(lista_opciones)
        if eleccion is not None:
            break

    archivo_json["perfil_actual"] = lista_opciones[eleccion]
    guardar_configuracion("perfil.json", archivo_json)
    uti.limpiar_consola()
    uti.imprimir_con_salto("El perfil fue seleccionado exitosamente")
    input("Presione Enter para volver al menú de configuración")

def ajustar_perfil():
    lista_opciones = [("General", ajustar_general, ()),
                      ("Audio", ajustar_audio, ()),
                      ("Errores y bugs", ajustar_errores, ()),
                      ("Volver a Configuración", None, ())]

    while True:
        uti.limpiar_consola()
        uti.imprimir_con_salto("Configuración del Perfil")
        mostrar_menu(lista_opciones)
        eleccion = obtener_eleccion(lista_opciones)
        if eleccion is not None: # None implica elección no válida
            funcion, argumentos = lista_opciones[eleccion][1:]
            if funcion is not None: # None implica elección de salir
                funcion(*argumentos)
            else:
                return

def ajustar_general():
    while True:
        archivo_json = cargar_configuracion("perfil.json")
        configuracion = archivo_json["perfiles"][archivo_json["perfil_actual"]]
        
        lista_opciones = [("Tipo de perfil", ajustar_dia_noche),
                          ("Directorio", ajustar_directorio),
                          ("Extensiones", ajustar_extensiones),
                          ("Volver a Configuración del Perfil", None)]

        uti.limpiar_consola()
        uti.imprimir_con_salto("Configuración general")
        mostrar_menu(lista_opciones)
        eleccion = obtener_eleccion(lista_opciones)
        if eleccion is not None: # None implica elección no válida
            funcion = lista_opciones[eleccion][1]
            if funcion is not None: # None implica elección de salir
                funcion(archivo_json, configuracion)
            else:
                return

def ajustar_dia_noche(archivo_json, configuracion):
    lista_opciones = [("Día", "dia"), ("Noche", "noche")]

    while True:
        uti.limpiar_consola()
        uti.imprimir_con_salto("Perfil de Día/Noche")
        uti.imprimir_con_salto("Elija si el perfil actual será diurno o nocturno."
                               " El perfil nocturno permite establecer un apagado"
                               " programado del sistema antes de iniciar el reproductor.")
        mostrar_menu(lista_opciones)
        eleccion = obtener_eleccion(lista_opciones)
        if eleccion is not None:
            break
    configuracion["dia_noche"] = lista_opciones[eleccion][1]
    guardar_configuracion("perfil.json", archivo_json)
    uti.limpiar_consola()
    uti.imprimir_con_salto("El perfil fue configurado exitosamente")
    input("Presione Enter para volver al menú anterior")

def ajustar_directorio(archivo_json, configuracion):
    while True:
        uti.limpiar_consola()
        uti.imprimir_con_salto("Directorio")
        uti.imprimir_con_salto("Elija el directorio donde el programa buscará"
                               " el contenido multimedia y guardará la lista de"
                               " reproducción con su selección.")

        nuevo_directorio = input(f"El directorio actual es: '{configuracion['directorio']}'."
                                 " Presione Enter para seguir usando este"
                                 " directorio, o ingrese uno nuevo a continuación: ").strip()

        if not nuevo_directorio:
            break
        if nuevo_directorio not in {".", ".."} and Path(nuevo_directorio).is_dir():
            configuracion["directorio"] = nuevo_directorio
            guardar_configuracion("perfil.json", archivo_json)
            break
        input("Error: El directorio ingresado no existe. Por favor, ingrese un directorio válido")

    uti.limpiar_consola()
    uti.imprimir_con_salto("El directorio fue configurado exitosamente")
    input("Presione Enter para volver al menú anterior")

def ajustar_extensiones(archivo_json, configuracion):
    lista_mostrar = ["mp4", "mkv", "webm", "avi", "flv", "ogg", "Finalizar"]
    lista_guardar = []

    while True:
        uti.limpiar_consola()
        uti.imprimir_con_salto("Seleccione las extensiones que podrán tener"
                               " los archivos de video que se mostrarán")
        mostrar_menu(lista_mostrar)
        eleccion = obtener_eleccion(lista_mostrar)
        if eleccion is not None:
            contenido = lista_mostrar.pop(eleccion)
            if contenido == "Finalizar":
                break
            lista_guardar.append(contenido)

    configuracion["extensiones"] = lista_guardar
    guardar_configuracion("perfil.json", archivo_json)
    uti.limpiar_consola()
    uti.imprimir_con_salto("Extensiones configuradas exitosamente")
    input("Presione Enter para volver al menú anterior")

def ajustar_audio():
    while True:
        archivo_json = cargar_configuracion("perfil.json")
        configuracion = archivo_json["perfiles"][archivo_json["perfil_actual"]]

        lista_opciones = [("Volumen HDMI", ajustar_volumen_hdmi, (archivo_json, configuracion)),
                          ("Volumen PC", ajustar_volumen_pc, (archivo_json, configuracion)),
                          ("Perfil HDMI", ajustar_perfil_hdmi, (archivo_json, configuracion)),
                          ("Perfil PC", ajustar_perfil_pc, (archivo_json, configuracion)),
                          ("Compresor", ajustar_compresor, ()),
                          ("Volver a Configuración del Perfil", None, ())]

        uti.limpiar_consola()
        uti.imprimir_con_salto("Configuración del Audio")
        mostrar_menu(lista_opciones)
        eleccion = obtener_eleccion(lista_opciones)
        if eleccion is not None: # None implica elección no válida
            funcion, argumentos = lista_opciones[eleccion][1:]
            if funcion is not None: # None implica elección de salir
                funcion(*argumentos)
            else:
                return

def ajustar_volumen_hdmi(archivo_json, configuracion):
    while True:
        uti.limpiar_consola()
        uti.imprimir_con_salto("Volumen HDMI")

        try:
            nuevo_volumen = int(input(r"Establezca el volumen (1%-100%) del sistema cuando"
                                      " se encuentra conectada una pantalla por HDMI: ").strip())
        except ValueError:
            pass
        else:
            if 0 < nuevo_volumen <= 100:
                break
        input("Error: Por favor, ingrese un volumen válido")

    configuracion["HDMI"]["volumen"] = nuevo_volumen
    guardar_configuracion("perfil.json", archivo_json)
    uti.limpiar_consola()
    uti.imprimir_con_salto("El volumen fue configurado exitosamente")
    input("Presione Enter para volver al menú anterior")

def ajustar_volumen_pc(archivo_json, configuracion):
    while True:
        uti.limpiar_consola()
        uti.imprimir_con_salto("Volumen PC")

        try:
            nuevo_volumen = int(input(r"Establezca el volumen (1%-100%) del sistema cuando"
                                      " no se encuentra conectada una pantalla por HDMI: ").strip())
        except ValueError:
            pass
        else:
            if 0 < nuevo_volumen <= 100:
                break
        input("Error: Por favor, ingrese un volumen válido")

    configuracion["PC"]["volumen"] = nuevo_volumen
    guardar_configuracion("perfil.json", archivo_json)
    uti.limpiar_consola()
    uti.imprimir_con_salto("El volumen fue configurado exitosamente")
    input("Presione Enter para volver al menú anterior")

def ajustar_perfil_hdmi(archivo_json, configuracion):
    with pulsectl.Pulse("Noni_ajustar_hdmi") as pulse:
        indice = pulse.get_sink_by_name(pulse.server_info().default_sink_name).card
        lista_perfiles = pulse.card_info(indice).profile_list
        lista_opciones = [(perfil.description, perfil.name) for perfil in lista_perfiles[:-1]]

    for perfil in lista_opciones:
        if configuracion["HDMI"]["perfil"] == perfil[1]:
            perfil_actual = perfil[0]

    while True:
        uti.limpiar_consola()
        uti.imprimir_con_salto("Perfil HDMI")
        uti.imprimir_con_salto("Establezca el perfil de PulseAudio del sistema cuando"
                               " se encuentra conectada una pantalla por HDMI. El perfil"
                               f" actual es: '{perfil_actual}'.")
        mostrar_menu(lista_opciones)
        eleccion = obtener_eleccion(lista_opciones)
        if eleccion is not None: # None implica elección no válida
            break

    configuracion["HDMI"]["perfil"] = lista_opciones[eleccion][1]
    guardar_configuracion("perfil.json", archivo_json)
    uti.limpiar_consola()
    uti.imprimir_con_salto("El perfil fue seleccionado exitosamente")
    input("Presione Enter para volver al menú anterior")

def ajustar_perfil_pc(archivo_json, configuracion):
    with pulsectl.Pulse("Noni_ajustar_pc") as pulse:
        indice = pulse.get_sink_by_name(pulse.server_info().default_sink_name).card
        lista_perfiles = pulse.card_info(indice).profile_list
        lista_opciones = [(perfil.description, perfil.name) for perfil in lista_perfiles[:-1]]

    for perfil in lista_opciones:
        if configuracion["PC"]["perfil"] == perfil[1]:
            perfil_actual = perfil[0]

    while True:
        uti.limpiar_consola()
        uti.imprimir_con_salto("Perfil PC")
        uti.imprimir_con_salto("Establezca el perfil de PulseAudio del sistema cuando"
                               "no se encuentra conectada una pantalla por HDMI. El perfil"
                               f" configurado actualmente es: '{perfil_actual}'.")
        mostrar_menu(lista_opciones)
        eleccion = obtener_eleccion(lista_opciones)
        if eleccion is not None: # None implica elección no válida
            break

    configuracion["PC"]["perfil"] = lista_opciones[eleccion][1]
    guardar_configuracion("perfil.json", archivo_json)
    uti.limpiar_consola()
    uti.imprimir_con_salto("El perfil fue seleccionado exitosamente")
    input("Presione Enter para volver al menú anterior")

def ajustar_compresor():
    while True:
        archivo_json = cargar_configuracion("perfil.json")
        compresor = archivo_json["perfiles"][archivo_json["perfil_actual"]]["compresor"]

        lista_opciones = [("Encender/Apagar el compresor", ajustar_compresor_encendido)]
        if compresor["encendido"]:
            lista_opciones += [("RMS/Pico", ajustar_compresor_rms),
                               ("Ataque", ajustar_compresor_attack),
                               ("Publicación", ajustar_compresor_release),
                               ("Umbral", ajustar_compresor_threshold),
                               ("Proporción", ajustar_compresor_ratio),
                               ("Radio", ajustar_compresor_knee),
                               ("Maquillaje", ajustar_compresor_makeup)
                               ]
        lista_opciones += [("Volver al menú anterior", None)]

        uti.limpiar_consola()
        uti.imprimir_con_salto("Configuración del Compresor")
        uti.imprimir_con_salto("El compresor es una herramienta procesamiento"
                               " de audio proporcionada por el reproductor VLC"
                               " destinada a reducir el rango dinámico de la pista."
                               " Puede ajustar sus parámetros desde aquí. Para"
                               " más información consulte la documentación del"
                               " reproductor")
        mostrar_menu(lista_opciones)
        eleccion = obtener_eleccion(lista_opciones)
        if eleccion is not None: # None implica elección no válida
            funcion = lista_opciones[eleccion][1]
            if funcion is not None: # None implica elección de salir
                funcion(archivo_json, compresor)
            else:
                return

def ajustar_compresor_encendido(archivo_json, compresor):
    lista_opciones = [("Encender", True), ("Apagar", False)]

    while True:
        uti.limpiar_consola()
        uti.imprimir_con_salto("Encendido/Apagado del Compresor")
        uti.imprimir_con_salto("Establezca si desea utilizar"
                               " el compresor de audio")       
        mostrar_menu(lista_opciones)
        eleccion = obtener_eleccion(lista_opciones)
        if eleccion is not None:
            break
    compresor["encendido"] = lista_opciones[eleccion][1]
    guardar_configuracion("perfil.json", archivo_json)
    uti.limpiar_consola()
    uti.imprimir_con_salto("El compresor fue configurado exitosamente")
    input("Presione Enter para volver al menú anterior")

def ajustar_compresor_rms(archivo_json, compresor):
    while True:
        uti.limpiar_consola()
        uti.imprimir_con_salto("RMS/Pico")

        try:
            nuevo_valor = float(input("Establezca el RMS/Pico (0.0-1.0): ").strip())
        except ValueError:
            pass
        else:
            if 0.0 <= nuevo_valor <= 1.0:
                break
        input("Error: Por favor, ingrese un valor válido")

    compresor["rms_peak"] = nuevo_valor
    guardar_configuracion("perfil.json", archivo_json)
    uti.limpiar_consola()
    uti.imprimir_con_salto("El compresor fue configurado exitosamente")
    input("Presione Enter para volver al menú anterior")

def ajustar_compresor_attack(archivo_json, compresor):
    while True:
        uti.limpiar_consola()
        uti.imprimir_con_salto("Ataque")

        try:
            nuevo_valor = float(input("Establezca el tiempo de ataque en"
                                      " milisegundos (1.5-400.0): ").strip())
        except ValueError:
            pass
        else:
            if 1.5 <= nuevo_valor <= 400.0:
                break
        input("Error: Por favor, ingrese un valor válido")

    compresor["attack"] = nuevo_valor
    guardar_configuracion("perfil.json", archivo_json)
    uti.limpiar_consola()
    uti.imprimir_con_salto("El compresor fue configurado exitosamente")
    input("Presione Enter para volver al menú anterior")

def ajustar_compresor_release(archivo_json, compresor):
    while True:
        uti.limpiar_consola()
        uti.imprimir_con_salto("Publicación")

        try:
            nuevo_valor = float(input("Establezca el tiempo de publicación"
                                      " en milisegundos (2.0-800.0): ").strip())
        except ValueError:
            pass
        else:
            if 2.0 <= nuevo_valor <= 800.0:
                break
        input("Error: Por favor, ingrese un valor válido")

    compresor["release"] = nuevo_valor
    guardar_configuracion("perfil.json", archivo_json)
    uti.limpiar_consola()
    uti.imprimir_con_salto("El compresor fue configurado exitosamente")
    input("Presione Enter para volver al menú anterior")

def ajustar_compresor_threshold(archivo_json, compresor):
    while True:
        uti.limpiar_consola()
        uti.imprimir_con_salto("Umbral")

        try:
            nuevo_valor = float(input("Establezca el nivel del límete en"
                                      " decibeles (-30.0-0.0): ").strip())
        except ValueError:
            pass
        else:
            if -30.0 <= nuevo_valor <= 0.0:
                break
        input("Error: Por favor, ingrese un valor válido")

    compresor["threshold"] = nuevo_valor
    guardar_configuracion("perfil.json", archivo_json)
    uti.limpiar_consola()
    uti.imprimir_con_salto("El compresor fue configurado exitosamente")
    input("Presione Enter para volver al menú anterior")

def ajustar_compresor_ratio(archivo_json, compresor):
    while True:
        uti.limpiar_consola()
        uti.imprimir_con_salto("Proporción")

        try:
            nuevo_valor = float(input("Establezca la proporción (1.0-20.0): ").strip())
        except ValueError:
            pass
        else:
            if 1.0 <= nuevo_valor <= 20.0:
                break
        input("Error: Por favor, ingrese un valor válido")

    compresor["ratio"] = nuevo_valor
    guardar_configuracion("perfil.json", archivo_json)
    uti.limpiar_consola()
    uti.imprimir_con_salto("El compresor fue configurado exitosamente")
    input("Presione Enter para volver al menú anterior")

def ajustar_compresor_knee(archivo_json, compresor):
    while True:
        uti.limpiar_consola()
        uti.imprimir_con_salto("Radio")

        try:
            nuevo_valor = float(input("Establezca el radio de curvatura"
                                      " en decibeles (1.0-10.0): ").strip())
        except ValueError:
            pass
        else:
            if 1.0 <= nuevo_valor <= 10.0:
                break
        input("Error: Por favor, ingrese un valor válido")

    compresor["knee"] = nuevo_valor
    guardar_configuracion("perfil.json", archivo_json)
    uti.limpiar_consola()
    uti.imprimir_con_salto("El compresor fue configurado exitosamente")
    input("Presione Enter para volver al menú anterior")

def ajustar_compresor_makeup(archivo_json, compresor):
    while True:
        uti.limpiar_consola()
        uti.imprimir_con_salto("Maquillaje")

        try:
            nuevo_valor = float(input("Establezca la ganancia de maquillaje"
                                      " en decibeles (0.0-24.0): ").strip())
        except ValueError:
            pass
        else:
            if 0.0 <= nuevo_valor <= 24.0:
                break
        input("Error: Por favor, ingrese un valor válido")

    compresor["makeup_gain"] = nuevo_valor
    guardar_configuracion("perfil.json", archivo_json)
    uti.limpiar_consola()
    uti.imprimir_con_salto("El compresor fue configurado exitosamente")
    input("Presione Enter para volver al menú anterior")

def ajustar_errores():
    while True:
        archivo_json = cargar_configuracion("perfil.json")
        configuracion = archivo_json["perfiles"][archivo_json["perfil_actual"]]

        lista_opciones = [("Factor de Espera", ajustar_espera),
                          ("Factor de tiempo límite", ajustar_tiempo_limite),
                          ("Tiempo de encendido", ajustar_encendido),
                          ("Coordenadas del HDMI", ajustar_coordenadas),
                          ("Volver a Configuración del Perfil", None)]

        uti.limpiar_consola()
        uti.imprimir_con_salto("Configuración del Audio")
        mostrar_menu(lista_opciones)
        eleccion = obtener_eleccion(lista_opciones)
        if eleccion is not None: # None implica elección no válida
            funcion = lista_opciones[eleccion][1]
            if funcion is not None: # None implica elección de salir
                funcion(archivo_json, configuracion)
            else:
                return

def ajustar_espera(archivo_json, configuracion):
    factor = configuracion["factor_espera"]
    while True:
        uti.limpiar_consola()
        uti.imprimir_con_salto("Factor de espera")
        uti.imprimir_con_salto("Aumentar el Factor de espera puede resultar útil"
                               " si experimenta fallos visuales a la hora de"
                               " comenzar la reproducción del contenido. Se"
                               " recomienda aumentar este valor en una unidad"
                               " hasta ver solucionado el problema. Cifras elevadas"
                               " podrían afectar la fluidez de la ejecución del"
                               f" programa. El Factor actual es: {factor}")

        try:
            nuevo_factor = int(input("Ingrese el nuevo valor: ").strip())
        except ValueError:
            pass
        else:
            if 0 < nuevo_factor <= 100:
                break
        input("Error: Por favor, ingrese un valor válido")

    configuracion["factor_espera"] = nuevo_factor
    guardar_configuracion("perfil.json", archivo_json)
    uti.limpiar_consola()
    uti.imprimir_con_salto("El Factor de espera fue configurado exitosamente")
    input("Presione Enter para volver al menú anterior")

def ajustar_tiempo_limite(archivo_json, configuracion):
    factor = configuracion["factor_tiempo_limite"]
    while True:
        uti.limpiar_consola()
        uti.imprimir_con_salto("Factor de tiempo límite")
        uti.imprimir_con_salto("El programa debe esperar a que ciertos procesos"
                               " externos se ejecuten, por lo que aumentar"
                               " el Factor de tiempo límite puede resultar útil"
                               " en equipos de bajos recursos. Se recomienda aumentar"
                               " este valor en una unidad hasta ver solucionado el"
                               f" problema. El Factor actual es: {factor}")

        try:
            nuevo_factor = int(input("Ingrese el nuevo valor: ").strip())
        except ValueError:
            pass
        else:
            if 0 < nuevo_factor <= 10:
                break
        input("Error: Por favor, ingrese un valor válido")

    configuracion["factor_tiempo_limite"] = nuevo_factor
    guardar_configuracion("perfil.json", archivo_json)
    uti.limpiar_consola()
    uti.imprimir_con_salto("El Factor de tiempo límite fue configurado exitosamente")
    input("Presione Enter para volver al menú anterior")

def ajustar_encendido(archivo_json, configuracion):
    tiempo = configuracion["tiempo_encendido"]
    while True:
        uti.limpiar_consola()
        uti.imprimir_con_salto("Tiempo de encendido")
        uti.imprimir_con_salto("Luego de que el programa apaga la pantalla auxiliar,"
                               " si el usuario programó un apagado del sistema,"
                               " esperará a que falte una determinada cantidad de"
                               " segundos para este que ocurra y encenderá nuevamente"
                               " la pantalla para garantizar que en el futuro el equipo"
                               " se inicie con el nivel de brillo que tenía antes de"
                               " apagar la pantalla.")
        uti.imprimir_con_salto("Puede aumentar el tiempo que transcurre entre que se"
                               " enciende la pantalla y se apaga el sistema si este"
                               " se enciende con el brillo mínimo luego de utilizar el"
                               f" programa. El Tiempo actual es de: {tiempo} segundos")

        try:
            nuevo_tiempo = int(input("Ingrese el nuevo valor en segundos: ").strip())
        except ValueError:
            pass
        else:
            if 0 < nuevo_tiempo <= 120:
                break
        input("Error: Por favor, ingrese un tiempo válido")

    configuracion["tiempo_encendido"] = nuevo_tiempo
    guardar_configuracion("perfil.json", archivo_json)
    uti.limpiar_consola()
    uti.imprimir_con_salto("El Tiempo de encendido fue configurado exitosamente")
    input("Presione Enter para volver al menú anterior")

def ajustar_coordenadas(archivo_json, configuracion):
    lista_opciones = [("Establecer nuevas coordenadas", obtener_coordenadas),
                      ("Volver al menú anterior", None)]

    x = configuracion["HDMI"]["x"]
    y = configuracion["HDMI"]["y"]

    while True:
        uti.limpiar_consola()
        uti.imprimir_con_salto("Coordenadas del HDMI")
        uti.imprimir_con_salto("Para minimizar la posibilidad de aparición de"
                               " errores al establecer la pantalla completa en"
                               " el repoductor VLC cuando existe un monitor"
                               " conectado por HDMI el programa sitúa la ventana"
                               " en una posición cualquiera de dicha pantalla.")
        uti.imprimir_con_salto(f"Las coordenadas actuales son: ({x}, {y}). Puede"
                               " volver a seleccionarlas coordenadas si el"
                               " reproductor no se inicia en la pantalla HDMI"
                               " cuando debería")

        mostrar_menu(lista_opciones)
        eleccion = obtener_eleccion(lista_opciones)
        if eleccion is not None:
            funcion = lista_opciones[eleccion][1]
            if funcion is not None: # None implica elección de salir
                nuevas_coordenadas = funcion()
                break
            return

    configuracion["HDMI"]["x"], configuracion["HDMI"]["y"] = nuevas_coordenadas
    guardar_configuracion("perfil.json", archivo_json)
    uti.limpiar_consola()
    uti.imprimir_con_salto("Las coordenadas fueron configuradas exitosamente")
    input("Presione Enter para volver al menú anterior")

def obtener_coordenadas():
    uti.limpiar_consola()
    uti.imprimir_con_salto("Mueva el mouse para iniciar la configuración")
    with mouse.Events() as eventos:
        for evento in eventos: # Bucle infinito
            uti.limpiar_consola()
            uti.imprimir_con_salto("Sitúe el cursor en cualquier lugar de la pantalla HDMI y"
                                   " presione el botón izquierdo para ingresar sus coordenadas.")
            print(f"La posición actual del mouse es: ({evento.x}, {evento.y})")
            if hasattr(evento, "button") and evento.button == mouse.Button.left:
                return evento.x, evento.y # Es la única salida

def crear_perfil(archivo_json):
    while True:
        uti.limpiar_consola()
        uti.imprimir_con_salto("Crear un nuevo perfil")

        try:
            nombre = input("Ingrese el nombre del nuevo perfil: ").strip()

            if not nombre:
                raise ValueError("Error: El nombre debe tener al menos un caracter."
                    " Por favor, ingrese un nombre válido")
            if nombre in archivo_json["perfiles"]:
                raise ValueError(f"Error: Ya existe un perfil con el nombre '{nombre}'."
                    " Por favor, ingrese un nombre válido")
            if len(nombre) > 20:
                raise ValueError("Error: El nombre debe tener menos de 20 caracteres."
                    " Por favor, ingrese un nombre válido")
            if "/" in nombre:
                raise ValueError("Error: El nombre no puede contener el siguiente símbolo: '/'."
                                 " Por favor, ingrese un nombre válido")

            break
        except ValueError as e:
            input(e)

    archivo_json["perfiles"][nombre] = {
        "nombre_playlist": f"{nombre}-playlist",
        "dia_noche": "noche",
        "directorio": "/home/luciano/Noni",
        "extensiones": [
            "mkv",
            "mp4"
            ],
        "compresor": {
            "encendido": True,
            "rms_peak": 0.0,
            "attack": 1.5,
            "release": 104.7,
            "threshold": -30.0,
            "ratio": 20.0,
            "knee": 1.0,
            "makeup_gain": 10.9
            },
        "HDMI": {
            "indice": 1,
            "perfil": "output:hdmi-surround",
            "volumen": 40,
            "x": 408,
            "y": 292
            },
        "PC": {
            "indice": 0,
            "perfil": "output:analog-stereo",
            "volumen": 50
            },
        "factor_espera": 1,
        "factor_tiempo_limite": 1,
        "tiempo_encendido": 5
        }

    guardar_configuracion("perfil.json", archivo_json)
    uti.limpiar_consola()
    uti.imprimir_con_salto("El perfil fue creado exitosamente")
    input("Presione Enter para volver al menú de configuración")


def eliminar_perfil(archivo_json):
    lista_opciones = [perfil for perfil in archivo_json["perfiles"] if
                      perfil != archivo_json["perfil_actual"]]

    while True:
        uti.limpiar_consola()
        uti.imprimir_con_salto("Eliminar perfil")
        uti.imprimir_con_salto("Seleccione el perfil que desea eliminar:")

        if not lista_opciones:
            uti.limpiar_consola()
            uti.imprimir_con_salto("No existen perfiles adicionales para eliminar")
            input("Presione Enter para volver al menú de configuración")
            return

        lista_opciones += ["Cancelar"]
        mostrar_menu(lista_opciones)
        eleccion = obtener_eleccion(lista_opciones)

        if eleccion is not None:
            perfil = lista_opciones[eleccion]
            if perfil == "Cancelar":
                return

            del archivo_json["perfiles"][perfil]
            guardar_configuracion("perfil.json", archivo_json)
            uti.limpiar_consola()
            uti.imprimir_con_salto("El perfil fue eliminado exitosamente")
            input("Presione Enter para volver al menú de configuración")
            return


def guardar_configuracion(archivo, configuracion):
    with open(archivo, 'w', encoding="utf-8") as a:
        json.dump(configuracion, a, indent=4)

def main():
    """Configura la región. Evalúa si existe un apagado programado y si el audio nocturno está configurado, arma un menú de 
    opciones en consecuencia y ejecuta según la entrada del usuario."""

    configurar_region()

    while True:
        archivo_json = cargar_configuracion("perfil.json")
        configuracion = archivo_json["perfiles"][archivo_json["perfil_actual"]]
        lista_opciones, lista_impresion = armar_listas(archivo_json, configuracion)
        eleccion = menu_principal(lista_opciones, lista_impresion)
        if eleccion is None:
            break

if __name__ == "__main__":
    main()