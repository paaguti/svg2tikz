#!/usr/bin/env python3
""" A program to generate TiKZ code from inkscape-generated SVGs
Future plans include generalising to SVG without depending on Inkscape
"""
# (c) 2014 by Pedro A. Aranda Gutierrez; paaguti@hotmail.com
# released under LGPL 3.0
# see LICENSE


from lxml import etree
import sys
import re
import codecs
import math
import argparse

class TiKZMaker(object):
    _output     = None
    _unit       = 'mm'
    _standalone = True
    _symbols    = None
    _nsmap      = None
    _verbose    = 1
    _dpi        = 72
    _round      = False
    _decimals   = 1

    # Keep track of where the point is and where the path started
    _lastx      = 0
    _startx     = 0
    _lasty      = 0
    _starty     = 0

    floatSpec = r'(-?\d+(\.\d+)?([eE]-?\d+)?)'
    tailSpec  = r'(\s+(\S.*))?'


    def __init__(self, output=sys.stdout, standalone=False, debug=1, unit='mm', dpi=72, round=False, multi=False):
        self._output     = output
        self._unit       = unit
        self._standalone = standalone
        self._verbose    = debug
        self._dpi        = dpi
        self._round      = round
        self._multi      = multi

        self.log('Debugging!',verbose=2)

    def log(self, msg, verbose=1, end=None):
        if verbose <= self._verbose:
            print (msg,end=end,file=sys.stderr)

    @staticmethod
    def output(colordef,strmsg,file=sys.stdout):
        if len(colordef) > 0:
            print (colordef,file=file)
        print (strmsg,file=file)

    str2uRe   = re.compile(floatSpec+r'([a-z]{2})?')

    # str2u return a floating with the units
    # s: a float or a string
    # do_round: set to False to suppress rounding
    def str2u(self,s, do_round=True):
        #f = float(s) if not isinstance(s,float) else s
        self.log ('str2u({})'.format(repr(s)),verbose=2)
        if isinstance(s,float):
            f = s
            u = self._unit
        elif isinstance(s,int):
            f = float(s)
            u = self._unit
        else:
            fall = TiKZMaker.str2uRe.findall(s)
            self.log('str2uRe.findall({}) -> {}'.format(s,repr(fall[0])),verbose=3)
            e = fall[0]
            n,_,_,u = e
            f = float(n)
            if u == 'px':
                f *= 25.4/72.0
                u = 'mm'
            else:
                if u == '':
                    u = self._unit
        decs = self._decimals
        if self._round and do_round:
            decs=0
        return '%.1f%s' % (round(f,decs), u)

    def pt2str(self,x=None,y=None,sep=','):
        assert x is not None and y is not None
        return '(%s%s%s)' % (self.str2u(x),sep,self.str2u(y))

    namedTagRe = re.compile(r'({([^}]+)})(.*)')
    @classmethod
    def delNS(cls,tag):
        m = cls.namedTagRe.match(tag)
        self.log ("delNS: tag='{}' --> {}".format(tag,repr(m.groups())),verbose=2)
        return m.group(3)

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
        # x = float(elem.attrib['x'])
        # y = float(elem.attrib['y'])
        return float(elem.xpath('string(.//@x)')),float(elem.xpath('string(.//@y)'))

    def get_dim(self,elem):
        # print (elem.tag,elem.attrib)
        # w = float(elem.attrib['width'])
        # h = float(elem.attrib['height'])
        return float(elem.xpath('string(.//@width)')),float(elem.xpath('string(.//@height)'))

    def hex2rgb(self,colour):
        self.log('hex2rgb(%s)' % colour,verbose=2)
        if colour.lower() == 'none': return 'none'
        r = int('0x'+colour[1:3],0)
        g = int('0x'+colour[3:5],0)
        b = int('0x'+colour[5:],0)
        return '{RGB}{%d,%d,%d}' % (r,g,b)

    rgbSpecRe = re.compile('rgb\((\d+%?),(\d+%?),(\d+%?)\)')
    def rgb2colour(self,colour):
        m = rgbSpecRe.match(colour)
        if m is None: return colour, None
        r = int(m.group(1)[:-1]) * 255 if m.group(1).endswith('%') else int(m.group(1))
        g = int(m.group(2)[:-1]) * 255 if m.group(2).endswith('%') else int(m.group(2))
        b = int(m.group(3)[:-1]) * 255 if m.group(3).endswith('%') else int(m.group(3))
        return '#%02x%02x%02x' % (r,g,b) , '{RGB}{%d,%d,%d}' % (r,g,b)

    def hex2colour(self,colour,cname=None,cdef=None):
        self.log('hex2colour(%s) = ' % colour,end='',verbose=2)
        result = None
        col,rgb = self.rbg2colour(colour) if colour.startswith('rgb(') else colour,self.hex2rgb(colour)
        self.log ('colour %s --> %s,%s' % (colour,col,rgb),verbose=2)
        d = {'none'    : 'none',
             '#000000' : 'black',
             '#ff0000' : 'red',
             '#00ff00' : 'green',
             '#0000ff' : 'blue',
             '#ffff00' : 'yellow',
             '#00ffff' : 'cyan',
             '#ff00ff' : 'magenta',
             '#ffffff' : 'white' }
        try :
            result = d[col]
        except:
            if cname is not None:
                cdef.append('\\definecolor{%s}%s' % (cname,rgb))
                result = cname
        self.log(result,verbose=2)
        return result

    def style2colour(self,style):
        self.log('style2colour(%s)' % style,end=' = ',verbose=2)
        stdef = []
        cdef  = []
        s2cDict = {
            'stroke':       lambda c: 'draw=' + self.hex2colour(c,cname='dc',cdef=cdef),
            'fill':         lambda c: 'fill=' + self.hex2colour(c,cname='fc',cdef=cdef),
            'stroke-width': lambda c: 'line width=' + self.str2u(c, do_round=False)
        }
        for s in style.split(';'):
            m,c = s.split(':')
            self.log ("Processing '%s=%s'" % (m,c),verbose=2)
            if m in s2cDict:
                self.log("Found '%s'" % m,verbose=2)
                stdef.append(s2cDict[m](c))

        result = '[%s]' % ','.join(stdef) if len(stdef) > 0 else '', '\n'.join(cdef)
        self.log('Returns %s' % repr(result), verbose=2)
        return result

    def process_rect(self,elem):
        self.log ('***\n** rectangle\n***',verbose=2)
        x,y   = self.get_loc(elem)
        w,h   = self.get_dim(elem)
        try:
            style,cdefs = self.style2colour(elem.attrib['style'])
            self.log(f'Result: style={style}\ncdefs={cdefs}', verbose=2)
        except:
            style = ''
            cdefs = ''
        TiKZMaker.output(cdefs,
                         '\\draw %s %s rectangle %s ;' % (style,self.pt2str(x,y),self.pt2str(w+x,h+y)),
                         file=self._output)

    def process_circle(self,elem):
        x    = float(elem.get('cx'))
        y    = float(elem.get('cy'))
        r    = float(elem.get('r'))
        try:
            style,cdefs = self.style2colour(elem.attrib['style'])
        except:
            style = ''
            cdefs = ''
        TiKZMaker.output(cdefs,
                         '\\draw %s %s circle (%s) ;' % (style,self.pt2str(x,y),self.str2u(r)),
                         file=self._output)

    def process_ellipse(self,elem):
        x    = float(elem.get('cx'))
        y    = float(elem.get('cy'))
        rx   = float(elem.get('rx'))
        ry   = float(elem.get('ry'))
        # style = elem.attrib['style']
        try:
            style,cdefs = self.style2colour(elem.attrib['style'])
        except:
            style = ''
            cdefs = ''
        TiKZMaker.output(cdefs,
                         '\\draw %s %s ellipse %s ;' % (style,self.pt2str(x,y),self.pt2str(rx,ry,' and ')),
                         file=self._output)

    dimRe   = re.compile(floatSpec + r'[, ]' + floatSpec + tailSpec)
    def dimChop(self,s):
        m=TiKZMaker.dimRe.match(s)
        self.log('dimChop({}) = {}'.format(s,repr(m.groups())),verbose=2)
        x=float(m.group(1))
        y=float(m.group(4))
        return self.pt2str(x,y),m.group(8),x,y

    intRe = re.compile (r'(-?\d+)'+tailSpec)
    def intChop(self,s):
        m = TiKZMaker.intRe.match(s)
        self.log('intChop({})={}'.format(s,m.groups()),verbose=2)
        return m.group(1),m.group(3),int(m.group(1))

    numRe = re.compile (floatSpec+tailSpec)
    def numChop(self,s):
        m = TiKZMaker.numRe.match(s)
        self.log('numChop({})={}'.format(s,repr(m.groups())),verbose=2)
        return m.group(1),m.group(4),float(m.group(1))

    pathRe = re.compile(r'([aAcCqQlLmMhHvV] )?'+floatSpec+'([, ]'+floatSpec+')?([ ,]+(.*))?')

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

    def path_chop(self, d, first=True, last_spec='', incremental=True, style=None):

        def path_controls(inc,p1,p2,p3):
            print ('.. controls %s%s and %s%s .. %s%s' % (inc,p1,inc,p2,inc,p3),
                   file=self._output)

        def path_arc(inc,arc,lge,comment=False):
            x,y,alpha,beta,rx,ry = arc
            print ('%s%s%s arc (%5.1f:%5.1f:%s and %s)' %
                   ('%% ' if comment else '',
                    inc,
                    self.pt2str(x,y),
                    alpha if lge else beta,
                    beta  if lge else alpha,
                    self.str2u(rx),self.str2u(rx)),file=self._output)


        self.log (f'[{last_spec}] -->> {d}', verbose=2)
        if d[0].upper() == 'Z':
            print ('-- cycle',file=self._output)
            self._lastx = self._startx
            self._lasty = self._starty
            return None, False, last_spec, incremental
        m = TiKZMaker.pathRe.match(d)
        # self.log (m)
        if m is None:
            print (f"ERROR: '{d}' does not have aAcChHlLmMqQvV element", file=sys.stderr)
            return None, False, last_spec, incremental
        rest = m.group(10)
        spec = m.group(1)
        self.log (' -- [%s] >> %s' % (spec,m.group(1)),verbose=2)

        # spec=last_spec[0] if spec is None else spec[0]
        if spec is None and last_spec is not None:
            if last_spec[0].upper() == 'M':
                spec = 'L' if last_spec[0] == 'M' else 'l'
            else:
                spec = last_spec

        if spec is not None:
            spec = spec[0]
            incremental = spec != spec.upper()
        inc = '++' if incremental and not first else ''

        ## print (' --]]>> [%s|%s]' % (spec,rest),file=sys.stderr)

        x1,y1='0.0','0.0'
        #
        # TODO: H xx implies keeping the vertical coordinate!
        # TODO: check V xx
        #
        if spec not in ['h','H','v','V']:
            x1 = float(m.group(2))
            y1 = float(m.group(6))
        pt = self.pt2str(x1,y1)

        if spec in ['l','L'] or spec is None:
            print ('-- %s%s' % (inc,pt),file=self._output)
            if spec == 'L':
                self._lastx = x1
                self._lasty = y1
            else:
                self._lastx += x1
                self._lasty += y1
        elif spec in ['h','v']:
            x = float(m.group(2))
            if spec == 'h':
                pt = self.pt2str(x,0)
                self._lastx += x
            else:
                pt = self.pt2str(0,x)
                self._lasty += x
            print ('-- %s%s' % (inc,pt),file=self._output)
        elif spec in ['H','V']:
            dim = float(m.group(2))
            if spec == 'H':
                pt = self.pt2str(dim, self._lasty)
                self._lastx = dim
            else:
                pt = self.pt2str(self._lastx, dim)
                self._lasty = dim
            print ('-- %s%s' % (inc,pt),file=self._output)
        elif spec in [ 'M','m']:
            if not first: print(';',file=self._output)
            if spec == 'M':
                self._lastx = x1
                self._lasty = y1
            else:
                self._lastx += x1
                self._lasty += y1
            #
            # This is the point for the next 'z' or 'Z'
            self._startx = self._lastx
            self._starty = self._lasty
            print('\\draw %s %s%s' % (style,inc,pt),file=self._output)
        elif spec in ['c', 'C']:
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
                self.log ('** Warning: check controls',verbose=2)
                print ('%%%% Warning: check controls',file=self._output)
            path_controls (inc,pt,pt2,pt3)
            if spec == 'C':
                self._lastx = x3
                self._lasty = y3
            else:
                self._lastx += x3
                self._lasty += y3
        elif spec in ['Q','q']:
            self.log ('>> Decoding quadratic Bezier curve',verbose=2)
            pt2,rest,x2,y2 = self.dimChop(rest)
            if spec == 'Q':
                self._lastx = x2
                self._lasty = y2
                self.log ('%% Warning: ignoring (abs) Quadratic Bezier')
                print ('%% This should be a quadratic Bezier with control point at %s' % pt,file=self._output)
                print (' -- %s' % (pt2),file=self._output)
            else:
                self._lastx += x2
                self._lasty += y2
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
        elif spec in ['A','a']:
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
                self.log('arcs: ',arcs,verbose=2)
                path_arc(inc,arcs[0 if _swap else 1],_large,False)
                path_arc(inc,arcs[1 if _swap else 0],_large,True)

            except Exception as e:
                self.log("ERROR: <{}> Couldn't process spec: {} {:6.1f},{:6.1f} {} {} {} {:6.1f},{:6.1f}".format(e, spec, x1, y1, _xrot, _large, _swap, _x, _y))
                print ("%%%% ERROR: Couldn't process spec: {} {:6.1f},{:6.1f} {} {} {} {} {:6.1f},{:6.1f}".format(spec, x1,y1,_xrot,_large,_swap,_x,_y), file=self._output)
            if spec == 'A':
                self._lastx = _x
                self._lasty = _y
            else:
                self._lastx += _x
                self._lasty += _y
        else:
            self.log (f"Warning: didn't process '{spec}' in path")
        return rest,False,spec,incremental

    def process_use(self,elem,debug=True):
        #print("TODO: process %s" % etree.tostring(elem))
        href = None
        x = None
        y = None
        self.log(']>]>  '+elem.xpath('string(.//@href)',namespaces = self._nsmap))
        for n in elem.attrib:
            print (n)

            if re.search(r'({[^}]+})?href',n):
                if debug: print ('reference to %s' % elem.get(n))
                href = elem.get(n)
            if n == 'x': x=float(elem.get(n))
            if n == 'y': y=float(elem.get(n))
        assert href is not None, 'use does not reference a symbol' % href
        assert href[0] == '#', 'Only local hrefs allowed for symbols (%s)' % href

        try:
            print ('\\begin{scope}[shift={%s}]' % (self.pt2str(x,y)),file=self._output)
        except: pass

        for s in self._symbols:
            if href[1:] == s.get('id'):
                self.process_g(s)
                break
        else:
            self.log ("ERROR: didn't find referenced symbol '%s'" % href[1:])

        if x is not None and y is not None:
            print ('\\end{scope}',file=self._output)

    def sodipodi_arc(self,cdefs,style,elem):
        rx    = float(elem.xpath('string(.//@sodipodi:rx)' ,namespaces=self._nsmap))
        ry    = float(elem.xpath('string(.//@sodipodi:ry)' ,namespaces=self._nsmap))
        cx    = float(elem.xpath('string(.//@sodipodi:cx)' ,namespaces=self._nsmap))
        cy    = float(elem.xpath('string(.//@sodipodi:cy)' ,namespaces=self._nsmap))
        start = float(elem.xpath('string(.//@sodipodi:start)' ,namespaces=self._nsmap))
        end   = float(elem.xpath('string(.//@sodipodi:end)' ,namespaces=self._nsmap))

        if end < start: end = end + 2.0 * math.pi

        x1 = cx + rx * math.cos(start)
        y1 = cy + ry * math.sin(start)

        outstreams = [self._output,sys.stderr]
        if self._verbose == 1:
            outstreams.pop()
        for f in  outstreams:
            TiKZMaker.output(cdefs,
                             '\\draw %s %s arc (%.2f:%.2f:%s and %s);' %
                             (style, self.pt2str(x1,y1),math.degrees(start),math.degrees(end),
                              self.str2u(rx),self.str2u(ry)),
                             file=f)

    def process_path(self,elem):
        d = elem.attrib['d']
        f = True
        i = False
        try:
            pid = elem.attrib['id']
            print (f'%% path id="{pid}"', file=self._output)
        except: pass
        print (f'%% path spec="{d}"', file=self._output)
        try:
            _style = elem.attrib['style']
            self.log (f'%% From "{_style}"', verbose=2)
            style,cdefs = self.style2colour(_style)
            self.log (f'%% style= "{style}"', verbose=2)
            self.log (f'%% colour defs = "{cdefs}"', verbose=2)
        except Exception as e:
            style,cdefs = '',''

        spec = None

        _type = elem.xpath('string(.//@sodipodi:type)', namespaces=self._nsmap)
        self.log (f"sodipodi type is '{_type}'", verbose=2)
        self.log (f"style is '{style}'", verbose=2)

        sodipodi_dict = {
            'arc' : lambda e: self.sodipodi_arc(cdefs,style,e),
            # Add more sodipodi elements here
        }
        if _type in sodipodi_dict:
            try:
                sodipodi_dict[_type](elem)
                return
            except Exception as e:
                self.log (f'<*> Exception {e} processing sodipodi:{_type}')
        if len(cdefs) > 0: print (cdefs,file=self._output)
        while d is not None and len(d) > 0:
            ## print (self.path_chop(d,f,spec,i,style),file=sys.stderr)
            d,f,spec,i = self.path_chop(d,first=f,last_spec=spec,incremental=i,style=style)
            # print(f'%% point=({self._lastx:.1f},{self._lasty:.1f})', file=self._output)
        print (';',file=self._output)

    # Escape characters to make them print correctly
    escapes = {
        '&': '\\&',
        '#': '\\#',
    }
    def escape_text(self, txt):
        result = txt
        for k,v in TiKZMaker.escapes.items():
            result = result.replace(k,v)
        return result

    def process_tspan(self,txt,x,y,_id,stdict={}):
        __id__ = _id
        def dict2style(styledict={},cdefs=[]):
            def mkFont(fname):
                try:
                    return 'font=' + {
                        # 'serif' :      '',
                        # 'Serif' :      '',
                        'sans-serif' : '\\sffamily',
                        'Sans' :       '\\sffamily',
                    }[fname]
                except:
                    return 'font='

            def mkAlign(style,id=None):
                align_xlate = {
                    'start':  'anchor=west',
                    'center': 'align=center',
                    'end':    'anchor=east'
                }
                try:
                    return align_xlate[style]
                except:
                    self.log ('** Warning: ignored string alignment {}'.format(style),end='')
                    if __id__ is not None: self.log(' for element {}'.format(__id__),end='')
                    self.log ('!!')
                    return aling_xlate['center']

            pxRe = re.compile(r'(-?\d+(\.\d+(e?[+-]?\d+)))([a-z]{2})?')
            def mkFSize(style):
                try:
                    size = 0.0
                    print ('**TODO refine mkFSize(%s)' % style,verbose=2)
                    val,_,_,unit = pxRe.match(style).groups()
                    fval = float(val)
                    for _min,_max,_result in [
                            ( 0.0,  4.0, 'font=\\small'),
                            ( 4.0,  6.0, ''),
                            ( 6.0, 10.0, 'font=\\large'),
                            (10.0, 1e06, 'font=\\LARGE')
                    ]:
                        if _min <= fval and fval < _max:
                            return _result
                    return ''
                except:
                    return ''
            result = []
            xlatestyle = {'fill' :        lambda s: self.hex2colour(s,cdefs),
                          'font-family' : lambda s: mkFont(s),
                          'text-align':   lambda s: mkAlign(s),
                          'font-size' :   lambda s: mkFSize(s)
            }

            result = [xlatestyle[x](styledict[x]) for x in xlatestyle if x in styledict]
            self.log(repr(result),end=' --> ',verbose=2)
            fspec = 'font=' + ''.join([f[5:] for f in result if f.startswith('font=')])
            result = [ r for r in result if len(r)>0 and not r.startswith('font=')]
            if len(fspec) != 5: result.append(fspec)
            self.log(repr(result),verbose=2)
            # result = [r for r in result if r is not None and len(r)>0]
            return '' if len(result) == 0 else '[' + ','.join(result) + ']','\n'.join(cdefs)

        # txt = elem.text
        s,c = dict2style(stdict)
        TiKZMaker.output('\n'.join(c),'\\node %s at %s { %s };' % (s,self.pt2str(x,y),self.escape_text(txt)),
                         file=self._output)

    def process_text(self,elem):
        def style2dict(st,styledict = {}):
            for s in [_s for _s in st.split(';') if len(_s) > 0]:
                k,v = s.split(':')
                styledict[k] = v
            return styledict

        x,y   = self.get_loc(elem)
        _id   = elem.get('id')
        style = style2dict(elem.xpath('string(.//@style)',namespaces=self._nsmap))
        self.log ('text.x,y = %d,%d' % (x,y),verbose=2)
        if elem.text is None:
            for tspan in elem.xpath('.//svg:tspan',namespaces=self._nsmap):
                _style = style2dict(tspan.xpath('string(.//@style)',namespaces=self._nsmap),
                                    dict(style))
                try:
                    _x,_y   = self.get_loc(tspan)
                    self.log ('>> tspan.x,y = %d,%d' % (_x,_y),verbose=2)
                except:
                    _x,_y = x,y
                self.process_tspan(tspan.text,_x,_y,_id,_style)
                del _style
        else:
            self.log (etree.tostring(elem,pretty_print=True))
            self.process_tspan(elem.text,x,y,_id,style)
        del style

    transformRe = re.compile(r'(translate|rotate|matrix|scale)\(([^)]+)\)')
    floatRe  = re.compile(floatSpec)


    def transformTranslate(self, xform, nums):
        xform.append('shift={(%s,%s)}' %
                     (self.str2u(nums[0]),
                      self.str2u(nums[1] if len(nums)>1 else '0')))
        return xform

    def transformRotate(self, xform, nums):
        if len(nums) == 1:
            xform.append('rotate=%s' % nums[0])
        else:
            xform.append('rotate around={%s:(%s,%s)}' %
                         (nums[0],
                          self.str2u(nums[1]),
                          self.str2u(nums[2])))
        return xform

    def transformMatrix(self, xform,nums):
        xform.append('cm={%s,%s,%s,%s,(%s,%s)}' %
                     (nums[0],nums[1],nums[2],nums[3],
                      self.str2u(nums[4]),
                      self.str2u(nums[5])))
        return xform

    def transformScale(self,xform, nums):
        xform.append('xscale={}'.format(nums[0]))
        xform.append('yscale={}'.format(nums[1]))
        return xform

    def transform2scope(self,elem):
        transformProcess = {
            'translate' : lambda xform,nums: self.transformTranslate(xform, nums),
            'rotate':     lambda xform,nums: self.transformRotate(xform, nums),
            'matrix':     lambda xform,nums: self.transformMatrix(xform, nums),
            'scale':      lambda xform,nums: self.transformScale(xform, nums),
        }

        #
        # This is the way to get the right attributes!
        #
        transform = elem.attrib.get('transform')
        if transform is None: return False

        self.log ('transform2scope(%s)' % transform,verbose=2)
        m = TiKZMaker.transformRe.match(transform)
        self.log (m.groups(),verbose=2)
        getFloats = TiKZMaker.floatRe.findall(m.group(2))
        self.log (repr(getFloats),verbose=2)
        nums = [ n for n,d,e in getFloats ]
        operation = m.group(1)
        self.log ('operation:{}, nums:{}'.format(operation,repr(nums)),verbose=2)
        xform = []
        try:
            xform = transformProcess[operation](xform, nums)
        except Exception as exc:
            self.log('>>> transform2scope({}) ==> {}'.format(transform,repr(exc)))
        self.log('>>> transform2scope({}) = {}'.format(transform,repr(xform)),verbose=2)
        if len(xform) > 0:
            print ('\\begin{scope}[%s]' % ','.join(xform),file=self._output)
            return True
        return False

    namedTagRe = re.compile(r'({([^}]+)})(.*)')

    def process_g(self, elem, top=False):
        if len(elem) == 0: return

        g_id = elem.get('id')
        self.log(f'process_g: id={g_id}', verbose=2)
        print (f'%% Group {g_id} --> top={top}', file=self._output)

        g_style = elem.get('style')
        if g_style is not None:
            self.log(f'TODO: process global style "{g_style}" in group')

        xlate = {
            'g':       lambda e: self.process_g(e),
            'text':    lambda e: self.process_text(e),
            'rect':    lambda e: self.process_rect(e),
            'circle':  lambda e: self.process_circle(e),
            'ellipse': lambda e: self.process_ellipse(e),
            'path':    lambda e: self.process_path(e),
            'use':     lambda e: self.process_use(e)
        }

        # print ('process_g(%s)' % elem.tag,file=sys.stderr)
        __slide = 1
        for child in elem:
            # print (' &&& -> %s' % child.tag,file=sys.stderr)
            tag = self.namedTagRe.match(child.tag).group(3)
            if tag in xlate:
                if top and self._multi:
                    print(f'\\onslide<{__slide}->{{%', file=self._output)
                transform = self.transform2scope(child)
                xlate[tag](child)
                if transform: print ('\\end{scope}', file=self._output)
                if top and self._multi:
                    print('}', file=self._output)
                    __slide += 1
            else:
                self.log ('WARNING: <%s ../> not processed' % tag)
        if g_style is not None:
            pass # print ('\\end{scope}',file=self._output)

    def mkStandaloneTikz(self, svg, xform='yscale=-1', border='1mm'):
        print (f'''\\documentclass[tikz,border={border}]{{standalone}}
\\usepackage{{tikz}}
\\usetikzlibrary{{shapes}}
\\usepackage[utf8]{{inputenc}}
\\makeatletter
\\begin{{document}}''', file=self._output)
        self.mkTikz(svg, xform=xform)
        print ('\\end{document}', file=self._output)

    def mkTikz(self,svg,xform='yscale=-1'):

        self._nsmap = { k:v for k,v in iter(svg.getroot().nsmap.items()) if k is not None }
        self._nsmap['svg'] = 'http://www.w3.org/2000/svg'
        self.log (repr(self._nsmap),verbose=2)

        svg_groups = svg.xpath('//svg:svg/svg:g',namespaces=self._nsmap)
        if self._multi == 1 and len(svg_groups) > 1:
            self.log(f'ERROR: Trying to make multi-slide TiKZ from SVG with {len(svg_groups)} object groups!')
            self.log('       Group them into a single object group!')
            if not self._output.isatty():
                import os
                _fname = self._output.name
                self._output.close()
                os.remove(_fname)
                self.log(f'       Removing empty output file `{_fname}`')
            sys.exit(1)

        self._symbols = svg.xpath('//svg:symbol',namespaces=self._nsmap)
        self.log ('Getting symbols with XPATH',verbose=2)
        for s in self._symbols:
            self.log(etree.tostring(s),verbose=2)

        units = self._unit
        self._unit = svg.xpath('string(//svg:svg/sodipodi:namedview/@units)',namespaces=self._nsmap)
        if len(self._unit) == 0: self._unit = units

        height=None
        try:
            height = svg.getroot().xpath('string(//svg:svg/@height)',namespaces=self._nsmap)
            self.log(f' height: {height}')
        except: pass

        width=None
        try:
            width = svg.getroot().xpath('string(//svg:svg/@width)',namespaces=self._nsmap)
            self.log(f' width: {width}')
        except: pass

        print (f'\\begin{{tikzpicture}}[{xform}]', file=self._output)

        if height is not None and width is not None:
            print('\\useasboundingbox(0,0) rectangle ({},{});'.format(self.str2u(width),
                                                                      self.str2u(height)),file=self._output)

        for elem in svg_groups:
            if len(elem) > 0:
                transform = self.transform2scope(elem)
                self.process_g(elem, top=True)
                if transform: print ('\\end{scope}',file=self._output)
        print ('\\end{tikzpicture}',file=self._output)

def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter,epilog='')
    parser.add_argument('--version', action='version', version='%(prog)s 3.2 190908')
    parser.add_argument('-d','--debug',
                        dest='debug',
                        action = 'count',
                        default = 1,
                        help='Enable debugging messages (repeat for more messages)')
    parser.add_argument('-a','--auto',
                        dest='auto',
                        action = 'store_true',
                        help='Create output name from source')
    parser.add_argument('-o','--output',
                        dest='output',
                        default=None,
                        help='Write to file(default is stdout)')
    parser.add_argument('-b','--border',
                        dest='border',
                        default='1mm',
                        help='Set standalone border (default:1mm)')
    parser.add_argument('-r','--dpi',
                        dest='dpi',
                        type=int,default=72,
                        help='Resolution (assume 72dpi)')
    parser.add_argument('-R','--round',
                        dest='round',
                        action = 'store_true',
                        help='Round numbers to the nearest integer (default is 1 decimal)')
    parser.add_argument('-M','--multi',
                        dest='multi',
                        action = 'store_true',
                        help='Make a multi-slide LaTEX file')
    parser.add_argument('-s','--standalone',
                        dest='standalone',
                        action = 'store_true',
                        help='Make a standalone LaTEX file')
    parser.add_argument('-S','--scale',
                        dest='scale',
                        type=float, default=1,
                        help='Scale factor for resulting image (default=1)')
    parser.add_argument('-X','--xform',
                        dest='xform',
                        type=str, default='yscale=-1',
                        help='transformation applied to the SVG code (default: yscale=-1)')
    parser.add_argument('--code',
                        dest='code',
                        default='utf-8',
                        help='Output file coding')
    parser.add_argument('infile',metavar='INFILE', type=str, help='Input file')

    args = parser.parse_args()

    if args.auto:
        import os
        args.output = os.path.splitext(args.infile)[0]+ '.tex'

    if args.multi:
        if args.standalone:
            print('*** svg2tikz.py: cannot generate multi-slide standalone beamers', file=sys.stderr)
            raise SystemExit

    out_xform = args.xform
    if out_xform == 'yscale=-1':
        if args.scale != 1.0:
            out_xform=f'xscale={args.scale:.2f},yscale={-args.scale:.2f}'
        print(f' Using global transform {out_xform}')

    processor = TiKZMaker(sys.stdout if args.output is None else codecs.open(args.output,'w',args.code),
                          debug=args.debug,
                          dpi=args.dpi,
                          multi=args.multi,
                          round=args.round)
    processor.log (' %s --> %s ' % (args.infile,args.output))
    try:
        tree = etree.parse(args.infile)

        if args.standalone:
            processor.mkStandaloneTikz(tree, xform=out_xform, border=args.border)
        else:
            processor.mkTikz(tree, xform=out_xform)
    except IndexError:
        parser.print_help()

if __name__ == '__main__':
    main()
