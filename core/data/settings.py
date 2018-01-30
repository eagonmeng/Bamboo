'''
Filename and path settings
'''

# Default source folder location
# source_path = '/media/DriveOne/todd/OR/'
source_path = 'C:\MGH\data\\'

# List of supported input files
INPUT_FILETYPES = ['.mat']

# Channel management defaults on new view
only_data_channels = False
only_spike_channels = True

# Default three channel view
three_channels = True

# Default data channels
data_channels = ['CRAW_01', 'CRAW_02', 'CRAW_03',
	'CSPK_01', 'CSPK_02', 'CSPK_03',
	'CLFP_01', 'CLFP_02', 'CLFP_03',
	'CRAW_1___01', 'CRAW_1___02', 'CRAW_1___03',
	'CSPK_1___01', 'CSPK_1___02', 'CSPK_1___03',
	'CLFP_1___01', 'CLFP_1___02', 'CLFP_1___03']
spike_channels = ['CSPK_01', 'CSPK_02', 'CSPK_03',
	'CSPK_1___01', 'CSPK_1___02', 'CSPK_1___03']

# Channel regexp groups to automatically populate three views
reg_data = ['^(CRAW_0)([1-3])$', '^(CSPK_0)([1-3])$', '^(CLFP_0)([1-3])$',
	'^(CRAW_1___0)([1-3])$', '^(CSPK_1___0)([1-3])$', '^(CLFP_1___0)([1-3])$']


'''
Annotation settings
'''
annotation_on = True

# Whether or not to minimize the splitter
hide_annotation = True

# Annotation filename
annotation_name = 'annotation_%s.csv'

# Annotation folder
annotation_path = 'annotations'

# Annotation label defaults
patient_labels = ['Parkinson', 'Dystonia', 'Essential Tremor', 'OCD', 'MDD', 'STN', 'GPi', 'VIM']
depth_labels = ['Spikes', 'STN', 'ZI', 'GPe', 'GPi', 'VIM', 'Thalamus', 'Putamen', 'White Matter', 'Border Cell', 'Dying', 'Artifact']
target_labels = ['STN', 'GPi', 'VIM']


'''
GUI Settings
'''

# Individual plot heights
plot_height = 200

# Units of X axis
data_x_label = 'Time'
data_x_units = 's'
data_hz = 44000

# Units of Y axis
data_y_label = 'mV'
data_gain = 20 / 38.147

# Label font
label_style = {'color': '#808080', 'font-size': '10pt'}

# Default display range 
# In ms
default_x_range = (0, 100)
# In mV
default_y_range = (-50, 50)

#Automatically apply range
auto_default_range = True

## Audio settings ##
default_spike_audio = False
 # Spike width in fraction of frequency
spike_width = 0.001
# Spike threshold in standard deviations
spike_threshold = 3 
# Show Audio progress line
show_audio_line = True


'''
Preprocessing settings
'''

# Preprocessing folder
preprocessing_path = 'preprocessed'

## Hash rate storage

# This is a flag that determines general display and use of hashes as well
preprocess_hashes = True

# Save settings
hashrates_folder = 'hashrates'
hashrates_filename = 'hashrate_%s.csv'