import scipy.io
# import h5py

def load_matfile(filepath):
    '''
    Load matfile
    '''
    try:
        return scipy.io.loadmat(filepath)
    except NotImplementedError:
        # Matfile version 7.3 loading, needs further testing
        # return h5py.File(filepath)
        return None