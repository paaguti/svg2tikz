DEBUG=-d

all:	tikz.pdf

%.pdf:	%.tex
	latexmk -pdf -interaction=nonstopmode $(patsubst %.pdf,%,$@)

tikz.tex:	tikz.svg svg2tikz.py
	python3 svg2tikz.py -o $@ -s $(DEBUG) $< 

kk.tex:	i2rs-arch.svg svg2tikz.py
	python3 svg2tikz.py -o $@ -s $(DEBUG) $< 

multi:	test-multi.pdf

test-multi.pdf:	test-multi.tex mount-ns.tex

mount-ns.tex:	mount-ns.svg svg2tikz.py
	python3 svg2tikz.py --multi -a $(DEBUG) $<

devel:
	python3 path.py 2> /dev/null
clean:
	latexmk -c
	rm -vf *~ kk.tex

realclean:
	latexmk -C
	rm -vf kk.pdf mount-ns.tex tikz.tex

rebuild:	realclean clean all

