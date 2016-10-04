# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'frmLogView.ui'
#
# Created: Wed Jun 05 12:00:50 2013
#      by: PyQt4 UI code generator 4.5.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_frmLogView(object):
    def setupUi(self, frmLogView):
        frmLogView.setObjectName("frmLogView")
        frmLogView.resize(880, 400)
        self.gridLayout = QtGui.QGridLayout(frmLogView)
        self.gridLayout.setObjectName("gridLayout")
        self.labelView = QtGui.QPlainTextEdit(frmLogView)
        self.labelView.setLineWrapMode(QtGui.QPlainTextEdit.NoWrap)
        self.labelView.setReadOnly(True)
        self.labelView.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        self.labelView.setBackgroundVisible(False)
        self.labelView.setObjectName("labelView")
        self.gridLayout.addWidget(self.labelView, 0, 1, 1, 1)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.pushButtonSave = QtGui.QPushButton(frmLogView)
        self.pushButtonSave.setAutoDefault(False)
        self.pushButtonSave.setObjectName("pushButtonSave")
        self.horizontalLayout.addWidget(self.pushButtonSave)
        self.pushButtonClose = QtGui.QPushButton(frmLogView)
        self.pushButtonClose.setDefault(True)
        self.pushButtonClose.setObjectName("pushButtonClose")
        self.horizontalLayout.addWidget(self.pushButtonClose)
        self.gridLayout.addLayout(self.horizontalLayout, 1, 1, 1, 1)

        self.retranslateUi(frmLogView)
        QtCore.QObject.connect(self.pushButtonClose, QtCore.SIGNAL("clicked()"), frmLogView.reject)
        QtCore.QObject.connect(self.pushButtonSave, QtCore.SIGNAL("clicked()"), frmLogView.accept)
        QtCore.QMetaObject.connectSlotsByName(frmLogView)

    def retranslateUi(self, frmLogView):
        frmLogView.setWindowTitle(QtGui.QApplication.translate("frmLogView", "Log History", None, QtGui.QApplication.UnicodeUTF8))
        self.pushButtonSave.setText(QtGui.QApplication.translate("frmLogView", "Save", None, QtGui.QApplication.UnicodeUTF8))
        self.pushButtonClose.setText(QtGui.QApplication.translate("frmLogView", "Close", None, QtGui.QApplication.UnicodeUTF8))

