#!/usr/bin/env python

"""Analyze the output of decals_simulations.

3216p000
"""

from __future__ import division, print_function

import matplotlib
matplotlib.use('Agg') #display backend
import os
import sys
import logging
import argparse
import numpy as np
from astropy.table import vstack, Table
#import seaborn as sns

import pdb

import matplotlib.pyplot as plt
from PIL import Image, ImageDraw

from astropy.io import fits
from astrometry.libkd.spherematch import match_radec

def main():

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                     description='DECaLS simulations.')
    parser.add_argument('-b', '--brick', type=str, default='2428p117', metavar='', 
                        help='process this brick (required input)')
    parser.add_argument('-o', '--objtype', type=str, choices=['STAR', 'ELG', 'LRG', 'BGS'], default='STAR', metavar='', 
                        help='object type (STAR, ELG, LRG, BGS)') 
    parser.add_argument('-v', '--verbose', action='store_true', 
                        help='toggle on verbose output')

    args = parser.parse_args()
    if args.brick is None:
        parser.print_help()
        sys.exit(1)

    # Set the debugging level
    if args.verbose:
        lvl = logging.DEBUG
    else:
        lvl = logging.INFO
    logging.basicConfig(format='%(message)s', level=lvl, stream=sys.stdout)
    log = logging.getLogger('__name__')

    brickname = args.brick
    objtype = args.objtype.upper()
    lobjtype = objtype.lower()
    log.info('Analyzing objtype {} on brick {}'.format(objtype, brickname))

    if 'DECALS_SIM_DIR' in os.environ:
        decals_sim_dir = os.getenv('DECALS_SIM_DIR')
    else:
        decals_sim_dir = '.'
    output_dir = os.path.join(decals_sim_dir, brickname)
    
    # Plotting preferences
    #sns.set(style='white',font_scale=1.6,palette='dark')#,font='fantasy')
    #col = sns.color_palette('dark')
    col = ['b','k','c','m','y',0.8]
        
    # Read the metadata catalog.
    metafile = os.path.join(output_dir, 'metacat-'+brickname+'-'+lobjtype+'.fits')
    log.info('Reading {}'.format(metafile))
    meta = fits.getdata(metafile, 1)

    # We need this for our histograms below
    magbinsz = 0.2
    rminmax = np.squeeze(meta['RMAG_RANGE'])
    #if meta['rmag_range'].shape == (1,2): rmin,rmax = meta['rmag_range'][0][0],meta['rmag_range'][0][1]
    #elif meta['rmag_range'].shape == (2,): rmin,rmax = meta['rmag_range'][0],meta['rmag_range'][1]
    #rminmax= np.array([rmin,rmax])
    nmagbin = long((rminmax[1]-rminmax[0])/magbinsz)
    
    # Work in chunks.
  
    bigsimcat = []
    bigtractor = []
    nchunk = np.squeeze(meta['nchunk'])
    for ichunk in range(nchunk):
        print('ichunk= ', ichunk)
        #log.info('Working on chunk {:02d}/{:02d}'.format(ichunk+1, nchunk))
        chunksuffix = '{:02d}'.format(ichunk)
        
        # Read the simulated object catalog
        simcatfile = os.path.join(output_dir, 'simcat-'+brickname+'-'+
                                  lobjtype+'-'+chunksuffix+'.fits')
        log.info('Reading {}'.format(simcatfile))
        simcat = Table(fits.getdata(simcatfile, 1))

        # Read and match to the Tractor catalog
        tractorfile = os.path.join(output_dir, 'tractor-'+brickname+'-'+
                                   lobjtype+'-'+chunksuffix+'.fits')
        log.info('Reading {}'.format(tractorfile))
        tractor = Table(fits.getdata(tractorfile, 1))

        m1, m2, d12 = match_radec(tractor['ra'], tractor['dec'],
                                  simcat['RA'], simcat['DEC'], 1.0/3600.0)
        missing = np.delete(np.arange(len(simcat)), m2, axis=0)

        #good = np.where((np.abs(tractor['decam_flux'][m1,2]/simcat['rflux'][m2]-1)<0.3)*1)
        #print("tractor['decam_flux'].shape=",tractor['decam_flux'].shape)
        print(ichunk, len(simcat), len(tractor), len(m1), len(m2))

        # Build matching catalogs for the plots below.
        if len(bigsimcat) == 0:
            bigsimcat = simcat[m2]
            bigtractor = tractor[m1]
        else:
            bigsimcat = vstack((bigsimcat, simcat[m2]))
            bigtractor = vstack((bigtractor, tractor[m1]))

        # Get cutouts of the missing sources
        # grab the code from below
        '''        
        if len(missing) > 0:
            imfile = os.path.join(output_dir, 'qa-'+brickname+'-'+lobjtype+'-image-'+chunksuffix+'.jpg')
            hw = 30 # half-width [pixels]
            ncols = 5
            nrows = 5
            nthumb = ncols*nrows
            dims = (ncols*hw*2,nrows*hw*2)
            mosaic = Image.new('RGB',dims)

            miss = missing[np.argsort(bigsimcat['R'][missing])]
            print('miss = ',miss)
            print('missing= ',missing)
            print(bigsimcat['R'][miss])
        
            xpos, ypos = np.meshgrid(np.arange(0,dims[0],hw*2,dtype='int'),
                                 np.arange(0,dims[1],hw*2,dtype='int'))
            im = Image.open(imfile)
            sz = im.size
            iobj = 0
            for ic in range(ncols):
                for ir in range(nrows):
                    mm = miss[iobj]
                    xx = int(bigsimcat['X'][mm])
                    yy = int(sz[1]-bigsimcat['Y'][mm])
                    crop = (xx-hw,yy-hw,xx+hw,yy+hw)
                    box = (xpos[ir,ic],ypos[ir,ic])
                    thumb = im.crop(crop)
                    mosaic.paste(thumb,box)
                    iobj = iobj+1

            # Add a border
            draw = ImageDraw.Draw(mosaic)
            for ic in range(ncols):
            for ir in range(nrows):
                draw.rectangle([(xpos[ir,ic],ypos[ir,ic]),
                                (xpos[ir,ic]+hw*2,ypos[ir,ic]+hw*2)])
            qafile = os.path.join(output_dir, 'qa-'+brickname+'-'+lobjtype+'-missing.png')
            log.info('Writing {}'.format(qafile))
            mosaic.save(qafile)
            '''
        # Modify the coadd image and residual files so the simulated sources
        # are labeled.
        # grab the code from below

    # Flux residuals vs r-band magnitude

    fig, ax = plt.subplots(3, sharex=True, figsize=(6,8))

    rmag = bigsimcat['R']
    for thisax, thiscolor, band, indx in zip(ax, col, ('G', 'R', 'Z'), (1, 2, 4)):
        simflux = bigsimcat[band+'FLUX']
        tractorflux = bigtractor['decam_flux'][:, indx]
        thisax.scatter(rmag, -2.5*np.log10(tractorflux/simflux),
                       color=thiscolor, s=10)
      
        thisax.set_ylim(-0.7,0.7)
        thisax.set_xlim(rminmax+[-0.1,0.0])
        thisax.axhline(y=0.0,lw=2,ls='solid',color='gray')
        
    
        thisax.text(0.05,0.05, band.lower(), horizontalalignment='left',
                    verticalalignment='bottom',transform=thisax.transAxes,
                    fontsize=16)
        
    ax[1].set_ylabel(r'$\Delta$m (Tractor minus Input)')
    ax[2].set_xlabel('Input r magnitude (AB mag)')

    fig.subplots_adjust(left=0.18,hspace=0.1)
    qafile = os.path.join(output_dir, 'qa-'+brickname+'-'+lobjtype+'-flux.png')
    log.info('Writing {}'.format(qafile))
    plt.savefig(qafile)
    
    # Color residuals
    gr_tra = -2.5*np.log10(bigtractor['decam_flux'][:, 1]/bigtractor['decam_flux'][:, 2])
    rz_tra = -2.5*np.log10(bigtractor['decam_flux'][:, 2]/bigtractor['decam_flux'][:, 4])
    gr_sim = -2.5*np.log10(bigsimcat['GFLUX']/bigsimcat['RFLUX'])
    rz_sim = -2.5*np.log10(bigsimcat['RFLUX']/bigsimcat['ZFLUX'])

    fig, ax = plt.subplots(2,sharex=True,figsize=(6,8))
    
    ax[0].scatter(rmag, gr_tra-gr_sim, color=col[0], s=10)
    ax[1].scatter(rmag, rz_tra-rz_sim, color=col[1], s=10)
    
    [thisax.set_ylim(-0.7,0.7) for thisax in ax]
    [thisax.set_xlim(rminmax+[-0.1,0.0]) for thisax in ax]
    [thisax.axhline(y=0.0, lw=2, ls='solid', color='gray') for thisax in ax]
    
    ax[0].set_ylabel('$\Delta$(g - r) (Tractor minus Input)')
    ax[1].set_ylabel('$\Delta$(r - z) (Tractor minus Input)')
    ax[1].set_xlabel('Input r magnitude (AB mag)')
    fig.subplots_adjust(left=0.18,hspace=0.1)

    qafile = os.path.join(output_dir, 'qa-'+brickname+'-'+lobjtype+'-color.png')
    log.info('Writing {}'.format(qafile))
    plt.savefig(qafile)

    # Fraction of matching sources
    rmaghist, magbins = np.histogram(bigsimcat['R'],bins=nmagbin,range=rminmax)
    cmagbins = (magbins[:-1] + magbins[1:]) / 2.0
    ymatch, binsmatch = np.histogram(bigsimcat['R'],bins=nmagbin,range=rminmax)
    #ymatchgood, binsgood = np.histogram(bigsimcat['R'][good],bins=nmagbin,range=rminmax)

    fig, ax = plt.subplots(1,figsize=(8,6))
    ax.step(cmagbins,1.0*ymatch/rmaghist,lw=3,alpha=0.5,label='All objects')
    #ax.step(cmagbins,1.0*ymatchgood/rmaghist,lw=3,ls='dashed',label='|$\Delta$m|<0.3')
    ax.axhline(y=1.0,lw=2,ls='dashed',color='gray')
    ax.set_xlabel('Input r magnitude (AB mag)')
    ax.set_ylabel('Fraction of Matching '+objtype+'s')
    ax.set_ylim([0.0,1.1])
    ax.legend(loc='lower left')
    fig.subplots_adjust(bottom=0.15)
    qafile = os.path.join(output_dir, 'qa-'+brickname+'-'+lobjtype+'-frac.png')
    log.info('Writing {}'.format(qafile))
    plt.savefig(qafile)

    # Distribution of object types
    fig = plt.figure(figsize=(8,6))
    ax = fig.gca()
    rmaghist, magbins = np.histogram(bigsimcat['R'],bins=nmagbin,range=rminmax)
    cmagbins = (magbins[:-1] + magbins[1:]) / 2.0
    tractortype = tractor['TYPE']#.strip()
    for otype in ['PSF', 'SIMP', 'EXP', 'DEV', 'COMP']:
        these = np.where(tractortype==otype)[0]
        if len(these)>0:
            yobj, binsobj = np.histogram(bigsimcat['R'][these],bins=nmagbin,range=rminmax)
            #plt.step(cmagbins,1.0*yobj,lw=3,alpha=0.5,label=otype)
            plt.step(cmagbins,1.0*yobj/rmaghist,lw=3,alpha=0.5,label=otype)
    plt.axhline(y=1.0,lw=2,ls='dashed',color='gray')
    plt.xlabel('Input r magnitude (AB mag)')
    #plt.ylabel('Number of Objects')
    plt.ylabel('Fraction of '+objtype+'s classified')
    plt.ylim([0.0,1.1])
    plt.legend(loc='center left',bbox_to_anchor=(0.08,0.5))
    fig.subplots_adjust(bottom=0.15)

    qafile = os.path.join(output_dir, 'qa-'+brickname+'-'+lobjtype+'-type.png')
    log.info('Writing {}'.format(qafile))
    plt.savefig(qafile)

    sys.exit(1)
    #pdb.trace()




    # Get cutouts of the missing sources - only if have missing sources
         
    # Modify the coadd image and residual files so the simulated sources
    # are labeled.
    rad = 15
    imfile = os.path.join(output_dir, 'qa-'+brickname+'-'+lobjtype+'-image-'+chunksuffix+'.jpg')
    imfile = [imfile, imfile.replace('-image','-resid')]
    imfile[0].encode('ascii', 'ignore').decode()

    for ifile in imfile:
        im = Image.open(ifile)
        print('ifile=',ifile)
        sz = im.size
        draw = ImageDraw.Draw(im)
        [draw.ellipse((cat['X']-rad, sz[1]-cat['Y']-rad,cat['X']+rad,
                       sz[1]-cat['Y']+rad)) for cat in bigsimcat]
        im.save(ifile)
    
    # Morphology plots
    if objtype=='ELG':
        fig = plt.figure(figsize=(8,4))
        plt.subplot(1,3,1)
        plt.plot(rmag,deltam,'s',markersize=3)
        plt.axhline(y=0.0,lw=2,ls='solid',color='gray')
        plt.xlim(rminmax)
        plt.xlabel('r (AB mag)')

        plt.subplot(1,3,2)
        plt.plot(bigsimcat['R50_1'],deltam,'s',markersize=3)
        plt.axhline(y=0.0,lw=2,ls='solid',color='gray')
        plt.xlabel('$r_{50}$ (arcsec)')

        plt.subplot(1,3,3)
        plt.plot(bigsimcat['BA_1'],deltam,'s',markersize=3)
        plt.axhline(y=0.0,lw=2,ls='solid',color='gray')
        plt.xlabel('b/a')
        plt.xlim([0.2,1.0])
        fig.subplots_adjust(bottom=0.18)
        qafile = os.path.join(output_dir,'qa-'+brickname+'-'+lobjtype+'-morph.png')
        log.info('Writing {}'.format(qafile))
        plt.savefig(qafile)
    
if __name__ == "__main__":
    main()
