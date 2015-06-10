test -f /reg/g/psdm/etc/ana_env.sh && . /reg/g/psdm/etc/ana_env.sh
export PATH=/reg/neh/home/benedikt/local/bin:$PATH
export PATH=/reg/neh/home/benedikt/src/pyCXI/scripts:/reg/neh/home/benedikt/local/bin:/reg/neh/home/benedikt/src/install/bin:/reg/neh/home/benedikt/bin:/reg/neh/home/benedikt/src/cheetah/build/source/psana:${PATH}

export PYTHONPATH=/reg/neh/home/benedikt/.local/lib/python2.7/site-packages/:${PYTHONPATH}

export CFLAGS="-I$HOME/local/include"    # for the C compiler  
export CXXFLAGS="-I$HOME/local/include"   # for the C++ compiler  
export LDFLAGS="-L$HOME/local/lib"        # for the linker     
export LD_LIBRARY_PATH=/reg/neh/home/benedikt/local/lib:/reg/neh/home/benedikt/local/lib64:$LD_LIBRARY_PATH
export C_INCLUDE_PATH=/reg/neh/home/benedikt/local/include

PS1='\[\033[31;1m\]\u\[\033[0m\]@\[\033[33;1m\]\h\[\033[0m\]:\[\033[32m\]\w\[\033[0m\]\$ '

alias emacs="emacs -nw"

export EDITOR=emacs
