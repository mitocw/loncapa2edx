#!/usr/bin/python
#
# File:   loncapa2edx.py
# Date:   08-May-12
# Author: I. Chuang <ichuang@mit.edu>
#
# covert loncapa problem files into an MITx course.xml + problem files

from __future__ import division

import os, sys, string, re
import math
import numpy, random, scipy
import glob
import copy
import shlex	# for split keeping quoted strings intact
from lxml.html.soupparser import fromstring as fsbs	# parse with beautifulsoup
from lxml import etree


pdir_origin = 'Mechanics_Online_Problems'

pdir = [pdir_origin + x for x in ['/Physics801','/boriskor']]

psets = ['Energy','Forces','Harmonic Motion','Kinematics','Momentum']

# things to map:
# <m></m> -> mathjax
# img src
# script variable definitions (remove leading $)

#-----------------------------------------------------------------------------
# fix script (and test)

sys.path += ['mitx-8.01x/mitx/lib']

def test_script(code):
    '''
    Try exec of script.
    '''
    global_context={'random':random,
                    'numpy':numpy,
                    'math':math,
                    'scipy':scipy, 
                    'sys':sys,
                    }
    context = {}
    try:
        exec code in global_context, context
    except Exception,err:
        print "-----------------------------------------------------------------------------"
        print "Error %s in doing exec of this code:" % err
        print code
        print "-----------------------------------------------------------------------------"

def fix_script(script):
    news = ''
    news += '\nfrom __future__ import division\n'
    news += 'from loncapa import *\n'

    lists = []

    def fixlist(m):
        lists.append(m.group(1))
        return '%s=[%s]' % (m.group(1),m.group(2))

    def fixmath(m):
        fun = m.group(1)
        if hasattr(math,fun):
            return 'math.%s(' % fun
        print "SCRIPT ERROR: unknown function %s" % fun

    for k in script.split('\n'):
        if k and k[0]=='$': k = k[1:]	# get rid of leading $
        k = k.replace('&random','lc_random')	# randrange(start,stop,step)
        k = re.sub('([^_a-zA-Z])random\(','\\1lc_random(',k)	# randrange(start,stop,step)
        k = re.sub('&([a-z]+)\(',fixmath,k)	# map to math
        k = re.sub('^\@([a-z]+)\s*=\s*\((.*)\)',fixlist,k)	# lists
        # k = k.replace('&sqrt','math.sqrt')	# sqrt
        if '$' in k: k = k.replace('$',' ')	# change $ to space
        if '&' in k: k = k.replace('&',' ')	# change & to space
        # fix defined lists
        for z in lists:
            if '@'+z in k:
                k = k.replace('@%s'%z,z)
        if k and k[-1]==';': k = k[:-1]		# get rid of trailing semicolon
        news += k+'\n'			# the final rewritten line
    test_script(news)
    return news

#-----------------------------------------------------------------------------
# get image width and height

def getwh(fn):
    nfn = fn.replace('/static/Physics801',pdir[0])
    if not os.path.exists(nfn):
        print "--> OOPS, can't find file %s" % nfn
        return (0,0)
    if '.jpg' in nfn:
        cmd = "convert '%s' -print \"%%wx%%h\" /dev/null" % nfn
        ret = os.popen(cmd).read().strip().split('x')
    else:
        print "oops, not jpg: %s" % nfn
        ret = (0,0)
    return ret

#-----------------------------------------------------------------------------
# add assignment

def add_assignment(cxml,ps):
    chapter = etree.SubElement(cxml,'chapter')
    chapter.set('name','%s' % ps)
    problems = []
    for pd in pdir:
        problems += glob.glob('%s/%s/*.problem' % (pd,ps))

    if 1:
        section = etree.SubElement(chapter,'section')
        section.set('format','Homework')
        section.set('name',ps)
        section.set('Due','Dec 12-25')

        seq = etree.SubElement(section,'sequential')

    for prob in problems:
        probpre = os.path.basename(prob).replace('.problem','')

        print prob

        # read the meta file to get the title
        metafn = prob+'.meta'
        title = None
        if os.path.exists(metafn):
            metaxml = etree.fromstring('<meta>%s</meta>' % open(metafn).read())
            title = metaxml.find('title').text
        if not title:
            title = probpre
        pfn = '%s-%s' % (ps,probpre)	# xml file to create for the problem

        problem = etree.SubElement(seq,'problem')
        problem.set('type','lecture')
        problem.set('showanswer','attempted')
        problem.set('rerandomize','never')
        problem.set('name',title)
        problem.set('filename',pfn)

        # create the problems/*.xml file from the *.problem loncapa file
        pcontent = open(prob).read().replace('&','&amp;')
        pcontent = pcontent.replace('\f','')
        pcontent = pcontent.replace('/res/MIT/rayyan','/static')
        pcontent = pcontent.replace('/res/MIT/boriskor','/static/Physics801')

        # change <startouttext/>....<endouttext/> to <text>...</text>
        pcontent = re.sub("<startouttext\s*/>","<text><p>",pcontent)
        pcontent = re.sub("<endouttext\s*/>","</p></text>",pcontent)

        if(0):
            # fix problem with </foil></foilgroup></radiobuttonresponse></part> happening too soon
            # when that occurs, move it to before the next \n\n\n
    
            pcstr = ''
            mode = 'init'
            fixedfoil = nlcnt = 0
            lastk = ''
            for k in pcontent.split('\n'):
                if '</foil></foilgroup></radiobuttonresponse></part>' in k:
                    fixedfoil = 1
                    mode = 'foilgroup'
                    pcstr += k.replace('</foil></foilgroup></radiobuttonresponse></part>','')+'\n'
                    pcstr += '</foil>\n'
                    nlcnt = 0
                elif mode=='foilgroup' and k=='' and lastk=='':
                    nlcnt += 1
                    if nlcnt==2:
                        mode = 'init'
                        pcstr += '</foilgroup></radiobuttonresponse></part>\n' + k + '\n'
                else:
                    nlcnt = 0
                    pcstr += k+'\n'
            pcontent = pcstr
            if fixedfoil:
                print pcontent

        # parse into XML
        #pxml = etree.fromstring(pcontent)
        pxml = fsbs(pcontent)

        def fixfoil(elem):
            # loncapa has buggy radiobuttonresponse foils.  If a <foil> appears after the end of
            # a <foilgroup>, at the same level, then move it into that foilgroup
            if elem.tag=='textfield': elem.tag = 'textbox'
            # recurse
            last_foilgroup = None
            for k in elem:
                if k.tag=='foilgroup': last_foilgroup = k
                elif k.tag=='foil' and last_foilgroup:
                    last_foilgroup.push(copy.deepcopy(k))
                    elem.remove(k)
                else: fixfoil(k)
        #fixfoil(pxml)

        def fixall(elem,cvtmath=False,dropp=False):

            # fix script variables and script contents (heuristic)
            if elem.tag=='script':
                if not elem.get('type')=='loncapa/python':
                    elem.set('type','loncapa/python')
                    elem.text = fix_script(elem.text)

            # fix math tag (<m> -> <math>)
            if elem.tag=='m':
                elem.tag='math'
                if elem.text:
                    elem.text = re.sub('\$=$','=$',elem.text)

            # fix ID attributes
            if 'id' in elem.attrib:
                elem.attrib['loncapaid'] = elem.attrib['id']
                elem.attrib.pop('id')

            # # convert <image>...</image> into <img src=...>
            # if elem.tag=='image':
            #     elem.tag = 'img'
            #     elem.attrib['src']=elem.text
            #     elem.text=''

            # change p to span if dropp
            if elem.tag=='p' and dropp:
                elem.tag = 'span'

            # convert <math> into [mathjax]
            if cvtmath and elem.tag=='math':
                elem.tag='span'
                mathstr = re.sub('\$(.*)\$','[mathjax]\\1[/mathjax]',elem.text)
                mtag = 'mathjax'
                if not '\\displaystyle' in mathstr: mtag += 'inline'
                else: mathstr = mathstr.replace('\\displaystyle','')
                elem.text = mathstr.replace('mathjax]','%s]'%mtag)

            # convert imageresponse: get rid of foilgroup and foil
            if elem.tag=='imageresponse':
                idx = 0
                for k in elem:
                    if k.tag=='foilgroup':
                        for foil in k:
                            ii = etree.Element('imageinput')
                            fn = foil.find('image').text
                            (w,h) = getwh(fn)
                            ii.set('src',fn)
                            ii.set('width',w)
                            ii.set('height',h)
                            ii.set('rectangle',foil.find('rectangle').text)
                            elem.insert(idx,ii)
                            idx += 1
                            if foil.find('text') is not None:
                                # print "found text ",foil.find('text').text
                                elem.insert(idx,copy.deepcopy(foil.find('text')))
                                idx += 1
                        elem.remove(k)

            # check for missing img images
            if elem.tag=='img':
                imfn = elem.get('src')
                if not imfn:
                    # print "----> OOPS, bad img entry",etree.tostring(elem,pretty_print=True)
                    p = elem.getparent()
                    p.remove(elem)
                else:
                    imfn = imfn.replace('/static/','')
                    if not os.path.exists('%s/%s' % (pdir_origin,imfn)):
                        print "----> OOPS, missing image %s" % imfn

            # convert radiobuttonresponses to multiplechoiceresponse
            if elem.tag=='radiobuttonresponse':
                elem.tag = 'multiplechoiceresponse'
                elem.set('type','MultipleChoice')
                # insert a <br/> before this
                parent = elem.getparent()
                idx = parent.index(elem)
                parent.insert(idx,etree.Element('br'))
                parent.insert(idx,etree.Element('br'))

            if elem.tag=='optionresponse':
                '''
                change foilgroup below into <ul>, change <foil> into <optioninput> with option attribute, and add <li>
                '''
                cg = elem.find('foilgroup')
                if cg==None:
                    # print "error: optionresponse has %s" % [x.tag for x in elem]
                    pass
                else:
                    cg.tag = 'ul'
                    options = cg.get('options')
                    for a in cg.attrib: cg.attrib.pop(a)	# remove attributes from ul
                    for foil in cg.findall('foil'):	# change foil to optioninput 
                        foil.set('options',options)
                        c = copy.deepcopy(foil)
                        c.tag = 'optioninput'
                        c.attrib['correct'] = c.attrib['value']	# change "value" to "correct"
                        c.attrib.pop('value')
                        liem = etree.Element('li')
                        for k in c:
                            liem.append(copy.deepcopy(k))	# move contents of optioninput into li
                            c.remove(k)
                        liem.append(c)		# move optioninput into li
                        cg.replace(foil,liem)	# replace original foil with li

            if elem.tag=='foilgroup':
                elem.tag = 'choicegroup'
                parent = elem.getparent()
                if parent.get('type'):
                    elem.set('type',parent.get('type'))
                else:
                    elem.set('type','MultipleChoice')	# could also be 'TrueFalse'
            if elem.tag=='foil':
                elem.tag = 'choice'
                if 'value' in elem.attrib:
                    elem.attrib['correct'] = elem.attrib['value']
                    elem.attrib.pop('value')
                # move elements of choice into a single <span>
                span = etree.Element('span')
                for k in elem:
                    span.append(copy.deepcopy(k))
                    elem.remove(k)
                span.append(etree.Element('br'))
                elem.insert(0,span)
                # recurse and change math
                for k in elem: fixall(k,cvtmath=True,dropp=True)
                return

            # add dojs="math" to textline
            if elem.tag=='textline':
                elem.set('dojs','math')

            # fix responseparam: if a textline is inside a responseparam, then move it out
            if elem.tag=='responseparam':
                for c in elem:
                    if c.tag in ['textline','textfield']:
                        # move these up to same level as responseparam
                        newin = copy.deepcopy(c)
                        parent = elem.getparent()
                        idx = parent.index(elem)
                        parent.insert(idx+1,newin)
                        elem.remove(c)

            # recurse
            for k in elem: fixall(k,cvtmath=cvtmath,dropp=dropp)
        fixall(pxml)

        def fixall2(elem):
            # convert textfield -> textbox
            if elem.tag=='textfield': elem.tag = 'textbox'
            # recurse
            for k in elem: fixall(k)
        fixall2(pxml)

        # fix img src
        #for img in pxml.findall('img'):
        #    src = img.attrib['src']
        #    (pre,src) = src.split('/Physics801/')
        #    img.attrib['src'] = '/static/Physics801/%s' % src

        # write out problem xml
        pstr = etree.tostring(pxml,pretty_print=True)
        pstr = pstr.replace('<p/>','<br/><br/>')
        pstr = pstr.strip()
        # open('problems/%s.xml' % pfn,'w').write(pstr)
        os.popen("xmllint --format - > 'problems/%s.xml'" % pfn,'w').write(pstr)
        
        
#-----------------------------------------------------------------------------
# main

if 1:
    # start course.xml
    cxml = etree.Element('course', graceperiod="1 day 5 hours 59 minutes 59 seconds")
    #cxml.set('actual_name',mitxcn)
    #cxml.set('name',"6.002 Spring 2012")
    cxml.set('name',"8.01 Spring 2013")

    # make one chapter for each psets
    for ps in psets:
        add_assignment(cxml,ps)
        
    fp = open('course.xml','w')
    fp.write(etree.tostring(cxml,pretty_print=True))
    fp.close()


