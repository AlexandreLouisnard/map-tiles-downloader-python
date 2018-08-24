# Map tiles downloader

**Author: Alexandre Louisnard alouisnard@gmail.com**  
**Python 3 script**  
**2018**

## DESCRIPTION
Download maps from Geoportail at zoom level 15 (1:25000) in JPEG format.  
Map coordinates and size are specified by:
* Specifying the lon/lat center and the width/height of the desired paper map in centimeters;
* Specifying the lon/lat of the starting point and the lon/lat of the ending point.


## USAGE
>py -2 python_map_tiles_downloader.py  [-h] --lon LON --lat LAT  
>                                      [--width WIDTH] [--height HEIGHT]  
>                                      [--toLon TOLON] [--toLat TOLAT]  
>                                      [--force]  

**Example:**  
>py -2 python_map_tiles_downloader.py --lat=45.2875374 --lon=5.7879211 --width=21 --height=29.7

**optional arguments:**
* -h, --help       show this help message and exit

**required named arguments:**
* --lon LON        (required) The map center longitude, in decimal degrees
* --lat LAT        (required) The map center latitude, in decimal degrees

**optional named arguments:**
* --width WIDTH    (optional) The paper map width, in decimal cm (by default: 21 for A4 portrait format)
* --height HEIGHT  (optional) The paper map height, in decimal cm (by default: 29.7 for A4 portrait format)
* --toLon TOLON    (optional) If specified, the map will go from --lon to --toLon. --width will be ignored.
* --toLat TOLAT    (optional) If specified, the map will go from --lat to --toLat. --height will be ignored.
* --force          (optional) Force re-downloading the map tiles even if they are already in cache

## CHANGELOG

## BACKLOG
