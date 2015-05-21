import eventlet
from eventlet.green import urllib2
import os, os.path, json, math
import pyprind, subprocess
from PIL import Image
import io, multiprocessing

def downloadPhotos(imagedb, output_dir, target_max_dim, num_processes = 4, num_threads = 10):
  def resize_image(filename, width, height):
    n_pixels = float(width * height)
    n_target_pixels = target_max_dim * target_max_dim
    
    if n_pixels > n_target_pixels * 1.5:
      try:
        ratio = math.sqrt(n_target_pixels / (n_pixels * 1.0))
        target_width = int(width * ratio)
        target_height = int(height * ratio)
        cmd = 'mogrify -resize %dx%d %s' % (target_width, target_height, filename)

        subprocess.check_call(cmd, shell=True)
        return (os.system(cmd) == 0)
      except subprocess.CalledProcessError, e:
        return False
    return True

  def check_and_resize_image(filename):
    try:
      jhead_output = subprocess.check_output(['jhead', filename], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError, e:
      return False
    else:
      for line in jhead_output.splitlines():
        tokens = line.split()
        if len(tokens) == 5 and tokens[0] == 'Resolution' and int(tokens[2]) > 0 and int(tokens[4]) > 0:
          return resize_image(filename, int(tokens[2]), int(tokens[4]))
      return False

  global processed_photos, progress_bar, downloaded_photos
  elements = []
  n = 0
  for id, data in imagedb.iteritems():
    n = n + 1
    elem_dir = os.path.join(output_dir, id[0:3])

    if not os.path.exists(elem_dir):
      try:
        os.mkdir(elem_dir)
      except:
        pass
    image_filename = os.path.join(elem_dir, '%s.jpg' % id)

    elem = {}
    elem['id'] = id
    if 'url_o' in data:
      elem['ou'] = data['url_o']
    if 'url_b' in data:
      elem['lu'] = data['url_b']
    if 'url_h' in data:
      elem['hu'] = data['url_h']
    elem['of'] = image_filename
    elements.append(elem)


  def downloadLink(url, dest):
    try:
      fd = urllib2.urlopen(url)
      image_file = io.BytesIO(fd.read())
      im = Image.open(image_file)
      (width, height) = im.size
      if width * height < 5e5:
        return False
      pix_val = list(im.getdata())
      valid = False
      for i in range(0,100):
        if pix_val[i] != 238:
          valid = True
      if not valid:
        return False
      
      n_pixels = float(width * height)
      n_target_pixels = target_max_dim * target_max_dim * 3 / 4.0
      
      if n_pixels > n_target_pixels * 1.2:
        ratio = math.sqrt(n_target_pixels / (n_pixels * 1.0))
        target_width = int(width * ratio)
        target_height = int(height * ratio)
        im = im.resize((target_width, target_height), Image.ANTIALIAS)
      im.save(dest)
      return True
    except Exception as e:
      print 'Exception in downloadLink: ', e
      return False


  def fetch(elem):
    global progress_bar, processed_photos, downloaded_photos
    if 'hu' in elem:
      if downloadLink(elem['hu'], elem['of']):
        processed_photos = processed_photos   + 1
        downloaded_photos = downloaded_photos + 1
        progress_bar.update(item_id = '%d downloaded, %d processed' % (downloaded_photos, processed_photos))
        return (elem['id'], 'largeh')
    if 'ou' in elem:
      if downloadLink(elem['ou'], elem['of']):
        processed_photos = processed_photos + 1
        downloaded_photos = downloaded_photos + 1
        progress_bar.update(item_id = '%d downloaded, %d processed' % (downloaded_photos, processed_photos))
        return (elem['id'], 'original')
    if 'lu' in elem:
      if downloadLink(elem['lu'], elem['of']):
        processed_photos = processed_photos + 1
        downloaded_photos = downloaded_photos + 10
        progress_bar.update(item_id = '%d downloaded, %d processed' % (downloaded_photos, processed_photos))
        return (elem['id'], 'large')

    processed_photos = processed_photos + 1
    progress_bar.update(item_id = '%d downloaded, %d processed' % (downloaded_photos, processed_photos))
    return (elem['id'], 'fail')

  chunksize = int(math.ceil(len(elements) / float(num_processes)))
  procs = []

  progress_bar = pyprind.ProgPercent(chunksize, title='Photos downloaded')
  downloaded_photos = 0
  processed_photos =  0

  def worker(elements):
    pool = eventlet.GreenPool(num_threads)
    for id, stat in pool.imap(fetch, elements):
      if stat != 'fail':
        elem_dir = os.path.join(output_dir, id[0:3])
        metadata_filename = os.path.join(elem_dir, '%s.txt' % id)
        f = open(metadata_filename, 'w')
        json.dump(imagedb[id], f, sort_keys=True, indent=4, separators=(',', ': '))
        f.close()

  for i in range(num_processes):
      p = multiprocessing.Process(
              target=worker,
              args=([elements[chunksize * i:chunksize * (i + 1)]]))
      procs.append(p)
      p.start()

  # Wait for all worker processes to finish
  for p in procs:
      p.join()


