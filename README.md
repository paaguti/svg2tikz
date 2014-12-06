svg2tikz
========

Convert SVG figures to TiKZ 

Usage
-----

```
python svg2tikz <flags> infile.svg
  
  -s,--standalone:      generate a standalone document
  -o,--output <file>:   print to file (default: stdout)
  -d,--debug:           include debug messages
  -h,--help:            print help message
```

This little script converts SVG to TiKZ drawings. These can then be
converted to PDF using pdflatex (see Makefile) or TeX files that are
included into LaTEX documents (using the \input{} command)

TODO:
*  Bezier:
  * check conversion of cubic Bezier control points (2nd control point is buggy)
  * implement conversion of quadratic Bezier specs ('Q' and 'q' specs in SVG)
  
Dependencies:
*  Python 2.7
* LXML to parse the SVG files
