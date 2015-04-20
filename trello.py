#! /usr/bin/python
# -*- coding: utf-8 -*-

import ConfigParser,sys,requests, json,urllib2,smtplib,time,codecs
from akamai.edgegrid import EdgeGridAuth
from os	import path
from urlparse import urljoin
from pprint import pprint


home = path.expanduser("~")
config_file = "%s/.trellorc" % home
default_block = "trello"

class BlankDict(dict):
        def __missing__(self, key):
			return ''

class Trello:
	def __init__(self,block=default_block,filename=config_file):
		self.dashboards = []
		if not path.isfile(filename):
			self.create_configuration(block)

		try:
			config = ConfigParser.ConfigParser()
			config.readfp(open(config_file))
			config.items(block)
			for key, value in config.items(block):
				# ConfigParser lowercases magically
				if key == "client_secret":
					self.client_secret = value
				elif key == "client_token":
					self.client_token = value
				elif key == "mail_port":
					self.mail_port = value
				elif key == "mail_server":
					self.mail_server = value
				elif key == "mail_user":
					self.mail_user = value
				elif key == "mail_password":
					self.mail_password = value
				else:
					print "I have no mapping for %s" % key	
		except(ConfigParser.NoSectionError):
			print "This block dont exists"
			self.create_configuration(block)


	def create_configuration(self,block,filename=config_file):
		url="https://trello.com/1/authorize?key="+self.client_key+"&name=My+Application&expiration=never&response_type=token"
		Config = ConfigParser.ConfigParser()
		config_items = ["client_token","client_secret","mail_server","mail_port","mail_user","mail_password"]
		print "You will need client_token, client_secret,mail_server, mail_port, mail_user and mail_password"
		print "You can generate your token in this URL: ",url
		# First, if we have a 'default' section protect it here
		if not path.exists(filename):
			myfile = open (filename, "w")
			myfile.write("\n")
			myfile.close()
		with open (filename, "r") as myfile:
 			data=myfile.read().replace('default','----DEFAULT----')
			myfile.close()
		with open (filename, "w") as myfile:
			myfile.write(data)
			myfile.close()

		Config.read(filename)
		config = open(filename,'w')

		if block in Config.sections():
			print "\n\nReplacing section: %s" % block
			Config.remove_section(block)
		else:
			print "\n\nCreating section: %s" % block

		Config.add_section(block)

		for i in config_items:
			var = ""
			while not var:
				message = "Insert your %s please:" % i
				var = raw_input(message).strip()
				if " " in var:
					print "Error"
					var = ""
				else:
					if i == "client_secret":
						Config.set(block,'client_secret',var)
					elif i == "client_token":
						Config.set(block,'client_token',var)
		Config.write(config)
		config.close ()
		config.close ()
		with open (filename, "r") as myfile:
 			data=myfile.read().replace('----DEFAULT----','default')
			myfile.close()
		with open (filename, "w") as myfile:
			myfile.write(data)
			myfile.close()

	def get_info(self,url):
		response = urllib2.urlopen(url)
		result = response.read()
		dump = json.loads(result)
		return dump

	def export_infocsv(self,result=[],args=[]):
		data = ""
		try:	
			if str(result["httpStatus"]) == "403" or str(result["status"]) == "403":
				print "Permisions Error"
				raise SystemExit
			if str(result["status"]) == "401":
				print "Permisions Error"
				raise SystemExit
	 	except (TypeError):
			pass
		while result:
			record =""
			line = result.pop()
			for i in args:
				s = line[i].encode("utf-8")
				record += s +";"
			data += "\n" + record
		return data

	def export_info(self,result=[]):
		data = ""
		actual_board = ""
		actual_card = ""
		actual_task = ""
		tasks = 0 
		try:	
			if str(result["httpStatus"]) == "403" or str(result["status"]) == "403":
				print "Permisions Error"
				raise SystemExit
			if str(result["status"]) == "401":
				print "Permisions Error"
				raise SystemExit
		except (TypeError):
			pass
		while result:
			line = result.pop()
			try:
				if actual_board != line["board"]:
					data += "\n" + line["board"].center(40,"*") + "\n"
					actual_board = line["board"]
					actual_card = ""
				if line["card"] != "Done":
					if actual_card != line["card"]:
						data += "  " + line["card"].center(40,"=") + "\n"
						actual_card = line["card"]
					if actual_task != line["name"]:

						seq = ("                ", line["name"],"\n")
						data += u" ".join(seq).encode("utf-8")
						actual_task = line["name"]
						tasks += 1
			except (UnicodeDecodeError):
				data += "            !!!Task not encoded properly\n"
				tasks += 1
		data += "\nTOTAL de Tareas = %i \n" % tasks
		return data

	def export_boards(self,filtering=[]):
		boards = []
		url = "https://api.trello.com/1/members/me/boards?key="+self.client_secret+"&token="+self.client_token
		result = self.get_info(url)
		while result:
			board = {}
			line = result.pop()
			if not (line["name"] in filtering):
				board["id"] = line["id"]
				board["name"] = line["name"].encode('utf-8')
				boards.append(board)
		return boards

	def export_cards(self,boards=[]):
		cards = []
		while boards:
			line = boards.pop()
			url = "https://api.trello.com/1/boards/"+line["id"]+"?lists=open&list_fields=name&fields=name,desc&key="+self.client_secret+"&token="+self.client_token
			result = self.get_info(url)
			while result["lists"]:
				card = {}
				record = result["lists"].pop()
				card["board"] = line["name"] 
				card["id"] = record["id"]
				card["name"] = record["name"]
				cards.append(card)
		return cards

	def export_tasks(self,cards=[]):
		tasks = []
		actual_task = ""
		line = []
		urls = []
		for line in cards:
			url = "https://api.trello.com/1/lists/"+line["id"]+"?fields=name&cards=open&card_fields=name&key="+self.client_secret+"&token="+self.client_token
			if not (url in urls):
				result = self.get_info(url)
				records = 0
				urls.append(url)
				results = result["cards"]
				while results:
					records += 1
					task = {}
					card = results.pop()
					if actual_task != unicode(card["name"]):
						task["board"] = line["board"]
						task["id"] = card["id"]
						task["card"] = line["name"]
						task["name"] = unicode(card["name"])
						tasks.append(task)							
						actual_task = unicode(card["name"])
		return tasks

	def send_mail(self,data,recipient):
		mail_user = self.mail_user
		mail_pwd = self.mail_password
		FROM = self.mail_user
		TO = [recipient] #must be a list
		SUBJECT = "Trello Tasks ("
		TEXT = data
		TIME = time.strftime("%d/%m/%Y")
		SUBJECT += TIME + ")"

		# Prepare actual message
		message = """\From: %s\nTo: %s\nSubject: %s\n\n%s
		""" % (FROM, ", ".join(TO), SUBJECT, TEXT)
		try:
  			#server = smtplib.SMTP(SERVER) 
			server = smtplib.SMTP(self.mail_server, self.mail_port) #or port 465 doesn't seem to work!
			server.ehlo()
			server.starttls()
			server.login(mail_user, mail_pwd)
			server.sendmail(FROM, TO, message)
			#server.quit()
			server.close()
			print 'successfully sent the mail'
		except:
			print "failed to send mail"

## This is an usage example. You can delete it.		
trello_instance = Trello()
export = ["id","board","card","name"]
filtering = ["Itx","Welcome Board"]
boards = trello_instance.export_boards(filtering)
print "Exported boards"
cards = trello_instance.export_cards(boards)
print "Exported tasks"
tasks = trello_instance.export_tasks(cards)
tasks = trello_instance.export_tasks(cards)
print "Exported cards"
data = trello_instance.export_info(tasks)
email = raw_input("Email?")
trello_instance.send_mail(data,email)
