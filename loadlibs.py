# -*- coding: utf-8 -*-
'''
Load required libraries and check versions  

PyCorder ActiChamp Recorder

------------------------------------------------------------

Copyright (C) 2010, Brain Products GmbH, Gilching

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


'''
------------------------------------------------------------
CHECK LIBRARY DEPENDENCIES
------------------------------------------------------------
'''

import sys

import_log = ""

# required Python and library versions
if sys.version_info[:2] == (2,7):
    #import_log += "Untested PyCorder running on Python Version 2.7 !\r\n\r\n"
    ver_Python = "2.7"
    ver_NumPy =  ("1.8.2")
    ver_SciPy =  ("0.14.0")
    ver_PyQt =   ("4.8.6")
    ver_PyQwt =  ("5.2.3",)
    ver_lxml =   ("3.3.6")
else:
    ver_Python = "2.6"
    ver_NumPy =  ("1.3.0", "1.4.1")
    ver_SciPy =  ("0.7.1", "0.8.0")
    ver_PyQt =   ("4.5.2", "4.6.3")
    ver_PyQwt =  ("5.2.1",)
    ver_lxml =   ("2.2.4", "2.2.7")

    
# try to import python libraries, check versions
if not ver_Python in sys.version:
    import_log += "- Wrong Python version (%s), please install Python %s\r\n"%(sys.version, ver_Python) 
try:
    import numpy as np
    if not np.__version__ in ver_NumPy:
        import_log += "- Wrong NumPy version (%s), please install NumPy %s\r\n"%(np.__version__, ver_NumPy) 
except ImportError:
    import_log += "- NumPy missing, please install NumPy %s\r\n"%(str(ver_NumPy))

try:
    import scipy as sc
    if not sc.__version__ in ver_SciPy:
        import_log += "- Wrong SciPy version (%s), please install SciPy %s\r\n"%(sc.__version__, ver_SciPy) 
except ImportError:
    import_log += "- SciPy missing, please install SciPy %s\r\n"%(str(ver_SciPy))

try:
    from PyQt4 import Qt
    if not Qt.QT_VERSION_STR in ver_PyQt:
        import_log += "- Wrong PyQt version (%s), please install PyQt %s\r\n"%(Qt.QT_VERSION_STR, ver_PyQt) 
except ImportError:
    import_log += "- PyQt missing, please install PyQt %s\r\n"%(str(ver_PyQt))

try:
    from PyQt4 import Qwt5 as Qwt
    if not Qwt.QWT_VERSION_STR in ver_PyQwt:
        import_log += "- Wrong PyQwt version (%s), please install PyQwt %s\r\n"%(Qwt.QWT_VERSION_STR, ver_PyQwt) 
except ImportError:
    import_log += "- PyQwt missing, please install PyQwt %s\r\n"%(str(ver_PyQwt))

try:
    from lxml import etree
    if not etree.__version__ in ver_lxml:
        import_log += "- Wrong lxml version (%s), please install lxml %s\r\n"%(etree.__version__, ver_lxml) 
except ImportError:
    import_log += "- lxml missing, please install lxml %s\r\n"%(str(ver_lxml))
    
