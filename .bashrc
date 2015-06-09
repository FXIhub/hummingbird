test -f /reg/g/psdm/etc/ana_env.sh && . /reg/g/psdm/etc/ana_env.sh
export PATH=$HOME/local/bin:$PATH

export PATH=/reg/neh/home/benedikt/src/pyCXI/scripts:/reg/neh/home/benedikt/local/bin:/reg/neh/home/benedikt/src/install/bin:/reg/neh/home/benedikt/bin:/reg/neh/home/benedikt/src/cheetah/build/source/psana:${PATH}

export PYTHONPATH=/reg/neh/home/benedikt/.local/lib/python2.7/site-packages/:${PYTHONPATH}

#export C_INCLUDE_PATH=/reg/neh/home/benedikt/src/install/include:${C_INCLUDE_PATH}
#export CPLUS_INCLUDE_PATH=/reg/neh/home/benedikt/src/install/include:${CPLUS_INCLUDE_PATH}
#export LIBRARY_PATH=/reg/neh/home/benedikt/src/install/lib:${LIBRARY_PATH}
#export LD_LIBRARY_PATH=/reg/neh/home/benedikt/src/install/lib:${LD_LIBRARY_PATH}
#export PYTHONPATH=/reg/neh/home/benedikt/local/lib/python:${PYTHONPATH}

export CFLAGS="-I$HOME/local/include"    # for the C compiler  
export CXXFLAGS="-I$HOME/local/include"   # for the C++ compiler  
export LDFLAGS="-L$HOME/local/lib"        # for the linker     
export LD_LIBRARY_PATH=$HOME/local/lib:$HOME/local/lib64:$LD_LIBRARY_PATH
export C_INCLUDE_PATH=$HOME/local/include

PS1='\[\033[31;1m\]\u\[\033[0m\]@\[\033[33;1m\]\h\[\033[0m\]:\[\033[32m\]\w\[\033[0m\]\$ '

# CHEETAH #
###########
export BEAMLINE="cxi"
export EXPERIMENT="cxic9714"
export H5DIR=/reg/neh/home/benedikt/data/$BEAMLINE/$EXPERIMENT/
export XTCDIR=/reg/d/ana12/$BEAMLINE/$EXPERIMENT/xtc/
export CONFDIR=/reg/neh/home/benedikt/conf/$BEAMLINE/$EXPERIMENT/
export EDITOR="emacs -nw"

alias emacs="emacs -nw"

sit_setup /reg/neh/home/hantke/programs/hummingbird