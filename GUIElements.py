import re
import logging

from copy import copy
from PyQt6 import QtCore
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QScrollArea, QWidget, QTableWidget, \
    QPlainTextEdit, QCheckBox, QHBoxLayout, QVBoxLayout, \
        QButtonGroup, QRadioButton, QLineEdit
from PyQt6.QtCore import QEvent, pyqtSignal


log = logging.getLogger('GuiElements')

EDIT_SIZE_HINT = 80


class RadioSet(QWidget):
    activated_custom = pyqtSignal()

    def __init__(self, choices, orientation='horizontal', parent=None):
        """
        The choices are specified as a list of dictionaries containing:

        * 'label': Shown in the UI
        * 'value': The value returned is selected

        :param choices: List of choices. See description.
        :type choices: list
        """
        super().__init__(parent)
        self.choices = copy(choices)

        if orientation == 'horizontal':
            layout = QHBoxLayout()
        else:
            layout = QVBoxLayout()

        group = QButtonGroup(self)

        for choice in self.choices:
            choice['radio'] = QRadioButton(choice['label'])
            group.addButton(choice['radio'])
            layout.addWidget(choice['radio'], stretch=0)
            choice['radio'].toggled.connect(self.on_toggle)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch()
        self.setLayout(layout)

        self.group_toggle_fn = lambda: None

    def on_toggle(self):
        log.debug("Radio toggled")
        radio = self.sender()
        # TODO - catch error if sender isn't a QRadioButton
        try:
            if radio.isChecked():
                self.group_toggle_fn()
                self.activated_custom.emit()
        except AttributeError as e:
            log.debug(f"Tried to treat {radio} as a QRadioButton, but it's not? {type(radio)}")

        return

    def get_value(self):
        for choice in self.choices:
            if choice['radio'].isChecked():
                return choice['value']
        log.error("No button was toggled in RadioSet.")
        return None

    def set_value(self, val):
        for choice in self.choices:
            if choice['value'] == val:
                choice['radio'].setChecked(True)
                return
        log.error("Value given is not part of this RadioSet: %s" % str(val))


class LengthEntry(QLineEdit):
    def __init__(self, output_units='IN', parent=None):
        super().__init__(parent)

        self.output_units = output_units
        self.format_re = re.compile(r"^([^\s]+)(?:\s([a-zA-Z]+))?$")

        # Unit conversion table OUTPUT-INPUT
        self.scales = {
            'IN': {'IN': 1.0,
                   'MM': 1/25.4},
            'MM': {'IN': 25.4,
                   'MM': 1.0}
        }

    def returnPressed(self, *args, **kwargs):
        val = self.get_value()
        if val is not None:
            self.set_text(str(val))
        else:
            log.warning("Could not interpret entry: %s" % self.get_text())

    def get_value(self):
        raw = str(self.text()).strip(' ')
        # match = self.format_re.search(raw)

        try:
            units = raw[-2:]
            units = self.scales[self.output_units][units.upper()]
            value = raw[:-2]
            return float(eval(value))*units
        except IndexError:
            value = raw
            return float(eval(value))
        except KeyError:
            value = raw
            return float(eval(value))
        except:
            log.warning("Could not parse value in entry: %s" % str(raw))
            return None

    def set_value(self, val):
        self.setText(str(val))

    def sizeHint(self):
        default_hint_size = super().sizeHint()
        return QtCore.QSize(EDIT_SIZE_HINT, default_hint_size.height())


class FloatEntry(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

    def returnPressed(self, *args, **kwargs):
        val = self.get_value()
        if val is not None:
            self.set_text(str(val))
        else:
            log.warning("Could not interpret entry: %s" % self.text())

    def get_value(self):
        raw = str(self.text()).strip(' ')
        try:
            evaled = eval(raw)
        except:
            log.error("Could not evaluate: %s" % str(raw))
            return None

        return float(evaled)

    def set_value(self, val):
        self.setText("%.6f" % val)

    def sizeHint(self):
        default_hint_size = super().sizeHint()
        return QSize(EDIT_SIZE_HINT, default_hint_size.height())


class IntEntry(QLineEdit):

    def __init__(self, parent=None, allow_empty=False, empty_val=None):
        super().__init__(parent)
        self.allow_empty = allow_empty
        self.empty_val = empty_val

    def get_value(self):

        if self.allow_empty:
            if str(self.text()) == "":
                return self.empty_val

        return int(self.text())

    def set_value(self, val):

        if val == self.empty_val and self.allow_empty:
            self.setText(str(""))
            return

        self.setText(str(val))

    def sizeHint(self):
        default_hint_size = super().sizeHint()
        return QSize(EDIT_SIZE_HINT, default_hint_size.height())


class FCEntry(QLineEdit):
    def __init__(self, parent=None):
        super(FCEntry, self).__init__(parent)

    def get_value(self):
        return str(self.text())

    def set_value(self, val):
        self.setText(str(val))

    def sizeHint(self):
        default_hint_size = super().sizeHint()
        return QSize(EDIT_SIZE_HINT, default_hint_size.height())


class EvalEntry(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

    def returnPressed(self, *args, **kwargs):
        val = self.get_value()
        if val is not None:
            self.setText(str(val))
        else:
            log.warning("Could not interpret entry: %s" % self.get_text())

    def get_value(self):
        raw = str(self.text()).strip(' ')
        try:
            return eval(raw)
        except:
            log.error("Could not evaluate: %s" % str(raw))
            return None

    def set_value(self, val):
        self.setText(str(val))

    def sizeHint(self):
        default_hint_size = super().sizeHint()
        return QSize(EDIT_SIZE_HINT, default_hint_size.height())


class FCCheckBox(QCheckBox):
    def __init__(self, label='', parent=None):
        super().__init__(str(label), parent)

    def get_value(self):
        return self.isChecked()

    def set_value(self, val):
        self.setChecked(val)

    def toggle(self):
        self.set_value(not self.get_value())


class FCTextArea(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

    def set_value(self, val):
        self.setPlainText(val)

    def get_value(self):
        return str(self.toPlainText())

    def sizeHint(self):
        default_hint_size = super().sizeHint()
        return QSize(EDIT_SIZE_HINT, default_hint_size.height())


class VerticalScrollArea(QScrollArea):
    """
    This widget extends QtGui.QScrollArea to make a vertical-only
    scroll area that also expands horizontally to accomodate
    its contents.
    """
    def __init__(self, parent=None):
        QScrollArea.__init__(self, parent=parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def eventFilter(self, source, event):
        """
        The event filter gets automatically installed when setWidget()
        is called.

        :param source:
        :param event:
        :return:
        """
        if event.type() == QEvent.Type.Resize and source == self.widget():
            # log.debug("VerticalScrollArea: Widget resized:")
            # log.debug(" minimumSizeHint().width() = %d" % self.widget().minimumSizeHint().width())
            # log.debug(" verticalScrollBar().width() = %d" % self.verticalScrollBar().width())

            self.setMinimumWidth(self.widget().sizeHint().width() +
                                 self.verticalScrollBar().sizeHint().width())

            # if self.verticalScrollBar().isVisible():
            #     log.debug(" Scroll bar visible")
            #     self.setMinimumWidth(self.widget().minimumSizeHint().width() +
            #                          self.verticalScrollBar().width())
            # else:
            #     log.debug(" Scroll bar hidden")
            #     self.setMinimumWidth(self.widget().minimumSizeHint().width())
        return QWidget.eventFilter(self, source, event)


class OptionalInputSection:

    def __init__(self, cb, optinputs):
        """
        Associates the a checkbox with a set of inputs.

        :param cb: Checkbox that enables the optional inputs.
        :param optinputs: List of widgets that are optional.
        :return:
        """
        assert isinstance(cb, FCCheckBox), \
            "Expected an FCCheckBox, got %s" % type(cb)

        self.cb = cb
        self.optinputs = optinputs

        self.on_cb_change()
        self.cb.stateChanged.connect(self.on_cb_change)

    def on_cb_change(self):

        if self.cb.checkState():

            for widget in self.optinputs:
                widget.setEnabled(True)

        else:

            for widget in self.optinputs:
                widget.setEnabled(False)


class FCTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def sizeHint(self):
        default_hint_size = super().sizeHint()
        return QSize(EDIT_SIZE_HINT, default_hint_size.height())
