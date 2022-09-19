############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
############################################################

import re
import sys
import traceback

from numpy import arctan2, sqrt, pi, sin, cos
from shapely import affinity
from shapely.geometry import Polygon, LineString, Point, MultiPolygon
from shapely.geometry import box as shply_box
from shapely.ops import unary_union

from .geometry import Geometry
from .utils import arc, setup_log


log = setup_log("fcCamlib.gerber")


class GerberParseError(Exception):
    pass


def arc_angle(start, stop, direction:str):
    if direction == "ccw" and stop <= start:
        stop += 2 * pi
    if direction == "cw" and stop >= start:
        stop -= 2 * pi

    return abs(stop - start)


def parse_gerber_number(strnumber, frac_digits):
    """
    Parse a single number of Gerber coordinates.

    :param strnumber: String containing a number in decimal digits
    from a coordinate data block, possibly with a leading sign.
    :type strnumber: str
    :param frac_digits: Number of digits used for the fractional
    part of the number
    :type frac_digits: int
    :return: The number in floating point.
    :rtype: float
    """
    return int(strnumber) * (10 ** (-frac_digits))


class Gerber (Geometry):
    """
    **ATTRIBUTES**

    * ``apertures`` (dict): The keys are names/identifiers of each aperture.
      The values are dictionaries key/value pairs which describe the aperture. The
      type key is always present and the rest depend on the key:

    +-----------+-----------------------------------+
    | Key       | Value                             |
    +===========+===================================+
    | type      | (str) "C", "R", "O", "P", or "AP" |
    +-----------+-----------------------------------+
    | others    | Depend on ``type``                |
    +-----------+-----------------------------------+

    * ``aperture_macros`` (dictionary): Are predefined geometrical structures
      that can be instanciated with different parameters in an aperture
      definition. See ``apertures`` above. The key is the name of the macro,
      and the macro itself, the value, is a ``Aperture_Macro`` object.

    * ``flash_geometry`` (list): List of (Shapely) geometric object resulting
      from ``flashes``. These are generated from ``flashes`` in ``do_flashes()``.

    * ``buffered_paths`` (list): List of (Shapely) polygons resulting from
      *buffering* (or thickening) the ``paths`` with the aperture. These are
      generated from ``paths`` in ``buffer_paths()``.

    **USAGE**::

        g = Gerber()
        g.parse_file(filename)
        g.create_geometry()
        do_something(s.solid_geometry)

    """

    defaults = {
        "steps_per_circle": 40,
        "use_buffer_for_union": True
    }

    def __init__(self, steps_per_circle=None):
        """
        The constructor takes no parameters. Use ``gerber.parse_files()``
        or ``gerber.parse_lines()`` to populate the object from Gerber source.

        :return: Gerber object
        :rtype: Gerber
        """

        # Initialize parent
        Geometry.__init__(self)

        self.solid_geometry = Polygon()

        # Number format
        self.int_digits = 3
        """Number of integer digits in Gerber numbers. Used during parsing."""

        self.frac_digits = 4
        """Number of fraction digits in Gerber numbers. Used during parsing."""
        
        ## Gerber elements ##
        # Apertures {'id':{'type':chr, 
        #             ['size':float], ['width':float],
        #             ['height':float]}, ...}
        self.apertures = {}

        # Aperture Macros
        self.aperture_macros = {}

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from Geometry.
        self.ser_attrs += ['int_digits', 'frac_digits', 'apertures',
                           'aperture_macros', 'solid_geometry']

        #### Parser patterns ####
        # FS - Format Specification
        # The format of X and Y must be the same!
        # L-omit leading zeros, T-omit trailing zeros
        # A-absolute notation, I-incremental notation
        self.fmt_re = re.compile(r'%FS([LT])([AI])X(\d)(\d)Y\d\d\*%$')

        # Mode (IN/MM)
        self.mode_re = re.compile(r'^%MO(IN|MM)\*%$')

        # Comment G04|G4
        self.comm_re = re.compile(r'^G0?4(.*)$')

        # AD - Aperture definition
        # Aperture Macro names: Name = [a-zA-Z_.$]{[a-zA-Z_.0-9]+}
        # NOTE: Adding "-" to support output from Upverter.
        self.ad_re = re.compile(r'^%ADD(\d\d+)([a-zA-Z_$\.][a-zA-Z0-9_$\.\-]*)(?:,(.*))?\*%$')

        # AM - Aperture Macro
        # Beginning of macro (Ends with *%):
        #self.am_re = re.compile(r'^%AM([a-zA-Z0-9]*)\*')

        # Tool change
        # May begin with G54 but that is deprecated
        self.tool_re = re.compile(r'^(?:G54)?D(\d\d+)\*$')

        # G01... - Linear interpolation plus flashes with coordinates
        # Operation code (D0x) missing is deprecated... oh well I will support it.
        self.lin_re = re.compile(r'^(?:G0?(1))?(?=.*X([\+-]?\d+))?(?=.*Y([\+-]?\d+))?[XY][^DIJ]*(?:D0?([123]))?\*$')

        # Operation code alone, usually just D03 (Flash)
        self.opcode_re = re.compile(r'^D0?([123])\*$')

        # G02/3... - Circular interpolation with coordinates
        # 2-clockwise, 3-counterclockwise
        # Operation code (D0x) missing is deprecated... oh well I will support it.
        # Optional start with G02 or G03, optional end with D01 or D02 with
        # optional coordinates but at least one in any order.
        self.circ_re = re.compile(r'^(?:G0?([23]))?(?=.*X([\+-]?\d+))?(?=.*Y([\+-]?\d+))' +
                                  '?(?=.*I([\+-]?\d+))?(?=.*J([\+-]?\d+))?[XYIJ][^D]*(?:D0([12]))?\*$')

        # G01/2/3 Occurring without coordinates
        self.interp_re = re.compile(r'^(?:G0?([123]))\*')

        # Single D74 or multi D75 quadrant for circular interpolation
        self.quad_re = re.compile(r'^G7([45])\*$')

        # Region mode on
        # In region mode, D01 starts a region
        # and D02 ends it. A new region can be started again
        # with D01. All contours must be closed before
        # D02 or G37.
        self.regionon_re = re.compile(r'^G36\*$')

        # Region mode off
        # Will end a region and come off region mode.
        # All contours must be closed before D02 or G37.
        self.regionoff_re = re.compile(r'^G37\*$')

        # End of file
        self.eof_re = re.compile(r'^M02\*')

        # IP - Image polarity
        self.pol_re = re.compile(r'^%IP(POS|NEG)\*%$')

        # LP - Level polarity
        self.lpol_re = re.compile(r'^%LP([DC])\*%$')

        # Units (OBSOLETE)
        self.units_re = re.compile(r'^G7([01])\*$')

        # Absolute/Relative G90/1 (OBSOLETE)
        self.absrel_re = re.compile(r'^G9([01])\*$')

        # Aperture macros
        self.am1_re = re.compile(r'^%AM([^\*]+)\*([^%]+)?(%)?$')
        self.am2_re = re.compile(r'(.*)%$')

        # How to discretize a circle.
        self.steps_per_circ = steps_per_circle or Gerber.defaults['steps_per_circle']

        self.use_buffer_for_union = self.defaults["use_buffer_for_union"]

    def scale(self, factor):
        """
        Scales the objects' geometry on the XY plane by a given factor.
        These are:

        * ``buffered_paths``
        * ``flash_geometry``
        * ``solid_geometry``
        * ``regions``

        NOTE:
        Does not modify the data used to create these elements. If these
        are recreated, the scaling will be lost. This behavior was modified
        because of the complexity reached in this class.

        :param factor: Number by which to scale.
        :type factor: float
        :rtype : None
        """

        ## solid_geometry ???
        #  It's a cascaded union of objects.
        self.solid_geometry = affinity.scale(self.solid_geometry, factor,
                                             factor, origin=(0, 0))

        # # Now buffered_paths, flash_geometry and solid_geometry
        # self.create_geometry()

    def offset(self, vect):
        """
        Offsets the objects' geometry on the XY plane by a given vector.
        These are:

        * ``buffered_paths``
        * ``flash_geometry``
        * ``solid_geometry``
        * ``regions``

        NOTE:
        Does not modify the data used to create these elements. If these
        are recreated, the scaling will be lost. This behavior was modified
        because of the complexity reached in this class.

        :param vect: (x, y) offset vector.
        :type vect: tuple
        :return: None
        """

        dx, dy = vect

        ## Solid geometry
        self.solid_geometry = affinity.translate(self.solid_geometry, xoff=dx, yoff=dy)

    # def mirror(self, axis, point):
    #     """
    #     Mirrors the object around a specified axis passign through
    #     the given point. What is affected:
    #
    #     * ``buffered_paths``
    #     * ``flash_geometry``
    #     * ``solid_geometry``
    #     * ``regions``
    #
    #     NOTE:
    #     Does not modify the data used to create these elements. If these
    #     are recreated, the scaling will be lost. This behavior was modified
    #     because of the complexity reached in this class.
    #
    #     :param axis: "X" or "Y" indicates around which axis to mirror.
    #     :type axis: str
    #     :param point: [x, y] point belonging to the mirror axis.
    #     :type point: list
    #     :return: None
    #     """
    #
    #     px, py = point
    #     xscale, yscale = {"X": (1.0, -1.0), "Y": (-1.0, 1.0)}[axis]
    #
    #     ## solid_geometry ???
    #     #  It's a cascaded union of objects.
    #     self.solid_geometry = affinity.scale(self.solid_geometry,
    #                                          xscale, yscale, origin=(px, py))

    def aperture_parse(self, apertureId, apertureType, apParameters):
        """
        Parse gerber aperture definition into dictionary of apertures.
        The following kinds and their attributes are supported:

        * *Circular (C)*: size (float)
        * *Rectangle (R)*: width (float), height (float)
        * *Obround (O)*: width (float), height (float).
        * *Polygon (P)*: diameter(float), vertices(int), [rotation(float)]
        * *Aperture Macro (AM)*: macro (ApertureMacro), modifiers (list)

        :param apertureId: Id of the aperture being defined.
        :param apertureType: Type of the aperture.
        :param apParameters: Parameters of the aperture.
        :type apertureId: str
        :type apertureType: str
        :type apParameters: str
        :return: Identifier of the aperture.
        :rtype: str
        """

        # Found some Gerber with a leading zero in the aperture id and the
        # referenced it without the zero, so this is a hack to handle that.
        apid = str(int(apertureId))

        try:  # Could be empty for aperture macros
            paramList = apParameters.split('X')
        except:
            paramList = None

        if apertureType == "C":  # Circle, example: %ADD11C,0.1*%
            self.apertures[apid] = {"type": "C",
                                    "size": float(paramList[0])}
            return apid
        
        if apertureType == "R":  # Rectangle, example: %ADD15R,0.05X0.12*%
            self.apertures[apid] = {"type": "R",
                                    "width": float(paramList[0]),
                                    "height": float(paramList[1]),
                                    "size": sqrt(float(paramList[0])**2 + float(paramList[1])**2)}  # Hack
            return apid

        if apertureType == "O":  # Obround
            self.apertures[apid] = {"type": "O",
                                    "width": float(paramList[0]),
                                    "height": float(paramList[1]),
                                    "size": sqrt(float(paramList[0])**2 + float(paramList[1])**2)}  # Hack
            return apid
        
        if apertureType == "P":  # Polygon (regular)
            self.apertures[apid] = {"type": "P",
                                    "diam": float(paramList[0]),
                                    "nVertices": int(paramList[1]),
                                    "size": float(paramList[0])}  # Hack
            if len(paramList) >= 3:
                self.apertures[apid]["rotation"] = float(paramList[2])
            return apid

        if apertureType in self.aperture_macros:
            self.apertures[apid] = {"type": "AM",
                                    "macro": self.aperture_macros[apertureType],
                                    "modifiers": paramList}
            return apid

        log.warning("Aperture not implemented: %s" % str(apertureType))
        return None
        
    def parse_file(self, filename, follow=False):
        """
        Calls Gerber.parse_lines() with generator of lines
        read from the given file. Will split the lines if multiple
        statements are found in a single original line.

        The following line is split into two::

            G54D11*G36*

        First is ``G54D11*`` and seconds is ``G36*``.

        :param filename: Gerber file to parse.
        :type filename: str
        :param follow: If true, will not create polygons, just lines
            following the gerber path.
        :type follow: bool
        :return: None
        """

        with open(filename, 'r') as gfile:

            def line_generator():
                for line in gfile:
                    line = line.strip(' \r\n')
                    while len(line) > 0:

                        # If ends with '%' leave as is.
                        if line[-1] == '%':
                            yield line
                            break

                        # Split after '*' if any.
                        starpos = line.find('*')
                        if starpos > -1:
                            cleanline = line[:starpos + 1]
                            yield cleanline
                            line = line[starpos + 1:]

                        # Otherwise leave as is.
                        else:
                            # yield cleanline
                            yield line
                            break

            self.parse_lines(line_generator(), follow=follow)

    #@profile
    def parse_lines(self, glines, follow=False):
        """
        Main Gerber parser. Reads Gerber and populates ``self.paths``, ``self.apertures``,
        ``self.flashes``, ``self.regions`` and ``self.units``.

        :param glines: Gerber code as list of strings, each element being
            one line of the source file.
        :type glines: list
        :param follow: If true, will not create polygons, just lines
            following the gerber path.
        :type follow: bool
        :return: None
        :rtype: None
        """

        # Coordinates of the current path, each is [x, y]
        path = []

        # Polygons are stored here until there is a change in polarity.
        # Only then they are combined via cascaded_union and added or
        # subtracted from solid_geometry. This is ~100 times faster than
        # applyng a union for every new polygon.
        poly_buffer = []

        last_path_aperture = None
        current_aperture = None

        # 1,2 or 3 from "G01", "G02" or "G03"
        current_interpolation_mode = None

        # 1 or 2 from "D01" or "D02"
        # Note this is to support deprecated Gerber not putting
        # an operation code at the end of every coordinate line.
        current_operation_code = None

        # Current coordinates
        current_x = None
        current_y = None

        # Absolute or Relative/Incremental coordinates
        # Not implemented
        absolute = True

        # How to interpret circular interpolation: SINGLE or MULTI
        quadrant_mode = None

        # Indicates we are parsing an aperture macro
        current_macro = None

        # Indicates the current polarity: D-Dark, C-Clear
        current_polarity = 'D'

        # If a region is being defined
        making_region = False

        #### Parsing starts here ####
        line_num = 0
        gline = ""
        try:
            for gline in glines:
                line_num += 1

                ### Cleanup
                gline = gline.strip(' \r\n')

                #log.debug("%3s %s" % (line_num, gline))

                ### Aperture Macros
                # Having this at the beggining will slow things down
                # but macros can have complicated statements than could
                # be caught by other patterns.
                if current_macro is None:  # No macro started yet
                    match = self.am1_re.search(gline)
                    # Start macro if match, else not an AM, carry on.
                    if match:
                        log.debug("Starting macro. Line %d: %s" % (line_num, gline))
                        current_macro = match.group(1)
                        self.aperture_macros[current_macro] = ApertureMacro(name=current_macro)
                        if match.group(2):  # Append
                            self.aperture_macros[current_macro].append(match.group(2))
                        if match.group(3):  # Finish macro
                            #self.aperture_macros[current_macro].parse_content()
                            current_macro = None
                            log.debug("Macro complete in 1 line.")
                        continue
                else:  # Continue macro
                    log.debug("Continuing macro. Line %d." % line_num)
                    match = self.am2_re.search(gline)
                    if match:  # Finish macro
                        log.debug("End of macro. Line %d." % line_num)
                        self.aperture_macros[current_macro].append(match.group(1))
                        #self.aperture_macros[current_macro].parse_content()
                        current_macro = None
                    else:  # Append
                        self.aperture_macros[current_macro].append(gline)
                    continue

                ### G01 - Linear interpolation plus flashes
                # Operation code (D0x) missing is deprecated... oh well I will support it.
                # REGEX: r'^(?:G0?(1))?(?:X(-?\d+))?(?:Y(-?\d+))?(?:D0([123]))?\*$'
                match = self.lin_re.search(gline)
                if match:
                    # Dxx alone?
                    # if match.group(1) is None and match.group(2) is None and match.group(3) is None:
                    #     try:
                    #         current_operation_code = int(match.group(4))
                    #     except:
                    #         pass  # A line with just * will match too.
                    #     continue
                    # NOTE: Letting it continue allows it to react to the
                    #       operation code.

                    # Parse coordinates
                    if match.group(2) is not None:
                        current_x = parse_gerber_number(match.group(2), self.frac_digits)
                    if match.group(3) is not None:
                        current_y = parse_gerber_number(match.group(3), self.frac_digits)

                    # Parse operation code
                    if match.group(4) is not None:
                        current_operation_code = int(match.group(4))

                    # Pen down: add segment
                    if current_operation_code == 1:
                        path.append([current_x, current_y])
                        last_path_aperture = current_aperture

                    elif current_operation_code == 2:
                        if len(path) > 1:

                            ## --- BUFFERED ---
                            if making_region:
                                if follow:
                                    geo = Polygon()
                                else:
                                    geo = Polygon(path)
                            else:
                                if last_path_aperture is None:
                                    log.warning("No aperture defined for curent path. (%d)" % line_num)
                                width = self.apertures[last_path_aperture]["size"]  # TODO: WARNING this should fail!
                                #log.debug("Line %d: Setting aperture to %s before buffering." % (line_num, last_path_aperture))
                                if follow:
                                    geo = LineString(path)
                                else:
                                    geo = LineString(path).buffer(width / 2)

                            if not geo.is_empty:
                                poly_buffer.append(geo)

                        path = [[current_x, current_y]]  # Start new path

                    # Flash
                    # Not allowed in region mode.
                    elif current_operation_code == 3:

                        # Create path draw so far.
                        if len(path) > 1:
                            # --- Buffered ----
                            width = self.apertures[last_path_aperture]["size"]

                            if follow:
                                geo = LineString(path)
                            else:
                                geo = LineString(path).buffer(width / 2)

                            if not geo.is_empty:
                                poly_buffer.append(geo)

                        # Reset path starting point
                        path = [[current_x, current_y]]

                        # --- BUFFERED ---
                        # Draw the flash
                        if follow:
                            continue
                        flash = Gerber.create_flash_geometry(Point([current_x, current_y]),
                                                             self.apertures[current_aperture])
                        if not flash.is_empty:
                            poly_buffer.append(flash)

                    continue

                ### G02/3 - Circular interpolation
                # 2-clockwise, 3-counterclockwise
                match = self.circ_re.search(gline)
                if match:
                    arcdir = [None, None, "cw", "ccw"]

                    mode, x, y, i, j, d = match.groups()
                    try:
                        x = parse_gerber_number(x, self.frac_digits)
                    except:
                        x = current_x
                    try:
                        y = parse_gerber_number(y, self.frac_digits)
                    except:
                        y = current_y
                    try:
                        i = parse_gerber_number(i, self.frac_digits)
                    except:
                        i = 0
                    try:
                        j = parse_gerber_number(j, self.frac_digits)
                    except:
                        j = 0

                    if quadrant_mode is None:
                        log.error("Found arc without preceding quadrant specification G74 or G75. (%d)" % line_num)
                        log.error(gline)
                        continue

                    if mode is None and current_interpolation_mode not in [2, 3]:
                        log.error("Found arc without circular interpolation mode defined. (%d)" % line_num)
                        log.error(gline)
                        continue
                    elif mode is not None:
                        current_interpolation_mode = int(mode)

                    # Set operation code if provided
                    if d is not None:
                        current_operation_code = int(d)

                    # Nothing created! Pen Up.
                    if current_operation_code == 2:
                        log.warning("Arc with D2. (%d)" % line_num)
                        if len(path) > 1:
                            if last_path_aperture is None:
                                log.warning("No aperture defined for curent path. (%d)" % line_num)

                            # --- BUFFERED ---
                            width = self.apertures[last_path_aperture]["size"]

                            if follow:
                                buffered = LineString(path)
                            else:
                                buffered = LineString(path).buffer(width / 2)
                            if not buffered.is_empty:
                                poly_buffer.append(buffered)

                        current_x = x
                        current_y = y
                        path = [[current_x, current_y]]  # Start new path
                        continue

                    # Flash should not happen here
                    if current_operation_code == 3:
                        log.error("Trying to flash within arc. (%d)" % line_num)
                        continue

                    if quadrant_mode == 'MULTI':
                        center = [i + current_x, j + current_y]
                        radius = sqrt(i ** 2 + j ** 2)
                        start = arctan2(-j, -i)  # Start angle
                        # Numerical errors might prevent start == stop therefore
                        # we check ahead of time. This should result in a
                        # 360 degree arc.
                        if current_x == x and current_y == y:
                            stop = start
                        else:
                            stop = arctan2(-center[1] + y, -center[0] + x)  # Stop angle

                        this_arc = arc(center, radius, start, stop,
                                       arcdir[current_interpolation_mode],
                                       self.steps_per_circ)

                        # The last point in the computed arc can have
                        # numerical errors. The exact final point is the
                        # specified (x, y). Replace.
                        this_arc[-1] = (x, y)

                        # Last point in path is current point
                        # current_x = this_arc[-1][0]
                        # current_y = this_arc[-1][1]
                        current_x, current_y = x, y

                        # Append
                        path += this_arc

                        last_path_aperture = current_aperture

                        continue

                    if quadrant_mode == 'SINGLE':

                        center_candidates = [
                            [i + current_x, j + current_y],
                            [-i + current_x, j + current_y],
                            [i + current_x, -j + current_y],
                            [-i + current_x, -j + current_y]
                        ]

                        valid = False
                        log.debug("I: %f  J: %f" % (i, j))
                        for center in center_candidates:
                            radius = sqrt(i ** 2 + j ** 2)

                            # Make sure radius to start is the same as radius to end.
                            radius2 = sqrt((center[0] - x) ** 2 + (center[1] - y) ** 2)
                            if radius2 < radius * 0.95 or radius2 > radius * 1.05:
                                continue  # Not a valid center.

                            # Correct i and j and continue as with multi-quadrant.
                            i = center[0] - current_x
                            j = center[1] - current_y

                            start = arctan2(-j, -i)  # Start angle
                            stop = arctan2(-center[1] + y, -center[0] + x)  # Stop angle
                            angle = abs(arc_angle(start, stop, arcdir[current_interpolation_mode]))
                            log.debug("ARC START: %f, %f  CENTER: %f, %f  STOP: %f, %f" %
                                      (current_x, current_y, center[0], center[1], x, y))
                            log.debug("START Ang: %f, STOP Ang: %f, DIR: %s, ABS: %.12f <= %.12f: %s" %
                                      (start * 180 / pi, stop * 180 / pi, arcdir[current_interpolation_mode],
                                       angle * 180 / pi, pi / 2 * 180 / pi, angle <= (pi + 1e-6) / 2))

                            if angle <= (pi + 1e-6) / 2:
                                log.debug("########## ACCEPTING ARC ############")
                                this_arc = arc(center, radius, start, stop,
                                               arcdir[current_interpolation_mode],
                                               self.steps_per_circ)

                                # Replace with exact values
                                this_arc[-1] = (x, y)

                                # current_x = this_arc[-1][0]
                                # current_y = this_arc[-1][1]
                                current_x, current_y = x, y

                                path += this_arc
                                last_path_aperture = current_aperture
                                valid = True
                                break

                        if valid:
                            continue
                        else:
                            log.warning("Invalid arc in line %d." % line_num)

                ### Operation code alone
                # Operation code alone, usually just D03 (Flash)
                # self.opcode_re = re.compile(r'^D0?([123])\*$')
                match = self.opcode_re.search(gline)
                if match:
                    current_operation_code = int(match.group(1))
                    if current_operation_code == 3:

                        ## --- Buffered ---
                        try:
                            log.debug("Bare op-code %d." % current_operation_code)
                            # flash = Gerber.create_flash_geometry(Point(path[-1]),
                            #                                      self.apertures[current_aperture])
                            if follow:
                                continue
                            flash = Gerber.create_flash_geometry(Point(current_x, current_y),
                                                                 self.apertures[current_aperture])
                            if not flash.is_empty:
                                poly_buffer.append(flash)
                        except IndexError:
                            log.warning("Line %d: %s -> Nothing there to flash!" % (line_num, gline))

                    continue

                ### G74/75* - Single or multiple quadrant arcs
                match = self.quad_re.search(gline)
                if match:
                    if match.group(1) == '4':
                        quadrant_mode = 'SINGLE'
                    else:
                        quadrant_mode = 'MULTI'
                    continue

                ### G36* - Begin region
                if self.regionon_re.search(gline):
                    if len(path) > 1:
                        # Take care of what is left in the path

                        ## --- Buffered ---
                        width = self.apertures[last_path_aperture]["size"]

                        if follow:
                            geo = LineString(path)
                        else:
                            geo = LineString(path).buffer(width/2)
                        if not geo.is_empty:
                            poly_buffer.append(geo)

                        path = [path[-1]]

                    making_region = True
                    continue

                ### G37* - End region
                if self.regionoff_re.search(gline):
                    making_region = False

                    # Only one path defines region?
                    # This can happen if D02 happened before G37 and
                    # is not and error.
                    if len(path) < 3:
                        # print "ERROR: Path contains less than 3 points:"
                        # print path
                        # print "Line (%d): " % line_num, gline
                        # path = []
                        #path = [[current_x, current_y]]
                        continue

                    # For regions we may ignore an aperture that is None
                    # self.regions.append({"polygon": Polygon(path),
                    #                      "aperture": last_path_aperture})

                    # --- Buffered ---
                    if follow:
                        region = Polygon()
                    else:
                        region = Polygon(path)
                    if not region.is_valid:
                        if not follow:
                            region = region.buffer(0)
                    if not region.is_empty:
                        poly_buffer.append(region)

                    path = [[current_x, current_y]]  # Start new path
                    continue

                ### Aperture definitions %ADD...
                match = self.ad_re.search(gline)
                if match:
                    log.info("Found aperture definition. Line %d: %s" % (line_num, gline))
                    self.aperture_parse(match.group(1), match.group(2), match.group(3))
                    continue

                ### G01/2/3* - Interpolation mode change
                # Can occur along with coordinates and operation code but
                # sometimes by itself (handled here).
                # Example: G01*
                match = self.interp_re.search(gline)
                if match:
                    current_interpolation_mode = int(match.group(1))
                    continue

                ### Tool/aperture change
                # Example: D12*
                match = self.tool_re.search(gline)
                if match:
                    current_aperture = match.group(1)
                    log.debug("Line %d: Aperture change to (%s)" % (line_num, match.group(1)))
                    log.debug(self.apertures[current_aperture])

                    # Take care of the current path with the previous tool
                    if len(path) > 1:
                        # --- Buffered ----
                        width = self.apertures[last_path_aperture]["size"]

                        if follow:
                            geo = LineString(path)
                        else:
                            geo = LineString(path).buffer(width / 2)
                        if not geo.is_empty:
                            poly_buffer.append(geo)

                        path = [path[-1]]

                    continue

                ### Polarity change
                # Example: %LPD*% or %LPC*%
                # If polarity changes, creates geometry from current
                # buffer, then adds or subtracts accordingly.
                match = self.lpol_re.search(gline)
                if match:
                    if len(path) > 1 and current_polarity != match.group(1):

                        # --- Buffered ----
                        width = self.apertures[last_path_aperture]["size"]

                        if follow:
                            geo = LineString(path)
                        else:
                            geo = LineString(path).buffer(width / 2)
                        if not geo.is_empty:
                            poly_buffer.append(geo)

                        path = [path[-1]]

                    # --- Apply buffer ---
                    # If added for testing of bug #83
                    # TODO: Remove when bug fixed
                    if len(poly_buffer) > 0:
                        if current_polarity == 'D':
                            self.solid_geometry = self.solid_geometry.union(unary_union(poly_buffer))
                        else:
                            self.solid_geometry = self.solid_geometry.difference(unary_union(poly_buffer))
                        poly_buffer = []

                    current_polarity = match.group(1)
                    continue

                ### Number format
                # Example: %FSLAX24Y24*%
                # TODO: This is ignoring most of the format. Implement the rest.
                match = self.fmt_re.search(gline)
                if match:
                    absolute = {'A': True, 'I': False}
                    self.int_digits = int(match.group(3))
                    self.frac_digits = int(match.group(4))
                    continue

                ### Mode (IN/MM)
                # Example: %MOIN*%
                match = self.mode_re.search(gline)
                if match:
                    #self.units = match.group(1)

                    # Changed for issue #80
                    self.convert_units(match.group(1))
                    continue

                ### Units (G70/1) OBSOLETE
                match = self.units_re.search(gline)
                if match:
                    #self.units = {'0': 'IN', '1': 'MM'}[match.group(1)]

                    # Changed for issue #80
                    self.convert_units({'0': 'IN', '1': 'MM'}[match.group(1)])
                    continue

                ### Absolute/relative coordinates G90/1 OBSOLETE
                match = self.absrel_re.search(gline)
                if match:
                    absolute = {'0': True, '1': False}[match.group(1)]
                    continue

                #### Ignored lines
                ## Comments
                match = self.comm_re.search(gline)
                if match:
                    continue

                ## EOF
                match = self.eof_re.search(gline)
                if match:
                    continue

                ### Line did not match any pattern. Warn user.
                log.warning("Line ignored (%d): %s" % (line_num, gline))

            if len(path) > 1:
                # EOF, create shapely LineString if something still in path

                ## --- Buffered ---
                width = self.apertures[last_path_aperture]["size"]
                if follow:
                    geo = LineString(path)
                else:
                    geo = LineString(path).buffer(width / 2)
                if not geo.is_empty:
                    poly_buffer.append(geo)

            # --- Apply buffer ---
            if follow:
                self.solid_geometry = poly_buffer
                return

            log.warn("Joining %d polygons." % len(poly_buffer))
            if self.use_buffer_for_union:
                log.debug("Union by buffer...")
                new_poly = MultiPolygon(poly_buffer)
                new_poly = new_poly.buffer(0.00000001)
                new_poly = new_poly.buffer(-0.00000001)
                log.warn("Union(buffer) done.")
            else:
                log.debug("Union by union()...")
                new_poly = unary_union(poly_buffer)
                new_poly = new_poly.buffer(0)
                log.warn("Union done.")
            if current_polarity == 'D':
                self.solid_geometry = self.solid_geometry.union(new_poly)
            else:
                self.solid_geometry = self.solid_geometry.difference(new_poly)

        except Exception as err:
            ex_type, ex, tb = sys.exc_info()
            traceback.print_tb(tb)
            #print traceback.format_exc()

            log.error("PARSING FAILED. Line %d: %s" % (line_num, gline))
            raise GerberParseError("Line %d: %s" % (line_num, gline), repr(err))

    @staticmethod
    def create_flash_geometry(location, aperture):

        log.debug('Flashing @%s, Aperture: %s' % (location, aperture))

        if type(location) == list:
            location = Point(location)

        if aperture['type'] == 'C':  # Circles
            return location.buffer(aperture['size'] / 2)

        if aperture['type'] == 'R':  # Rectangles
            loc = location.coords[0]
            width = aperture['width']
            height = aperture['height']
            minx = loc[0] - width / 2
            maxx = loc[0] + width / 2
            miny = loc[1] - height / 2
            maxy = loc[1] + height / 2
            return shply_box(minx, miny, maxx, maxy)

        if aperture['type'] == 'O':  # Obround
            loc = location.coords[0]
            width = aperture['width']
            height = aperture['height']
            if width > height:
                p1 = Point(loc[0] + 0.5 * (width - height), loc[1])
                p2 = Point(loc[0] - 0.5 * (width - height), loc[1])
                c1 = p1.buffer(height * 0.5)
                c2 = p2.buffer(height * 0.5)
            else:
                p1 = Point(loc[0], loc[1] + 0.5 * (height - width))
                p2 = Point(loc[0], loc[1] - 0.5 * (height - width))
                c1 = p1.buffer(width * 0.5)
                c2 = p2.buffer(width * 0.5)
            return unary_union([c1, c2]).convex_hull

        if aperture['type'] == 'P':  # Regular polygon
            loc = location.coords[0]
            diam = aperture['diam']
            n_vertices = aperture['nVertices']
            points = []
            for i in range(0, n_vertices):
                x = loc[0] + 0.5 * diam * (cos(2 * pi * i / n_vertices))
                y = loc[1] + 0.5 * diam * (sin(2 * pi * i / n_vertices))
                points.append((x, y))
            ply = Polygon(points)
            if 'rotation' in aperture:
                ply = affinity.rotate(ply, aperture['rotation'])
            return ply

        if aperture['type'] == 'AM':  # Aperture Macro
            loc = location.coords[0]
            flash_geo = aperture['macro'].make_geometry(aperture['modifiers'])
            if flash_geo.is_empty:
                log.warning("Empty geometry for Aperture Macro: %s" % str(aperture['macro'].name))
            return affinity.translate(flash_geo, xoff=loc[0], yoff=loc[1])

        log.warning("Unknown aperture type: %s" % aperture['type'])
        return None
    
    def create_geometry(self):
        """
        Geometry from a Gerber file is made up entirely of polygons.
        Every stroke (linear or circular) has an aperture which gives
        it thickness. Additionally, aperture strokes have non-zero area,
        and regions naturally do as well.

        :rtype : None
        :return: None
        """

        # self.buffer_paths()
        #
        # self.fix_regions()
        #
        # self.do_flashes()
        #
        # self.solid_geometry = cascaded_union(self.buffered_paths +
        #                                      [poly['polygon'] for poly in self.regions] +
        #                                      self.flash_geometry)

    def get_bounding_box(self, margin=0.0, rounded=False):
        """
        Creates and returns a rectangular polygon bounding at a distance of
        margin from the object's ``solid_geometry``. If margin > 0, the polygon
        can optionally have rounded corners of radius equal to margin.

        :param margin: Distance to enlarge the rectangular bounding
         box in both positive and negative, x and y axes.
        :type margin: float
        :param rounded: Wether or not to have rounded corners.
        :type rounded: bool
        :return: The bounding box.
        :rtype: Shapely.Polygon
        """

        bbox = self.solid_geometry.envelope.buffer(margin)
        if not rounded:
            bbox = bbox.envelope
        return bbox
