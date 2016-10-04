# -*- coding: utf-8 -*-
'''
Compile the tutorial user interfaces
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
@date: $Date: 2011-03-24 16:03:45 +0100 (Do, 24 Mrz 2011) $
@version: 1.0

B{Revision:} $LastChangedRevision: 62 $
'''

from PyQt4 import uic

if __name__ == '__main__':
    f = open("frmTUT4Online.py", "w")
    uic.compileUi("frmTUT4Online.ui", f)
    f.close()

