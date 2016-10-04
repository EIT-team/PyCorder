# -*- coding: utf-8 -*-
'''
Generic Model/View Table

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
@date: $Date: 2013-06-05 12:04:17 +0200 (Mi, 05 Jun 2013) $
@version: 1.0

B{Revision:} $LastChangedRevision: 197 $
'''

from PyQt4 import Qt
import types



class GenericTableWidget(Qt.QTableView):
    ''' Generic model/view table widget
    Table view for a list of data objects:
    The view content is defined by a list of column dictionaries
        dictionary: {'variable':'variable name', 'header':'header text', 
                     'edit':False/True, 'editor':'default' or 'combobox' or 'plaintext'}
        optional entries: 'min': minum value, 'max': maximum value, 
                          'dec': number of decimal places, 'step': spin box incr/decr
                          'indexed' : True, use value as combobox index  
    If a column is defined as combobox, the cb list text items can also be defined in a dictionary:
        dictionary: {'variable name':['Item 1', 'Item 2', ...]}

    e.g.:
    class data()
         def __init__(self, idx):
             self.intVar = 55
             self.floatVar = 1.25
             self.strVar = "the quick brown fox"
             self.boolVar = False
                    
    columns =  [
                {'variable':'intVar', 'header':'Index', 'edit':True, 'editor':'default', 'min':5, 'step':5},
                {'variable':'floatVar', 'header':'Float Variable', 'edit':True, 'editor':'combobox'},
                {'variable':'boolVar', 'header':'Bool Variable', 'edit':True, 'editor':'default'},
                {'variable':'strVar', 'header':'String Variable', 'edit':True, 'editor':'default'},
               ]

    cblist = {'floatVar':['0.1', '0.22', '1.23', '2', '4.5', '6.44']}
    
    datalist = []
    for r in range(5):
        datalist.append(data())

    setData(datalist, columns, cblist)
    '''
    def __init__(self, *args, **kwargs):
        ''' Constructor
        '''
        apply(Qt.QTableView.__init__, (self,) + args)

        self.setAlternatingRowColors(True)
        #self.setObjectName("tableViewGeneric")
        #self.horizontalHeader().setCascadingSectionResizes(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setResizeMode(Qt.QHeaderView.ResizeToContents)
        if "RowNumbers" in kwargs:
            self.verticalHeader().setVisible(kwargs["RowNumbers"])
        else:
            self.verticalHeader().setVisible(False)
        self.verticalHeader().setResizeMode(Qt.QHeaderView.ResizeToContents)
        if "SelectionBehavior" in kwargs:
            self.setSelectionBehavior(kwargs["SelectionBehavior"])
        self.setSelectionMode(Qt.QAbstractItemView.ExtendedSelection)

        # table description and content
        self.fnColorSelect = lambda x: None
        self.fnCheckBox = lambda x: None
        self.fnValidate = lambda row, col, data: True
        self.descrition = []
        self.cblist = {}
        self.data = []
        
        # selection info
        self.selectedRow = 0

    def _fillTables(self):
        ''' Create and fill data tables
        '''
        self.data_model = _DataTableModel(self.data, self.descrition, self.cblist)
        self.setModel(self.data_model)
        self.setItemDelegate(_DataItemDelegate())
        self.setEditTriggers(Qt.QAbstractItemView.AllEditTriggers)
        self.data_model.fnColorSelect = self.fnColorSelect
        self.data_model.fnCheckBox = self.fnCheckBox
        self.data_model.fnValidate = self.fnValidate

        # actions
        self.connect(self.data_model, Qt.SIGNAL("dataChanged(QModelIndex, QModelIndex)"), self._table_data_changed)
        self.connect(self.selectionModel(), Qt.SIGNAL("selectionChanged(QItemSelection, QItemSelection)"), self._selectionChanged)
        
    def _table_data_changed(self, topLeft, bottomRight):
        ''' SIGNAL data in channel table has changed
        '''
        # look for multiple selected rows
        cr = self.currentIndex().row()
        cc = self.currentIndex().column()
        selectedRows = [i.row() for i in self.selectedIndexes() if i.column() == cc]
        # change column value in all selected rows, but only if value is of type Bool
        if len(selectedRows) > 1:
            val = self.data_model._getitem(cr, cc)
            if val.type() == Qt.QMetaType.Bool:
                for r in selectedRows:
                    self.data_model._setitem(r, cc, val)

        # notify parent about changes
        self.emit(Qt.SIGNAL('dataChanged()'))



    def _selectionChanged(self, selected, deselected):
        if len(selected.indexes()) > 0:
            self.selectedRow = selected.indexes()[0].row()
        '''
        selectedIdx = [i.row() for i in selected.indexes()]
        deselectedIdx = [i.row() for i in deselected.indexes()]
        print "selected: ",selectedIdx, " deselected: ", deselectedIdx
        '''

    
    def setData(self, data, description, cblist):
        ''' Initialize the table view
        @param data: list of data objects
        @param description: list of column description dictionaries
        @param cblist: dictionary of combo box list contents 
        '''
        self.data = data
        self.descrition = description
        self.cblist = cblist
        self._fillTables()
        
    def setfnColorSelect(self, lambdaColor):
        ''' Set the background color selection function
        @param lambdaColor: color selction function  
        '''
        self.fnColorSelect = lambdaColor
        
    def setfnCheckBox(self, lambdaCheckBox):
        ''' Set the checkbox display function
        @param lambdaCheckBox: function override  
        '''
        self.fnCheckBox = lambdaCheckBox
        
    def setfnValidate(self, lambdaValidate):
        ''' Set the row validation function
        @param lambdaValidate: function override  
        '''
        self.fnValidate = lambdaValidate
        
    def getSelectedRow(self):
        return self.selectedRow
            

class _DataTableModel(Qt.QAbstractTableModel):
    ''' EEG and AUX table data model for the configuration pane
    '''
    def __init__(self, data, description, cblist, parent=None, *args):
        ''' Constructor
        @param data: list of data objects
        @param description: list of column description dictionaries
        @param cblist: dictionary of combo box list contents 
        '''
        Qt.QAbstractTableModel.__init__(self, parent, *args)
        self.arraydata = data
        # list of column description dictionaries
        # dictionary: {'variable':'variable name', 'header':'header text', 'edit':False/True, 'editor':'default' or 'combobox'}
        # optional entries: 'min': minum value, 'max': maximum value, 'dec': number of decimal places, 
        #                   'step': spin box incr/decr
        #                   'indexed' : True, use value as combobox index  
        self.columns = description

        # dictionary of combo box list contents
        # dictionary: {'variable name':['Item 1', 'Item 2', ...]}
        self.cblist = cblist
        
        # color selection function
        self.fnColorSelect = lambda x: None
        # checkbox modification function
        self.fnCheckBox = lambda x: None
        # row validation function
        self.fnValidate = lambda row, col, data: True
        
    def _getitem(self, row, column):
        ''' Get data item based on table row and column
        @param row: row number
        @param column: column number
        @return:  QVariant data value
        ''' 
        if (row >= len(self.arraydata)) or (column >= len(self.columns)):
            return Qt.QVariant()
        
        # get data object
        data = self.arraydata[row]
        # get variable name from column description
        variable_name = self.columns[column]['variable']
        # get variable value
        if hasattr(data, variable_name):
            d = Qt.QVariant(vars(data)[variable_name])
            # get value from combobox list values?
            if self.columns[column].has_key('indexed') and self.cblist.has_key(variable_name):
                idx, ok = d.toInt()
                if ok and idx >=0 and idx < len(self.cblist[variable_name]):
                    d = Qt.QVariant(self.cblist[variable_name][idx])
        else:
            d = Qt.QVariant()
        return d

    def _setitem(self, row, column, value):
        ''' Set data item based on table row and column
        @param row: row number
        @param column: column number
        @param value: QVariant value object
        @return: True if property value was set, False if not
        ''' 
        if (row >= len(self.arraydata)) or (column >= len(self.columns)):
            return False
        
        # get data object
        data = self.arraydata[row]

        # get variable name from column description
        variable_name = self.columns[column]['variable']

        # get index from combobox list values
        if self.columns[column].has_key('indexed') and self.cblist.has_key(variable_name):
            v = value.toString()
            if v in self.cblist[variable_name]:
                value = Qt.QVariant(self.cblist[variable_name].index(v))
            else:
                return False
            
        # set variable value
        if hasattr(data, variable_name):
            t = type(vars(data)[variable_name])
            if t is bool:
                vars(data)[variable_name] = value.toBool()
                return True
            elif t is float:
                vars(data)[variable_name] = value.toDouble()[0]
                return True
            elif t is int:
                vars(data)[variable_name] = value.toInt()[0]
                return True
            elif t in types.StringTypes:
                vars(data)[variable_name] = "%s" % value.toString()
                return True
            else:
                return False
        else:
            return False
        
    def editorType(self, column):
        ''' Get the columns editor type from column description
        @param column: table column number
        @return: editor type as QVariant (string)
        ''' 
        if column >= len(self.columns):
            return Qt.QVariant()
        return Qt.QVariant(self.columns[column]['editor'])
    
    def editorMinValue(self, column):
        ''' Get the columns editor minimum value from column description
        @param column: table column number
        @return: minimum value as QVariant
        ''' 
        if column >= len(self.columns):
            return Qt.QVariant()
        if self.columns[column].has_key('min'):
            return Qt.QVariant(self.columns[column]['min'])
        else:
            return Qt.QVariant()
            
    def editorMaxValue(self, column):
        ''' Get the columns editor maximum value from column description
        @param column: table column number
        @return: minimum value as QVariant
        ''' 
        if column >= len(self.columns):
            return Qt.QVariant()
        if self.columns[column].has_key('max'):
            return Qt.QVariant(self.columns[column]['max'])
        else:
            return Qt.QVariant()

    def editorDecimals(self, column):
        ''' Get the columns editor decimal places from column description
        @param column: table column number
        @return: minimum value as QVariant
        ''' 
        if column >= len(self.columns):
            return Qt.QVariant()
        if self.columns[column].has_key('dec'):
            return Qt.QVariant(self.columns[column]['dec'])
        else:
            return Qt.QVariant()

    def editorStep(self, column):
        ''' Get the columns editor single step value from column description
        @param column: table column number
        @return: minimum value as QVariant
        ''' 
        if column >= len(self.columns):
            return Qt.QVariant()
        if self.columns[column].has_key('step'):
            return Qt.QVariant(self.columns[column]['step'])
        else:
            return Qt.QVariant()

    
    def comboBoxList(self, column):
        ''' Get combo box item list for specified column
        @param column: table column number
        @return: combo box item list as QVariant 
        '''
        if column >= len(self.columns):
            return Qt.QVariant()
        
        # get variable name from column description
        variable_name = self.columns[column]['variable']
        # lookup list in dictionary
        if self.cblist.has_key(variable_name):
            return Qt.QVariant(self.cblist[variable_name])
        else:
            return Qt.QVariant()
    
    def rowCount(self, parent=Qt.QModelIndex()):
        ''' Get the number of required table rows
        @return: number of rows
        '''
        if parent.isValid():
            return 0
        return len(self.arraydata)
    
    def columnCount(self, parent=Qt.QModelIndex()):
        ''' Get the number of required table columns
        @return: number of columns
        '''
        if parent.isValid():
            return 0
        return len(self.columns)
        
    def data(self, index, role): 
        ''' Abstract method from QAbstactItemModel to get cell data based on role
        @param index: QModelIndex table cell reference
        @param role: given role for the item referred to by the index
        @return: the data stored under the given role for the item referred to by the index
        '''
        if not index.isValid(): 
            return Qt.QVariant()
        
        # get the underlying data
        value = self._getitem(index.row(), index.column())
        
        if role == Qt.Qt.CheckStateRole:
            # display function override?
            data = self.arraydata[index.row()]
            check = self.fnCheckBox((index.column(), data))
            if check != None:
                if check:
                    return Qt.Qt.Checked
                else:
                    return Qt.Qt.Unchecked
            # use data value
            if value.type() == Qt.QMetaType.Bool:
                if value.toBool():
                    return Qt.Qt.Checked
                else:
                    return Qt.Qt.Unchecked
        
        elif (role == Qt.Qt.DisplayRole) or (role == Qt.Qt.EditRole):
            if value.type() != Qt.QMetaType.Bool:
                return value
        
        elif role == Qt.Qt.BackgroundRole:
            # change background color for a specified row
            data = self.arraydata[index.row()]
            color = self.fnColorSelect(data)
            if not self.fnValidate(index.row(), index.column(), self.arraydata):
                color = Qt.QColor(255, 0, 0)
            if color != None:
                return Qt.QVariant(color)
            
        return Qt.QVariant()
    
    def flags(self, index):
        ''' Abstract method from QAbstactItemModel
        @param index: QModelIndex table cell reference
        @return: the item flags for the given index
        '''
        if not index.isValid():
            return Qt.Qt.ItemIsEnabled
        if not self.columns[index.column()]['edit']:
            return Qt.Qt.ItemIsEnabled | Qt.Qt.ItemIsSelectable
        value = self._getitem(index.row(), index.column())
        if value.type() == Qt.QMetaType.Bool:
            return Qt.QAbstractTableModel.flags(self, index) | Qt.Qt.ItemIsUserCheckable | Qt.Qt.ItemIsSelectable
        return Qt.QAbstractTableModel.flags(self, index) | Qt.Qt.ItemIsEditable
        
    def setData(self, index, value, role):
        ''' Abstract method from QAbstactItemModel to set cell data based on role
        @param index: QModelIndex table cell reference
        @param value: QVariant new cell data
        @param role: given role for the item referred to by the index
        @return: true if successful; otherwise returns false.
        '''
        if index.isValid(): 
            left = self.createIndex(index.row(), 0)
            right = self.createIndex(index.row(), self.columnCount())
            if role == Qt.Qt.EditRole:
                if not self._setitem(index.row(), index.column(), value):
                    return False
                self.emit(Qt.SIGNAL('dataChanged(QModelIndex, QModelIndex)'), index, index)
                return True
            elif role == Qt.Qt.CheckStateRole:
                if not self._setitem(index.row(), index.column(), Qt.QVariant(value == Qt.Qt.Checked)):
                    return False
                self.emit(Qt.SIGNAL('dataChanged(QModelIndex, QModelIndex)'), left, right)
                return True
        return False

    def headerData(self, section, orientation, role):
        ''' Abstract method from QAbstactItemModel to get the column header
        @param section: column or row number
        @param orientation: Qt.Horizontal = column header, Qt.Vertical = row header
        @param role: given role for the item referred to by the index
        @return: header
        '''
        if orientation == Qt.Qt.Horizontal and role == Qt.Qt.DisplayRole:
            return Qt.QVariant(self.columns[section]['header'])
        if orientation == Qt.Qt.Vertical and role == Qt.Qt.DisplayRole:
            return Qt.QVariant(Qt.QString.number(section+1))
        return Qt.QVariant()


class _DataItemDelegate(Qt.QStyledItemDelegate):  
    ''' Combobox item editor
    '''
    def __init__(self, parent=None):
        super(_DataItemDelegate, self).__init__(parent)
        
    def createEditor(self, parent, option, index):
        # combo box
        if index.model().editorType(index.column()) == 'combobox':
            combobox = Qt.QComboBox(parent)
            combobox.addItems(index.model().comboBoxList(index.column()).toStringList())
            combobox.setEditable(False)
            self.connect(combobox, Qt.SIGNAL('activated(int)'), self.emitCommitData)
            return combobox
        
        # multi line editor (plain text)
        if index.model().editorType(index.column()) == 'plaintext':
            editor = Qt.QPlainTextEdit(parent)
            editor.setMinimumHeight(100)
            return editor

        # get default editor
        editor = Qt.QStyledItemDelegate.createEditor(self, parent, option, index)
        
        # set min/max Values for integer values if available
        if isinstance(editor, Qt.QSpinBox):
            min = index.model().editorMinValue(index.column())
            if min.isValid():
                editor.setMinimum(min.toInt()[0])
            max = index.model().editorMaxValue(index.column())
            if max.isValid():
                editor.setMaximum(max.toInt()[0])
            step = index.model().editorStep(index.column())
            if step.isValid():
                editor.setSingleStep(step.toInt()[0])
            
        # set min/max Values for float values if available
        if isinstance(editor, Qt.QDoubleSpinBox):
            min = index.model().editorMinValue(index.column())
            if min.isValid():
                editor.setMinimum(min.toDouble()[0])
            max = index.model().editorMaxValue(index.column())
            if max.isValid():
                editor.setMaximum(max.toDouble()[0])
            dec = index.model().editorDecimals(index.column())
            if dec.isValid():
                editor.setDecimals(dec.toInt()[0])
            step = index.model().editorStep(index.column())
            if step.isValid():
                editor.setSingleStep(step.toDouble()[0])

        return editor

    def setEditorData(self, editor, index):
        #if index.model().columns[index.column()]['editor'] == 'combobox':
        if isinstance(editor, Qt.QComboBox):
            idx = 0
            # get data
            d = index.model().data(index, Qt.Qt.DisplayRole)
            if d.isValid():
                if d.type() == Qt.QMetaType.QString:
                    # find matching list item text
                    idx = editor.findText(d.toString())
                    if idx == -1:
                        idx = 0
                else:
                    # find the closest matching index
                    closest = lambda a,l:min(enumerate(l),key=lambda x:abs(x[1]-a))
                    # get item list
                    itemlist = []
                    for i in range(editor.count()):
                        itemlist.append(editor.itemText(i).toDouble()[0])
                    # find index
                    idx = closest(d.toDouble()[0], itemlist)[0]
            
            editor.setCurrentIndex(idx)
            return
        Qt.QStyledItemDelegate.setEditorData(self, editor, index)


    def setModelData(self, editor, model, index):
        #if model.columns[index.column()]['editor'] == 'combobox':
        if isinstance(editor, Qt.QComboBox):
            model.setData(index, Qt.QVariant(editor.currentText()), Qt.Qt.EditRole)
            #model.reset()
            return
        Qt.QStyledItemDelegate.setModelData(self, editor, model, index)

    def emitCommitData(self):
        self.emit(Qt.SIGNAL('commitData(QWidget*)'), self.sender())


        