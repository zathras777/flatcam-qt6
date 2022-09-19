import re

from io import StringIO
from PyQt6.QtWidgets import QLabel, QFileDialog, QGridLayout, QPushButton

from fcCamlib.cncjob import CNCjob
from FlatCAMObj import FlatCAMObj, ObjectDeleted
from GUIElements import FCEntry, FCTextArea, FCCheckBox, LengthEntry

from .base import ObjectUI


class CNCObjectUI(ObjectUI):
    """
    User interface for CNCJob objects.
    """

    def __init__(self, parent=None):
        """
        Creates the user interface for CNCJob objects. GUI elements should
        be placed in ``self.custom_box`` to preserve the layout.
        """

        ObjectUI.__init__(self, title='CNC Job Object', icon_file='share/cnc32.png', parent=parent)

        # Scale and offset are not available for CNCJob objects.
        # Hiding from the GUI.
        for i in range(0, self.scale_grid.count()):
            self.scale_grid.itemAt(i).widget().hide()
        self.scale_label.hide()
        self.scale_button.hide()

        for i in range(0, self.offset_grid.count()):
            self.offset_grid.itemAt(i).widget().hide()
        self.offset_label.hide()
        self.offset_button.hide()

        ## Plot options
        self.plot_options_label = QLabel("<b>Plot Options:</b>")
        self.custom_box.addWidget(self.plot_options_label)

        grid0 = QGridLayout()
        self.custom_box.addLayout(grid0)

        # Plot CB
        # self.plot_cb = QCheckBox('Plot')
        self.plot_cb = FCCheckBox('Plot')
        self.plot_cb.setToolTip(
            "Plot (show) this object."
        )
        grid0.addWidget(self.plot_cb, 0, 0)

        # Tool dia for plot
        tdlabel = QLabel('Tool dia:')
        tdlabel.setToolTip(
            "Diameter of the tool to be\n"
            "rendered in the plot."
        )
        grid0.addWidget(tdlabel, 1, 0)
        self.tooldia_entry = LengthEntry()
        grid0.addWidget(self.tooldia_entry, 1, 1)

        # Update plot button
        self.updateplot_button = QPushButton('Update Plot')
        self.updateplot_button.setToolTip(
            "Update the plot."
        )
        self.custom_box.addWidget(self.updateplot_button)

        ##################
        ## Export G-Code
        ##################
        self.export_gcode_label = QLabel("<b>Export G-Code:</b>")
        self.export_gcode_label.setToolTip(
            "Export and save G-Code to\n"
            "make this object to a file."
        )
        self.custom_box.addWidget(self.export_gcode_label)

        # Prepend text to Gerber
        prependlabel = QLabel('Prepend to G-Code:')
        prependlabel.setToolTip(
            "Type here any G-Code commands you would\n"
            "like to add to the beginning of the generated file."
        )
        self.custom_box.addWidget(prependlabel)

        self.prepend_text = FCTextArea()
        self.custom_box.addWidget(self.prepend_text)

        # Append text to Gerber
        appendlabel = QLabel('Append to G-Code:')
        appendlabel.setToolTip(
            "Type here any G-Code commands you would\n"
            "like to append to the generated file.\n"
            "I.e.: M2 (End of program)"
        )
        self.custom_box.addWidget(appendlabel)

        self.append_text = FCTextArea()
        self.custom_box.addWidget(self.append_text)

        # Dwell
        grid1 = QGridLayout()
        self.custom_box.addLayout(grid1)

        dwelllabel = QLabel('Dwell:')
        dwelllabel.setToolTip(
            "Pause to allow the spindle to reach its\n"
            "speed before cutting."
        )
        dwelltime = QLabel('Duration [sec.]:')
        dwelltime.setToolTip(
            "Number of second to dwell."
        )
        self.dwell_cb = FCCheckBox()
        self.dwelltime_entry = FCEntry()
        grid1.addWidget(dwelllabel, 0, 0)
        grid1.addWidget(self.dwell_cb, 0, 1)
        grid1.addWidget(dwelltime, 1, 0)
        grid1.addWidget(self.dwelltime_entry, 1, 1)

        # GO Button
        self.export_gcode_button = QPushButton('Export G-Code')
        self.export_gcode_button.setToolTip(
            "Opens dialog to save G-Code\n"
            "file."
        )
        self.custom_box.addWidget(self.export_gcode_button)


class FlatCAMCNCjob(FlatCAMObj, CNCjob):
    """
    Represents G-Code.
    """

    ui_type = CNCObjectUI

    def __init__(self, name, units="in", kind="generic", z_move=0.1,
                 feedrate=3.0, z_cut=-0.002, tooldia=0.0,
                 spindlespeed=None):

        CNCjob.__init__(self, units=units, kind=kind, z_move=z_move,
                        feedrate=feedrate, z_cut=z_cut, tooldia=tooldia,
                        spindlespeed=spindlespeed)

        FlatCAMObj.__init__(self, name)

        self.kind = "cncjob"

        self.app.log.debug("Creating CNCJob object...")

        self.options.update({
            "plot": True,
            "tooldia": 0.4 / 25.4,  # 0.4mm in inches
            "append": "",
            "prepend": "",
            "dwell": False,
            "dwelltime": 1
        })

        # Attributes to be included in serialization
        # Always append to it because it carries contents
        # from predecessors.
        self.ser_attrs += ['options', 'kind']

        self.annotation = self.app.plotcanvas.new_text_group()

    def set_ui(self, ui):
        FlatCAMObj.set_ui(self, ui)

        self.app.log.debug("FlatCAMCNCJob.set_ui()")

        assert isinstance(self.ui, CNCObjectUI), \
            "Expected a CNCObjectUI, got %s" % type(self.ui)

        self.form_fields.update({
            "plot": self.ui.plot_cb,
            "tooldia": self.ui.tooldia_entry,
            "append": self.ui.append_text,
            "prepend": self.ui.prepend_text,
            "dwell": self.ui.dwell_cb,
            "dwelltime": self.ui.dwelltime_entry
        })

        # Fill form fields only on object create
        self.to_form()

        self.ui.plot_cb.stateChanged.connect(self.on_plot_cb_click)
        self.ui.updateplot_button.clicked.connect(self.on_updateplot_button_click)
        self.ui.export_gcode_button.clicked.connect(self.on_exportgcode_button_click)

    def on_updateplot_button_click(self, *args):
        """
        Callback for the "Updata Plot" button. Reads the form for updates
        and plots the object.
        """
        self.read_form()
        self.plot()

    def on_exportgcode_button_click(self, *args):
        self.app.report_usage("cncjob_on_exportgcode_button")
        self.read_form()
        try:
            fileinfo = QFileDialog.getSaveFileName(caption="Export G-Code ...",
                                                   directory=self.app.defaults["last_folder"])
        except TypeError:
            fileinfo = QFileDialog.getSaveFileName(caption="Export G-Code ...")

        preamble = str(self.ui.prepend_text.get_value())
        postamble = str(self.ui.append_text.get_value())

        self.export_gcode(fileinfo[0], preamble=preamble, postamble=postamble)

    def dwell_generator(self, lines):
        """
        Inserts "G4 P..." instructions after spindle-start
        instructions (M03 or M04).

        """

        self.app.log.debug("dwell_generator()...")

        m3m4re = re.compile(r'^\s*[mM]0[34]')
        g4re = re.compile(r'^\s*[gG]4\s+([\d\.\+\-e]+)')
        bufline = None

        for line in lines:
            # If the buffer contains a G4, yield that.
            # If current line is a G4, discard it.
            if bufline is not None:
                yield bufline
                bufline = None
                if not g4re.search(line):
                    yield line
                continue

            # If start spindle, buffer a G4.
            if m3m4re.search(line):
                self.app.log.debug("Found M03/4")
                bufline = "G4 P{}\n".format(self.options['dwelltime'])
            yield line

        # Nothing more to export. We're done :-)
        return

    def export_gcode(self, filename, preamble='', postamble=''):

        lines = StringIO(self.gcode)

        ## Post processing
        # Dwell?
        if self.options['dwell']:
            self.app.log.debug("Will add G04!")
            lines = self.dwell_generator(lines)

        ## Write
        with open(filename, 'w') as f:
            f.write(preamble + "\n")
            for line in lines:
                f.write(line)
            f.write(postamble)

        # Just for adding it to the recent files list.
        self.app.file_opened.emit("cncjob", filename)

        self.app.inform.emit("Saved to: " + filename)

    def get_gcode(self, preamble='', postamble=''):
        #we need this to beable get_gcode separatelly for shell command export_code
        return preamble + '\n' + self.gcode + "\n" + postamble

    def on_plot_cb_click(self, *args):
        if self.muted_ui:
            return
        self.read_form_item('plot')

    def plot(self):

        # Does all the required setup and returns False
        # if the 'ptint' option is set to False.
        if not FlatCAMObj.plot(self):
            return

        try:
            self.plot2(tooldia=self.options["tooldia"], obj=self, visible=self.options['plot'])
            self.shapes.redraw()
        except (ObjectDeleted, AttributeError):
            self.shapes.clear(update=True)
            self.annotation.clear(update=True)

    def convert_units(self, units):
        factor = CNCjob.convert_units(self, units)
        self.app.log.debug("FlatCAMCNCjob.convert_units()")
        self.options["tooldia"] *= factor
