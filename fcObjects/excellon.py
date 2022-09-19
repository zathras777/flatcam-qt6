
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QTableWidgetItem, QGridLayout, QPushButton
from shapely.geometry import Point

from fcCamlib.excellon import Excellon
from FlatCAMObj import FlatCAMObj, ObjectDeleted
from GUIElements import FCTable, FCCheckBox, IntEntry, LengthEntry, OptionalInputSection

from .base import ObjectUI
from .geometry import FlatCAMGeometry
from .cncjob import FlatCAMCNCjob


class ExcellonObjectUI(ObjectUI):
    """
    User interface for Excellon objects.
    """

    def __init__(self, parent=None):
        ObjectUI.__init__(self, title='Excellon Object',
                          icon_file='share/drill32.png',
                          parent=parent)

        #### Plot options ####

        self.plot_options_label = QLabel("<b>Plot Options:</b>")
        self.custom_box.addWidget(self.plot_options_label)

        grid0 = QGridLayout()
        self.custom_box.addLayout(grid0)
        self.plot_cb = FCCheckBox(label='Plot')
        self.plot_cb.setToolTip(
            "Plot (show) this object."
        )
        grid0.addWidget(self.plot_cb, 0, 0)
        self.solid_cb = FCCheckBox(label='Solid')
        self.solid_cb.setToolTip(
            "Solid circles."
        )
        grid0.addWidget(self.solid_cb, 0, 1)

        #### Tools ####

        self.tools_table_label = QLabel('<b>Tools</b>')
        self.tools_table_label.setToolTip(
            "Tools in this Excellon object."
        )
        self.custom_box.addWidget(self.tools_table_label)
        self.tools_table = FCTable()
        self.tools_table.setFixedHeight(100)

        self.custom_box.addWidget(self.tools_table)

        #### Create CNC Job ####

        self.cncjob_label = QLabel('<b>Create CNC Job</b>')
        self.cncjob_label.setToolTip(
            "Create a CNC Job object\n"
            "for this drill object."
        )
        self.custom_box.addWidget(self.cncjob_label)

        grid1 = QGridLayout()
        self.custom_box.addLayout(grid1)

        cutzlabel = QLabel('Cut Z:')
        cutzlabel.setToolTip(
            "Drill depth (negative)\n"
            "below the copper surface."
        )
        grid1.addWidget(cutzlabel, 0, 0)
        self.cutz_entry = LengthEntry()
        grid1.addWidget(self.cutz_entry, 0, 1)

        travelzlabel = QLabel('Travel Z:')
        travelzlabel.setToolTip(
            "Tool height when travelling\n"
            "across the XY plane."
        )
        grid1.addWidget(travelzlabel, 1, 0)
        self.travelz_entry = LengthEntry()
        grid1.addWidget(self.travelz_entry, 1, 1)

        frlabel = QLabel('Feed rate:')
        frlabel.setToolTip(
            "Tool speed while drilling\n"
            "(in units per minute)."
        )
        grid1.addWidget(frlabel, 2, 0)
        self.feedrate_entry = LengthEntry()
        grid1.addWidget(self.feedrate_entry, 2, 1)

        # Tool change:
        toolchlabel = QLabel("Tool change:")
        toolchlabel.setToolTip(
            "Include tool-change sequence\n"
            "in G-Code (Pause for tool change)."
        )
        self.toolchange_cb = FCCheckBox()
        grid1.addWidget(toolchlabel, 3, 0)
        grid1.addWidget(self.toolchange_cb, 3, 1)

        # Tool change Z:
        toolchzlabel = QLabel("Tool change Z:")
        toolchzlabel.setToolTip(
            "Z-axis position (height) for\n"
            "tool change."
        )
        grid1.addWidget(toolchzlabel, 4, 0)
        self.toolchangez_entry = LengthEntry()
        grid1.addWidget(self.toolchangez_entry, 4, 1)
        self.ois_tcz = OptionalInputSection(self.toolchange_cb, [self.toolchangez_entry])

        # Spindlespeed
        spdlabel = QLabel('Spindle speed:')
        spdlabel.setToolTip(
            "Speed of the spindle\n"
            "in RPM (optional)"
        )
        grid1.addWidget(spdlabel, 5, 0)
        self.spindlespeed_entry = IntEntry(allow_empty=True)
        grid1.addWidget(self.spindlespeed_entry, 5, 1)

        choose_tools_label = QLabel(
            "Select from the tools section above\n"
            "the tools you want to include."
        )
        self.custom_box.addWidget(choose_tools_label)

        self.generate_cnc_button = QPushButton('Generate')
        self.generate_cnc_button.setToolTip(
            "Generate the CNC Job."
        )
        self.custom_box.addWidget(self.generate_cnc_button)

        #### Milling Holes ####
        self.mill_hole_label = QLabel('<b>Mill Holes</b>')
        self.mill_hole_label.setToolTip(
            "Create Geometry for milling holes."
        )
        self.custom_box.addWidget(self.mill_hole_label)

        grid1 = QGridLayout()
        self.custom_box.addLayout(grid1)
        tdlabel = QLabel('Tool dia:')
        tdlabel.setToolTip(
            "Diameter of the cutting tool."
        )
        grid1.addWidget(tdlabel, 0, 0)
        self.tooldia_entry = LengthEntry()
        grid1.addWidget(self.tooldia_entry, 0, 1)

        choose_tools_label2 = QLabel(
            "Select from the tools section above\n"
            "the tools you want to include."
        )
        self.custom_box.addWidget(choose_tools_label2)

        self.generate_milling_button = QPushButton('Generate Geometry')
        self.generate_milling_button.setToolTip(
            "Create the Geometry Object\n"
            "for milling toolpaths."
        )
        self.custom_box.addWidget(self.generate_milling_button)


class FlatCAMExcellon(FlatCAMObj, Excellon):
    """
    Represents Excellon/Drill code.
    """

    ui_type = ExcellonObjectUI

    def __init__(self, name):
        Excellon.__init__(self)
        FlatCAMObj.__init__(self, name)

        self.kind = "excellon"

        self.options.update({
            "plot": True,
            "solid": False,
            "drillz": -0.1,
            "travelz": 0.1,
            "feedrate": 5.0,
            # "toolselection": ""
            "tooldia": 0.1,
            "toolchange": False,
            "toolchangez": 1.0,
            "spindlespeed": None
        })

        # TODO: Document this.
        self.tool_cbs = {}

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind']

    @staticmethod
    def merge(exc_list, exc_final):
        """
        Merge excellons in exc_list into exc_final.
        Options are allways copied from source .

        Tools are also merged, if name for tool is same and   size differs, then as name is used next available  number from both lists

        if only one object is  specified in exc_list then this acts  as copy only

        :param exc_list: List or one object of FlatCAMExcellon Objects to join.
        :param exc_final: Destination FlatCAMExcellon object.
        :return: None
        """

        if type(exc_list) is not list:
            exc_list_real= list()
            exc_list_real.append(exc_list)
        else:
            exc_list_real=exc_list

        for exc in exc_list_real:
            # Expand lists
            if type(exc) is list:
                FlatCAMExcellon.merge(exc, exc_final)
            # If not list, merge excellons
            else:

                #    TODO: I realize forms does not save values into options , when  object is deselected
                #    leave this  here for future use
                #    this  reinitialize options based on forms, all steps may not be necessary
                #    exc.app.collection.set_active(exc.options['name'])
                #    exc.to_form()
                #    exc.read_form()
                for option in exc.options:
                    if option != 'name':
                        try:
                            exc_final.options[option] = exc.options[option]
                        except:
                            exc.app.log.warning("Failed to copy option.",option)

                #deep copy of all drills,to avoid any references
                for drill in exc.drills:
                    point = Point(drill['point'].x,drill['point'].y)
                    exc_final.drills.append({"point": point, "tool": drill['tool']})
                toolsrework=dict()
                max_numeric_tool=0
                for toolname in exc.tools.iterkeys():
                    numeric_tool=int(toolname)
                    if numeric_tool>max_numeric_tool:
                        max_numeric_tool=numeric_tool
                    toolsrework[exc.tools[toolname]['C']]=toolname

                #exc_final as last because names from final tools will be used
                for toolname in exc_final.tools.iterkeys():
                    numeric_tool=int(toolname)
                    if numeric_tool>max_numeric_tool:
                        max_numeric_tool=numeric_tool
                    toolsrework[exc_final.tools[toolname]['C']]=toolname

                for toolvalues in toolsrework.iterkeys():
                    if toolsrework[toolvalues] in exc_final.tools:
                        if exc_final.tools[toolsrework[toolvalues]]!={"C": toolvalues}:
                            exc_final.tools[str(max_numeric_tool+1)]={"C": toolvalues}
                    else:
                        exc_final.tools[toolsrework[toolvalues]]={"C": toolvalues}
                #this value  was not co
                exc_final.zeros=exc.zeros
                exc_final.create_geometry()

    def build_ui(self):
        FlatCAMObj.build_ui(self)

        # Populate tool list
        n = len(self.tools)
        self.ui.tools_table.setColumnCount(2)
        self.ui.tools_table.setHorizontalHeaderLabels(['#', 'Diameter'])
        self.ui.tools_table.setRowCount(n)
        self.ui.tools_table.setSortingEnabled(False)
        i = 0
        for tool in self.tools:
            id = QTableWidgetItem(tool)
            id.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.ui.tools_table.setItem(i, 0, id)  # Tool name/id
            dia = QTableWidgetItem(str(self.tools[tool]['C']))
            dia.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.ui.tools_table.setItem(i, 1, dia)  # Diameter
            i += 1
        
        # sort the tool diameter column
        self.ui.tools_table.sortItems(1)
        # all the tools are selected by default
        self.ui.tools_table.selectColumn(0)
        
        self.ui.tools_table.resizeColumnsToContents()
        self.ui.tools_table.resizeRowsToContents()
        self.ui.tools_table.horizontalHeader().setStretchLastSection(True)
        self.ui.tools_table.verticalHeader().hide()
        self.ui.tools_table.setSortingEnabled(True)

        self.app.ui.showSelectedTab()

    def set_ui(self, ui):
        """
        Configures the user interface for this object.
        Connects options to form fields.

        :param ui: User interface object.
        :type ui: ExcellonObjectUI
        :return: None
        """
        FlatCAMObj.set_ui(self, ui)

        #log.debug("FlatCAMExcellon.set_ui()")

        self.form_fields.update({
            "plot": self.ui.plot_cb,
            "solid": self.ui.solid_cb,
            "drillz": self.ui.cutz_entry,
            "travelz": self.ui.travelz_entry,
            "feedrate": self.ui.feedrate_entry,
            "tooldia": self.ui.tooldia_entry,
            "toolchange": self.ui.toolchange_cb,
            "toolchangez": self.ui.toolchangez_entry,
            "spindlespeed": self.ui.spindlespeed_entry
        })

        # Fill form fields
        self.to_form()

        assert isinstance(self.ui, ExcellonObjectUI), \
            "Expected a ExcellonObjectUI, got %s" % type(self.ui)
        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)
        self.ui.solid_cb.stateChanged.connect(self.on_solid_cb_click)
        self.ui.generate_cnc_button.clicked.connect(self.on_create_cncjob_button_click)
        self.ui.generate_milling_button.clicked.connect(self.on_generate_milling_button_click)

    def get_selected_tools_list(self):
        """
        Returns the keys to the self.tools dictionary corresponding
        to the selections on the tool list in the GUI.

        :return: List of tools.
        :rtype: list
        """
        return [str(x.text()) for x in self.ui.tools_table.selectedItems()]

    def generate_milling(self, tools=None, outname=None, tooldia=None):
        """
        Note: This method is a good template for generic operations as
        it takes it's options from parameters or otherwise from the
        object's options and returns a success, msg tuple as feedback
        for shell operations.

        :return: Success/failure condition tuple (bool, str).
        :rtype: tuple
        """

        # Get the tools from the list. These are keys
        # to self.tools
        if tools is None:
            tools = self.get_selected_tools_list()

        if outname is None:
            outname = self.options["name"] + "_mill"

        if tooldia is None:
            tooldia = self.options["tooldia"]

        if len(tools) == 0:
            self.app.inform.emit("Please select one or more tools from the list and try again.")
            return False, "Error: No tools."

        for tool in tools:
            if self.tools[tool]["C"] < tooldia:
                self.app.inform.emit("[warning] Milling tool is larger than hole size. Cancelled.")
                return False, "Error: Milling tool is larger than hole."

        def geo_init(geo_obj, app_obj):
            assert isinstance(geo_obj, FlatCAMGeometry), \
                "Initializer expected a FlatCAMGeometry, got %s" % type(geo_obj)
            app_obj.progress.emit(20)

            geo_obj.solid_geometry = []

            for hole in self.drills:
                if hole['tool'] in tools:
                    geo_obj.solid_geometry.append(
                        Point(hole['point']).buffer(self.tools[hole['tool']]["C"] / 2 -
                                                    tooldia / 2).exterior
                    )

        def geo_thread(app_obj):
            app_obj.new_object("geometry", outname, geo_init)
            app_obj.progress.emit(100)

        # Create a promise with the new name
        self.app.collection.promise(outname)

        # Send to worker
        self.app.worker_task.emit({'fcn': geo_thread, 'params': [self.app]})

        return True, ""

    def on_generate_milling_button_click(self, *args):
        self.app.report_usage("excellon_on_create_milling_button")
        self.read_form()

        self.generate_milling()

    def on_create_cncjob_button_click(self, *args):
        self.app.report_usage("excellon_on_create_cncjob_button")
        self.read_form()

        # Get the tools from the list
        tools = self.get_selected_tools_list()

        if len(tools) == 0:
            self.app.inform.emit("Please select one or more tools from the list and try again.")
            return

        job_name = self.options["name"] + "_cnc"

        # Object initialization function for app.new_object()
        def job_init(job_obj, app_obj):
            assert isinstance(job_obj, FlatCAMCNCjob), \
                "Initializer expected a FlatCAMCNCjob, got %s" % type(job_obj)

            app_obj.progress.emit(20)
            job_obj.z_cut = self.options["drillz"]
            job_obj.z_move = self.options["travelz"]
            job_obj.feedrate = self.options["feedrate"]
            job_obj.spindlespeed = self.options["spindlespeed"]
            # There could be more than one drill size...
            # job_obj.tooldia =   # TODO: duplicate variable!
            # job_obj.options["tooldia"] =

            tools_csv = ','.join(tools)
            job_obj.generate_from_excellon_by_tool(self, tools_csv,
                                                   toolchange=self.options["toolchange"],
                                                   toolchangez=self.options["toolchangez"])

            app_obj.progress.emit(50)
            job_obj.gcode_parse()

            app_obj.progress.emit(60)
            job_obj.create_geometry()

            app_obj.progress.emit(80)

        # To be run in separate thread
        def job_thread(app_obj):
            app_obj.new_object("cncjob", job_name, job_init)
            app_obj.progress.emit(100)

        # Create promise for the new name.
        self.app.collection.promise(job_name)

        # Send to worker
        # self.app.worker.add_task(job_thread, [self.app])
        self.app.worker_task.emit({'fcn': job_thread, 'params': [self.app]})

    def on_plot_cb_click(self, *args):
        if self.muted_ui:
            return
        self.read_form_item('plot')

    def on_solid_cb_click(self, *args):
        if self.muted_ui:
            return
        self.read_form_item('solid')
        self.plot()

    def convert_units(self, units):
        factor = Excellon.convert_units(self, units)

        self.options['drillz'] *= factor
        self.options['travelz'] *= factor
        self.options['feedrate'] *= factor

    def plot(self):

        # Does all the required setup and returns False
        # if the 'ptint' option is set to False.
        if not FlatCAMObj.plot(self):
            return

        try:
            _ = iter(self.solid_geometry)
        except TypeError:
            self.solid_geometry = [self.solid_geometry]

        try:
            # Plot excellon (All polygons?)
            if self.options["solid"]:
                for geo in self.solid_geometry:
                    self.add_shape(shape=geo, color='#750000BF', face_color='#C40000BF', visible=self.options['plot'],
                                   layer=2)
            else:
                for geo in self.solid_geometry:
                    self.add_shape(shape=geo.exterior, color='red', visible=self.options['plot'])
                    for ints in geo.interiors:
                        self.add_shape(shape=ints, color='green', visible=self.options['plot'])

            self.shapes.redraw()
        except (ObjectDeleted, AttributeError):
            self.shapes.clear(update=True)
