"""
Understanding GIS: Assessment 2 POSTGRADUATE VERSION
@author [INSERT STUDENT NUMBER HERE]

** ONLY USE THIS TEMPLATE IF YOU ARE A POSTGRADUATE (MSc) STUDENT **
"""
from math import exp
from time import perf_counter

# set start time
start_time = perf_counter()	

''' NO CODE ABOVE HERE '''

# set the start and end coordinates of the route (British National Grid)
START = (322500, 307500)    # Welshpool
END = (349200, 312500)      # Shrewsbury

# set the weights for the visibility penalty to test (0 = quickest route)
WEIGHTS = [0, 0.25, 1, 5, 10]

# set the the height of the lookout and walker (m)
LOOKOUT_HEIGHT = 5      # assume a person stood on a fort is 5 m above the ground
WALKER_HEIGHT = 1.8     # assume average height of a person is 1.8 m above the ground

# the maximum distance (m) at which a lookout could detect a small party on foot
RADIUS = 5000   # (use this as the viewshed radius)

# the maximum walking speed from Tobler's Hiking Function (6 km/h). `/ 3.6` converts to m/s)
MAX_SPEED = 6 / 3.6 # (`distance / MAX_SPEED` gives you the fastest possible speed - useful for calculating a heuristic)


def tobler_time(dz, distance):
    """
    * I am providing this function to you to use in the calculation of speed of travel over 
    *   terrain.
    *
    * Calculate the time (in seconds) taken to walk a given horizontal distance (in metres)
    *	with a given change in elevation (in metres), using Tobler's Hiking Function:
    *
    * 	speed (km/h) = 6 * e^(-3.5 * |slope + 0.05|)
    *
    * References:
    *   Tobler (1993):      https://escholarship.org/uc/item/05r820mz
    *   Goodchild (2020):   https://onlinelibrary.wiley.com/doi/epdf/10.1111/gean.12253?saml_referrer
    *   Wikipedia page:     https://en.wikipedia.org/wiki/Tobler%27s_hiking_function
    """
    # calculate the slope (rise over run)
    slope = dz / distance

    # calculate the walking speed in km/h using Tobler's Hiking Function
    speed = 6 * exp(-3.5 * abs(slope + 0.05))

    # convert the speed to m/s and return the time taken (time = distance / speed)
    return distance / (speed / 3.6) # (`/ 3.6` converts km/h to m/s)



''' NO CODE BELOW HERE '''

# report runtime
print(f"completed in: {perf_counter() - start_time} seconds")