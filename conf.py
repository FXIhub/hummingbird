import numpy as np
import utils.reader


# Path to rawdata
#base_path = "/data/beamline"
base_path = '/asap3/flash/gpfs/bl1/2017/data/11001733/' 


# Physical constants
h = 6.62606957e-34 #[Js]
c = 299792458 #[m/s]
hc = h*c  #[Jm]
eV_to_J = 1.602e-19 #[J/eV]

# Detector
detector_type_raw = "photonPixelDetectors"
detector_key_raw  = "pnCCD"
ny=1024
nx=1024
pixel_size=7.5e-05
detector_distance = 150e-03 # 200E-03 (in the early shifts, not clear from logbook when it changed)
gap_top = 0.8e-03
gap_bottom = 3.0e-03
gap_total = gap_top + gap_bottom
center_shift = int((gap_top-gap_bottom)/pixel_size)

# Mask
Mask = utils.reader.MaskReader("/asap3/flash/gpfs/bl1/2017/data/11001733/processed/mask_v3.h5", "/data")
mask = Mask.boolean_mask
mask_center=np.ones((ny, nx), dtype=np.bool)
radius=30
cx=0
cy=0
xx,yy=np.meshgrid(np.arange(nx), np.arange(ny))
rr=(xx-nx/2)**2+(yy-ny/2)**2 >= (radius**2)
mask_center &= rr
mask_center &= mask

# Patterson
patterson_threshold = 3.
patterson_params = {
    "floor_cut" : 50.,
    "mask_smooth" : 5.,
    "darkfield_x" : 130,
    "darkfield_y" : 130,
    "darkfield_sigma" : 30.,
    "darkfield_N" : 4,
}
patterson_diameter = 150.
patterson_xgap_pix = 10
patterson_ygap_pix = 10
patterson_frame_pix = 10

# Sizing parameters
# ------
binning = 4

centerParams = {'x0'       : (512 - (nx-1)/2.)/binning,
                'y0'       : (512 + center_shift -(ny-1)/2.)/binning,
                'maxshift' : int(np.ceil(10./binning)),
                'threshold': 1,
                'blur'     : 4}

modelParams = {'wavelength': 5.3, #in nm
               'pixelsize': 75*binning, #um
               'distance': 220., #mm
               'material': 'sucrose'}

sizingParams = {'d0':20., # in nm
                'i0':1., # in mJ/um2
                'brute_evals':10}

#res = modelParams["distance"] * 1E-3* modelParams["wavelength"] * 1E-9 / ( pixelsize_native * nx_front )
#expected_diameter = 150

# Thresholds for good sizing fits
fit_error_threshold = 2.6E-3#4.0e-3
photon_error_threshold = 3000
diameter_min = 40  #[nm]
diameter_max = 90 #[nm]
