#!/usr/bin/env python
# coding: utf-8

# Author Alexandre Louisnard

# Download maps from Geoportail at zoom level 15 (1:25000) centered on the specified lon/lat in decimal degrees and with the specified expected size on paper.
# Usage: ./downloadTileTop25.py lon lat (in decimal degree)
# Example (Chamechaude): ./downloadTileTop25.py --lat=45.2875374 --lon=5.7879211

import sys
import argparse
import os
import math
import urllib2
from PIL import Image

# Constants
API_KEY = "XXXXXXXXXXXXXXXXXX"
REFERER = "Firefox"
LAYER = "GEOGRAPHICALGRIDSYSTEMS.MAPS"
# 1:25000 zoom level
ZOOM="15"

# Get arguments
parser=argparse.ArgumentParser(prog="Geoportail 1:25000 Downloader", description="Download maps from Geoportail at zoom level 15 (1:25000) centered on the specified lon/lat (in decimal degrees) and with the specified expected size (in decimal cm) on paper.")
parser.add_argument('--lon', type=float, required=True, help='(required) The map center longitude, in decimal degrees')
parser.add_argument('--lat', type=float, required=True, help='(required) The map center latitude, in decimal degrees')

parser.add_argument('--width', type=float, help='(optional) The paper map width, in decimal cm (by default: 21 for A4 portrait format)', default=21)
parser.add_argument('--height', type=float, help='(optional) The paper map height, in decimal cm (by default: 29.7 for A4 portrait format)', default=29.7)

parser.add_argument('--toLon', type=float, help='(optional) If specified, the map will go from --lon to --toLon. --width will be ignored.')
parser.add_argument('--toLat', type=float, help='(optional) If specified, the map will go from --lat to --toLat. --height will be ignored.')
args=parser.parse_args()

if args.toLon:
	lon_start = args.lon
	lon_end = args.toLon
	height_km = (lon_end - lon_start) * 111
	paper_height = height_km / 25000.0 * 100000.0
else:
	# 1° of latitude or longitude is equivalent to 111 km
	paper_width = args.width
	width_km = paper_width * 25000.0 / 100000.0
	lon_start = args.lon - (width_km / 111.0) / 2.0
	lon_end = args.lon + (width_km / 111.0) / 2.0
if args.toLat:
	lat_start = args.lat
	lat_end = args.toLat
	width_km = (lat_end - lat_start) * 111
	paper_width = width_km / 25000.0 * 100000.0
else:
	paper_height = args.height
	height_km = paper_height * 25000.0 / 100000.0
	lat_start = args.lat - (height_km / 111.0) / 2.0
	lat_end = args.lat + (height_km / 111.0) / 2.0

print "from longitude\t{:>12} to {:<12} for a paper map width {:.2f} cm ({:.2f} km, {} degrees)".format(lon_start, lon_end, paper_width, width_km, lon_end-lon_start)
print "from latitude\t{:>12} to {:<12} for a paper map height {:.2f} cm ({:.2f} km, {} degrees)".format(lat_start, lat_end, paper_height, height_km, lat_end-lat_start)

def main():
	# Convert (lon,lat) to (x,y) web-mercator coordinates in meters 
	(x_start, y_start) = lonlat2xy(lon_start,lat_start)
	(x_end, y_end) = lonlat2xy(lon_end,lat_end)

	(xx_start, yy_start) = shiftXY(x_start, y_start)
	(xx_end, yy_end) = shiftXY(x_end, y_end)

	# Scale Denominator for ZOOM=15
	scale_denominator = 17061.8366707982724577   # scale 1:scale_denominator

	# The standardized rendering pixel size is defined to be 0.28mm x 0.28mm.
	rendering_pixel_size = 0.00028                       		# meters / rendering pixel ???
	pixel_size = rendering_pixel_size * scale_denominator  		# meters / pixel
	tile_width_height = 256                                		# pixels
	tile_size = tile_width_height * pixel_size               	# meters

	col_start = int(xx_start / tile_size)
	col_end = int(xx_end / tile_size)
	row_start = int(yy_start / tile_size)
	row_end = int(yy_end / tile_size)

	if (col_start > col_end):
		tmp = col_end
		col_end = col_start
		col_start = tmp
		
	if (row_start > row_end):
		tmp = row_end
		row_end = row_start
		row_start = tmp

	print "from col\t{:>12} to {:<12} ({} cols)".format(col_start, col_end, col_end-col_start)
	print "from row\t{:>12} to {:<12} ({} rows)".format(row_start, row_end, row_end-row_start)

	# Download all tiles
	for col in range (col_start, col_end + 1):
		for row in range (row_start, row_end + 1):
			COL = str(col)
			ROW = str(row)

			# Prepare URL and file
			URL = "http://wxs.ign.fr/"+API_KEY+"/geoportail/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER="+LAYER+"&STYLE=normal&TILEMATRIXSET=PM&TILEMATRIX="+ZOOM+"&TILEROW="+ROW+"&TILECOL="+COL+"&FORMAT=image/jpeg"  
			FILE = "zoom"+ZOOM+"-row"+ROW+"-col"+COL+".jpeg"

			# Launch HTTP request and save output
			req = urllib2.Request(URL)
			req.add_header('Referer', REFERER)
			ans = urllib2.urlopen(req)
			output = open(FILE,'wb')
			output.write(ans.read())
			output.close()
		
	# Join all tiles
	script_dir = os.path.dirname(os.path.abspath(__file__))
	# For each row, join all columns horizontally
	for row in range(row_start, row_end + 1):
		cols = [os.path.join(script_dir, "zoom"+ZOOM+"-row"+str(row)+"-col"+str(col)+".jpeg") for col in range(col_start, col_end + 1)]
		images = map(Image.open, cols)
		widths, heights = zip(*(i.size for i in images))

		total_width = sum(widths)
		max_height = max(heights)

		new_im = Image.new('RGB', (total_width, max_height))

		x_offset = 0
		for im in images:
		  new_im.paste(im, (x_offset,0))
		  x_offset += im.size[0]

		new_im.save("zoom"+ZOOM+"-row"+str(row)+".jpeg")
		
	# Join all reconstituted rows vertically
	rows = [os.path.join(script_dir, "zoom"+ZOOM+"-row"+str(row)+".jpeg") for row in range(row_start, row_end + 1)]
	images = map(Image.open, rows)
	widths, heights = zip(*(i.size for i in images))

	max_width = max(widths)
	total_height = sum(heights)

	new_im = Image.new('RGB', (max_width, total_height))

	y_offset = 0
	for im in images:
	  new_im.paste(im, (0,y_offset))
	  y_offset += im.size[1]

	new_im.save("zoom"+ZOOM+".jpeg")



### Computes (col, row) from (lon, lat) for ZOOM=15
# Documentation: http://api.ign.fr/tech-docs-js/fr/developpeur/wmts.html
# EPSG:3857 ("WGS 84 / Pseudo-Mercator")
## The GetCapabilities request gives the following values for EPSG:3857 at zoom level 15:
# <MinTileRow>10944</MinTileRow>
# <MaxTileRow>21176</MaxTileRow>
# <MinTileCol>163</MinTileCol><MaxTileCol>31695</MaxTileCol>
# <ScaleDenominator>17061.8366707982724577</ScaleDenominator>
# <TopLeftCorner>-20037508 20037508</TopLeftCorner>
# <TileWidth>256</TileWidth>
# <TileHeight>256</TileHeight>
# <MatrixWidth>32768</MatrixWidth>
# <MatrixHeight>32768</MatrixHeight></TileMatrix>
def lonlat2xy(lon_deg, lat_deg):
	lon_rad = math.radians(lon_deg)
	lat_rad = math.radians(lat_deg)
	# rayon equatorial (demi grand axe) de l'ellipsoide
	a = 6378137.0 # in meters
	x = a * lon_rad
	y = a * math.log(math.tan(lat_rad/2.0 + math.pi/4.0))
	return (x, y) # return coordinates in meters

# Shift coordinates according to the "Top Left Corner"
def shiftXY(x, y):
	# Top Left Corner for ZOOM=15
	x0 = -20037508 
	y0 = 20037508
	return (x-x0, y0-y)


if __name__ == '__main__':
    main()
