#!/usr/bin/env python
# coding: utf-8

# Author Alexandre Louisnard

# Download maps from Geoportail at zoom level 15 (1:25000) centered on the specified lon/lat in decimal degrees and with the specified expected size on paper.
# Usage: ./downloadTileTop25.py lon lat (in decimal degree)
# Example (Chamechaude): ./downloadTileTop25.py --lat=45.2875374 --lon=5.7879211 --width=21 --height=29.7

import sys
import argparse
import os
import math
import urllib2
from PIL import Image
#############################################################################################################################################
# Secret data
#############################################################################################################################################
from secret_data import * # Import from other file or define below
# API_KEY_GEOPORTAIL = ""

#############################################################################################################################################
# Constants
#############################################################################################################################################
# Geoportail constants
MAP_NAME = "IGN"
REFERER = "Firefox"
LAYER = "GEOGRAPHICALGRIDSYSTEMS.MAPS"
# 1:25000 Geoportail zoom level
ZOOM="15"
# Map scale denominator for ZOOM=15 (not exactly 1:25000 but close)
SCALE_TERRAIN_M_PER_PAPER_M = 17061.8366707982724577							# terrain meters / paper meter
# The standardized rendering pixel size is defined to be 0.28mm x 0.28mm.
PAPER_METERS_PER_PIXEL = 0.00028												# paper meters / pixel
TERRAIN_METERS_PER_PIXEL = PAPER_METERS_PER_PIXEL * SCALE_TERRAIN_M_PER_PAPER_M	# terrain meters / pixel
TILE_SIZE_PX = 256                                								# pixels
TILE_SIZE_TERRAIN_METERS = TILE_SIZE_PX * TERRAIN_METERS_PER_PIXEL  			# terrain meters

# Common constants
# 1° of latitude or longitude is equivalent to 111 km
TERRAIN_METERS_PER_DEGREE = 111000.0											# terrain meters / degree
EARTH_EQUATORIAL_RADIUS_M = 6378137.0												# meters

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = "temp"

#############################################################################################################################################
# Variables declaration
#############################################################################################################################################
# Required by user with command-line arguments
# Longitude/columns/width
required_lon_start = 0
required_lon_end = 0
required_paper_width_cm = 0
required_terrain_width_m = 0
#Latitude/rows/height
required_lat_start = 0
required_lat_end = 0
required_paper_height_cm = 0
required_terrain_height_m = 0

# Effective after rounding up to the required tiles
# Longitude/columns/width
effective_col_start = 0
effective_col_end = 0
effective_cols_count = 0
effective_paper_width_cm = 0
effective_terrain_width_m = 0
#Latitude/rows/height
effective_row_start = 0
effective_row_end = 0
effective_rows_count = 0
effective_paper_height_cm = 0
effective_terrain_height_m = 0

#############################################################################################################################################
# Variables initialization
#############################################################################################################################################
# Get arguments
parser=argparse.ArgumentParser(prog="Geoportail 1:25000 Downloader", description="Download maps from Geoportail at zoom level 15 (1:25000) centered on the specified lon/lat (in decimal degrees) and with the specified expected size (in decimal cm) on paper.")
required_named = parser.add_argument_group('required named arguments')
optional_named = parser.add_argument_group('optional named arguments')

required_named.add_argument('--lon', type=float, required=True, help='(required) The map center longitude, in decimal degrees')
required_named.add_argument('--lat', type=float, required=True, help='(required) The map center latitude, in decimal degrees')

optional_named.add_argument('--width', type=float, help='(optional) The paper map width, in decimal cm (by default: 21 for A4 portrait format)', default=21)
optional_named.add_argument('--height', type=float, help='(optional) The paper map height, in decimal cm (by default: 29.7 for A4 portrait format)', default=29.7)

optional_named.add_argument('--toLon', type=float, help='(optional) If specified, the map will go from --lon to --toLon. --width will be ignored.')
optional_named.add_argument('--toLat', type=float, help='(optional) If specified, the map will go from --lat to --toLat. --height will be ignored.')

optional_named.add_argument('--force', action='store_true', help='(optional) Force re-downloading the map tiles even if they are already in cache')

args=parser.parse_args()

# Required longitudes defined by from-to values
if args.toLon:
	required_lon_start = min(args.lon, args.toLon)
	required_lon_end = max(args.lon, args.toLon)
	required_terrain_width_m = (required_lon_end - required_lon_start) * TERRAIN_METERS_PER_DEGREE
	required_paper_width_cm = required_terrain_width_m / (SCALE_TERRAIN_M_PER_PAPER_M / 100.0)
# Required longitudes defined by center-width values
else:
	required_paper_width_cm = args.width
	required_terrain_width_m = required_paper_width_cm * (SCALE_TERRAIN_M_PER_PAPER_M / 100.0)
	required_lon_start = args.lon - (required_terrain_width_m / TERRAIN_METERS_PER_DEGREE) / 2.0
	required_lon_end = args.lon + (required_terrain_width_m / TERRAIN_METERS_PER_DEGREE) / 2.0
# Required latitudes defined by from-to values
if args.toLat:
	required_lat_start = min(args.lat, args.toLat)
	required_lat_end = max(args.lat, args.toLat)
	required_terrain_height_m = (required_lat_end - required_lat_start) * TERRAIN_METERS_PER_DEGREE
	required_paper_height_cm = required_terrain_height_m / (SCALE_TERRAIN_M_PER_PAPER_M / 100.0)
# Required latitudes defined by center-width values
else:
	required_paper_height_cm = args.height
	required_terrain_height_m = required_paper_height_cm * (SCALE_TERRAIN_M_PER_PAPER_M / 100.0)
	required_lat_start = args.lat - (required_terrain_height_m / TERRAIN_METERS_PER_DEGREE) / 2.0
	required_lat_end = args.lat + (required_terrain_height_m / TERRAIN_METERS_PER_DEGREE) / 2.0
force_redownload = args.force

print "Asked to download:"
print " longitude from {:>9.5f} to {:<10.5f} <-> paper width  {:>4.1f} cm <-> {:>5.0f} px <-> terrain width  {:>5.0f} m <-> {:>9.5f} degrees".format(required_lon_start, required_lon_end, required_paper_width_cm, required_terrain_width_m / TERRAIN_METERS_PER_PIXEL, required_terrain_width_m, required_lon_end-required_lon_start)
print " latitude  from {:>9.5f} to {:<10.5f} <-> paper height {:>4.1f} cm <-> {:>5.0f} px <-> terrain height {:>5.0f} m <-> {:>9.5f} degrees".format(required_lat_start, required_lat_end, required_paper_height_cm, required_terrain_height_m / TERRAIN_METERS_PER_PIXEL, required_terrain_height_m, required_lat_end-required_lat_start)

#############################################################################################################################################
# main()
#############################################################################################################################################
def main():
	# Create TEMP_DIR
	if not os.path.exists(TEMP_DIR):
		os.makedirs(TEMP_DIR)

	# Convert (lon,lat) to (x,y) web-mercator coordinates in meters 
	(x_start, y_start) = lon_lat_2_xy(required_lon_start,required_lat_start)
	(x_end, y_end) = lon_lat_2_xy(required_lon_end,required_lat_end)

	(xx_start, yy_start) = shift_xy(x_start, y_start)
	(xx_end, yy_end) = shift_xy(x_end, y_end)

	effective_col_start = int(xx_start / TILE_SIZE_TERRAIN_METERS)
	effective_col_end = int(xx_end / TILE_SIZE_TERRAIN_METERS)
	effective_row_start = int(yy_start / TILE_SIZE_TERRAIN_METERS)
	effective_row_end = int(yy_end / TILE_SIZE_TERRAIN_METERS)

	if effective_col_start > effective_col_end:
		tmp = effective_col_end
		effective_col_end = effective_col_start
		effective_col_start = tmp
		
	if effective_row_start > effective_row_end:
		tmp = effective_row_end
		effective_row_end = effective_row_start
		effective_row_start = tmp
		
	effective_cols_count = effective_col_end - effective_col_start + 1
	effective_rows_count = effective_row_end - effective_row_start + 1
	effective_terrain_width_m = effective_cols_count * TILE_SIZE_TERRAIN_METERS
	effective_terrain_height_m = effective_rows_count * TILE_SIZE_TERRAIN_METERS
	effective_paper_width_cm = effective_cols_count * TILE_SIZE_TERRAIN_METERS / (SCALE_TERRAIN_M_PER_PAPER_M / 100.0)
	effective_paper_height_cm = effective_rows_count * TILE_SIZE_TERRAIN_METERS / (SCALE_TERRAIN_M_PER_PAPER_M / 100.0)

	print "\nActually downloading:"
	print " {:>4} cols from {:>9} to {:<10} <-> paper width  {:>4.1f} cm <-> {:>5.0f} px <-> terrain width  {:>5.0f} m <-> {:>9.5f} degrees".format(effective_cols_count, effective_col_start, effective_col_end, effective_paper_width_cm, effective_cols_count * TILE_SIZE_PX,  effective_terrain_width_m, effective_terrain_width_m / TERRAIN_METERS_PER_DEGREE)
	print " {:>4} rows from {:>9} to {:<10} <-> paper height {:>4.1f} cm <-> {:>5.0f} px <-> terrain height {:>5.0f} m <-> {:>9.5f} degrees".format(effective_rows_count, effective_row_start, effective_row_end, effective_paper_height_cm, effective_rows_count * TILE_SIZE_PX, effective_terrain_height_m, effective_terrain_height_m / TERRAIN_METERS_PER_DEGREE)

	# Download all tiles
	for col in range (effective_col_start, effective_col_end + 1):
		for row in range (effective_row_start, effective_row_end + 1):
			# Check if tile already exists in cache
			if not force_redownload and os.path.exists(tile_file(MAP_NAME, ZOOM, row, col)):
				continue
		
			# Prepare URL and file
			URL = "http://wxs.ign.fr/"+API_KEY_GEOPORTAIL+"/geoportail/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER="+LAYER+"&STYLE=normal&TILEMATRIXSET=PM&TILEMATRIX="+ZOOM+"&TILEROW="+str(row)+"&TILECOL="+str(col)+"&FORMAT=image/jpeg"  

			# Launch HTTP request and save output
			req = urllib2.Request(URL)
			req.add_header('Referer', REFERER)
			ans = urllib2.urlopen(req)
			output = open(tile_file(MAP_NAME, ZOOM, row, col), 'wb')
			output.write(ans.read())
			output.close()
		
	# Join all tiles
	# For each row, join all columns horizontally
	for row in range(effective_row_start, effective_row_end + 1):
		cols = [os.path.join(SCRIPT_DIR, tile_file(MAP_NAME, ZOOM, row, col)) for col in range(effective_col_start, effective_col_end + 1)]
		images = map(Image.open, cols)
		widths, heights = zip(*(i.size for i in images))

		total_width = sum(widths)
		max_height = max(heights)

		new_im = Image.new('RGB', (total_width, max_height))

		x_offset = 0
		for im in images:
		  new_im.paste(im, (x_offset,0))
		  x_offset += im.size[0]

		new_im.save(merged_row_file(MAP_NAME, ZOOM, row, effective_col_start, effective_col_end))
				
	# Join all reconstituted rows vertically
	rows = [os.path.join(SCRIPT_DIR, merged_row_file(MAP_NAME, ZOOM, row, effective_col_start, effective_col_end)) for row in range(effective_row_start, effective_row_end + 1)]
	images = map(Image.open, rows)
	widths, heights = zip(*(i.size for i in images))

	max_width = max(widths)
	total_height = sum(heights)

	new_im = Image.new('RGB', (max_width, total_height))

	y_offset = 0
	for im in images:
		new_im.paste(im, (0,y_offset))
		y_offset += im.size[1]
		
	new_im.save(map_file(MAP_NAME, ZOOM, effective_row_start, effective_row_end, effective_col_start, effective_col_end))
	
	# Clean up cache
	for row in range(effective_row_start, effective_row_end + 1):
		os.remove(merged_row_file(MAP_NAME, ZOOM, row, effective_col_start, effective_col_end))
		# for col in range(effective_col_start, effective_col_end + 1):
			# os.remove(tile_file(MAP_NAME, ZOOM, row, col))




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
def lon_lat_2_xy(lon_deg, lat_deg):
	lon_rad = math.radians(lon_deg)
	lat_rad = math.radians(lat_deg)
	# rayon equatorial (demi grand axe) de l'ellipsoide
	x = EARTH_EQUATORIAL_RADIUS_M * lon_rad
	y = EARTH_EQUATORIAL_RADIUS_M * math.log(math.tan(lat_rad/2.0 + math.pi/4.0))
	return (x, y) # return coordinates in meters

# Shift coordinates according to the "Top Left Corner"
def shift_xy(x, y):
	# Top Left Corner for ZOOM=15
	X0 = -20037508 
	Y0 = 20037508
	return (x-X0, Y0-y)
	
def tile_file(map_name, zoom_level, row, col):
	return os.path.join(SCRIPT_DIR, TEMP_DIR, MAP_NAME+"_zoom"+zoom_level+"_row"+str(row)+"_col"+str(col)+".jpeg")
	
def merged_row_file(map_name, zoom_level, row, fromCol, toCol):
	return os.path.join(SCRIPT_DIR, TEMP_DIR, MAP_NAME+"_zoom"+zoom_level+"_row"+str(row)+"_cols"+str(fromCol)+"-"+str(toCol)+".jpeg")

def map_file(map, zoom_level, fromRow, toRow, fromCol, toCol):
	return os.path.join(SCRIPT_DIR, MAP_NAME+"_zoom"+zoom_level+"_rows"+str(fromRow)+"-"+str(toRow)+"_cols"+str(fromCol)+"-"+str(toCol)+".jpeg")
	
if __name__ == '__main__':
    main()
