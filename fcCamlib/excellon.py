############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
############################################################

import re

from shapely.geometry import Point

from .geometry import Geometry
from .utils import setup_log

log = setup_log("fcCamlib.excellon")


class Excellon(Geometry):
    """
    *ATTRIBUTES*

    * ``tools`` (dict): The key is the tool name and the value is
      a dictionary specifying the tool:

    ================  ====================================
    Key               Value
    ================  ====================================
    C                 Diameter of the tool
    Others            Not supported (Ignored).
    ================  ====================================

    * ``drills`` (list): Each is a dictionary:

    ================  ====================================
    Key               Value
    ================  ====================================
    point             (Shapely.Point) Where to drill
    tool              (str) A key in ``tools``
    ================  ====================================
    """

    defaults = {
        "zeros": "L"
    }

    def __init__(self, zeros=None):
        """
        The constructor takes no parameters.

        :return: Excellon object.
        :rtype: Excellon
        """

        Geometry.__init__(self)
        
        self.tools = {}
        
        self.drills = []

        ## IN|MM -> Units are inherited from Geometry
        #self.units = units

        # Trailing "T" or leading "L" (default)
        #self.zeros = "T"
        self.zeros = zeros or self.defaults["zeros"]

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from Geometry.
        self.ser_attrs += ['tools', 'drills', 'zeros']

        #### Patterns ####
        # Regex basics:
        # ^ - beginning
        # $ - end
        # *: 0 or more, +: 1 or more, ?: 0 or 1

        # M48 - Beggining of Part Program Header
        self.hbegin_re = re.compile(r'^M48$')

        # M95 or % - End of Part Program Header
        # NOTE: % has different meaning in the body
        self.hend_re = re.compile(r'^(?:M95|%)$')

        # FMAT Excellon format
        # Ignored in the parser
        #self.fmat_re = re.compile(r'^FMAT,([12])$')

        # Number format and units
        # INCH uses 6 digits
        # METRIC uses 5/6
        self.units_re = re.compile(r'^(INCH|METRIC)(?:,([TL])Z)?$')

        # Tool definition/parameters (?= is look-ahead
        # NOTE: This might be an overkill!
        # self.toolset_re = re.compile(r'^T(0?\d|\d\d)(?=.*C(\d*\.?\d*))?' +
        #                              r'(?=.*F(\d*\.?\d*))?(?=.*S(\d*\.?\d*))?' +
        #                              r'(?=.*B(\d*\.?\d*))?(?=.*H(\d*\.?\d*))?' +
        #                              r'(?=.*Z([-\+]?\d*\.?\d*))?[CFSBHT]')
        self.toolset_re = re.compile(r'^T(\d+)(?=.*C(\d*\.?\d*))?' +
                                     r'(?=.*F(\d*\.?\d*))?(?=.*S(\d*\.?\d*))?' +
                                     r'(?=.*B(\d*\.?\d*))?(?=.*H(\d*\.?\d*))?' +
                                     r'(?=.*Z([-\+]?\d*\.?\d*))?[CFSBHT]')

        # Tool select
        # Can have additional data after tool number but
        # is ignored if present in the header.
        # Warning: This will match toolset_re too.
        # self.toolsel_re = re.compile(r'^T((?:\d\d)|(?:\d))')
        self.toolsel_re = re.compile(r'^T(\d+)')

        # Comment
        self.comm_re = re.compile(r'^;(.*)$')

        # Absolute/Incremental G90/G91
        self.absinc_re = re.compile(r'^G9([01])$')

        # Modes of operation
        # 1-linear, 2-circCW, 3-cirCCW, 4-vardwell, 5-Drill
        self.modes_re = re.compile(r'^G0([012345])')

        # Measuring mode
        # 1-metric, 2-inch
        self.meas_re = re.compile(r'^M7([12])$')

        # Coordinates
        #self.xcoord_re = re.compile(r'^X(\d*\.?\d*)(?:Y\d*\.?\d*)?$')
        #self.ycoord_re = re.compile(r'^(?:X\d*\.?\d*)?Y(\d*\.?\d*)$')
        self.coordsperiod_re = re.compile(r'(?=.*X([-\+]?\d*\.\d*))?(?=.*Y([-\+]?\d*\.\d*))?[XY]')
        self.coordsnoperiod_re = re.compile(r'(?!.*\.)(?=.*X([-\+]?\d*))?(?=.*Y([-\+]?\d*))?[XY]')

        # R - Repeat hole (# times, X offset, Y offset)
        self.rep_re = re.compile(r'^R(\d+)(?=.*[XY])+(?:X([-\+]?\d*\.?\d*))?(?:Y([-\+]?\d*\.?\d*))?$')

        # Various stop/pause commands
        self.stop_re = re.compile(r'^((G04)|(M09)|(M06)|(M00)|(M30))')

        # Parse coordinates
        self.leadingzeros_re = re.compile(r'^[-\+]?(0*)(\d*)')
        
    def parse_file(self, filename):
        """
        Reads the specified file as array of lines as
        passes it to ``parse_lines()``.

        :param filename: The file to be read and parsed.
        :type filename: str
        :return: None
        """
        with open(filename, 'r') as efile:
            estr = efile.readlines()
        self.parse_lines(estr)

    def parse_lines(self, elines):
        """
        Main Excellon parser.

        :param elines: List of strings, each being a line of Excellon code.
        :type elines: list
        :return: None
        """

        # State variables
        current_tool = ""
        in_header = False
        current_x = None
        current_y = None

        #### Parsing starts here ####
        line_num = 0  # Line number
        eline = ""
        try:
            for eline in elines:
                line_num += 1
                #log.debug("%3d %s" % (line_num, str(eline)))

                ### Cleanup lines
                eline = eline.strip(' \r\n')

                ## Header Begin (M48) ##
                if self.hbegin_re.search(eline):
                    in_header = True
                    continue

                ## Header End ##
                if self.hend_re.search(eline):
                    in_header = False
                    continue

                ## Alternative units format M71/M72
                # Supposed to be just in the body (yes, the body)
                # but some put it in the header (PADS for example).
                # Will detect anywhere. Occurrence will change the
                # object's units.
                match = self.meas_re.match(eline)
                if match:
                    #self.units = {"1": "MM", "2": "IN"}[match.group(1)]

                    # Modified for issue #80
                    self.convert_units({"1": "MM", "2": "IN"}[match.group(1)])
                    log.debug("  Units: %s" % self.units)
                    continue

                #### Body ####
                if not in_header:

                    ## Tool change ##
                    match = self.toolsel_re.search(eline)
                    if match:
                        current_tool = str(int(match.group(1)))
                        log.debug("Tool change: %s" % current_tool)
                        continue

                    ## Coordinates without period ##
                    match = self.coordsnoperiod_re.search(eline)
                    if match:
                        try:
                            #x = float(match.group(1))/10000
                            x = self.parse_number(match.group(1))
                            current_x = x
                        except TypeError:
                            x = current_x

                        try:
                            #y = float(match.group(2))/10000
                            y = self.parse_number(match.group(2))
                            current_y = y
                        except TypeError:
                            y = current_y

                        if x is None or y is None:
                            log.error("Missing coordinates")
                            continue

                        self.drills.append({'point': Point((x, y)), 'tool': current_tool})
                        log.debug("{:15} {:8} {:8}".format(eline, x, y))
                        continue

                    ## Coordinates with period: Use literally. ##
                    match = self.coordsperiod_re.search(eline)
                    if match:
                        try:
                            x = float(match.group(1))
                            current_x = x
                        except TypeError:
                            x = current_x

                        try:
                            y = float(match.group(2))
                            current_y = y
                        except TypeError:
                            y = current_y

                        if x is None or y is None:
                            log.error("Missing coordinates")
                            continue

                        self.drills.append({'point': Point((x, y)), 'tool': current_tool})
                        log.debug("{:15} {:8} {:8}".format(eline, x, y))
                        continue

                #### Header ####
                if in_header:

                    ## Tool definitions ##
                    match = self.toolset_re.search(eline)
                    if match:

                        name = str(int(match.group(1)))
                        spec = {
                            "C": float(match.group(2)),
                            # "F": float(match.group(3)),
                            # "S": float(match.group(4)),
                            # "B": float(match.group(5)),
                            # "H": float(match.group(6)),
                            # "Z": float(match.group(7))
                        }
                        self.tools[name] = spec
                        log.debug("  Tool definition: %s %s" % (name, spec))
                        continue

                    ## Units and number format ##
                    match = self.units_re.match(eline)
                    if match:
                        self.zeros = match.group(2) or self.zeros  # "T" or "L". Might be empty

                        #self.units = {"INCH": "IN", "METRIC": "MM"}[match.group(1)]

                        # Modified for issue #80
                        self.convert_units({"INCH": "IN", "METRIC": "MM"}[match.group(1)])
                        log.debug("  Units/Format: %s %s" % (self.units, self.zeros))
                        continue

                log.warning("Line ignored: %s" % eline)

            log.info("Zeros: %s, Units %s." % (self.zeros, self.units))

        except Exception as e:
            log.error("PARSING FAILED. Line %d: %s" % (line_num, eline))
            raise
        
    def parse_number(self, number_str):
        """
        Parses coordinate numbers without period.

        :param number_str: String representing the numerical value.
        :type number_str: str
        :return: Floating point representation of the number
        :rtype: foat
        """
        if self.zeros == "L":
            # With leading zeros, when you type in a coordinate,
            # the leading zeros must always be included.  Trailing zeros
            # are unneeded and may be left off. The CNC-7 will automatically add them.
            # r'^[-\+]?(0*)(\d*)'
            # 6 digits are divided by 10^4
            # If less than size digits, they are automatically added,
            # 5 digits then are divided by 10^3 and so on.
            match = self.leadingzeros_re.search(number_str)
            if self.units.lower() == "in":
                return float(number_str) / \
                    (10 ** (len(match.group(1)) + len(match.group(2)) - 2))
            else:
                return float(number_str) / \
                    (10 ** (len(match.group(1)) + len(match.group(2)) - 3))

        else:  # Trailing
            # You must show all zeros to the right of the number and can omit
            # all zeros to the left of the number. The CNC-7 will count the number
            # of digits you typed and automatically fill in the missing zeros.
            if self.units.lower() == "in":  # Inches is 00.0000
                return float(number_str) / 10000
            else:
                return float(number_str) / 1000  # Metric is 000.000

    def create_geometry(self):
        """
        Creates circles of the tool diameter at every point
        specified in ``self.drills``.

        :return: None
        """
        self.solid_geometry = []

        for drill in self.drills:
            # poly = drill['point'].buffer(self.tools[drill['tool']]["C"]/2.0)
            tooldia = self.tools[drill['tool']]['C']
            poly = drill['point'].buffer(tooldia / 2.0)
            self.solid_geometry.append(poly)

    def scale(self, factor):
        """
        Scales geometry on the XY plane in the object by a given factor.
        Tool sizes, feedrates an Z-plane dimensions are untouched.

        :param factor: Number by which to scale the object.
        :type factor: float
        :return: None
        :rtype: NOne
        """

        # Drills
        for drill in self.drills:
            drill['point'] = affinity.scale(drill['point'], factor, factor, origin=(0, 0))

        self.create_geometry()

    def offset(self, vect):
        """
        Offsets geometry on the XY plane in the object by a given vector.

        :param vect: (x, y) offset vector.
        :type vect: tuple
        :return: None
        """

        dx, dy = vect

        # Drills
        for drill in self.drills:
            drill['point'] = affinity.translate(drill['point'], xoff=dx, yoff=dy)

        # Recreate geometry
        self.create_geometry()

    def mirror(self, axis, point):
        """

        :param axis: "X" or "Y" indicates around which axis to mirror.
        :type axis: str
        :param point: [x, y] point belonging to the mirror axis.
        :type point: list
        :return: None
        """

        px, py = point
        xscale, yscale = {"X": (1.0, -1.0), "Y": (-1.0, 1.0)}[axis]

        # Modify data
        for drill in self.drills:
            drill['point'] = affinity.scale(drill['point'], xscale, yscale, origin=(px, py))

        # Recreate geometry
        self.create_geometry()

    def convert_units(self, units):
        factor = Geometry.convert_units(self, units)

        # Tools
        for tname in self.tools:
            self.tools[tname]["C"] *= factor

        self.create_geometry()

        return factor
