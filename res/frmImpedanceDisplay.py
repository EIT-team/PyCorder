# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'frmImpedanceDisplay.ui'
#
# Created: Wed Jun 05 12:00:50 2013
#      by: PyQt4 UI code generator 4.5.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_frmImpedanceDisplay(object):
    def setupUi(self, frmImpedanceDisplay):
        frmImpedanceDisplay.setObjectName("frmImpedanceDisplay")
        frmImpedanceDisplay.resize(1100, 744)
        frmImpedanceDisplay.setSizeGripEnabled(True)
        self.gridLayout_2 = QtGui.QGridLayout(frmImpedanceDisplay)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.tableWidgetValues = QtGui.QTableWidget(frmImpedanceDisplay)
        self.tableWidgetValues.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.tableWidgetValues.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
        self.tableWidgetValues.setRowCount(16)
        self.tableWidgetValues.setColumnCount(10)
        self.tableWidgetValues.setObjectName("tableWidgetValues")
        self.tableWidgetValues.setColumnCount(10)
        self.tableWidgetValues.setRowCount(16)
        self.tableWidgetValues.horizontalHeader().setCascadingSectionResizes(False)
        self.tableWidgetValues.horizontalHeader().setDefaultSectionSize(70)
        self.tableWidgetValues.horizontalHeader().setHighlightSections(True)
        self.tableWidgetValues.horizontalHeader().setMinimumSectionSize(10)
        self.tableWidgetValues.verticalHeader().setDefaultSectionSize(40)
        self.gridLayout_2.addWidget(self.tableWidgetValues, 0, 0, 1, 1)
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.groupBoxRange = QtGui.QGroupBox(frmImpedanceDisplay)
        self.groupBoxRange.setObjectName("groupBoxRange")
        self.gridLayout = QtGui.QGridLayout(self.groupBoxRange)
        self.gridLayout.setObjectName("gridLayout")
        self.ScaleWidget = Qwt5.QwtScaleWidget(self.groupBoxRange)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.ScaleWidget.sizePolicy().hasHeightForWidth())
        self.ScaleWidget.setSizePolicy(sizePolicy)
        self.ScaleWidget.setMinimumSize(QtCore.QSize(80, 0))
        self.ScaleWidget.setObjectName("ScaleWidget")
        self.gridLayout.addWidget(self.ScaleWidget, 0, 0, 1, 1)
        self.checkBoxValues = QtGui.QCheckBox(self.groupBoxRange)
        self.checkBoxValues.setObjectName("checkBoxValues")
        self.gridLayout.addWidget(self.checkBoxValues, 3, 0, 1, 1)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label = QtGui.QLabel(self.groupBoxRange)
        self.label.setObjectName("label")
        self.horizontalLayout_2.addWidget(self.label)
        self.comboBoxRange = QtGui.QComboBox(self.groupBoxRange)
        self.comboBoxRange.setEditable(True)
        self.comboBoxRange.setInsertPolicy(QtGui.QComboBox.NoInsert)
        self.comboBoxRange.setObjectName("comboBoxRange")
        self.comboBoxRange.addItem(QtCore.QString())
        self.comboBoxRange.addItem(QtCore.QString())
        self.comboBoxRange.addItem(QtCore.QString())
        self.comboBoxRange.addItem(QtCore.QString())
        self.horizontalLayout_2.addWidget(self.comboBoxRange)
        self.label_2 = QtGui.QLabel(self.groupBoxRange)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_2.addWidget(self.label_2)
        self.gridLayout.addLayout(self.horizontalLayout_2, 1, 0, 1, 1)
        self.verticalLayout.addWidget(self.groupBoxRange)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.gridLayout_2.addLayout(self.verticalLayout, 0, 1, 1, 1)

        self.retranslateUi(frmImpedanceDisplay)
        QtCore.QMetaObject.connectSlotsByName(frmImpedanceDisplay)

    def retranslateUi(self, frmImpedanceDisplay):
        frmImpedanceDisplay.setWindowTitle(QtGui.QApplication.translate("frmImpedanceDisplay", "Impedance", None, QtGui.QApplication.UnicodeUTF8))
        self.groupBoxRange.setTitle(QtGui.QApplication.translate("frmImpedanceDisplay", "Range [KOhm]", None, QtGui.QApplication.UnicodeUTF8))
        self.checkBoxValues.setText(QtGui.QApplication.translate("frmImpedanceDisplay", "Show Values", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("frmImpedanceDisplay", "0 - ", None, QtGui.QApplication.UnicodeUTF8))
        self.comboBoxRange.setItemText(0, QtGui.QApplication.translate("frmImpedanceDisplay", "5", None, QtGui.QApplication.UnicodeUTF8))
        self.comboBoxRange.setItemText(1, QtGui.QApplication.translate("frmImpedanceDisplay", "20", None, QtGui.QApplication.UnicodeUTF8))
        self.comboBoxRange.setItemText(2, QtGui.QApplication.translate("frmImpedanceDisplay", "50", None, QtGui.QApplication.UnicodeUTF8))
        self.comboBoxRange.setItemText(3, QtGui.QApplication.translate("frmImpedanceDisplay", "100", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("frmImpedanceDisplay", "KOhm", None, QtGui.QApplication.UnicodeUTF8))

from PyQt4 import Qwt5
