.. SPI Online Analysis documentation master file, created by
   sphinx-quickstart on Thu Feb 12 12:18:01 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to SPI Online Analysis's documentation!
===============================================

If you want to quickly edit this documentation you can simply click on the ``Edit on BitBucket`` button on the top of the page.

Alternatively ff you want to edit the documentation on your computer you need:

* A copy of the Hummingbird git repository
* Your favourite text editor
* ``sphinx`` installed: ``pip install sphinx``

Now you can simply edit existing ``.rst`` files, or add new ones, in the ``docs`` directory
inside the root of the hummingbird git repository::

  $ cd docs
  $ emacs index.rst

The pages are written in `reStructuredText <http://sphinx-doc.org/rest.html>`_, 
which is a simple to use and read markup language.

After you finish editing you can look at the result by doing::

  $ make html

This will create the html files inside ``.build/html``, which you can open in your
browser.

If you're happy with the result you can now simply commit the changes and push.
Your changes should be automatically pushed to
http://spidocs.readthedocs.org/ by BitBucket.


.. toctree::
   :maxdepth: 2

