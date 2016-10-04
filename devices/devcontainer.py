# -*- coding: utf-8 -*-
'''
Container class for input devices

PyCorder ActiChamp Recorder

------------------------------------------------------------

Copyright (C) 2013, Brain Products GmbH, Gilching

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
@date: $Date: 2013-06-10 08:40:11 +0200 (Mo, 10 Jun 2013) $
@version: 1.0

B{Revision:} $LastChangedRevision: 199 $
'''

# add ourself package path to system path
import os, sys 
res_path = os.path.abspath('devices') 
sys.path.append(res_path) 


from modbase import *
import pkgutil
from inspect import getmembers, isclass
from tools.modview import GenericTableWidget

################################################################
# Input device container and factory

class DeviceContainer(Qt.QObject):
    def __init__(self):
        Qt.QObject.__init__(self)
        
        # XML parameter version
        # 1: initial version
        self.xmlVersion = 1 
        
        # a valid device class needs the attribute deviceName     
        def isDeviceClass(obj):
            if not isclass(obj):
                return False
            if not hasattr(obj, "deviceName"):
                return False
            return len(obj.deviceName) > 0 
        
        # create a dictionary for all device classes within this package
        self.availableDevices = dict()
        for importer, module, ispgk in pkgutil.iter_modules(["../devices", "devices"]):
            classes = getmembers(__import__(module), isDeviceClass)
            self.availableDevices.update(classes)
        
        # initialize class variables
        self.instantiatedDevices = []
        
    def reset(self):
        ''' Remove all instantiated devices
        '''
        self.instantiatedDevices = []
        
    def get_configuration_widget(self):
        self.CfgWidget = DeviceContainerWidget()
        acolumns =  [
                    {'variable':'deviceName', 'header':'Devices available', 'edit':False, 'editor':'default'},
                   ]
        ccolumns =  [
                    {'variable':'description', 'header':'Devices connected', 'edit':False, 'editor':'default'},
                   ]
        cblist = {}
        self.CfgWidget.availabletable.setData(self.availableDevices.values(), acolumns, cblist)
        self.CfgWidget.instantiatedtable.setData(self.instantiatedDevices, ccolumns, cblist)
        self.connect(self.CfgWidget, Qt.SIGNAL("insertDevice(int)"), self._insertDevice)
        self.connect(self.CfgWidget, Qt.SIGNAL("removeDevice(int)"), self._removeDevice)
        self.connect(self.CfgWidget, Qt.SIGNAL("updateDevice(int)"), self._updateDevice)
        return self.CfgWidget
        
    def _insertDevice(self, idx):
        ''' Signal from configuration widget
        '''
        dev = self.availableDevices.values()
        if idx >= 0 and idx < len(dev):
            new_device = dev[idx]()
            if new_device.configure_device():
                # check for already connected input channels
                overlapping = False
                for d in self.instantiatedDevices:
                    overlapping |= new_device.hasOverlappingInputChannels(d)
                if not overlapping:
                    self.instantiatedDevices.append(new_device)
                    self.CfgWidget.instantiatedtable.model().reset()
                    # notify parent about changes
                    self.emit(Qt.SIGNAL('dataChanged()'))
                else:
                    Qt.QMessageBox.critical(None,"Can't connect device","Required input channels are already in use by other devices")

    def _removeDevice(self, idx):
        ''' Signal from configuration widget
        '''
        if idx >= 0 and idx < len(self.instantiatedDevices):
            del self.instantiatedDevices[idx]
            self.CfgWidget.instantiatedtable.model().reset()
            # notify parent about changes
            self.emit(Qt.SIGNAL('dataChanged()'))

    def _updateDevice(self, idx):
        ''' Signal from configuration widget
        '''
        if idx >= 0 and idx < len(self.instantiatedDevices):
            device = self.instantiatedDevices[idx]
            while True:
                # configure device
                device.configure_device()
                # check for already connected input channels
                overlapping = False
                for d in self.instantiatedDevices:
                    if d != device:
                        overlapping |= device.hasOverlappingInputChannels(d)
                if not overlapping:
                    break
                else:
                    Qt.QMessageBox.critical(None,"Can't reconnect device","Required input channels are already in use by other devices")
                    
            self.CfgWidget.instantiatedtable.model().reset()
            # notify parent about changes
            self.emit(Qt.SIGNAL('dataChanged()'))


    def process_update(self, params):
        ''' Get the whole input data object, select the affected channels 
        and replace the output property array
        '''
        new_properties = np.array([])
        new_output = np.array([[]])
        processed_indices = np.array([])
        
        # let all connected devices select their channels
        for device in self.instantiatedDevices:
            properties, output, processed = device.process_updatechannels(params)
            if properties.size > 0:
                new_properties = np.concatenate((new_properties, properties))
            if output.size > 0:
                if new_output.size == 0:
                    new_output = output
                else:
                    new_output = np.concatenate((new_output, output))
            if processed.size > 0:
                processed_indices = np.concatenate((processed_indices, processed))
        
        # remove all processed channels from the original properties 
        self.processed_indices = np.unique(processed_indices)
        remaining_channel_properties = np.delete(params.channel_properties, self.processed_indices, 0)
        if params.eeg_channels.size > 0:
            remaining_channel_output = np.delete(params.eeg_channels, self.processed_indices, 0)
        else:
            remaining_channel_output = params.eeg_channels

        # add all new channel definitions to the remaining properties
        self.new_channel_properties = np.concatenate((remaining_channel_properties, new_properties))
        params.channel_properties = self.new_channel_properties
        if new_output.size > 0:
            params.eeg_channels = np.concatenate((remaining_channel_output, new_output))
        else:
            params.eeg_channels = remaining_channel_output
        return params
            
    def process_input(self, data):
        ''' let all connected devices process the input data
        '''
        if len(self.instantiatedDevices) > 0:    
            data.channel_properties = self.new_channel_properties
            output_channels = np.delete(data.eeg_channels, self.processed_indices, 0)
            for device in self.instantiatedDevices:
                output = device.process_input(data)
                if output != None:
                    output_channels = np.concatenate((output_channels, output))
            data.eeg_channels = output_channels

        
    def getXML(self):
        ''' Get input device configuration as XML for configuration file
        @return: objectify XML element
        '''
        E = objectify.E
        devices = E.InputDevices()
        for device in self.instantiatedDevices:
            devices.append(device.getXML())
        devices.attrib["version"] = str(self.xmlVersion)
        return devices

    def setXML(self, xml):
        ''' Setup device properties from XML configuration file
        @param xml: objectify XML device configuration 
        '''
        # remove existing devices
        self.reset()

        # check version, has to be lower or equal than current version
        version = xml.InputDevices.get("version")
        if (version == None) or (int(version) > self.xmlVersion):
            raise Exception, "Input Device Configuration: wrong version > %d"%(self.xmlVersion)
        version = int(version)
        
        # get and instantiate the input devices
        for device in xml.InputDevices.iterchildren():
            # instantiate device
            if self.availableDevices.has_key(device.classname.pyval):
                d = self.availableDevices[device.classname.pyval]() 
                d.setXML(device)
                # check for already connected input channels
                overlapping = False
                for di in self.instantiatedDevices:
                    overlapping |= di.hasOverlappingInputChannels(d)
                if not overlapping:
                    self.instantiatedDevices.append(d)
                else:
                    raise Exception, "Can't connect %s: "%(d.description)+"Required input channels are already in use by other devices"





        
        
################################################################
# Input device container configuration widget

class DeviceContainerWidget(Qt.QWidget):
    def __init__(self, parent=None):
        super(DeviceContainerWidget, self).__init__(parent)

        # base layout
        self.gridLayout = Qt.QGridLayout(self)

        # create insert / remove buttons
        self.buttonRemove = Qt.QPushButton("<", self)
        self.buttonInsert = Qt.QPushButton(">", self)

        # create available device table view
        self.availabletable = GenericTableWidget(self, RowNumbers=True, SelectionBehavior=Qt.QAbstractItemView.SelectRows)
        
        # create instantiated device table view
        self.instantiatedtable = GenericTableWidget(self, RowNumbers=True, SelectionBehavior=Qt.QAbstractItemView.SelectRows)
        
        # add all items to the layout 
        self.gridLayout.addWidget(self.availabletable, 0, 0, 3, 2)
        self.gridLayout.addWidget(self.buttonInsert, 1, 2)
        self.gridLayout.addWidget(self.buttonRemove, 2, 2)
        self.gridLayout.addWidget(self.instantiatedtable, 0, 3, 3, 1)

        # actions
        self.connect(self.buttonInsert, Qt.SIGNAL("clicked()"), self._insertDevice)
        self.connect(self.buttonRemove, Qt.SIGNAL("clicked()"), self._removeDevice)
        self.connect(self.instantiatedtable, Qt.SIGNAL("doubleClicked(QModelIndex)"), self._updateDevice)
        self.connect(self.availabletable, Qt.SIGNAL("doubleClicked(QModelIndex)"), self._dcinsertDevice)
        
    def _insertDevice(self):
        idx = self.availabletable.getSelectedRow()
        self.emit(Qt.SIGNAL('insertDevice(int)'), idx)
        
    def _dcinsertDevice(self, modelIndex):
        idx = modelIndex.row()
        self.emit(Qt.SIGNAL('insertDevice(int)'), idx)
        
    def _removeDevice(self):
        idx = self.instantiatedtable.getSelectedRow()
        self.emit(Qt.SIGNAL('removeDevice(int)'), idx)
        
    def _updateDevice(self, modelIndex):
        idx = modelIndex.row()
        self.emit(Qt.SIGNAL('updateDevice(int)'), idx)

    def resizeEvent(self, event):
        self.availabletable.resizeRowsToContents()
        self.instantiatedtable.resizeRowsToContents()


