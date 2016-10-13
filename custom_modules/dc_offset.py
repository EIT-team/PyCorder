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
from PyQt4 import Qt
from sqlite3.dbapi2 import paramstyle


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
        self.setDCScale()
		
        self.connect(self.onlinePane.btnDCOffset, 
            Qt.SIGNAL("clicked()"),
            self.toggleDCPane)
        
        self.connect(self.onlinePane.comboBoxScale,
					Qt.SIGNAL("currentIndexChanged(int)"),
					self.setDCScale)
			
    def toggleDCPane(self):
        if self.signalPane.isVisible():
            self.signalPane.hide()
         
        else:
            self.signalPane.show()
          
          #set the Scale of the DC offset plot
    def setDCScale(self):
		scale = self.onlinePane.getCurrentValues()
		self.signalPane.setScale(scale)
		
    def process_input(self, datablock):
        ''' Get data from previous module.
        Because we need to exchange data between different threads we will use 
        a queue object to send data to the display thread to be thread-safe.  
        @param datablock: EEG_DataBlock object 
        '''
        self.dataavailable = True       # signal data availability
        self.data = datablock           # get a local reference
        
        #Caluclate the mean dc value on each channel and update plot values
        #but only if the pane is visible
        
        if self.signalPane.isVisible():
     	    dc_offsets = np.mean(datablock.eeg_channels,1)/1000 #Convert from uV to mV
     	    chan_indices = [x + 1 for x in range(datablock.channel_properties.shape[0])]
     	    
     	    self.signalPane.DCValues.setData(chan_indices,dc_offsets)
            
            
    def process_output(self):
        ''' Send data out to next module
        '''
        if not self.dataavailable:
            return None
        self.dataavailable = False
        return self.data
		
    def process_update(self, params):
    	if params != None:
        		#Set the width of the pen for DC offset plot based on the dimensions of the window
		#and the number of channels
            num_channels = params.channel_properties.shape[0]
            frame_width = self.signalPane.width()	
		#Calculate sensible value for line width, so that bars don't overlap
            new_pen_width = 0.9*frame_width/ (2*num_channels)
            self.signalPane.setLineWidth(new_pen_width)

        return params
    
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
        self.comboBoxScale.setObjectName("comboBoxScale")
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
        self.comboBoxScale.setCurrentIndex(1)
    
    def getCurrentValues(self):
    	scale,ok = self.comboBoxScale.currentText().toFloat()
        return scale
       
		################################################################
# Signal Pane

class  _SignalPane(Qt.QFrame):
    ''' FFT display pane
    '''
    def __init__(self , *args):
        apply(Qt.QFrame.__init__, (self,) + args)
		
        self.setMinimumSize(Qt.QSize(200,50))

		#Initialise plot object and set background, labels etc
        self.DCplot = Qwt.QwtPlot(self)
        self.DCplot.setCanvasBackground(Qt.Qt.white)
		
        font = Qt.QFont("arial", 9)
        title = Qwt.QwtText('DC Offset')
        xLabel = Qwt.QwtText('Channel number')
        yLabel = Qwt.QwtText('Voltage (mV)')
        
        title.setFont(font)
        xLabel.setFont(font)
        yLabel.setFont(font)
        
        self.DCplot.setTitle(title)
        self.DCplot.setAxisTitle(Qwt.QwtPlot.xBottom,xLabel)
        self.DCplot.setAxisTitle(Qwt.QwtPlot.yLeft,yLabel)
        
        
        self.verticalLayout = QtGui.QVBoxLayout(self)
        self.verticalLayout.addWidget(self.DCplot)
        
        #Simple hack to get a bar graph by using stick plot and making the pen wider than default
        self.DCValues = Qwt.QwtPlotCurve()
        self.DCValues.setStyle(Qwt.QwtPlotCurve.Sticks)
        #Set the line width
        self.setLineWidth(5) #Set pen width to 5 - too big if lots of channels (e.g. 128) are used
        self.DCValues.attach(self.DCplot)
        
        self.grid = Qwt.QwtPlotGrid()
        self.grid.enableXMin(True)
        self.grid.setMajPen(Qt.QPen(Qt.Qt.gray, 0, Qt.Qt.SolidLine))
        self.grid.setMinPen(Qt.QPen(Qt.Qt.gray, 0, Qt.Qt.DashLine))
        self.grid.attach(self.DCplot)
        
        #Start display timer to update plot
        self.startTimer(100)
        
        #Set the y-axis scale 
    def setScale(self, scale):
        self.DCplot.setAxisScale(0,-scale,scale)
        
    def setLineWidth(self,width):
    	
        self.DCValues.setPen(Qt.QPen(Qt.Qt.red, width, Qt.Qt.SolidLine))

    def timerEvent(self,e):
        ''' Display timer callback.
        Get data from input queue and distribute it to the plot widgets
        '''
        self.DCplot.replot()
