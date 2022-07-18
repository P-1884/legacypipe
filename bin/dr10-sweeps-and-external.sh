#!/bin/bash -l
#SBATCH -q regular
#SBATCH -N 1
#SBATCH -t 04:00:00
#SBATCH -L SCRATCH,project
#SBATCH -C haswell

# ADM an all-in-one shell script for running the sweeps and external-match
# ADM files for DR9. Although you can slurm this, it also usually runs to
# ADM completion within 4 hours on an interactive node, e.g.
#   salloc -N 1 -C haswell -t 04:00:00 --qos interactive -L SCRATCH,project

# ADM the easiest way to run this is using a docker container. This can
# ADM be achieved by grabbing an interactive node and then executing, e.g.:
#   srun [args] shifter --image=docker:legacysurvey/legacypipe:DR10.0.1 ./this-script.sh

# ADM if this is true, make the list of bricks. If that was already
# ADM done, set this to False as a speed-up.
makelist=false
# ADM if this is true, don't overwrite any existing files. This
# ADM is useful for recovering faster if there's a failure.
mopup=true

# ADM you may need to change the top-level environment variables from
# -------------------------------here--------------------------------

# ADM set the data release and hence the main input directory.
dr=dr10
drdir=/global/cfs/cdirs/cosmo/work/legacysurvey/$dr

# ADM write to scratch.
droutdir=$CSCRATCH/$dr

# ADM uncomment these to pull and enter the docker/shifter environment.
# ADM this is useful if NOT parallelizing across multiple nodes using srun.
# shifterimg pull docker:legacysurvey/legacypipe:latest
# shifter --image docker:legacysurvey/legacypipe:latest bash

# ADM example set-ups for using custom code are commented out!
# ADM the UN-commented code is for the docker container.
export LEGACYPIPE_DIR=/src/legacypipe
# ADM this next line can be uncommented for, e.g., developing code.
export LEGACYPIPE_DIR=$HOME/git/legacypipe/
export PYTHONPATH=/usr/local/lib/python:/usr/local/lib/python3.6/dist-packages:$LEGACYPIPE_DIR/py

# ADM location of external-match files.
export SDSSDIR=/global/cfs/cdirs/sdss/data/sdss/

# ------------------------------to here------------------------------

# ADM a sensible number of processors on which to run.
export NUMPROC=$(($SLURM_CPUS_ON_NODE / 2))
# ADM the sweeps need more memory since we started to write three files.
export SWEEPS_NUMPROC=$(($SLURM_CPUS_ON_NODE / 10))

# ADM if the bricks and matching files are common to all surveys then
# ADM uncomment the next line and comment the subsequent for line.
for survey in ""
# ADM run once for each of the DECaLS and MzLS/BASS surveys.
#for survey in south north
do

    # ADM the file that holds general information about LS bricks.
    export BRICKSFILE=$drdir/$survey/survey-bricks.fits.gz

    # ADM set up the per-survey input and output directories.
    export INDIR=$drdir/$survey
    echo working on input directory $INDIR
    export TRACTOR_INDIR=$INDIR/tractor

    export OUTDIR=$droutdir/$survey
    echo writing to output directory $OUTDIR
    export SWEEP_OUTDIR=$OUTDIR/sweep
    export EXTERNAL_OUTDIR=$OUTDIR/external
    export TRACTOR_FILELIST=$OUTDIR/tractor_filelist

    mkdir -p $SWEEP_OUTDIR
    mkdir -p $EXTERNAL_OUTDIR

    # ADM write the bricks of interest to the output directory.
    if "$makelist"; then
        echo making new list of bricks to process
        find $TRACTOR_INDIR -name 'tractor-*.fits' > $TRACTOR_FILELIST
        echo wrote list of tractor files to $TRACTOR_FILELIST
    else
        echo makelist is $makelist: Refusing to make new list of bricks to process.
    fi

    # ADM run the sweeps. Should never have to use the --ignore option here,
    # ADM which usually means there are some discrepancies in the data model!
    echo running sweeps for the $survey on $SWEEPS_NUMPROC nodes
    if "$mopup"; then
        echo "Mopping up (won't overwrite existing sweep files)"
        time python $LEGACYPIPE_DIR/bin/generate-sweep-files.py \
             -v --numproc $SWEEPS_NUMPROC -f fits -F $TRACTOR_FILELIST --schema blocks$dr \
             --mopup -d $BRICKSFILE $TRACTOR_INDIR $SWEEP_OUTDIR
    else
        time python $LEGACYPIPE_DIR/bin/generate-sweep-files.py \
             -v --numproc $SWEEPS_NUMPROC -f fits -F $TRACTOR_FILELIST --schema blocks$dr \
             -d $BRICKSFILE $TRACTOR_INDIR $SWEEP_OUTDIR
    fi
    echo done running sweeps for the $survey

    # ADM run each of the external matches.
    echo making $EXTERNAL_OUTDIR/survey-$dr-$survey-dr7Q.fits
    time python $LEGACYPIPE_DIR/bin/match-external-catalog.py \
         -v --numproc $NUMPROC -f fits -F $TRACTOR_FILELIST \
         $SDSSDIR/dr7/dr7qso.fit.gz \
         $TRACTOR_INDIR \
         $EXTERNAL_OUTDIR/survey-$dr-$survey-dr7Q.fits --copycols SMJD PLATE FIBER RERUN
    echo done making $EXTERNAL_OUTDIR/survey-$dr-$survey-dr7Q.fits

    echo making $EXTERNAL_OUTDIR/survey-$dr-$survey-dr12Q.fits
    time python $LEGACYPIPE_DIR/bin/match-external-catalog.py \
         -v --numproc $NUMPROC -f fits -F $TRACTOR_FILELIST \
         $SDSSDIR/dr12/boss/qso/DR12Q/DR12Q.fits \
         $TRACTOR_INDIR \
         $EXTERNAL_OUTDIR/survey-$dr-$survey-dr12Q.fits --copycols MJD PLATE FIBERID RERUN_NUMBER
    echo done making $EXTERNAL_OUTDIR/survey-$dr-$survey-dr12Q.fits

    echo making $EXTERNAL_OUTDIR/survey-$dr-$survey-superset-dr12Q.fits
    time python $LEGACYPIPE_DIR/bin/match-external-catalog.py \
         -v --numproc $NUMPROC -f fits -F $TRACTOR_FILELIST \
         $SDSSDIR/dr12/boss/qso/DR12Q/Superset_DR12Q.fits \
         $TRACTOR_INDIR \
         $EXTERNAL_OUTDIR/survey-$dr-$survey-superset-dr12Q.fits --copycols MJD PLATE FIBERID
    echo done making $EXTERNAL_OUTDIR/survey-$dr-$survey-superset-dr12Q.fits

    echo making $EXTERNAL_OUTDIR/survey-$dr-$survey-specObj-dr16.fits
    time python $LEGACYPIPE_DIR/bin/match-external-catalog.py \
         -v --numproc $NUMPROC -f fits -F $TRACTOR_FILELIST \
         $SDSSDIR/dr16/sdss/spectro/redux/specObj-dr16.fits \
         $TRACTOR_INDIR \
         $EXTERNAL_OUTDIR/survey-$dr-$survey-specObj-dr16.fits --copycols MJD PLATE FIBERID RUN2D
    echo done making $EXTERNAL_OUTDIR/survey-$dr-$survey-specObj-dr16.fits

    echo making $EXTERNAL_OUTDIR/survey-$dr-$survey-dr16Q-v4.fits
    time python $LEGACYPIPE_DIR/bin/match-external-catalog.py \
         -v --numproc $NUMPROC -f fits -F $TRACTOR_FILELIST \
         $SDSSDIR/dr16/eboss/qso/DR16Q/DR16Q_v4.fits \
         $TRACTOR_INDIR \
         $EXTERNAL_OUTDIR/survey-$dr-$survey-dr16Q-v4.fits --copycols MJD PLATE FIBERID
    echo done making $EXTERNAL_OUTDIR/survey-$dr-$survey-dr16Q-v4.fits

    echo making $EXTERNAL_OUTDIR/survey-$dr-$survey-superset-dr16Q-v3.fits
    time python $LEGACYPIPE_DIR/bin/match-external-catalog.py \
         -v --numproc $NUMPROC -f fits -F $TRACTOR_FILELIST \
	 $SDSSDIR/dr16/eboss/qso/DR16Q/DR16Q_Superset_v3.fits \
         $TRACTOR_INDIR \
         $EXTERNAL_OUTDIR/survey-$dr-$survey-superset-dr16Q-v3.fits --copycols MJD PLATE FIBERID
    echo done making $EXTERNAL_OUTDIR/survey-$dr-$survey-superset-dr16Q-v3.fits
done

wait
echo done writing sweeps and externals for all surveys
