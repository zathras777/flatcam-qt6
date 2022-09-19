############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
############################################################

from shapely import affinity
from shapely.geometry import Polygon, LineString, Point, LinearRing
from shapely.geometry import MultiPoint, MultiPolygon
from shapely.geometry import box as shply_box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.wkt import loads as sloads
from shapely.wkt import dumps as sdumps

from .utils import setup_log

log = setup_log("fcCamlib.geometry")


class Geometry:
    """
    Base geometry class.
    """

    defaults = {
        "init_units": 'in'
    }

    def __init__(self):
        # Units (in or mm)
        self.units = Geometry.defaults["init_units"]
        
        # Final geometry: MultiPolygon or list (of geometry constructs)
        self.solid_geometry = None

        # Attributes to be included in serialization
        self.ser_attrs = ['units', 'solid_geometry']

        # Flattened geometry (list of paths only)
        self.flat_geometry = []

    def add_circle(self, origin, radius):
        """
        Adds a circle to the object.

        :param origin: Center of the circle.
        :param radius: Radius of the circle.
        :return: None
        """
        # TODO: Decide what solid_geometry is supposed to be and how we append to it.

        if self.solid_geometry is None:
            self.solid_geometry = []

        if type(self.solid_geometry) is list:
            self.solid_geometry.append(Point(origin).buffer(radius))
            return

        try:
            self.solid_geometry = self.solid_geometry.union(Point(origin).buffer(radius))
        except:
            #print "Failed to run union on polygons."
            log.error("Failed to run union on polygons.")
            raise

    def add_polygon(self, points):
        """
        Adds a polygon to the object (by union)

        :param points: The vertices of the polygon.
        :return: None
        """
        if self.solid_geometry is None:
            self.solid_geometry = []

        if type(self.solid_geometry) is list:
            self.solid_geometry.append(Polygon(points))
            return

        try:
            self.solid_geometry = self.solid_geometry.union(Polygon(points))
        except:
            #print "Failed to run union on polygons."
            log.error("Failed to run union on polygons.")
            raise

    def add_polyline(self, points):
        """
        Adds a polyline to the object (by union)

        :param points: The vertices of the polyline.
        :return: None
        """
        if self.solid_geometry is None:
            self.solid_geometry = []

        if type(self.solid_geometry) is list:
            self.solid_geometry.append(LineString(points))
            return

        try:
            self.solid_geometry = self.solid_geometry.union(LineString(points))
        except:
            #print "Failed to run union on polygons."
            log.error("Failed to run union on polylines.")
            raise

    def is_empty(self):

        if isinstance(self.solid_geometry, BaseGeometry):
            return self.solid_geometry.is_empty

        if isinstance(self.solid_geometry, list):
            return len(self.solid_geometry) == 0

        raise Exception("self.solid_geometry is neither BaseGeometry or list.")

    def subtract_polygon(self, points):
        """
        Subtract polygon from the given object. This only operates on the paths in the original geometry, i.e. it converts polygons into paths.

        :param points: The vertices of the polygon.
        :return: none
        """
        if self.solid_geometry is None:
            self.solid_geometry = []

        #pathonly should be allways True, otherwise polygons are not subtracted
        flat_geometry = self.flatten(pathonly=True)
        log.debug("%d paths" % len(flat_geometry))
        polygon=Polygon(points)
        toolgeo=cascaded_union(polygon)
        diffs=[]
        for target in flat_geometry:
            if type(target) == LineString or type(target) == LinearRing:
                diffs.append(target.difference(toolgeo))
            else:
                log.warning("Not implemented.")
        self.solid_geometry=cascaded_union(diffs)

    def bounds(self):
        """
        Returns coordinates of rectangular bounds
        of geometry: (xmin, ymin, xmax, ymax).
        """
        log.debug("Geometry->bounds()")
        if self.solid_geometry is None:
            log.debug("solid_geometry is None")
            return 0, 0, 0, 0

        if type(self.solid_geometry) is list:
            # TODO: This can be done faster. See comment from Shapely mailing lists.
            if len(self.solid_geometry) == 0:
                log.debug('solid_geometry is empty []')
                return 0, 0, 0, 0
            return cascaded_union(self.solid_geometry).bounds
        else:
            return self.solid_geometry.bounds

    def find_polygon(self, point, geoset=None):
        """
        Find an object that object.contains(Point(point)) in
        poly, which can can be iterable, contain iterable of, or
        be itself an implementer of .contains().

        :param poly: See description
        :return: Polygon containing point or None.
        """

        if geoset is None:
            geoset = self.solid_geometry

        try:  # Iterable
            for sub_geo in geoset:
                p = self.find_polygon(point, geoset=sub_geo)
                if p is not None:
                    return p

        except TypeError:  # Non-iterable

            try:  # Implements .contains()
                if geoset.contains(Point(point)):
                    return geoset

            except AttributeError:  # Does not implement .contains()
                return None

        return None

    def get_interiors(self, geometry=None):

        interiors = []

        if geometry is None:
            geometry = self.solid_geometry

        ## If iterable, expand recursively.
        try:
            for geo in geometry:
                interiors.extend(self.get_interiors(geometry=geo))

        ## Not iterable, get the exterior if polygon.
        except TypeError:
            if type(geometry) == Polygon:
                interiors.extend(geometry.interiors)

        return interiors

    def get_exteriors(self, geometry=None):
        """
        Returns all exteriors of polygons in geometry. Uses
        ``self.solid_geometry`` if geometry is not provided.

        :param geometry: Shapely type or list or list of list of such.
        :return: List of paths constituting the exteriors
           of polygons in geometry.
        """

        exteriors = []

        if geometry is None:
            geometry = self.solid_geometry

        ## If iterable, expand recursively.
        try:
            for geo in geometry:
                exteriors.extend(self.get_exteriors(geometry=geo))

        ## Not iterable, get the exterior if polygon.
        except TypeError:
            if type(geometry) == Polygon:
                exteriors.append(geometry.exterior)

        return exteriors

    def flatten(self, geometry=None, reset=True, pathonly=False):
        """
        Creates a list of non-iterable linear geometry objects.
        Polygons are expanded into its exterior and interiors if specified.

        Results are placed in self.flat_geoemtry

        :param geometry: Shapely type or list or list of list of such.
        :param reset: Clears the contents of self.flat_geometry.
        :param pathonly: Expands polygons into linear elements.
        """

        if geometry is None:
            geometry = self.solid_geometry

        if reset:
            self.flat_geometry = []

        ## If iterable, expand recursively.
        try:
            for geo in geometry.geoms:
                self.flatten(geometry=geo, reset=False, pathonly=pathonly)
        except AttributeError:
            if pathonly and type(geometry) == Polygon:
                self.flat_geometry.append(geometry.exterior)
                for interior in list(geometry.interiors):
                    self.flatten(geometry=interior, reset=False, pathonly=True)
            else:
                self.flat_geometry.append(geometry)

        ## Not iterable, do the actual indexing and add.
        except TypeError:
            if pathonly and type(geometry) == Polygon:
                self.flat_geometry.append(geometry.exterior)
                self.flatten(geometry=geometry.interiors,
                             reset=False,
                             pathonly=True)
            else:
                self.flat_geometry.append(geometry.geoms)

        return self.flat_geometry

    # def make2Dstorage(self):
    #
    #     self.flatten()
    #
    #     def get_pts(o):
    #         pts = []
    #         if type(o) == Polygon:
    #             g = o.exterior
    #             pts += list(g.coords)
    #             for i in o.interiors:
    #                 pts += list(i.coords)
    #         else:
    #             pts += list(o.coords)
    #         return pts
    #
    #     storage = FlatCAMRTreeStorage()
    #     storage.get_points = get_pts
    #     for shape in self.flat_geometry:
    #         storage.insert(shape)
    #     return storage

    # def flatten_to_paths(self, geometry=None, reset=True):
    #     """
    #     Creates a list of non-iterable linear geometry elements and
    #     indexes them in rtree.
    #
    #     :param geometry: Iterable geometry
    #     :param reset: Wether to clear (True) or append (False) to self.flat_geometry
    #     :return: self.flat_geometry, self.flat_geometry_rtree
    #     """
    #
    #     if geometry is None:
    #         geometry = self.solid_geometry
    #
    #     if reset:
    #         self.flat_geometry = []
    #
    #     ## If iterable, expand recursively.
    #     try:
    #         for geo in geometry:
    #             self.flatten_to_paths(geometry=geo, reset=False)
    #
    #     ## Not iterable, do the actual indexing and add.
    #     except TypeError:
    #         if type(geometry) == Polygon:
    #             g = geometry.exterior
    #             self.flat_geometry.append(g)
    #
    #             ## Add first and last points of the path to the index.
    #             self.flat_geometry_rtree.insert(len(self.flat_geometry) - 1, g.coords[0])
    #             self.flat_geometry_rtree.insert(len(self.flat_geometry) - 1, g.coords[-1])
    #
    #             for interior in geometry.interiors:
    #                 g = interior
    #                 self.flat_geometry.append(g)
    #                 self.flat_geometry_rtree.insert(len(self.flat_geometry) - 1, g.coords[0])
    #                 self.flat_geometry_rtree.insert(len(self.flat_geometry) - 1, g.coords[-1])
    #         else:
    #             g = geometry
    #             self.flat_geometry.append(g)
    #             self.flat_geometry_rtree.insert(len(self.flat_geometry) - 1, g.coords[0])
    #             self.flat_geometry_rtree.insert(len(self.flat_geometry) - 1, g.coords[-1])
    #
    #     return self.flat_geometry, self.flat_geometry_rtree

    def isolation_geometry(self, offset):
        """
        Creates contours around geometry at a given
        offset distance.

        :param offset: Offset distance.
        :type offset: float
        :return: The buffered geometry.
        :rtype: Shapely.MultiPolygon or Shapely.Polygon
        """
        return self.solid_geometry.buffer(offset)

    def import_svg(self, filename, flip=True):
        """
        Imports shapes from an SVG file into the object's geometry.

        :param filename: Path to the SVG file.
        :type filename: str
        :return: None
        """

        # Parse into list of shapely objects
        svg_tree = ET.parse(filename)
        svg_root = svg_tree.getroot()

        # Change origin to bottom left
        # h = float(svg_root.get('height'))
        # w = float(svg_root.get('width'))
        h = svgparselength(svg_root.get('height'))[0]  # TODO: No units support yet
        geos = getsvggeo(svg_root)

        if flip:
            geos = [translate(scale(g, 1.0, -1.0, origin=(0, 0)), yoff=h) for g in geos]

        # Add to object
        if self.solid_geometry is None:
            self.solid_geometry = []

        if type(self.solid_geometry) is list:
            self.solid_geometry.append(unary_union(geos))
        else:  # It's shapely geometry
            self.solid_geometry = unary_union([self.solid_geometry,
                                               unary_union(geos)])

        return

    def import_dxf(self, filename, object_type=None, units='MM'):
        """
        Imports shapes from an DXF file into the object's geometry.

        :param filename: Path to the DXF file.
        :type filename: str
        :param units: Application units
        :type flip: str
        :return: None
        """

        # Parse into list of shapely objects
        dxf = ezdxf.readfile(filename)
        geos = getdxfgeo(dxf)

        # Add to object
        if self.solid_geometry is None:
            self.solid_geometry = []

        if type(self.solid_geometry) is list:
            if type(geos) is list:
                self.solid_geometry += geos
            else:
                self.solid_geometry.append(geos)
        else:  # It's shapely geometry
            self.solid_geometry = [self.solid_geometry, geos]

        # flatten the self.solid_geometry list for import_dxf() to import DXF as Gerber
        self.solid_geometry = list(self.flatten_list(self.solid_geometry))
        if self.solid_geometry is not None:
            self.solid_geometry = unary_union(self.solid_geometry)
        else:
            return

        # commented until this function is ready
        # geos_text = getdxftext(dxf, object_type, units=units)
        # if geos_text is not None:
        #     geos_text_f = []
        #     self.solid_geometry = [self.solid_geometry, geos_text_f]

    def size(self):
        """
        Returns (width, height) of rectangular
        bounds of geometry.
        """
        if self.solid_geometry is None:
            log.warning("Solid_geometry not computed yet.")
            return 0
        bounds = self.bounds()
        return bounds[2] - bounds[0], bounds[3] - bounds[1]
        
    def get_empty_area(self, boundary=None):
        """
        Returns the complement of self.solid_geometry within
        the given boundary polygon. If not specified, it defaults to
        the rectangular bounding box of self.solid_geometry.
        """
        if boundary is None:
            boundary = self.solid_geometry.envelope
        return boundary.difference(self.solid_geometry)
        
    @staticmethod
    def clear_polygon(polygon, tooldia, overlap=0.15):
        """
        Creates geometry inside a polygon for a tool to cover
        the whole area.

        This algorithm shrinks the edges of the polygon and takes
        the resulting edges as toolpaths.

        :param polygon: Polygon to clear.
        :param tooldia: Diameter of the tool.
        :param overlap: Overlap of toolpasses.
        :return:
        """

        log.debug("camlib.clear_polygon()")
        assert type(polygon) == Polygon or type(polygon) == MultiPolygon, \
            "Expected a Polygon or MultiPolygon, got %s" % type(polygon)

        ## The toolpaths
        # Index first and last points in paths
        def get_pts(o):
            return [o.coords[0], o.coords[-1]]
        geoms = FlatCAMRTreeStorage()
        geoms.get_points = get_pts

        # Can only result in a Polygon or MultiPolygon
        current = polygon.buffer(-tooldia / 2.0)

        # current can be a MultiPolygon
        try:
            for p in current:
                geoms.insert(p.exterior)
                for i in p.interiors:
                    geoms.insert(i)

        # Not a Multipolygon. Must be a Polygon
        except TypeError:
            geoms.insert(current.exterior)
            for i in current.interiors:
                geoms.insert(i)

        while True:

            # Can only result in a Polygon or MultiPolygon
            current = current.buffer(-tooldia * (1 - overlap))
            if current.area > 0:

                # current can be a MultiPolygon
                try:
                    for p in current:
                        geoms.insert(p.exterior)
                        for i in p.interiors:
                            geoms.insert(i)

                # Not a Multipolygon. Must be a Polygon
                except TypeError:
                    geoms.insert(current.exterior)
                    for i in current.interiors:
                        geoms.insert(i)
            else:
                break

        # Optimization: Reduce lifts
        log.debug("Reducing tool lifts...")
        geoms = Geometry.paint_connect(geoms, polygon, tooldia)

        return geoms

    @staticmethod
    def clear_polygon2(polygon, tooldia, seedpoint=None, overlap=0.15):
        """
        Creates geometry inside a polygon for a tool to cover
        the whole area.

        This algorithm starts with a seed point inside the polygon
        and draws circles around it. Arcs inside the polygons are
        valid cuts. Finalizes by cutting around the inside edge of
        the polygon.

        :param polygon: Shapely.geometry.Polygon
        :param tooldia: Diameter of the tool
        :param seedpoint: Shapely.geometry.Point or None
        :param overlap: Tool fraction overlap bewteen passes
        :return: List of toolpaths covering polygon.
        """

        log.debug("camlib.clear_polygon2()")

        # Current buffer radius
        radius = tooldia / 2 * (1 - overlap)

        ## The toolpaths
        # Index first and last points in paths
        def get_pts(o):
            return [o.coords[0], o.coords[-1]]
        geoms = FlatCAMRTreeStorage()
        geoms.get_points = get_pts

        # Path margin
        path_margin = polygon.buffer(-tooldia / 2)

        # Estimate good seedpoint if not provided.
        if seedpoint is None:
            seedpoint = path_margin.representative_point()

        # Grow from seed until outside the box. The polygons will
        # never have an interior, so take the exterior LinearRing.
        while 1:
            path = Point(seedpoint).buffer(radius).exterior
            path = path.intersection(path_margin)

            # Touches polygon?
            if path.is_empty:
                break
            else:
                #geoms.append(path)
                #geoms.insert(path)
                # path can be a collection of paths.
                try:
                    for p in path:
                        geoms.insert(p)
                except TypeError:
                    geoms.insert(path)

            radius += tooldia * (1 - overlap)

        # Clean inside edges of the original polygon
        outer_edges = [x.exterior for x in autolist(polygon.buffer(-tooldia / 2))]
        inner_edges = []
        for x in autolist(polygon.buffer(-tooldia / 2)):  # Over resulting polygons
            for y in x.interiors:  # Over interiors of each polygon
                inner_edges.append(y)
        #geoms += outer_edges + inner_edges
        for g in outer_edges + inner_edges:
            geoms.insert(g)

        # Optimization connect touching paths
        # log.debug("Connecting paths...")
        # geoms = Geometry.path_connect(geoms)

        # Optimization: Reduce lifts
        log.debug("Reducing tool lifts...")
        geoms = Geometry.paint_connect(geoms, polygon, tooldia)

        return geoms

    def scale(self, factor):
        """
        Scales all of the object's geometry by a given factor. Override
        this method.
        :param factor: Number by which to scale.
        :type factor: float
        :return: None
        :rtype: None
        """
        return

    def offset(self, vect):
        """
        Offset the geometry by the given vector. Override this method.

        :param vect: (x, y) vector by which to offset the object.
        :type vect: tuple
        :return: None
        """
        return

    @staticmethod
    def paint_connect(storage, boundary, tooldia, max_walk=None):
        """
        Connects paths that results in a connection segment that is
        within the paint area. This avoids unnecessary tool lifting.

        :param storage: Geometry to be optimized.
        :type storage: FlatCAMRTreeStorage
        :param boundary: Polygon defining the limits of the paintable area.
        :type boundary: Polygon
        :param max_walk: Maximum allowable distance without lifting tool.
        :type max_walk: float or None
        :return: Optimized geometry.
        :rtype: FlatCAMRTreeStorage
        """

        # If max_walk is not specified, the maximum allowed is
        # 10 times the tool diameter
        max_walk = max_walk or 10 * tooldia

        # Assuming geolist is a flat list of flat elements

        ## Index first and last points in paths
        def get_pts(o):
            return [o.coords[0], o.coords[-1]]

        # storage = FlatCAMRTreeStorage()
        # storage.get_points = get_pts
        #
        # for shape in geolist:
        #     if shape is not None:  # TODO: This shouldn't have happened.
        #         # Make LlinearRings into linestrings otherwise
        #         # When chaining the coordinates path is messed up.
        #         storage.insert(LineString(shape))
        #         #storage.insert(shape)

        ## Iterate over geometry paths getting the nearest each time.
        #optimized_paths = []
        optimized_paths = FlatCAMRTreeStorage()
        optimized_paths.get_points = get_pts
        path_count = 0
        current_pt = (0, 0)
        pt, geo = storage.nearest(current_pt)
        storage.remove(geo)
        geo = LineString(geo)
        current_pt = geo.coords[-1]
        try:
            while True:
                path_count += 1
                #log.debug("Path %d" % path_count)

                pt, candidate = storage.nearest(current_pt)
                storage.remove(candidate)
                candidate = LineString(candidate)

                # If last point in geometry is the nearest
                # then reverse coordinates.
                # but prefer the first one if last == first
                if pt != candidate.coords[0] and pt == candidate.coords[-1]:
                    candidate.coords = list(candidate.coords)[::-1]

                # Straight line from current_pt to pt.
                # Is the toolpath inside the geometry?
                walk_path = LineString([current_pt, pt])
                walk_cut = walk_path.buffer(tooldia / 2)

                if walk_cut.within(boundary) and walk_path.length < max_walk:
                    #log.debug("Walk to path #%d is inside. Joining." % path_count)

                    # Completely inside. Append...
                    geo.coords = list(geo.coords) + list(candidate.coords)
                    # try:
                    #     last = optimized_paths[-1]
                    #     last.coords = list(last.coords) + list(geo.coords)
                    # except IndexError:
                    #     optimized_paths.append(geo)

                else:

                    # Have to lift tool. End path.
                    #log.debug("Path #%d not within boundary. Next." % path_count)
                    #optimized_paths.append(geo)
                    optimized_paths.insert(geo)
                    geo = candidate

                current_pt = geo.coords[-1]

                # Next
                #pt, geo = storage.nearest(current_pt)

        except StopIteration:  # Nothing left in storage.
            #pass
            optimized_paths.insert(geo)

        return optimized_paths

    @staticmethod
    def path_connect(storage, origin=(0, 0)):
        """

        :return: None
        """

        log.debug("path_connect()")

        ## Index first and last points in paths
        def get_pts(o):
            return [o.coords[0], o.coords[-1]]
        #
        # storage = FlatCAMRTreeStorage()
        # storage.get_points = get_pts
        #
        # for shape in pathlist:
        #     if shape is not None:  # TODO: This shouldn't have happened.
        #         storage.insert(shape)

        path_count = 0
        pt, geo = storage.nearest(origin)
        storage.remove(geo)
        #optimized_geometry = [geo]
        optimized_geometry = FlatCAMRTreeStorage()
        optimized_geometry.get_points = get_pts
        #optimized_geometry.insert(geo)
        try:
            while True:
                path_count += 1

                #print "geo is", geo

                _, left = storage.nearest(geo.coords[0])
                #print "left is", left

                # If left touches geo, remove left from original
                # storage and append to geo.
                if type(left) == LineString:
                    if left.coords[0] == geo.coords[0]:
                        storage.remove(left)
                        geo.coords = list(geo.coords)[::-1] + list(left.coords)
                        continue

                    if left.coords[-1] == geo.coords[0]:
                        storage.remove(left)
                        geo.coords = list(left.coords) + list(geo.coords)
                        continue

                    if left.coords[0] == geo.coords[-1]:
                        storage.remove(left)
                        geo.coords = list(geo.coords) + list(left.coords)
                        continue

                    if left.coords[-1] == geo.coords[-1]:
                        storage.remove(left)
                        geo.coords = list(geo.coords) + list(left.coords)[::-1]
                        continue

                _, right = storage.nearest(geo.coords[-1])
                #print "right is", right

                # If right touches geo, remove left from original
                # storage and append to geo.
                if type(right) == LineString:
                    if right.coords[0] == geo.coords[-1]:
                        storage.remove(right)
                        geo.coords = list(geo.coords) + list(right.coords)
                        continue

                    if right.coords[-1] == geo.coords[-1]:
                        storage.remove(right)
                        geo.coords = list(geo.coords) + list(right.coords)[::-1]
                        continue

                    if right.coords[0] == geo.coords[0]:
                        storage.remove(right)
                        geo.coords = list(geo.coords)[::-1] + list(right.coords)
                        continue

                    if right.coords[-1] == geo.coords[0]:
                        storage.remove(right)
                        geo.coords = list(left.coords) + list(geo.coords)
                        continue

                # right is either a LinearRing or it does not connect
                # to geo (nothing left to connect to geo), so we continue
                # with right as geo.
                storage.remove(right)

                if type(right) == LinearRing:
                    optimized_geometry.insert(right)
                else:
                    # Cannot exteng geo any further. Put it away.
                    optimized_geometry.insert(geo)

                    # Continue with right.
                    geo = right

        except StopIteration:  # Nothing found in storage.
            optimized_geometry.insert(geo)

        #print path_count
        log.debug("path_count = %d" % path_count)

        return optimized_geometry

    def convert_units(self, units):
        """
        Converts the units of the object to ``units`` by scaling all
        the geometry appropriately. This call ``scale()``. Don't call
        it again in descendents.

        :param units: "IN" or "MM"
        :type units: str
        :return: Scaling factor resulting from unit change.
        :rtype: float
        """
        log.debug("Geometry.convert_units()")

        if units.upper() == self.units.upper():
            return 1.0

        if units.upper() == "MM":
            factor = 25.4
        elif units.upper() == "IN":
            factor = 1 / 25.4
        else:
            log.error("Unsupported units: %s" % str(units))
            return 1.0

        self.units = units
        self.scale(factor)
        return factor

    def to_dict(self):
        """
        Returns a respresentation of the object as a dictionary.
        Attributes to include are listed in ``self.ser_attrs``.

        :return: A dictionary-encoded copy of the object.
        :rtype: dict
        """
        d = {}
        for attr in self.ser_attrs:
            d[attr] = getattr(self, attr)
        return d

    def from_dict(self, d):
        """
        Sets object's attributes from a dictionary.
        Attributes to include are listed in ``self.ser_attrs``.
        This method will look only for only and all the
        attributes in ``self.ser_attrs``. They must all
        be present. Use only for deserializing saved
        objects.

        :param d: Dictionary of attributes to set in the object.
        :type d: dict
        :return: None
        """
        for attr in self.ser_attrs:
            setattr(self, attr, d[attr])

    def union(self):
        """
        Runs a cascaded union on the list of objects in
        solid_geometry.

        :return: None
        """
        self.solid_geometry = [unary_union(self.solid_geometry)]

    def export_svg(self, scale_factor=0.00):
        """
        Exports the Gemoetry Object as a SVG Element

        :return: SVG Element
        """
        # Make sure we see a Shapely Geometry class and not a list
        geom = cascaded_union(self.flatten())

        # scale_factor is a multiplication factor for the SVG stroke-width used within shapely's svg export

        # If 0 or less which is invalid then default to 0.05
        # This value appears to work for zooming, and getting the output svg line width
        # to match that viewed on screen with FlatCam
        if scale_factor <= 0:
            scale_factor = 0.05

        # Convert to a SVG
        svg_elem = geom.svg(scale_factor=scale_factor)
        return svg_elem

    def mirror(self, axis, point):
        """
        Mirrors the object around a specified axis passign through
        the given point.

        :param axis: "X" or "Y" indicates around which axis to mirror.
        :type axis: str
        :param point: [x, y] point belonging to the mirror axis.
        :type point: list
        :return: None
        """

        px, py = point
        xscale, yscale = {"X": (1.0, -1.0), "Y": (-1.0, 1.0)}[axis]

        ## solid_geometry ???
        #  It's a cascaded union of objects.
        self.solid_geometry = affinity.scale(self.solid_geometry,
                                             xscale, yscale, origin=(px, py))
