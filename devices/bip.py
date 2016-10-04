# -*- coding: utf-8 -*-
'''
BipToAux input device

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
from devbase import HardwareInputDevice

    
class DeviceBipToAux(HardwareInputDevice):    
    deviceName = "BIP2AUX"
    def __init__(self):
        # initialize the base class
        HardwareInputDevice.__init__(self)
        
        # device input configuration
        self.inputGroup = ChannelGroup.AUX              # input channel group
        self.inputChannel = 1                           # device is attached to this group channel
        self.inputImpedances = []                       # no impedance values
        self.possibleGroups = [ChannelGroup.AUX]
        self.possibleChannels = range(1,9)
        self.inputGain = 100.0                          # analog gain is 100 for this module
        
        # device output configuration
        self.outputGroup = ChannelGroup.BIP
        self.outputChannelName = "BIP"
        self.outputImpedances = []                      # no impedance values
        self.update_device()
        
    def output_function(self, x):
        return x[:,0] / self.inputGain

    def impedance_function(self, x):
        return x[:,0] * 0.0                             # this module has no impedance mode

    def update_device(self):
        ''' Configure the input channel numbers
        '''
        self.inputChannels = np.array([[self.inputChannel]])
        self.description = "%s connected to %s channel %i\nGain: %.0f"%(self.deviceName, 
                                                                      ChannelGroup.Name[self.inputGroup], 
                                                                      self.inputChannel,
                                                                      self.inputGain)





