vlott backend rewrite.

Previous version can be found on branch "legacy".

================================================================================
Setup:
================================================================================

Download source and install dependencies.
$ git clone https://github.com/cloud11665/vlott
$ cd vlott
$ pip install -r requirements.txt
$ VLOTT_USE_V1=0 ./run.py

We won't be using the legacy api proxy, since it's written in a lisp and is a
pain to setup.

Create a file `raw.txt` that contains the plaintext dump of the google groups
data (more info in the script itself).
$ ./tools/ggroup_conv.py raw.txt > versions/v2/overrides/gdata.tsv

optional: Add desired override files to "versions/v2/overrides"

================================================================================
Changelog:
================================================================================

0.1 (aa74e38a065072029cac21938304111422563ad5)
    - First "working" release
