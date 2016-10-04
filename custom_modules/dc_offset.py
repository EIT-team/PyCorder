	# -*- coding: utf-8 -*-
'''
DC Offset Module

PyCorder ActiChamp Recorder

------------------------------------------------------------

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

@author: Thomas Dowrick
@date: $Date: 04.10.2016 $
@version: 1.0

'''

from modbase import *
from PyQt4 import QtGui
from PyQt4 import Qwt5 as Qwt
import collections

################################################################
# The module itself

class dc_offset(ModuleBase):
    ''' DC_Offset Module
    
    Calculate and display the DC offset on all EEG channels.
      
        - GUI elements
            - Create and use configuration panes
            - Create and use a DC offset signal pane
        - Data processing
            - calculate and display the DC offset
    '''

    def __init__(self, *args, **keys):
        ''' Constructor. 
        Initialize instance variables and instantiate GUI objects 
        '''
        # initialize the base class, give a descriptive name
        ModuleBase.__init__(self, name="DC_Offset", **keys)    

        
        # initialize module variables
        self.data = None                #: hold the data block we got from previous module
        self.dataavailable = False      #: data available for output to next module 
        

        self.onlinePane = _OnlineCfgPane()

        self.signalPane = _SignalPane()
		
        self.connect(self.onlinePane.btnDCOffset, 
            Qt.SIGNAL("clicked()"),
            self.toggleDCPane)
			
    def toggleDCPane(self):
        if self.signalPane.isVisible():
            self.signalPane.hide()
            

        else:
            self.signalPane.show()
            
		
    def process_input(self, datablock):
        ''' Get data from previous module.
        Because we need to exchange data between different threads we will use 
        a queue object to send data to the display thread to be thread-safe.  
        @param datablock: EEG_DataBlock object 
        '''
        self.dataavailable = True       # signal data availability
        self.data = datablock           # get a local reference
        
   
    
    def process_output(self):
        ''' Send data out to next module
        '''
        if not self.dataavailable:
            return None
        self.dataavailable = False
        return self.data
		
		
    def get_online_configuration(self):
        ''' Get the online configuration pane
        @return: a QFrame object or None if you don't need a online configuration pane
        '''
        return self.onlinePane
		
    def get_display_pane(self):
	''' Get the signal pane
	@return: a QFrame object
	'''
        return self.signalPane
    
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
        self.groupBox.setTitle("DC Offset")
        
        # group box layout
        self.gridLayoutGroup = QtGui.QGridLayout(self.groupBox)
        self.gridLayoutGroup.setHorizontalSpacing(10)
        self.gridLayoutGroup.setContentsMargins(20, -1, 20, -1)
        
        # add the chunk size combobox
        self.btnDCOffset = QtGui.QPushButton('Show DC',self.groupBox)
        self.btnDCOffset.setCheckable(True)
        self.btnDCOffset.setObjectName("btnDCOffset")

        
        # add the frequency range combobox
        self.comboBoxScale = QtGui.QComboBox(self.groupBox)
        self.comboBoxScale.setObjectName("comboBoxChunk")
        self.comboBoxScale.addItem(Qt.QString("10"))
        self.comboBoxScale.addItem(Qt.QString("100"))
        self.comboBoxScale.addItem(Qt.QString("250"))
        self.comboBoxScale.addItem(Qt.QString("500"))

        # create unit labels

        self.labelFrequency = QtGui.QLabel(self.groupBox)
        self.labelFrequency.setText("Scale [mV]")
        
        # add widgets to layouts
        self.gridLayoutGroup.addWidget(self.comboBoxScale, 0, 0, 1, 1)
        self.gridLayoutGroup.addWidget(self.labelFrequency, 0, 1, 1, 1)
        self.gridLayoutGroup.addWidget(self.btnDCOffset, 0, 2, 1, 1)
        
        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)

        # set default values
        self.comboBoxScale.setCurrentIndex(2)

        
		################################################################
# Signal Pane

class _SignalPane(Qt.QFrame):
    ''' FFT display pane
    '''
    def __init__(self , *args):
        apply(Qt.QFrame.__init__, (self,) + args)
		
		
        self.DCplot = Qwt.QwtPlot(self)
        self.setMinimumSize(Qt.QSize(200,50))
        
        self.verticalLayout = QtGui.QVBoxLayout(self)
		
        self.verticalLayout.addWidget(self.DCplot)
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
        self.DCplot.replot()

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

