# -*- coding: utf-8 -*-
'''
Tutorial Module 1

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

class TUT_1(ModuleBase):
    ''' Tutorial Module 1
    
    Command and event handling. 
        - How to get and print the channel configuration
        - Modify the channel configuration: Subtract channel two from channel one, put the
          result into channel one and change the label of channel one
        - Evaluate module events
    '''

    def __init__(self, *args, **keys):
        ''' Constructor
        '''
        # initialize the base class, give a descriptive name
        ModuleBase.__init__(self, name="Tutorial 1", **keys)    

        # initialize module variables
        self.data = None                # hold the data block we got from previous module
        self.dataavailable = False      # data available for output to next module 
        
    def _modify_properties(self, params):
        ''' Update channel properties
        @param params: EEG_DataBlock object.
        '''
        # if there are two or more channels available, we want to subtract channel 2 from channel 1 
        # we need at least two channels for subtraction
        if len(params.channel_properties) >= 2:
            # change the label of channel 1 -> "ch1 - ch2" 
            params.channel_properties[0].name += " - " + params.channel_properties[1].name
            # and remove channel 2 from configuration. But remember to remove channel 2 also from data array! 
            params.channel_properties = np.delete(params.channel_properties, 1, 0)
        
        
    def process_update(self, params):
        ''' Evaluate and maybe modify the data block configuration.
        @param params: EEG_DataBlock object. We will get a complete EEG_DataBlock object 
        but we are only interested to get the channel configuration and sample rate at 
        this time.   
        @return: EEG_DataBlock object
        '''
        # print the channel configuration to the Python console 
        print "%s, process_update()"%(self._object_name) # just to see where we are
        print " Number of channels: %d, Sample Rate = %d [Hz]"%(len(params.channel_properties), params.sample_rate)
        print " Channel names:"
        names = "  "
        for channel in params.channel_properties:
            names += channel.name + ", "
        print names

        # modify channel properties
        self._modify_properties(params)
        
        return params # don't forget to pass the configuration down to the next module

    
    def process_start(self):
        ''' Prepare the module for startup
        '''
        # put this event into the log entries
        self.send_event(ModuleEvent(self._object_name, 
                                    EventType.LOGMESSAGE, 
                                    info="process_start"))

    
    def process_stop(self):
        ''' Finalize the data acquisition process
        '''
        # put this event into the log entries
        self.send_event(ModuleEvent(self._object_name, 
                                    EventType.LOGMESSAGE, 
                                    info="process_stop"))


    def process_event(self, event):
        ''' Handle events from attached receivers
        @param event: ModuleEvent object
        '''
        # look for the event types of interest
        eventinfo = "%s: "%(event.module)
        if event.type == EventType.COMMAND:
            eventinfo += "COMMAND %s, %s"%(event.info, str(event.cmd_value))
        elif event.type == EventType.ERROR:
            eventinfo += "ERROR %s, %s"%(event.info, str(event.severity))
        elif event.type == EventType.LOGMESSAGE:
            eventinfo += "LOGMESSAGE %s"%(event.info)
        elif event.type == EventType.MESSAGE:
            eventinfo += "MESSAGE %s"%(event.info)
        elif event.type == EventType.STATUS:
            eventinfo += "STATUS %s, %s"%(event.info, str(event.status_field))

        print eventinfo

        
    def process_input(self, datablock):
        ''' Get data from previous module and subtract channel 2 from channel 1
        @param datablock: EEG_DataBlock object 
        '''
        self.dataavailable = True       # signal data availability
        self.data = datablock           # get a local reference
        
        # Data modification: subtract ch2 from ch1 and put the result into ch1
        # for subtraction we need at least two channels
        if len(self.data.channel_properties) >= 2:
            # subtract ch2 from ch1
            self.data.eeg_channels[0] -= self.data.eeg_channels[1]
            # replace channel configuration within the data block with our modified configuration
            self._modify_properties(self.data)
            # remove channel 2 from data array
            self.data.eeg_channels = np.delete(self.data.eeg_channels, 1, 0)


        # let the application status bar display the sample counter 
        self.send_event(ModuleEvent(self._object_name, 
                                    EventType.MESSAGE,
                                    info = self.data.sample_counter))
        
        # raise a divide by zero exception after 10000 received samples, 
        # just to see what happens ;-)
        if self.data.sample_counter > 10000:
            a = 100/0
    
   
    def process_output(self):
        ''' Send data out to next module
        @return: EEG_DataBlock or None if no data available
        '''
        if not self.dataavailable:
            return None
        self.dataavailable = False
        return self.data
    

