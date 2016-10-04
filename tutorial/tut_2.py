# -*- coding: utf-8 -*-
'''
Tutorial Module 2

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

from modbase import *

class TUT_2(ModuleBase):
    ''' Tutorial Module 2
    
    Data Processing. 
        - Create and use a channel selection mask
        - Demonstrate the effect of for loops
        - Insert markers
    '''

    def __init__(self, *args, **keys):
        ''' Constructor
        '''
        # initialize the base class, give a descriptive name
        ModuleBase.__init__(self, name="Tutorial 2", **keys)    

        # initialize module variables
        self.data = None                # hold the data block we got from previous module
        self.dataavailable = False      # data available for output to next module 
        
    def process_update(self, params):
        ''' Evaluate and maybe modify the data block configuration.
        @param params: EEG_DataBlock object. We will get a complete EEG_DataBlock object 
        but we are only interested to get the channel configuration and sample rate at 
        this time.   
        @return: EEG_DataBlock object
        '''

        # get a local reference to the parameter object  
        self.params = params
        
        # select channels with "_x2" in channel name, these channels will be multiplied by 2
        mask = lambda x: ("_x2" in x.name) # selection function
        mask_ref = np.array(map(mask, self.params.channel_properties)) # create an boolean array with results of the mask function
        self.mask_index = np.nonzero(mask_ref) # create an array of TRUE indices
        print self.mask_index
        
        # search channels with "_loop" in channel name, 
        # all channels will be processed within a for-loop
        mask = lambda x: ("_loop" in x.name) # selection function
        mask_ref = np.array(map(mask, self.params.channel_properties)) # create an boolean array with results of the mask function
        self.loop = (np.nonzero(mask_ref)[0].size > 0) # use for loop if any channel name contains _loop
        print self.loop
        
        return self.params # don't forget to pass the configuration down to the next module

        
    def process_input(self, datablock):
        ''' Get data from previous module.
            - Multiply selected channels by 2
            - Add an DC offest to all channels.
            - Create and insert 1s tick markers.
        @param datablock: EEG_DataBlock object 
        '''
        self.dataavailable = True       # signal data availability
        self.data = datablock           # get a local reference
        
        # multiply selected channels by 2
        self.data.eeg_channels[self.mask_index] *= 2.0
        
        # add an 100uV DC offset to all channels 
        if self.loop:
            # use for-loops to demonstrate the loss of performance
            for channel in range(self.data.eeg_channels.shape[0]):
                for n in range(self.data.eeg_channels.shape[1]):
                    self.data.eeg_channels[channel][n] += 100.0
        else:
            # use array function
            self.data.eeg_channels += 100.0
    
        # Create and insert markers
        # search 1s sample counter ticks
        tickmap = (self.data.sample_channel[0] % self.data.sample_rate) == 0 
        ticks = np.nonzero(tickmap)[0]     
        # add 1s tick markers
        for tick in ticks:
            self.data.markers.append(EEG_Marker(type="1s Tick",
                                                description="1s",
                                                position=self.data.sample_channel[0][tick],
                                                channel=0))
    
    def process_output(self):
        ''' Send data out to next module
        @return: EEG_DataBlock object
        '''
        if not self.dataavailable:
            return None
        self.dataavailable = False
        return self.data
    

