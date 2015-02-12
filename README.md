# Hummingbird, the SPI Online Analysis Repository

This repository aims to coordinate the Single Particle Initiative effort on online analysis software.

## Contribute

If you would like to contribute just go the issues page and create a new issue
asking to be added to the team.

### Getting Started

To be able to contribute first you need a copy of the repository:

  $ git clone git@bitbucket.org:spinitiative/hummingbird.git

For help on using `git` please check [here](http://git-scm.com/doc) and
[here](https://www.atlassian.com/git/)

## Documentation

You can find documentation about the project at [spidocs.readthedocs.org](spidocs.readthedocs.org).

### Editing Documentation

The documentation is written in
[reStructuredText](http://sphinx-doc.org/rest.html), which is a simple to use and read markup language.
The documentation is automatically built and published on the website after
every commit to the `Hummingbird` repository.

There are two ways to edit documentation, online using the Bitbucket built-in
editor, or offline using your favourite text editor.

#### Online Editing

Simply click on the `Edit on Bitbucket` button at the top of the desired
[spidocs.readthedocs.org](spidocs.readthedocs.org) page. This will take you to
the Bitbucket page corresponding to the source of the page. Click on the `Edit`
button, due the changes you want, and finally commit.

#### Offline Editing

For editing the documentation on your computer you will need:

* A copy of the Hummingbird git repository
* Your favourite text editor
* `sphinx` installed: `pip install sphinx` or `sudo pip install sphinx`

Now you can simply edit existing `.rst` files, or add new ones, in the `docs` directory
inside the root of the hummingbird git repository:

	$ cd docs
	$ emacs index.rst

After you finish editing you can look at the result by doing::

  $ make html

This will create the html files inside `.build/html`, which you can open in your
browser.

If you're happy with the result you can now simply commit the changes and push.
Your changes should be automatically pushed to
[http://spidocs.readthedocs.org/](http://spidocs.readthedocs.org/) by BitBucket.

