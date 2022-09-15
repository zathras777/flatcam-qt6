import inspect

from PyQt6.QtWidgets import QLabel, QGridLayout, QPushButton
from shapely.geometry import Polygon, MultiPolygon

from FlatCAMObj import FlatCAMObj
from ObjectUI import ObjectUI
from camlib import Gerber

from GUIElements import FCEntry, FloatEntry, FCCheckBox, \
    LengthEntry, IntEntry, RadioSet


class GerberObjectUI(ObjectUI):
    """
    User interface for Gerber objects.
    """

    def __init__(self, parent=None):
        ObjectUI.__init__(self, title='Gerber Object', parent=parent)

        ## Plot options
        self.plot_options_label = QLabel("<b>Plot Options:</b>")
        self.custom_box.addWidget(self.plot_options_label)

        grid0 = QGridLayout()
        self.custom_box.addLayout(grid0)
        # Plot CB
        self.plot_cb = FCCheckBox(label='Plot')
        self.plot_options_label.setToolTip(
            "Plot (show) this object."
        )
        grid0.addWidget(self.plot_cb, 0, 0)

        # Solid CB
        self.solid_cb = FCCheckBox(label='Solid')
        self.solid_cb.setToolTip(
            "Solid color polygons."
        )
        grid0.addWidget(self.solid_cb, 0, 1)

        # Multicolored CB
        self.multicolored_cb = FCCheckBox(label='Multicolored')
        self.multicolored_cb.setToolTip(
            "Draw polygons in different colors."
        )
        grid0.addWidget(self.multicolored_cb, 0, 2)

        ## Isolation Routing
        self.isolation_routing_label = QLabel("<b>Isolation Routing:</b>")
        self.isolation_routing_label.setToolTip(
            "Create a Geometry object with\n"
            "toolpaths to cut outside polygons."
        )
        self.custom_box.addWidget(self.isolation_routing_label)

        grid1 = QGridLayout()
        self.custom_box.addLayout(grid1)
        tdlabel = QLabel('Tool dia:')
        tdlabel.setToolTip(
            "Diameter of the cutting tool."
        )
        grid1.addWidget(tdlabel, 0, 0)
        self.iso_tool_dia_entry = LengthEntry()
        grid1.addWidget(self.iso_tool_dia_entry, 0, 1)

        passlabel = QLabel('Width (# passes):')
        passlabel.setToolTip(
            "Width of the isolation gap in\n"
            "number (integer) of tool widths."
        )
        grid1.addWidget(passlabel, 1, 0)
        self.iso_width_entry = IntEntry()
        grid1.addWidget(self.iso_width_entry, 1, 1)

        overlabel = QLabel('Pass overlap:')
        overlabel.setToolTip(
            "How much (fraction of tool width)\n"
            "to overlap each pass."
        )
        grid1.addWidget(overlabel, 2, 0)
        self.iso_overlap_entry = FloatEntry()
        grid1.addWidget(self.iso_overlap_entry, 2, 1)

        # combine all passes CB
        self.combine_passes_cb = FCCheckBox(label='Combine Passes')
        self.combine_passes_cb.setToolTip(
            "Combine all passes into one object"
        )
        grid1.addWidget(self.combine_passes_cb, 3, 0)

        self.generate_iso_button = QPushButton('Generate Geometry')
        self.generate_iso_button.setToolTip(
            "Create the Geometry Object\n"
            "for isolation routing."
        )
        self.custom_box.addWidget(self.generate_iso_button)

        ## Clear non-copper regions
        self.clearcopper_label = QLabel("<b>Clear non-copper:</b>")
        self.clearcopper_label.setToolTip(
            "Create a Geometry object with\n"
            "toolpaths to cut all non-copper regions."
        )
        self.custom_box.addWidget(self.clearcopper_label)

        grid5 = QGridLayout()
        self.custom_box.addLayout(grid5)
        ncctdlabel = QLabel('Tools dia:')
        ncctdlabel.setToolTip(
            "Diameters of the cutting tools, separated by ','"
        )
        grid5.addWidget(ncctdlabel, 0, 0)
        self.ncc_tool_dia_entry = FCEntry()
        grid5.addWidget(self.ncc_tool_dia_entry, 0, 1)

        nccoverlabel = QLabel('Overlap:')
        nccoverlabel.setToolTip(
            "How much (fraction of tool width)\n"
            "to overlap each pass."
        )
        grid5.addWidget(nccoverlabel, 1, 0)
        self.ncc_overlap_entry = FloatEntry()
        grid5.addWidget(self.ncc_overlap_entry, 1, 1)

        nccmarginlabel = QLabel('Margin:')
        nccmarginlabel.setToolTip(
            "Bounding box margin."
        )
        grid5.addWidget(nccmarginlabel, 2, 0)
        self.ncc_margin_entry = FloatEntry()
        grid5.addWidget(self.ncc_margin_entry, 2, 1)

        self.generate_ncc_button = QPushButton('Generate Geometry')
        self.generate_ncc_button.setToolTip(
            "Create the Geometry Object\n"
            "for non-copper routing."
        )
        self.custom_box.addWidget(self.generate_ncc_button)

        ## Board cutout
        self.board_cutout_label = QLabel("<b>Board cutout:</b>")
        self.board_cutout_label.setToolTip(
            "Create toolpaths to cut around\n"
            "the PCB and separate it from\n"
            "the original board."
        )
        self.custom_box.addWidget(self.board_cutout_label)

        grid2 = QGridLayout()
        self.custom_box.addLayout(grid2)
        tdclabel = QLabel('Tool dia:')
        tdclabel.setToolTip(
            "Diameter of the cutting tool."
        )
        grid2.addWidget(tdclabel, 0, 0)
        self.cutout_tooldia_entry = LengthEntry()
        grid2.addWidget(self.cutout_tooldia_entry, 0, 1)

        marginlabel = QLabel('Margin:')
        marginlabel.setToolTip(
            "Distance from objects at which\n"
            "to draw the cutout."
        )
        grid2.addWidget(marginlabel, 1, 0)
        self.cutout_margin_entry = LengthEntry()
        grid2.addWidget(self.cutout_margin_entry, 1, 1)

        gaplabel = QLabel('Gap size:')
        gaplabel.setToolTip(
            "Size of the gaps in the toolpath\n"
            "that will remain to hold the\n"
            "board in place."
        )
        grid2.addWidget(gaplabel, 2, 0)
        self.cutout_gap_entry = LengthEntry()
        grid2.addWidget(self.cutout_gap_entry, 2, 1)

        gapslabel = QLabel('Gaps:')
        gapslabel.setToolTip(
            "Where to place the gaps, Top/Bottom\n"
            "Left/Rigt, or on all 4 sides."
        )
        grid2.addWidget(gapslabel, 3, 0)
        self.gaps_radio = RadioSet([{'label': '2 (T/B)', 'value': 'tb'},
                                    {'label': '2 (L/R)', 'value': 'lr'},
                                    {'label': '4', 'value': '4'}])
        grid2.addWidget(self.gaps_radio, 3, 1)

        self.generate_cutout_button = QPushButton('Generate Geometry')
        self.generate_cutout_button.setToolTip(
            "Generate the geometry for\n"
            "the board cutout."
        )
        self.custom_box.addWidget(self.generate_cutout_button)

        ## Non-copper regions
        self.noncopper_label = QLabel("<b>Non-copper regions:</b>")
        self.noncopper_label.setToolTip(
            "Create polygons covering the\n"
            "areas without copper on the PCB.\n"
            "Equivalent to the inverse of this\n"
            "object. Can be used to remove all\n"
            "copper from a specified region."
        )
        self.custom_box.addWidget(self.noncopper_label)

        grid3 = QGridLayout()
        self.custom_box.addLayout(grid3)

        # Margin
        bmlabel = QLabel('Boundary Margin:')
        bmlabel.setToolTip(
            "Specify the edge of the PCB\n"
            "by drawing a box around all\n"
            "objects with this minimum\n"
            "distance."
        )
        grid3.addWidget(bmlabel, 0, 0)
        self.noncopper_margin_entry = LengthEntry()
        grid3.addWidget(self.noncopper_margin_entry, 0, 1)

        # Rounded corners
        self.noncopper_rounded_cb = FCCheckBox(label="Rounded corners")
        self.noncopper_rounded_cb.setToolTip(
            "Creates a Geometry objects with polygons\n"
            "covering the copper-free areas of the PCB."
        )
        grid3.addWidget(self.noncopper_rounded_cb, 1, 0, 1, 2)

        self.generate_noncopper_button = QPushButton('Generate Geometry')
        self.custom_box.addWidget(self.generate_noncopper_button)

        ## Bounding box
        self.boundingbox_label = QLabel('<b>Bounding Box:</b>')
        self.custom_box.addWidget(self.boundingbox_label)

        grid4 = QGridLayout()
        self.custom_box.addLayout(grid4)

        bbmargin = QLabel('Boundary Margin:')
        bbmargin.setToolTip(
            "Distance of the edges of the box\n"
            "to the nearest polygon."
        )
        grid4.addWidget(bbmargin, 0, 0)
        self.bbmargin_entry = LengthEntry()
        grid4.addWidget(self.bbmargin_entry, 0, 1)

        self.bbrounded_cb = FCCheckBox(label="Rounded corners")
        self.bbrounded_cb.setToolTip(
            "If the bounding box is \n"
            "to have rounded corners\n"
            "their radius is equal to\n"
            "the margin."
        )
        grid4.addWidget(self.bbrounded_cb, 1, 0, 1, 2)

        self.generate_bb_button = QPushButton('Generate Geometry')
        self.generate_bb_button.setToolTip(
            "Genrate the Geometry object."
        )
        self.custom_box.addWidget(self.generate_bb_button)


class FlatCAMGerber(FlatCAMObj, Gerber):
    """
    Represents Gerber code.
    """

    ui_type = GerberObjectUI

    def __init__(self, name):
        Gerber.__init__(self)
        FlatCAMObj.__init__(self, name)

        self.kind = "gerber"

        # The 'name' is already in self.options from FlatCAMObj
        # Automatically updates the UI
        self.options.update({
            "plot": True,
            "multicolored": False,
            "solid": False,
            "isotooldia": 0.016,
            "isopasses": 1,
            "isooverlap": 0.15,
            "combine_passes": True,
            "ncctools": "1.0, 0.5",
            "nccoverlap": 0.4,
            "nccmargin": 1,
            "cutouttooldia": 0.07,
            "cutoutmargin": 0.2,
            "cutoutgapsize": 0.15,
            "gaps": "tb",
            "noncoppermargin": 0.0,
            "noncopperrounded": False,
            "bboxmargin": 0.0,
            "bboxrounded": False
        })

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind']

        # assert isinstance(self.ui, GerberObjectUI)
        # self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)
        # self.ui.solid_cb.stateChanged.connect(self.on_solid_cb_click)
        # self.ui.multicolored_cb.stateChanged.connect(self.on_multicolored_cb_click)
        # self.ui.generate_iso_button.clicked.connect(self.on_iso_button_click)
        # self.ui.generate_cutout_button.clicked.connect(self.on_generatecutout_button_click)
        # self.ui.generate_bb_button.clicked.connect(self.on_generatebb_button_click)
        # self.ui.generate_noncopper_button.clicked.connect(self.on_generatenoncopper_button_click)

    def set_ui(self, ui):
        """
        Maps options with GUI inputs.
        Connects GUI events to methods.

        :param ui: GUI object.
        :type ui: GerberObjectUI
        :return: None
        """
        FlatCAMObj.set_ui(self, ui)

        self.app.log.debug("FlatCAMGerber.set_ui()")

        self.form_fields.update({
            "plot": self.ui.plot_cb,
            "multicolored": self.ui.multicolored_cb,
            "solid": self.ui.solid_cb,
            "isotooldia": self.ui.iso_tool_dia_entry,
            "isopasses": self.ui.iso_width_entry,
            "isooverlap": self.ui.iso_overlap_entry,
            "combine_passes": self.ui.combine_passes_cb,
            "ncctools": self.ui.ncc_tool_dia_entry,
            "nccoverlap": self.ui.ncc_overlap_entry,
            "nccmargin": self.ui.ncc_margin_entry,
            "cutouttooldia": self.ui.cutout_tooldia_entry,
            "cutoutmargin": self.ui.cutout_margin_entry,
            "cutoutgapsize": self.ui.cutout_gap_entry,
            "gaps": self.ui.gaps_radio,
            "noncoppermargin": self.ui.noncopper_margin_entry,
            "noncopperrounded": self.ui.noncopper_rounded_cb,
            "bboxmargin": self.ui.bbmargin_entry,
            "bboxrounded": self.ui.bbrounded_cb
        })

        # Fill form fields only on object create
        self.to_form()

        assert isinstance(self.ui, GerberObjectUI)
        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)
        self.ui.solid_cb.stateChanged.connect(self.on_solid_cb_click)
        self.ui.multicolored_cb.stateChanged.connect(self.on_multicolored_cb_click)
        self.ui.generate_iso_button.clicked.connect(self.on_iso_button_click)
        self.ui.generate_ncc_button.clicked.connect(self.on_ncc_button_click)
        self.ui.generate_cutout_button.clicked.connect(self.on_generatecutout_button_click)
        self.ui.generate_bb_button.clicked.connect(self.on_generatebb_button_click)
        self.ui.generate_noncopper_button.clicked.connect(self.on_generatenoncopper_button_click)

    def on_generatenoncopper_button_click(self, *args):
        self.app.report_usage("gerber_on_generatenoncopper_button")

        self.read_form()
        name = self.options["name"] + "_noncopper"

        def geo_init(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry)
            bounding_box = self.solid_geometry.envelope.buffer(self.options["noncoppermargin"])
            if not self.options["noncopperrounded"]:
                bounding_box = bounding_box.envelope
            non_copper = bounding_box.difference(self.solid_geometry)
            geo_obj.solid_geometry = non_copper

        # TODO: Check for None
        self.app.new_object("geometry", name, geo_init)

    def on_generatebb_button_click(self, *args):
        self.app.report_usage("gerber_on_generatebb_button")
        self.read_form()
        name = self.options["name"] + "_bbox"

        def geo_init(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry)
            # Bounding box with rounded corners
            bounding_box = self.solid_geometry.envelope.buffer(self.options["bboxmargin"])
            if not self.options["bboxrounded"]:  # Remove rounded corners
                bounding_box = bounding_box.envelope
            geo_obj.solid_geometry = bounding_box

        self.app.new_object("geometry", name, geo_init)

    def on_generatecutout_button_click(self, *args):
        self.app.report_usage("gerber_on_generatecutout_button")
        self.read_form()
        name = self.options["name"] + "_cutout"

        def geo_init(geo_obj, app_obj):
            margin = self.options["cutoutmargin"] + self.options["cutouttooldia"]/2
            gap_size = self.options["cutoutgapsize"] + self.options["cutouttooldia"]
            minx, miny, maxx, maxy = self.bounds()
            minx -= margin
            maxx += margin
            miny -= margin
            maxy += margin
            midx = 0.5 * (minx + maxx)
            midy = 0.5 * (miny + maxy)
            hgap = 0.5 * gap_size
            pts = [[midx - hgap, maxy],
                   [minx, maxy],
                   [minx, midy + hgap],
                   [minx, midy - hgap],
                   [minx, miny],
                   [midx - hgap, miny],
                   [midx + hgap, miny],
                   [maxx, miny],
                   [maxx, midy - hgap],
                   [maxx, midy + hgap],
                   [maxx, maxy],
                   [midx + hgap, maxy]]
            cases = {"tb": [[pts[0], pts[1], pts[4], pts[5]],
                            [pts[6], pts[7], pts[10], pts[11]]],
                     "lr": [[pts[9], pts[10], pts[1], pts[2]],
                            [pts[3], pts[4], pts[7], pts[8]]],
                     "4": [[pts[0], pts[1], pts[2]],
                           [pts[3], pts[4], pts[5]],
                           [pts[6], pts[7], pts[8]],
                           [pts[9], pts[10], pts[11]]]}
            cuts = cases[self.options['gaps']]
            geo_obj.solid_geometry = unary_union([LineString(segment) for segment in cuts])

        # TODO: Check for None
        self.app.new_object("geometry", name, geo_init)

    def on_iso_button_click(self, *args):
        self.app.report_usage("gerber_on_iso_button")
        self.read_form()
        self.isolate()

    def on_ncc_button_click(self, *args):
        self.app.report_usage("gerber_on_ncc_button")

        # Prepare parameters
        try:
            tools = [float(eval(dia)) for dia in self.ui.ncc_tool_dia_entry.get_value().split(",")]
        except:
            self.app.log.error("At least one tool diameter needed")
            return

        over = self.ui.ncc_overlap_entry.get_value()
        margin = self.ui.ncc_margin_entry.get_value()

        if over is None or margin is None:
            self.app.log.error("Overlap and margin values needed")
            return

        print("non-copper clear button clicked", tools, over, margin)

        # Sort tools in descending order
        tools.sort(reverse=True)

        # Prepare non-copper polygons
        bounding_box = self.solid_geometry.envelope.buffer(distance=margin, join_style=JOIN_STYLE.mitre)
        empty = self.get_empty_area(bounding_box)
        if type(empty) is Polygon:
            empty = MultiPolygon([empty])

        # Main procedure
        def clear_non_copper():

            # Already cleared area
            cleared = MultiPolygon()

            # Geometry object creating callback
            def geo_init(geo_obj, app_obj):
                geo_obj.options["cnctooldia"] = tool
                geo_obj.solid_geometry = []
                for p in area.geoms:
                    try:
                        cp = self.clear_polygon(p, tool, over)
                        geo_obj.solid_geometry.append(list(cp.get_objects()))
                    except:
                        self.app.log.warning("Polygon is ommited")

            # Generate area for each tool
            offset = sum(tools)
            for tool in tools:
                # Get remaining tools offset
                offset -= tool

                # Area to clear
                area = empty.buffer(-offset).difference(cleared)

                # Transform area to MultiPolygon
                if type(area) is Polygon:
                    area = MultiPolygon([area])

                # Check if area not empty
                if len(area.geoms) > 0:
                    # Overall cleared area
                    cleared = empty.buffer(-offset * (1 + over)).buffer(-tool / 2).buffer(tool / 2)

                    # Create geometry object
                    name = self.options["name"] + "_ncc_" + repr(tool) + "D"
                    self.app.new_object("geometry", name, geo_init)
                else:
                    return

        # Do job in background
        proc = self.app.proc_container.new("Clearing non-copper areas.")

        def job_thread(app_obj):
            try:
                clear_non_copper()
            except Exception as e:
                proc.done()

                raise e
            proc.done()

        self.app.inform.emit("Clear non-copper areas started ...")
        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    def follow(self, outname=None):
        """
        Creates a geometry object "following" the gerber paths.

        :return: None
        """

        default_name = self.options["name"] + "_follow"
        follow_name = outname or default_name

        def follow_init(follow_obj, app_obj):
            # Propagate options
            follow_obj.options["cnctooldia"] = self.options["isotooldia"]
            follow_obj.solid_geometry = self.solid_geometry
            app_obj.info("Follow geometry created: %s" % follow_obj.options["name"])

        # TODO: Do something if this is None. Offer changing name?
        self.app.new_object("geometry", follow_name, follow_init)

    def isolate(self, dia=None, passes=None, overlap=None, outname=None, combine=None):
        """
        Creates an isolation routing geometry object in the project.

        :param dia: Tool diameter
        :param passes: Number of tool widths to cut
        :param overlap: Overlap between passes in fraction of tool diameter
        :param outname: Base name of the output object
        :return: None
        """
        if dia is None:
            dia = self.options["isotooldia"]
        if passes is None:
            passes = int(self.options["isopasses"])
        if overlap is None:
            overlap = self.options["isooverlap"]
        if combine is None:
            combine = self.options["combine_passes"]
        else:
            combine = bool(combine)

        base_name = self.options["name"] + "_iso"
        base_name = outname or base_name

        def generate_envelope(offset, invert):
            # isolation_geometry produces an envelope that is going on the left of the geometry
            # (the copper features). To leave the least amount of burrs on the features
            # the tool needs to travel on the right side of the features (this is called conventional milling)
            # the first pass is the one cutting all of the features, so it needs to be reversed
            # the other passes overlap preceding ones and cut the left over copper. It is better for them
            # to cut on the right side of the left over copper i.e on the left side of the features. 
            geom = self.isolation_geometry(offset)
            if invert:
                if type(geom) is MultiPolygon:
                    pl = []
                    for p in geom:
                        pl.append(Polygon(p.exterior.coords[::-1], p.interiors))
                    geom = MultiPolygon(pl)
                elif type(geom) is Polygon:
                    geom = Polygon(geom.exterior.coords[::-1], geom.interiors)
                else:
                    raise "Unexpected Geometry"
            return geom

        if combine:
            iso_name = base_name

            # TODO: This is ugly. Create way to pass data into init function.
            def iso_init(geo_obj, app_obj):
                # Propagate options
                geo_obj.options["cnctooldia"] = self.options["isotooldia"]
                geo_obj.solid_geometry = []
                for i in range(passes):
                    offset = (2 * i + 1) / 2.0 * dia - i * overlap * dia
                    geom = generate_envelope (offset, i == 0)
                    geo_obj.solid_geometry.append(geom)
                app_obj.info("Isolation geometry created: %s" % geo_obj.options["name"])

            # TODO: Do something if this is None. Offer changing name?
            self.app.new_object("geometry", iso_name, iso_init)

        else:
            for i in range(passes):

                offset = (2 * i + 1) / 2.0 * dia - i * overlap  * dia
                if passes > 1:
                    iso_name = base_name + str(i + 1)
                else:
                    iso_name = base_name

                # TODO: This is ugly. Create way to pass data into init function.
                def iso_init(geo_obj, app_obj):
                    # Propagate options
                    geo_obj.options["cnctooldia"] = self.options["isotooldia"]
                    geo_obj.solid_geometry = generate_envelope (offset, i == 0)
                    app_obj.info("Isolation geometry created: %s" % geo_obj.options["name"])

                # TODO: Do something if this is None. Offer changing name?
                self.app.new_object("geometry", iso_name, iso_init)

    def on_plot_cb_click(self, *args):
        if self.muted_ui:
            return
        self.read_form_item('plot')

    def on_solid_cb_click(self, *args):
        if self.muted_ui:
            return
        self.read_form_item('solid')
        self.plot()

    def on_multicolored_cb_click(self, *args):
        if self.muted_ui:
            return
        self.read_form_item('multicolored')
        self.plot()

    def convert_units(self, units):
        """
        Converts the units of the object by scaling dimensions in all geometry
        and options.

        :param units: Units to which to convert the object: "IN" or "MM".
        :type units: str
        :return: None
        :rtype: None
        """

        factor = Gerber.convert_units(self, units)

        self.options['isotooldia'] *= factor
        self.options['cutoutmargin'] *= factor
        self.options['cutoutgapsize'] *= factor
        self.options['noncoppermargin'] *= factor
        self.options['bboxmargin'] *= factor

    def plot(self):

        self.app.log.debug(str(inspect.stack()[1][3]) + " --> FlatCAMGerber.plot()")

        # Does all the required setup and returns False
        # if the 'ptint' option is set to False.
        if not FlatCAMObj.plot(self):
            return

        geometry = self.solid_geometry

        # Make sure geometry is iterable.
        try:
            _ = geometry.geoms
        except TypeError:
            geometry = [geometry]

        def random_color():
            color = np.random.rand(4)
            color[3] = 1
            return color

        try:
            if self.options["solid"]:
                for poly in geometry.geoms:
                    self.add_shape(shape=poly, color='#006E20BF', face_color=random_color()
                                   if self.options['multicolored'] else '#BBF268BF', visible=self.options['plot'])
            else:
                for poly in geometry.geoms:
                    self.add_shape(shape=poly, color=random_color() if self.options['multicolored'] else 'black',
                                   visible=self.options['plot'])
            self.shapes.redraw()
        except (ObjectDeleted, AttributeError):
            self.shapes.clear(update=True)

    def serialize(self):
        return {
            "options": self.options,
            "kind": self.kind
        }

    def build_ui(self):
        FlatCAMObj.build_ui(self)
        self.app.ui.showSelectedTab()
