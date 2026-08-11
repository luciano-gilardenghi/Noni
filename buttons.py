#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, Gdk

def create_buttons(option_list, widget, button_type):
    if button_type == "check":
        return create_check_buttons(option_list, widget)
    return create_radio_buttons(option_list, widget)

def create_radio_buttons(option_list, widget):
    button_dict = {}
    first_label = option_list[0]
    first_button = create_radio_button(first_label)
    widget.add(first_button) # Going to be active unless default == (options[i != 0])
    button_dict[first_label] = first_button

    for label in option_list[1:]:
        next_button = create_radio_button(label, first_button)
        widget.add(next_button)
        button_dict[label] = next_button

    return button_dict

def create_radio_button(label, widget=None):
    if widget:
        radio_button = Gtk.RadioButton.new_with_label_from_widget(widget, label)
    else:
        radio_button = Gtk.RadioButton.new_with_label(None, label)
    radio_button.set_mode(draw_indicator=False)
    return radio_button

def create_check_buttons(option_list, widget):
    button_dict = {}

    first_label = option_list[0]
    first_button = create_check_button(first_label)
    widget.add(first_button) # Going to be active unless default == (options[i != 0])
    button_dict[first_label] = first_button

    for label in option_list[1:]:
        next_button = create_check_button(label)
        widget.add(next_button)
        button_dict[label] = next_button

    return button_dict

def create_check_button(label):
    check_button = Gtk.CheckButton.new_with_label(label)
    check_button.set_mode(draw_indicator=False)
    return check_button

def set_default_buttons(default_list, button_dict, widget):
    for default in default_list:
        button_dict[default].set_active(True)
        widget.set_focus_child(button_dict[default])
