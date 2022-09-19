from PyQt6.QtWidgets import QLabel, QFileDialog, QGridLayout, QPushButton
from shapely import affinity

from fcCamlib.geometry import Geometry
from FlatCAMObj import FlatCAMObj, ObjectDeleted
from GUIElements import FCCheckBox, IntEntry, LengthEntry, OptionalInputSection, RadioSet

from .base import ObjectUI
from .cncjob import FlatCAMCNCjob


class GeometryObjectUI(ObjectUI):
    """
    User interface for Geometry objects.
    """

    def __init__(self, parent=None):
        super().__init__(title='Geometry Object', 
            icon_file='share/geometry32.png', parent=parent)

        ## Plot options
        self.plot_options_label = QLabel("<b>Plot Options:</b>")
        self.custom_box.addWidget(self.plot_options_label)

        # Plot CB
        self.plot_cb = FCCheckBox(label='Plot')
        self.plot_cb.setToolTip(
            "Plot (show) this object."
        )
        self.custom_box.addWidget(self.plot_cb)

        #-----------------------------------
        # Create CNC Job
        #-----------------------------------
        self.cncjob_label = QLabel('<b>Create CNC Job:</b>')
        self.cncjob_label.setToolTip(
            "Create a CNC Job object\n"
            "tracing the contours of this\n"
            "Geometry object."
        )
        self.custom_box.addWidget(self.cncjob_label)

        grid1 = QGridLayout()
        self.custom_box.addLayout(grid1)

        cutzlabel = QLabel('Cut Z:')
        cutzlabel.setToolTip(
            "Cutting depth (negative)\n"
            "below the copper surface."
        )
        grid1.addWidget(cutzlabel, 0, 0)
        self.cutz_entry = LengthEntry()
        grid1.addWidget(self.cutz_entry, 0, 1)

        # Travel Z
        travelzlabel = QLabel('Travel Z:')
        travelzlabel.setToolTip(
            "Height of the tool when\n"
            "moving without cutting."
        )
        grid1.addWidget(travelzlabel, 1, 0)
        self.travelz_entry = LengthEntry()
        grid1.addWidget(self.travelz_entry, 1, 1)

        # Feedrate
        frlabel = QLabel('Feed Rate:')
        frlabel.setToolTip(
            "Cutting speed in the XY\n"
            "plane in units per minute"
        )
        grid1.addWidget(frlabel, 2, 0)
        self.cncfeedrate_entry = LengthEntry()
        grid1.addWidget(self.cncfeedrate_entry, 2, 1)

        # Tooldia
        tdlabel = QLabel('Tool dia:')
        tdlabel.setToolTip(
            "The diameter of the cutting\n"
            "tool (just for display)."
        )
        grid1.addWidget(tdlabel, 3, 0)
        self.cnctooldia_entry = LengthEntry()
        grid1.addWidget(self.cnctooldia_entry, 3, 1)

        # Spindlespeed
        spdlabel = QLabel('Spindle speed:')
        spdlabel.setToolTip(
            "Speed of the spindle\n"
            "in RPM (optional)"
        )
        grid1.addWidget(spdlabel, 4, 0)
        self.cncspindlespeed_entry = IntEntry(allow_empty=True)
        grid1.addWidget(self.cncspindlespeed_entry, 4, 1)

        # Multi-pass
        mpasslabel = QLabel('Multi-Depth:')
        mpasslabel.setToolTip(
            "Use multiple passes to limit\n"
            "the cut depth in each pass. Will\n"
            "cut multiple times until Cut Z is\n"
            "reached."
        )
        grid1.addWidget(mpasslabel, 5, 0)
        self.mpass_cb = FCCheckBox()
        grid1.addWidget(self.mpass_cb, 5, 1)

        maxdepthlabel = QLabel('Depth/pass:')
        maxdepthlabel.setToolTip(
            "Depth of each pass (positive)."
        )
        grid1.addWidget(maxdepthlabel, 6, 0)
        self.maxdepth_entry = LengthEntry()
        grid1.addWidget(self.maxdepth_entry, 6, 1)

        self.ois_mpass = OptionalInputSection(self.mpass_cb, [self.maxdepth_entry])

        # Button
        self.generate_cnc_button = QPushButton('Generate')
        self.generate_cnc_button.setToolTip(
            "Generate the CNC Job object."
        )
        self.custom_box.addWidget(self.generate_cnc_button)

        #------------------------------
        # Paint area
        #------------------------------
        self.paint_label = QLabel('<b>Paint Area:</b>')
        self.paint_label.setToolTip(
            "Creates tool paths to cover the\n"
            "whole area of a polygon (remove\n"
            "all copper). You will be asked\n"
            "to click on the desired polygon."
        )
        self.custom_box.addWidget(self.paint_label)

        grid2 = QGridLayout()
        self.custom_box.addLayout(grid2)

        # Tool dia
        ptdlabel = QLabel('Tool dia:')
        ptdlabel.setToolTip(
            "Diameter of the tool to\n"
            "be used in the operation."
        )
        grid2.addWidget(ptdlabel, 0, 0)

        self.painttooldia_entry = LengthEntry()
        grid2.addWidget(self.painttooldia_entry, 0, 1)

        # Overlap
        ovlabel = QLabel('Overlap:')
        ovlabel.setToolTip(
            "How much (fraction) of the tool\n"
            "width to overlap each tool pass."
        )
        grid2.addWidget(ovlabel, 1, 0)
        self.paintoverlap_entry = LengthEntry()
        grid2.addWidget(self.paintoverlap_entry, 1, 1)

        # Margin
        marginlabel = QLabel('Margin:')
        marginlabel.setToolTip(
            "Distance by which to avoid\n"
            "the edges of the polygon to\n"
            "be painted."
        )
        grid2.addWidget(marginlabel, 2, 0)
        self.paintmargin_entry = LengthEntry()
        grid2.addWidget(self.paintmargin_entry, 2, 1)

        # Method
        methodlabel = QLabel('Method:')
        methodlabel.setToolTip(
            "Algorithm to paint the polygon:<BR>"
            "<B>Standard</B>: Fixed step inwards.<BR>"
            "<B>Seed-based</B>: Outwards from seed."
        )
        grid2.addWidget(methodlabel, 3, 0)
        self.paintmethod_combo = RadioSet([
            {"label": "Standard", "value": "standard"},
            {"label": "Seed-based", "value": "seed"}
        ])
        grid2.addWidget(self.paintmethod_combo, 3, 1)

        # GO Button
        self.generate_paint_button = QPushButton('Generate')
        self.generate_paint_button.setToolTip(
            "After clicking here, click inside\n"
            "the polygon you wish to be painted.\n"
            "A new Geometry object with the tool\n"
            "paths will be created."
        )
        self.custom_box.addWidget(self.generate_paint_button)


class FlatCAMGeometry(FlatCAMObj, Geometry):
    """
    Geometric object not associated with a specific
    format.
    """

    ui_type = GeometryObjectUI

    @staticmethod
    def merge(geo_list, geo_final):
        """
        Merges the geometry of objects in geo_list into
        the geometry of geo_final.

        :param geo_list: List of FlatCAMGeometry Objects to join.
        :param geo_final: Destination FlatCAMGeometry object.
        :return: None
        """

        if geo_final.solid_geometry is None:
            geo_final.solid_geometry = []
        if type(geo_final.solid_geometry) is not list:
            geo_final.solid_geometry = [geo_final.solid_geometry]

        for geo in geo_list:

            # Expand lists
            if type(geo) is list:
                FlatCAMGeometry.merge(geo, geo_final)

            # If not list, just append
            else:
                geo_final.solid_geometry.append(geo.solid_geometry)

            # try:  # Iterable
            #     for shape in geo.solid_geometry:
            #         geo_final.solid_geometry.append(shape)
            #
            # except TypeError:  # Non-iterable
            #     geo_final.solid_geometry.append(geo.solid_geometry)

    def __init__(self, name):
        FlatCAMObj.__init__(self, name)
        Geometry.__init__(self)

        self.kind = "geometry"

        self.options.update({
            "plot": True,
            "cutz": -0.002,
            "travelz": 0.1,
            "feedrate": 5.0,
            "spindlespeed": None,
            "cnctooldia": 0.4 / 25.4,
            "painttooldia": 0.0625,
            "paintoverlap": 0.15,
            "paintmargin": 0.01,
            "paintmethod": "standard",
            "multidepth": False,
            "depthperpass": 0.002
        })

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind']

    def build_ui(self):
        FlatCAMObj.build_ui(self)
        self.app.ui.showSelectedTab()

    def set_ui(self, ui):
        FlatCAMObj.set_ui(self, ui)

        self.app.log.debug("FlatCAMGeometry.set_ui()")

        assert isinstance(self.ui, GeometryObjectUI), \
            "Expected a GeometryObjectUI, got %s" % type(self.ui)

        self.form_fields.update({
            "plot": self.ui.plot_cb,
            "cutz": self.ui.cutz_entry,
            "travelz": self.ui.travelz_entry,
            "feedrate": self.ui.cncfeedrate_entry,
            "spindlespeed": self.ui.cncspindlespeed_entry,
            "cnctooldia": self.ui.cnctooldia_entry,
            "painttooldia": self.ui.painttooldia_entry,
            "paintoverlap": self.ui.paintoverlap_entry,
            "paintmargin": self.ui.paintmargin_entry,
            "paintmethod": self.ui.paintmethod_combo,
            "multidepth": self.ui.mpass_cb,
            "depthperpass": self.ui.maxdepth_entry
        })

        # Fill form fields only on object create
        self.to_form()

        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)
        self.ui.generate_cnc_button.clicked.connect(self.on_generatecnc_button_click)
        self.ui.generate_paint_button.clicked.connect(self.on_paint_button_click)

    def on_paint_button_click(self, *args):
        self.app.report_usage("geometry_on_paint_button")

        self.app.info("Click inside the desired polygon.")
        self.read_form()
        tooldia = self.options["painttooldia"]
        overlap = self.options["paintoverlap"]

        # To be called after clicking on the plot.
        def doit(event):
            self.app.info("Painting polygon...")
            self.app.plotcanvas.vis_disconnect('mouse_release', doit)
            pos = self.app.plotcanvas.vispy_canvas.translate_coords(event.pos)
            self.paint_poly([pos[0], pos[1]], tooldia, overlap)

        self.app.plotcanvas.vis_connect('mouse_release', doit)

    def paint_poly(self, inside_pt, tooldia, overlap):

        # Which polygon.
        #poly = find_polygon(self.solid_geometry, inside_pt)
        poly = self.find_polygon(inside_pt)

        # No polygon?
        if poly is None:
            self.app.log.warning('No polygon found.')
            self.app.inform.emit('[warning] No polygon found.')
            return

        proc = self.app.proc_container.new("Painting polygon.")

        name = self.options["name"] + "_paint"

        # Initializes the new geometry object
        def gen_paintarea(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry), \
                "Initializer expected a FlatCAMGeometry, got %s" % type(geo_obj)
            #assert isinstance(app_obj, App)

            if self.options["paintmethod"] == "seed":
                cp = self.clear_polygon2(poly.buffer(-self.options["paintmargin"]),
                                         tooldia, overlap=overlap)

            else:
                cp = self.clear_polygon(poly.buffer(-self.options["paintmargin"]),
                                        tooldia, overlap=overlap)

            geo_obj.solid_geometry = list(cp.get_objects())
            geo_obj.options["cnctooldia"] = tooldia
            self.app.inform.emit("Done.")

        def job_thread(app_obj):
            try:
                app_obj.new_object("geometry", name, gen_paintarea)
            except Exception as e:
                proc.done()
                raise e
            proc.done()

        self.app.inform.emit("Polygon Paint started ...")

        # Promise object with the new name
        self.app.collection.promise(name)

        # Background
        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    def on_generatecnc_button_click(self, *args):
        self.app.report_usage("geometry_on_generatecnc_button")
        self.read_form()
        self.generatecncjob()

    def generatecncjob(self,
                       z_cut=None,
                       z_move=None,
                       feedrate=None,
                       tooldia=None,
                       outname=None,
                       spindlespeed=None,
                       multidepth=None,
                       depthperpass=None,
                       use_thread=True):
        """
        Creates a CNCJob out of this Geometry object. The actual
        work is done by the target FlatCAMCNCjob object's
        `generate_from_geometry_2()` method.

        :param z_cut: Cut depth (negative)
        :param z_move: Hight of the tool when travelling (not cutting)
        :param feedrate: Feed rate while cutting
        :param tooldia: Tool diameter
        :param outname: Name of the new object
        :param spindlespeed: Spindle speed (RPM)
        :return: None
        """

        outname = outname if outname is not None else self.options["name"] + "_cnc"
        z_cut = z_cut if z_cut is not None else self.options["cutz"]
        z_move = z_move if z_move is not None else self.options["travelz"]
        feedrate = feedrate if feedrate is not None else self.options["feedrate"]
        tooldia = tooldia if tooldia is not None else self.options["cnctooldia"]
        multidepth = multidepth if multidepth is not None else self.options["multidepth"]
        depthperpass = depthperpass if depthperpass is not None else self.options["depthperpass"]

        # To allow default value to be "" (optional in gui) and translate to None
        # if not isinstance(spindlespeed, int):
        #     if isinstance(self.options["spindlespeed"], int) or \
        #             isinstance(self.options["spindlespeed"], float):
        #         spindlespeed = int(self.options["spindlespeed"])
        #     else:
        #         spindlespeed = None

        if spindlespeed is None:
            # int or None.
            spindlespeed = self.options['spindlespeed']

        # Object initialization function for app.new_object()
        # RUNNING ON SEPARATE THREAD!
        def job_init(job_obj, app_obj):
            assert isinstance(job_obj, FlatCAMCNCjob), \
                "Initializer expected a FlatCAMCNCjob, got %s" % type(job_obj)

            # Propagate options
            job_obj.options["tooldia"] = tooldia

            app_obj.progress.emit(20)
            job_obj.z_cut = z_cut
            job_obj.z_move = z_move
            job_obj.feedrate = feedrate
            job_obj.spindlespeed = spindlespeed
            app_obj.progress.emit(40)
            # TODO: The tolerance should not be hard coded. Just for testing.
            job_obj.generate_from_geometry_2(self,
                                             multidepth=multidepth,
                                             depthpercut=depthperpass,
                                             tolerance=0.0005)

            app_obj.progress.emit(50)
            job_obj.gcode_parse()

            app_obj.progress.emit(80)

        if use_thread:
            # To be run in separate thread
            def job_thread(app_obj):
                with self.app.proc_container.new("Generating CNC Job."):
                    app_obj.new_object("cncjob", outname, job_init)
                    app_obj.inform.emit("CNCjob created: %s" % outname)
                    app_obj.progress.emit(100)

            # Create a promise with the name
            self.app.collection.promise(outname)

            # Send to worker
            self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})
        else:
            self.app.new_object("cncjob", outname, job_init)

    def on_plot_cb_click(self, *args):  # TODO: args not needed
        if self.muted_ui:
            return
        self.read_form_item('plot')

    def scale(self, factor):
        """
        Scales all geometry by a given factor.

        :param factor: Factor by which to scale the object's geometry/
        :type factor: float
        :return: None
        :rtype: None
        """

        if type(self.solid_geometry) == list:
            self.solid_geometry = [affinity.scale(g, factor, factor, origin=(0, 0))
                                   for g in self.solid_geometry]
        else:
            self.solid_geometry = affinity.scale(self.solid_geometry, factor, factor,
                                                 origin=(0, 0))

    def offset(self, vect):
        """
        Offsets all geometry by a given vector/

        :param vect: (x, y) vector by which to offset the object's geometry.
        :type vect: tuple
        :return: None
        :rtype: None
        """

        dx, dy = vect

        def translate_recursion(geom):
            if type(geom) == list:
                geoms=list()
                for local_geom in geom:
                    geoms.append(translate_recursion(local_geom))
                return geoms
            else:
                return  affinity.translate(geom, xoff=dx, yoff=dy)

        self.solid_geometry=translate_recursion(self.solid_geometry)

    def convert_units(self, units):
        factor = Geometry.convert_units(self, units)

        self.options['cutz'] *= factor
        self.options['travelz'] *= factor
        self.options['feedrate'] *= factor
        self.options['cnctooldia'] *= factor
        self.options['painttooldia'] *= factor
        self.options['paintmargin'] *= factor

        return factor

    def plot_element(self, element):
        try:
            for sub_el in element.geoms:
                self.plot_element(sub_el)

        except TypeError:  # Element is not iterable...
            self.add_shape(shape=element, color='red', visible=self.options['plot'], layer=0)

    def plot(self):
        """
        Adds the object into collection.

        :return: None
        """

        # Does all the required setup and returns False
        # if the 'ptint' option is set to False.
        if not FlatCAMObj.plot(self):
            return

        try:
            self.plot_element(self.solid_geometry)
            self.shapes.redraw()
        except (ObjectDeleted, AttributeError):
            self.shapes.clear(update=True)
