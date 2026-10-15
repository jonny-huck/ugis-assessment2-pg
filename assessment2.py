"""
Understanding GIS: Assessment 2 Resit
@author [INSERT STUDENT NUMBER HERE]
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
LOOKOUT_HEIGHT = 5
WALKER_HEIGHT = 1.8

# the maximum distance (m) at which a lookout could detect a small party on foot
RADIUS = 5000   # (use this as the viewshed radius)

# the maximum walking speed from Tobler's Hiking Function (6 km/h, converted to m/s)
MAX_SPEED = 6 / 3.6

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
	return distance / (speed / 3.6)



''' NO CODE BELOW HERE '''

# report runtime
print(f"completed in: {perf_counter() - start_time} seconds")










# this block will only run if the script is executed directly
if __name__ == "__main__":



	# make sure that the weights are valid (must not be negative)
	if not all([w >= 0 for w in WEIGHTS]):
		print("Sorry, all of the weights must be >= 0")
		exit()

	# open the elevation data file (a virtual raster that mosaics the OS Terrain 50 tiles),
	# 	catching the error if it can't be found
	try:
		with rio_open("./data/welsh-borders/welsh_border.vrt") as dem:

			# read the data out of band 1 in the dataset, and get the transform object
			dem_data = dem.read(1)
			transform = dem.transform

	# if the file can't be opened, tell the user and stop
	except RasterioIOError:
		print("Sorry, could not open the DEM - please check the file path.")
		exit()

	# open the dataset of fortified sites, catching the error if it can't be found
	try:
		sites = read_csv("./data/welsh-borders/marches_sites.csv")

	# if the file can't be opened, tell the user and stop
	except FileNotFoundError:
		print("Sorry, could not open the sites dataset - please check the file path.")
		exit()

	# get the resolution of the dataset (assumes square cells)
	resolution = transform[0]

	# convert the start and end of the route into image space
	start_cell = coord_2_img(transform, *START)
	end_cell = coord_2_img(transform, *END)

	# make sure that both are inside the dataset
	for cell in [start_cell, end_cell]:
		if not in_bounds(*cell, dem_data):
			print("Sorry, the route starts or ends outside the DEM - please check the coordinates.")
			exit()

	# start timer
	start_time = perf_counter()

	# create a single Executor (force spawn context) and use it for both stages, so we only pay the
	#	overhead of launching the processes once
	with ProcessPoolExecutor(mp_context=get_context("spawn")) as executor:

		''' STAGE 1: CUMULATIVE VIEWSHED '''

		# submit one viewshed per site. These are 'reverse' viewsheds: rather than calculating a viewshed
		#	from every cell that the walker might pass through to see which lookouts are visible (hundreds
		#	of thousands of viewsheds), we calculate one from each lookout to see where it can see, as
		#	visibility is (approximately) reciprocal. The lookout is the observer and the walker is the target.
		future_map = {}
		for idx, site in sites.iterrows():

			# submit the task to the executor and record the site name
			future = executor.submit(viewshed, site.easting, site.northing, RADIUS, LOOKOUT_HEIGHT, WALKER_HEIGHT,
				dem_data, transform)
			future_map[future] = site['name']

		# report how many processes were launched
		print(f"Launched {len(executor._processes)} processes...")

		# initialise a surface to hold the number of lookouts that can see each cell (16-bit, as
		#	more than 255 lookouts could theoretically see the same cell)
		visibility = zeros(dem_data.shape, dtype='uint16')

		# process the viewsheds as they complete
		for future in as_completed(future_map.keys()):

			# use try-except so if one viewshed fails they don't all fail
			try:
				# add each viewshed to the surface (giving the number of lookouts that can see each cell)
				visibility += future.result()

			# report any problems
			except Exception as e:
				print(f"ERROR: viewshed for {future_map[future]} failed: {e}")

		# report progress
		print(f"{len(future_map)} viewsheds complete after {perf_counter() - start_time:.2f} seconds.")

		''' STAGE 2: ROUTES '''

		# submit one route per weight
		future_map = {}
		for weight in WEIGHTS:

			# submit the task to the executor and record the weight
			future = executor.submit(astar_raster, start_cell, end_cell, dem_data, visibility, weight, resolution)
			future_map[future] = weight

		# initialise a dictionary for the routes
		routes = {}

		# process the routes as they complete
		for future in as_completed(future_map.keys()):

			# get the weight for this future
			weight = future_map[future]

			# use try-except so if one route fails they don't all fail
			try:
				# get the path for this route and convert it to a LineString in coordinate space
				routes[weight] = LineString([img_2_coord(transform, r, c) for r, c in future.result()])

			# catch exception for no path available
			except NoPathError:
				print(f"Sorry, there is no path available (weight={weight})")

	# report the time taken for the analysis
	print(f"Analysis complete after {perf_counter() - start_time:.2f} seconds.\n")

	# make sure that we have at least one route before going any further
	if not routes:
		print("Sorry, no routes could be found.")
		exit()

	# report the length of the route for each weight (the CRS units are metres, so convert to km)
	for weight in sorted(routes.keys()):
		print(f"Weight {weight}: {routes[weight].length / 1000:.1f} km") # .length acceptable for projected data

	''' DRAW YOUR MAP '''

	# create map axis object
	fig, my_ax = subplots(1, 1, figsize=(16, 10))
	my_ax.set_title("Welshpool to Shrewsbury: the sneakiest route", fontsize=16)

	# set a colour for each route using an existing color ramp
	cmap = colormaps['Blues']
	route_colours = dict(zip(WEIGHTS, cmap(linspace(0, 1, len(WEIGHTS)))))

	# draw dem (pale greyscale so that the other data stand out)
	rio_show(
		dem_data,
		ax=my_ax,
		transform=transform,
		cmap='Greys_r',
		alpha=0.6,
		zorder=0,
		)

	# draw the cumulative viewshed (masking out the cells that no lookout can see)
	rio_show(
		# masked_where(visibility == 0, visibility),
		visibility,
		ax=my_ax,
		transform=transform,
		cmap='YlOrRd',
		vmin=1,
		vmax=visibility.max(),
		alpha=0.8,
		)

	# add the sites
	my_ax.plot(sites.easting, sites.northing, linestyle='', marker='^', markersize=8, color='black', markeredgecolor='white')

	# add the route for each weight
	for weight, route in routes.items():
		GeoSeries(route).plot(ax=my_ax, color=route_colours[weight], linewidth=3, zorder=5)

	# add the start and end points with labels
	my_ax.plot(*START, marker='o', markersize=12, color='white', markeredgecolor='black', zorder=10)
	my_ax.plot(*END, marker='o', markersize=22, color='white', markeredgecolor='black', zorder=10)
	my_ax.annotate('Welshpool', xy=START, xytext=(8, -24), textcoords='offset points', fontsize=13, fontweight='bold')
	my_ax.annotate('Shrewsbury', xy=END, xytext=(-10, 14), textcoords='offset points', fontsize=13, fontweight='bold')

	# add a colour bar for the cumulative viewshed
	fig.colorbar(ScalarMappable(norm=Normalize(vmin=1, vmax=visibility.max()), cmap='YlOrRd'), ax=my_ax, pad=0.01,
		shrink=0.7, label="Number of visible forts")

	# manually draw a legend (one entry per route, plus the sites) below the map
	my_ax.legend(handles=[Line2D([0], [0], color=route_colours[w], lw=3, label=f"Visibility weight = {w}" +
		(" (quickest)" if w == 0 else "")) for w in sorted(routes.keys())] + [
		Line2D([0], [0], marker='^', color=(1, 1, 1, 0), markerfacecolor='black', markersize=10, label='Fortified site'),
		], loc='upper left', bbox_to_anchor=(0, -0.01), ncol=3, fontsize=11)

	# add north arrow
	x, y, arrow_length = 0.97, 0.99, 0.1
	my_ax.annotate('N', xy=(x, y), xytext=(x, y-arrow_length),
		arrowprops=dict(facecolor='black', width=5, headwidth=15),
		ha='center', va='center', fontsize=20, xycoords=my_ax.transAxes)

	# add scalebar
	my_ax.add_artist(ScaleBar(dx=1, units="m", location="lower right"))

	# remove axes
	my_ax.axis('off')

	# save the result
	savefig('./out/A2-PG.png', bbox_inches='tight')
	print("done!")
