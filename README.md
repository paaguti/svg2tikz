svg2tikz
========

Convert SVG figures to TiKZ 

Usage
-----

```
python svg2tikz <flags> infile.svg
  
  -s,--standalone:      generate a standalone document
  -o,--output <file>:   print to file (default: stdout)
  -a,--auto:            auto-generate TeX file name
  -d,--debug:           include debug messages
  -h,--help:            print help message
```

This little script converts SVG to TiKZ drawings. These can then be
converted to PDF using pdflatex (see Makefile) or TeX files that are
included into LaTEX documents (using the \input{} command)

TODO:
*  Bezier:
  * check Bezier control points (2nd control point in Cubic curves)
  * ```\draw[line width=2pt,...```
  * ```\node[rotate=<angle>] at (<x>,<y>){text}```
  * ```\node[colour] at (<x>,<y>){text}```
  
Dependencies:
*  Python 2.7
* LXML to parse the SVG files
