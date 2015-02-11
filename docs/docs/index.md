# Welcome to the SPI Online Analysis Documentation Page

## Adding Documentation

To add documentation to this website you need:

* A copy of the Hummingbird git repository, with included submodules
* `mkdocs` installed: `pip install mkdocs`
* Your favourite text editor

If you're not sure if you have all submodules just run:

	$ git submodule update --init --recursive

inside the Hummingbird repository.

Now you can simply edit the files in the docs/docs directory
inside the root of the hummingbird git repository.
For example to edit this page one would do:

	$ cd docs/
	$ emacs docs/index.md

The pages are written in [Markdown](http://daringfireball.net/projects/markdown/syntax), 
which is a simple to use and read markup language.

After you finish editing you can look at a live version of the docs using:

	$ mkdocs serve

If you're happy about how it turned out you need to generate the HTML:

	$ mkdocs build

Please ignore any warnings about "stale files"
Now just commit it. Don't forget to add any possible new files.
Equally import is to commit the changes in the `spinitiative.bitbucket.org` directory.
Those are the actual HTML files that will go live.

You should now be able to see the documentation online at
[http://spinitiative.bitbucket.org](http://spinitiative.bitbucket.org)

For full documentation visit [mkdocs.org](http://mkdocs.org).
