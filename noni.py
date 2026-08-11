#!/usr/bin/env python3

"""
Noni

Este programa se basa en dos parámtros fundamentales: la existencia de un
apagado programado y la configuracion del audio en parámetros acordes al uso
nocturno. En función de ambos, mostrará las opciones que permiten programar un
apagado, cancelarlo y aplicar el audio nocturno. Además, permite apagar la pantalla
que no se va a utilizar, sin que esto modifique el nivel de brillo que tendrá
el sistema en el siguiente inicio.

Autor: [Luciano Gilardenghi]
Fecha: [15/08/2023]
"""

import os
import locale
import sys
import select
import re
from datetime import datetime

estado = {"directorio": "/home/luciano/Noni"}

directorio_actual = "/home/luciano/Noni"
formato_fecha = "%A %d de %B, %H:%M:%S"


def obtener_minutos():
    """Solicita un numero de minutos para programar el apagado."""
    while True:
        try:
            limpiar_consola()
            return int(input("Establezca los minutos para programar el apagado: "))
        except ValueError:
            input("Error: Por favor, ingrese un valor válido de minutos")

def apagar_sistema():
    """"Permite programar un apagado del sistema en un número de minutos ingresado por el usuario."""            
    minutos = obtener_minutos()
    os.system (f"shutdown -h +{minutos} 'El sistema se apagará en {minutos} minutos' > /dev/null 2>&1")
    limpiar_consola()
    print(f"El sistema se apagará en {minutos} minutos")
    print()
    input("Presione Enter para volver al menú principal")

def cancelar_apagado():
    """Cancela un apagado programado en el sistema."""
    limpiar_consola()
    os.system ("shutdown -c")
    print("Apagado cancelado")
    print()
    input("Presione Enter para volver al menú principal")

def limpiar_consola():
    """Limpia la consola utilizando 'clear'."""
    os.system("clear")

def formatear_fecha(fecha, formato):
    """Devuelve la fecha en el formato adecuado."""
    fecha_formateada = datetime.strftime(fecha, formato)
    return fecha_formateada[0].capitalize() + fecha_formateada[1:]

def desformatear_fecha(fecha, formato):
    """Devuelve la fecha como objeto datetime sobre el que operar."""
    return datetime.strptime(fecha, formato)     

def hay_apagado():
    """Devuelve la fecha y hora exactas (sin formato) en caso de haber un apagado programado, si no, devuelve False."""
    resultado_comando = os.popen("date -d @`cat /run/systemd/shutdown/scheduled 2>/dev/null"
                                 "| head -n 1 | cut -c6-15` 2>&1").read().strip()
    print(resultado_comando)
    if "fecha inválida" in resultado_comando:
        return False
    return datetime.strptime(resultado_comando[:-4], "%a %d %b %Y %H:%M:%S")

def tiempo_para_apagar(apagado):
    """Devuelve el tiempo restante para que se apague el equipo."""
    return apagado-eliminar_microsegundos(datetime.now())

def tiempo_limite(apagado):
    """Devuelve True si faltan 15 segundos para que se apague el equipo, si no, devuelve False."""
    if tiempo_para_apagar(apagado).total_seconds() <= 15:
        return True
    return False

def imprimir_apagado(fecha):
    """Imprime un mensaje y la fecha formateada del apagado programado."""
    print("¡Atención! Existe un apagado programado:")
    print(formatear_fecha(fecha, formato_fecha))
    print()

def eliminar_microsegundos(hora):
    """Devuelve la hora sin microsegundos."""
    hora_sin_microsegundos = datetime(
                                year=hora.year,
                                month=hora.month,
                                day=hora.day,
                                hour=hora.hour,
                                minute=hora.minute,
                                second=hora.second
                                )
    return hora_sin_microsegundos

def mostrar_menu(opciones_validas):
    """Genera un menú de opciones a partir de una lista de tuplas y devuelve la primera componente de cada una."""
    for i, (descripcion, __) in enumerate(opciones_validas, start=1):
        print(f"{i}. {descripcion}")

def obtener_eleccion(opciones_validas):
    """Solicita una opción del menú y devuelve la elección si esta es un número."""
    entrada = input("Seleccione una opción: ")
    if entrada.isdigit():
        eleccion = int(entrada) -1
        if 0 <= eleccion < len(opciones_validas):
            return eleccion
    else:
        input("Opción no válida. Por favor, elija una opción válida")
        return None

def ejecutar_opcion(opciones_validas, eleccion):
    """Ejecuta la función asociada a una opción de una lista de tuplas si esta no es None."""
    funcion = opciones_validas[eleccion][1]
    if funcion is not None:
        funcion()
        return True
    return False

def apagar_pantalla():
    """Baja el brillo de la pantalla eDP-1 hasta el mínimo, apagándola."""
    os.system("sudo light -U 100")

def encender_pantalla():
    """Establece el brillo de la pantalla eDP-1 al máximo."""
    os.system("sudo light -A 100")
    
def porcentaje_a_valor(porcentaje):
    """Convierte la cantidad porcentual de volumen a un valor absoluto."""
    return int(porcentaje/100*65536)

def establecer_volumen(porcentaje):
    """Establece el volumen de salida del sistema en el porcentaje indicado."""
    valor = porcentaje_a_valor(porcentaje)
    os.system(f"pactl set-sink-volume alsa_output.pci-0000_00_1b.0.hdmi-surround {valor}")

def cambiar_perfil():
    """Establece el perfil de audio como HDMI Surround 5.1 + Entrada estéreo analógico."""
    os.system("pacmd set-card-profile 0 output:hdmi-surround+input:analog-stereo")

def desmutear():
    """Desactiva el silencio en caso de estar activado."""
    os.system("pactl set-sink-mute alsa_output.pci-0000_00_1b.0.hdmi-surround 0")

def configurar_audio():
    """Selecciona la salida HDMI, desactiva el silencio y establece el volumen."""
    limpiar_consola()
    porcentaje = 20
    cambiar_perfil()
    desmutear()
    establecer_volumen(porcentaje)
    print("Audio nocturno establecido.")
    print()
    input("Presione Enter para volver al menú principal")

def perfil_es_hdmi():
    """Devuelve True si el perfil de auido es HDMI Surround 5.1 + Entrada estéreo analógico, si no, devuelve False."""
    resultado_comando = os.popen("pacmd list-cards | grep 'active profile:' | cut -d ' ' -f 3").read()

    if "output:hdmi-surround+input:analog-stereo" in resultado_comando:
        return True
    return False

def no_muteado():
    """Devuelve uno si no está activado el silencio, si no, devuelve cero."""
    resultado_comando = os.popen("pacmd list-sinks | grep 'muted:' | cut -d ' ' -f 2").read()

    if "no" in resultado_comando:
        return 1
    return 0
        
def volumen_en_porcentaje(porcentaje):
    """Devuelve uno si el volumen está establecido en el porcentaje especificado, si no, devuelve cero."""
    valor = porcentaje_a_valor(porcentaje)
    resultado_comando = os.popen("pacmd list-sinks | grep 'volume:' | grep -E -o '[0-9]+' | head -n 1").read()
    

    if str(valor) in resultado_comando:
        return True
    return False

def imprimir_audio_nocturno():
    """Imprime un mensaje sobre el audio nocturno."""
    print("El audio nocturno está establecido.")
    print()
    
def esperar_apagado():
    """Apaga la pantalla auxiliar. Si existe un apagado programado, comprueba periódicamente el
    tiempo faltante para este, y en caso de ser menor o igual a 10 segundos, vuelve a encender la pantalla."""
    limpiar_consola()
    apagar_pantalla()
    print("Presione Enter para volver al menú principal")

    apagado = hay_apagado()

    if apagado:
        while True:
            if tiempo_limite(apagado):
                encender_pantalla()
                break
            ready, _, _ = select.select([sys.stdin], [], [], 10)
            if ready:
                input()
                break
    else:
        input("Presione Enter para volver al menú principal")

def armar_encabezado():
    """Establece el brillo de la pantalla al máximo, limpia la consola y muestra el título del programa"""
    encender_pantalla()
    limpiar_consola()
    print("Apagado automático del pc", end="\n\n")

def configurar_region():
    """Establece la configuración regional a 'español (España)' con el conjunto de caracteres UTF-8"""
    locale.setlocale(locale.LC_TIME, "es_ES.utf8")

def armar_opciones_apagado():
    """Devuelve una lista de opciones para un menú dependiendo de la existencia de un apagado programado."""
    apagado = hay_apagado()
    if apagado:
        imprimir_apagado(apagado)
        opciones_validas = [
            ("Programar un nuevo apagado", apagar_sistema),
            ("Cancelar el apagado programado", cancelar_apagado)
            ]
    else:
        opciones_validas = [("Programar apagado", apagar_sistema)]
    return opciones_validas

def armar_opciones_audio():
    """Devuelve una lista de opciones para un menú dependiendo de si está establecido el audio nocturno."""
    condiciones_de_volumen = perfil_es_hdmi() and no_muteado() and volumen_en_porcentaje(20)
    if condiciones_de_volumen:
        opciones_validas =[]
        imprimir_audio_nocturno()
    else:
        opciones_validas = [("Establecer audio nocturno", configurar_audio)]
    return opciones_validas

def armar_opciones_globales():
    """Devuelve una lista de opciones siempre necesarias en el menú principal."""
    opciones_validas =[("Salir", None)]
    return opciones_validas

def armar_opciones_validas():
    "Devuelve la lista de opciones definitivas a partir de las condiciones de apagado y audio."
    opciones_validas=[
        *armar_opciones_apagado(),
        *armar_opciones_audio(),
        *armar_opciones_playlist(),
        *armar_opciones_hdmi(),
        *armar_opciones_globales(),
        ]
    return opciones_validas

def extension_permitida(archivo):
    """Devuelve uno si la extensión del archivo está permitida, si no devuelve 0."""
    extensiones_permitidas = {".mkv", ".mp4"}
    return any(archivo.endswith(ext) for ext in extensiones_permitidas)

def listar_archivos_video(directorio):
    """Lista los archivos de video en la carpeta especificada ordenados alfabéticamente."""
    try:
        archivos_mkv = [archivo for archivo in os.listdir(directorio) if extension_permitida(archivo)]
        lista_ordenada = sorted(archivos_mkv)
        return lista_ordenada
    except FileNotFoundError:
        input("No hay archivos de video con las extensiones seleccionadas en el directorio actual."
              " Compruebe la configuración del programa.")

def limpiar_lista(lista):
    """Forma una lista con los nombres de los capítulos de una lista de archivos de video."""
    patron = re.compile(r'\d+x\d+ - (.+?)\.\w+')
    lista_limpia=[]
    for archivo in lista:
        coincidencia = patron.match(archivo)
        if coincidencia:
            nombre_capitulo = coincidencia.group(1)
            lista_limpia.append(nombre_capitulo)
    return lista_limpia

def hacer_lista_doble(carpeta):
    """Forma una lista de tuplas compuestas por el nombre recortado del capítulo y el nombre del archivo."""
    lista = listar_archivos_video(carpeta)
    lista_limpia = limpiar_lista(lista)
    lista_doble = list(zip(lista_limpia, lista))
    return lista_doble

def armar_opciones_globales_capitulo():
    """Devuelve una lista de opciones siempre necesarias en la elección de capítulo."""
    opciones_validas =[
    ("Finalizar", None)
    ]
    return opciones_validas

def obtener_eleccion_capitulo(opciones_validas):
    """Solicita una opción del menú y devuelve la elección si esta es un número."""
    print()
    entrada = input()
    if entrada.isdigit():
        eleccion = int(entrada) -1
        if 0 <= eleccion < len(opciones_validas):
            return eleccion
    input("Opción no válida. Por favor, elija una opción válida")
    return None

def ejecutar_opcion_capitulo(opciones_validas, eleccion):
    """Devuelve la segunda componente de una lista de tuplas si esta no es None."""
    capitulo = opciones_validas[eleccion][1]
    if capitulo is not None:
        return capitulo
    return False

def armar_opciones_capitulos(directorio):
    """Devuelve la lista de opciones de capítulos con las opciones globales."""
    lista_opciones_capitulos = hacer_lista_doble(directorio) + armar_opciones_globales_capitulo()
    return lista_opciones_capitulos    

def elegir_capitulos():
    """Arma un menú de opciones con los capítulos presentes en
    el directorio y devuelve la selección del usuario como lista.
    """
    lista_opciones_capitulos = armar_opciones_capitulos(directorio_actual)
    lista_para_guardar = []

    while True:
        limpiar_consola()
        print("Seleccione los capítulos que desea agregar a la lista de reproducción:")
        print()
        mostrar_menu(lista_opciones_capitulos)
        eleccion = obtener_eleccion_capitulo(lista_opciones_capitulos)
        if eleccion is not None:
            capitulo = ejecutar_opcion_capitulo(lista_opciones_capitulos, eleccion)
            lista_opciones_capitulos.pop(eleccion)
            if not capitulo:
                break
            lista_para_guardar.append(capitulo)

    return lista_para_guardar

def hacer_playlist():
    """Crea una lista de capítulos según la elección del usuario y lo escribe en un archivo .m3u"""
    lista = elegir_capitulos()
    with open(directorio_actual+"/playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(lista))
    limpiar_consola()
    print("Capítulos seleccionados exitosamente")
    print()
    input("Presione Enter para volver al menú principal")

def hay_playlist(directorio):
    lista=[]
    try:
        with open(directorio+"/playlist.m3u", "r", encoding="utf-8") as f:
            for linea in f:
                lista.append(linea.strip())
        return lista
    except FileNotFoundError:
        pass

def armar_opciones_playlist():
    playlist = hay_playlist(directorio_actual)
    if playlist:
        imprimir_playlist(limpiar_lista(playlist))
        opciones_validas = [
            ("Volver a seleccionar capítulos", hacer_playlist),
            ("Abrir reproductor", abrir_vlc)
            ]
    else:
        opciones_validas = [("Seleccionar capítulos",
                            hacer_playlist)]
    return opciones_validas

def imprimir_playlist(playlist):
    print("Capítulos seleccionados:")
    for capitulo in playlist:
        print(" -" + capitulo)
    print()

def hay_hdmi():
    return True

def armar_opciones_hdmi():
    if hay_hdmi():
        opciones_validas = [("Apagar pantalla auxiliar", esperar_apagado)]
    else:
        opciones_validas =[]
    return opciones_validas

def abrir_vlc():
    os.chdir(directorio_actual)
    os.system("nohup vlc --playlist-enqueue playlist.m3u > /dev/null 2>&1")

def menu_principal(opciones):
    while True:
        mostrar_menu(opciones)
        eleccion = obtener_eleccion(opciones)
        if eleccion is not None:
            return eleccion
        armar_encabezado()

def main():
    """Configura la región. Evalúa si existe un apagado programado y si el audio nocturno está configurado, arma un menú de 
    opciones en consecuencia y ejecuta según la entrada del usuario."""

    configurar_region()
    
    while True:
        armar_encabezado()
        opciones_validas = armar_opciones_validas()
        eleccion = menu_principal(opciones_validas)
        if not ejecutar_opcion(opciones_validas, eleccion):
            break

if __name__ == "__main__":
    main()
