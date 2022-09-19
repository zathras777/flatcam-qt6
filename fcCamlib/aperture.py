############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
############################################################


import re

from numpy import cos, pi, sin
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon
from shapely.geometry import box as shply_box
from shapely.ops import unary_union

from .utils import setup_log


log = setup_log("fcCamlib.aprture")


class ApertureMacro:
    """
    Syntax of aperture macros.

    <AM command>:           AM<Aperture macro name>*<Macro content>
    <Macro content>:        {{<Variable definition>*}{<Primitive>*}}
    <Variable definition>:  $K=<Arithmetic expression>
    <Primitive>:            <Primitive code>,<Modifier>{,<Modifier>}|<Comment>
    <Modifier>:             $M|< Arithmetic expression>
    <Comment>:              0 <Text>
    """

    ## Regular expressions
    am1_re = re.compile(r'^%AM([^\*]+)\*(.+)?(%)?$')
    am2_re = re.compile(r'(.*)%$')
    amcomm_re = re.compile(r'^0(.*)')
    amprim_re = re.compile(r'^[1-9].*')
    amvar_re = re.compile(r'^\$([0-9a-zA-z]+)=(.*)')

    def __init__(self, name=None):
        self.name = name
        self.raw = ""

        ## These below are recomputed for every aperture
        ## definition, in other words, are temporary variables.
        self.primitives = []
        self.locvars = {}
        self.geometry = None

    def to_dict(self):
        """
        Returns the object in a serializable form. Only the name and
        raw are required.

        :return: Dictionary representing the object. JSON ready.
        :rtype: dict
        """

        return {
            'name': self.name,
            'raw': self.raw
        }

    def from_dict(self, d):
        """
        Populates the object from a serial representation created
        with ``self.to_dict()``.

        :param d: Serial representation of an ApertureMacro object.
        :return: None
        """
        for attr in ['name', 'raw']:
            setattr(self, attr, d[attr])

    def parse_content(self):
        """
        Creates numerical lists for all primitives in the aperture
        macro (in ``self.raw``) by replacing all variables by their
        values iteratively and evaluating expressions. Results
        are stored in ``self.primitives``.

        :return: None
        """
        # Cleanup
        self.raw = self.raw.replace('\n', '').replace('\r', '').strip(" *")
        self.primitives = []

        # Separate parts
        parts = self.raw.split('*')

        #### Every part in the macro ####
        for part in parts:
            ### Comments. Ignored.
            match = ApertureMacro.amcomm_re.search(part)
            if match:
                continue

            ### Variables
            # These are variables defined locally inside the macro. They can be
            # numerical constant or defind in terms of previously define
            # variables, which can be defined locally or in an aperture
            # definition. All replacements ocurr here.
            match = ApertureMacro.amvar_re.search(part)
            if match:
                var = match.group(1)
                val = match.group(2)

                # Replace variables in value
                for v in self.locvars:
                    val = re.sub(r'\$'+str(v)+r'(?![0-9a-zA-Z])', str(self.locvars[v]), val)

                # Make all others 0
                val = re.sub(r'\$[0-9a-zA-Z](?![0-9a-zA-Z])', "0", val)

                # Change x with *
                val = re.sub(r'[xX]', "*", val)

                # Eval() and store.
                self.locvars[var] = eval(val)
                continue

            ### Primitives
            # Each is an array. The first identifies the primitive, while the
            # rest depend on the primitive. All are strings representing a
            # number and may contain variable definition. The values of these
            # variables are defined in an aperture definition.
            match = ApertureMacro.amprim_re.search(part)
            if match:
                ## Replace all variables
                for v in self.locvars:
                    part = re.sub(r'\$' + str(v) + r'(?![0-9a-zA-Z])', str(self.locvars[v]), part)

                # Make all others 0
                part = re.sub(r'\$[0-9a-zA-Z](?![0-9a-zA-Z])', "0", part)

                # Change x with *
                part = re.sub(r'[xX]', "*", part)

                ## Store
                elements = part.split(",")
                self.primitives.append([eval(x) for x in elements])
                continue

            log.warning("Unknown syntax of aperture macro part: %s" % str(part))

    def append(self, data):
        """
        Appends a string to the raw macro.

        :param data: Part of the macro.
        :type data: str
        :return: None
        """
        self.raw += data

    @staticmethod
    def default2zero(n, mods):
        """
        Pads the ``mods`` list with zeros resulting in an
        list of length n.

        :param n: Length of the resulting list.
        :type n: int
        :param mods: List to be padded.
        :type mods: list
        :return: Zero-padded list.
        :rtype: list
        """
        x = [0.0] * n
        na = len(mods)
        x[0:na] = mods
        return x

    @staticmethod
    def make_circle(mods):
        """

        :param mods: (Exposure 0/1, Diameter >=0, X-coord, Y-coord)
        :return:
        """

        pol, dia, x, y = ApertureMacro.default2zero(4, mods)

        return {"pol": int(pol), "geometry": Point(x, y).buffer(dia/2)}

    @staticmethod
    def make_vectorline(mods):
        """

        :param mods: (Exposure 0/1, Line width >= 0, X-start, Y-start, X-end, Y-end,
            rotation angle around origin in degrees)
        :return:
        """
        pol, width, xs, ys, xe, ye, angle = ApertureMacro.default2zero(7, mods)

        line = LineString([(xs, ys), (xe, ye)])
        box = line.buffer(width/2, cap_style=2)
        box_rotated = affinity.rotate(box, angle, origin=(0, 0))

        return {"pol": int(pol), "geometry": box_rotated}

    @staticmethod
    def make_centerline(mods):
        """

        :param mods: (Exposure 0/1, width >=0, height >=0, x-center, y-center,
            rotation angle around origin in degrees)
        :return:
        """

        pol, width, height, x, y, angle = ApertureMacro.default2zero(6, mods)

        box = shply_box(x-width/2, y-height/2, x+width/2, y+height/2)
        box_rotated = affinity.rotate(box, angle, origin=(0, 0))

        return {"pol": int(pol), "geometry": box_rotated}

    @staticmethod
    def make_lowerleftline(mods):
        """

        :param mods: (exposure 0/1, width >=0, height >=0, x-lowerleft, y-lowerleft,
            rotation angle around origin in degrees)
        :return:
        """

        pol, width, height, x, y, angle = ApertureMacro.default2zero(6, mods)

        box = shply_box(x, y, x+width, y+height)
        box_rotated = affinity.rotate(box, angle, origin=(0, 0))

        return {"pol": int(pol), "geometry": box_rotated}

    @staticmethod
    def make_outline(mods):
        """

        :param mods:
        :return:
        """

        pol = mods[0]
        n = mods[1]
        points = [(0, 0)]*(n+1)

        for i in range(n+1):
            points[i] = mods[2*i + 2:2*i + 4]

        angle = mods[2*n + 4]

        poly = Polygon(points)
        poly_rotated = affinity.rotate(poly, angle, origin=(0, 0))

        return {"pol": int(pol), "geometry": poly_rotated}

    @staticmethod
    def make_polygon(mods):
        """
        Note: Specs indicate that rotation is only allowed if the center
        (x, y) == (0, 0). I will tolerate breaking this rule.

        :param mods: (exposure 0/1, n_verts 3<=n<=12, x-center, y-center,
            diameter of circumscribed circle >=0, rotation angle around origin)
        :return:
        """

        pol, nverts, x, y, dia, angle = ApertureMacro.default2zero(6, mods)
        points = [(0, 0)]*nverts

        for i in range(nverts):
            points[i] = (x + 0.5 * dia * cos(2*pi * i/nverts),
                         y + 0.5 * dia * sin(2*pi * i/nverts))

        poly = Polygon(points)
        poly_rotated = affinity.rotate(poly, angle, origin=(0, 0))

        return {"pol": int(pol), "geometry": poly_rotated}

    @staticmethod
    def make_moire(mods):
        """
        Note: Specs indicate that rotation is only allowed if the center
        (x, y) == (0, 0). I will tolerate breaking this rule.

        :param mods: (x-center, y-center, outer_dia_outer_ring, ring thickness,
            gap, max_rings, crosshair_thickness, crosshair_len, rotation
            angle around origin in degrees)
        :return:
        """

        x, y, dia, thickness, gap, nrings, cross_th, cross_len, angle = ApertureMacro.default2zero(9, mods)

        r = dia/2 - thickness/2
        result = Point((x, y)).buffer(r).exterior.buffer(thickness/2.0)
        ring = Point((x, y)).buffer(r).exterior.buffer(thickness/2.0)  # Need a copy!

        i = 1  # Number of rings created so far

        ## If the ring does not have an interior it means that it is
        ## a disk. Then stop.
        while len(ring.interiors) > 0 and i < nrings:
            r -= thickness + gap
            if r <= 0:
                break
            ring = Point((x, y)).buffer(r).exterior.buffer(thickness/2.0)
            result = unary_union([result, ring])
            i += 1

        ## Crosshair
        hor = LineString([(x - cross_len, y), (x + cross_len, y)]).buffer(cross_th/2.0, cap_style=2)
        ver = LineString([(x, y-cross_len), (x, y + cross_len)]).buffer(cross_th/2.0, cap_style=2)
        result = unary_union([result, hor, ver])

        return {"pol": 1, "geometry": result}

    @staticmethod
    def make_thermal(mods):
        """
        Note: Specs indicate that rotation is only allowed if the center
        (x, y) == (0, 0). I will tolerate breaking this rule.

        :param mods: [x-center, y-center, diameter-outside, diameter-inside,
            gap-thickness, rotation angle around origin]
        :return:
        """

        x, y, dout, din, t, angle = ApertureMacro.default2zero(6, mods)

        ring = Point((x, y)).buffer(dout/2.0).difference(Point((x, y)).buffer(din/2.0))
        hline = LineString([(x - dout/2.0, y), (x + dout/2.0, y)]).buffer(t/2.0, cap_style=3)
        vline = LineString([(x, y - dout/2.0), (x, y + dout/2.0)]).buffer(t/2.0, cap_style=3)
        thermal = ring.difference(hline.union(vline))

        return {"pol": 1, "geometry": thermal}

    def make_geometry(self, modifiers):
        """
        Runs the macro for the given modifiers and generates
        the corresponding geometry.

        :param modifiers: Modifiers (parameters) for this macro
        :type modifiers: list
        :return: Shapely geometry
        :rtype: shapely.geometry.polygon
        """

        ## Primitive makers
        makers = {
            "1": ApertureMacro.make_circle,
            "2": ApertureMacro.make_vectorline,
            "20": ApertureMacro.make_vectorline,
            "21": ApertureMacro.make_centerline,
            "22": ApertureMacro.make_lowerleftline,
            "4": ApertureMacro.make_outline,
            "5": ApertureMacro.make_polygon,
            "6": ApertureMacro.make_moire,
            "7": ApertureMacro.make_thermal
        }

        ## Store modifiers as local variables
        modifiers = modifiers or []
        modifiers = [float(m) for m in modifiers]
        self.locvars = {}
        for i in range(0, len(modifiers)):
            self.locvars[str(i + 1)] = modifiers[i]

        ## Parse
        self.primitives = []  # Cleanup
        self.geometry = Polygon()
        self.parse_content()

        ## Make the geometry
        for primitive in self.primitives:
            # Make the primitive
            prim_geo = makers[str(int(primitive[0]))](primitive[1:])

            # Add it (according to polarity)
            # if self.geometry is None and prim_geo['pol'] == 1:
            #     self.geometry = prim_geo['geometry']
            #     continue
            if prim_geo['pol'] == 1:
                self.geometry = self.geometry.union(prim_geo['geometry'])
                continue
            if prim_geo['pol'] == 0:
                self.geometry = self.geometry.difference(prim_geo['geometry'])
                continue

        return self.geometry
