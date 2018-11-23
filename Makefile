all:	tikz.pdf

tikz.pdf:	tikz.tex
	pdflatex -interaction=nonstopmode tikz > /dev/null

tikz.tex:	svg2tikz.py tikz.svg
	python3 svg2tikz.py -s -d -a tikz.svg

clean:
	latexmk -c
	rm -vf *~ tikz.tex *.synctex.gz

realclean:
	rm -vf tikz.pdf

rebuild:	realclean clean all

