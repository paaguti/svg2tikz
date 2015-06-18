#!/usr/bin/env python
""" A program to generate TiKZ code from simple SVGs 
"""
# (c) 2014 by Pedro A. Aranda Gutierrez; paaguti@hotmail.com
# released under LGPL 3.0
# see LICENSE

from __future__ import print_function
from lxml import etree
import sys
import re
import codecs
import math

class TiKZMaker(object):
    _output     = None
    _unit       = "mm"
    _standalone = True
    _debug      = False

    align     = re.compile(r"text-align:([^;]+);")
    ffamily   = re.compile(r"font-family:([^;]+);")
    fsize     = re.compile(r"font-size:(\d+(\.\d+)?)px;")
    stroke    = re.compile(r"stroke:(none|#[0-9a-f]{6});")
    stwidth   = re.compile(r"stroke-width:(\d+\.\d+);")
    fill      = re.compile(r"fill:(none|#[0-9a-f]{6});")

    def __init__(self, output=sys.stdout, standalone = False,debug=False,unit="mm"):
        self._output     = output
        self._unit       = unit
        self._standalone = standalone
        self._debug      = debug
        if self._debug: print ("Debugging!",file=sys.stderr)
        
        
    def str2u(self,s):
        f = float(s) if not isinstance(s,float) else s
        return "%.2f%s" % (f,self._unit)

    def u2str(self,x=None):
        assert x is not None
        return "(%s)" % self.str2u(x)

    def pt2str(self,x=None,y=None,sep=','):
        assert x is not None and y is not None
        return "(%s%s%s)" % (self.str2u(x),sep,self.str2u(y))
    
    def addNS(self,tag,defNS="{http://www.w3.org/2000/svg}"):
        return defNS+tag
        
    def sodipodi(self,tag):
        return self.addNS(tag,defNS='{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}')
        
    namedTagRe = re.compile(r"\{[^}]+\}(.*)")

    def delNS(self,tag):
        # if self._debug:
        #     print ("Full tag : '%s'" % tag,file=sys.stderr)
        m = TiKZMaker.namedTagRe.match(tag)
        # if self._debug:
        #     print (m.groups(),file=sys.stderr)
        return m.group(1)

    def circle_center(self,x1,y1,r):
        """Using the algebraic solution: we have one line passing throgh the origin and (x1,y1)
We are looking for two points that are equidistant from the origin and (x1,y1). These are on a line
that is orthogonal to the first one and passes through (x1/2, y1/2).

Throws exception when no solutions are found, else returns the two points.

@param:  x1,y1 : second point for the circular arc
@param:  r     : radius of the circular arc

@returns: [(xa,ya),(xb,yb)] : the two centers for the arcs
@throws Exception if no center is found"""
        l1 = math.pow(r,2.0) - math.pow(0.5 * x1,2.0) - math.pow(0.5 * y1,2.0)
        l2 = math.pow(x1,2.0) + math.pow(y1,2.0)
        l = math.sqrt(l1/l2)
        xa = 0.5*x1 - l * y1
        ya = 0.5*y1 + l * x1
        xb = 0.5*x1 + l * y1
        yb = 0.5*y1 - l * x1
        return [(xa,ya),(xb,yb)]

    def svg_circle_arc(self,x1,y1,r):
        """Get the specs for the arc as (centre_x,centre_y,alpha,beta,radius) """
        res = []
        for pt in self.circle_center(x1,y1,r):
            alpha = math.degrees(math.atan2(-1.0 * y1, -1.0 * x1))
            beta  = math.degrees(math.atan2(y1-pt[1], x1 - pt[0]))
            res.append((pt[0],pt[1],alpha,beta,r))
            # print (res,file=sys.stderr)
        return res
    
    def svg_ellipse_arc(self,x1,y1,rx,ry):
        mu = ry/rx
        res = []
        for arc in self.svg_circle_arc(x1*mu,y1,ry):
            res.append((arc[0]/mu,arc[1],arc[2],arc[3],rx,ry))
            # print (res,file=sys.stderr)
        return res
    
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
        if self._debug: print ('hex2rgb(%s)' % colour,file=sys.stderr)
        r = int("0x"+colour[1:3],0)
        g = int("0x"+colour[3:5],0)
        b = int("0x"+colour[5:],0)
        return r,g,b

    def hex2colour(self,colour):
        if self._debug:
            print ("hex2colour(%s) = " % colour,end="",file=sys.stderr)
        result = None
        d = {'none'   : 'none', 
             '#000000' : 'black',
             '#ff0000' : 'red',
             '#00ff00' : 'green',
             '#0000ff' : 'blue',
             '#ffff00' : 'yellow',
             '#ffffff' : 'white' } 
        try :
            result = d[colour]
        except: pass
        if self._debug:
            print (result,file=sys.stderr)
        return result

    def style2colour(self,style):
        if self._debug: print ("style2colour(%s)" % style,file=sys.stderr)
        result = []
        m = TiKZMaker.stroke.findall(style)
        try:
            colour=m[0]
            if self._debug: print ("stroke = %s" % colour,file=sys.stderr)
            hc = self.hex2colour(colour)
            if hc is not None:
                if hc != 'black': result.append("draw=%s" % hc)
            else:
                print ("\\definecolor{dc}{RGB}{%d,%d,%d}" % self.hex2rgb(colour),file=self._output)
                result.append("draw=dc")
        except: pass
        m = TiKZMaker.stwidth.findall(style)
        try:
            swidth = float(m[0])
            if self._debug:
                print ("stroke-width=%.3f" % swidth,file=sys.stderr)
            result.append("line width=%.3f%s" % (swidth,self._unit))
        except: pass
        m = TiKZMaker.fill.findall(style)
        if self._debug: print ("fill = %s" % m,file=sys.stderr)
        try:
            colour=m[0]
            hc = self.hex2colour(colour)
            if hc is not None:
                result.append("fill=%s" % hc)
            else:
                print ("\\definecolor{fc}{RGB}{%d,%d,%d}" % self.hex2rgb(colour),file=self._output)
                result.append("fill=fc")
        except: pass
        if len(result) == 0: return ""
        return "[%s]" % ",".join(result)

    def process_rect(self,elem):
        x,y   = self.get_loc(elem)
        w,h   = self.get_dim(elem)
        try:
            style = self.style2colour(elem.attrib['style'])
        except:
            style = ""
        print ("\\draw %s %s rectangle %s ;" % (style,self.pt2str(x,y),self.pt2str(w+x,h+y)),
               file=self._output)

    def process_circle(self,elem):
        x    = float(elem.get('cx'))
        y    = float(elem.get('cy'))
        r    = float(elem.get('r'))
        try:
            style = self.style2colour(elem.attrib['style'])
        except:
            style = ""
        print ("\\draw %s %s circle %s ;" % (style,self.pt2str(x,y),self.u2str(r)),
               file=self._output)

    def process_ellipse(self,elem):
        x    = float(elem.get('cx'))
        y    = float(elem.get('cy'))
        rx   = float(elem.get('rx'))
        ry   = float(elem.get('ry'))
        # style = elem.attrib['style']
        try:
            style = self.style2colour(elem.attrib['style'])
        except:
            style = ""
        print ("\\draw %s %s ellipse %s ;" % (style,self.pt2str(x,y),self.pt2str(rx,ry,' and ')),
               file=self._output)

    dimRe  = re.compile(r"(-?\d+(\.\d+)?)[, ](-?\d+(\.\d+)?)(\s+(\S.*))?")
    def dimChop(self,s):
        m=TiKZMaker.dimRe.match(s)
        x=float(m.group(1))
        y=float(m.group(3))
        return self.pt2str(x,y),m.group(6),x,y

    intRe = re.compile (r"(-?\d+)(\s+(\S.*))?")
    def intChop(self,s):
        m = TiKZMaker.intRe.match(s)
        return m.group(1),m.group(3),int(m.group(1))
    
    numRe = re.compile (r"(-?\d+(\.\d+)?)(\s+(\S.*))?")
    def numChop(self,s):
        m = TiKZMaker.numRe.match(s)
        return m.group(1),m.group(4),float(m.group(1))
        
    pathRe = re.compile(r"(([aAcCqQlLmM] )?(-?\d+(\.\d+)?),(-?\d+(\.\d+)?))(\s+(\S.*))?")

    # path_chop
    # @param:
    #  d:           path descriptor (string)
    #  first:       whether this is the first element or not
    #  last_spec:   last operation specification
    #  incremental: whether we are in incremental mode or not
    #  style:       style to use
    # @return
    #  rest:        path description after processing
    #  first:       should be False
    #  spec:        spec for next operation
    #  incremental: whether next operation will be incremental
    
    def path_chop(self,d,first,last_spec,incremental,style):

        def path_controls(inc,p1,p2,p3):
            print (".. controls %s%s and %s%s .. %s%s" % (inc,p1,inc,p2,inc,p3),
                   file=self._output)

        def path_arc(inc,arc,lge,comment=False):
            x,y,alpha,beta,rx,ry = arc
            print ("%s%s%s arc (%5.1f:%5.1f:%s and %s)" %
                   ("%% " if comment else "",
                    inc, 
                    self.pt2str(x,y),
                    alpha if lge else beta,
                    beta  if lge else alpha,
                    self.str2u(rx),self.str2u(rx)),file=self._output)


        if self._debug:
            print ("[%s] -->> %s" % (last_spec,d),file=sys.stderr)
        if d[0].upper() == 'Z':
            print ("-- cycle",file=self._output)
            return None, False, last_spec, incremental            
        m = TiKZMaker.pathRe.match(d)
        # print (m,file=sys.stderr)
        if m is None:
            print ("'%s' does not have aAcCqQlLmM element" % d,file=sys.stderr)
            return None, False, last_spec, incremental
        spec = m.group(2)
        x1 = float(m.group(3))
        y1 = float(m.group(5))
        pt = self.pt2str(x1,y1)
        if self._debug:
            print (" -- [%s] >> %s" % (spec,m.group(1)),file=sys.stderr)
        
        # spec=last_spec[0] if spec is None else spec[0]
        if spec is None and last_spec is not None:
            if last_spec[0].upper() == 'M':
                spec = 'L' if last_spec[0] == 'M' else 'l'
            else:
                spec = last_spec

        if spec is not None:
            spec = spec[0]
            incremental = spec != spec.upper()
        inc = "++" if incremental else ""
            
        rest = m.group(8)
        ## print (" --]]>> [%s|%s]" % (spec,rest),file=sys.stderr)

        if spec in ["L","l"] or spec is None:
            print ("-- %s%s" % (inc,pt),file=self._output)
        elif spec in [ "M","m"]:
            if not first: print(";",file=self._output)
            print("\\draw %s %s%s" % (style,inc,pt),file=self._output)
        elif spec in ["c", "C"]:
            pt2,rest,x2,y2 = self.dimChop(rest)
            pt3,rest,x3,y3 = self.dimChop(rest)
            #
            # Quick hack
            #
            # %.. controls ++(4.2mm,4.2mm) and ++(12.6mm,-4.2mm) .. ++(16.9mm,0.0mm)
            # Correct
            # .. controls ++(4.2mm,4.2mm) and ++(-4.2mm,-4.2mm) .. ++(16.8mm,0.0mm)
            if incremental:
                pt2 = self.pt2str(x2-x3,y2-y3)
            else:
                if self._debug: print ("** Warning: check controls",file=sys.stderr)
                print ("%%%% Warning: check controls",file=self._output)
            path_controls (inc,pt,pt2,pt3)
        elif spec in ["Q","q"]:
            if self._debug: print (">> Decoding quadratic Bezier curve",file=sys.stderr)
            pt2,rest,x2,y2 = self.dimChop(rest)
            if spec == "Q":
                print ("%% Warning: ignoring (abs) Quadratic Bezier",file=sys.stderr)
                print ("%% This should be a quadratic Bezier with control point at %s" % pt,file=self._output)
                print (" -- %s" % (pt2),file=self._output)
            else:
                #
                # See http://www.latex-community.org/forum/viewtopic.php?t=4424&f=45
                # And above
                #
                # Q3 = P2
                # Q2 = (2*P1+P2)/3 [ -P2 ^see above^]
                # Q1 = 
                pt3 = pt2
                pt2 = self.pt2str(2.0*(x1-x2)/3.0,2.0*(y1-y2)/3)
                pt1 = self.pt2str(2.0*x1/3.0,      2.0*y1/3)
                path_controls(inc,pt1,pt2,pt3)
        elif spec in ["A","a"]:
            #
            # First 'point' were rx and ry
            #
            _,rest,xrot  = self.intChop(rest)
            _,rest,large = self.intChop(rest)
            _,rest,swap  = self.intChop(rest)
            pt2,rest,_x,_y    = self.dimChop(rest) # this is the second point
            _large =  large == 0
            _swap =   swap  == 1
            try:
                arcs = self.svg_ellipse_arc(_x,_y,x1,y1)
                if self._debug: print("arcs: ",arcs,file=sys.stderr)
                path_arc(inc,arcs[0 if _swap else 1],_large,False)
                path_arc(inc,arcs[1 if _swap else 0],_large,True)
                
            except Exception,e:
                print ("ERROR: <%s> Couldn't process spec: %c %6.1f,%6.1f %d %d %d %6.1f,%6.1f" %
                       (e, spec, x1, y1, _xrot, _large, _swap, _x, _y), file=sys.stderr)
                print ("%%%% ERROR: Couldn't process spec: %c %6.1f,%6.1f %d %d %d %d %6.1f,%6.1f" %
                       (spec, x1,y1,_xrot,_large,_swap,_x,_y), file=self._output)
        else:
            print ("Warning: didn't process '%s' in path" % spec,file=sys.stderr)
        return rest,False,spec,incremental
    
    def process_path(self,elem):
        d = elem.attrib['d']
        pid = elem.attrib['id']
        f = True 
        i = False
        print ("%% path id='%s'" % pid,file=self._output)
        print ("%% path spec='%s'" % d,file=self._output)
        try:
            style = self.style2colour(elem.attrib['style'])
        except:
            style = ""
        spec = None
        try:
            # print ("Trying to see if we have an arc",file=sys.stderr)
            # print ("Lookinf for a '%s'" % self.sodipodi('type'),file=sys.stderr)
            # print ("In: ",elem.attrib,file=sys.stderr)
            
            if elem.get(self.sodipodi('type')) == 'arc':
                if self._debug: print ("So we have an arc!",file=sys.stderr)
                
                rx    = float(elem.get(self.sodipodi('rx')))
                ry    = float(elem.get(self.sodipodi('ry')))
                cx    = float(elem.get(self.sodipodi('cx')))
                cy    = float(elem.get(self.sodipodi('cy')))
                start = float(elem.get(self.sodipodi('start')))
                end   = float(elem.get(self.sodipodi('end')))

                x1 = cx + rx * math.cos(start)
                y1 = cy + ry * math.sin(start)
                
                print ("\\draw%s %s arc (%.2f:%.2f:%s and %s);" % 
                        (style, self.pt2str(x1,y1),math.degrees(start),math.degrees(end),
                        self.str2u(rx),self.str2u(ry)),file=self._output)
                if self._debug:
                    print ("\\draw%s %s arc (%.2f:%.2f:%s and %s);" % 
                        (style, self.pt2str(x1,y1),math.degrees(start),math.degrees(end),
                        self.str2u(rx),self.str2u(ry)),file=sys.stderr)

                return
        except Exception,e: 
            print ("Exception %s" % e,file=sys.stderr)
            pass
        while d is not None and len(d) > 0:
            ## print (self.path_chop(d,f,spec,i,style),file=sys.stderr)
            
            d,f,spec,i = self.path_chop(d,f,spec,i,style)
        print (";",file=self._output)

    def get_align(self,style):
        m = TiKZMaker.align.findall(style)
        try:
            al = {'start':'left','center':'center','end':'right' }[m[0]]
        except:
            al = "center"
        if al != "center":
            print ("** Warning: ignored string alignment to the %s" % al,file=sys.stderr)
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

    def process_tspan(self,elem,x,y,style):
        txt = elem.text
        try:
            x,y = self.get_loc(elem)
        except: pass
        try:
            style=elem.attrib['style']            
        except: pass
        styles = [self.get_align(style)]
        f = self.get_font(style)
        if f is not None: styles.append(f)
        print ("\\node [%s] at %s { %s };" % (",".join(styles),self.pt2str(x,y),txt),
               file=self._output)
        
    def process_text(self,elem):
        x,y   = self.get_loc(elem)
        txt   = elem.text
        style = elem.attrib['style']
        if txt is None:
            for tspan in elem.findall(self.addNS('tspan')):
                self.process_tspan(tspan,x,y,style)
        else:
            self.process_tspan(elem,x,y,style)

    transformRe = re.compile(r"(translate|rotate|matrix)\(([^)]+)\)")
    floatRe     = re.compile(r"(-?\d+(\.\d+([eE]-?\d+)?)?)")

    def transform2scope(self,elem):
        try:
            transform = elem.attrib['transform']
            if self._debug: 
                print ("transform2scope(%s)" % transform,file=sys.stderr)
            m = TiKZMaker.transformRe.match(transform)
            if self._debug: 
                print (m.groups(),file=sys.stderr)
            getFloats = TiKZMaker.floatRe.findall(m.group(2)) 
            if self._debug:
                print (getFloats,file=sys.stderr)
            nums = [ n for n,d,e in getFloats ]
            operation = m.group(1)
            if self._debug:
                print (operation,nums,file=sys.stderr)
            xform = []

            if operation == "translate":
                xform.append("shift={(%s,%s)}" % (self.str2u(nums[0]),self.str2u(nums[1])))
            elif operation == "rotate":
                if len(nums) == 1:
                    xform.append("rotate=%s" % nums[0])
                else:
                    xform.append("rotate around={%s:(%s,%s)}" % (nums[0],self.str2u(nums[1]),self.str2u(nums[2])))
            elif operation == "matrix":
                xform.append("cm={%s,%s,%s,%s,(%s,%s)}" % (nums[0],nums[1],nums[2],nums[3],
                                                           self.str2u(nums[4]),self.str2u(nums[5])))
            if len(xform) > 0:
                print ("\\begin{scope}[%s]" % ",".join(xform),file=self._output)
                return True
            return False
        except:
            return False

            
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
        for child in elem:
            tag = self.delNS(child.tag)
            for x in xlate:
                if tag == x:
                    transform = self.transform2scope(child)
                    xlate[x](child)
                    if transform: print ("\\end{scope}",file=self._output)
                    break
            else:
                print ("WARNING: <%s ../> not processed" % tag,file=sys.stderr)

    def mkStandaloneTikz(self,svg):
        print ("""\\documentclass[tikz,border=1mm]{standalone}
\\usepackage{tikz}
\\usetikzlibrary{shapes}
\\usepackage[utf8]{inputenc}
\\makeatletter
\\begin{document}""",file=self._output)
        self.mkTikz(svg)
        print ("\\end{document}",file=self._output)

    def mkTikz(self,svg):
        units = self._unit
        print ("\\begin{tikzpicture}[yscale=-1]",file=self._output)
        if self._debug:
            print (svg.getroot().attrib,file=sys.stderr)
        for elem in svg.getroot():
            if self.delNS(elem.tag) == 'g':
                if len([c for c in elem]) > 0:
                    transform=self.transform2scope(elem)
                    self.process_g(elem)
                    if transform: print ("\\end{scope}",file=self._output)
            elif self.delNS(elem.tag) == "namedview":
                try:
                    self._unit = elem.attrib["units"]
                except: 
                    self._unit = units

        print ("\\end{tikzpicture}",file=self._output)
        # self._unit = units

def main():
    import optparse
    parser = optparse.OptionParser(description=__doc__,
                                   usage="%prog [flags] file...")
    parser.add_option("-d","--debug",      dest="debug",      
                      action = "store_true", default=False, 
                      help="Enable debugging messages")
    parser.add_option("-a","--auto",      dest="auto",      
                      action = "store_true", default=False, 
                      help="Create output name from source")
    parser.add_option("-o","--output",     dest="output",
                      default=None,  
                      help="Write to file(default is stdout)")
    parser.add_option("-s","--standalone", dest="standalone", 
                      action = "store_true", default=False, 
                      help="Make a standalone LaTEX file")
    
    options, remainder = parser.parse_args()
    if options.auto:
        import os
        options.output = os.path.splitext(remainder[0])[0] + ".tex"
        print (" %s --> %s " % (remainder[0],options.output),file=sys.stderr)

    processor = TiKZMaker(sys.stdout if options.output is None else codecs.open(options.output,"w","utf-8"),
                          debug=options.debug)
    try:
        if options.standalone:
            processor.mkStandaloneTikz(etree.parse(remainder[0]))
        else:
            processor.mkTikz(etree.parse(remainder[0]))
            
    except IndexError:
        parser.print_help()

if __name__ == "__main__":
    main()
