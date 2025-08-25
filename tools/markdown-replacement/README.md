The goal in this directory: investigate possible replacements for the overly-complex calls to Ruby for Github-flavoured markdown conversion to HTML.

## Notes

Hopefully a Python library that implements [the GFM spec](https://github.github.com/gfm/) and replicates the output of the github-markdown and/or commonmarker gems.

## Results

I can find no Markdown input where `pycmarkgfm` or `cmarkgfm` differ from the previously-used Ruby foreign function call (when configured as in `test.py`). That isn't much of a surprise: they are themselves foreign function calls to GitHub's library.

The cmarkgfm project (https://github.com/theacodes/cmarkgfm) seems more active: more forks, more stars, more contributors, reasonably-recent updates to mention new Python versions in compatibility list.