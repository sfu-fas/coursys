ALL: arch.png docker-arch.png

%.png: %.puml
	plantuml $< 
	pngquant -q 50 $@
	mv $*-fs8.png $@
	optipng -q $@
