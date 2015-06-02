import numpy

def slacH5ToCheetah(slacArr):
    out_arr = numpy.zeros((8*185, 4*388))
    for c in range(4):
        for r in range(8):
            slacPos = r + c*8
            (rB, rE) = (r*185, (r+1)*185)
            (cB, cE) = (c*388, (c+1)*388)
            out_arr[rB:rE, cB:cE] = (slacArr[slacPos])
    return out_arr


def cheetahToSlacH5(cheetahArr):
    out_arr = numpy.zeros((32, 185, 388))
    for c in range(4):
        for r in range(8):
            slacPos = r + c*8
            (rB, rE) = (r*185, (r+1)*185)
            (cB, cE) = (c*388, (c+1)*388)
            out_arr[slacPos] = cheetahArr[rB:rE, cB:cE]
    return out_arr

def assembleImage(x, y, img=None, nx=None, ny=None, dtype=None, return_indices=False):
    x -= x.min()
    y -= y.min()
    shape = (y.max() - y.min() + 1, x.max() - x.min() + 1)  
    (height, width) = shape
    if (nx is not None) and (nx > shape[1]):
        width = nx
    if (ny is not None) and (ny > shape[0]):
        height = ny 
    assembled = numpy.zeros((height,width))
    if return_indices:
        return assembled, height, width, shape, y, x
    assembled[height-shape[0]:height, :shape[1]][y,x] = img
    if dtype is not None:
        assembled = assembled.astype(getattr(numpy, dtype))
    return assembled

