FROM filipemaia/psana:latest


ENV SIT_ROOT /reg/g/psdm
ENV PATH /reg/g/psdm/sw/dist/apt-rpm/rhel6-x86_64/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
ENV APT_CONFIG /reg/g/psdm/sw/dist/apt-rpm/rhel6-x86_64/etc/apt/apt.conf
RUN source /reg/g/psdm/etc/ana_env.sh && /reg/g/psdm/sw/releases/ana-current/arch/x86_64-rhel6-gcc44-opt/bin/easy_install pip
RUN source /reg/g/psdm/etc/ana_env.sh && /reg/g/psdm/sw/external/python/2.7.10/x86_64-rhel6-gcc44-opt/bin/pip install codecov subprocess32 pytest-cov
