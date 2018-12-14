#all:	mount-ns.pdf
all:	tikz.pdf

%.pdf:	%.tex
	pdflatex -interaction=nonstopmode $(<:%.tex=%) > /dev/null

%.tex:	%.svg | svg2tikz.py
	python3 $| -s -R -a $<

tikz.pdf:	tikz.tex
tikz.tex:	tikz.svg

mount-ns.pdf:	mount-ns.tex
mount-ns.tex:	mount-ns.svg

clean:
	-latexmk -c
	rm -vf *~ tikz.tex mount-ns.tex *.synctex.gz

realclean:
	rm -vf tikz.pdf mount-ns.pdf

rebuild:	realclean clean all
