import time
import matplotlib.cm as mplcm
import matplotlib.colors as colors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from datetime import datetime, timedelta
from matplotlib.colors import to_rgba
from matplotlib.lines import Line2D
from mpl_toolkits.basemap import Basemap

from utils import gc_points

# Load the datset
flights_raw = pd.read_csv('flights.csv')
flights = flights_raw.astype({
    'carrier': 'str',
    'dep_airport': 'str',
    'arr_airport': 'str',
    'dep_latitude': 'float64',
    'dep_longitude': 'float64',
    'arr_latitude': 'float64',
    'arr_longitude': 'float64',
    'dep_datetime_utc': 'datetime64',
    'air_time_minutes': 'float64'
})
flights = flights.sort_values(['dep_datetime_utc', 'carrier', 'dep_airport', 'arr_airport'])

# Draw the map
coast_color = (0, 0, 0, 0)

unique_airlines = flights['carrier'].unique()

flight_colormap = plt.get_cmap('gist_rainbow')
c_norm = colors.Normalize(vmin=0, vmax=len(unique_airlines)-1)
scalar_map = mplcm.ScalarMappable(norm=c_norm, cmap=flight_colormap)
airline_colors_raw = [scalar_map.to_rgba(i) for i in range(len(unique_airlines))]
airline_colors = [(color[0], color[1], color[2], 0.3) for color in airline_colors_raw]

airline_color = pd.DataFrame()
airline_color['airline'] = unique_airlines
airline_color['color'] = airline_colors
airline_color = airline_color.set_index('airline')

fig = plt.figure(dpi=400)
ax = fig.add_subplot(111)

fig.set_facecolor('black')
ax.set_facecolor('black')
time_text = ax.text(0, 0, '00:00:00 EST', color=(0.8, 0.8, 0.8, 1))

plt.gca().set_position([0.01, 0.01, 0.99, 0.99])

plt.ion()
plt.show()

# Create our map centered on the USA
m = Basemap(
    width=12000000,
    height=8000000,
    projection='lcc',
    resolution='c',
    lat_1=0,
    lat_2=10,
    lat_0=43,  # center latitude of map
    lon_0=-105  # center longitude of map
)

m.drawcoastlines(color=coast_color, linewidth=1.0)


def upsert_line(idx, airline, xdata, ydata):
    '''
    Creates a new line or updates the data of a line that already exists
    '''
    if idx >= len(ax.lines):
        color = airline_color.at[airline, 'color']
        line = Line2D(xdata, ydata, color=color, linewidth=0.66)
        ax.add_line(line)
    else:
        ax.lines[idx].set_xdata(xdata)
        ax.lines[idx].set_ydata(ydata)


def decay_line(idx):
    '''
    Decreases the opacity of a line that has already reached its final destination
    '''
    color = to_rgba(ax.lines[idx].get_color())

    decayed_alpha = color[3] - 0.05
    if decayed_alpha < 0:
        decayed_alpha = 0

    new_color = (color[0], color[1], color[2], decayed_alpha)
    ax.lines[idx].set_color(new_color)

    return decayed_alpha


# The Flight Launch Algo:
# Our flights are stored in order of their departure time, with this in mind we...
#   Have a variable to track what "time" it currently is
#   Fetch the next flight from our flights dataframe
#   If its departure time is on or before the current "time", set it as an "active" flight
#   Advance to the next flight
#   Repeat the previous 3 steps until our current flight departs at a time in the future
#   Increment the current "time" by our desired delta and repeat the previous steps

flight_iter = flights.iterrows()
idx, flight = next(flight_iter)

# Start time is the departure time of the first flight
start_time = flight['dep_datetime_utc']

# End time is 1 day after the start_time
end_time = start_time + timedelta(days=2)

t = start_time
active_flights = pd.DataFrame()
inactive_flights = pd.DataFrame()

frame_counter = 0
while t < end_time:
    t_etc_str = (t + timedelta(hours=-5)).strftime('%H:%M:%S')
    time_text.set_text(f'{t_etc_str} EST')

    while flight is not None and flight['dep_datetime_utc'] <= t:
        # Each flight must have a unique ID. 
        # This is how its corresponding line in the figure will be updateed
        # To keep things simple, we will have the ID be the index of the flight
        flight['id'] = int(idx)
        active_flights = active_flights.append(flight, ignore_index=True)
        try:
            idx, flight = next(flight_iter)
        except:
            flight = None
            break

    # t is the total elapsed time divided by the air time
    minutes_elapsed = active_flights['dep_datetime_utc'].subtract(t).multiply(-1).dt.total_seconds().divide(60)
    flight_proportion = minutes_elapsed / active_flights['air_time_minutes']
    active_flights['t'] = flight_proportion

    # Get the line2c for each lerped greatcircle path
    active_flights['points'] = active_flights.apply(
        lambda row: gc_points(
            lon_0=row['dep_longitude'],
            lat_0=row['dep_latitude'],
            lon_1=row['arr_longitude'],
            lat_1=row['arr_latitude'],
            basemap=m,
            t=row['t']
        ),
        axis=1
    )

    # Draw each active flight
    active_flights.apply(
        lambda row: upsert_line(int(row['id']), row['carrier'], row['points'][0], row['points'][1]),
        axis=1
    )

    # Remove all flights that have been completed (these are no longer "active")
    # Set them to start decaying
    ended_flights = active_flights[active_flights['t'] > 1.0]
    active_flights = active_flights[active_flights['t'] <= 1.0]

    inactive_flights = inactive_flights.append(ended_flights)
    opacities = inactive_flights.apply(
        lambda row: decay_line(int(row['id'])),
        axis=1
    )

    # Remove any flights that have faded entirely, so we don't recalculate unecessarily
    if len(opacities) > 0:
        inactive_flights = inactive_flights[opacities > 0]

    # Save 
    plt.savefig('img/%07d.png' % frame_counter)

    plt.draw()
    plt.pause(0.00001)
    t = t + timedelta(minutes=1)

    frame_counter += 1
