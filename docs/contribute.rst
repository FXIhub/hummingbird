How to contribute?
==================

If you would like to contribute just go the issues page and `create a
new issue <https://github.com/FXIhub/hummingbird/issues/new>`_
asking to be added to the team.

Getting Started
---------------

To be able to contribute first you need a copy of the repository. If
you have not done so already submit your rsa public key to github
under Mange/SSH keys and then clone the repository:

::

    $ git clone https://github.com/FXIhub/hummingbird.git

For help on using ``git`` please check `the official git documentation <http://git-scm.com/doc>`_
and the `Github tutorials <https://help.github.com/>`_.

Contributing algorithms
-----------------------

You can find all the analysis algorithms inside the ``src/analysis`` directory and all
plotting functions inside the ``src/plotting`` directory.

To add your own analysis algorithm to Hummingbird first check if there is
already an algorithm that already does, or could be easily extended to do what
you want. If there, then just edit the existing one and submit.

In many cases you will have to start from scratch though. Start by choosing to
what module you should add your algorithm (e.g. ``event.py``), or create a new
module if you think it does not fit in any existing one.

Most algorithms take as argument a ``Record`` (e.g. ``evt['pixel_detectors']['CCD']``) or a dictionary of ``Records``
(e.g. ``evt['pulseEnergies']``), although many also take the entire event
variable. You are free to choose, as long as you document it. 

If you want to keep some result from your algorithm to be used by subsequent
algorithms just return as a ``Record`` object and assign it to a new key of the
event variable in the conf file (e.g. ``examples/dummy/conf.py``)

There is a template for new analysis modules in ``src/analysis/template.py``.

.. note::

   Algorithms that want to keep results for further processing by other
   algorithms must be able to access the ``evt`` variable, so they must receive
   it as an argument.

Contributing to documentation
-----------------------------

You can find documentation about the project at
`spidocs.readthedocs.org <http://spidocs.readthedocs.org>`_.

Editing Documentation
~~~~~~~~~~~~~~~~~~~~~

The documentation is written in
`reStructuredText <http://sphinx-doc.org/rest.html>`_, which is a simple
to use and read markup language. The documentation is automatically
built and published on the website after every commit to the
``Hummingbird`` repository.

There are two ways to edit documentation, online using the Github
built-in editor, or offline using your favourite text editor.

Online Editing
^^^^^^^^^^^^^^

Simply click on the ``Edit on Github`` button at the top of the
desired page in
`spidocs.readthedocs.org <http://fxihub.github.io/hummingbird/docs>`_. This will
take you to the Github page corresponding to the source of the page.
Click on the ``Edit`` button, due the changes you want, and finally
commit.

Offline Editing
^^^^^^^^^^^^^^^

For editing the documentation on your computer you will need:

-  A copy of the Hummingbird git repository
-  Your favourite text editor
-  ``sphinx`` installed: ``pip install sphinx`` or
   ``sudo pip install sphinx``
-  ``sphinx_rtd_theme`` installed: ``pip install sphinx_rtd_theme`` or
   ``sudo pip install sphinx_rtd_theme``

Now you can simply edit existing ``.rst`` files, or add new ones, in the
``docs`` directory inside the root of the hummingbird git repository:

::

    $ cd docs
    $ emacs index.rst

After you finish editing you can look at the result by doing:

::

    $ make html

This will create the html files inside ``.build/html``, which you can
open in your browser.

If you're happy with the result you can now simply commit the changes
and push. Your changes should be automatically pushed to
`http://fxihub.github.io/hummingbird/docs <http://fxihub.github.io/hummingbird/docs/>`_ by
Github.
