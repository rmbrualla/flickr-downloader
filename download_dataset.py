#!/usr/bin/env python

import flickrquery
import argparse
import os.path, os
import subprocess, math
import json
from joblib import Parallel, delayed
import pyprind

import flickr_downloader

parser = argparse.ArgumentParser()
parser.add_argument("output_dir", help="output directory where images will be stored")
parser.add_argument("num_images", help="max number of images")
parser.add_argument("--query", help="query string", default="")
parser.add_argument("--geo", help="lat,lon,radius", default="")
parser.add_argument('--only_cc', help="download only Creative Commons images.", dest='only_cc', action='store_true')
parser.add_argument('--only_cc_nr', help="download only Creative Commons images with no restrictions.", dest='only_cc_nr', action='store_true')

parser.set_defaults(only_cc=False)
parser.set_defaults(only_cc_nr=False)

parser.add_argument("-start_date", help="start date", default="01/01/2003")
parser.add_argument("-end_date", help="end date", default="01/01/2016")
parser.add_argument("-target_max_dim", type=int, help="Target max dimension", default=1600)

args = parser.parse_args()

if not os.path.exists(args.output_dir):
  os.mkdir(args.output_dir)
if not os.path.exists(args.output_dir):
  print 'Cannot create output directory, exiting.'
  exit()

all_results = {}

query_results_file = os.path.join(args.output_dir, 'query_results.txt')
if not os.path.exists(query_results_file):
  print 'Querying flickr...'
  if len(args.query) > 0:
    queries = args.query.split(';')

    for q in queries:
      print q
      query_args = {'text': q}
      if args.only_cc:
        query_args['license'] = '4,5,6,7'
      if args.only_cc_nr:
        query_args['license'] = '4'
      results = flickrquery.run_flickr_query(query_args=query_args, max_photos = args.num_images, startDate=args.start_date, endDate=args.end_date)

      print 'Found %d images for query: %s' % (len(results), q)
      for photo_id, data in results.items():
        all_results[photo_id] = data;
  if len(args.geo) > 0:
    tokens = args.geo.split(',')
    if len(tokens) != 3:
      print 'geo argument format: lat,lon,radius'
      raise
    query_args={'lat': tokens[0], 'lon': tokens[1], 'radius':tokens[2]}
    if args.only_cc:
      query_args['license'] = '1,2,3,4,5,6,7'
      
    results = flickrquery.run_flickr_query(query_args=query_args, max_photos = args.num_images, startDate=args.start_date, endDate=args.end_date)

    print 'Found %d images for query: %s' % (len(results), args.geo)
    for photo_id, data in results.items():
      all_results[photo_id] = data;

  print 'Caching results...'

  f = open(query_results_file, 'w')
  json.dump(all_results, f, sort_keys=True, indent=4, separators=(',', ': '))
  f.close()

  print 'Downloading %d images.' % len(all_results.keys())
else:
  print 'Loading cached results...'
  f = open(query_results_file, 'r')
  all_results = json.load(f)
  f.close()
  print 'Found %d images for the queries.' % len(all_results.keys())

print 'Calling download'

flickr_downloader.downloadPhotos(all_results, args.output_dir, args.target_max_dim)

