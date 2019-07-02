all:	kk.pdf

%.pdf:	%.tex
	latexmk -pdf -interaction=nonstopmode $(patsubst %.pdf,%,$@) > /dev/null

kk.tex:	i2rs-arch.svg svg2tikz.py
	python svg2tikz.py -o $@ -s -d $< 

multi:	test-multi.pdf

test-multi.pdf:	test-multi.tex mount-ns.tex

mount-ns.tex:	mount-ns.svg svg2tikz.py
	python3 svg2tikz.py --multi -a $<

clean:
	latexmk -C
	rm -vf *~ kk.tex

realclean:
	rm -vf kk.pdf

rebuild:	realclean clean all

