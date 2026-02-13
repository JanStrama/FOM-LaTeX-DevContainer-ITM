$pdf_mode = 4; # force LuaLaTeX for PDF output
$pdflatex = 'lualatex -synctex=1 -interaction=nonstopmode %O %S';
$bibtex = 'biber %O %B';

# Clean up common aux files latexmk might leave behind
$clean_ext = 'acn acr alg aux bbl bcf blg fdb_latexmk fls glg glo gls glsdefs ist lof log lot nlo nls out run.xml synctex.gz toc';
