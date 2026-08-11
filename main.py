#!/usr/bin/env python3

import random
import time
from natsort import natsorted
from ewmh import EWMH
import os
from screeninfo import get_monitors, Enumerator
import screen_brightness_control as sbc
from abc import ABC, abstractmethod
import json
from abc import ABC
import gi
from datetime import datetime
import threading
import buttons
import back
from controller import Controller
gi.require_version('Gtk', '3.0')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, Gdk, GLib


class Builder:
    def __init__(self, builder):
        self.builder = builder

    def get(self, name: str):
        """Get a widget from the window."""
        return self.builder.get_object(name)

class UserInterface(Builder):
    def __init__(self, controller):
        builder = Gtk.Builder()
        super().__init__(builder)

        self.controller = controller

        self.build_ui()

        self.json_file = self.load_config("perfiles.json")
        initial_mode = self.json_file["profiles"][self.json_file["current_profile"]]["current_mode"]

        self.window: Gtk.Window = self.get("window")

        self.main_box = self.get("main_box")

        self.stack = Stack(builder, controller, self.json_file, initial_mode)
        self.arrows = {"button_prev": self.get("prev"),
                       "button_next": self.get("next")
                       }
        self.button_bar = {"day": self.get("day"),
                           "night": self.get("night"),
                           "clock": self.get("clock"),
                           "shutdown": self.get("shutdown")
                           }

        self.window.connect("destroy", Gtk.main_quit)
        self.window.connect("key-press-event", self.on_window_key_press)
        self.window.connect("key-release-event", self.on_window_key_release)

        self.stack.object.connect("notify::visible-child-name", self.on_page_changed)
        self.connect_video_buttons()

        self.arrows["button_prev"].connect("clicked", self.on_button_prev_clicked)
        self.arrows["button_next"].connect("clicked", self.on_button_next_clicked)

        self.button_bar["day"].connect("clicked", self.on_day_night_toggled, 
                                              builder, controller, self.json_file)

        self._left_pressed = False
        self._right_pressed = False
        self._click_key_pressed = {Gdk.KEY_Return: False,
                                   Gdk.KEY_space: False,
                                   Gdk.KEY_KP_Enter: False
                                   }
        
        threading.Thread(target=self.set_clock, daemon=True).start()
        self.window.show_all()


    def load_config(self, json_file):
        with open(json_file, "r", encoding="utf-8") as a:
            return json.load(a)

    def disable_entry(self):
        self.main_box.set_sensitive(False)

    def restart_stack(self):
        self.change_mode(self.builder, self.controller, self.json_file)
        self.main_box.set_sensitive(True)

    def connect_video_buttons(self):
        for button in (video_buttons := self.stack.page_dict[3].widget):
            button.connect("toggled", self.any_button_toggled, video_buttons)

    def any_button_toggled(self, _, video_buttons):
        if any(button.get_active() for button in video_buttons):
            self.arrows["button_next"].set_sensitive(True)
        else:
            self.arrows["button_next"].set_sensitive(False)

    def on_window_key_press(self, _, event):
        if (event.keyval == Gdk.KEY_Right
                and not self._right_pressed
                and not any(self._click_key_pressed.values())):
            self.stack.next_page()
            self._right_pressed = True
            return True # Avoid side effects
        if (event.keyval == Gdk.KEY_Left
                and not self._right_pressed
                and not any(self._click_key_pressed.values())):
            if self.stack.current_index - 1 in self.stack.page_dict:
                self.stack.prev_page()
            else:
                self.change_mode_button()
            self._left_pressed = True
            return True # Avoid side effects
        if event.keyval in self._click_key_pressed:
            if self._click_key_pressed[event.keyval]:
                return True
            self._click_key_pressed[event.keyval] = True
        return False

    def on_window_key_release(self, _, event):
        if event.keyval == Gdk.KEY_Right:
            self._right_pressed = False
        elif event.keyval == Gdk.KEY_Left:
            self._left_pressed = False
        elif event.keyval in self._click_key_pressed:
            self._click_key_pressed[event.keyval] = False

    def on_page_changed(self, _, _event):
        if not self.stack.current_index - 1 in self.stack.page_dict:
            self.arrows["button_prev"].set_sensitive(False)
        else:
            self.arrows["button_prev"].set_sensitive(True)

    def on_button_next_clicked(self, _):
        self.stack.next_page()

    def on_button_prev_clicked(self, _):
        self.stack.prev_page()

    def on_day_night_toggled(self, _, builder, controller, json_file):
        self.change_mode(builder, controller, json_file)

    def change_mode_button(self,):
        if (button_day := self.button_bar["day"]).get_active():
            self.button_bar["night"].set_active(True)
        else:
            button_day.set_active(True)

    def change_mode(self, builder, controller, json_file):
        self.stack.destroy_all_pages()
        if self.button_bar["day"].get_active():
            self.stack = Stack(builder, controller, json_file, "day")
        else:
            self.stack = Stack(builder, controller, json_file, "night")
        self.connect_video_buttons()

    def set_clock(self):
        while True:
            while (shutdown_date := back.get_shutdown_date()) is not None:
                self.button_bar["clock"].set_sensitive(True)
                left_time = int(back.get_left_time(shutdown_date))
                m, s = divmod(left_time, 60)
                self.button_bar["shutdown"].set_label(f"Apagado programado en {m:02d}:{s:02d}")
                time.sleep(1)
                left_time -= 1
            self.button_bar["clock"].set_sensitive(False)
            time.sleep(1)

    def build_ui(self):
        """Build the window from stylesheet and gladefile."""
        css_provider = Gtk.CssProvider()

        with open("style.css", "r", encoding="UTF-8") as file:
            css_provider.load_from_data(bytes(file.read(), encoding="UTF-8"))

        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        gladefile = "interface.glade"
        self.builder.add_from_file(gladefile)
        

class Stack(Builder):
    def __init__(self, builder, controller, json_file, mode):
        super().__init__(builder)

        self.json_file = json_file
        self.config = json_file["profiles"][json_file["current_profile"]]

        self.controller = controller
        self.mode = mode
        self.object = self.get("stack")

        self.page_dict = {}
        self.answer_dict = {}
        self.current_index = None

        self.set_initial_page()

    @classmethod
    def new(cls, builder, config, mode):
        return cls(builder, config, mode)

    def dump_config(self):
        with open("perfiles2.json", 'w', encoding="utf-8") as a:
            json.dump(self.json_file, a, indent=4)

    def apply_audio(self, audio_option, screen):
        if audio_option == "Pantalla":
            volume = self.config["audio"][screen][self.mode]
            audio_profile = self.config[screen]["profile"]
            back.set_system_audio(volume, audio_profile)
        else:
            volume = self.config["audio"][audio_option]
            back.set_system_audio(volume)

    def set_last_videos(self, videos):
        self.config["last_videos"] = videos
        self.dump_config()

    def apply_answers(self):
        answers = self.answer_dict

        screen_option = answers[1]
        audio_option = answers[2]
        videos = answers[3]
        turnoff = answers[4]

        playlist_file = f"{self.config['directory']}/{self.config['playlist_name']}.m3u"

        if self.mode == "night" and (shutdown_option := answers[0]) != "No":
            back.set_shutdown(int(shutdown_option.split()[0]))

        if audio_option != "No":
            self.apply_audio(audio_option, screen_option)

        back.write_playlist(playlist_file, self.page_dict[3].get_full_names(videos))
        self.set_last_videos(videos)

        self.finish(playlist_file, screen_option, turnoff)

    def finish(self, playlist_file, screen, turnoff):
        bug_fixers = self.config["bug_fixers"]
        compressor = self.config["compressor"]
        compressor["on"] = compressor[self.mode]

        ewmh = EWMH()
        shutdown_date = back.get_shutdown_date()

        if back.is_ewmh_window(ewmh, "VLC"):
            raise RuntimeError

        try:
            back.open_vlc(playlist_file, self.config[screen]["index"], self.config["compressor"])

            back.set_window(ewmh, "VLC", bug_fixers["timeout_factor"],
                            self.config[screen]["coordinates"]) # timeout
            if turnoff:
                initial_brightness = sbc.get_brightness(0, method="sysfiles").pop()
                sbc.set_brightness(value=0, display=0, method="sysfiles", force=True)

            player = back.get_playerctl_window("vlc", bug_fixers["timeout_factor"]) # timeout
            back.play_vlc(player, bug_fixers["delay_factor"])
            back.set_vlc_audio(bug_fixers["timeout_factor"]) # timeout

        except (TimeoutError, sbc.ScreenBrightnessError) as e:
            input(e)
            return

        loop = GLib.MainLoop()

        if turnoff:
            player.connect("exit", self.on_exit, loop, initial_brightness)
            if shutdown_date is not None:
                self.set_turnon_thread(shutdown_date, initial_brightness, bug_fixers)
        else:
            player.connect("exit", self.on_exit, loop)
        loop.run()

    def on_exit(self, _, loop, initial_brightness=None):
        if initial_brightness is not None:
            sbc.set_brightness(value=initial_brightness, display=0, method="sysfiles", force=True)
        self.controller.restart_stack()
        loop.quit()

    def set_turnon_thread(self, shutdown_date, initial_brightness, bug_fixers):
        left_time = back.get_left_time(shutdown_date)
        kwargs = {"value": initial_brightness,
                    "display": 0,
                    "method": "sysfiles",
                    "force": True
                    }
        threading.Timer(left_time - bug_fixers["wakeup_time"],
                        sbc.set_brightness, kwargs=kwargs).start()

    def destroy_all_pages(self):
        for page in self.page_dict.values():
            page.destroy()

    def set_initial_page(self):
        self.page_dict.update({1: self.new_page_from_index(1), 2: self.new_page_from_index(2),
                           3: self.new_page_from_index(3)})
        null_transition = Gtk.StackTransitionType(0)
        if self.mode == "night":
            self.page_dict.update({0: self.new_page_from_index(0)})
            self.current_index = 0
            self.object.set_visible_child_full("page0", null_transition)
            self.page_dict[0].grab_focus()
        else:
            self.current_index = 1
            self.object.set_visible_child_full("page1", null_transition)
            self.page_dict[1].grab_focus()

    def new_page_from_index(self, index):
        page_dict = {0: ShutdownPage,
                     1: ScreenPage,
                     2: AudioPage,
                     3: VideoPage
                     }
        if index == 4:
            return OpenPage(self.config, self.mode, self.get("options4"), self.get("scroll4"),
                            self.answer_dict[1])
        return page_dict[index](self.config, self.mode, self.get(f"options{index}"),
                                self.get(f"scroll{index}"))

    def next_page(self):
        self.answer_dict[self.current_index] = self.page_dict[self.current_index].get_answer()
        if self.current_index == 4:
            self.controller.pause_gui()
            threading.Thread(target=self.apply_answers).start()
        elif (self.current_index == 3
              and any(button.get_active() for button in self.page_dict[3].widget)):
            self.page_dict[4] = self.new_page_from_index(4)
            self.current_index += 1
            self.object.set_visible_child_name(f"page{self.current_index}")
            self.page_dict[self.current_index].grab_focus()
        elif self.current_index != 3:
            self.current_index += 1
            self.object.set_visible_child_name(f"page{self.current_index}")
            self.page_dict[self.current_index].grab_focus()

    def prev_page(self): #OK
        self.current_index -= 1
        self.object.set_visible_child_name(f"page{self.current_index}")
        if self.current_index == 3:
            self.page_dict[self.current_index + 1].destroy()

class Page(ABC):
    def __init__(self, config, mode, widget):
        self.config = config
        self.mode = mode
        self.widget = widget
        self.button_type = None
        self.option_list = []
        self.button_dict = {}

    def create_page(self, widget, scroll):
        self.option_list = self._make_options()
        self.default_list = self._make_default()

        self.button_dict = buttons.create_buttons(self.option_list, widget, self.button_type)
        if self.button_type == "check":
            self.connect_buttons()
        buttons.set_default_buttons(self.default_list, self.button_dict, widget)

        self.set_scroll(scroll, widget)
        self.widget.show_all()

    @abstractmethod
    def _make_options(self):
        pass

    @abstractmethod
    def _make_default(self):
        pass

    @abstractmethod
    def get_answer(self):
        pass

    def set_scroll(self, scroll, box):
        adjustment = scroll.get_vadjustment()
        box.set_focus_vadjustment(adjustment)

    def set_focus(self):
        for o in self.widget:
            if o.get_active():
                self.widget.set_focus_child(o)
                break

    def grab_focus(self):
        self.button_dict[self.default_list[0]].grab_focus()

    def destroy(self):
        for button in self.widget:
            button.destroy()

class ShutdownPage(Page):
    def __init__(self, config, mode, widget, scroll):
        super().__init__(config, mode, widget)
        self.button_type = "radio"
        self.create_page(widget, scroll)

    def _make_options(self):
        return self.config["options"]["0"]

    def _make_default(self):
        return [self.config["defaults"][self.mode]["0"]]

    def get_answer(self):
        for option in self.widget:
            if option.get_active():
                shutdown_option = option.get_label()
                break
        return shutdown_option

class ScreenPage(Page):
    def __init__(self, config, mode, widget, scroll):
        super().__init__(config, mode, widget)
        self.button_type = "radio"
        self.create_page(widget, scroll)

    def _make_options(self):
        config_options = self.config["options"]["1"]
        screen_options = config_options
        if self._is_hdmi():
            screen_options = config_options + ["HDMI"]
        return screen_options

    def _make_default(self):
        screen_default = self.config["defaults"][self.mode]["1"]
        if not screen_default in self.option_list:
            screen_default = "PC"
        return [screen_default]

    def _is_hdmi(self):
        return "HDMI-1" in [monitor.name for monitor in get_monitors(Enumerator.Xrandr)]

    def get_answer(self):
        for option in self.widget:
            if option.get_active():
                screen = option.get_label()
                break
        return screen

class AudioPage(Page):
    def __init__(self, config, mode, widget, scroll):
        super().__init__(config, mode, widget)
        self.button_type = "radio"
        self.create_page(widget, scroll)

    def _make_options(self):
        return self.config["options"]["2"]

    def _make_default(self):
        return [self.config["defaults"][self.mode]["2"]]

    def get_answer(self):
        for option in self.widget:
            if option.get_active():
                audio_option = option.get_label()
                break
        return audio_option

class VideoPage(Page):
    def __init__(self, config, mode, widget, scroll):
        super().__init__(config, mode, widget)
        self.button_type = "check"
        self.video_dict = self._make_video_dict()
        self.selected_buttons = []
        self.create_page(widget, scroll)

    def _make_options(self):
        return list(self.video_dict.keys())

    def _make_default(self):
        screen_default = self.config["defaults"][self.mode]["3"]
        if screen_default == "last":
            last_videos = [video for video in self.config["last_videos"] if video in self.video_dict]
            if last_videos:
                return last_videos
        return [self.option_list[0]]

    def _make_video_dict(self):
        video_list = self._make_video_list()
        return {file.rsplit(".", 1)[0]: file for file in video_list}

    def _make_video_list(self):
        videos = [file for file in os.listdir(self.config["directory"]) if
                  self._allowed_extension(file)]
        if not videos:
            raise ValueError
        return natsorted(videos, reverse=False)

    def _allowed_extension(self, file):
        return any(file.endswith(ext) for ext in set(self.config["extensions"]))

    def get_answer(self):
        return self.selected_buttons

    def get_full_names(self, video_list):
        final_list = []
        for video in video_list:
            final_list.append(self.video_dict[video])
        return final_list

    def connect_buttons(self):
        for button in self.widget:
            button.connect("toggled", self.on_button_toggled)

    def on_button_toggled(self, button):
        if button.get_active():
            self.selected_buttons.append(button.get_label())
        else:
            self.selected_buttons.remove(button.get_label())

class OpenPage(Page):
    def __init__(self, config, mode, widget, scroll, screen):
        super().__init__(config, mode, widget)
        self.screen = screen
        self.button_type = "radio"
        self.create_page(widget, scroll)

    def _make_options(self):
        config_options = self.config["options"]["4"]
        open_options = config_options
        if self.screen == "HDMI":
            open_options = config_options + ["Abrir reproductor y apagar pantalla auxiliar"]
        return open_options

    def _make_default(self):
        open_default = self.config["defaults"][self.mode]["4"]
        if not open_default in self.option_list:
            open_default = "Abrir reproductor"
        return [open_default]

    def get_answer(self):
        for option in self.widget:
            if option.get_active():
                turnoff = option.get_label() == "Abrir reproductor y apagar pantalla auxiliar"
                break
        return turnoff

class ClockThread(threading.Thread):
    def __init__(self, shutdown_button, shutdown_label):
        super().__init__()
        self.shutdown_button = shutdown_button
        self.shutdown_label = shutdown_label

    def run(self):
        while True:
            while (shutdown_date := back.get_shutdown_date()) is not None:
                self.shutdown_button.set_sensitive(True)
                left_time = int(back.get_left_time(shutdown_date))
                m, s = divmod(left_time, 60)
                self.shutdown_label.set_label(f"Apagado programado en {m:02d}:{s:02d}")
                time.sleep(1)
                left_time -= 1
            self.shutdown_button.set_sensitive(False)


if __name__ == "__main__":
    controller = Controller()
    ui = UserInterface(controller)
    controller.set_gui(ui)
    Gtk.main()
