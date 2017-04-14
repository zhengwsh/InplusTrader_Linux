import os
import json
import pymongo
import pandas as pd

from datetime import datetime, timedelta
from api2 import Config, PyApi
from api2 import BaseDataContainer, History, Bar

from errors import (VNPAST_ConfigError, VNPAST_RequestError,
VNPAST_DataConstructorError, VNPAST_DatabaseError)

class DBConfig(Config):
	"""
	Json-like config object; inherits from Config()

	Contains all kinds of settings relating to database settings.

	privates
	--------
	Inherited from api.Config, plus:

	* client: pymongo.MongoClient object, the connection
	  that is to be used for this session.
	* body: dictionary; the main content of config.

			- client: pymongo.MongoClient(), refers to self.client.

			- dbs: dictionary, is a mapping from database alias 
				   to another dictionary, which inclues configurations
				   and themselves(i.e. pymongo.database entity)
				   Concretely, dbs has the structure like:
				   {
				   		alias1 : {
				   			'self': client[dbName1],
				   			'index': dbIndex1,
				   			'collNames': collectionNameType1
				   		},
				   		alias2 : {
				   			'self': client[dbName2],
				   			'index': dbIndex2,
				   			'collNames': collectionNameType2
				   		}, ...
				   }
				   where alias#: string;
				   		 dbs.alias#.self: pymongo.database;
				   		 dbs.alias#.index: string;
				   		 dbs.alias#.collNames: string;

			- dbNames: list; a list of database alias.

	"""
	head = 'DB config'

	client = pymongo.MongoClient('172.18.181.134')
	body = {
		'client': client,
		'dbs': {
			'FUT_D1': {
				'self': client['idTrader_Future_Db'],
				'index': 'date',
				'collNames': 'futTicker'
			}
		},
		'dbNames': ['FUT_D1']
	}

	def __init__(self, head=None, token=None, body=None):
		""" 
		Inherited constructor. 

		parameters
		----------
		* head: string; the name of config file. Default is None.
		* token: string; user's token.
		* body: dictionary; the main content of config
		"""
		super(DBConfig, self).__init__(head, token, body)

	def view(self):
		""" Reloaded Prettify printing method. """
		config_view = {
			'dbConfig_head' : self.head,
			'dbConfig_body' : str(self.body),
		}
		print json.dumps(config_view, 
						 indent=4, 
						 sort_keys=True)

#----------------------------------------------------------------------
# MongoDB Controller class

class MongodController(object):
	"""
	The MongoDB controller interface.

	MongodController is initialized with a DBConfig configuration
	object and a PyApi object, which has already been contructed with
	its own Config json. The default version of constructor actually
	does nothing special about the database. Yet if user executes shell
	script prepare.sh to prepare the connection, MongodController will
	firstly gather symbols that are going to become collection names
	in corresponding databases. This process is done one database by another,
	user can skip useless databases by editing the scripts.
	Then, it ensures the index of each collection due to the 'index' value
	in DBConfig.body.dbs. Concretely, for D1 bars, the index will be 'date',
	and for intraday bars, it will be 'dateTime'; both take the form of 
	datetime.datetime timestamp.

	download() and update() methods of controller dynamically construct 
	and maintain the databases, requesting data via PyApi. Once the database
	is constructed, MongodController can access required data via its fetch()
	method.


	privates
	--------
	* _config: DBConfig object; a container of all useful settings for the
	  databases.

	* _api: PyApi object; is responsible for making requests.

	* _client: pymongo.MongoClient object; the connection to MongoDB.

	* _dbs: dictionary; a mapping from database names to another dictionary,
	  which includes configurations of the database and the pymongo.database
	  entity. Inherited from _config.body.['dbs']. Note that keys
	  self._dbs are mere strings, only self._dbs[key]['self'] refers to the 
	  pymongo.Database object.

	* _dbNames: list; a list of names of databases.

	* _collNames: dictionary; mapping from self._db[key]['collNames'] attribute
	  to the names of collections(i.e. tickers) within.
	  		- example: _collNames['equTicker'] = ['000001', '000002', ...]

	* _connected: boolean; whether the MongoClient was connected to or not.

	* _mapTickersToSecIDs: dictionary; mapping from stock tickers to 
	  its security ID.


	example
	-------
	>> myApi = PyApi(Config())
	>> mydbs = DBConfig()
	>> controller = MongodController(mydbs, myApi)
	>> controller._get_coll_names()
	>> controller._ensure_index()
	>> controller.download_equity_D1(20130101, 20150801)
	>> controller.update_equity_D1()

	"""
	_config = DBConfig()
	_api = None

	_client = None
	_dbs = None
	_dbNames = []
	_collNames = dict()
	_connected = False

	_mapTickersToSecIDs = dict()

	def __init__(self, config, api):
		"""
		Constructor.

		parameters
		----------
		* config: DBConfig object; specifies database configs.
		* api: PyApi object.

		"""
		self._api = api # Set Datayes PyApi.
		if config.body:
			try:
				self._config = config.body
				self._client = config.body['client']
				self._dbs = config.body['dbs']
				self._dbNames = config.body['dbNames']
				self._connected = True
			except KeyError:
				msg = '[MONGOD]: Unable to configure database; ' + \
					  'config file is incomplete.'
				raise VNPAST_ConfigError(msg)
			except Exception,e:
				msg = '[MONGOD]: Unable to configure database; ' + str(e)
				raise VNPAST_ConfigError(msg)

		if self._connected:
			#self._get_coll_names()
			#self._ensure_index()
			pass

	#----------------------------------------------------------------------
	# Get collection names methods.

	"""
	Decorator;
	Targeting at path dName, if exists, read data from this file;
	if not, execute handle() which returns a json-like data and
	stores the data at dName path.

	parameters
	----------
	* dName: string; the specific path of file that __md looks at.
	"""
	def __md(dName):
		def _md(get):
			def handle(*args, **kwargs):
				try:
					if os.path.isfile(dName):
						# if directory exists, read from it.
						jsonFile = open(dName,'r')
						data = json.loads(jsonFile.read())
						jsonFile.close()
					else:
						# if not, get data via *get method, 
						# then write to the file.
						data = get(*args, **kwargs)
						jsonFile = open(dName, 'w+')
						jsonFile.write(json.dumps(data))
						jsonFile.close()
					#print data
					return data
				except Exception,e:
					raise e
			return handle
		return _md

	@__md('names/futTicker.json')
	def _allFutTickers(self):
		"""get all future tickers, decorated by @__md()."""
		data = self._api.get_future_D1()
		allFutTickers = list(data.body['ticker'])
		return allFutTickers

	def _get_coll_names(self):
		"""
		get all instruments'names and store them in self._collNames.

		"""
		try:
			if not os.path.exists('names'):
				os.makedirs('names')

			self._collNames['equTicker'] = self._allEquTickers()
			self._collNames['fudTicker'] = self._allFudTickers()
			

			print '[MONGOD]: Collection names gotten.'
			return 1
		except AssertionError: 
			warning = '[MONGOD]: Warning, collection names ' + \
					  'is an empty list.'
			print warning
		except Exception, e:
			msg = '[MONGOD]: Unable to set collection names; ' + \
				   str(e)
			raise VNPAST_DatabaseError(msg)

	#----------------------------------------------------------------------
	# Ensure collection index method.

	def _ensure_index(self):
		"""
		Ensure indices for all databases and collections.

		first access self._dbs config to get index column names;
		then get collection names from self._collNames and loop
		over all collections.

		"""
		if self._collNames and self._dbs:
			try:
				for dbName in self._dbs:
					# Iterate over database configurations.

					db = self._dbs[dbName]
					dbSelf = db['self']
					index = db['index']
					collNames = self._collNames[db['collNames']]
					# db['self'] is the pymongo.Database object.

					for name in collNames:
						coll = dbSelf[name]
						coll.ensure_index([(index, 
											pymongo.DESCENDING)], unique=True)
				print '[MONGOD]: MongoDB index set.'
				return 1
			except KeyError:
				msg = '[MONGOD]: Unable to set collection indices; ' + \
					  'infomation in Config.body["dbs"] is incomplete.'
				raise VNPAST_DatabaseError(msg)
			except Exception, e:
				msg = '[MONGOD]: Unable to set collection indices; ' + str(e)
				raise VNPAST_DatabaseError(msg)

	#----------------------------------------------------------------------
	# Download method.


	def download_future_D1(self, start, end, sessionNum=30):
		"""

		"""
		try:
			db = self._dbs['FUT_D1']['self']
			self._api.get_future_D1_mongod(db, start, end, sessionNum)
		except Exception, e:
			msg = '[MONGOD]: Unable to download data; ' + str(e)
			raise VNPAST_DatabaseError(msg)



	#----------------------------------------------------------------------
	# Update methods.

	def __update(self, key, target1, target2, sessionNum):
		"""
		Basic update method.
		Looks into the database specified by 'key', find the latest 
		record in the collection of it. Then update the collections 
		till last trading date.

		parameters
		----------
		* key: string; a database alias (refer to the database config)
		  e.g., 'EQU_D1'.
		* target1: method; pointer to the function with which controller
		  obtain all tickers in the database. Concretely, target1 are 
		  self._all#Tickers methods.
		* target2: method; pointer to the api overlord requesting functions
		  i.e. self._api.get_###_mongod methods.
		* sessionNum: integer; the number of threads.

		"""
		try:
			# get databases and tickers
			db = self._dbs[key]['self']
			index = self._dbs[key]['index']
			allTickers = target1()
			coll = db[allTickers[0]]

			# find the latest timestamp in collection.
			latest = coll.find_one(
					 sort=[(index, pymongo.DESCENDING)])[index]
			start = datetime.strftime(
				latest + timedelta(days=1),'%Y%m%d')
			end = datetime.strftime(datetime.now(), '%Y%m%d')

			# then download.
			target2(db, start, end, sessionNum)
			return db
			
		except Exception, e:
			msg = '[MONGOD]: Unable to update data; ' + str(e)
			raise VNPAST_DatabaseError(msg)


	def update_future_D1(self, sessionNum=30):
		"""

		"""
		db = self.__update(key = 'FUT_D1',
					  	   target1 = self._allFutTickers,
					  	   target2 = self._api.get_future_D1_mongod,
					  	   sessionNum = sessionNum)
		return db

	#----------------------------------------------------------------------
	# Fetch method.

	def fetch(self, dbName, ticker, start, end, output='list'):
		"""

		"""
		# check inputs' validity.
		if output not in ['df', 'list', 'json']:
			raise ValueError('[MONGOD]: Unsupported output type.')
		if dbName not in self._dbNames:
			raise ValueError('[MONGOD]: Unable to locate database name.')

		db = self._dbs[dbName]
		dbSelf = db['self']
		dbIndex = db['index']
		try:
			coll = db[ticker]
			if len(start)==8 and len(end)==8:
				# yyyymmdd, len()=8
				start = datetime.strptime(start, '%Y%m%d')
				end = datetime.strptime(end, '%Y%m%d')
			elif len(start)==14 and len(end)==14:
				# yyyymmdd HH:MM, len()=14
				start = datetime.strptime(start, '%Y%m%d %H:%M')
				end = datetime.strptime(end, '%Y%m%d %H:%M')
			else:
				pass
			docs = []

			# find in MongoDB.
			for doc in coll.find(filter={dbIndex: {'$lte': end,
				'$gte': start}}, projection={'_id': False}):
				docs.append(doc)

			if output == 'list':
				return docs[::-1]

		except Exception, e:
			msg = '[MONGOD]: Error encountered when fetching data' + \
				  'from MongoDB; '+ str(e)
			return -1
