from scipy.io import loadmat
import numpy as np
import sounddevice as sd
from time import time
from core.data import settings

# Constants
SPIKE_WIDTH = settings.spike_width
SPIKE_THRESHOLD = settings.spike_threshold

OUTPUT_SAMPLE_RATE = 44000

def preprocess_audio(data, freq=OUTPUT_SAMPLE_RATE, spikes_only=False, spike_threshold=SPIKE_THRESHOLD):
	data = np.array(data).squeeze()
	data = data - data.mean()
	# data = data/np.linalg.norm(data)
	rng = np.abs(data).max()
	output = data/rng

	if spikes_only:
		sd = data.std()
		spike_bin = int(OUTPUT_SAMPLE_RATE*SPIKE_WIDTH/2)
		keep = np.logical_or(data > sd*spike_threshold, data < -sd*spike_threshold).squeeze()

		# Grab everything within a spike bin
		for idx in np.arange(-spike_bin, spike_bin + 1):
			if idx < 0:
				keep = np.logical_or(keep, np.pad(keep[-idx:], (0,-idx), 'constant', constant_values=(0)))
			elif idx > 0:
				keep = np.logical_or(keep, np.pad(keep[:-idx], (idx,0), 'constant', constant_values=(0)))

		output[~keep] = 0

	return output

# x = time()
# file = loadmat('spikedata.mat')
# data = file['CSPK_1___02']

# print('Time to load data: %f' % (time() - x))
# y = time()
# output = preprocess_audio(data, spikes_only=False)
# print('Time to process data: %f' % (time() - y))
# sd.play(output)
