def stage_blobmask(targetwcs=None,
                   W=None,H=None,
                   bands=None, ps=None, tims=None,
                   plots=False,
                   brickname=None,
                   version_header=None,
                   mp=None, nsigma=None,
                   survey=None, brick=None,
                   nsatur=None,
                   record_event=None,
                   blob_dilate=None,
                   **kwargs):
    from functools import reduce
    from legacypipe.detection import detection_maps, sed_matched_detection
    from scipy.ndimage.morphology import binary_dilation

    record_event and record_event('stage_blobmask: starting')
    _add_stage_version(version_header, 'BLOBMASK', 'blobmask')

    record_event and record_event('stage_blobmask: detection maps')
    detmaps, detivs, satmaps = detection_maps(tims, targetwcs, bands, mp,
                                              apodize=10, nsatur=nsatur)
    # Expand the mask around saturated pixels to avoid generating
    # peaks at the edge of the mask.
    saturated_pix = [binary_dilation(satmap > 0, iterations=4) for satmap in satmaps]

    # SED-matched detections
    record_event and record_event('stage_blobmask: SED-matched')
    debug('Running source detection at', nsigma, 'sigma')
    SEDs = survey.sed_matched_filters(bands)

    H,W = detmaps[0].shape
    hot = np.zeros((H,W), bool)

    for sedname,sed in SEDs:
        sedhot = sed_matched_detection(
            sedname, sed, detmaps, detivs, bands, None, None, None,
            nsigma=nsigma, blob_dilate=blob_dilate, hotmap_only=True)
        if sedhot is None:
            continue
        hot |= sedhot

    hot = merge_hot_satur(hot, saturated_pix)

    # # Remap to -1 / 0
    # blob = np.empty(hot.shape, np.int16)
    # blob[:,:] = -1
    # blob[hot] = 0

    hdr = copy_header_with_wcs(version_header, targetwcs)
    hdr.add_record(dict(name='IMTYPE', value='blobmask',
                        comment='LegacySurveys image type'))
    with survey.write_output('blobmask', brick=brickname,
                             shape=hot.shape) as out:
        out.fits.write(hot, header=hdr)
    # del blob

    keys = ['hot', 'saturated_pix', 'version_header', ]
    L = locals()
    rtn = dict([(k,L[k]) for k in keys])
    return rtn
