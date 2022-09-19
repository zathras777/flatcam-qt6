from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout, QHBoxLayout, \
    QGridLayout, QPushButton
from PyQt6.QtGui import QPixmap

from GUIElements import FCEntry, FloatEntry, EvalEntry


class ObjectUI(QWidget):
    """
    Base class for the UI of FlatCAM objects. Deriving classes should
    put UI elements in ObjectUI.custom_box (QLayout).
    """

    def __init__(self, icon_file='share/flatcam_icon32.png', title='FlatCAM Object', parent=None):
        QWidget.__init__(self, parent=parent)

        layout = QVBoxLayout()
        self.setLayout(layout)

        ## Page Title box (spacing between children)
        self.title_box = QHBoxLayout()
        layout.addLayout(self.title_box)

        ## Page Title icon
        pixmap = QPixmap(icon_file)
        self.icon = QLabel("")
        self.icon.setPixmap(pixmap)
        self.title_box.addWidget(self.icon, stretch=0)

        ## Title label
        self.title_label = QLabel("<font size=5><b>" + title + "</b></font>")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.title_box.addWidget(self.title_label, stretch=1)

        ## Object name
        self.name_box = QHBoxLayout()
        layout.addLayout(self.name_box)
        name_label = QLabel("Name:")
        self.name_box.addWidget(name_label)
        self.name_entry = FCEntry()
        self.name_box.addWidget(self.name_entry)

        ## Box box for custom widgets
        # This gets populated in offspring implementations.
        self.custom_box = QVBoxLayout()
        layout.addLayout(self.custom_box)

        ###########################
        ## Common to all objects ##
        ###########################

        #### Scale ####
        self.scale_label = QLabel('<b>Scale:</b>')
        self.scale_label.setToolTip(
            "Change the size of the object."
        )
        layout.addWidget(self.scale_label)

        self.scale_grid = QGridLayout()
        layout.addLayout(self.scale_grid)

        # Factor
        faclabel = QLabel('Factor:')
        faclabel.setToolTip(
            "Factor by which to multiply\n"
            "geometric features of this object."
        )
        self.scale_grid.addWidget(faclabel, 0, 0)
        self.scale_entry = FloatEntry()
        self.scale_entry.set_value(1.0)
        self.scale_grid.addWidget(self.scale_entry, 0, 1)

        # GO Button
        self.scale_button = QPushButton('Scale')
        self.scale_button.setToolTip(
            "Perform scaling operation."
        )
        layout.addWidget(self.scale_button)

        #### Offset ####
        self.offset_label = QLabel('<b>Offset:</b>')
        self.offset_label.setToolTip(
            "Change the position of this object."
        )
        layout.addWidget(self.offset_label)

        self.offset_grid = QGridLayout()
        layout.addLayout(self.offset_grid)

        self.offset_vectorlabel = QLabel('Vector:')
        self.offset_vectorlabel.setToolTip(
            "Amount by which to move the object\n"
            "in the x and y axes in (x, y) format."
        )
        self.offset_grid.addWidget(self.offset_vectorlabel, 0, 0)
        self.offsetvector_entry = EvalEntry()
        self.offsetvector_entry.setText("(0.0, 0.0)")
        self.offset_grid.addWidget(self.offsetvector_entry, 0, 1)

        self.offset_button = QPushButton('Offset')
        self.offset_button.setToolTip(
            "Perform the offset operation."
        )
        layout.addWidget(self.offset_button)

        layout.addStretch()
