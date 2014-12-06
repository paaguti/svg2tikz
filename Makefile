all:	tikz.pdf

tikz.pdf:	tikz.tex
	pdflatex -interaction=nonstopmode tikz > /dev/null

tikz.tex:	svg2tikz.py tikz.svg
	python svg2tikz.py -s -o tikz.tex tikz.svg

clean:
	rm -vf *.aux *.log *~ tikz.tex

realclean:
	rm -vf tikz.pdf

rebuild:	realclean clean all

