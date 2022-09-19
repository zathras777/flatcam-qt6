from OpenGL import GL as gl
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QAction, QIcon, QPixmap, QMovie
from PyQt6.QtWidgets import QMainWindow, QLabel, QGridLayout, \
    QMenu, QApplication, QToolBar, QSplitter, QWidget, QTabWidget, \
    QVBoxLayout, QHBoxLayout, QComboBox, QProgressBar, QGroupBox
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

from GUIElements import *


# In order to enable OpenGL support in Qt6, we need to add an
# OpenGL widget. Here we also take the opportunity to set some
# defaults that were previously set in the VisPyPatch code.
class OpenGLWidget(QOpenGLWidget):
    def __init__(self):
        super().__init__()

    def initializeGL(self):
        gl.glDisable(gl.GL_LINE_SMOOTH)
        gl.glLineWidth(1.0)
        gl.glClearColor(0.2, 0.2, 0.2, 1)
        gl.glEnable(gl.GL_DEPTH_TEST)


class FlatCAMGUI(QMainWindow):
    # Emitted when persistent window geometry needs to be retained
    geom_update = pyqtSignal(int, int, int, int, int, name='geomUpdate')
    # Emitted when we want to save prior to exit
    final_save = pyqtSignal(name='saveBeforeExit')

    def __init__(self, version:str, app):
        super().__init__()

        # Divine icon pack by Ipapun @ finicons.com

        self.app = app
        ############
        ### Menu ###
        ############
        self.menu = self.menuBar()

        ### File ###
        self.menufile = self.menu.addMenu('&File')
        self.menufile.setToolTipsVisible(True)
        # New
        self.menufilenew = QAction(QIcon('share/file16.png'), '&New', self)
        self.menufile.addAction(self.menufilenew)

        self.menufileopenproject = QAction(QIcon('share/folder16.png'), 'Open &Project ...', self)
        self.menufile.addAction(self.menufileopenproject)

        # Open gerber ...
        self.menufileopengerber = QAction('Open &Gerber ...', self)
        self.menufile.addAction(self.menufileopengerber)

        # Open Excellon ...
        self.menufileopenexcellon = QAction('Open &Excellon ...', self)
        self.menufile.addAction(self.menufileopenexcellon)

        # Open G-Code ...
        self.menufileopengcode = QAction('Open G-&Code ...', self)
        self.menufile.addAction(self.menufileopengcode)

        # Recent
        self.recent = self.menufile.addMenu("Recent files")

        # Separator
        self.menufile.addSeparator()

        self.menufileimport = self.menufile.addMenu(QIcon('share/import.png'), 'Import')

        # Import SVG ...
        self.menufileimportsvg = QAction('Import &SVG ...', self)
        self.menufileimport.addAction(self.menufileimportsvg)

        self.menufileimportdxf = QAction(QIcon('share/dxf16.png'),
                                         '&DXF as Geometry Object', self)
        self.menufileimport.addAction(self.menufileimportdxf)
        self.menufileimportdxf_as_gerber = QAction(QIcon('share/dxf16.png'),
                                                   '&DXF as Gerber Object', self)
        self.menufileimport.addAction(self.menufileimportdxf_as_gerber)

        self.menufileimport.addSeparator()

        # Export SVG ...
        self.menufileexportsvg = QAction('Export &SVG ...', self)
        self.menufile.addAction(self.menufileexportsvg)

        # Separator
        self.menufile.addSeparator()

        # Save Defaults
        self.menufilesavedefaults = QAction('Save &Defaults', self)
        self.menufile.addAction(self.menufilesavedefaults)

        # Separator
        self.menufile.addSeparator()

        # Save Project
        self.menufilesaveproject = QAction(QIcon('share/floppy16.png'), '&Save Project', self)
        self.menufile.addAction(self.menufilesaveproject)

        # Save Project As ...
        self.menufilesaveprojectas = QAction('Save Project &As ...', self)
        self.menufile.addAction(self.menufilesaveprojectas)

        # Save Project Copy ...
        self.menufilesaveprojectcopy = QAction('Save Project C&opy ...', self)
        self.menufile.addAction(self.menufilesaveprojectcopy)

        # Separator
        self.menufile.addSeparator()

        # Quit
        exit_action = QAction(QIcon('share/power16.png'), 'E&xit', self)
        # exitAction.setShortcut('Ctrl+Q')
        # exitAction.setStatusTip('Exit application')
        exit_action.triggered.connect(QApplication.quit)

        self.menufile.addAction(exit_action)

        ### Edit ###
        self.menuedit = self.menu.addMenu('&Edit')
        self.menueditnew = self.menuedit.addAction(QIcon('share/new_geo16.png'), 'New Geometry')
        self.menueditedit = self.menuedit.addAction(QIcon('share/edit16.png'), 'Edit Geometry')
        self.menueditok = self.menuedit.addAction(QIcon('share/edit_ok16.png'), 'Update Geometry')
        #self.menueditok.
        #self.menueditcancel = self.menuedit.addAction(QIcon('share/cancel_edit16.png'), "Cancel Edit")
        self.menueditjoin = self.menuedit.addAction(QIcon('share/join16.png'), 'Join Geometry')
        self.menueditdelete = self.menuedit.addAction(QIcon('share/trash16.png'), 'Delete')

        ### Options ###
        self.menuoptions = self.menu.addMenu('&Options')
        self.menuoptions_transfer = self.menuoptions.addMenu('Transfer options')
        self.menuoptions_transfer_a2p = self.menuoptions_transfer.addAction("Application to Project")
        self.menuoptions_transfer_p2a = self.menuoptions_transfer.addAction("Project to Application")
        self.menuoptions_transfer_p2o = self.menuoptions_transfer.addAction("Project to Object")
        self.menuoptions_transfer_o2p = self.menuoptions_transfer.addAction("Object to Project")
        self.menuoptions_transfer_a2o = self.menuoptions_transfer.addAction("Application to Object")
        self.menuoptions_transfer_o2a = self.menuoptions_transfer.addAction("Object to Application")

        ### View ###
        self.menuview = self.menu.addMenu('&View')
        self.menuviewenable = self.menuview.addAction(QIcon('share/replot16.png'), 'Enable all plots')
        self.menuviewdisableall = self.menuview.addAction(QIcon('share/clear_plot16.png'), 'Disable all plots')
        self.menuviewdisableother = self.menuview.addAction(QIcon('share/clear_plot16.png'),
                                                            'Disable non-selected')

        ### Tool ###
        #self.menutool = self.menu.addMenu('&Tool')
        self.menutool = QMenu('&Tool')
        self.menutoolaction = self.menu.addMenu(self.menutool)
        self.menutoolshell = self.menutool.addAction(QIcon('share/shell16.png'), '&Command Line')

        ### Help ###
        self.menuhelp = self.menu.addMenu('&Help')
        self.menuhelp_about = self.menuhelp.addAction(QIcon('share/tv16.png'), 'About FlatCAM')
        self.menuhelp_home = self.menuhelp.addAction(QIcon('share/home16.png'), 'Home')
        self.menuhelp_manual = self.menuhelp.addAction(QIcon('share/globe16.png'), 'Manual')

        ####################
        ### Context menu ###
        ####################

        self.menuproject = QMenu()
        self.menuprojectenable = self.menuproject.addAction('Enable')
        self.menuprojectdisable = self.menuproject.addAction('Disable')
        self.menuproject.addSeparator()
        self.menuprojectgeneratecnc = self.menuproject.addAction('Generate CNC')
        self.menuproject.addSeparator()
        self.menuprojectdelete = self.menuproject.addAction('Delete')

        ###############
        ### Toolbar ###
        ###############
        self.toolbarfile = QToolBar('File')
        self.toolbarfile.setToolTipDuration(10000)


        def add_to_toolbar(toolbar:QToolBar, iconName:str, actionName:str, eventFn) -> None:
            btn = QAction(QIcon(iconName), actionName, self)
            btn.setStatusTip(actionName)
            btn.setToolTip(actionName)
            btn.triggered.connect(eventFn)
            toolbar.addAction(btn)

        self.addToolBar(self.toolbarfile)       
        add_to_toolbar(self.toolbarfile, "share/file32.png", "New Project", self.app.on_file_new)
        add_to_toolbar(self.toolbarfile, 'share/folder32.png', "Open project", self.app.on_file_openproject)
        add_to_toolbar(self.toolbarfile, 'share/floppy32.png', "Save project", self.app.on_file_saveproject)

        # self.file_open_btn = self.toolbarfile.addAction(QIcon('share/folder32.png'), "Open project")
        # self.file_save_btn = self.toolbarfile.addAction(QIcon('share/floppy32.png'), "Save project")

        self.toolbargeo = QToolBar('Edit')
        self.addToolBar(self.toolbargeo)

        self.newgeo_btn = self.toolbargeo.addAction(QIcon('share/new_geo32.png'), "New Blank Geometry")
        self.delete_btn = self.toolbargeo.addAction(QIcon('share/cancel_edit32.png'), "&Delete")
        self.editgeo_btn = self.toolbargeo.addAction(QIcon('share/edit32.png'), "Edit Geometry")
        self.updategeo_btn = self.toolbargeo.addAction(QIcon('share/edit_ok32.png'), "Update Geometry")
        self.updategeo_btn.setEnabled(False)
        #self.canceledit_btn = self.toolbar.addAction(QIcon('share/cancel_edit32.png'), "Cancel Edit")

        self.toolbarview = QToolBar('View')
        self.addToolBar(self.toolbarview)
        self.zoom_fit_btn = self.toolbarview.addAction(QIcon('share/zoom_fit32.png'), "&Zoom Fit")
        self.zoom_in_btn = self.toolbarview.addAction(QIcon('share/zoom_in32.png'), "&Zoom In")
        self.zoom_out_btn = self.toolbarview.addAction(QIcon('share/zoom_out32.png'), "&Zoom Out")
        self.replot_btn = self.toolbarview.addAction(QIcon('share/replot32.png'), "&Replot")
        self.clear_plot_btn = self.toolbarview.addAction(QIcon('share/clear_plot32.png'), "&Clear plot")

        self.toolbartools = QToolBar('Tools')
        self.addToolBar(self.toolbartools)
        self.shell_btn = self.toolbartools.addAction(QIcon('share/shell32.png'), "&Command Line")

        ################
        ### Splitter ###
        ################
        self.splitter = QSplitter()
        self.setCentralWidget(self.splitter)

        ################
        ### Notebook ###
        ################
        self.notebook = QTabWidget()
        # self.notebook.setMinimumWidth(250)

        ### Projet ###
        project_tab = QWidget()
        # project_tab.setMinimumWidth(250)  # Hack
        self.project_tab_layout = QVBoxLayout(project_tab)
        self.project_tab_layout.setContentsMargins(2, 2, 2, 2)
        self.notebook.addTab(project_tab, "Project")

        ### Selected ###
        self.selected_tab = QWidget()
        self.selected_tab.setToolTip("Selected Object Details")
        self.selected_tab_layout = QVBoxLayout(self.selected_tab)
        self.selected_tab_layout.setContentsMargins(2, 2, 2, 2)
        self.selected_scroll_area = VerticalScrollArea()
        self.selected_tab_layout.addWidget(self.selected_scroll_area)
        self.notebook.addTab(self.selected_tab, "Selected")

        ### Options ###
        self.options_tab = QWidget()
        self.options_tab.setContentsMargins(0, 0, 0, 0)
        self.options_tab_layout = QVBoxLayout(self.options_tab)
        self.options_tab_layout.setContentsMargins(2, 2, 2, 2)

        hlay1 = QHBoxLayout()
        self.options_tab_layout.addLayout(hlay1)

        self.icon = QLabel()
        self.icon.setPixmap(QPixmap('share/gear48.png'))
        hlay1.addWidget(self.icon)

        self.options_combo = QComboBox()
        self.options_combo.addItem("APPLICATION DEFAULTS")
        self.options_combo.addItem("PROJECT OPTIONS")
        hlay1.addWidget(self.options_combo)
        hlay1.addStretch()

        self.options_scroll_area = VerticalScrollArea()
        self.options_tab_layout.addWidget(self.options_scroll_area)

        self.notebook.addTab(self.options_tab, "Options")

        ### Tool ###
        self.tool_tab = QWidget()
        self.tool_tab_layout = QVBoxLayout(self.tool_tab)
        self.tool_tab_layout.setContentsMargins(2, 2, 2, 2)
        self.notebook.addTab(self.tool_tab, "Tool")
        self.tool_scroll_area = VerticalScrollArea()
        self.tool_tab_layout.addWidget(self.tool_scroll_area)

        self.splitter.addWidget(self.notebook)

        ######################
        ### Plot and other ###
        ######################
        right_widget = OpenGLWidget()
        # right_widget.setContentsMargins(0, 0, 0, 0)
        self.splitter.addWidget(right_widget)
        self.right_layout = QVBoxLayout()
        #self.right_layout.set  .setMargin(0)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        right_widget.setLayout(self.right_layout)

        ################
        ### Info bar ###
        ################
        infobar = self.statusBar()

        #self.info_label = QLabel("Welcome to FlatCAM.")
        #self.info_label.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        #infobar.addWidget(self.info_label, stretch=1)
        self.fcinfo = FlatCAMInfoBar()
        infobar.addWidget(self.fcinfo, stretch=1)

        self.position_label = QLabel("")
        #self.position_label.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        self.position_label.setMinimumWidth(110)
        infobar.addWidget(self.position_label)

        self.units_label = QLabel("[in]")
        # self.units_label.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        self.units_label.setMargin(2)
        infobar.addWidget(self.units_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        #infobar.addWidget(self.progress_bar)

        self.activity_view = FlatCAMActivityView()
        infobar.addWidget(self.activity_view)

        #############
        ### Icons ###
        #############
        self.app_icon = QIcon()
        self.app_icon.addFile('share/flatcam_icon16.png', QSize(16, 16))
        self.app_icon.addFile('share/flatcam_icon24.png', QSize(24, 24))
        self.app_icon.addFile('share/flatcam_icon32.png', QSize(32, 32))
        self.app_icon.addFile('share/flatcam_icon48.png', QSize(48, 48))
        self.app_icon.addFile('share/flatcam_icon128.png', QSize(128, 128))
        self.app_icon.addFile('share/flatcam_icon256.png', QSize(256, 256))
        self.setWindowIcon(self.app_icon)

        self.setGeometry(100, 100, 1024, 650)
        self.setWindowTitle(f"FlatCAM {version} - Development Version")
        self.show()

    def showSelectedTab(self):
        self.notebook.setCurrentIndex(1)

    def eventFilter(self, obj, event):
        """
        Filter the ToolTips display based on a Preferences setting

        :param obj:
        :param event: QT event to filter
        :return:
        """
        print(f"eventFilter({obj}, {event})")
        if self.app.defaults["global_toggle_tooltips"] is False:
            if event.type() == QtCore.QEvent.ToolTip:
                return True
            else:
                return False

        return False

    def closeEvent(self, event):
        grect = self.geometry()
        self.geom_update.emit(grect.x(), grect.y(), grect.width(), grect.height(), self.splitter.sizes()[0])
        QApplication.quit()


class FlatCAMActivityView(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setMinimumWidth(200)

        self.icon = QLabel(self)
        self.icon.setGeometry(0, 0, 12, 12)
        self.movie = QMovie("share/active.gif")
        self.icon.setMovie(self.movie)
        #self.movie.start()

        layout = QHBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setLayout(layout)

        layout.addWidget(self.icon)
        self.text = QLabel(self)
        self.text.setText("Idle.")

        layout.addWidget(self.text)

    def set_idle(self):
        self.movie.stop()
        self.text.setText("Idle.")

    def set_busy(self, msg):
        self.movie.start()
        self.text.setText(msg)


class FlatCAMInfoBar(QWidget):

    def __init__(self, parent=None):
        super(FlatCAMInfoBar, self).__init__(parent=parent)

        self.icon = QLabel(self)
        self.icon.setGeometry(0, 0, 12, 12)
        self.pmap = QPixmap('share/graylight12.png')
        self.icon.setPixmap(self.pmap)

        layout = QHBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)
        self.setLayout(layout)

        layout.addWidget(self.icon)

        self.text = QLabel(self)
        self.text.setText("Ready")
        self.text.setToolTip("Hello!")
        self.set_status("Ready", "success")
        layout.addWidget(self.text)

        layout.addStretch()

    def set_text_(self, text):
        self.text.setText(text)
        self.text.setToolTip(text)

    def set_status(self, text, level="info"):
        level = str(level)
        self.pmap.fill()
        if level == "error":
            self.pmap = QPixmap('share/redlight12.png')
        elif level == "success":
            self.pmap = QPixmap('share/greenlight12.png')
        elif level == "warning":
            self.pmap = QPixmap('share/yellowlight12.png')
        else:
            self.pmap = QPixmap('share/graylight12.png')

        self.icon.setPixmap(self.pmap)
        self.set_text_(text)


class OptionsGroupUI(QGroupBox):
    def __init__(self, title, parent=None):
        QGroupBox.__init__(self, title, parent=parent)
        self.setStyleSheet("""
        QGroupBox
        {
            font-size: 16px;
            font-weight: bold;
        }
        """)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)


class GerberOptionsGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        OptionsGroupUI.__init__(self, "Gerber Options", parent=parent)

        ## Plot options
        self.plot_options_label = QLabel("<b>Plot Options:</b>")
        self.layout.addWidget(self.plot_options_label)

        grid0 = QGridLayout()
        self.layout.addLayout(grid0)
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
        self.layout.addWidget(self.isolation_routing_label)

        grid1 = QGridLayout()
        self.layout.addLayout(grid1)
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
        
        self.combine_passes_cb = FCCheckBox(label='Combine Passes')
        self.combine_passes_cb.setToolTip(
            "Combine all passes into one object"
        )
        grid1.addWidget(self.combine_passes_cb, 3, 0)

        ## Clear non-copper regions
        self.clearcopper_label = QLabel("<b>Clear non-copper:</b>")
        self.clearcopper_label.setToolTip(
            "Create a Geometry object with\n"
            "toolpaths to cut all non-copper regions."
        )
        self.layout.addWidget(self.clearcopper_label)

        grid5 = QGridLayout()
        self.layout.addLayout(grid5)
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

        ## Board cuttout
        self.board_cutout_label = QLabel("<b>Board cutout:</b>")
        self.board_cutout_label.setToolTip(
            "Create toolpaths to cut around\n"
            "the PCB and separate it from\n"
            "the original board."
        )
        self.layout.addWidget(self.board_cutout_label)

        grid2 = QGridLayout()
        self.layout.addLayout(grid2)
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

        ## Non-copper regions
        self.noncopper_label = QLabel("<b>Non-copper regions:</b>")
        self.noncopper_label.setToolTip(
            "Create polygons covering the\n"
            "areas without copper on the PCB.\n"
            "Equivalent to the inverse of this\n"
            "object. Can be used to remove all\n"
            "copper from a specified region."
        )
        self.layout.addWidget(self.noncopper_label)

        grid3 = QGridLayout()
        self.layout.addLayout(grid3)

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

        ## Bounding box
        self.boundingbox_label = QLabel('<b>Bounding Box:</b>')
        self.layout.addWidget(self.boundingbox_label)

        grid4 = QGridLayout()
        self.layout.addLayout(grid4)

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


class ExcellonOptionsGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        OptionsGroupUI.__init__(self, "Excellon Options", parent=parent)

        ## Plot options
        self.plot_options_label = QLabel("<b>Plot Options:</b>")
        self.layout.addWidget(self.plot_options_label)

        grid0 = QGridLayout()
        self.layout.addLayout(grid0)
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

        ## Create CNC Job
        self.cncjob_label = QLabel('<b>Create CNC Job</b>')
        self.cncjob_label.setToolTip(
            "Create a CNC Job object\n"
            "for this drill object."
        )
        self.layout.addWidget(self.cncjob_label)

        grid1 = QGridLayout()
        self.layout.addLayout(grid1)

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

        toolchangezlabel = QLabel('Toolchange Z:')
        toolchangezlabel.setToolTip(
            "Tool Z where user can change drill bit\n"
        )
        grid1.addWidget(toolchangezlabel, 3, 0)
        self.toolchangez_entry = LengthEntry()
        grid1.addWidget(self.toolchangez_entry, 3, 1)

        spdlabel = QLabel('Spindle speed:')
        spdlabel.setToolTip(
            "Speed of the spindle\n"
            "in RPM (optional)"
        )
        grid1.addWidget(spdlabel, 4, 0)
        self.spindlespeed_entry = IntEntry(allow_empty=True)
        grid1.addWidget(self.spindlespeed_entry, 4, 1)

        #### Milling Holes ####
        self.mill_hole_label = QLabel('<b>Mill Holes</b>')
        self.mill_hole_label.setToolTip(
            "Create Geometry for milling holes."
        )
        self.layout.addWidget(self.mill_hole_label)

        grid1 = QGridLayout()
        self.layout.addLayout(grid1)
        tdlabel = QLabel('Tool dia:')
        tdlabel.setToolTip(
            "Diameter of the cutting tool."
        )
        grid1.addWidget(tdlabel, 0, 0)
        self.tooldia_entry = LengthEntry()
        grid1.addWidget(self.tooldia_entry, 0, 1)


class GeometryOptionsGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        OptionsGroupUI.__init__(self, "Geometry Options", parent=parent)

        ## Plot options
        self.plot_options_label = QLabel("<b>Plot Options:</b>")
        self.layout.addWidget(self.plot_options_label)

        # Plot CB
        self.plot_cb = FCCheckBox(label='Plot')
        self.plot_cb.setToolTip(
            "Plot (show) this object."
        )
        self.layout.addWidget(self.plot_cb)

        ## Create CNC Job
        self.cncjob_label = QLabel('<b>Create CNC Job:</b>')
        self.cncjob_label.setToolTip(
            "Create a CNC Job object\n"
            "tracing the contours of this\n"
            "Geometry object."
        )
        self.layout.addWidget(self.cncjob_label)

        grid1 = QGridLayout()
        self.layout.addLayout(grid1)

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

        spdlabel = QLabel('Spindle speed:')
        spdlabel.setToolTip(
            "Speed of the spindle\n"
            "in RPM (optional)"
        )
        grid1.addWidget(spdlabel, 4, 0)
        self.cncspindlespeed_entry = IntEntry(allow_empty=True)
        grid1.addWidget(self.cncspindlespeed_entry, 4, 1)

        ## Paint area
        self.paint_label = QLabel('<b>Paint Area:</b>')
        self.paint_label.setToolTip(
            "Creates tool paths to cover the\n"
            "whole area of a polygon (remove\n"
            "all copper). You will be asked\n"
            "to click on the desired polygon."
        )
        self.layout.addWidget(self.paint_label)

        grid2 = QGridLayout()
        self.layout.addLayout(grid2)

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
        grid2.addWidget(self.paintmargin_entry)


class CNCJobOptionsGroupUI(OptionsGroupUI):
    def __init__(self, parent=None):
        OptionsGroupUI.__init__(self, "CNC Job Options", parent=None)

        ## Plot options
        self.plot_options_label = QLabel("<b>Plot Options:</b>")
        self.layout.addWidget(self.plot_options_label)

        grid0 = QGridLayout()
        self.layout.addLayout(grid0)

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

        ## Export G-Code
        self.export_gcode_label = QLabel("<b>Export G-Code:</b>")
        self.export_gcode_label.setToolTip(
            "Export and save G-Code to\n"
            "make this object to a file."
        )
        self.layout.addWidget(self.export_gcode_label)

        # Prepend to G-Code
        prependlabel = QLabel('Prepend to G-Code:')
        prependlabel.setToolTip(
            "Type here any G-Code commands you would\n"
            "like to add at the beginning of the G-Code file."
        )
        self.layout.addWidget(prependlabel)

        self.prepend_text = FCTextArea()
        self.layout.addWidget(self.prepend_text)

        # Append text to G-Code
        appendlabel = QLabel('Append to G-Code:')
        appendlabel.setToolTip(
            "Type here any G-Code commands you would\n"
            "like to append to the generated file.\n"
            "I.e.: M2 (End of program)"
        )
        self.layout.addWidget(appendlabel)

        self.append_text = FCTextArea()
        self.layout.addWidget(self.append_text)

        # Dwell
        grid1 = QGridLayout()
        self.layout.addLayout(grid1)

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
        self.dwelltime_cb = FCEntry()
        grid1.addWidget(dwelllabel, 0, 0)
        grid1.addWidget(self.dwell_cb, 0, 1)
        grid1.addWidget(dwelltime, 1, 0)
        grid1.addWidget(self.dwelltime_cb, 1, 1)


class GlobalOptionsUI(QWidget):
    """
    This is the app and project options editor.
    """
    def __init__(self, parent=None):
        QWidget.__init__(self, parent=parent)

        layout = QVBoxLayout()
        self.setLayout(layout)

        hlay1 = QHBoxLayout()
        layout.addLayout(hlay1)
        unitslabel = QLabel('Units:')
        hlay1.addWidget(unitslabel)
        self.units_radio = RadioSet([{'label': 'inch', 'value': 'IN'},
                                     {'label': 'mm', 'value': 'MM'}])
        hlay1.addWidget(self.units_radio)

        ####### Gerber #######
        # gerberlabel = QLabel('<b>Gerber Options</b>')
        # layout.addWidget(gerberlabel)
        self.gerber_group = GerberOptionsGroupUI()
        # self.gerber_group.setFrameStyle(QFrame.StyledPanel)
        layout.addWidget(self.gerber_group)

        ####### Excellon #######
        # excellonlabel = QLabel('<b>Excellon Options</b>')
        # layout.addWidget(excellonlabel)
        self.excellon_group = ExcellonOptionsGroupUI()
        # self.excellon_group.setFrameStyle(QFrame.StyledPanel)
        layout.addWidget(self.excellon_group)

        ####### Geometry #######
        # geometrylabel = QLabel('<b>Geometry Options</b>')
        # layout.addWidget(geometrylabel)
        self.geometry_group = GeometryOptionsGroupUI()
        # self.geometry_group.setStyle(QFrame.StyledPanel)
        layout.addWidget(self.geometry_group)

        ####### CNC #######
        # cnclabel = QLabel('<b>CNC Job Options</b>')
        # layout.addWidget(cnclabel)
        self.cncjob_group = CNCJobOptionsGroupUI()
        # self.cncjob_group.setStyle(QFrame.StyledPanel)
        layout.addWidget(self.cncjob_group)

