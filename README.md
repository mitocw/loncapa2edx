loncapa2edx
===========

Python script to convert LON-CAPA course content to edX

This script has been used to successfully convert LON-CAPA course
content into edX format.  The main complication is to convert syntax;
while the "capa" module of edX is loosely motivated by LON-CAPA, there
are some differences in convention and in XML file syntax.  Also,
LON-CAPA is based on Perl, whereas edX is based on Python.  Thus,
embedded Perl scrips in (eg randomized) LON-CAPA problems cannot
generally be converted automatically.

See http://data.edx.org for details about the edX XML format.

The current version of the script is old, and may not be completely
compatible with the current edX system.  

See these other related projects for more information:

  - xbundle:    https://github.com/mitocw/xbundle
  - moodle2edx: https://github.com/mitocw/moodle2edx
  - latex2edx:  https://github.com/mitocw/latex2edx

