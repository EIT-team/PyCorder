# -*- coding: utf-8 -*-
'''
Base class for all recording modules

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
@date: $Date: 2013-06-10 12:20:40 +0200 (Mo, 10 Jun 2013) $
@version: 1.0

B{Revision:} $LastChangedRevision: 201 $
'''

from PyQt4 import Qt
import numpy as np
import time
import datetime
import Queue
import threading
import copy
import os, sys, traceback
from lxml import etree
from lxml import objectify 


# impedance value invalid (electrode disconnected)
#CHAMP_IMP_INVALID = 2147483647  # INT_MAX
CHAMP_IMP_INVALID = 999900  # INT_MAX

def GetExceptionTraceBack():
    ''' Get last trace back info as tuple
    @return: tuple(string representation, filename, line number, module)
    '''
    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
    tb = traceback.extract_tb(exceptionTraceback)[-1]
    fn = os.path.split(tb[0])[1]
    txt = "%s, %d, %s"%(fn, tb[1], tb[2])
    return tuple([txt, fn, tb[1], tb[2]])


class ModuleError(Exception):
    ''' Generic module exception
    '''
    def __init__(self, module, value):
        ''' Create the exception object
        @param module: module object name
        @param value: exception description
        '''   
        self.value = str(module) + ': ' + str(value)
    def __str__(self):
        return self.value


class EventType:
    ''' Module Event Types
    @ivar LOGMESSAGE: display event description in status bar info field and log it
    @ivar STATUS: display event description in dedicated status_field
    @ivar MESSAGE: display event description in status bar info field
    @ivar ERROR: an error occured, see info and severity
    @ivar COMMAND: send an command to the module chain
    @ivar LOG: only log the message, without showing it in the status bar     
    '''
    (LOGMESSAGE, STATUS, MESSAGE, ERROR, COMMAND, LOG) = range(6)

    
class ErrorSeverity:
    ''' Module event classification in case of ERROR
    @ivar IGNORE: error can be safely ignored
    @ivar NOTIFY: notify user
    @ivar STOP: notify and stop acquisition
    '''
    (IGNORE, NOTIFY, STOP) = range(3)

class ModuleEvent(object):
    ''' Generic module event
    '''
    def __init__(self, module, type, info="", severity=ErrorSeverity.IGNORE, status_field="", cmd_value=0):
        ''' Initialize the event
        @param module: module name (string)
        @param type: event type (class EventType)
        @param info: event description (could be a string or numerical value)
        @param severity: event classification in case of ERROR (class ErrorSeverity) 
        @param status_field: status bar field name
        @param cmd_value: any numerical value in case of COMMAND
        '''
        self.module = module
        self.type = type
        self.info = info
        self.severity = severity
        self.status_field = status_field
        self.cmd_value = cmd_value
        self.event_time = datetime.datetime.now()
        
    def __str__(self):
        ''' Event string representation
        '''
        txt = str(self.module) + ': ' + str(self.info)
        return txt


class RecordingMode:
    ''' Module Recording Modes
    @ivar NORMAL: Record EEG
    @ivar TEST: Record test signals
    @ivar IMPEDANCE: Impedance measurement 
    '''
    (NORMAL, TEST, IMPEDANCE) = range(3)

class ImpedanceIndex:
    ''' Index for impedance values within the data array for each channel
    '''
    (DATA, REF, GND) = range(3)
    Name = ["+", "-", "GND"]

class ChannelGroup:
    ''' EEG channel groups used in EEG_ChannelProperties
    @ivar EEG: channel belongs to EEG channel group
    @ivar AUX: channel belongs to AUX channel group
    @ivar EPP: channel belongs to EPP (EP-PreAmp) group
    '''
    (EEG, AUX, EPP, BIP) = range(4)
    Name = ["EEG", "AUX", "EPP", "BIP"]


class EEG_ChannelProperties(object):
    ''' Properties of EEG channels
    '''
    def __init__(self, name):
        ''' Set default property values
        @param name: channel label
        '''
        # XML parameter version
        # 1: initial version
        # 2: added notchfilter and reference
        # 3: added inputgroup
        self.xmlVersion = 3                 #: XML configuration data version

        self.input = 0                      #: hardware input channel number
        self.inputgroup = ChannelGroup.EEG  #: hardware input channel group
        self.enable = True                  #: enable channel for recording
        self.name = name                    #: channel label
        self.refname = ""                   #: reference channel name
        self.group = ChannelGroup.EEG       #: logical channel group
        self.lowpass = 100.0                #: low pass cutoff frequency in Hz
        self.highpass = 0.0                 #: high pass cutoff frequency in Hz
        self.notchfilter = False            #: enable / disable notch filter
        self.isReference = False            #: use this channel as reference channel
        self.color = Qt.Qt.darkBlue         #: display color
        self.unit = ""                      #: channel unit string (use uV if empty)
        
    def __cmp__(self, other):
        ''' Compare two channels by name and group
        @param other: channel to compare with
        '''
        if other == None:
            return -1
        if (self.name == other.name) & (self.group == other.group):
            return 0
        else:
            return -1

    def getXML(self):
        ''' Get channel properties for XML configuration file
        @return: objectify XML element::
            <channel version="1" ...>
                <input>0</input>
                ...
            </channel>
        '''
        E = objectify.E
        ch = E.channel(E.input(self.input), 
                       E.inputgroup(self.inputgroup),
                       E.enable(self.enable), 
                       E.name(self.name),
                       E.group(self.group),
                       E.lowpass(self.lowpass),
                       E.highpass(self.highpass),
                       E.notchfilter(self.notchfilter),
                       E.reference(self.isReference))
        ch.attrib["version"] = str(self.xmlVersion)
        return ch


    def setXML(self, xml):
        ''' Setup channel properties from XML configuration file
        @param xml: objectify XML channel configuration 
        '''
        # check version, has to be lower or equal than current version
        version = xml.get("version")
        if (version == None) or (int(version) > self.xmlVersion):
            raise Exception, "channel %d wrong version > %d"%(self.input, self.xmlVersion)
        version = int(version)
        
        # get the values
        self.input = xml.input.pyval
        self.enable = xml.enable.pyval
        self.name = xml.name.pyval
        self.group = xml.group.pyval
        self.lowpass = xml.lowpass.pyval
        self.highpass = xml.highpass.pyval
        if version > 1:
            self.notchfilter = xml.notchfilter.pyval
            self.isReference = xml.reference.pyval
        
        # get the hardware input channel group 
        if version > 2:
            self.inputgroup = xml.inputgroup.pyval
        else:
            self.inputgroup = self.group


class EEG_Marker(object):
    ''' Recording marker position and description
    '''
    def __init__(self, position=0, points=1, type="unknown", description="", channel=0, date=False):
        ''' Create a new marker object
        '''
        self.position = position        #: Position of marker in data points
        self.points = points            #: Number of points
        self.type = type                #: Marker type ("Stimulus", etc.)
        self.description = description  #: Marker description
        self.invisible = False          #: If true, marker should not be shown.
        self.channel = channel          #: Channel number of marker (0 = all channels).
        self.date = date                #: If true, write date / time to file
             

class EEG_DataBlock(object):
    ''' Block of EEG data, channel properties, marker and impedance values 
    '''
    def __init__(self, eeg=32, aux=8):
        ''' Set default values for requested number of channels
        @param eeg: number of EEG channels for this block
        @param aux: number of AUX channels for this block
        '''
        self.sample_counter = 0          #: total number of received samples
        self.sample_rate = 500.0         #: sample rate in Hz
        self.eeg_channels = np.zeros((eeg+aux, 1000), 'd')      #: channel data for EEG and AUX
        self.trigger_channel = np.zeros((1, 1000), np.uint32)   #: trigger values
        self.sample_channel = np.zeros((1, 1000), np.uint64)    #: sample counter
        self.channel_properties = self.get_default_properties(eeg, aux) #: channel properties
        self.markers = []                   #: marker descriptions and positions
        self.impedances = []                #: impedance values [Ohm] -> obsolete since 1.0.6, should be left empty
        self.block_time = datetime.datetime.now()   #: block creation time
        self.performance_timer = 0          #: processing time since block creation
        self.performance_timer_max = 0      #: maximum module processing time for this block
        self.recording_mode = RecordingMode.NORMAL #: recording mode of this block
        self.ref_channel_name = ""          #: combined name of reference channels

    def __copy__(self):
        ''' We always need a deep copy of channel properties, markers and impedance values
        '''
        copy_obj = EEG_DataBlock(1,1)
        copy_obj.sample_counter = self.sample_counter
        copy_obj.sample_rate = self.sample_rate
        copy_obj.eeg_channels = self.eeg_channels
        copy_obj.trigger_channel = self.trigger_channel
        copy_obj.sample_channel = self.sample_channel
        copy_obj.channel_properties = copy.deepcopy(self.channel_properties)
        copy_obj.markers = copy.deepcopy(self.markers)
        copy_obj.impedances = copy.deepcopy(self.impedances)
        copy_obj.block_time = copy.deepcopy(self.block_time)
        copy_obj.performance_timer = self.performance_timer
        copy_obj.performance_timer_max = self.performance_timer_max
        copy_obj.recording_mode = self.recording_mode
        copy_obj.ref_channel_name = self.ref_channel_name
        return copy_obj 

    def __cmp__(self, other):
        ''' Compare settings of two data blocks
        '''
        if other == None:
            return -1
        if self.sample_rate != other.sample_rate:
            return -1
        if self.channel_properties.shape != other.channel_properties.shape:
            return -1
        if (self.channel_properties == other.channel_properties).all() == False:
            return -1
        if self.recording_mode != other.recording_mode:
            return -1
        return 0
            
    def get_default_properties(self, eeg, aux):
        ''' Get an property array with default settings
        @param eeg: number of EEG channels
        @param aux: number of AUX channels
        '''
        channel_properties = []
        for c in range(0, eeg):
            # EEG channels
            ch = EEG_ChannelProperties("Ch%d"%(c+1))
            ch.inputgroup = ChannelGroup.EEG
            ch.group = ChannelGroup.EEG
            ch.input = c + 1
            channel_properties.append(ch)
        for c in range(0, aux):
            # AUX channels
            ch = EEG_ChannelProperties("Aux%d"%(c+1))
            ch.inputgroup = ChannelGroup.AUX
            ch.group = ChannelGroup.AUX
            ch.input = c + 1
            channel_properties.append(ch)
        return np.array(channel_properties)
    get_default_properties = classmethod(get_default_properties)






class ModuleBase(Qt.QObject):
    ''' Base class for all recording modules
    '''

    def __init__(self, usethread=True, queuesize=20, name="ModuleBase", instance=0):
        ''' Create a new recording module object
        @param usethread: true if data transfer should be handled internally by worker thread
        @param queuesize: size of receiver input queue in elements
        @param name: module object identifier 
        @param instance: instance number for this object
        '''
        Qt.QObject.__init__(self)
        # set identifier and instance
        self._object_name = name
        self._instance = instance
        # reset the receiver collection
        self._receivers = [] 

        # receiver input queue and data block
        self._input_queue = Queue.Queue(queuesize)
        self._input_data = EEG_DataBlock()

        # reset the I/O worker thread
        self._work = None
        self._running = False
        self._usethread = usethread
        self._thLock = threading.Lock()
        
    def terminate(self):
        ''' Destructor, override this method if you need to clean up 
        '''
        return
        
    def setDefault(self):
        ''' Set all module parameters to default values
        Override this method to provide your own default settings
        '''
        return
        
    def start(self):
        ''' Start the data transfer. Don't override this method.
        '''
        # flush input queue
        while not self._input_queue.empty():
            self._input_queue.get_nowait()
        # let derived class objects handle the start command
        try:
            self.process_start()
        except Exception as e:
            self.send_exception(e, ErrorSeverity.STOP)
            return
        # propagate start command to all attached receivers
        for receiver in self._receivers:
            receiver.start()
        # start the data transfer worker thread
        if self._usethread:
            if not self._running:
                # create a new thread because threads are not reusable
                self._running = True
                self._work = threading.Thread(target=self._worker_thread)  
                self._work.start()
        
    def stop(self):
        ''' Stop the data transfer.  Don't override this method.
        '''
        # terminate the data transfer worker thread
        if self._usethread:
            self._running = False    
            if self._work != None:
                self._work.join(5.0) # wait 5s for terminating
                self._work = None
        # propagate stop command to all attached receivers
        for receiver in self._receivers:
            receiver.stop()
        # let derived class objects handle the stop command
        try:
            self.process_stop()
        except Exception as e:
            self.send_exception(e, ErrorSeverity.NOTIFY)


    def query(self, command):
        ''' Ask attached modules if the requested command is acceptable
        @param command: requested command
        @return: True if acceptable, False if not 
        '''
        # let the module handle query first
        if not self.process_query(command):
            return False
        # propagate query to all attached receivers
        for receiver in self._receivers:
            if not receiver.query(command):
                return False
        return True
        

    def get_online_configuration(self):
        ''' Override this method to provide a online configuration pane
        @return: a QFrame object or None if you don't need a online configuration pane
        '''
        return None


    def get_configuration_pane(self):
        ''' Override this method to provide a configuration pane
        @return: a QFrame object or None if you don't need a configuration pane
        '''
        return None

    def get_display_pane(self):
        ''' Override this method to provide a signal display pane
        @return: a QFrame object or None if you don't need a display pane
        '''
        return None

    def get_module_info(self):
        ''' Get information about this module for the about dialog
        @return: information string or None if info is not available
        '''
        return None
    
    def update_receivers(self, params=None, propagate_only=False):
        ''' Propagate parameter update down to all attached receivers.
        Don't override this method.
        @param params: EEG_Datablock object
        @param propagate_only: don't update ourself  
        '''
        if not propagate_only:
            # let derived class objects process parameter update
            try:
                params = self.process_update(copy.copy(params))
            except Exception as e:
                self.send_exception(e, ErrorSeverity.STOP)
                return
        # propagate down to all attached receivers
        for receiver in self._receivers:
            receiver.update_receivers(params)
        
        
    def add_receiver(self, receiver):
        ''' Add an receiver object to the receiver collection.
        Don't override this method.
        @param receiver: ModuleBase object to add 
        '''
        if not self._usethread:
            return
        # propagate start command to added receiver
        if self._running:
            receiver.start()
        # attach receiver
        self._receivers.append(receiver)
        # get events from receiver
        self.connect(receiver, Qt.SIGNAL("event(PyQt_PyObject)"), self.receiver_event, Qt.Qt.QueuedConnection)
        # tell the receiver to get events from parent
        receiver.connect(self, Qt.SIGNAL("parentevent(PyQt_PyObject)"), receiver.parent_event, Qt.Qt.QueuedConnection)


    def remove_receiver(self, receiver):
        ''' Remove an receiver object from the receiver collection.
        Don't override this method.
        @param receiver: ModuleBase object to remove 
        '''
        if not self._usethread:
            return
        # detach receiver
        self._receivers.remove(receiver)
        # propagate stop command to removed receiver
        receiver.stop()


    def parent_event(self, event):
        ''' Get events from attached parent.
        Don't override this method.
        @param event: ModuleEvent object
        '''
        # let derived class objects handle the event
        self.process_event(event)
        # propagate event to receivers
        self.emit(Qt.SIGNAL('parentevent(PyQt_PyObject)'), event)

    def receiver_event(self, event):
        ''' Get events from attached receivers.
        Don't override this method.
        @param event: ModuleEvent object
        '''
        # let derived class objects handle the event
        self.process_event(event)
        # propagate event to parent
        #self.send_event(event)  
        self.emit(Qt.SIGNAL('event(PyQt_PyObject)'), event)

        
    def send_event(self, event):
        ''' Send ModuleEvent objects to all connected slots.
        Don't override this method.
        @param event: ModuleEvent object
        '''
        self.emit(Qt.SIGNAL('event(PyQt_PyObject)'), event)
        self.emit(Qt.SIGNAL('parentevent(PyQt_PyObject)'), event)

        
    def isRunning(self):
        ''' Get the worker thread state
        Don't override this method.
        @return: true if worker thread is running
        '''
        return self._running

    
    def process_event(self, event):
        ''' Override this method to handle events from attached receivers
        @param event: ModuleEvent
        '''
        return
        
        
    def process_input(self, datablock):
        ''' Override this method to get and process data from input queue. This method must be
        overridden! At least the input data must be provided as output::
            self.dataavailable = True
            self.data = datablock
        @param datablock: EEG_DataBlock object 
        '''
        raise ModuleError(self._object_name, "not implemented! This method must be overridden")


    def process_output(self):
        ''' Override this method to put processed data into output queue. This method must be
        overridden! At least pass through the input data::
            if self.dataavailable:
                return self.data
            else:
                return None
        @return: processed data block or None if no data available
        '''
        raise ModuleError(self._object_name, "not implemented! This method must be overridden")

    
    def process_update(self, params):
        ''' Override this method to evaluate and maybe modify the data block configuration.
        @param params: EEG_DataBlock object
        @return: EEG_DataBlock object  
        '''
        return params

    
    def process_start(self):
        ''' Override this method to prepare the module for startup
        '''
        return

    
    def process_stop(self):
        ''' Override this method to finalize the acquisition process
        '''
        return

    def process_query(self, command):
        ''' Override this method to accept or recject requested commands
        '''
        return True
    
    def process_idle(self):
        ''' Override this method to do something else during worker thread idle time or to
        change the thread suspend time.
        '''
        time.sleep(0.001)        # suspend thread (default = 1ms)
        return

    
    def receive_data(self):
        try:
            data = self._input_queue.get(False)
            return data
        except:
            return None
        
    def receive_data_available(self):
        return self._input_queue.qsize()


    def _transmit_data(self, data):
        ''' Put data into the input queue. This method is invoked from the parent module.
        Don't override this method.
        @param data: EEG_DataBlock object
        '''
        try:
            self._input_queue.put(data, False)
        except:
            self.send_event(ModuleEvent(self._object_name, EventType.ERROR,
                                        "Input queue FULL, overrun!", severity=ErrorSeverity.NOTIFY))

    def _worker_thread(self):
        ''' The worker thread takes data from the input queue and 
        puts the processed data into the output queue.
        Don't override this method.
        '''   
        while self._running:
            wt = 0                      # reset performance timer
            # process input queue
            self._thLock.acquire()
            try:
                data = self._input_queue.get(False)
                t = time.clock() 
                self.process_input(data)
                wt += time.clock() - t
                self._thLock.release()
            except Queue.Empty:
                self._thLock.release()
            except Exception as e:
                self._thLock.release()
                self.send_exception(e, severity=ErrorSeverity.STOP)
                
            
            # put data to all registered output queues
            self._thLock.acquire()
            try:
                self.output_timer = time.clock() 
                data = self.process_output()
                wt += time.clock() - self.output_timer
                self._thLock.release()
            except Exception as e:
                self._thLock.release()
                self.send_exception(e, severity=ErrorSeverity.STOP)
                data = None

            if data != None:
                data.performance_timer_max = max(data.performance_timer_max, wt)
                data.performance_timer += wt
                #for idx, receiver in enumerate(self._receivers):
                for idx, receiver in enumerate(reversed(self._receivers)):
                    if idx == 0:
                        receiver._transmit_data(data)
                    else:
                        receiver._transmit_data(copy.deepcopy(data))
                    
                    
            # give a chance for idle processing
            self.process_idle()

            
    def send_exception(self, exception, severity=ErrorSeverity.STOP):
        ''' Send Exception as ModuleEvent object to all connected slots.
        Don't override this method.
        @param exception: Exception() object
        @param severity: error severity
        '''
        tb = GetExceptionTraceBack()[0]
        self.send_event(ModuleEvent(self._object_name, EventType.ERROR, tb + " -> " + str(exception), severity=severity))


    def getXML(self):
        ''' Get module properties for XML configuration file. Override this method if you 
        want to put module properties into the configuration file.
        @return: objectify XML element::
            <ModuleName instance="n" version="v">
                <properties>
                    ...
                </properties>
            </ModuleName>
        '''
        return None


    def setXML(self, xml):
        ''' Set module properties from XML configuration file. Override this method if you 
        want to get module properties from configuration file.
        @param xml: complete objectify XML configuration tree, 
        module will search for matching values
        '''
        return


        
