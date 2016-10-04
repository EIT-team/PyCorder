# -*- coding: utf-8 -*-
'''
Impedance Display Module

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
@date: $Date: 2013-06-07 19:21:40 +0200 (Fr, 07 Jun 2013) $
@version: 1.0

B{Revision:} $LastChangedRevision: 198 $
'''

from PyQt4 import Qwt5 as Qwt
from modbase import *
from res import frmImpedanceDisplay

class IMP_Display(ModuleBase):
    ''' Display impedance values
    '''

    def __init__(self, *args, **keys):
        ''' Constructor
        '''
        ModuleBase.__init__(self, name="Impedance Display", **keys)

        # XML parameter version
        # 1: initial version
        self.xmlVersion = 1

        # set default values
        self.params = None
        self.data = None
        self.dataavailable = False
        
        self.impDialog = None           #: Impedance dialog widget
        self.range_max = 50             #: Impedance range 0-range_max in KOhm
        self.show_values = True         #: Show numerical impedance values

    def terminate(self):
        ''' Destructor
        '''
        # close dialog widget on exit
        if self.impDialog != None:
            self.impDialog.close()
            self.impDialog = None
        
    def setDefault(self):
        ''' Set all module parameters to default values
        '''
        self.range_max = 50
        self.show_values = True

    def process_start(self):
        ''' Prepare and open impedance dialog if recording mode == IMPEDANCE
        '''
        # create and show the impedance dialog
        if self.params.recording_mode == RecordingMode.IMPEDANCE:
            if self.impDialog == None:
                # impedance dialog should be always on top
                topLevelWidgets = Qt.QApplication.topLevelWidgets()
                activeWindow = Qt.QApplication.activeWindow()
                if activeWindow:
                    self.impDialog = DlgImpedance(self, Qt.QApplication.activeWindow())
                else:
                    if len(topLevelWidgets):
                        self.impDialog = DlgImpedance(self, topLevelWidgets[0])
                    else:
                        self.impDialog = DlgImpedance(self)
                self.impDialog.setWindowFlags(Qt.Qt.Tool)
                self.impDialog.show()
                self.impDialog.updateLabels(self.params)
            else:
                self.impDialog.updateLabels(self.params)
            self.sendColorRange()
        else:
            if self.impDialog != None:
                self.impDialog.close()
                self.impDialog = None
        
    def process_stop(self):
        ''' Close impedance dialog
        '''
        if self.impDialog != None:
            self.impDialog.close()
            self.impDialog = None
        

    def process_update(self, params):
        ''' Get channel properties and 
        propagate parameter update down to all attached receivers
        '''
        self.params = params 
        # propagate down
        return params
        
    def process_input(self, datablock):
        ''' Get data from input queue and update display
        '''
        self.dataavailable = True
        self.data = datablock

        # nothing to do if not in impedance mode
        if datablock.recording_mode != RecordingMode.IMPEDANCE:
            return

        # check for an outdated impedance structure
        if len(datablock.impedances) > 0 or len(datablock.channel_properties) != len(self.params.channel_properties):
            raise ModuleError(self._object_name, "outdated impedance structure received!")
        
        if self.impDialog != None:
            self.emit(Qt.SIGNAL('update(PyQt_PyObject)'), datablock)
    
    def process_output(self):
        ''' Put processed data into output queue
        '''
        if not self.dataavailable:
            return None
        self.dataavailable = False
        return self.data
    

    def getXML(self):
        ''' Get module properties for XML configuration file
        @return: objectify XML element::
            e.g.
            <IMP_Display instance="0" version="1">
                <range_max>50</range_max>
                ...
            </IMP_Display>
        '''
        E = objectify.E
        cfg = E.IMP_Display(E.range_max(self.range_max),
                            E.show_values(self.show_values),
                            version=str(self.xmlVersion),
                            instance=str(self._instance),
                            module="impedance")
        return cfg
        
        
    def setXML(self, xml):
        ''' Set module properties from XML configuration file
        @param xml: complete objectify XML configuration tree, 
        module will search for matching values
        '''
        # search my configuration data
        displays = xml.xpath("//IMP_Display[@module='impedance' and @instance='%i']"%(self._instance) )
        if len(displays) == 0:
            # configuration data not found, leave everything unchanged
            return      
        
        # we should have only one display instance from this type
        cfg = displays[0]   
        
        # check version, has to be lower or equal than current version
        version = cfg.get("version")
        if (version == None) or (int(version) > self.xmlVersion):
            self.send_event(ModuleEvent(self._object_name, EventType.ERROR, "XML Configuration: wrong version"))
            return
        version = int(version)
        
        # get the values
        try:
            self.range_max = cfg.range_max.pyval
            self.show_values = cfg.show_values.pyval
        except Exception as e:
            self.send_exception(e, severity=ErrorSeverity.NOTIFY)

    def sendColorRange(self):
        ''' Send new impedance color range as ModuleEvent to update ActiCap LED color range
        '''
        val = tuple([self.range_max / 3.0, self.range_max * 2.0 / 3.0])
        self.send_event(ModuleEvent(self._object_name, EventType.COMMAND, info="ImpColorRange",
                                    cmd_value = val))


'''
------------------------------------------------------------
IMPEDANCE DIALOG
------------------------------------------------------------
'''

class DlgImpedance(Qt.QDialog, frmImpedanceDisplay.Ui_frmImpedanceDisplay):
    ''' Impedance display dialog
    '''
    def __init__(self, module, *args):
        ''' Constructor
        @param module: parent module
        '''
        apply(Qt.QDialog.__init__, (self,) + args)
        self.setupUi(self)
        self.module = module
        self.params = None  # last received parameter block
        self.data = None    # last received data block
        
        # create table view grid (10x16 eeg electrodes + 1 row for ground electrode)
        cc = 10
        rc = 16
        self.tableWidgetValues.setColumnCount(cc)
        self.tableWidgetValues.setRowCount(rc+1)
        self.tableWidgetValues.horizontalHeader().setResizeMode(Qt.QHeaderView.Stretch)
        self.tableWidgetValues.horizontalHeader().setDefaultAlignment(Qt.Qt.Alignment(Qt.Qt.AlignCenter))
        self.tableWidgetValues.verticalHeader().setResizeMode(Qt.QHeaderView.Stretch)
        self.tableWidgetValues.verticalHeader().setDefaultAlignment(Qt.Qt.Alignment(Qt.Qt.AlignCenter))
        # add ground electrode row
        self.tableWidgetValues.setSpan(rc,0,1,cc)
        # row headers
        rheader = Qt.QStringList()
        for r in xrange(rc):
            rheader.append("%d - %d"%(r*cc+1, r*cc+cc))
        rheader.append("GND")
        self.tableWidgetValues.setVerticalHeaderLabels(rheader)
        # create cell items
        fnt = Qt.QFont()
        fnt.setPointSize(8)
        for r in xrange(rc):
            for c in xrange(cc):
                item = Qt.QTableWidgetItem()
                item.setTextAlignment(Qt.Qt.AlignCenter)
                item.setFont(fnt)
                self.tableWidgetValues.setItem(r, c, item)
        # GND electrode cell
        item = Qt.QTableWidgetItem()
        item.setTextAlignment(Qt.Qt.AlignCenter)
        item.setFont(fnt)
        item.setText("GND")
        self.tableWidgetValues.setItem(rc, 0, item)
        self.defaultColor = item.backgroundColor()
        
        # set range list
        self.comboBoxRange.clear()
        self.comboBoxRange.addItem("15")
        self.comboBoxRange.addItem("50")
        self.comboBoxRange.addItem("100")
        self.comboBoxRange.addItem("500")

        # set validators
        validator = Qt.QIntValidator(self)
        validator.setBottom(15)
        validator.setTop(500)
        self.comboBoxRange.setValidator(validator)
        self.comboBoxRange.setEditText(str(self.module.range_max))
        
        # setup color scale
        self.linearscale = False
        self.scale_engine = Qwt.QwtLinearScaleEngine()
        self.scale_interval = Qwt.QwtDoubleInterval(0, self.module.range_max)
        self.scale_map = Qwt.QwtLinearColorMap(Qt.Qt.green, Qt.Qt.red)
        if self.linearscale:
            self.scale_map.addColorStop(0.45, Qt.Qt.yellow)
            self.scale_map.addColorStop(0.55, Qt.Qt.yellow)
            self.scale_map.setMode(Qwt.QwtLinearColorMap.ScaledColors)
        else:
            self.scale_map.addColorStop(0.33, Qt.Qt.yellow)
            self.scale_map.addColorStop(0.66, Qt.Qt.red)
            self.scale_map.setMode(Qwt.QwtLinearColorMap.FixedColors)
        self.ScaleWidget.setColorMap(self.scale_interval, self.scale_map)
        self.ScaleWidget.setColorBarEnabled(True)
        self.ScaleWidget.setColorBarWidth(30)
        self.ScaleWidget.setBorderDist(10,10)

        # set default values
        self.setColorRange(0, self.module.range_max)
        self.checkBoxValues.setChecked(self.module.show_values)

        # actions
        self.connect(self.comboBoxRange, Qt.SIGNAL("editTextChanged(QString)"), self._rangeChanged)
        self.connect(self.checkBoxValues, Qt.SIGNAL("stateChanged(int)"), self._showvalues_changed)
        self.connect(self.module, Qt.SIGNAL('update(PyQt_PyObject)'), self._updateValues)

        
    def _rangeChanged(self, rrange):
        ''' SIGNAL range combo box value has changed
        @param range: new range value in KOhm
        '''
        # validate range 
        valid = self.comboBoxRange.validator().validate(rrange,0)[0]
        if valid != Qt.QValidator.Acceptable:
            return 
        # use new range
        newrange,ok = rrange.toInt()
        if ok:
            self.setColorRange(0, newrange)
            self.module.range_max = newrange
            self._updateValues(self.data)
            self.module.sendColorRange()

    def _showvalues_changed(self, state):
        ''' SIGNAL show values radio button clicked
        '''
        self.module.show_values = (state == Qt.Qt.Checked) 
        self._updateValues(self.data)
       
             
    def setColorRange(self, cmin, cmax):
        ''' Create new color range for the scale widget
        '''
        self.scale_interval.setMaxValue(cmax)
        self.scale_interval.setMinValue(cmin)
        self.ScaleWidget.setColorMap(self.scale_interval, self.scale_map)
        self.ScaleWidget.setScaleDiv(self.scale_engine.transformation(),
                                     self.scale_engine.divideScale(self.scale_interval.minValue(),
                                                                   self.scale_interval.maxValue(), 
                                                                   5, 2))
        
            
    def closeEvent(self, event):
        ''' Dialog want's close, send stop request to main window
        '''
        self.setParent(None)
        self.disconnect(self.module, Qt.SIGNAL('update(PyQt_PyObject)'), self._updateValues)
        if self.sender() == None:
            self.module.send_event(ModuleEvent(self.module._object_name, EventType.COMMAND, "Stop"))
        event.accept()
        
       
    def reject(self):
        ''' ESC key pressed, Dialog want's close, just ignore it
        '''
        return
    
    def _setLabelText(self, row, col, text):
        item = self.tableWidgetValues.item(row, col)
        item.setText(text)
        item.setBackgroundColor(Qt.QColor(128,128,128))
        item.label = text
    
    def updateLabels(self, params):
        ''' Update cell labels
        '''
        # copy channel configuration
        self.params = copy.deepcopy(params)

        # update cells
        cc = self.tableWidgetValues.columnCount()
        rc = self.tableWidgetValues.rowCount() - 1
        # reset items
        for row in xrange(rc):
            for col in xrange(cc):
                item = self.tableWidgetValues.item(row, col)
                item.setText("")
                item.label = ""
                item.setBackgroundColor(Qt.Qt.white)
        # set channel labels
        for idx, ch in enumerate(self.params.channel_properties):
            if (ch.enable or ch.isReference) and (ch.input > 0) and (ch.input <= rc*cc) and (ch.inputgroup == ChannelGroup.EEG):
                row = (ch.input-1) / cc
                col = (ch.input-1) % cc
                # channel has a reference impedance value?
                if self.params.eeg_channels[idx, ImpedanceIndex.REF] == 1:
                    # prefix the channel name
                    name =  ch.name + " " + ImpedanceIndex.Name[ImpedanceIndex.DATA]
                    self._setLabelText(row, col, name)
                    # put the reference values at the following table item, if possible
                    name =  ch.name + " " + ImpedanceIndex.Name[ImpedanceIndex.REF]
                    row = (ch.input) / cc
                    col = (ch.input) % cc
                    self._setLabelText(row, col, name)
                else:
                    self._setLabelText(row, col, ch.name)

    def _getValueText(self, impedance):
        ''' evaluate the impedance value and get the text and color for display
        @return: text and color
        '''
        if impedance > CHAMP_IMP_INVALID:
            valuetext = "disconnected"
            color = Qt.QColor(128,128,128)
        else:
            v = impedance / 1000.0
            if impedance == CHAMP_IMP_INVALID:
                valuetext = "out of range"
            else:
                valuetext = "%.0f"%(v)
            color = self.ScaleWidget.colorMap().color(self.ScaleWidget.colorBarInterval(), v)
        return valuetext, color

    def _updateValues(self, data):
        ''' SIGNAL send from impedance module to update cell values 
        @param data: EEG_DataBlock
        ''' 
        if data == None:
            return
        # keep the last data block
        self.data = copy.deepcopy(data)

        # check for an outdated impedance structure
        if len(data.impedances) > 0 or len(data.channel_properties) != len(self.params.channel_properties):
            print "outdated impedance structure received!"
            return
        
        cc = self.tableWidgetValues.columnCount()
        rc = self.tableWidgetValues.rowCount() - 1
        # EEG electrodes
        gndImpedance = None
        impCount = 0
        for idx, ch in enumerate(data.channel_properties):
            if (ch.enable or ch.isReference) and (ch.input > 0) and (ch.input <= rc*cc) and (ch.inputgroup == ChannelGroup.EEG):
                impCount += 1
                row = (ch.input-1) / cc
                col = (ch.input-1) % cc
                item = self.tableWidgetValues.item(row, col)

                # channel has a data impedance value?
                if self.params.eeg_channels[idx, ImpedanceIndex.DATA] == 1:
                    # data channel value
                    value, color = self._getValueText(data.eeg_channels[idx, ImpedanceIndex.DATA])
                    item.setBackgroundColor(color)
                    if self.module.show_values:
                        item.setText("%s\n%s"%(item.label, value))
                    else:
                        item.setText(item.label)

                # channel has a reference impedance value?
                if self.params.eeg_channels[idx, ImpedanceIndex.REF] == 1:
                    row = (ch.input) / cc
                    col = (ch.input) % cc
                    item = self.tableWidgetValues.item(row, col)
                    # reference channel value
                    value, color = self._getValueText(data.eeg_channels[idx, ImpedanceIndex.REF])
                    item.setBackgroundColor(color)
                    if self.module.show_values:
                        item.setText("%s\n%s"%(item.label, value))
                    else:
                        item.setText(item.label)

                # channel has a GND impedance value?
                if gndImpedance == None and  self.params.eeg_channels[idx, ImpedanceIndex.GND] == 1:
                    gndImpedance = data.eeg_channels[idx, ImpedanceIndex.GND]

                    
        # GND electrode, take the value of the first EEG electrode
        item = self.tableWidgetValues.item(rc, 0)
        if gndImpedance == None:
            item.setText("")
            item.setBackgroundColor(Qt.Qt.white)
        else:
            value, color = self._getValueText(gndImpedance)
            item.setBackgroundColor(color)
            if self.module.show_values:
                item.setText("%s\n%s"%("GND", value))
            else:
                item.setText("GND")
        
        
        
    
