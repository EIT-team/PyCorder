# -*- coding: utf-8 -*-
'''
Base class for all hardware input devices

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
@date: $Date: 2013-06-18 16:31:58 +0200 (Di, 18 Jun 2013) $
@version: 1.0

B{Revision:} $LastChangedRevision: 204 $
'''


from modbase import *
from tools.modview import GenericTableWidget


################################################################
# Base class for input devices

class HardwareInputDevice():
    deviceName = ""
    def __init__(self):
        
        # XML parameter version
        # 1: initial version
        self.xmlVersion = 1 
               
        # device input configuration
        self.inputGroup = ChannelGroup.AUX          # input channel group
        self.inputChannel = 1                       # device is attached to this channel
        self.inputImpedances = []                   # ImpedanceIndex list with required input impedances 
        self.possibleGroups = [ChannelGroup.AUX]    # groups to which the device can be connected
        self.possibleChannels = range(1,9)          # channels to which the device can be connected
        
        # device output configuration
        self.outputGroup = ChannelGroup.EEG         # processed channels will be put into this group 
        self.outputChannelName = "x"                # default channel name prefix
        self.outputImpedances = []                  # ImpedanceIndex list for output impedances 
        
        # calculated values        
        self.inputChannels = np.array([[],[]])      # input channel numbers for this device, grouped by function 
        self.input_channel_indices = np.array([[]]) # input channel indices for this device
        self.outputProperties = np.array([])
        self.description = self.deviceName
        self.hasInputImpedances = False

    def hasOverlappingInputChannels(self, device):
        ''' check for overlapping input channels
        @param device: HardwareInputDevice to compare with
        @return: True if overlapping channels detected
        '''
        # compare input groups of both devices
        if device.inputGroup != self.inputGroup:
            return False
        # compare input channels of both devices
        i1 = self.inputChannels.flatten()[None,...]
        i2 = device.inputChannels.flatten()[...,None]
        return (i1==i2).any() 
    
    def process_updatechannels(self, params):
        ''' Get the whole input data object, select the affected channels 
        and return an output property array and indices of processed channels
        '''
        # get the required channel indices
        mask = lambda x: (x.inputgroup == self.inputGroup) and (x.input in self.inputChannels)
        ch_map = np.array(map(mask, params.channel_properties))
        indices = np.nonzero(ch_map)[0]     # indices of required channels
        # dictionary with channel number as key and its index in the input data array as value
        idx = dict((x.input, indices[i]) for i, x in enumerate(params.channel_properties[indices]))
        # indices of required channels
        if len(params.channel_properties) == 0:
            self.input_channel_indices = np.array([[]])
        else:
            self.input_channel_indices = np.empty_like(self.inputChannels) 
            for i in range(self.input_channel_indices.shape[0]):
                for n in range(self.input_channel_indices.shape[1]):
                    if not idx.has_key(self.inputChannels[i][n]):
                        self.input_channel_indices = np.array([[]])
                        raise Exception("missing input channels for device: " + self.deviceName)
                    self.input_channel_indices[i,n] = idx[self.inputChannels[i,n]]
        # Update and return the channel properties for this device
        # take the parameters from the first channel in each function group, modify group and name and use it
        # as output channel for this device
        if self.input_channel_indices.size > 0:
            #print "Input Channel Indices", self.input_channel_indices
            self.outputProperties = params.channel_properties[self.input_channel_indices[:,0]]
            n = 1
            for ch in self.outputProperties:
                ch.enable = False
                ch.group = self.outputGroup
                ch.name = "%s%d"%(self.outputChannelName, n)
                n += 1
            # add impedance identifiers to channel values 
            self.hasInputImpedances = (params.eeg_channels[self.input_channel_indices.flatten()][:,self.inputImpedances] == 1).all()
            outputData = params.eeg_channels[self.input_channel_indices[:,0]]
            outputData[:] = 0
            if params.recording_mode == RecordingMode.IMPEDANCE and self.hasInputImpedances:
                for imp_index in self.outputImpedances:
                    outputData[:,imp_index] = 1
            # prepare and use the output mask for enabled channel selection 
            self.outputMask = self.prepareOutputMask()
            outputProperties = self.outputProperties[self.outputMask]
            outputData = outputData[self.outputMask,:]
        else:
            self.outputProperties = np.array([])
            self.outputMask = np.array([])
            outputData = np.array([[]])
            outputProperties = self.outputProperties

        return outputProperties, outputData, self.input_channel_indices.flatten()
            
    def prepareOutputMask(self):
        ''' Create a mask for enabled output channels. Override this function if you want to hide some of the default output channels.
        @return: channel index array 
        '''
        # the default implementation enables all output channels
        mask = lambda x: True
        ch_map = np.array(map(mask, self.outputProperties))
        # indices of enabled output channels
        indices = np.nonzero(ch_map)[0]     
        return indices
        
            
    def output_function(self, x):
        ''' This is the modules data process function, override this function and implement your own algorithm 
        '''
        raise Exception("function not implemented")
            
    def impedance_function(self, x):
        ''' This is the modules impedance process function, override this function and implement your own algorithm 
        '''
        raise Exception("function not implemented")
            
    def process_input(self, data):
        ''' Get the whole input channels data block, select and process the affected channels 
        and return the processed output channels array or None
        '''
        # anything todo?
        if self.input_channel_indices.size == 0:
            return None
        # select the device input channels
        x = data.eeg_channels[self.input_channel_indices]
        if data.recording_mode == RecordingMode.IMPEDANCE:
            device_channels = self.impedance_function(x)
        else:
            device_channels = self.output_function(x)
        return device_channels[self.outputMask]

    def update_device(self):
        pass
    
    def configure_device(self):
        dlg = DeviceConfigDlg()
        curidx = 0
        for idx, item in enumerate(self.possibleGroups):
            dlg.comboGroup.addItem(ChannelGroup.Name[item])
            if item == self.inputGroup:
                curidx = idx
        dlg.comboGroup.setCurrentIndex(curidx)
        dlg.spinboxChannel.setValue(self.inputChannel)
        dlg.spinboxChannel.setMinimum(self.possibleChannels[0])
        dlg.spinboxChannel.setMaximum(self.possibleChannels[-1])
        dlg.setWindowTitle("%s configuration"%(self.deviceName))
        if dlg.exec_() == Qt.QDialog.Accepted:
            self.inputChannel = dlg.spinboxChannel.value()
            self.inputGroup = self.possibleGroups[dlg.comboGroup.currentIndex()]
            self.update_device()
            return True
        return False
    
    def getXML(self):
        ''' Get device properties as XML for configuration file
        @return: objectify XML element
        '''
        E = objectify.E
        ch = E.device(
                      E.classname(self.__class__.__name__),
                      E.inputgroup(self.inputGroup),
                      E.inputchannel(self.inputChannel),
                      ) 
        ch.attrib["version"] = str(self.xmlVersion)
        return ch

    def setXML(self, xml):
        ''' Setup device properties from XML configuration file
        @param xml: objectify XML device configuration 
        '''
        # check version, has to be lower or equal than current version
        version = xml.get("version")
        if (version == None) or (int(version) > self.xmlVersion):
            raise Exception, "Device %s wrong version > %d"%(self.deviceName, self.xmlVersion)
        version = int(version)
        
        # get the values
        self.inputGroup = xml.inputgroup.pyval
        self.inputChannel = xml.inputchannel.pyval
        self.update_device()
        return version




################################################################
# Default configuration dialog for input devices

class DeviceConfigDlg(Qt.QDialog):
    def __init__(self, parent=None):
        super(DeviceConfigDlg, self).__init__(parent)
        self.labelConnectedTo = Qt.QLabel("Connected to:")
        self.comboGroup = Qt.QComboBox()
        self.labelChannel = Qt.QLabel("Channel #")
        self.spinboxChannel = Qt.QSpinBox()
        self.spinboxChannel.setMinimum(1)
        self.spinboxChannel.setMaximum(256)
        self.buttonBox = Qt.QDialogButtonBox(Qt.QDialogButtonBox.Ok | Qt.QDialogButtonBox.Cancel)

        layout = Qt.QHBoxLayout()
        layout.addWidget(self.labelConnectedTo)
        layout.addWidget(self.comboGroup)
        layout.addWidget(self.labelChannel)
        layout.addWidget(self.spinboxChannel)

        vlayout = Qt.QVBoxLayout()
        vlayout.addLayout(layout)
        vlayout.addWidget(self.buttonBox)
        
        self.setLayout(vlayout)
        self.setWindowTitle("Device")

        self.connect(self.buttonBox, Qt.SIGNAL("accepted()"), self.accept)
        self.connect(self.buttonBox, Qt.SIGNAL("rejected()"), self.reject)









