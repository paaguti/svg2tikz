#!/usr/bin/env python
""" A program to generate TiKZ code from simple SVGs 
(c) 2014 by Pedro A. Aranda Gutierrez; paaguti@hotmail.com
"""
from __future__ import print_function
from lxml import etree
import sys
import re

class TiKZMaker(object):
    _output     = None
    _unit       = "mm"
    _standalone = True
    _debug      = False

    align     = re.compile(r"text-align:([^;]+);")
    ffamily   = re.compile(r"font-family:([^;]+);")
    fsize     = re.compile(r"font-size:(\d+(\.\d+)?)px;")
    translate = re.compile(r"translate\((-?\d+(\.\d+)?),(-?\d+(\.\d+)?)\)")
    stroke    = re.compile(r"stroke:#(none|[0-9a-f]{6});")
    fill      = re.compile(r"fill:#(none|[0-9a-f]{6});")

    def __init__(self, output=sys.stdout, standalone = False,debug=False,unit="mm"):
        self._output     = output
        self._unit       = unit
        self._standalone = standalone
        self._debug      = debug
        
    def pt2str(self,x,y,sep=','):
        return "(%.1f%s%s%.1f%s)" % (x,self._unit,sep,y,self._unit)

    def u2str(self,x):
        return "(%.1f%s)" % (x,self._unit)
    
    def addNS(self,tag,defNS="{http://www.w3.org/2000/svg}"):
        return defNS+tag

    def get_loc(self,elem):
        # print (elem.tag,elem.attrib)
        x = float(elem.attrib['x'])
        y = float(elem.attrib['y'])
        return x,y

    def get_dim(self,elem):
        # print (elem.tag,elem.attrib)
        w = float(elem.attrib['width'])
        h = float(elem.attrib['height'])
        return w,h

    def hex2rgb(self,colour):
        r = int("0x"+colour[0:2],0)
        g = int("0x"+colour[2:4],0)
        b = int("0x"+colour[4:],0)
        return r,g,b

    def style2colour(self,style):
        print ("style2colour(%s)" % style,file=sys.stderr)
        result = []
        m = TiKZMaker.stroke.findall(style)
        # print ("m = %s" % m,file=sys.stderr)
        try:
            colour=m[0]
            if colour == "none":
                result.append("draw=none")
            else:
                print ("\\definecolor{dc}{RGB}{%d,%d,%d}" % self.hex2rgb(colour),file=self._output)
                result.append("draw=dc")
        except: pass
        m = TiKZMaker.fill.findall(style)
        try:
            colour=m[0]
            if colour == "none":
                result.append("fill=none")
            else:
                # print ("m = %s" % colour,file=sys.stderr)
                print ("\\definecolor{fc}{RGB}{%d,%d,%d}" % self.hex2rgb(colour),file=self._output)
                result.append("fill=fc")
        except: pass
        if len(result) == 0: return ""
        return "[%s]" % ",".join(result)

    def process_rect(self,elem):
        x,y   = self.get_loc(elem)
        w,h   = self.get_dim(elem)
        style = self.style2colour(elem.attrib['style'])
        print ("\\draw %s %s rectangle %s ;" % (style,self.pt2str(x,y),self.pt2str(w+x,h+y)),
               file=self._output)

    def process_circle(self,elem):
        x    = float(elem.attrib['cx'])
        y    = float(elem.attrib['cy'])
        r    = float(elem.attrib['r'])
        style = elem.attrib['style']
        print ("\\draw %s circle %s ;" % (self.pt2str(x,y),self.u2str(r)),
               file=self._output)

    def process_ellipse(self,elem):
        x    = float(elem.attrib['cx'])
        y    = float(elem.attrib['cy'])
        rx   = float(elem.attrib['rx'])
        ry   = float(elem.attrib['ry'])
        style = elem.attrib['style']
        print ("\\draw %s ellipse %s ;" % (self.pt2str(x,y),self.pt2str(rx,ry,' and ')),
               file=self._output)

    dimRe  = re.compile(r"(-?\d+(\.\d+)?),(-?\d+(\.\d+)?)(\s+(\S.*))?")

    def dimChop(self,s):
        m=TiKZMaker.dimRe.match(s)
        x=float(m.group(1))
        y=float(m.group(3))
        return self.pt2str(x,y),m.group(6)

    pathRe = re.compile(r"(([cClLmM] )?(-?\d+(\.\d+)?),(-?\d+(\.\d+)?))(\s+(\S.*))?")

    def path_chop(self,d,first,incremental):
        # print (d,file=sys.stderr)
        if d == 'z':
            print ("-- cycle;",file=self._output)
            return None, False, False            
        m = TiKZMaker.pathRe.match(d)
        # print (m,file=sys.stderr)
        # print (m.groups(),file=sys.stderr)
        spec = m.group(2)
        x = float(m.group(3))
        y = float(m.group(5))
        pt = self.pt2str(x,y)
        
        if spec is not None:
            incremental = spec[0] != spec[0].upper()
        inc = "++" if incremental else ""
            
        rest = m.group(8)
        if spec == "C " or spec == "c ":
            pt2,rest = self.dimChop(rest)
            pt3,rest = self.dimChop(rest)
            print (".. controls %s%s and %s%s .. %s%s" % (inc,pt,inc,pt2,inc,pt3),file=self._output)
        elif spec == "M " or spec == "m ":
            if first is False: print(";",file=self._output)
            print("\\draw %s%s" % (inc,pt),file=self._output)
        elif spec == "L " or spec == "l " or spec is None:
            print ("-- %s%s" % (inc,pt),file=self._output)
        return rest,False,incremental
    
    def process_path(self,elem):
        d = elem.attrib['d']
        f = True
        i = False
        while d is not None and len(d) > 0:
            d,f,i = self.path_chop(d,f,i)
        print (";",file=self._output)

    def get_align(self,style):
        m = TiKZMaker.align.findall(style)
        try:
            al = {'start':'left','center':'center','end':'right' }[m[0]]
        except:
            al = "center"
        if al != "center":
            print ("""** Warning: ignored string alignment to the %s""" % al,file=sys.stderr)
            print ("%%%% This element will be anyhow centered!",file=self._output)
        return "align=%s" % al

    def get_font(self,style):

        fnames = {
            "serif" :      "",
            "Serif" :      "",
            "sans-serif" : "\\sffamily",
            "Sans" :       "\\sffamily",
        }
    
        result = []
        size = 0.0
        fn = None
        try:
            ssize,_ = TiKZMaker.fsize.findall(style)[0]
            size = float(ssize)
            if size <= 4.0 : result.append("\\small")
            elif size <= 6.0: pass
            else: result.append("\\large")
        except: pass
        try:
            fn = TiKZMaker.ffamily.findall(style)[0]
            if fn in fnames:
                if len(fnames[fn]):
                    result.append(fnames[fn])
        except: pass
        if self._debug:
            print (">> %s" % style,file=sys.stderr)
            print ("** Font %s %.1f => %s" % (fn,size,result),file=sys.stderr)
        return "font=%s" % "".join(result) if len(result) != 0 else None

    def process_text(self,elem):
        x,y   = self.get_loc(elem)
        txt   = elem.text
        style = elem.attrib['style']
        if txt is None:
            tspan = elem.find(self.addNS('tspan'))
            if tspan is not None:  # Take everything from the <tspan>
                txt = tspan.text
                try:
                    x,y = self.get_loc(tspan)
                except: pass
                if 'style' in tspan.attrib:
                    style=tspan.attrib['style']            
        styles = [self.get_align(style)]
        f = self.get_font(style)
        if f is not None: styles.append(f)
        print ("\\node [%s] at %s { %s };" % (",".join(styles),self.pt2str(x,y),txt),
               file=self._output)

    def process_g(self,elem):
        if len([c for c in elem]) == 0: return
        xlate = {
            'g':       lambda e: self.process_g(e),
            'text':    lambda e: self.process_text(e),
            'rect':    lambda e: self.process_rect(e),
            'circle':  lambda e: self.process_circle(e),
            'ellipse': lambda e: self.process_ellipse(e),
            'path':    lambda e: self.process_path(e)
        }
        # print ("process_g(%s)" % elem.tag,file=sys.stderr)
        # print (" %d children" % len([c for c in elem]))
        transform = None
        dx = 0.0
        dy = 0.0
        try:
            transform = elem.attrib["transform"]
            sdx,_,sdy,_ = TiKZMaker.translate.findall(transform)[0]
            dx = float(sdx)
            dy = float(sdy)
            transform = "shift={%s}" % self.pt2str(x,y)
        except:
            transform = None
        if transform is not None:
            print ("\\begin{scope}[%s]" % transform,file=self._output)
        for child in elem:
            for x in xlate:
                if self.addNS(x) == child.tag:
                    xlate[x](child)
        if transform is not None:
            print ("\\end{scope}",file=self._output)

    def mkTikz(self,svg):
        if self._standalone:
            print ("""\\documentclass{standalone}
\\usepackage{tikz}
\\usetikzlibrary{shapes}
\\makeatletter
\\begin{document}""",file=self._output)

        print ("\\begin{tikzpicture}",file=self._output)
        print ("\\begin{scope}[yscale=-1]",file=self._output)
        for elem in svg.getroot():
            if elem.tag == self.addNS('g'):
                self.process_g(elem)
        print ("\\end{scope}",file=self._output)
        print ("\\end{tikzpicture}",file=self._output)
        if self._standalone:
            print ("\\end{document}",file=self._output)

def main():
    import optparse
    parser = optparse.OptionParser(description=__doc__,
                                   usage="%prog [flags] file...}")
    parser.add_option("-d","--debug",      dest="debug",      
                      action = "store_true", default=False, 
                      help="Enable debugging messages")
    parser.add_option("-o","--output",     dest="output",
                      default=None,  
                      help="Write to file(default is stdout)")
    parser.add_option("-s","--standalone", dest="standalone", 
                      action = "store_true", default=False, 
                      help="Make a standalone LaTEX file")
    
    options, remainder = parser.parse_args()
    processor = TiKZMaker(sys.stdout if options.output is None else open(options.output,"w"),
                          options.standalone)
    processor.mkTikz(etree.parse(remainder[0]))
    
if __name__ == "__main__":
   main()
