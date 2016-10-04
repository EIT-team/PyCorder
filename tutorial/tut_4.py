# -*- coding: utf-8 -*-
'''
Tutorial Module 4

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
@date: $Date: 2011-04-11 11:51:56 +0200 (Mo, 11 Apr 2011) $
@version: 1.0

B{Revision:} $LastChangedRevision: 69 $
'''

from modbase import *
import frmTUT4Online

class TUT_4(ModuleBase):
    ''' Tutorial Module 4
    
    Set the trigger out port with values from the online configuration pane.
    Indicate the "My Button" state. Both, trigger out and "My Button" state are available
    only during data acquisition.
    '''
    
    def __init__(self, *args, **keys):
        ''' Constructor. 
        Initialize instance variables and instantiate GUI objects 
        '''
        # initialize the base class, give a descriptive name
        ModuleBase.__init__(self, name="Trigger Output", **keys)
        self.data = None
        self.dataavailable = False
    
        # instantiate online configuration pane
        self.online_cfg = _OnlineCfgPane(self)
        
        # connect the signal handler for trigger out settings
        self.connect(self.online_cfg, Qt.SIGNAL("valueChanged(int)"), self.sendTrigger)
        self.online_cfg.groupBox.setEnabled(False)
        
    def get_online_configuration(self):
        ''' Get the online configuration pane
        @return: a QFrame object or None if you don't need a online configuration pane
        '''
        return self.online_cfg

    def process_event(self, event):
        ''' Handle events from attached modules. 
        @param event: ModuleEvent
        '''
        # Search for "MyButton" ModuleEvents from acquisition module
        # and indicate the button state
        if (event.type == EventType.COMMAND) and (event.info == "MyButton"):
            if "pressed" == event.cmd_value:
                self.online_cfg.MyButton.setChecked(True)
                self.setButtonLED(True)
            else:
                self.online_cfg.MyButton.setChecked(False)
                self.setButtonLED(False)

    def process_start(self):
        ''' Data acquisition started.
        Enable the trigger setting group box.
        '''
        self.online_cfg.groupBox.setEnabled(True)
        self.firstblock = True
        
    def process_stop(self):
        ''' Data acquisition stopped.
        Disable the trigger setting group box.
        '''
        self.online_cfg.groupBox.setEnabled(False)
        
    def process_input(self, datablock):
        ''' Get data from previous module.
        @param datablock: EEG_DataBlock object 
        '''
        self.dataavailable = True
        self.data = datablock
        # first time initialization of trigger output
        if self.firstblock:
            self.firstblock = False
            self.sendTrigger(self.online_cfg.getCheckboxes())
            
   
    def process_output(self):
        ''' Send data out to next module.
        '''
        if not self.dataavailable:
            return None
        self.dataavailable = False
        return self.data
    
    def sendTrigger(self, triggervalue):
        ''' Signal from online configuration pane, 
        if the trigger output value has changed.
        @param triggervalue: binary trigger out value (Bit0=D0, Bit1=D1 ...)
        '''
        # send new trigger output value to acquisition module
        self.send_event(ModuleEvent(self._object_name, 
                                    EventType.COMMAND,
                                    info = "TriggerOut",
                                    cmd_value=triggervalue
                                    ))
        
    def setButtonLED(self, on):
        ''' Switch MyButton LED on/off
        @param on: on=True, off=False
        '''
        period = 300    # let it blink at a rate of 300ms
        duty = 50       # with a 50% duty cycle
        if not on:
            duty = 0    # switch it off
        
        # send LED command to acquisition module
        self.send_event(ModuleEvent(self._object_name, 
                                    EventType.COMMAND,
                                    info = "SetLED",
                                    cmd_value = (period, duty)
                                    ))
    

################################################################
# Online Configuration Pane

class _OnlineCfgPane(Qt.QFrame, frmTUT4Online.Ui_frmTUT4Online):
    ''' TUT_4 Module online configuration pane
    '''
    def __init__(self, module, *args):
        # initialize designer generated user interface
        apply(Qt.QFrame.__init__, (self,) + args)
        self.setupUi(self)
        
        self.module = module
        self.triggervalue = 0
        
        # connect the event handlers
        self.connect(self.checkBox0, Qt.SIGNAL("clicked()"), self.valueChanged)
        self.connect(self.checkBox1, Qt.SIGNAL("clicked()"), self.valueChanged)
        self.connect(self.checkBox2, Qt.SIGNAL("clicked()"), self.valueChanged)
        self.connect(self.checkBox3, Qt.SIGNAL("clicked()"), self.valueChanged)
        self.connect(self.checkBox4, Qt.SIGNAL("clicked()"), self.valueChanged)
        self.connect(self.checkBox5, Qt.SIGNAL("clicked()"), self.valueChanged)
        self.connect(self.checkBox6, Qt.SIGNAL("clicked()"), self.valueChanged)
        self.connect(self.checkBox7, Qt.SIGNAL("clicked()"), self.valueChanged)
        self.connect(self.pushButton_ResetAll, Qt.SIGNAL("clicked()"), self.resetAll)
        self.connect(self.pushButton_SetAll, Qt.SIGNAL("clicked()"), self.setAll)
        self.connect(self.MyButton, Qt.SIGNAL("clicked(bool)"), self.myButton)
        
    def myButton(self, checked):
        ''' MyButton signal handler.
        Don't check it manually
        '''
        self.MyButton.setChecked(not checked)
        
    def valueChanged(self):
        ''' Signal handler for value checkboxes
        '''
        # get value from checkboxes
        trigger_out = self.getCheckboxes()
        # send value to parent
        if trigger_out != self.triggervalue:
            self.triggervalue = trigger_out
            self.emit(Qt.SIGNAL('valueChanged(int)'), self.triggervalue)
        
    def resetAll(self):
        ''' "Reset All" button signal handler
        '''
        self.setCheckboxes(0)
        self.valueChanged()
    
    def setAll(self):
        ''' "Set All" button signal handler
        '''
        self.setCheckboxes(0xFF)
        self.valueChanged()
    
    def setCheckboxes(self, value):
        ''' Set checkboxes from trigger out value.
        @param value: binary trigger out value (Bit0=D0, Bit1=D1 ...)
        '''
        
        self.checkBox0.setChecked(value & 0x01)
        self.checkBox1.setChecked(value & 0x02)
        self.checkBox2.setChecked(value & 0x04)
        self.checkBox3.setChecked(value & 0x08)
        self.checkBox4.setChecked(value & 0x10)
        self.checkBox5.setChecked(value & 0x20)
        self.checkBox6.setChecked(value & 0x40)
        self.checkBox7.setChecked(value & 0x80)
        
    def getCheckboxes(self):
        ''' Get trigger out value from checkboxes.
        @return: binary trigger out value (Bit0=D0, Bit1=D1 ...)
        '''
        value = 0
        if self.checkBox0.isChecked():
            value |= 0x01
        if self.checkBox1.isChecked():
            value |= 0x02
        if self.checkBox2.isChecked():
            value |= 0x04
        if self.checkBox3.isChecked():
            value |= 0x08
        if self.checkBox4.isChecked():
            value |= 0x10
        if self.checkBox5.isChecked():
            value |= 0x20
        if self.checkBox6.isChecked():
            value |= 0x40
        if self.checkBox7.isChecked():
            value |= 0x80
        return value
            
    
    
