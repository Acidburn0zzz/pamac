#! /usr/bin/python3
# -*- coding:utf-8 -*-

# pamac - A Python implementation of alpm
# Copyright (C) 2013-2014  Guillaume Benoit <guillaume@manjaro.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from gi.repository import Gtk, GObject, Notify
from subprocess import call
import dbus
from dbus.mainloop.glib import DBusGMainLoop
from threading import Thread
from time import sleep

from pamac import common, config

# i18n
import gettext
gettext.bindtextdomain('pamac', '/usr/share/locale')
gettext.textdomain('pamac')
_ = gettext.gettext

update_icon = 'pamac-tray-update'
update_info = _('{number} available updates')
one_update_info = _('1 available update')
noupdate_icon = 'pamac-tray-no-update'
noupdate_info = _('Your system is up-to-date')
icon = noupdate_icon
info = noupdate_info

class Tray:
	def __init__(self):
		self.statusIcon = Gtk.StatusIcon()
		self.statusIcon.set_visible(True)

		self.menu = Gtk.Menu()
		self.menuItem = Gtk.ImageMenuItem(_('Update Manager'))
		self.menuItem.set_image(Gtk.Image.new_from_icon_name('system-software-update', Gtk.IconSize.MENU))
		self.menuItem.connect('activate', self.execute_update, self.statusIcon)
		self.menu.append(self.menuItem)
		self.menuItem = Gtk.ImageMenuItem(_('Package Manager'))
		self.menuItem.set_image(Gtk.Image.new_from_icon_name('system-software-install', Gtk.IconSize.MENU))
		self.menuItem.connect('activate', self.execute_manager, self.statusIcon)
		self.menu.append(self.menuItem)
		self.menuItem = Gtk.ImageMenuItem(_('Quit'))
		self.menuItem.set_image(Gtk.Image.new_from_icon_name('application-exit', Gtk.IconSize.MENU))
		self.menuItem.connect('activate', self.quit_tray, self.statusIcon)
		self.menu.append(self.menuItem)

		self.statusIcon.connect('popup-menu', self.popup_menu_cb, self.menu)
		self.statusIcon.connect('activate', self.activate_cb)

		self.update_icon(icon, info)

	def execute_update(self, widget, event, data = None):
		Thread(target = call, args = (['/usr/bin/pamac-updater'],)).start()

	def execute_manager(self, widget, event, data = None):
		Thread(target = call, args = (['/usr/bin/pamac-manager'],)).start()

	def quit_tray(self, widget, data = None):
		Gtk.main_quit()

	def popup_menu_cb(self, widget, button, time, data = None):
		if button == 3:
			if data:
				data.show_all()
				data.popup(None, None, Gtk.StatusIcon.position_menu, self.statusIcon, 3, time)

	def activate_cb(self, widget, data = None):
		if icon == update_icon:
			Thread(target = call, args = (['/usr/bin/pamac-updater'],)).start()

	def update_icon(self, icon, info):
		self.statusIcon.set_from_icon_name(icon)
		self.statusIcon.set_tooltip_markup(info)

	def set_visible(self, boolean):
		self.statusIcon.set_visible(boolean)

def refresh():
	Thread(target = call, args = (['/usr/bin/pamac-refresh'],)).start()
	return True

def check_updates():
	Thread(target = call, args = (['/usr/bin/pamac-check_updates'],)).start()

locked = False
def check_pacman_running():
	global locked
	if locked:
		if not common.lock_file_exists():
			locked = False
			check_updates()
	else:
		if common.lock_file_exists():
			if not common.pid_file_exists():
				locked = True
	sleep(0.5)
	return True

def set_icon(update_data):
	global icon
	global info
	syncfirst, updates = update_data
	if updates:
		icon = update_icon
		if len(updates) == 1:
			info = one_update_info
		else:
			info = update_info.format(number = len(updates))
		if not common.pid_file_exists():
			Notify.Notification.new(_('Update Manager'), info, 'system-software-update').show()
	else:
		icon = noupdate_icon
		info = noupdate_info
	print(info)
	tray.update_icon(icon, info)

def launch_refresh_timeout():
	# GObject timeout is in milliseconds
	global refresh_timeout_id
	refresh_timeout_id = GObject.timeout_add(config.refresh_period*3600*1000, refresh)

def relaunch_refresh_timeout(msg):
	config.pamac_conf.reload()
	GObject.source_remove(refresh_timeout_id)
	launch_refresh_timeout()

DBusGMainLoop(set_as_default = True)
bus = dbus.SystemBus()
bus.add_signal_receiver(set_icon, dbus_interface = "org.manjaro.pamac", signal_name = "EmitAvailableUpdates")
bus.add_signal_receiver(relaunch_refresh_timeout, dbus_interface = "org.manjaro.pamac", signal_name = "EmitReloadConfig")
tray = Tray()
Notify.init(_('Update Manager'))
refresh()
launch_refresh_timeout()
GObject.idle_add(check_pacman_running)
Gtk.main()
