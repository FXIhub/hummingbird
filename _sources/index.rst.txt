Hummingbird
===========

Hummingbird is a python-based software tool for monitoring and analysing Flash X-ray Imaging (FXI) experiments in real time.

Getting Hummingbird
-------------------
The easiest way to get Hummingbird is to clone it from the |git_link|.

.. |git_link| raw:: html
                    
   <a href="https://github.com/FXIhub/hummingbird" target="_blank">Github project</a>

::

    $ git clone https://github.com/FXIhub/hummingbird.git
    
More instructions can be found in the `Installation guide <installation.html>`_.

Getting started
---------------
Hummingbird is very simple to use. `Configuration <configuration.html>`_ is done using a single python configuration file. For the beginning, checkout our collection of `basic examples <basic_examples.html>`_.

Getting help
------------
`More advanced examples <advanced_examples.html>`_ and a full `API documentation <API/modules.html>`_ are available here at |hum_doc|.

.. |hum_doc| raw:: html

             <a href="http://fxihub.github.io/hummingbird" target="_self">https://fxihub.github.io/hummingbird/docs</a>

Supported facilities
--------------------
Hummingbird is intended to be used across different user facilities. It has been extensively tested at the LCLS facility, see `LCLS examples <lcls_examples.html>`_. Future releases of Hummingbird will include the European XFEL facility and more XFEL facilities.

Contribute to Hummingbird
-------------------------
Hummingbird is meant to be an open project, developed by users of Flash X-ray Imaging (FXI) using modern X-ray sources. You are welcome to `contribute <contribute.html>`_.


How to cite
-----------
Daurer, B. J., Hantke, M. F., Nettelblad, C. & Maia, F. R. N. C. (2016). J. Appl. Cryst. **49**, 1042-1047 |hum_doi|.

.. |hum_doi| raw:: html

                   <a href="http://dx.doi.org/10.1107/S1600576716005926" target="_blank">http://dx.doi.org/10.1107/S1600576716005926</a>

.. toctree::
   :maxdepth: 1

.. toctree::
   :hidden:

   installation
   getting_started
   configuration
   basic_examples
   lcls_examples
   advanced_examples
   API/modules
   contribute
