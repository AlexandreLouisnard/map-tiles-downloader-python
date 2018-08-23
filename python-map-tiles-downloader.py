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

#############################################################################################################################################
# Constants
#############################################################################################################################################
API_KEY = ""
REFERER = "Firefox"
LAYER = "GEOGRAPHICALGRIDSYSTEMS.MAPS"
# 1:25000 zoom level
ZOOM="15"
# Scale Denominator for ZOOM=15
SCALE_DENOMINATOR = 17061.8366707982724577
# The standardized rendering pixel size is defined to be 0.28mm x 0.28mm.
RENDERING_PIXEL_SIZE = 0.00028                       		# meters / rendering pixel ???
METERS_PER_PIXEL = RENDERING_PIXEL_SIZE * SCALE_DENOMINATOR  		# meters / pixel
TILE_SIZE_PX = 256                                		# pixels
TILE_SIZE_METERS = TILE_SIZE_PX * METERS_PER_PIXEL               	# meters
# 1° of latitude or longitude is equivalent to 111 km
METERS_PER_DEGREE = 111000.0
# 1:25000 means 250 m in reality for 1 cm on the paper
METERS_PER_PAPER_CM = 250

#############################################################################################################################################
# Variables declaration
#############################################################################################################################################
# Required by user
# Longitude/columns/width
required_lon_start = 0
required_lon_end = 0
required_width_m = 0
required_paper_width_cm = 0
#Latitude/rows/height
required_lat_start = 0
required_lat_end = 0
required_height_m = 0
required_paper_height_cm = 0

# Effective after rounding up to the required tiles
# Longitude/columns/width
effective_col_start = 0
effective_col_end = 0
effective_cols_count = 0
effective_width_m = 0
effective_paper_width_cm = 0
#Latitude/rows/height
effective_row_start = 0
effective_row_end = 0
effective_rows_count = 0
effective_height_m = 0
effective_paper_height_cm = 0

#############################################################################################################################################
# Variables initialization
#############################################################################################################################################
# Get arguments
parser=argparse.ArgumentParser(prog="Geoportail 1:25000 Downloader", description="Download maps from Geoportail at zoom level 15 (1:25000) centered on the specified lon/lat (in decimal degrees) and with the specified expected size (in decimal cm) on paper.")
parser.add_argument('--lon', type=float, required=True, help='(required) The map center longitude, in decimal degrees')
parser.add_argument('--lat', type=float, required=True, help='(required) The map center latitude, in decimal degrees')

parser.add_argument('--width', type=float, help='(optional) The paper map width, in decimal cm (by default: 21 for A4 portrait format)', default=21)
parser.add_argument('--height', type=float, help='(optional) The paper map height, in decimal cm (by default: 29.7 for A4 portrait format)', default=29.7)

parser.add_argument('--toLon', type=float, help='(optional) If specified, the map will go from --lon to --toLon. --width will be ignored.')
parser.add_argument('--toLat', type=float, help='(optional) If specified, the map will go from --lat to --toLat. --height will be ignored.')
args=parser.parse_args()

# Required longitudes defined by from-to values
if args.toLon:
	required_lon_start = min(args.lon, args.toLon)
	required_lon_end = max(args.lon, args.toLon)
	required_width_m = (required_lon_end - required_lon_start) * METERS_PER_DEGREE
	required_paper_width_cm = required_width_m / METERS_PER_PAPER_CM
# Required longitudes defined by center-width values
else:
	required_paper_width_cm = args.width
	required_width_m = required_paper_width_cm * METERS_PER_PAPER_CM
	required_lon_start = args.lon - (required_width_m / METERS_PER_DEGREE) / 2.0
	required_lon_end = args.lon + (required_width_m / METERS_PER_DEGREE) / 2.0
# Required latitudes defined by from-to values
if args.toLat:
	required_lat_start = min(args.lat, args.toLat)
	required_lat_end = max(args.lat, args.toLat)
	required_height_m = (required_lat_end - required_lat_start) * METERS_PER_DEGREE
	required_paper_height_cm = required_height_m / METERS_PER_PAPER_CM
# Required latitudes defined by center-width values
else:
	required_paper_height_cm = args.height
	required_height_m = required_paper_height_cm * METERS_PER_PAPER_CM
	required_lat_start = args.lat - (required_height_m / METERS_PER_DEGREE) / 2.0
	required_lat_end = args.lat + (required_height_m / METERS_PER_DEGREE) / 2.0

print "Asked to download:"
print " longitude from {:>9.5f} to {:<10.5f} <-> paper width  {:>4.1f} cm <-> {:>5.0f} px <-> terrain width  {:>5.0f} m = {:>9.5f} degrees".format(required_lon_start, required_lon_end, required_paper_width_cm, required_width_m / METERS_PER_PIXEL, required_width_m, required_lon_end-required_lon_start)
print " latitude  from {:>9.5f} to {:<10.5f} <-> paper height {:>4.1f} cm <-> {:>5.0f} px <-> terrain height {:>5.0f} m = {:>9.5f} degrees".format(required_lat_start, required_lat_end, required_paper_height_cm, required_height_m / METERS_PER_PIXEL, required_height_m, required_lat_end-required_lat_start)

#############################################################################################################################################
# main()
#############################################################################################################################################
def main():
	# Convert (lon,lat) to (x,y) web-mercator coordinates in meters 
	(x_start, y_start) = lonlat2xy(required_lon_start,required_lat_start)
	(x_end, y_end) = lonlat2xy(required_lon_end,required_lat_end)

	(xx_start, yy_start) = shiftXY(x_start, y_start)
	(xx_end, yy_end) = shiftXY(x_end, y_end)

	effective_col_start = int(xx_start / TILE_SIZE_METERS)
	effective_col_end = int(xx_end / TILE_SIZE_METERS)
	effective_row_start = int(yy_start / TILE_SIZE_METERS)
	effective_row_end = int(yy_end / TILE_SIZE_METERS)

	if (effective_col_start > effective_col_end):
		tmp = effective_col_end
		effective_col_end = effective_col_start
		effective_col_start = tmp
		
	if (effective_row_start > effective_row_end):
		tmp = effective_row_end
		effective_row_end = effective_row_start
		effective_row_start = tmp
		
	effective_cols_count = effective_col_end - effective_col_start + 1
	effective_rows_count = effective_row_end - effective_row_start + 1
	effective_width_m = effective_cols_count * TILE_SIZE_METERS
	effective_height_m = effective_rows_count * TILE_SIZE_METERS
	effective_paper_width_cm = effective_cols_count * TILE_SIZE_METERS / METERS_PER_PAPER_CM
	effective_paper_height_cm = effective_rows_count * TILE_SIZE_METERS / METERS_PER_PAPER_CM

	print "\nActually downloading:"
	print " {:>4} cols from {:>9} to {:<10} <-> paper width  {:>4.1f} cm <-> {:>5.0f} px <-> terrain width  {:>5.0f} m = {:>9.5f} degrees".format(effective_cols_count, effective_col_start, effective_col_end, effective_paper_width_cm, effective_cols_count * TILE_SIZE_PX,  effective_width_m, effective_width_m / METERS_PER_DEGREE)
	print " {:>4} rows from {:>9} to {:<10} <-> paper height {:>4.1f} cm <-> {:>5.0f} px <-> terrain height {:>5.0f} m = {:>9.5f} degrees".format(effective_rows_count, effective_row_start, effective_row_end, effective_paper_height_cm, effective_rows_count * TILE_SIZE_PX, effective_height_m, effective_height_m / METERS_PER_DEGREE)

	# Download all tiles
	for col in range (effective_col_start, effective_col_end + 1):
		for row in range (effective_row_start, effective_row_end + 1):
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
	for row in range(effective_row_start, effective_row_end + 1):
		cols = [os.path.join(script_dir, "zoom"+ZOOM+"-row"+str(row)+"-col"+str(col)+".jpeg") for col in range(effective_col_start, effective_col_end + 1)]
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
	rows = [os.path.join(script_dir, "zoom"+ZOOM+"-row"+str(row)+".jpeg") for row in range(effective_row_start, effective_row_end + 1)]
	images = map(Image.open, rows)
	widths, heights = zip(*(i.size for i in images))

	max_width = max(widths)
	total_height = sum(heights)

	new_im = Image.new('RGB', (max_width, total_height))

	y_offset = 0
	for im in images:
		new_im.paste(im, (0,y_offset))
		y_offset += im.size[1]
		
	new_im.save("IGN-zoom"+ZOOM+".jpeg")
	
	# Clean up tiles
	for row in range(effective_row_start, effective_row_end + 1):
		os.remove("zoom"+ZOOM+"-row"+str(row)+".jpeg")
		for col in range(effective_col_start, effective_col_end + 1):
			os.remove("zoom"+ZOOM+"-row"+str(row)+"-col"+str(col)+".jpeg")




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
	X0 = -20037508 
	Y0 = 20037508
	return (x-X0, Y0-y)


if __name__ == '__main__':
    main()
