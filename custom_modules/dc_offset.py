# -*- coding: utf-8 -*-
'''
Tutorial Module 3

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
from PyQt4 import QtGui
from PyQt4 import Qwt5 as Qwt
import collections

################################################################
# The module itself

class TUT_3(ModuleBase):
    ''' Tutorial Module 3
    
    Calculate and display a FFT for selected channels. Channel selection will be
    send from display module as command events.
      
        - GUI elements
            - Create and use configuration panes
            - Create and use a FFT signal pane
        - Data processing
            - collect chunks of data and send it to the signal pane
            - calculate and display the FFT
        - Cofiguration management
            - write parameters to XML stream
            - read parameters from XML stream
    '''

    def __init__(self, *args, **keys):
        ''' Constructor. 
        Initialize instance variables and instantiate GUI objects 
        '''
        # initialize the base class, give a descriptive name
        ModuleBase.__init__(self, name="Tutorial 3", **keys)    

        # XML parameter version
        # 1: initial version
        self.xmlVersion = 1
        
        # initialize module variables
        self.data = None                #: hold the data block we got from previous module
        self.dataavailable = False      #: data available for output to next module 
        self.channelFifo = collections.deque() #: channel selection FiFo
        self.params = EEG_DataBlock(0,0)    #: default channel configuration

        # Plot configuration data
        self.chunk = 1024               #: FFT chunk size
        self.frequency_range = 200      #: Display frequency range [Hz]
        self.plot_items = 4             #: Maximum number of plot items

        # instantiate online configuration pane
        self.onlinePane = _OnlineCfgPane()
        # connect the event handler for changes in chunk size
        self.connect(self.onlinePane.comboBoxChunk, 
                     Qt.SIGNAL("currentIndexChanged(int)"),
                     self.onlineValueChanged)
        # connect the event handler for changes in frequency
        self.connect(self.onlinePane.comboBoxFrequency, 
                     Qt.SIGNAL("currentIndexChanged(int)"),
                     self.onlineValueChanged)

        # instantiate signal pane
        self.signalPane = _SignalPane()

        # set default values
        self.setDefault()

    def setDefault(self):
        ''' Set all module parameters to default values
        '''
        self.chunk = 1024               
        self.frequency_range = 200      
        self.plot_items = 4      
        self.onlinePane.setCurrentValues(self.frequency_range, self.chunk)       
        
    def process_input(self, datablock):
        ''' Get data from previous module.
        Because we need to exchange data between different threads we will use 
        a queue object to send data to the display thread to be thread-safe.  
        @param datablock: EEG_DataBlock object 
        '''
        self.dataavailable = True       # signal data availability
        self.data = datablock           # get a local reference
        
        # anything to do ? check channel selection and recording mode.
        # If we are in impedance mode, it makes no sense to calculate the FFT
        if (self.channel_index[0].size == 0) or (self.data.recording_mode == RecordingMode.IMPEDANCE):
            return
        
        # because we need a predefined data chunk size, we have to collect data until
        # at least one data block of data with chunk size is available
        # so first we append data from selected channels to a local buffer
        append = self.data.eeg_channels[self.channel_index]
        self.eeg_channels = np.append(self.eeg_channels, append, 1) # append to axis 1 of local buffer 

        # slice the local buffer into chunks
        while self.eeg_channels.shape[1] > self.chunk:
            # copy data of chunk size from all selected channels
            bufcopy = self.eeg_channels[:,:self.chunk]
            self.eeg_channels = self.eeg_channels[:,self.chunk:]
            # send channel data to the signal pane queue
            if self.signalPane.data_queue.empty():
                self.signalPane.data_queue.put(bufcopy, False) 
            #print bufcopy.shape[1]
            
        # set different color for selected channels
        selected = self.data.channel_properties[self.channel_index]
        for ch in selected:
            ch.color = Qt.Qt.darkYellow
    
    
    def process_output(self):
        ''' Send data out to next module
        '''
        if not self.dataavailable:
            return None
        self.dataavailable = False
        return self.data
    
    
    def process_update(self, params):
        ''' Evaluate and maybe modify the channel configuration.
        @param params: EEG_DataBlock object.
        @return: EEG_DataBlock object
        '''
        # keep a reference of the channel configuration
        self.params = params
        # Create a new channel selection array and setup the signal pane
        self.updateSignalPane()
        return params
    
    
    def process_event(self, event):
        ''' Handle events from attached receivers. 
        @param event: ModuleEvent
        '''
        # Search for ModuleEvents from display module and update channel selection
        if (event.type == EventType.COMMAND) and (event.info == "ChannelSelected"):
            channel = event.cmd_value
            # if channel is already in selection, remove it
            if channel in self.channelFifo:
                self.channelFifo.remove(channel)
            else:
                self.channelFifo.appendleft(channel)
            # limit selection to max. entries
            while len(self.channelFifo) > self.plot_items:
                self.channelFifo.pop()
            # Create a new channel selection array and setup the signal pane
            self.updateSignalPane()
    
    
    def updateSignalPane(self):
        ''' Create a channel selection array and setup the signal pane
        '''
        # acquire ModuleBase thread lock
        self._thLock.acquire()
        
        # get values from online configuration pane
        self.frequency_range, self.chunk = self.onlinePane.getCurrentValues()
        
        # if channel FiFo contains more than maximum configured items, remove odd
        while len(self.channelFifo) > self.plot_items:
            self.channelFifo.pop()
        
        # create channel selection indices from channel FiFo
        mask = lambda x: (x.name in self.channelFifo)
        channel_ref = np.array(map(mask, self.params.channel_properties))
        self.channel_index = np.nonzero(channel_ref)
        
        # create empty calculation buffers
        if self.params.eeg_channels.shape[0] > 0:
            self.eeg_channels = np.delete(np.zeros_like(self.params.eeg_channels[self.channel_index]),
                                          np.s_[:], 
                                          1)
        
        # create FFT plot for each selected channel
        self.signalPane.setupDisplay(self.params.channel_properties[self.channel_index],
                                     self.params.sample_rate, 
                                     self.chunk, 
                                     self.frequency_range)
        # release ModuleBase thread lock
        self._thLock.release()
    
        
    def get_display_pane(self):
        ''' Get the signal display pane
        @return: a QFrame object or None if you don't need a display pane
        '''
        return self.signalPane

    def get_online_configuration(self):
        ''' Get the online configuration pane
        @return: a QFrame object or None if you don't need a online configuration pane
        '''
        return self.onlinePane
    
    def get_configuration_pane(self):
        ''' Get the configuration pane
        @return: a QFrame object or None if you don't need a configuration pane
        '''
        cfgPane = _ConfigurationPane(self)
        return cfgPane

    def onlineValueChanged(self, int):
        ''' Event handler for changes in frequency and chunk size 
        '''
        # Create a new channel selection array and setup the signal pane
        self.updateSignalPane()
    
    
    def getXML(self):
        ''' Get module properties for XML configuration file
        @return: objectify XML element::
            e.g.
            <Tut_FFT version="1" module="FFT" instance="0">
                <frequency_range>200.0</frequency_range>
                <chunk_size>2048</chunk_size>
                <plot_items>4</plot_items>
            </Tut_FFT>
        '''
        E = objectify.E
        cfg = E.Tut_FFT(E.frequency_range(self.frequency_range),
                        E.chunk_size(self.chunk),
                        E.plot_items(self.plot_items),
                        version=str(self.xmlVersion),
                        module="FFT",
                        instance=str(self._instance))
        return cfg
        
        
    def setXML(self, xml):
        ''' Set module properties from XML configuration file
        @param xml: complete objectify XML configuration tree, 
        module will search for matching values
        '''
        # search module configuration data
        storages = xml.xpath("//Tut_FFT[@module='FFT' and @instance='%i']"%(self._instance) )
        if len(storages) == 0:
            # configuration data not found, set default values
            self.setDefault()
            return      
        
        # we should have only one instance from this type
        cfg = storages[0]   
        
        # check version, has to be lower or equal than current version
        version = cfg.get("version")
        if (version == None) or (int(version) > self.xmlVersion):
            self.send_event(ModuleEvent(self._object_name, 
                                        EventType.ERROR, 
                                        "XML Configuration: wrong version"))
            return
        version = int(version)
        
        # get the values
        try:
            self.frequency_range = cfg.frequency_range.pyval
            self.chunk = cfg.chunk_size.pyval
            self.plot_items = cfg.plot_items.pyval
            self.onlinePane.setCurrentValues(self.frequency_range, self.chunk)       
        except Exception as e:
            self.send_exception(e, severity=ErrorSeverity.NOTIFY)





################################################################
# Online Configuration Pane

class _OnlineCfgPane(Qt.QFrame):
    ''' Online configuration pane
    '''
    def __init__(self , *args):
        apply(Qt.QFrame.__init__, (self,) + args)

        # make it nice ;-)
        self.setFrameShape(QtGui.QFrame.Panel)
        self.setFrameShadow(QtGui.QFrame.Raised)

        # give us a layout and group box
        self.gridLayout = QtGui.QGridLayout(self)
        self.groupBox = QtGui.QGroupBox(self)
        self.groupBox.setTitle("FFT")
        
        # group box layout
        self.gridLayoutGroup = QtGui.QGridLayout(self.groupBox)
        self.gridLayoutGroup.setHorizontalSpacing(10)
        self.gridLayoutGroup.setContentsMargins(20, -1, 20, -1)
        
        # add the chunk size combobox
        self.comboBoxChunk = QtGui.QComboBox(self.groupBox)
        self.comboBoxChunk.setObjectName("comboBoxChunk")
        self.comboBoxChunk.addItem(Qt.QString("128"))
        self.comboBoxChunk.addItem(Qt.QString("256"))
        self.comboBoxChunk.addItem(Qt.QString("512"))
        self.comboBoxChunk.addItem(Qt.QString("1024"))
        self.comboBoxChunk.addItem(Qt.QString("2048"))
        self.comboBoxChunk.addItem(Qt.QString("4096"))
        self.comboBoxChunk.addItem(Qt.QString("8129"))
        self.comboBoxChunk.addItem(Qt.QString("16384"))
        self.comboBoxChunk.addItem(Qt.QString("32768"))
        
        # add the frequency range combobox
        self.comboBoxFrequency = QtGui.QComboBox(self.groupBox)
        self.comboBoxFrequency.setObjectName("comboBoxChunk")
        self.comboBoxFrequency.addItem(Qt.QString("20"))
        self.comboBoxFrequency.addItem(Qt.QString("50"))
        self.comboBoxFrequency.addItem(Qt.QString("100"))
        self.comboBoxFrequency.addItem(Qt.QString("200"))
        self.comboBoxFrequency.addItem(Qt.QString("500"))
        self.comboBoxFrequency.addItem(Qt.QString("1000"))
        self.comboBoxFrequency.addItem(Qt.QString("2000"))
        self.comboBoxFrequency.addItem(Qt.QString("5000"))

        # create unit labels
        self.labelChunk = QtGui.QLabel(self.groupBox)
        self.labelChunk.setText("[n]")
        self.labelFrequency = QtGui.QLabel(self.groupBox)
        self.labelFrequency.setText("[Hz]")
        
        # add widgets to layouts
        self.gridLayoutGroup.addWidget(self.comboBoxFrequency, 0, 0, 1, 1)
        self.gridLayoutGroup.addWidget(self.labelFrequency, 0, 1, 1, 1)
        self.gridLayoutGroup.addWidget(self.comboBoxChunk, 0, 2, 1, 1)
        self.gridLayoutGroup.addWidget(self.labelChunk, 0, 3, 1, 1)
        
        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)

        # set default values
        self.comboBoxFrequency.setCurrentIndex(2)
        self.comboBoxChunk.setCurrentIndex(4)
        
    def getCurrentValues(self):
        ''' Get current selected values for frequency and chunk size
        @return: frequency and chunk size as tuple
        '''
        chunk,ok = self.comboBoxChunk.currentText().toFloat()
        frequency,ok = self.comboBoxFrequency.currentText().toFloat()
        return frequency, chunk

    def setCurrentValues(self, frequency, chunk):
        ''' Set the current values for frequency and chunk size
        @param frequency: new frequency value
        @param chunk: new chunk size
        '''
        # find chunk size index
        idx = -1
        for i in range(self.comboBoxChunk.count()):
            if chunk == self.comboBoxChunk.itemText(i).toFloat()[0]:
                idx = i
        # set new combobox index
        if idx >= 0:
            self.comboBoxChunk.setCurrentIndex(idx)
        
        # find frequency index
        idx = -1
        for i in range(self.comboBoxFrequency.count()):
            if frequency == self.comboBoxFrequency.itemText(i).toFloat()[0]:
                idx = i
        # set new combobox index
        if idx >= 0:
            self.comboBoxFrequency.setCurrentIndex(idx)
            
            

################################################################
# Signal Pane

class _SignalPane(Qt.QFrame):
    ''' FFT display pane
    '''
    def __init__(self , *args):
        apply(Qt.QFrame.__init__, (self,) + args)

        # Initialize local variables
        self.data_queue = Queue.Queue(10)       # data exchange queue
        
        # Layout display items
        self.setMinimumSize(Qt.QSize(0, 0))     # hide signal pane if there are no plot items
        self.verticalLayout = QtGui.QVBoxLayout(self) # arrange plot items vertically
        
        # list of current plot widgets
        self.plot = []

        # start 50ms display timer 
        self.startTimer(50)


    def setupDisplay(self, channels, samplerate, datapoints, frequency_range):
        ''' Rearrange and setup plot widgets
        @param channels: list of selected channels as EEG_ChannelProperties 
        @param samplerate:  sampling rate in Hz
        @param datapoints:  chunk size in samples
        @param frequency_range: show frequencies up to this value [Hz]
        ''' 
        # flush input data queue
        while not self.data_queue.empty():
            self.data_queue.get_nowait()

        # remove previous plot widgets
        for plot in self.plot[:]:
            self.verticalLayout.removeWidget(plot)
            plot.setParent(None)
            self.plot.remove(plot)
            del plot

        # create and setup requested display widgets
        pos = 0
        for channel in channels:
            plot = _FFT_Plot(self)
            self.plot.append(plot)
            plot.setupDisplay(channel.name, samplerate, datapoints, frequency_range)
            self.verticalLayout.insertWidget(pos, plot)
            pos += 1


    def timerEvent(self,e):
        ''' Display timer callback.
        Get data from input queue and distribute it to the plot widgets
        '''
        while not self.data_queue.empty():
            # get data from queue
            channel_data = self.data_queue.get_nowait()
            # distribute data to plot widgets
            for index, plot in enumerate(self.plot):
                plot.calculate(channel_data[index])


class _FFT_Plot(Qwt.QwtPlot):
    ''' FFT plot widget
    '''
    def __init__(self, *args):
        Qwt.QwtPlot.__init__(self, *args)

        self.setMinimumSize(Qt.QSize(300, 50))

        font = Qt.QFont("arial", 11)
        title = Qwt.QwtText('FFT')
        title.setFont(font)
        self.setTitle(title);
        self.setCanvasBackground(Qt.Qt.white)
        
        # grid 
        self.grid = Qwt.QwtPlotGrid()
        self.grid.enableXMin(True)
        self.grid.setMajPen(Qt.QPen(Qt.Qt.gray, 0, Qt.Qt.SolidLine));
        self.grid.attach(self)

        # axes
        font = Qt.QFont("arial", 9)
        titleX = Qwt.QwtText('Frequency [Hz]')
        titleX.setFont(font)
        titleY = Qwt.QwtText('Amplitude')
        titleY.setFont(font)
        self.setAxisTitle(Qwt.QwtPlot.xBottom, titleX);
        self.setAxisTitle(Qwt.QwtPlot.yLeft, titleY);
        self.setAxisMaxMajor(Qwt.QwtPlot.xBottom, 10);
        self.setAxisMaxMinor(Qwt.QwtPlot.xBottom, 0);
        self.setAxisMaxMajor(Qwt.QwtPlot.yLeft, 10);
        self.setAxisMaxMinor(Qwt.QwtPlot.yLeft, 0);
        self.setAxisFont(Qwt.QwtPlot.xBottom, font)
        self.setAxisFont(Qwt.QwtPlot.yLeft, font)
        self.axisWidget(Qwt.QwtPlot.yLeft).setMinBorderDist(5,10)

        # curves
        self.curve1 = Qwt.QwtPlotCurve('Trace1')
        self.curve1.setPen(Qt.QPen(Qt.Qt.blue,2))
        self.curve1.setYAxis(Qwt.QwtPlot.yLeft)
        self.curve1.attach(self)

        # set initial display values
        self.setupDisplay("channel", 500, 1024, 200) 
        

    def setupDisplay(self, channelname, samplerate, datapoints, frequency_range):
        ''' Initialize all display parameters
        @param channelname: channel name as string 
        @param samplerate:  sampling rate in Hz
        @param datapoints:  chunk size in samples
        @param frequency_range: show frequencies up to this value [Hz]
        '''
        self.samplerate = samplerate
        self.datapoints = datapoints
        self.frequency_range = frequency_range
        
        self.dt = 1.0 / samplerate
        self.df = 1.0 / (datapoints * self.dt)
        self.xValues = np.arange(0.0, samplerate, self.df)
        self.yValues = 0.0 * self.xValues
        self.setAxisScale( Qwt.QwtPlot.xBottom, 0.0, frequency_range)
        #self.setAxisScale( Qwt.QwtPlot.yLeft, 0.0, 10000.0)
        self.curve1.setData(self.xValues, self.yValues)
        self.setTitle(channelname);
        self.replot()

    def calculate(self, channel_data):
        ''' Do the FFT
        @param channel_data: raw data array of chunk size
        '''
        lenX = channel_data.shape[0]
        window = np.hanning(lenX)
        window = window / sum(window) * 2.0
        A = np.fft.fft(channel_data*window)
        B = np.abs(A) 
        self.curve1.setData(self.xValues[:lenX/2], B[:lenX/2])
        self.replot()



################################################################
# Configuration Pane
        
class _ConfigurationPane(Qt.QFrame):
    ''' FFT Module configuration pane.
    
    Tab for global configuration dialog, contains only one item: "Max. number of plot items"
    '''
    def __init__(self, module, *args):
        apply(Qt.QFrame.__init__, (self,) + args)
        
        # reference to our parent module (TUT_3)
        self.module = module
        
        # Set tab name
        self.setWindowTitle("FFT")
        
        # make it nice
        self.setFrameShape(QtGui.QFrame.StyledPanel)
        self.setFrameShadow(QtGui.QFrame.Raised)
        
        # base layout
        self.gridLayout = QtGui.QGridLayout(self)

        # item label
        self.label = QtGui.QLabel(self)
        self.label.setText("Max. number of plot items")

        # plot item combobox
        self.comboBoxItems = QtGui.QComboBox(self)
        self.comboBoxItems.setObjectName("comboBoxItems")
        # add combobox list items (1-4)
        for n in range(1,5):
            self.comboBoxItems.addItem(Qt.QString(str(n)))

        # use spacer items to align label and combox top-left
        spacerItem1 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        spacerItem2 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        
        # add all items to the layout
        self.gridLayout.addWidget(self.label, 0, 0)
        self.gridLayout.addWidget(self.comboBoxItems, 0, 1)
        self.gridLayout.addItem(spacerItem1, 1, 0, 1, 1)
        self.gridLayout.addItem(spacerItem2, 0, 2, 1, 1)

        # set initial value from parent module
        self.comboBoxItems.setCurrentIndex(self.module.plot_items-1)

        # actions
        self.connect(self.comboBoxItems, Qt.SIGNAL("currentIndexChanged(int)"),
                     self._ItemsChanged)

    def _ItemsChanged(self, index):
        ''' Event handler for changes in "number of plot items"
        '''
        self.module.plot_items = index + 1  # update the TUT_3 module parameter
        
