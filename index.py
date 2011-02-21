#!/usr/bin/env python
# -*- coding: utf-8 -*-

XML_NEWS_FEED = "http://rss.appleactionews.com/rss.xml"

from google.appengine.ext import db

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import time, datetime

# Try to import feedparser (append library in sys path)
try:
	import feedparser, pytz
except ImportError:
	import sys, os
	sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'library'))
	import feedparser, pytz

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
class UtilHelper(object):
	# UtilHelper().to_date_time(str(entry.updated_parsed[:-3]))
	def to_date_time(self, string, format = "(%Y, %m, %d, %H, %M, %S)"):
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
		
		# Add each entry to table
		for entry in feed_dict.entries:
			# If current news not in news table
			if entry.title not in temp_entry:
				try:
					self.puts("<p>%s :: %s</p>" % (entry.title, entry.updated_parsed))
					
					news = NewsModel(
						title = entry.title,
						link = entry.link,
						description = entry.description,
						publish_date = str(entry.updated_parsed),
						add_date = datetime.datetime.now(tz=pytz.timezone('Asia/Hong_Kong'))
					)
					news.put()
				except UnicodeEncodeError:
					pass # if news has full-width characters will except ?
		
	def puts(self, message):
		self.response.out.write(message)

class MainPage(webapp.RequestHandler):
	def get(self):
		self.response.headers['Content-Type'] = 'text/plain'
		self.response.out.write("This is a hk apple news robot for plurk")

if __name__ == "__main__":
	run_wsgi_app(webapp.WSGIApplication([
		('/', MainPage),
		('/fetch-news', FetchNews),
	], debug=True))