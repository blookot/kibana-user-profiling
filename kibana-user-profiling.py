# kibana-user-profiling.py
# author: Vincent Maury, license: Apache 2.0
# reads a CSV export - trunked in N csv files - from packetbeat (frop Kibana discover) and reformats in a single csv with the relevant data
# expected fields: timestamp, path, responseTime, requestBody


import csv
import json
import os
import sys
from datetime import datetime, timedelta


# get all csv files in current dir
currentDir = os.getcwd()
filenames = os.listdir(currentDir)
csv.field_size_limit(sys.maxsize)


def readBody(path, body):
	# try reading json (could be empty)
	b = timeStart = timeEnd = index = query = aggs = ""
	# try reading the index from the path
	if path.endswith('/_search'):
		searchLoc = path.find('/_search')
		index = path[1:searchLoc]
	if path.endswith('/_count'):
		countLoc = path.find('/_count')
		index = path[1:countLoc]
	if body == '':
		return [b, timeStart, timeEnd, index, query, aggs]
	try:
		# Remove the LF (\n)
		b = body.replace('\n','').replace('\t','')
		# try to find index & time range info
		if b.startswith('{"index":'):
			index = b[10:b.find('","ignore_unavailable"')]
			if index.startswith('rollup-allsources'):
				index = 'rollup-allsources'
		gtLoc = b.find('"gte":')
		ltLoc = b.find('"lt', gtLoc)
		if gtLoc > 0 and ltLoc > 0:
			timeStart = b[gtLoc:ltLoc].replace(',','').replace('"gte":','').replace('"','').strip()
			timeEnd = b[ltLoc:b.find('}',ltLoc)].replace(',"format":"epoch_millis"','').replace('"lt":','').replace('"lte":','').replace('"','').strip()
			# date conversion
		# trying to load as json (doesn't work for _msearch)
		b = json.loads(b)
		# capture a few info
		if "query" in b:
			query = b["query"]
		if "aggs" in b:
			aggs = b["aggs"]
		timeStart = b['query']['bool']['filter']['range']['event.end']['gte'].replace('/d','').replace('||/m','')
		timeEnd = b['query']['bool']['filter']['range']['event.end']['lt'].replace('/d','').replace('||/m','')
		return [b, timeStart, timeEnd, index, query, aggs]
	except Exception as e:
		# print('*** ERROR ' + format(e))
		return [b, timeStart, timeEnd, index, query, aggs]


# change the date format
def dateShift(timestamp, start, end):
	t = s = e = ''
	# change timestamp to epoch, form of "October 5th 2021, 06:22:57.199", taking into account the UTC+2
	eventTime = datetime.strptime(timestamp.replace('5th', '05'), '%B %d %Y, %H:%M:%S.%f') + timedelta(hours=2)
	t = int(eventTime.timestamp())
	if start == '' or end == '':
		return [t,s,e]
	# sometimes already in epoch
	if start.startswith('1'):
		return [t, start[:-3], end[:-3]]
	# if it's now-10d
	if start.startswith('now-'):
		if start.endswith('m'):
			n = int(start[4:start.find('m')])
			s = int((eventTime - timedelta(minutes=n)).timestamp())
		if start.endswith('h'):
			n = int(start[4:start.find('h')])
			s = int((eventTime - timedelta(hours=n)).timestamp())
		if start.endswith('d'):
			n = int(start[4:start.find('d')])
			s = int((eventTime - timedelta(days=n)).timestamp())
	# if it's iso like 2021-10-05T10:06:41.849Z
	if start.startswith('2021-'):
		s = int(datetime.strptime(start, '%Y-%m-%dT%H:%M:%S.%fZ').timestamp())
	if end.startswith('2021-'):
		e = int(datetime.strptime(end, '%Y-%m-%dT%H:%M:%S.%fZ').timestamp())
	if end == 'now':
		e = t
	return [t, s, e]


# open the export file
with open('kibana-user-profiling.csv', 'w', newline='', encoding='utf-8') as exportFile:
	writer = csv.writer(exportFile, quoting=csv.QUOTE_ALL)
	writer.writerow(['@timestamp', '@timestamp-epoch', 'path', 'response time', 'body', 'timeStart', 'timeStart-epoch', 'timeEnd', 'timeEnd-epoch', 'index', 'query', 'aggs'])
	# scroll the csv files
	for filename in filenames:
		if filename.startswith("export") and filename.endswith(".csv"):
			# open each file
			print("Reading file: ", filename)
			with open(filename, 'r', encoding='utf-8') as file:
				reader = csv.reader(file, quoting=csv.QUOTE_ALL)
				# drop the header (fields)
				fields = []
				fields = next(reader)
				# scroll all rows
				for row in reader:
					# print("==> ",row)
					timestamp = row[0]
					path = row[1]
					responseTime = row[2]
					body = row[3]
					# lines with no body are not interesting
					if body != "" and not path.startswith('/_xpack') and not path.startswith('/.') and not path.startswith('/api') and not path.startswith('/_security') and not path.startswith('/_template') and not path.startswith('/s/') and not path.startswith('/rollup') and not path.startswith('/_search/scroll'):
						requestBody = readBody(path, body)
						newDates = dateShift(timestamp, requestBody[1], requestBody[2])
						writer.writerow([timestamp] + [newDates[0]] + [path, responseTime] + requestBody[0:2] + [newDates[1]] + [requestBody[2]] + [newDates[2]] + requestBody[3:6])

print("Done writing to kibana-user-profiling.csv!")
