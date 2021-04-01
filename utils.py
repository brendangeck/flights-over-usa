import pyproj
import time

def gc_points(lon_0, lat_0, lon_1, lat_1, basemap, t=1.0):
    '''
    Partially ripped from here: t.ly/oB4q
    Given a start and end point, first calculate the great circle distance connecting the two
    Then, get the points (as lats and lons) needed to represent the great circle line between these points
    
    Notice the extra parameter 't'. We have a use case where we would like to plot a portion
    of the larger great circle line. T represents the amount of the line we want to consider
    For example, if t is set to 0, our line ends at <lon_0, lat_0>. If set to 0.5, we end halfway
    along the intended great circle line. If set to 1.0, then we want to full great circle line
    '''
    start = time.perf_counter()

    gc = pyproj.Geod(a=basemap.rmajor, b=basemap.rminor)

    # Rely on Geod to calculate the great circle distance
    # Note: The 'az' variables are the 'azimuths'. For the sake of this program,
    # you can just consider these directions: az_front is the directrom from 
    # point 0 to point 1. az_back is the direction from point 1 to point 0
    az_front, az_back, dist = gc.inv(lon_0, lat_0, lon_1, lat_1)

    # Use t to determine how "far" along this great circle distance we should travel
    dist_scaled = dist * t

    # Use Geod to fetch the lon and lat at our new distance along the great circle path
    lon_scaled, lat_scaled, _  = gc.fwd(lon_0, lat_0, az_front, dist_scaled)

    # Calculate the number of points needed to properly visualize this line
    npoints = int((dist_scaled + 0.5 * 1000 * 100) / (1000 * 100))

    # Rely on Geod to space these points out properly
    lonlats = gc.npts(lon_0, lat_0, lon_scaled, lat_scaled, npoints)

    # Unpack the longitudes and latitudes into separate arrays
    lons = [lon_0]
    lats = [lat_0]
    for lon, lat in lonlats:
        lons.append(lon)
        lats.append(lat)

    # Convert the lons and lats into x and y coordinates for proper plotting
    x, y = basemap(lons, lats)

    # Return these calculated x and y coordinates
    return x, y
