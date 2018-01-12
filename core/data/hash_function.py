'''
Function to calculate all hash rates for a patient
'''

import numpy as np

HASH_THRESH_SD = 5; # number of standard dev above the noise floor for hash detection

# Noise floor parameters
TARGET = .159 # one standard deviation will have 0.159 values greater and 0.159 values lesser

# Hash rate parameters
DEAD_TIME_MS = 0.3
THRESH_HIGH = True # Set to false for low threshold

# Depth selection parameters
DEPTH_RANGE = [-5, 10]
# In seconds
MIN_RECORD_DURATION = .5

# Return a threshold based on # of standard deviations multiplied on noise floor
def noise_floor(data, freq, depth, sd=HASH_THRESH_SD):
	if data.size <= 1 or len(data.squeeze())/float(freq) < MIN_RECORD_DURATION or depth < DEPTH_RANGE[0] or depth > DEPTH_RANGE[1]:
		return np.nan
	data = np.sort(np.array(data).squeeze())
	x1, x2 = [int(np.round(len(data)*TARGET)), int(np.round(len(data)*(1-TARGET)))]
	noisefloor = [data[x1], data[x2]]
	return np.abs(noisefloor).mean() * sd

# Calculate the hashrate
def hash_rate(data, freq, depth, thresh):
	# Default rate of 0
	rate = 0

	data = np.array(data).squeeze()

	# Currently only limiting for depth, not minium record duration
	if data.size <= 1 or len(data.squeeze())/float(freq) < MIN_RECORD_DURATION or depth < DEPTH_RANGE[0] or depth > DEPTH_RANGE[1]:
		return rate

	# Dead time samples
	dead_samples = DEAD_TIME_MS * freq / 1000

	# Boolean array of values that pass threshold
	if THRESH_HIGH:
		crossed = data > thresh
	else:
		crossed = data < -thresh

	# Boolean operation with arrays to find all crosses
	crossed[1:][crossed[:-1] & crossed[1:]] = False	
	crossed_ind = np.where(crossed)[0]

	# comp = crossed.astype(int)
	# crossed_ind = np.where(comp[1:] - comp[:-1] == 1)[0]

	# If we find crossings
	if crossed_ind.size != 0:
		# Eliminate all threshold crossings within the dead interval
		elim = []

		last_ind = crossed_ind[0]
		for ind in crossed_ind[1:]:
			if ind - last_ind < dead_samples:
				elim.append(ind)
			else:
				last_ind = ind

		crossed_ind = np.delete(crossed_ind, elim)

		rate = len(crossed_ind) / (len(crossed) / float(freq))

	return rate

# Simple function for returning subset of depths that are appropriate
