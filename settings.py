# Core package location
core_path = ''

# Default figure height
fig_height = 200

# Default number of figures to display
nr_figs = 5

def load_params(params):
    params.fig_height = fig_height
    params.nr_figs = nr_figs

    return params
