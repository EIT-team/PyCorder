# -*- coding: utf-8 -*-
'''
Compile the user interface
PyCorder ActiChamp Recorder

------------------------------------------------------------

Copyright (C) 2010, Brain Products GmbH, Gilching

            This file is part of PyCorder

PyCorder is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PyCorder. If not, see <http://www.gnu.org/licenses/>.

------------------------------------------------------------

@author: Norbert Hauser
'''

from PyQt4 import uic

if __name__ == '__main__':
    f = open("frmMain.py", "w")
    uic.compileUi("frmMain.ui", f)
    f.close()

    f = open("frmScopeOnline.py", "w")
    uic.compileUi("frmScopeOnline.ui", f)
    f.close()

    f = open("frmActiChampOnline.py", "w")
    uic.compileUi("frmActiChampOnline.ui", f)
    f.close()

    f = open("frmActiChampConfig.py", "w")
    uic.compileUi("frmActiChampConfig.ui", f)
    f.close()

    f = open("frmMainConfiguration.py", "w")
    uic.compileUi("frmMainConfiguration.ui", f)
    f.close()

    f = open("frmStorageVisionOnline.py", "w")
    uic.compileUi("frmStorageVisionOnline.ui", f)
    f.close()

    f = open("frmStorageVisionConfig.py", "w")
    uic.compileUi("frmStorageVisionConfig.ui", f)
    f.close()

    f = open("frmMainStatusBar.py", "w")
    uic.compileUi("frmMainStatusBar.ui", f)
    f.close()

    f = open("frmLogView.py", "w")
    uic.compileUi("frmLogView.ui", f)
    f.close()

    f = open("frmImpedanceDisplay.py", "w")
    uic.compileUi("frmImpedanceDisplay.ui", f)
    f.close()

    f = open("frmFilterConfig.py", "w")
    uic.compileUi("frmFilterConfig.ui", f)
    f.close()

    f = open("frmRdaClientOnline.py", "w")
    uic.compileUi("frmRdaClientOnline.ui", f)
    f.close()

