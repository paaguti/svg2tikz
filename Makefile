all:	mount-ns.pdf

tikz.pdf:	tikz.tex
	pdflatex -interaction=nonstopmode tikz > /dev/null

tikz.tex:	svg2tikz.py tikz.svg
	python3 svg2tikz.py -s -d -a tikz.svg

mount-ns.pdf:	mount-ns.tex
	pdflatex -interaction=nonstopmode mount-ns > /dev/null

mount-ns.tex:	svg2tikz.py mount-ns.svg
	python3 svg2tikz.py -s -d -a mount-ns.svg

clean:
	latexmk -c
	rm -vf *~ tikz.tex *.synctex.gz

realclean:
	rm -vf tikz.pdf mount-ns.pdf

rebuild:	realclean clean all

