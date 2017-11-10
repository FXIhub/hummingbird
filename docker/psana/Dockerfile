FROM centos:6.6
## update packages and install dependencies
##    csh, tar, perl needed for cctbx
##    gcc, zlib-devel needed to build mp4ipy
##    bunch of things for psana
RUN yum --enablerepo=updates clean metadata && \
    yum upgrade -y && \
    yum install -y \
        csh \
        gcc \
        gcc-c++ \
        patch \
        perl \
        tar \
        which \
        zlib-devel && \
    yum install -y \
        alsa-lib atk compat-libf2c-34 fontconfig freetype gsl libgfortran \
        libgomp libjpeg libpng libpng-devel pango postgresql-libs unixODBC \
        libICE libSM libX11 libXext libXft libXinerama libXpm libXrender libXtst \
        libXxf86vm mesa-libGL mesa-libGLU gtk2 xorg-x11-fonts-Type1 \
        xorg-x11-fonts-base xorg-x11-fonts-100dpi xorg-x11-fonts-truetype \
        xorg-x11-fonts-75dpi xorg-x11-fonts-misc

WORKDIR /
## setup SLAC software stack
# apt-get install psdm-release-ana-0.13.18-x86_64-rhel6-gcc44-opt && \
ADD http://pswww.slac.stanford.edu/psdm-repo/dist_scripts/site-setup.sh /usr/src/
ENV SIT_ROOT /reg/g/psdm
ENV PATH /reg/g/psdm/sw/dist/apt-rpm/rhel6-x86_64/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
ENV APT_CONFIG /reg/g/psdm/sw/dist/apt-rpm/rhel6-x86_64/etc/apt/apt.conf
RUN cd /usr/src && \
    chmod a+rx /usr/src/site-setup.sh && \
    /usr/src/site-setup.sh /reg/g/psdm && \
    apt-get update && \
    apt-get install psdm-release-ana-0.15.0-x86_64-rhel6-gcc44-opt -y && \
    /reg/g/psdm/bin/relcurrent $(ls -tr /reg/g/psdm/sw/releases/ | grep -v current | tail -n 1) && \
    source /reg/g/psdm/etc/ana_env.sh && \
    echo $( echo $LD_LIBRARY_PATH | awk -F: '{print $1}' ) >> /etc/ld.so.conf && \
    ldconfig && \
    printf "export SIT_ROOT=/reg/g/psdm\n" > /etc/profile.d/00_psana_site.sh && \
    printf "#!/bin/csh -f\nsetenv SIT_ROOT /reg/g/psdm\n" > /etc/profile.d/00_psana_site.csh && \
    printf "export PATH=/reg/g/psdm/sw/dist/apt-rpm/rhel6-x86_64/bin:\$PATH\n" >> /etc/profile.d/00_psana_site.sh && \
    printf "setenv PATH /reg/g/psdm/sw/dist/apt-rpm/rhel6-x86_64/bin:\$PATH\n" >> /etc/profile.d/00_psana_site.csh && \
    printf "export APT_CONFIG=/reg/g/psdm/sw/dist/apt-rpm/rhel6-x86_64/etc/apt/apt.conf\n" >> /etc/profile.d/00_psana_site.sh && \
    printf "setenv APT_CONFIG /reg/g/psdm/sw/dist/apt-rpm/rhel6-x86_64/etc/apt/apt.conf\n" >> /etc/profile.d/00_psana_site.csh && \
    printf "source /reg/g/psdm/etc/ana_env.sh\n" >> /etc/profile.d/01_psana.sh && \
    printf "#!/bin/csh -f\nsource /reg/g/psdm/etc/ana_env.csh\n" >> /etc/profile.d/01_psana.csh
