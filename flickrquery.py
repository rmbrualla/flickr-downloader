#Image querying script written by Tamara Berg,
#and extended heavily James Hays

#9/26/2007 added dynamic timeslices to query more efficiently.
#8/18/2008 added new fields and set maximum time slice.
#8/19/2008 this is a much simpler function which gets ALL geotagged photos of
# sufficient accuracy.  No queries, no negative constraints.
# divides up the query results into multiple files
# 1/5/2009
# now uses date_taken instead of date_upload to get more diverse blocks of images
# 1/13/2009 - uses the original im2gps keywords, not as negative constraints though

import sys, string, math, socket
import time as os_time
from flickrapi import FlickrAPI
from datetime import datetime, date, time
import calendar
from flickr_api_key import *

import pyprind


def convertDate(date_string):
    tokens = date_string.split('/')
    year = int(tokens[2])
    month = int(tokens[1])
    day = int(tokens[0])
    d = date(year, month, day)
    t = time(0, 0)
    dt = datetime.combine(d, t)
    return calendar.timegm(dt.utctimetuple())


def NumberImagesInInterval(fapi, mintime, maxtime, query_args):
    min_taken_date=str(datetime.fromtimestamp(round(mintime)))
    max_taken_date=str(datetime.fromtimestamp(round(maxtime)))

    try:
        os_time.sleep(0.5)
        rsp1 = fapi.photos.search(media="photos",
                              per_page="300", 
                             page="1",
                             min_upload_date=min_taken_date,
                             max_upload_date=max_taken_date,
                             format='parsed-json',
                              **query_args)
    except FlickError as e:
        print e
        return (0, {})

    if rsp1['stat'] != 'ok':
        print 'Return status: ', rsp1['stat']

    total1 = int(rsp1['photos']['total'])

    #print 'Calling api (%s, %s) => %d' % (min_taken_date, max_taken_date, total1)

    return (total1, rsp1)


def processResult(rsp):
    global progress_bar
    result = {}
    
    if True:
        
        if True:
            for b in rsp['photos']['photo']:
                if b!=None:
                    photo_id = b['id']

                    #photo_data = { }
                    #photo_data['id'] = b['id']
                    #photo_data['secret'] = b['secret']
                    #photo_data['server'] = b['server']
                    #photo_data['farm'] = b['farm']
                    #photo_data['owner'] = b['owner']
                    #photo_data['title'] = b['title']
                    #photo_data['originalsecret'] = b['originalsecret']
                    #photo_data['originalformat'] = b['originalformat']
                    #photo_data['o_height'] = b['o_height']
                    #photo_data['o_width'] = b['o_width']
                    #photo_data['datetaken'] = b['datetaken'].encode("ascii","replace")
                    #photo_data['dateupload'] = b['dateupload'].encode("ascii","replace")
                    #photo_data['tags'] = b['tags'].encode("ascii","replace")
                    #photo_data['license'] = b['license'].encode("ascii","replace")
                    #photo_data['latitude'] = b['latitude'].encode("ascii","replace")
                    #photo_data['longitude'] = b['longitude'].encode("ascii","replace")
                    #photo_data['accuracy'] = b['accuracy'].encode("ascii","replace")
                    #photo_data['views'] = b['views']
                    dateupload = b['dateupload']
                    result[photo_id] = b
                    progress_bar.update(item_id = str(date.fromtimestamp(float(dateupload))))
    return result



def subdivide(num_photos, start_time, end_time, query_args, fapi, recursive):
    result = {}
    if recursive >= 5:
        print '\nRecursive reach: ', recursive, ' skipping ', num_photos, 
        return result

    if num_photos == 0:
        return result   
    photos_per_page = 100
    num_pages = (num_photos + photos_per_page) / photos_per_page
    #print 'subdivide photos: %s pages: %d range: %d %d' % (num_photos, num_pages, start_time, end_time)
    time_delta = (end_time - start_time) / num_pages
    t1 = start_time
    for i in range(num_pages):
        t2 = t1 + time_delta
        tries = 0
        while tries < 10:
            (n, rsp) = NumberImagesInInterval(fapi, t1, t2, query_args)
            if n <= num_photos and n > 0:
                break
            tries = tries + 1
        if tries == 10:
            n = 0;
        if n > 2 * photos_per_page and recursive < 5:
            res = subdivide(n, t1, t2, query_args, fapi, recursive + 1)
            result.update(res)
        elif (n > 0):
            if n > 2 * photos_per_page:
                print '\nSkipping due to recursion ', (n - 2 * photos_per_page), ' photos'
            res = processResult(rsp)
            result.update(res)
        t1 = t2
    return result;

def run_flickr_query(max_photos = 1000, startDate = "1/1/2010", endDate = "31/12/2011", query_args = {}):
    global progress_bar

    socket.setdefaulttimeout(30)  #30 second time out on sockets before they throw
    #an exception.  I've been having trouble with urllib.urlopen hanging in the 
    #flickr API.  This will show up as exceptions.IOError.

    #the time out needs to be pretty long, it seems, because the flickr servers can be slow
    #to respond to our big searches.

    ###########################################################################
    # Modify this section to reflect your data and specific search 
    ###########################################################################
    # flickr auth information:
    # change these to your flickr api keys and secret

    # make a new FlickrAPI instance
    fapi = FlickrAPI(flickrAPIKey, flickrSecret)

    #print '\n\nquery_string is ' + query_string
    total_images_queried = 0;

    # number of seconds to skip per query  

    starttime = convertDate(startDate)
    endtime = convertDate(endDate)


    photos_per_page = 100;

    tries = 0
    while tries < 10:
        extra_args = {'extras':  "original_format,license,geo,date_taken,date_upload,url_o,url_h,url_b"}
        extra_args.update(query_args)

        (num_photos, rsp) = NumberImagesInInterval(fapi, starttime, endtime, extra_args)
        if num_photos < 100000 and num_photos > 0:
            break
        tries = tries + 1
    if tries == 10:
        return {}
    print 'Querying for "%s" (%d photos)' % (str(query_args), num_photos)

    progress_bar = pyprind.ProgPercent(num_photos, title='Photos processed')

    result = subdivide(num_photos, starttime, endtime, extra_args, fapi, 0)
    progress_bar.stop()

    return result
