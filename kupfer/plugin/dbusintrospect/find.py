"""
This file originates in linglish [1], [2], a program by Stuart Langridge.

Copyright 2009 Stuart Langridge

[1]: http://svn.kryogenix.org/svn/linglish/
[2]: http://www.kryogenix.org/days/2009/02/08/linglish-or-some-thoughts-on-a-scripting-language-for-the-linux-desktop

Stuart has agreed to license the code under the X11 License.

(which permits us to use it in a GPL distribution.)
"""

import dbus
import os
import traceback
from xml.dom import minidom

import gobject

class LinglishException(Exception):
    def __init__(self, *args):
        self.args = [x or 'unspecified' for x in args]

    def __str__(self):
        return self.errorstr % self.args

class BadBus(LinglishException):
    errorstr = "No such bus %s"
    
class BadApplication(LinglishException):
    errorstr = "Couldn't find application %s"

class InspecificApplication(LinglishException):
    errorstr = "Application %s was not specific enough: matches were %s"


def get_matching_application(act_bus, requested):
	"""
	This method was written by Stuart Langridge for Linglish
	"""
	# get all bus names on this bus
	dbus_proxy = act_bus.get_object('org.freedesktop.DBus','/')
	busnames = [str(x) for x in list(dbus_proxy.ListNames())] + \
			   [str(x) for x in list(dbus_proxy.ListActivatableNames())]
	busnames = dict([(x,"") for x in busnames]).keys() # uniquify

	# work out whether our application matches one of the names
	possible_apps = []
	for busname in busnames:
		if busname.find(requested) != -1:
			# case-sensitive check first
			possible_apps.append(busname)
		elif busname.lower().find(requested.lower()) != -1:
			# failing that case-insensitive
			possible_apps.append(busname)
	if len(possible_apps) == 0:
		raise BadApplication(requested)
	elif len(possible_apps) > 1:
		raise InspecificApplication(requested, ", ".join(possible_apps))
	act_application = possible_apps[0]
	return act_application

def get_objects(bus, app, cum_path=""):
	"""
	This method was written by Stuart Langridge for Linglish
	"""
	found_objects = {}
	if cum_path == "":
		proxy = bus.get_object(app, "/")
	else:
		proxy = bus.get_object(app, cum_path)
	xml = proxy.Introspect(dbus_interface='org.freedesktop.DBus.Introspectable')
	dom = minidom.parseString(xml)
	elements = [x for x in dom.documentElement.childNodes
				if x.nodeType == 1]
	subdict = {}
	for element in elements:
		if element.nodeName == "node":
			subpath = cum_path + "/" + element.getAttribute("name")
			found_objects.update(get_objects(bus, app, subpath))
		elif element.nodeName == "interface":
			methods = []
			signals = []
			properties = []
			for subel in element.childNodes:
				if subel.nodeName == "method":
					mname = subel.getAttribute("name")
					margs = []
					for argel in subel.childNodes:
						if argel.nodeName == "arg":
							margs.append((
								argel.getAttribute("name"),
								argel.getAttribute("direction"),
								argel.getAttribute("type"),
							))
					methods.append((mname, margs))
				if subel.nodeName == "signal":
					signals.append(subel.getAttribute("name"))
				if subel.nodeName == "property":
					properties.append(subel.getAttribute("name"))
			subdict[element.getAttribute("name")] = {}
			subdict[element.getAttribute("name")]["methods"] = methods
			subdict[element.getAttribute("name")]["signals"] = signals
			subdict[element.getAttribute("name")]["properties"] = properties
		else:
			pass
	if subdict:
		if cum_path == "":
			found_objects["/"] = {"path": "/", "interfaces": subdict}
		else:
			found_objects[cum_path] = {"path": cum_path, "interfaces": subdict}
	return found_objects
	

if __name__ == '__main__':
	session_bus = dbus.Bus()
	app_name = "Notifications"
	app = get_matching_application(session_bus, app_name)

	import pprint
	objs = get_objects(session_bus, app)
	pprint.pprint(objs)
