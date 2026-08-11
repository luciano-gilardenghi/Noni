#!/usr/bin/env python3

import shlex
import subprocess

def limpiar_consola():
    """Limpia la consola utilizando 'clear'."""
    subprocess.run("clear", check=False)
    
def grep_y_cut(comando: str, grep: str, cut: str = None):
    """Ejecuta un comando para buscar patrones y extraer las partes seleccionadas."""
    if not all(isinstance(arg, str) for arg in [comando, grep]):
        raise TypeError("Todas las entradas deben ser cadenas.")
    p1 = subprocess.Popen(shlex.split(comando), stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True)
    p1_stdout, p1_stderr = p1.communicate()
    if p1_stderr:
        raise subprocess.SubprocessError(p1_stderr)
    p2 = subprocess.Popen(["grep", *shlex.split(grep)], stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    p2_stdout, p2_stderr = p2.communicate(input=p1_stdout)
    if p2_stderr:
        raise subprocess.SubprocessError(p2_stderr)
    if cut is not None:
        if not isinstance(cut, str):
            raise TypeError("Todas las entradas deben ser cadenas.")
        p3 = subprocess.Popen(["cut", *shlex.split(cut)], stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        p3_stdout, p3_stderr = p3.communicate(input=p2_stdout)
        if p3_stderr:
            raise subprocess.SubprocessError(p3_stderr)
        return p3_stdout.strip()
    return p2_stdout.strip()

def llamar_terminal(comando):
    """Llama a subprocess.run con el comando elegido,
    shell=False, check=False y capture_output=True.
    """
    subprocess.run(shlex.split(comando), shell=False, check=False, capture_output=True)

def imprimir_con_salto(cadena):
    r"""Llama la funcion print con end='\n\n'."""
    print(cadena, end="\n\n")

def repetir(intentos, intervalo):
    def decorador(funcion):
        def decorada(*args, **kwargs):
            intento = 0
            while intento < intentos:
                funcion(*args, **kwargs)
                intento += 1
                time.sleep(intervalo)
            raise TimeoutError()
        return decorada
    return decorador

def ignorar_primer_llamada(funcion):
    primer_llamada = True
    def interna(*args, **kwargs):
        nonlocal primer_llamada
        if primer_llamada:
            primer_llamada = False
        else:
            funcion(*args, **kwargs)
    return interna
