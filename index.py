#!/usr/bin/env python
# -*- coding: utf-8 -*-

DEBUG = True
ENABLE_PLURK_TEST_PAGE = False
XML_NEWS_FEED = "http://rss.appleactionews.com/rss.xml"

# Import GAE package
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from django.utils import simplejson as json

# Import system package
import time, datetime, urllib, urllib2, cookielib, logging

# Try to import feedparser (append library in sys path)
try:
	import feedparser, pytz
except ImportError:
	import sys, os
	sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'library'))
	import feedparser, pytz
	
# Custom file
import config, googl

# Entry
class NewsEntry(object):
	def __init__(self, title, link, description, publish_date):
		self.title = title
		self.link = link
		self.description = description
		self.publish_date = publish_date

# Models
class NewsModel(db.Model):
	title = db.StringProperty(required=True)
	link = db.StringProperty(required=True)
	description = db.TextProperty(required=True)
	publish_date = db.TextProperty(required=True)
	add_date = db.DateTimeProperty()
	
class SettingModel(db.Model):
	value = db.StringProperty(required=False)
	
# Helper
"""
class UtilHelper(object):
	# UtilHelper().to_time_struct(str(entry.updated_parsed[:-3]))
	def to_time_struct(self, string, format = "(%Y, %m, %d, %H, %M, %S)"):
		return time.strptime(string, format)

class SettingHelper(object):
	setting = {}
	
	def get(self, name):
		setting = SettingModel.get_by_key_name(name)
		try:
			return setting.value
		except AttributeError:
			return ""
				
	def set(self, name, value):
		model = SettingModel(key_name=name)
		model.value = value
		model.put()
"""
class PlurkHelper(object):
	opener = None
	api_key = ""

	def __init__(self, api_key):
		self.api_key = api_key
		self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())

	def get_api_url(self, action):
		return 'http://www.plurk.com/API%s' % action

	def login(self, username, password):
		try:
			response = self.opener.open(
				self.get_api_url('/Users/login'),
				urllib.urlencode({'username': username, 'password': password, 'api_key': self.api_key})
			)
		except urllib2.HTTPError, message:
			logging.debug('HTTP Error on PlurkHelper.add_login')
			
			if message.code == 400:
				response = json.loads(message.fp.read().decode("utf-8"))
		
		return response
		
	def add_content(self, content):
		try:
			response = self.opener.open(
				self.get_api_url('/Timeline/plurkAdd'),
				urllib.urlencode({'content': content, 'qualifier': 'says', 'lang': 'en', 'api_key': self.api_key})
			)
		except urllib2.HTTPError, message:
			logging.debug('HTTP Error on PlurkHelper.add_content')
			
			if message.code == 400:
				response = json.loads(message.fp.read().decode("utf-8"))
				
		return response
		
# Controllers
class FetchNews(webapp.RequestHandler):
	def get(self):
		# Fetch news feed
		feed_dict = feedparser.parse(XML_NEWS_FEED)
		
		# Get latest 20 rows from news table 
		temp_entry = []
		newsModel = NewsModel.all()
		newsModel.order("-add_date")
		newsModel.fetch(limit=20)
		for news in newsModel:
			temp_entry.append(news.title)
		
		# Reverse news (for plurk, latest will show in first)
		feed_dict.entries.reverse()
		
		# Login to plurk
		plurk = PlurkHelper(config.API_KEY)
		login = plurk.login(config.USERNAME, config.PASSWORD)
		
		if DEBUG == True:
			self.puts("<p>login: %s</p>" % str(login))
		
		# Add each entry to table
		for entry in feed_dict.entries:
			# If current news not in news table
			if entry.title not in temp_entry:
				try:
					# Display news
					self.puts("<p>%s :: %s</p>" % (entry.title, entry.updated_parsed))

					# Short url by goo.gl
					entry.link = googl.shorten(entry.link)
					
					# Create plurk content
					message = u'%s (%s)' % (entry.link, entry.title)
					message = message.encode("utf-8")
					
					# Debug is or not encode message success?
					# Using utf-8 to decode, Because it is encode by utf-8
					if DEBUG is True:
						self.puts("<p>-- Content: %s<p>" % message.decode("utf-8"))
						
					# Post to plurk
					content = plurk.add_content(message)

					# Debug post status
					if DEBUG is True:
						self.puts("<p>-- Plurk Back: %s</p>" % str(content))
						
					# If not error_text
					if "error_text" not in content:
						news = NewsModel(
							title = entry.title,
							link = entry.link,
							description = entry.description,
							publish_date = str(entry.updated_parsed),
							add_date = datetime.datetime.now(tz=pytz.timezone('Asia/Hong_Kong'))
						)
						news.put()
						self.puts("<p>-- Saved</p>")
						
						time.sleep(5) # delay 300 secs -- for anti-flood(HTTPError: HTTP Error 400: BAD REQUEST)
				except UnicodeEncodeError:
					self.puts("<p>Unicode Error %s</p>")
					
					logging.debug('Unicode Error' % entry.title)
		
	def puts(self, message):
		self.response.out.write(message)

class AddPlurkTest(webapp.RequestHandler):
	def get(self):
		if ENABLE_PLURK_TEST_PAGE is True:
			plurk = PlurkHelper(config.API_KEY)
			login = plurk.login(config.USERNAME, config.PASSWORD)
			post = plurk.add_content("this is a test message: %s" % datetime.datetime.now())
			self.response.out.write( login )
			self.response.out.write( "<br />" )
			self.response.out.write( post )
		else:
			self.response.out.write("Please switch to debug mode")

class MainPage(webapp.RequestHandler):
	def get(self):
		self.response.headers['Content-Type'] = 'text/plain'
		self.response.out.write("This is a hk apple news robot for plurk")

if __name__ == "__main__":
	run_wsgi_app(webapp.WSGIApplication([
		('/', MainPage),
		('/fetch-news', FetchNews),
		('/add-plurk-test', AddPlurkTest),
	], debug=True))