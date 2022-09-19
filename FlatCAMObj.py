import inspect  # TODO: For debugging only.
import re
import sys

from copy import copy
from io import StringIO
from PyQt6.QtCore import pyqtSignal, Qt, QObject, QTimer
from PyQt6.QtWidgets import QTableWidgetItem, QFileDialog
from shapely import affinity
from shapely.geometry import Point
from shapely.geometry.base import JOIN_STYLE

import FlatCAMApp

from FlatCAMCommon import LoudDict
from fcObjects.base import ObjectUI
from fcCamlib.geometry import Geometry


# Interrupts plotting process if FlatCAMObj has been deleted
class ObjectDeleted(Exception):
    pass


########################################
##            FlatCAMObj              ##
########################################
class FlatCAMObj(QObject):
    """
    Base type of objects handled in FlatCAM. These become interactive
    in the GUI, can be plotted, and their options can be modified
    by the user in their respective forms.
    """

    # Instance of the application to which these are related.
    # The app should set this value.
    app = None
    optionChanged = pyqtSignal(str)

    def __init__(self, name):
        """

        :param name: Name of the object given by the user.
        :return: FlatCAMObj
        """
        QObject.__init__(self)

        # View
        self.ui = None

        self.options = LoudDict(name=name)
        self.options.set_change_callback(self.on_options_change)

        self.form_fields = {}

        self.kind = None  # Override with proper name

        # self.shapes = ShapeCollection(parent=self.app.plotcanvas.vispy_canvas.view.scene)
        self.shapes = self.app.plotcanvas.new_shape_group()

        self.item = None  # Link with project view item

        self.muted_ui = False
        self.deleted = False

        self._drawing_tolerance = 0.01

        # assert isinstance(self.ui, ObjectUI)
        # self.ui.name_entry.returnPressed.connect(self.on_name_activate)
        # self.ui.offset_button.clicked.connect(self.on_offset_button_click)
        # self.ui.scale_button.clicked.connect(self.on_scale_button_click)

    def __del__(self):
        pass

    def from_dict(self, d):
        """
        This supersedes ``from_dict`` in derived classes. Derived classes
        must inherit from FlatCAMObj first, then from derivatives of Geometry.

        ``self.options`` is only updated, not overwritten. This ensures that
        options set by the app do not vanish when reading the objects
        from a project file.
        """

        for attr in self.ser_attrs:

            if attr == 'options':
                self.options.update(d[attr])
            else:
                setattr(self, attr, d[attr])

    def on_options_change(self, key):
        # Update form on programmatically options change
        self.set_form_item(key)

        # Set object visibility
        if key == 'plot':
            self.visible = self.options['plot']
        self.optionChanged.emit(key)

    def set_ui(self, ui):
        self.ui = ui

        self.form_fields = {"name": self.ui.name_entry}

        assert isinstance(self.ui, ObjectUI)
        self.ui.name_entry.returnPressed.connect(self.on_name_activate)
        self.ui.offset_button.clicked.connect(self.on_offset_button_click)
        self.ui.scale_button.clicked.connect(self.on_scale_button_click)

    def __str__(self):
        return "<FlatCAMObj({:12s}): {:20s}>".format(self.kind, self.options["name"])

    def on_name_activate(self):
        old_name = copy(self.options["name"])
        new_name = self.ui.name_entry.get_value()
        self.options["name"] = self.ui.name_entry.get_value()
        self.app.info("Name changed from %s to %s" % (old_name, new_name))

    def on_offset_button_click(self):
        self.app.report_usage("obj_on_offset_button")

        self.read_form()
        vect = self.ui.offsetvector_entry.get_value()
        self.offset(vect)
        self.plot()

    def on_scale_button_click(self):
        self.app.report_usage("obj_on_scale_button")
        self.read_form()
        factor = self.ui.scale_entry.get_value()
        self.scale(factor)
        self.plot()

    def to_form(self):
        """
        Copies options to the UI form.

        :return: None
        """
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + "--> FlatCAMObj.to_form()")
        for option in self.options:
            try:
                self.set_form_item(option)
            except:
                self.app.log.warning("Unexpected error:", sys.exc_info())

    def read_form(self):
        """
        Reads form into ``self.options``.

        :return: None
        :rtype: None
        """
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + "--> FlatCAMObj.read_form()")
        for option in self.options:
            try:
                self.read_form_item(option)
            except:
                self.app.log.warning("Unexpected error:", sys.exc_info())

    def build_ui(self):
        """
        Sets up the UI/form for this object. Show the UI
        in the App.

        :return: None
        :rtype: None
        """

        self.muted_ui = True
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + "--> FlatCAMObj.build_ui()")

        # Remove anything else in the box
        # box_children = self.app.ui.notebook.selected_contents.get_children()
        # for child in box_children:
        #     self.app.ui.notebook.selected_contents.remove(child)
        # while self.app.ui.selected_layout.count():
        #     self.app.ui.selected_layout.takeAt(0)

        # Put in the UI
        # box_selected.pack_start(sw, True, True, 0)
        # self.app.ui.notebook.selected_contents.add(self.ui)
        # self.app.ui.selected_layout.addWidget(self.ui)
        try:
            self.app.ui.selected_scroll_area.takeWidget()
        except:
            self.app.log.debug("Nothing to remove")
        self.app.ui.selected_scroll_area.setWidget(self.ui)

        self.muted_ui = False

    def set_form_item(self, option):
        """
        Copies the specified option to the UI form.

        :param option: Name of the option (Key in ``self.options``).
        :type option: str
        :return: None
        """

        try:
            self.form_fields[option].set_value(self.options[option])
        except KeyError:
            self.app.log.warn("Tried to set an option or field that does not exist: %s" % option)

    def read_form_item(self, option):
        """
        Reads the specified option from the UI form into ``self.options``.

        :param option: Name of the option.
        :type option: str
        :return: None
        """

        try:
            self.options[option] = self.form_fields[option].get_value()
        except KeyError:
            self.app.log.warning("Failed to read option from field: %s" % option)

        # #try read field only when option have equivalent in form_fields
        # if option in self.form_fields:
        #     option_type=type(self.options[option])
        #     try:
        #         value=self.form_fields[option].get_value()
        #     #catch per option as it was ignored anyway, also when syntax error (probably uninitialized field),don't read either.
        #     except (KeyError,SyntaxError):
        #         self.app.log.warning("Failed to read option from field: %s" % option)
        # else:
        #     self.app.log.warning("Form fied does not exists: %s" % option)

    def plot(self):
        """
        Plot this object (Extend this method to implement the actual plotting).
        Call this in descendants before doing the plotting.

        :return: Whether to continue plotting or not depending on the "plot" option.
        :rtype: bool
        """
        FlatCAMApp.App.log.debug(str(inspect.stack()[1][3]) + " --> FlatCAMObj.plot()")

        if self.deleted:
            return False

        self.clear()

        return True

    def serialize(self):
        """
        Returns a representation of the object as a dictionary so
        it can be later exported as JSON. Override this method.

        :return: Dictionary representing the object
        :rtype: dict
        """
        return

    def deserialize(self, obj_dict):
        """
        Re-builds an object from its serialized version.

        :param obj_dict: Dictionary representing a FlatCAMObj
        :type obj_dict: dict
        :return: None
        """
        return

    def add_shape(self, **kwargs):
        if self.deleted:
            raise ObjectDeleted()
        else:
            self.shapes.add(tolerance=self.drawing_tolerance, **kwargs)

    @property
    def visible(self):
        return self.shapes.visible

    @visible.setter
    def visible(self, value):
        self.shapes.visible = value

        # Not all object types has annotations
        try:
            self.annotation.visible = value
        except AttributeError:
            pass

    @property
    def drawing_tolerance(self):
        return self._drawing_tolerance if self.units == 'MM' or not self.units else self._drawing_tolerance / 25.4

    @drawing_tolerance.setter
    def drawing_tolerance(self, value):
        self._drawing_tolerance = value if self.units == 'MM' or not self.units else value / 25.4

    def clear(self, update=False):
        self.shapes.clear(update)

        # Not all object types has annotations
        try:
            self.annotation.clear(update)
        except AttributeError:
            pass

    def delete(self):
        # Free resources
        del self.ui
        del self.options

        # Set flag
        self.deleted = True
