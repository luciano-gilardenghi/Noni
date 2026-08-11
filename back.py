#!/usr/bin/env python3

import subprocess
import shlex
import pulsectl
import json
import time
import os
import screen_brightness_control as sbc
from ewmh import EWMH
from natsort import natsorted
from screeninfo import get_monitors, Enumerator
from datetime import datetime
import gi
gi.require_version('Playerctl', '2.0')
from gi.repository import Playerctl, GLib

def set_shutdown(shutdown_time):
    command = f"shutdown -h +{shutdown_time}"
    subprocess.run(shlex.split(command), shell=False, check=False, capture_output=True)

def write_playlist(playlist_file, videos):
    with open(playlist_file, "w", encoding="utf-8") as f:
        f.write("\n".join(videos))

def set_system_audio(volume, screen_profile=None):
    with pulsectl.Pulse("system") as pulse:
        if screen_profile:
            current_sink = pulse.get_sink_by_name(pulse.server_info().default_sink_name)
            card = pulse.card_info(current_sink.card)
            pulse.card_profile_set(card, screen_profile)
        new_sink = pulse.get_sink_by_name(pulse.server_info().default_sink_name)
        set_audio(pulse, new_sink, volume)


def open_vlc(playlist_file, screen_index, compressor):
    command = [
        "vlc",
        "--dbus",
        playlist_file,
        "--qt-fullscreen-screennumber", str(screen_index),
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

    if compressor["on"]:
        command += [
            "--compressor-rms-peak", str(compressor["rms_peak"]),
            "--compressor-attack", str(compressor["attack"]),
            "--compressor-release", str(compressor["release"]),
            "--compressor-threshold", str(compressor["threshold"]),
            "--compressor-ratio", str(compressor["ratio"]),
            "--compressor-knee", str(compressor["knee"]),
            "--compressor-makeup-gain", str(compressor["makeup_gain"])
            ]

    subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def set_window(ewmh, name, timeout_factor, coordinates):
    window = get_ewmh_window(ewmh, name, timeout_factor) # error: no se pudo abrir vlc
    move_window(ewmh, window, coordinates)
    ewmh.display.flush()

def move_window(ewmh, window, coordinates):
    ewmh.setWmState(window, 0, '_NET_WM_STATE_FULLSCREEN')
    ewmh.setWmState(window, 0, '_NET_WM_STATE_MAXIMIZED_VERT', '_NET_WM_STATE_MAXIMIZED_HORZ')
    x, y = coordinates
    ewmh.setMoveResizeWindow(window, x=x, y=y, w=300, h=100)

def is_ewmh_window(ewmh, name):
    attempt = 0
    while attempt < 5:
        for window in ewmh.getClientList():
            window_name = ewmh.getWmName(window)
            if window_name and name in window_name.decode():
                return window
        attempt += 1
        time.sleep(0.1)

def get_ewmh_window(ewmh, name, timeout_factor, attempts=300):
    attempt = 0
    while attempt < attempts * timeout_factor:
        for window in ewmh.getClientList():
            window_name = ewmh.getWmName(window)
            if window_name and name in window_name.decode():
                return window
        attempt += 1
        time.sleep(0.1)
    raise TimeoutError

def get_playerctl_window(name, timeout_factor, attempts=300):
    attempt = 0
    while attempt < attempts * timeout_factor:
        for player_name in Playerctl.list_players():
            if player_name.name == name:
                window = Playerctl.Player.new_from_name(player_name)
                return window
        attempt += 1
        time.sleep(0.1)
    raise TimeoutError

def play_vlc(player, delay_factor):
    for __ in range(2):
        time.sleep(0.5 * delay_factor)
        player.play()

def set_vlc_audio(timeout_factor):
    with pulsectl.Pulse("vlc") as pulse:
        window = get_pulse_window(pulse, "VLC", timeout_factor)
        set_audio(pulse, window, volume=100)

def get_pulse_window(pulse, name, timeout_factor, attempts=300):
    attempt = 0
    while attempt < attempts * timeout_factor:
        for window in pulse.sink_input_list():
            if name in window.proplist.get('application.name'):
                return window
        attempt += 1
        time.sleep(0.1)
    raise TimeoutError

def set_audio(pulse, obj, volume):
    pulse.mute(obj, mute=False)
    pulse.volume_set_all_chans(obj, volume / 100)

def get_shutdown_date():
    try:
        with open("/run/systemd/shutdown/scheduled", "r", encoding="utf-8") as shutdown_file:
            usec_date = shutdown_file.readline().split("USEC=")[1].strip()
    except FileNotFoundError:
        return None
    return datetime.fromtimestamp(float(usec_date) / 1e6)

def get_left_time(shutdown_date):
    return (shutdown_date - datetime.now()).total_seconds()

