############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
############################################################

import re

from decimal import Decimal
from numpy import arctan2, sqrt
from io import StringIO
from shapely import affinity
from shapely.geometry import LineString, Point, LinearRing
from shapely.ops import unary_union

from .fcTree import FlatCAMRTreeStorage
from .geometry import Geometry
from .utils import arc, setup_log

log = setup_log("fcCamlib.cncjob")


class CNCjob(Geometry):
    """
    Represents work to be done by a CNC machine.

    *ATTRIBUTES*

    * ``gcode_parsed`` (list): Each is a dictionary:

    =====================  =========================================
    Key                    Value
    =====================  =========================================
    geom                   (Shapely.LineString) Tool path (XY plane)
    kind                   (string) "AB", A is "T" (travel) or
                           "C" (cut). B is "F" (fast) or "S" (slow).
    =====================  =========================================
    """

    defaults = {
        "zdownrate": None,
        "coordinate_format": "X%.4fY%.4f"
    }

    def __init__(self,
                 units="in",
                 kind="generic",
                 z_move=0.1,
                 feedrate=3.0,
                 z_cut=-0.002,
                 tooldia=0.0,
                 zdownrate=None,
                 spindlespeed=None):

        Geometry.__init__(self)
        self.kind = kind
        self.units = units
        self.z_cut = z_cut
        self.z_move = z_move
        self.feedrate = feedrate
        self.tooldia = tooldia
        self.unitcode = {"IN": "G20", "MM": "G21"}
        # TODO: G04 Does not exist. It's G4 and now we are handling in postprocessing.
        #self.pausecode = "G04 P1"
        self.feedminutecode = "G94"
        self.absolutecode = "G90"
        self.gcode = ""
        self.input_geometry_bounds = None
        self.gcode_parsed = None
        self.steps_per_circ = 20  # Used when parsing G-code arcs

        if zdownrate is not None:
            self.zdownrate = float(zdownrate)
        elif CNCjob.defaults["zdownrate"] is not None:
            self.zdownrate = float(CNCjob.defaults["zdownrate"])
        else:
            self.zdownrate = None

        self.spindlespeed = spindlespeed

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from Geometry.
        self.ser_attrs += ['kind', 'z_cut', 'z_move', 'feedrate', 'tooldia',
                           'gcode', 'input_geometry_bounds', 'gcode_parsed',
                           'steps_per_circ']

    def convert_units(self, units):
        factor = Geometry.convert_units(self, units)
        log.debug("CNCjob.convert_units()")

        self.z_cut *= factor
        self.z_move *= factor
        self.feedrate *= factor
        self.tooldia *= factor

        return factor

    def generate_from_excellon_by_tool(self, exobj, tools="all",
                                       toolchange=False, toolchangez=0.1):
        """
        Creates gcode for this object from an Excellon object
        for the specified tools.

        :param exobj: Excellon object to process
        :type exobj: Excellon
        :param tools: Comma separated tool names
        :type: tools: str
        :return: None
        :rtype: None
        """

        log.debug("Creating CNC Job from Excellon...")

        # Tools
        
        # sort the tools list by the second item in tuple (here we have a dict with diameter of the tool)
        # so we actually are sorting the tools by diameter
        sorted_tools = sorted(exobj.tools.items(), key = lambda x: x[1])
        if tools == "all":
            tools = [i[0] for i in sorted_tools]   # we get a array of ordered tools
            log.debug("Tools 'all' and sorted are: %s" % str(tools))
        else:
            selected_tools = [x.strip() for x in tools.split(",")]  # we strip spaces and also separate the tools by ','
            selected_tools = filter(lambda i: i in selected_tools, selected_tools)

            # Create a sorted list of selected tools from the sorted_tools list
            tools = [i for i, j in sorted_tools for k in selected_tools if i == k]
            log.debug("Tools selected and sorted are: %s" % str(tools)) 

        # Points (Group by tool)
        points = {}
        for drill in exobj.drills:
            if drill['tool'] in tools:
                try:
                    points[drill['tool']].append(drill['point'])
                except KeyError:
                    points[drill['tool']] = [drill['point']]

        #log.debug("Found %d drills." % len(points))
        self.gcode = []

        # Basic G-Code macros
        t = "G00 " + CNCjob.defaults["coordinate_format"] + "\n"
        down = "G01 Z%.4f\n" % self.z_cut
        up = "G00 Z%.4f\n" % self.z_move
        up_to_zero = "G01 Z0\n"

        # Initialization
        gcode = self.unitcode[self.units.upper()] + "\n"
        gcode += self.absolutecode + "\n"
        gcode += self.feedminutecode + "\n"
        gcode += "F%.2f\n" % self.feedrate
        gcode += "G00 Z%.4f\n" % self.z_move  # Move to travel height

        if self.spindlespeed is not None:
            # Spindle start with configured speed
            gcode += "M03 S%d\n" % int(self.spindlespeed)
        else:
            gcode += "M03\n"  # Spindle start

        #gcode += self.pausecode + "\n"

        for tool in tools:

            # Only if tool has points.
            if tool in points:
                # Tool change sequence (optional)
                if toolchange:
                    gcode += "G00 Z%.4f\n" % toolchangez
                    gcode += "T%d\n" % int(tool)  # Indicate tool slot (for automatic tool changer)
                    gcode += "M5\n"  # Spindle Stop
                    gcode += "M6\n"  # Tool change
                    gcode += "(MSG, Change to tool dia=%.4f)\n" % exobj.tools[tool]["C"]
                    gcode += "M0\n"  # Temporary machine stop
                    if self.spindlespeed is not None:
                        # Spindle start with configured speed
                        gcode += "M03 S%d\n" % int(self.spindlespeed)
                    else:
                        gcode += "M03\n"  # Spindle start

                # Drillling!
                for point in points[tool]:
                    x, y = point.coords.xy
                    gcode += t % (x[0], y[0])
                    gcode += down + up_to_zero + up

        gcode += t % (0, 0)
        gcode += "M05\n"  # Spindle stop

        self.gcode = gcode

    def generate_from_geometry_2(self,
                                 geometry,
                                 append=True,
                                 tooldia=None,
                                 tolerance=0,
                                 multidepth=False,
                                 depthpercut=None):
        """
        Second algorithm to generate from Geometry.

        ALgorithm description:
        ----------------------
        Uses RTree to find the nearest path to follow.

        :param geometry:
        :param append:
        :param tooldia:
        :param tolerance:
        :param multidepth: If True, use multiple passes to reach
           the desired depth.
        :param depthpercut: Maximum depth in each pass.
        :return: None
        """
        assert isinstance(geometry, Geometry), \
            "Expected a Geometry, got %s" % type(geometry)

        log.debug("generate_from_geometry_2()")

        ## Flatten the geometry
        # Only linear elements (no polygons) remain.
        flat_geometry = geometry.flatten(pathonly=True)
        log.debug("%d paths" % len(flat_geometry))

        ## Index first and last points in paths
        # What points to index.
        def get_pts(o):
            return [o.coords[0], o.coords[-1]]

        # Create the indexed storage.
        storage = FlatCAMRTreeStorage()
        storage.get_points = get_pts

        # Store the geometry
        log.debug("Indexing geometry before generating G-Code...")
        for shape in flat_geometry:
            if shape is not None:  # TODO: This shouldn't have happened.
                storage.insert(shape)

        if tooldia is not None:
            self.tooldia = tooldia

        # self.input_geometry_bounds = geometry.bounds()

        if not append:
            self.gcode = ""

        # Initial G-Code
        self.gcode = self.unitcode[self.units.upper()] + "\n"
        self.gcode += self.absolutecode + "\n"
        self.gcode += self.feedminutecode + "\n"
        self.gcode += "F%.2f\n" % self.feedrate
        self.gcode += "G00 Z%.4f\n" % self.z_move  # Move (up) to travel height
        if self.spindlespeed is not None:
            self.gcode += "M03 S%d\n" % int(self.spindlespeed)  # Spindle start with configured speed
        else:
            self.gcode += "M03\n"  # Spindle start
        #self.gcode += self.pausecode + "\n"

        ## Iterate over geometry paths getting the nearest each time.
        log.debug("Starting G-Code...")
        path_count = 0
        current_pt = (0, 0)
        pt, geo = storage.nearest(current_pt)
        try:
            while True:
                path_count += 1
                #print "Current: ", "(%.3f, %.3f)" % current_pt

                # Remove before modifying, otherwise
                # deletion will fail.
                storage.remove(geo)

                # If last point in geometry is the nearest
                # but prefer the first one if last point == first point
                # then reverse coordinates.
                if pt != geo.coords[0] and pt == geo.coords[-1]:
                    geo.coords = list(geo.coords)[::-1]

                #---------- Single depth/pass --------
                if not multidepth:
                    # G-code
                    # Note: self.linear2gcode() and self.point2gcode() will
                    # lower and raise the tool every time.
                    if type(geo) == LineString or type(geo) == LinearRing:
                        self.gcode += self.linear2gcode(geo, tolerance=tolerance)
                    elif type(geo) == Point:
                        self.gcode += self.point2gcode(geo)
                    else:
                        log.warning("G-code generation not implemented for %s" % (str(type(geo))))

                #--------- Multi-pass ---------
                else:
                    if isinstance(self.z_cut, Decimal):
                        z_cut = self.z_cut
                    else:
                        z_cut = Decimal(self.z_cut).quantize(Decimal('0.000000001'))

                    if depthpercut is None:
                        depthpercut = z_cut
                    elif not isinstance(depthpercut, Decimal):
                        depthpercut = Decimal(depthpercut).quantize(Decimal('0.000000001'))

                    depth = 0
                    reverse = False
                    while depth > z_cut:

                        # Increase depth. Limit to z_cut.
                        depth -= depthpercut
                        if depth < z_cut:
                            depth = z_cut

                        # Cut at specific depth and do not lift the tool.
                        # Note: linear2gcode() will use G00 to move to the
                        # first point in the path, but it should be already
                        # at the first point if the tool is down (in the material).
                        # So, an extra G00 should show up but is inconsequential.
                        if type(geo) == LineString or type(geo) == LinearRing:
                            self.gcode += self.linear2gcode(geo, tolerance=tolerance,
                                                            zcut=depth,
                                                            up=False)

                        # Ignore multi-pass for points.
                        elif type(geo) == Point:
                            self.gcode += self.point2gcode(geo)
                            break  # Ignoring ...

                        else:
                            log.warning("G-code generation not implemented for %s" % (str(type(geo))))

                        # Reverse coordinates if not a loop so we can continue
                        # cutting without returning to the beginhing.
                        if type(geo) == LineString:
                            geo.coords = list(geo.coords)[::-1]
                            reverse = True

                    # If geometry is reversed, revert.
                    if reverse:
                        if type(geo) == LineString:
                            geo.coords = list(geo.coords)[::-1]

                    # Lift the tool
                    self.gcode += "G00 Z%.4f\n" % self.z_move
                    # self.gcode += "( End of path. )\n"

                # Did deletion at the beginning.
                # Delete from index, update current location and continue.
                #rti.delete(hits[0], geo.coords[0])
                #rti.delete(hits[0], geo.coords[-1])

                current_pt = geo.coords[-1]

                # Next
                pt, geo = storage.nearest(current_pt)

        except StopIteration:  # Nothing found in storage.
            pass

        log.debug("%s paths traced." % path_count)

        # Finish
        self.gcode += "G00 Z%.4f\n" % self.z_move  # Stop cutting
        self.gcode += "G00 X0Y0\n"
        self.gcode += "M05\n"  # Spindle stop

    @staticmethod
    def codes_split(gline):
        """
        Parses a line of G-Code such as "G01 X1234 Y987" into
        a dictionary: {'G': 1.0, 'X': 1234.0, 'Y': 987.0}

        :param gline: G-Code line string
        :return: Dictionary with parsed line.
        """

        command = {}

        match = re.search(r'^\s*([A-Z])\s*([\+\-\.\d\s]+)', gline)
        while match:
            command[match.group(1)] = float(match.group(2).replace(" ", ""))
            gline = gline[match.end():]
            match = re.search(r'^\s*([A-Z])\s*([\+\-\.\d\s]+)', gline)

        return command

    def gcode_parse(self):
        """
        G-Code parser (from self.gcode). Generates dictionary with
        single-segment LineString's and "kind" indicating cut or travel,
        fast or feedrate speed.
        """

        kind = ["C", "F"]  # T=travel, C=cut, F=fast, S=slow

        # Results go here
        geometry = []        

        # Last known instruction
        current = {'X': 0.0, 'Y': 0.0, 'Z': 0.0, 'G': 0}

        # Current path: temporary storage until tool is
        # lifted or lowered.
        path = [(0, 0)]

        # Process every instruction
        for line in StringIO(self.gcode):

            gobj = self.codes_split(line)

            ## Units
            if 'G' in gobj and (gobj['G'] == 20.0 or gobj['G'] == 21.0):
                self.units = {20.0: "IN", 21.0: "MM"}[gobj['G']]
                continue

            ## Changing height
            if 'Z' in gobj:
                if ('X' in gobj or 'Y' in gobj) and gobj['Z'] != current['Z']:
                    log.warning("Non-orthogonal motion: From %s" % str(current))
                    log.warning("  To: %s" % str(gobj))
                current['Z'] = gobj['Z']
                # Store the path into geometry and reset path
                if len(path) > 1:
                    geometry.append({"geom": LineString(path),
                                     "kind": kind})
                    path = [path[-1]]  # Start with the last point of last path.

            if 'G' in gobj:
                current['G'] = int(gobj['G'])
                
            if 'X' in gobj or 'Y' in gobj:
                
                if 'X' in gobj:
                    x = gobj['X']
                else:
                    x = current['X']
                
                if 'Y' in gobj:
                    y = gobj['Y']
                else:
                    y = current['Y']

                kind = ["C", "F"]  # T=travel, C=cut, F=fast, S=slow

                if current['Z'] > 0:
                    kind[0] = 'T'
                if current['G'] > 0:
                    kind[1] = 'S'
                   
                arcdir = [None, None, "cw", "ccw"]
                if current['G'] in [0, 1]:  # line
                    path.append((x, y))

                if current['G'] in [2, 3]:  # arc
                    center = [gobj['I'] + current['X'], gobj['J'] + current['Y']]
                    radius = sqrt(gobj['I']**2 + gobj['J']**2)
                    start = arctan2(-gobj['J'], -gobj['I'])
                    stop = arctan2(-center[1] + y, -center[0] + x)
                    path += arc(center, radius, start, stop,
                                arcdir[current['G']],
                                self.steps_per_circ)

            # Update current instruction
            for code in gobj:
                current[code] = gobj[code]

        # There might not be a change in height at the
        # end, therefore, see here too if there is
        # a final path.
        if len(path) > 1:
            geometry.append({"geom": LineString(path),
                             "kind": kind})

        self.gcode_parsed = geometry
        return geometry

    # def plot(self, tooldia=None, dpi=75, margin=0.1,
    #          color={"T": ["#F0E24D", "#B5AB3A"], "C": ["#5E6CFF", "#4650BD"]},
    #          alpha={"T": 0.3, "C": 1.0}):
    #     """
    #     Creates a Matplotlib figure with a plot of the
    #     G-code job.
    #     """
    #     if tooldia is None:
    #         tooldia = self.tooldia
    #
    #     fig = Figure(dpi=dpi)
    #     ax = fig.add_subplot(111)
    #     ax.set_aspect(1)
    #     xmin, ymin, xmax, ymax = self.input_geometry_bounds
    #     ax.set_xlim(xmin-margin, xmax+margin)
    #     ax.set_ylim(ymin-margin, ymax+margin)
    #
    #     if tooldia == 0:
    #         for geo in self.gcode_parsed:
    #             linespec = '--'
    #             linecolor = color[geo['kind'][0]][1]
    #             if geo['kind'][0] == 'C':
    #                 linespec = 'k-'
    #             x, y = geo['geom'].coords.xy
    #             ax.plot(x, y, linespec, color=linecolor)
    #     else:
    #         for geo in self.gcode_parsed:
    #             poly = geo['geom'].buffer(tooldia/2.0)
    #             patch = PolygonPatch(poly, facecolor=color[geo['kind'][0]][0],
    #                                  edgecolor=color[geo['kind'][0]][1],
    #                                  alpha=alpha[geo['kind'][0]], zorder=2)
    #             ax.add_patch(patch)
    #
    #     return fig
        
    def plot2(self, tooldia=None, dpi=75, margin=0.1,
              color={"T": ["#F0E24D4C", "#B5AB3A4C"], "C": ["#5E6CFFFF", "#4650BDFF"]},
              alpha={"T": 0.3, "C": 1.0}, tool_tolerance=0.0005, obj=None, visible=False):
        """
        Plots the G-code job onto the given axes.

        :param tooldia: Tool diameter.
        :param dpi: Not used!
        :param margin: Not used!
        :param color: Color specification.
        :param alpha: Transparency specification.
        :param tool_tolerance: Tolerance when drawing the toolshape.
        :return: None
        """
        path_num = 0

        if tooldia is None:
            tooldia = self.tooldia
        
        if tooldia == 0:
            for geo in self.gcode_parsed:
                obj.add_shape(shape=geo['geom'], color=color[geo['kind'][0]][1], visible=visible)
        else:
            text = []
            pos = []
            for geo in self.gcode_parsed:
                path_num += 1

                text.append(str(path_num))
                pos.append(geo['geom'].coords[0])

                poly = geo['geom'].buffer(tooldia / 2.0).simplify(tool_tolerance)
                obj.add_shape(shape=poly, color=color[geo['kind'][0]][1], face_color=color[geo['kind'][0]][0],
                              visible=visible, layer=1 if geo['kind'][0] == 'C' else 2)

            obj.annotation.set(text=text, pos=pos, visible=obj.options['plot'])

    def create_geometry(self):
        # TODO: This takes forever. Too much data?
#        self.solid_geometry = cascaded_union([geo['geom'] for geo in self.gcode_parsed])
        self.solid_geometry = unary_union([geo['geom'] for geo in self.gcode_parsed])

    def linear2gcode(self, linear, tolerance=0, down=True, up=True,
                     zcut=None, ztravel=None, downrate=None,
                     feedrate=None, cont=False):
        """
        Generates G-code to cut along the linear feature.

        :param linear: The path to cut along.
        :type: Shapely.LinearRing or Shapely.Linear String
        :param tolerance: All points in the simplified object will be within the
            tolerance distance of the original geometry.
        :type tolerance: float
        :return: G-code to cut along the linear feature.
        :rtype: str
        """

        if zcut is None:
            zcut = self.z_cut

        if ztravel is None:
            ztravel = self.z_move

        if downrate is None:
            downrate = self.zdownrate

        if feedrate is None:
            feedrate = self.feedrate

        t = "G0%d " + CNCjob.defaults["coordinate_format"] + "\n"

        # Simplify paths?
        if tolerance > 0:
            target_linear = linear.simplify(tolerance)
        else:
            target_linear = linear

        gcode = ""

        path = list(target_linear.coords)

        # Move fast to 1st point
        if not cont:
            gcode += t % (0, path[0][0], path[0][1])  # Move to first point

        # Move down to cutting depth
        if down:
            # Different feedrate for vertical cut?
            if self.zdownrate is not None:
                gcode += "F%.2f\n" % downrate
                gcode += "G01 Z%.4f\n" % zcut       # Start cutting
                gcode += "F%.2f\n" % feedrate       # Restore feedrate
            else:
                gcode += "G01 Z%.4f\n" % zcut       # Start cutting

        # Cutting...
        for pt in path[1:]:
            gcode += t % (1, pt[0], pt[1])    # Linear motion to point

        # Up to travelling height.
        if up:
            gcode += "G00 Z%.4f\n" % ztravel  # Stop cutting

        return gcode

    def point2gcode(self, point):
        gcode = ""
        #t = "G0%d X%.4fY%.4f\n"
        t = "G0%d " + CNCjob.defaults["coordinate_format"] + "\n"
        path = list(point.coords)
        gcode += t % (0, path[0][0], path[0][1])  # Move to first point

        if self.zdownrate is not None:
            gcode += "F%.2f\n" % self.zdownrate
            gcode += "G01 Z%.4f\n" % self.z_cut       # Start cutting
            gcode += "F%.2f\n" % self.feedrate
        else:
            gcode += "G01 Z%.4f\n" % self.z_cut       # Start cutting

        gcode += "G00 Z%.4f\n" % self.z_move      # Stop cutting
        return gcode

    def scale(self, factor):
        """
        Scales all the geometry on the XY plane in the object by the
        given factor. Tool sizes, feedrates, or Z-axis dimensions are
        not altered.

        :param factor: Number by which to scale the object.
        :type factor: float
        :return: None
        :rtype: None
        """

        for g in self.gcode_parsed:
            g['geom'] = affinity.scale(g['geom'], factor, factor, origin=(0, 0))

        self.create_geometry()

    def offset(self, vect):
        """
        Offsets all the geometry on the XY plane in the object by the
        given vector.

        :param vect: (x, y) offset vector.
        :type vect: tuple
        :return: None
        """
        dx, dy = vect

        for g in self.gcode_parsed:
            g['geom'] = affinity.translate(g['geom'], xoff=dx, yoff=dy)

        self.create_geometry()

    def export_svg(self, scale_factor=0.00):
        """
        Exports the CNC Job as a SVG Element

        :scale_factor: float
        :return: SVG Element string
        """
        # scale_factor is a multiplication factor for the SVG stroke-width used within shapely's svg export
        # If not specified then try and use the tool diameter
        # This way what is on screen will match what is outputed for the svg
        # This is quite a useful feature for svg's used with visicut

        if scale_factor <= 0:
            scale_factor = self.options['tooldia'] / 2

        # If still 0 then defailt to 0.05
        # This value appears to work for zooming, and getting the output svg line width
        # to match that viewed on screen with FlatCam
        if scale_factor == 0:
            scale_factor = 0.05

        # Seperate the list of cuts and travels into 2 distinct lists
        # This way we can add different formatting / colors to both
        cuts = []
        travels = []
        for g in self.gcode_parsed:
            if g['kind'][0] == 'C': cuts.append(g)
            if g['kind'][0] == 'T': travels.append(g)

        # Used to determine the overall board size
        self.solid_geometry = unary_union([geo['geom'] for geo in self.gcode_parsed])

        # Convert the cuts and travels into single geometry objects we can render as svg xml
        if travels:
            travelsgeom = unary_union([geo['geom'] for geo in travels])
        if cuts:
            cutsgeom = unary_union([geo['geom'] for geo in cuts])

        # Render the SVG Xml
        # The scale factor affects the size of the lines, and the stroke color adds different formatting for each set
        # It's better to have the travels sitting underneath the cuts for visicut
        svg_elem = ""
        if travels:
            svg_elem = travelsgeom.svg(scale_factor=scale_factor, stroke_color="#F0E24D")
        if cuts:
            svg_elem += cutsgeom.svg(scale_factor=scale_factor, stroke_color="#5E6CFF")

        return svg_elem
