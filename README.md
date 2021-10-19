# Kibana user profiling
This gives a quick tool to profile user queries on Kibana (and indirectly on Elasticsearch).

## Introduction
This tool was made to quickly analyze how users query Kibana (and Elasticsearch) on a 6.8 cluster.
The result was great! very helpful.
_Note_: Not tested on other versions than 6.8, specially since Kibana 7.7 that uses async.

## Capture traffic
First, we need to capture traffic. Here, we used `packetbeat` installed on the Elasticsearch node queried by Kibana to capture all traffic coming from Kibana to Elasticsearch (not the logs coming from data ingestion).

Then, simply create a saved search in Discover to display:
* @timestamp, in the form `October 5th 2021, 20:59:56.052`, in UTC
* path, for instance `/myindex/_search`
* responsetime (integer, in ms)
* http.request.body that is the body posted, like `{"size": 0,"query": {"range": {"event.end": {"gte": "now-24h","lt": "now"}}}}`

The time range should be on 1 day, midnight to midnight.
Once the search is saved, export in CSV, name the file `export.csv`.

_Note_: if the file is too big, change the `xpack.reporting.csv.maxSizeBytes` setting (by default 10MB). If you can't, simply chunk the export by hour for instance, naming `export-NN.csv` for instance.

## What's inside this export?
Answer: a mess :-/
The body part can be a proper json... or not! `_msearch` usually concatenates several json.
The date range also varies, sometimes in `now-10m` form, sometimes in millisecond epoch, sometimes in unix timestamp...

## Use this tool
In its simplest form, simply works placing this py file in the same directory than the exported csv file(s) and running:
`python kibana-user-profiling.py`
This should export a new `kibana-user-profiling.csv` file.

Inside the script, several hard coded values may be adapted:
* epoch dates shifted to UTC+2 (Paris time!)
* years, parsing taking '2021' into account, so if you're in 2022...
* several paths are excluded like `_xpack`, `_security`, rollup indices, internal `.*` indices etc. You may want to keep them

## Visualize using Excel!
Yeah I know, Excel...
python could work all the way to the visualization, but I really like Excel!
Do not open the csv file as is. This won't work. Instead, use Data > Get Data (or New Query) > From CSV.
Once imported, the table has 12 columns.

I added a few columns afterwards, but they could be computed by the py script of course:
* a query type, being 'dashboard' for _msearch queries, 'count' for _count ones and 'search' for _search ones
* a start age in hours, computed as the difference between timeEnd-epoch and timeStart-epoch, divided by 3600
* a viz type (for instance a date histogram) and query filter (for instance a term filter), parsed from the body, computed using a VB macro, but I didn't finish it... :-(

From there, I created several reports like:
* histogram of number of requests, per age (displayed hereunder)
* number of queries, per index (pivot table, index in lines, query type in columns, with a simple count as values)
* average response time, per index (pivot table, index in lines, query type in columns, with avg response time)

![image](https://user-images.githubusercontent.com/30144076/137923421-5603f32a-fdaa-4963-92bd-519f8f53d838.png)

If your histogram looks very crushed as mine here, you should customize bins.
Add a sheet, make new bins - mine are 0.2, 0.3, 3, 48, 120, 480 hours, and beyond.
Then use the `FREQUENCY` function, like `=FREQUENCY('data'!M2:M8225;'freq range'!B2:B8)`
I also added a cumulated %

Here you go:

![image](https://user-images.githubusercontent.com/30144076/137922582-a7e70866-10df-4ddd-a1b7-217a1b4cd8b1.png)

You can build a histogram out of it:

![image](https://user-images.githubusercontent.com/30144076/137922712-c5fd3683-fb08-4651-b089-fd3f1314f04a.png)

## Conclusion
In my example, this analysis showed 95% requests target data that are less than 5 days old, 97% less than 30 days old.
Quite a hint to play with ILM and resize!
Happy profiling!

## Author
* Author: Vincent Maury
* Contributor: a great partner of Elastic that cannot be shared ;)
* License: Apache 2.0
