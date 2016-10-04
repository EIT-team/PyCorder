# -*- coding: utf-8 -*-
'''
EP-PreAmp input device

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
@date: $Date: 2013-06-10 12:20:40 +0200 (Mo, 10 Jun 2013) $
@version: 1.0

B{Revision:} $LastChangedRevision: 201 $
'''

from modbase import *
from devbase import HardwareInputDevice
from tools.modview import GenericTableWidget

class EppChProperty(object):
    def __init__(self):
        self.setDefault()
    def setDefault(self):
        self.gain = "50"

class DeviceEpPreamp(HardwareInputDevice):    
    deviceName = "EP-PreAmp"
    def __init__(self):
        # initialize the base class
        HardwareInputDevice.__init__(self)
        
        # device input configuration
        self.inputGroup = ChannelGroup.EEG              # input channel group
        self.inputChannel = 1                           # device is attached to this channel
        self.inputImpedances = [ImpedanceIndex.DATA, ImpedanceIndex.GND]    # we need impedance values for each input channel
        self.possibleGroups = [ChannelGroup.EEG]
        self.possibleChannels = range(1,161)
        self.possibleGains = ['off','1','50']
        
        # device output configuration
        self.outputGroup = ChannelGroup.EPP
        self.outputImpedances = [ImpedanceIndex.DATA, ImpedanceIndex.REF, ImpedanceIndex.GND]
        #self.outputGroup = ChannelGroup.AUX
        self.outputChannelName = "EP"

        # set default input channel gains
        self.channelProperties = []
        for c in range(0, 16):
            prop = EppChProperty()
            if c >= 2:
                prop.gain = "off"
            self.channelProperties.append(prop)

        self.update_device()
        
    def prepareOutputMask(self):
        ''' Create a mask for enabled output channels. Hide all channels with gain = "off".
        @return: channel index array 
        '''
        mask = lambda x: x.gain != "off"
        ch_map = np.array(map(mask, self.channelProperties))
        # indices of enabled output channels
        indices = np.nonzero(ch_map)[0]     
        return indices
        
    def output_function(self, x):
        # subtract reference channels from data channels and scale to gain
        return (x[:,0] - x[:,1]) * self.gain_div

    def impedance_function(self, x):
        # put the electrode impedance values from the reference channels into the data channels
        # keep the GND value from data channel 
        out = x[:,0]
        ref = x[:,1]
        # set unused values to 0
        mask = (np.zeros(out.shape[1]) == 0)
        mask[self.outputImpedances] = False
        out[:,mask] = 0
        # combine data and reference impedances
        out[:,ImpedanceIndex.REF] = ref[:,ImpedanceIndex.DATA]
        return out

    def update_device(self):
        ''' Configure the input channel numbers, based on the actiCHamp EEG channel number
        '''
        # adjust input channel to module boundaries
        self.inputChannel = ((self.inputChannel-1)/32) * 32 + 1
        self.inputChannels = np.arange(self.inputChannel, self.inputChannel+32).reshape(-1,2)
        # create the gain divisor array
        g = []
        for p in self.channelProperties:
            try:
                gdiv = 0.5 / float(p.gain)
            except:
                gdiv = 0.0
            g.append(gdiv) 
        self.gain_div = np.array(g, float)[:,np.newaxis]
        self.description = "%s connected to %s channels %i-%i\nGain: %s"%(self.deviceName, 
                                                                ChannelGroup.Name[self.inputGroup], 
                                                                self.inputChannel,
                                                                self.inputChannel+31,
                                                                ", ".join(p.gain for p in self.channelProperties))

    def configure_device(self):
        ''' override default configuration dialog
        '''
        dlg = EPPConfigDlg()
        # gain selection
        columns =  [
                    {'variable':'gain', 'header':'Input gain', 'edit':True, 'editor':'combobox'},
                   ]
        cblist = {'gain':self.possibleGains}
        dlg.gaintable.setData(self.channelProperties, columns, cblist)
        
        # module number from channel
        module = ((self.inputChannel-1)/32) + 1
        dlg.spinboxModule.setValue(module)
        dlg.setWindowTitle("%s configuration"%(self.deviceName))
        if dlg.exec_() == Qt.QDialog.Accepted:
        # adjust input channel to module boundaries
            self.inputChannel = (dlg.spinboxModule.value()-1) * 32 + 1
            self.inputGroup = self.possibleGroups[0]
            self.update_device()
            return True
        return False


    def getXML(self):
        ''' Get device properties as XML for configuration file
        @return: objectify XML element
        '''
        E = objectify.E
        properties = E.properties()
        for c in range(len(self.channelProperties)):
            chproperty = E.property(
                                    E.channel(c),
                                    E.gain(self.channelProperties[c].gain)
                                    )
            properties.append(chproperty)
            
        ch = E.device(
                      E.classname(self.__class__.__name__),
                      E.inputgroup(self.inputGroup),
                      E.inputchannel(self.inputChannel),
                      properties,
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
        
        # get channel properties
        for prop in self.channelProperties:
            prop.setDefault()
        try:
            if xml.find("properties") != None:
                for prop in xml.properties.iterchildren():
                    c = prop.channel.pyval
                    if c >= 0 and c < len(self.channelProperties):
                        self.channelProperties[c].gain = prop.gain.pyval
        except:
            pass
        
        self.update_device()
        return version




################################################################
# Default configuration dialog for input devices

class EPPConfigDlg(Qt.QDialog):
    def __init__(self, parent=None):
        super(EPPConfigDlg, self).__init__(parent)
        
        # create module selection items
        self.labelConnectedTo = Qt.QLabel("Connected to ")
        self.labelModule = Qt.QLabel("EEG module #")
        self.spinboxModule = Qt.QSpinBox()
        self.spinboxModule.setMinimum(1)
        self.spinboxModule.setMaximum(5)
        self.buttonBox = Qt.QDialogButtonBox(Qt.QDialogButtonBox.Ok | Qt.QDialogButtonBox.Cancel)

        # create gain table view
        self.gaintable = GenericTableWidget(self, RowNumbers=True)
        self.gaintable.setMaximumWidth(150)

        # create layout
        layout = Qt.QGridLayout()

        layout.addWidget(self.labelConnectedTo, 0, 0)
        layout.addWidget(self.labelModule, 0, 1)
        layout.addWidget(self.spinboxModule, 0, 2)
        layout.addWidget(self.gaintable, 1, 2, 1, 1)

        vlayout = Qt.QVBoxLayout()
        vlayout.addLayout(layout)
        vlayout.addWidget(self.buttonBox)
        
        self.setLayout(vlayout)
        self.setWindowTitle("Device")

        self.connect(self.buttonBox, Qt.SIGNAL("accepted()"), self.accept)
        self.connect(self.buttonBox, Qt.SIGNAL("rejected()"), self.reject)





