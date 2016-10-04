# -*- coding: utf-8 -*-
'''
Main Application

PyCorder ActiChamp Recorder

------------------------------------------------------------

Copyright (C) 2010, Brain Products GmbH, Gilching

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

B{Default Module Configuration:}

    - L{MainWindow}         
        - Instantiate module chain L{InstantiateModules}
            - Amplifier L{AMP_ActiChamp}
                - L{Configuration Pane<amplifier._ConfigurationPane>}
                - L{Online Configuration Pane<amplifier._OnlineCfgPane>}
            - Trigger Input Detection L{TRG_Eeg}
            - Data Storage (Vision Data Exchange Format) L{StorageVision}
                - L{Configuration Pane<storage._ConfigurationPane>}
                - L{Online Configuration Pane<storage._OnlineCfgPane>}
            - Remote Data Access Server L{RDA_Server} 
            - Digital Filter (Low-Cut, High-Cut and Notch) L{FLT_Eeg}
                - L{Configuration Pane<filter._ConfigurationPane>}
            - Impedance Display Dialog L{IMP_Display}
                - L{Dialog<impedance.DlgImpedance>}
            - Data Display Module L{DISP_Scope} 
                - L{Online Configuration Pane<display._OnlineCfgPane>}

B{Dependencies:}
    - Python   2.6
    - NumPy    1.3.0 or 1.4.1
    - SciPy    0.7.1 or 0.8.0
    - PyQt     4.5.4 or 4.6.3
    - PyQwt    5.2.0 
    - lxml     2.2.4 or 2.2.7

@author: Norbert Hauser
@version: 1.0
'''
from PyQt4.Qt import QString

__version__ = "1.0.9"
'''Application Version'''

# show or hide the confirmation dialog box at start up
ShowConfirmationDialog = True
ConfirmationText = u"\
The PyCorder is based on the Python programming language and is explicitly designed as open source software. \
The program is provided free of charge under the GNU General Public License (GPL) for open-source \
software by Brain Products GmbH.\n\
Because it is open-source software, the PyCorder allows users to follow all the processing steps \
in the source code. Users have the option of modifying the program code to meet their scientific requirements \
irrespective of the program version that we provide and without prior consultation with us.\n\
The PyCorder is exclusively intended for research purposes. Because it is also provided free of charge, \
Brain Products GmbH is unable to provide support for the software directly.\nIn particular, \
we can accept no liability for program functions that have been modified or created from scratch by the user.\n\
If problems should arise when using the program, you can make use of the forum that has been set up \
for this purpose. You will find the forum at http://www.actichamp.com/forum/.\n\
Use of the program demands a considerable degree of responsibility and safety awareness on the part of the user.\n\
It is possible to deactivate this information page in the source code.\n\
Please confirm that you accept the conditions of use of the program as stated here by clicking Accept."

# show or hide the battery disconnection reminder
ShowBatteryReminder = True

# force battery logging independent from the -rBL command line switch 
ForceBatteryLogging = True


import sys
import collections
import re
from optparse import OptionParser

'''
------------------------------------------------------------
LOAD LIBRARIES AND CHECK DEPENDENCIES
------------------------------------------------------------
'''
import loadlibs

# check library import
if len(loadlibs.import_log) > 0:
    print "PyCorder: The following libraries are missing or have the wrong version\r\n\r\n"
    print loadlibs.import_log
    if "missing" in loadlibs.import_log:
        raw_input("Press RETURN to close the application ..." )
        sys.exit(1)
    else:
        raw_input("Press RETURN to continue ..." )
        


'''
------------------------------------------------------------
IMPORT GUI RESOURCES
------------------------------------------------------------
'''

from res import frmMain
from res import frmMainStatusBar
from res import frmLogView
from res import frmMainConfiguration


'''
------------------------------------------------------------
IMPORT AND INSTANTIATE RECORDING MODULES
------------------------------------------------------------
'''
# import the remote control server
from remote import RemoteControlServer

# import base functionality modules
from amplifier import AMP_ActiChamp
from storage import StorageVision
from filter import FLT_Eeg
from trigger import TRG_Eeg
from impedance import IMP_Display
from display import DISP_Scope
from rda_server import RDA_Server
from rda_client import RDA_Client
from montage import MNT_Recording
from modbase import *

# import your own modules here
#from tutorial.tut_0 import TUT_0
#from tutorial.tut_1 import TUT_1
#from tutorial.tut_2 import TUT_2
#from tutorial.tut_3 import TUT_3
#from tutorial.tut_4 import TUT_4
from custom_modules.dc_offset import dc_offset

def InstantiateModules(run_as):
    ''' Instantiate and arrange module objects. 
    Modules will be connected top -> down, starting with array index 0. 
    Additional modules can be connected left -> right with tuples as list objects.
    @param run_as: command line option (-r, --runas) for different module configurations 
    @return: list with instantiated module objects 
    '''
    # get command line arguments
    if 'RC' in run_as:
        # run as remote client
        modules = [RDA_Client(),
                   TRG_Eeg(), 
                   FLT_Eeg(), 
                   IMP_Display(), 
                   DISP_Scope(instance=0)]
    else:
        # run as actiCHamp recorder
        modules = [AMP_ActiChamp(),
                   MNT_Recording(),
                   TRG_Eeg(),
                   StorageVision(), 
                   FLT_Eeg(),
                   dc_offset(),				   
                   RDA_Server(),
                   IMP_Display(), 
                   DISP_Scope(instance=0)
                   ]
    return modules

        
'''
------------------------------------------------------------
APPLICATION MAIN WINDOW
------------------------------------------------------------
'''

class MainWindow(Qt.QMainWindow, frmMain.Ui_MainWindow):
    ''' Application Main Window Class
    includes main menu, status bar and module handling 
    '''
    def __init__(self):
        ''' Instantiate and initialize GUI objects.
            - Connect to button and menu actions.
            - Instantiate and connect PyCorder module chain.
             -Load the last used module configuration.
        '''
        Qt.QMainWindow.__init__(self)
        self.setupUi(self)
        
        # create status bar
        self.statusWidget = StatusBarWidget()
        self.statusBar().addPermanentWidget(self.statusWidget, 1)
        
        # menu actions
        self.connect(self.actionQuit, Qt.SIGNAL('triggered()'),
                     Qt.SLOT('close()'))
        self.connect(self.actionShow_Log, Qt.SIGNAL('triggered()'),
                     self.statusWidget.showLogEntries)
        self.connect(self.actionLoad_Configuration, Qt.SIGNAL('triggered()'),
                     self.loadConfiguration)
        self.connect(self.actionSave_Configuration, Qt.SIGNAL('triggered()'),
                     self.saveConfiguration)
        self.connect(self.actionDefault_Configuration, Qt.SIGNAL('triggered()'),
                     self.defaultConfiguration)

        # button actions
        self.connect(self.pushButtonConfiguration, Qt.SIGNAL("clicked()"),
                     self.configurationClicked)
        self.connect(self.statusWidget, Qt.SIGNAL("saveLog()"),
                     self.saveLogFile)
        self.connect(self.statusWidget, Qt.SIGNAL("showLog()"),
                     self.showLogEntries)
        
        # preferences
        self.application_name = "PyCorder"
        self.configuration_file = ""
        self.configuration_dir = ""
        self.log_dir = ""
        self.loadPreferences()
        self.recording_mode = -1
        self.usageConfirmed = False
        
        # remote control server
        self.RC = None
        
        # parse command line options    
        # look for old style command line option "-RC"
        if "-RC" in sys.argv:
            sys.argv.remove("-RC")  # skip old style
            RemoteClient = True
        else:
            RemoteClient = False
    
        # get command line options    
        parser = OptionParser()
        parser.add_option("-m", "--modules", dest="ModuleFile",
                          help="Instantiate modules from separate module definition file MODULEFILE. "
                               "InstantiateModules() from this file will be called." )
        parser.add_option("-c", "--configfile", dest="ConfigurationFile",
                          help="Load CONFIGURATIONFILE instead of last configuration.")
        parser.add_option("-r", "--runas", dest="RunAs", default="",
                          help="Specify the module configuration that should be used.")
        parser.add_option("-o", "--options", dest="Options", default="",
                          help="General options: R - start the remote server")
        try:
            self.cmd_options, args = parser.parse_args()
        except: 
            raise Exception("Command line parser error !")
        # merge run configuration with old style
        if self.cmd_options.RunAs == "" and RemoteClient:
            self.cmd_options.RunAs = "RC"
            
        
        # create module chain (top = index 0, bottom = last index)
        self.defineModuleChain()
        
        # connect modules
        for idx_vertical in range(len(self.modules)-1):
            if type(self.modules[idx_vertical]) in (tuple, list):
                # connect top/down
                if type(self.modules[idx_vertical+1]) in (tuple, list):
                    self.modules[idx_vertical][0].add_receiver(self.modules[idx_vertical+1][0])
                else:
                    self.modules[idx_vertical][0].add_receiver(self.modules[idx_vertical+1])
                # connect left/right
                for idx_horizontal in range(len(self.modules[idx_vertical])-1):
                    self.modules[idx_vertical][idx_horizontal].add_receiver(self.modules[idx_vertical][idx_horizontal+1])
            else:
                # connect top/down
                if type(self.modules[idx_vertical+1]) in (tuple, list):
                    self.modules[idx_vertical].add_receiver(self.modules[idx_vertical+1][0])
                else:
                    self.modules[idx_vertical].add_receiver(self.modules[idx_vertical+1])

        # get the top module
        if type(self.modules[0]) in (tuple, list):
            self.topmodule = self.modules[0][0]
        else:
            self.topmodule = self.modules[0]
        
        # get the bottom module
        if type(self.modules[-1]) in (tuple, list):
            self.bottommodule = self.modules[-1][-1]
        else:
            self.bottommodule = self.modules[-1]

        # get events from module chain top module
        self.connect(self.topmodule, Qt.SIGNAL("event(PyQt_PyObject)"), self.processEvent)

        # tell the top module to get events from us
        self.topmodule.connect(self, Qt.SIGNAL("parentevent(PyQt_PyObject)"), self.topmodule.parent_event, Qt.Qt.QueuedConnection)

        # get signal panes for plot area
        self.horizontalLayout_SignalPane.removeItem(self.horizontalLayout_SignalPane.itemAt(0))
        for module in flatten(self.modules):
            pane = module.get_display_pane()
            if pane != None:
                self.horizontalLayout_SignalPane.addWidget(pane)
        

        # initial module chain update (top module)
        self.topmodule.update_receivers()

        # insert online configuration panes
        position = 0
        for module in flatten(self.modules):
            module.main_object = self
            pane = module.get_online_configuration()
            if pane != None:
                #self.verticalLayout_OnlinePane.insertWidget(self.verticalLayout_OnlinePane.count()-2, pane)
                self.verticalLayout_OnlinePane.insertWidget(position, pane)
                position += 1

        # load configuration file
        if self.cmd_options.ConfigurationFile == None:
            # try to load the last configuration file
            try:
                if len(self.configuration_file) > 0:
                    cfg = os.path.normpath(self.configuration_dir + '/' + self.configuration_file)
                    self._loadConfiguration(cfg)
                else:
                    self.defaultConfiguration()
            except:
                pass
        else:
            # try to load configuration from command line file
            try:
                self._loadConfiguration(os.path.normpath(self.cmd_options.ConfigurationFile))
            except Exception as e:
                raise Exception("Failed to load configuration from file: " +
                                self.cmd_options.ConfigurationFile + "\n" + repr(e))
            

        # update log text module info
        self.updateModuleInfo()
        
        # update button states
        self.updateUI()

        # instantiate and start the remote control server
        try:
            if "R" in self.cmd_options.Options:
                self.RC = RemoteControlServer()
        except Exception as e:
            self.RC = None
            Qt.QMessageBox.information(None, "Remote Control Server", str(e))
        if self.RC != None:
            # get events from server
            self.connect(self.RC, Qt.SIGNAL("event(PyQt_PyObject)"), self.processEvent)

        # performance boost ;-)
        self.startTimer(1)
        

        
    def defineModuleChain(self):
        ''' Instantiate and arrange module objects 
        - Modules will be connected top -> down, starting with array index 0 
        - Additional modules can be connected left -> right with tuples as list objects 
        '''
        # check the command line option
        if self.cmd_options.ModuleFile == None:
            # get modules from global function
            self.modules = InstantiateModules(self.cmd_options.RunAs)
        else:
            # get module configuration from external file
            try:
                exec("from " + self.cmd_options.ModuleFile + " import InstantiateModules")
                self.modules = InstantiateModules(self.cmd_options.RunAs)
            except Exception as e:
                raise Exception("Failed to instantiate modules from external file: " +
                                self.cmd_options.ModuleFile + "\n" + str(e))
        
        # show battery reminder only for the acticCHamp amplifier
        global ShowBatteryReminder
        classnames = [m.__class__.__name__ for m in self.modules]
        if not "AMP_ActiChamp" in classnames:
            ShowBatteryReminder = False
            
        
       
    def configurationClicked(self):
        ''' Configuration button clicked
        - Open configuration dialog and add configuration panes for each module in the
        module chain, if available
        '''
        dlg = DlgConfiguration()
        for module in flatten(self.modules):
            pane = module.get_configuration_pane()
            if pane != None:
                dlg.addPane(pane)
        ok = dlg.exec_()
        if ok:
            self.saveConfiguration()
    
    def defaultConfiguration(self):
        ''' Menu "Reset Configuration": 
        Set default values for all modules
        '''
        # reset all modules
        for module in flatten(self.modules):
            module.setDefault()

        # update module chain, starting from top module
        self.topmodule.update_receivers()

        # update status line
        self.processEvent(ModuleEvent("Application",
                                      EventType.STATUS,
                                      info = "default",
                                      status_field = "Workspace"))
        
    def _loadConfiguration(self, filename):
        ''' Load module configuration from XML file
        @param filename: Full qualified XML file name 
        '''
        ok = True
        cfg = objectify.parse(filename)
        # check application and version
        app = cfg.xpath("//PyCorder")
        if (len(app) == 0) or (app[0].get("version") == None):
            # configuration data not found
            self.processEvent(ModuleEvent("Load Configuration", EventType.ERROR,\
                                          "%s is not a valid PyCorder configuration file"%(filename),\
                                          severity=1) )
            ok = False          

        if ok:
            version = app[0].get("version")
            if cmpver(version, __version__, 2) > 0:
                # wrong version
                self.processEvent(ModuleEvent("Load Configuration", EventType.ERROR,\
                                              "%s wrong version %s > %s"%(filename, version, __version__),\
                                              severity=ErrorSeverity.NOTIFY) )
                ok = False          
        
        # setup modules from configuration file
        if ok:
            for module in flatten(self.modules):
                module.setXML(cfg)

        # update module chain, starting from top module
        self.topmodule.update_receivers()

        # update status line
        file_name, ext = os.path.splitext(os.path.split(filename)[1])            
        self.processEvent(ModuleEvent("Application",
                                      EventType.STATUS,
                                      info = file_name,
                                      status_field = "Workspace"))
        
    
    def loadConfiguration(self):
        ''' Menu "Load Configuration ...": 
        Load module configuration from XML file
        '''
        dlg = Qt.QFileDialog()
        dlg.setFileMode(Qt.QFileDialog.ExistingFile)
        dlg.setAcceptMode(Qt.QFileDialog.AcceptOpen)
        dlg.setNameFilter("Configuration files (*.xml)")
        dlg.setDefaultSuffix("xml")
        if len(self.configuration_dir) > 0:
            dlg.setDirectory(self.configuration_dir)
        dlg.selectFile(self.configuration_file)
        if dlg.exec_() == True:
            try:
                files = dlg.selectedFiles()
                file_name = unicode(files[0])
                # load configuration from XML file
                self._loadConfiguration(file_name)
                # set preferences
                dir, fn = os.path.split(file_name)            
                self.configuration_file = fn
                self.configuration_dir = dir
            except Exception as e:
                tb = GetExceptionTraceBack()[0]
                self.processEvent(ModuleEvent("Load Configuration", EventType.ERROR,\
                                              tb + " -> %s "%(file_name) + str(e), 
                                              severity=ErrorSeverity.NOTIFY))
                

    def _saveConfiguration(self, filename):
        ''' Save module configuration to XML file
        @param filename: Full qualified XML file name 
        '''
        E = objectify.E
        modules = E.modules()
        # get configuration from each connected module
        for module in flatten(self.modules):
            cfg = module.getXML()
            if cfg != None:
                modules.append(cfg)
        # build complete configuration tree
        root = E.PyCorder(modules, version=__version__)
        # write it to file
        etree.ElementTree(root).write(filename, pretty_print=True, encoding="UTF-8")
       
    def saveConfiguration(self):
        ''' Menu "Save Configuration ...": 
        Save module configuration to XML file
        '''
        dlg = Qt.QFileDialog()
        dlg.setFileMode(Qt.QFileDialog.AnyFile)
        dlg.setAcceptMode(Qt.QFileDialog.AcceptSave)
        dlg.setNameFilter("Configuration files (*.xml)")
        dlg.setDefaultSuffix("xml")
        if len(self.configuration_dir) > 0:
            dlg.setDirectory(self.configuration_dir)
        dlg.selectFile(self.configuration_file)
        if dlg.exec_() == True:
            try:
                files = dlg.selectedFiles()
                file_name = unicode(files[0])
                # save configuration to XML
                self._saveConfiguration(file_name)
                # set preferences
                dir, fn = os.path.split(file_name)            
                self.configuration_file = fn
                self.configuration_dir = dir
                # update status line
                fn, ext = os.path.splitext(os.path.split(file_name)[1])            
                self.processEvent(ModuleEvent("Application",
                                              EventType.STATUS,
                                              info = fn,
                                              status_field = "Workspace"))
            except Exception as e:
                tb = GetExceptionTraceBack()[0]
                self.processEvent(ModuleEvent("Save Configuration", EventType.ERROR,\
                                              tb + " -> %s "%(file_name) + str(e), 
                                              severity=ErrorSeverity.NOTIFY))
        
    def savePreferences(self):
        ''' Save preferences to XML file
        '''
        E = objectify.E
        preferences = E.preferences(E.config_dir(self.configuration_dir),
                                    E.config_file(self.configuration_file),
                                    E.log_dir(self.log_dir))
        root = E.PyCorder(preferences, version=__version__)
        
        # preferences will be stored to user home directory
        try:
            homedir = Qt.QDir.home()
            appdir = "." + self.application_name
            if not homedir.cd(appdir):
                homedir.mkdir(appdir)
                homedir.cd(appdir)
            filename = unicode(homedir.absoluteFilePath("preferences.xml"))
            etree.ElementTree(root).write(filename, pretty_print=True, encoding="UTF-8")
        except:
            pass
        
    def loadPreferences(self):
        ''' Load preferences from XML file
        '''
        try:
            # preferences will be stored to user home directory
            homedir = Qt.QDir.home()
            appdir = "." + self.application_name
            if not homedir.cd(appdir):
                return
            filename = unicode(homedir.absoluteFilePath("preferences.xml"))
    
            # read XML file
            cfg = objectify.parse(filename)
            # check application and version
            app = cfg.xpath("//PyCorder")
            if (len(app) == 0) or (app[0].get("version") == None):
                # configuration data not found
                return          
            # check version
            version = app[0].get("version")
            if cmpver(version, __version__, 2) > 0:
                # wrong version
                return          
    
            # update preferences
            preferences = app[0].preferences
            self.configuration_dir = preferences.config_dir.pyval
            self.configuration_file = preferences.config_file.pyval
            self.log_dir = preferences.log_dir.pyval
        except:
            pass
        
    def showLogEntries(self):
        ''' Show log entries
        '''
        self.updateModuleInfo()
        self.statusWidget.showLogEntries()
        
    def saveLogFile(self):
        ''' Write log entries to file
        '''
        dlg = Qt.QFileDialog()
        dlg.setFileMode(Qt.QFileDialog.AnyFile)
        dlg.setAcceptMode(Qt.QFileDialog.AcceptSave)
        dlg.setNameFilter("Log files (*.log)")
        dlg.setDefaultSuffix("log")
        if len(self.log_dir) > 0:
            dlg.setDirectory(self.log_dir)
        if dlg.exec_() == True:
            try:
                files = dlg.selectedFiles()
                file_name = unicode(files[0])
                # set preferences
                dir, fn = os.path.split(file_name)            
                self.log_dir = dir
                # write log entries to file
                f = open(file_name, "w")
                f.write(self.statusWidget.getLogText().encode('utf-8'))
                f.close()
            except Exception as e:
                tb = GetExceptionTraceBack()[0]
                Qt.QMessageBox.critical(None, "PyCorder", 
                                        "Failed to write log file (%s)\n"%(file_name) +
                                        tb + " -> " + str(e))
        
    def closeEvent(self, event):
        ''' Application wants to close, prevent closing if recording to file is still active
        '''
        if not self.topmodule.query("Stop"):
            event.ignore()
        else:
            self.topmodule.stop(force=True)
            self.savePreferences()
            # clean up modules
            for module in flatten(self.modules):
                module.terminate()
            # terminate remote control server
            if self.RC != None:
                self.RC.terminate()
            event.accept()
            
    def sendEvent(self, event):
        ''' Send an event to the top module event chain
        '''
        self.emit(Qt.SIGNAL('parentevent(PyQt_PyObject)'), event)

        
    def processRemoteCommand(self, cmd_string):
        ''' Process commands received from remote control
        @param cmd: the received command
        @return: log entry and error message
        '''
        error_message = ""
        log_entry = u"command received: '%s'"%(cmd_string)
        if len(cmd_string) > 0:
            # split command and value
            cmd = cmd_string[0].upper()
            if len(cmd_string) > 1:
                cmd_value = cmd_string[1:]
            else:
                cmd_value = ""
                
            # check for supported commands
            if cmd not in ["1", "2", "3", "4", "M", "I", "S", "Q", "X", "F"]:
                error_message = u"command not supported: '%s'"%(cmd_string)     

            # check the recording state and if the requested command can be applied 
            elif cmd in ["S", "I", "M", "X", "Q"] and self.topmodule.isRunning() and not self.RC.remoteRecording:
                error_message = u"recording is in progress and was not started remote: '%s'"%(cmd_string) 

            elif cmd not in ["Q", "X"] and not self.topmodule.query("RemoteStop"):
                error_message = u"recording is still in progress, stop it first with 'X': '%s'"%(cmd_string) 

            elif cmd in ["1", "2", "3", "4"] and self.topmodule.isRunning():
                error_message = u"data acquisition is still in progress, stop it first with 'X': '%s'"%(cmd_string) 
            
            elif cmd in ["4", "S", "I", "M", "X", "Q"] and not self.RC.isInitialized():
                error_message = u"some variables (1 Configuration file, 2 Experiment ID or 3 Subject ID) are not initialized: '%s'"%(cmd_string)
                
            # Initialization
            elif cmd == "1":
                self.RC.S_ConfigurationFile = cmd_value
            elif cmd == "2":
                self.RC.S_ExperimentNr = cmd_value
            elif cmd == "3":
                self.RC.S_SubjectID = cmd_value
            elif cmd == "4":
                # prepare recording
                # load configuration file
                try:
                    self._loadConfiguration(self.RC.S_ConfigurationFile)
                except:
                    error_message = u"failed to load configuration file: '%s'"%(self.RC.S_ConfigurationFile)

            # Exit
            elif cmd == "X":
                # exit, stop everything and reset all state variables
                # stop data acquisition
                self.sendEvent(ModuleEvent("RemoteControl", 
                                            EventType.COMMAND,
                                            info="Stop",
                                            cmd_value="force"))
                #self.RC.resetControlState()
                self.RC.remoteRecording = False

            # Monitoring
            elif cmd == "I":
                # start impedance mode
                self.sendEvent(ModuleEvent("RemoteControl", 
                                            EventType.COMMAND,
                                            info="StartImpedance"))
                self.RC.remoteRecording = True

            elif cmd == "M":
                # start monitoring
                self.sendEvent(ModuleEvent("RemoteControl", 
                                            EventType.COMMAND,
                                            info="StartRecording"))
                self.RC.remoteRecording = True
            
            # Recording
            elif cmd == "S":
                # start monitoring if not yet started
                if not self.topmodule.isRunning() or self.recording_mode != RecordingMode.NORMAL:
                    self.sendEvent(ModuleEvent("RemoteControl", 
                                                EventType.COMMAND,
                                                info="StartRecording"))
                # start recording
                filename = "%s_%s"%(self.RC.S_ExperimentNr, self.RC.S_SubjectID)  
                self.sendEvent(ModuleEvent("RemoteControl", 
                                            EventType.COMMAND,
                                            info="StartSaving",
                                            cmd_value=filename))
                self.RC.remoteRecording = True
                    
            elif cmd == "Q":
                # stop recording
                self.sendEvent(ModuleEvent("RemoteControl", 
                                            EventType.COMMAND,
                                            info="StopSaving"))
                
            # enable / disable feedback
            elif cmd == "F":
                self.RC.feedbackEnabled = (cmd_value == "1")

        else:
            error_message = u"invalid command (size=0)"
        
        # send feedback 
        if error_message:
            self.RC.send_feedback("%sFAILED %s"%(cmd, error_message))
        else:
            if cmd in ["S", "I", "M"]:
                self.RC.postpone_feedback(cmd)
            else:
                self.RC.send_feedback("%sOK"%(cmd))
        
        return log_entry, error_message
   
   
    def processRemoteFeedback(self, event):
        ''' Handle postponed command feedbacks
        '''
        if not self.RC:
            return
        if not self.RC.isClientConnected():
            return

        for idx, cmd in enumerate(self.RC.postponed):
            if event.type == EventType.ERROR:
                self.RC.send_feedback("%sFAILED %s"%(cmd, event.info))
                del self.RC.postponed[idx]
            elif cmd == "M":
                if event.type == EventType.STATUS and event.status_field == "Mode" and event.info == RecordingMode.NORMAL:
                    self.RC.send_feedback("%sOK"%(cmd))
                    del self.RC.postponed[idx]
            elif cmd == "I":
                if event.type == EventType.STATUS and event.status_field == "Mode" and event.info == RecordingMode.IMPEDANCE:
                    self.RC.send_feedback("%sOK"%(cmd))
                    del self.RC.postponed[idx]
            elif cmd == "S":
                if event.type == EventType.STATUS and event.status_field == "Storage" and event.info:
                    self.RC.send_feedback("%sOK %s"%(cmd, event.info))
                    del self.RC.postponed[idx]
   
       
    def processEvent(self, event):
        ''' Process events from module chain
        @param event: ModuleEvent object
        Stop acquisition on errors with a severity > 1
        '''
        # handle remote postponed feedback
        self.processRemoteFeedback(event)
        
        # process commands
        if event.type == EventType.COMMAND:
            if event.info == "RemoteCommand":
                # ignore remote commands until the usage conditions are confirmed
                if not self.usageConfirmed:
                    return
                # handle and log commands from any remote control client
                cmd_log, cmd_error = self.processRemoteCommand(event.cmd_value)
                # modify the command event for logging
                if len(cmd_error) > 0:
                    event.type = EventType.ERROR
                    event.severity = ErrorSeverity.IGNORE
                    event.info = cmd_error
                else:
                    event.type = EventType.LOGMESSAGE
                    event.info = cmd_log
            else:
                # don't log other commands
                return
        
        # recording mode changed?
        if event.type == EventType.STATUS:
            if event.status_field == "Mode":
                self.recording_mode = event.info
                self.updateUI(isRunning=(event.info >= 0))
                self.updateModuleInfo()
                
        # write battery voltage to log file
        self.writeBatteryLog(event)

        # log events and update status line
        self.statusWidget.updateEventStatus(event)

        # look for errors
        if (event.type == EventType.ERROR) and (event.severity > 1):
            self.topmodule.stop(force=True)

    def writeBatteryLog(self, event):
        ''' Write battery voltage to log file
        '''
        try:
            if self.battery_log:
                if event.type == EventType.STATUS:
                    # log battery voltage
                    if event.status_field == "Battery": 
                        t = time.clock()
                        if (t - self.battery_timer >= 59) and (self.battery_mode >= 0):
                            voltage = float(event.info.split("V")[0])
                            level = '?'
                            if event.severity == ErrorSeverity.IGNORE:
                                level = 'H'
                            elif event.severity == ErrorSeverity.NOTIFY:
                                level = 'M'
                            elif event.severity == ErrorSeverity.STOP:
                                level = 'L'
                            if "V C" in event.info:
                                level = 'C'
                            logentry = "%.2f\t%s\t%s\t%s"%(voltage, 
                                                           event.event_time.strftime("%H:%M:%S\t%d/%m/%Y"), 
                                                           self.battery_ampSN,
                                                           level)
                            if self.battery_mode != self.battery_logmode:
                                logentry += "\tStart %d at %s"%(self.battery_mode, self.battery_rate)
                                self.battery_logmode = self.battery_mode
                            logentry += "\n"
                            with open(self.battery_logfile,"a") as f:
                                f.write(logentry)
                            self.battery_timer = t
                        event.info += "\nLOG"
                    # update recording mode    
                    if event.status_field == "Mode":
                        self.battery_timer = time.clock() - 60.0
                        self.battery_mode = event.info
                        if event.info < 0:
                            self.battery_logmode = event.info
                        sn = self.statusWidget.moduleinfo.split("SN: ")
                        self.battery_ampSN = "???"
                        if len(sn) > 1:
                            sn = sn[1].split()
                            if len(sn) > 0:
                                self.battery_ampSN = sn[0]
                    # update sampling rate
                    if event.status_field == "Rate":
                        self.battery_rate = event.info

        except AttributeError:
            # enable battery log with command line option -rBL or if it is forced
            self.battery_log = (self.cmd_options.RunAs == "BL") or (ForceBatteryLogging)
            self.battery_timer = time.clock() - 60.0
            self.battery_ampSN = "???"
            self.battery_rate = "???"
            self.battery_mode = -1
            self.battery_logmode = -1
            
            # log to users home /.PyCorder directory
            logpath = os.path.join(unicode(Qt.QDir.toNativeSeparators(Qt.QDir.homePath())), "." + self.application_name)
            # create or use the auto incremented file name 
            homedir = Qt.QDir.home()
            appdir = "." + self.application_name
            if not homedir.cd(appdir):
                homedir.mkdir(appdir)
            logdir = Qt.QDir(logpath)
            if not logdir.exists():
                if self.battery_log:
                    print "Battery Log is disabled because the log directory (%s) doesn't exist"%logpath
                self.battery_log = False
            else:
                fname = "CHampBattery_"
                numbersize = 3
                numberstring = "?"
                for n in range(1, numbersize):
                    numberstring += "?"
                logdir.setNameFilters(Qt.QStringList("%s%s.log"%(fname, numberstring)))
                logdir.setFilter(Qt.QDir.Files)
                flist = logdir.entryList()
                # extract numbers
                flist.replaceInStrings(".log", "", Qt.Qt.CaseInsensitive)
                flist.replaceInStrings(fname, "", Qt.Qt.CaseInsensitive)
                numbers = []
                for f in flist:
                    num,ok = f.toInt()
                    if ok and (num < 10**numbersize):
                        numbers.append(num)
                if len(numbers) > 0:
                    # get the highest number
                    numbers.sort()
                    fnumber = numbers[-1]
                else:
                    fnumber = 0
                name = "%s%0*d.log"%(fname, numbersize, fnumber)
                logfile = os.path.join(logpath, name)
                            
                # verify that the file size is not yet exceeding 10MB
                if Qt.QFile.exists(logfile):
                    if os.path.getsize(logfile) > 10 * 2**20:
                        name = "%s%0*d.log"%(fname, numbersize, fnumber + 1)
                        logfile = os.path.join(logpath, name)
            
                self.battery_logfile = logfile

                if self.battery_log:
                    print "Battery Log to %s is enabled"%self.battery_logfile 
        except Exception as e:
            print e
            self.battery_log = False
        
        
    def updateUI(self, isRunning=False):
        ''' Update user interface to reflect the recording state
        '''
        if isRunning:
            self.pushButtonConfiguration.setEnabled(False)
            self.actionLoad_Configuration.setEnabled(False)
            self.actionSave_Configuration.setEnabled(False)
            self.actionQuit.setEnabled(False)
            self.actionDefault_Configuration.setEnabled(False)
        else:
            self.pushButtonConfiguration.setEnabled(True)
            self.actionLoad_Configuration.setEnabled(True)
            self.actionSave_Configuration.setEnabled(True)
            self.actionQuit.setEnabled(True)
            self.actionDefault_Configuration.setEnabled(True)
            self.statusWidget.resetUtilization()

    def updateModuleInfo(self):
        ''' Update the module information in the log text
        and propagate it to all connected modules as status information   
        '''
        # get module information
        self.statusWidget.moduleinfo = ""
        for module in flatten(self.modules):
            info = module.get_module_info()
            if info != None:
                self.statusWidget.moduleinfo += module._object_name + "\n"
                self.statusWidget.moduleinfo += info
        if len(self.statusWidget.moduleinfo) > 0:
            self.statusWidget.moduleinfo += "\n\n"
        
        # propagate status info to all connected modules
        moduleinfo = u"PyCorder V" + __version__ + "\n\n"
        moduleinfo += self.statusWidget.moduleinfo
        msg = ModuleEvent("PyCorder",
                          EventType.STATUS,
                          info = moduleinfo,
                          status_field="ModuleInfo")
        self.sendEvent(msg)


'''
------------------------------------------------------------
LOG ENTRY DIALOG
------------------------------------------------------------
'''

class DlgLogView(Qt.QDialog, frmLogView.Ui_frmLogView):
    ''' Show all log entries as plain text
    '''
    def __init__(self, *args):
        apply(Qt.QDialog.__init__, (self,) + args)
        self.setupUi(self)
        
    def setLogEntry(self, entry):
        self.labelView.setPlainText(entry)


'''
------------------------------------------------------------
BATTERY INFO DIALOG
------------------------------------------------------------
'''

class DlgBatteryInfo(Qt.QMessageBox):
    ''' Show disconnect info for 10s
    '''
    def __init__(self, *args):
        infoText = (u"Please disconnect actiCHamp from actiPOWER after you finished recording.\n" +
                    u"Always attach actiPOWER to the charger when not in use to prevent damaging the accumulator.")
        Qt.QMessageBox.__init__(self, Qt.QMessageBox.Information, "Disconnect Battery", infoText)
        self.startTimer(10000)
    
    def timerEvent(self, e):
        self.done(0)

        
'''
------------------------------------------------------------
MAIN CONFIGURATION DIALOG
------------------------------------------------------------
'''

class DlgConfiguration(Qt.QDialog, frmMainConfiguration.Ui_frmConfiguration):
    ''' Module main configuration dialog
    All module configuration panes will go here
    '''
    def __init__(self):
        Qt.QDialog.__init__(self)
        self.setupUi(self)
        self.panes = []
        
    def addPane(self, pane):
        ''' Insert new tab and add module configuration pane
        @param pane: module configuration pane (QFrame object)
        '''
        if pane == None:
            return
        currenttabs = len(self.panes) 
        if currenttabs > 0:
            # add new tab
            tab = Qt.QWidget()
            tab.setObjectName("tab%d"%(currenttabs+1))
            gridLayout = Qt.QGridLayout(tab)
            gridLayout.setObjectName("gridLayout%d"%(currenttabs+1))
            self.tabWidget.addTab(tab, "")
        else:
            gridLayout = self.gridLayout1
            tab = self.tab1
            
        self.panes.append(pane)
        gridLayout.addWidget(pane)
        self.tabWidget.setTabText(self.tabWidget.indexOf(tab), pane.windowTitle())
        

'''
------------------------------------------------------------
STATUS BAR
------------------------------------------------------------
'''
        
class StatusBarWidget(Qt.QWidget, frmMainStatusBar.Ui_frmStatusBar):
    ''' Main Window status bar
    '''
    def __init__(self):
        Qt.QWidget.__init__(self)
        self.setupUi(self)
        
        # info label color and click 
        self.labelInfo.setAutoFillBackground(True)
        self.labelInfo.mouseReleaseEvent = self.labelInfoClicked
        self.defaultBkColor = self.labelInfo.palette().color(self.labelInfo.backgroundRole())
        self.labelInfo.setText("Brain Products GmbH, PyCorder V" + __version__)
        self.labelStatus_4.setAutoFillBackground(True)
        
        # log entries
        self.logFifo = collections.deque(maxlen=10000)
        self.lockError = False
        self.moduleinfo = ""
        
        # number of channels and reference channel names
        self.status_channels = ""
        self.status_reference = ""
        
        # utilization progressbar fifo
        self.resetUtilization()
        
    def resetUtilization(self):
        ''' Reset utilization parameters
        '''
        self.utilizationFifo = collections.deque()
        self.utilizationUpdateCounter = 0
        self.utilizationMaxValue = 0
        self.updateUtilization(0)
        
    def updateUtilization(self, utilization):
        ''' Update the utilization progressbar
        @param utilization: percentage of utilization 
        '''
        # average utilization value
        self.utilizationFifo.append(utilization)
        if len(self.utilizationFifo) > 5:
            self.utilizationFifo.popleft()
        utilization = sum(self.utilizationFifo) / len(self.utilizationFifo)
        self.utilizationMaxValue = max(self.utilizationMaxValue, utilization)
        
        # slow down utilization display
        if self.utilizationUpdateCounter > 0:
            self.utilizationUpdateCounter -= 1
            return
        self.utilizationUpdateCounter = 5
        utilization = self.utilizationMaxValue
        self.utilizationMaxValue = 0
        
        # update progress bar
        if utilization < 100:
            self.progressBarUtilization.setValue(utilization)
        else:
            self.progressBarUtilization.setValue(100)
        self.progressBarUtilization.setFormat("%d%% Utilization"%(utilization))
        
        # modify progress bar color (<80% -> green, >=80% -> red) 
        if utilization < 80:
            self.progressBarUtilization.setStyleSheet("QProgressBar {padding: 1px; text-align: right; margin-right: 35ex;} "\
                                                      "QProgressBar::chunk {background: "\
                                                      "qlineargradient(x1: 1, y1: 0, x2: 1, y2: 0.5, stop: 1 green, stop: 0 white);"\
                                                      "margin: 0.5px}")
        else:
            self.progressBarUtilization.setStyleSheet("QProgressBar {padding: 1px; text-align: right; margin-right: 35ex;} "\
                                                      "QProgressBar::chunk {background: "\
                                                      "qlineargradient(x1: 1, y1: 0, x2: 1, y2: 0.5, stop: 1 red, stop: 0 white);"\
                                                      "margin: 0.5px}")
        
    def updateEventStatus(self, event):
        ''' Update status info field and put events into the log fifo
        @param event: ModuleEvent object
        '''
        # display dedicated status info values
        if event.type == EventType.STATUS:
            if event.status_field == "Rate":
                self.labelStatus_1.setText(event.info)
            elif event.status_field == "Channels":
                self.status_channels = event.info
                self.labelStatus_2.setText(self.status_channels + ", " + self.status_reference)
            elif event.status_field == "Reference":
                refnames = event.info
                # limit the number of displayed channel names
                if len(refnames) > 70:
                    refnames = refnames[:70].rsplit('+',1)[0] + "+ ..."
                self.status_reference = refnames
                self.labelStatus_2.setText(self.status_channels + ", " + self.status_reference)
            elif event.status_field == "Workspace":
                self.labelStatus_3.setText(event.info)
            elif event.status_field == "Battery":
                # set voltage
                self.labelStatus_4.setText(event.info)
                # severity indicates normal, critical or bad
                palette = self.labelStatus_4.palette()
                if event.severity == ErrorSeverity.NOTIFY:
                    palette.setColor(self.labelStatus_4.backgroundRole(), Qt.Qt.yellow)
                elif event.severity == ErrorSeverity.STOP:
                    palette.setColor(self.labelStatus_4.backgroundRole(), Qt.Qt.red)
                else:
                    palette.setColor(self.labelStatus_4.backgroundRole(), self.defaultBkColor)
                self.labelStatus_4.setPalette(palette)
            elif event.status_field == "Utilization":
                self.updateUtilization(event.info)
            return
        
        # lock an error display until LogView is shown
        if ((self.lockError == False) or (event.severity > 0)) and event.type != EventType.LOG:
            # update label
            self.labelInfo.setText(unicode(event))
            palette = self.labelInfo.palette()
            if event.type == EventType.ERROR:
                palette.setColor(self.labelInfo.backgroundRole(), Qt.Qt.red)
                if event.severity > 0:
                    self.lockError = True
                    palette.setColor(self.labelInfo.backgroundRole(), Qt.Qt.red)
                else:
                    palette.setColor(self.labelInfo.backgroundRole(), Qt.Qt.yellow)
            else:
                palette.setColor(self.labelInfo.backgroundRole(), self.defaultBkColor)
            self.labelInfo.setPalette(palette)
        # put events into log fifo
        if event.type != EventType.MESSAGE:
            self.logFifo.append(event)
        
    def showLogEntries(self):
        ''' Show the event log content
        ''' 
        dlg = DlgLogView()
        dlg.setLogEntry(self.getLogText())
        save = dlg.exec_()
        if save:
            self.emit(Qt.SIGNAL('saveLog()'))   
        self.resetErrorState()
    
    def getLogText(self):
        ''' Get the log entries as plain text
        '''
        txt = u"PyCorder V" + __version__ + u" Event Log\n\n"
        txt += self.moduleinfo
        for event in reversed(self.logFifo):
            txt += u"%s\t %s\n"%(event.event_time.strftime("%Y-%m-%d %H:%M:%S.%f"), str(event))
        return txt
        
        
    def labelInfoClicked(self, mouse_event):
        ''' Mouse click into info label
        Show the event log content
        ''' 
        self.emit(Qt.SIGNAL('showLog()'))   
        
        
    def resetErrorState(self):
        ''' Reset error lock and info display
        '''
        self.lockError = False
        self.labelInfo.setText("")
        palette = self.labelInfo.palette()
        palette.setColor(self.labelInfo.backgroundRole(), self.defaultBkColor)
        self.labelInfo.setPalette(palette)
        
        
'''
------------------------------------------------------------
UTILITIES
------------------------------------------------------------
'''

def flatten(lst):
    ''' Flatten a list containing lists or tuples
    '''
    for elem in lst:
        if type(elem) in (tuple, list):
            for i in flatten(elem):
                yield i
        else:
            yield elem

def cmpver(a, b, n=3):
    ''' Compare two version numbers
    @param a: version number 1
    @param b: version number 2
    @param n: number of categories to compare
    @return:  -1 if a<b, 0 if a=b, 1 if a>b
    '''
    def fixup(i):
        try:
            return int(i)
        except ValueError:
            return i
    a = map(fixup, re.findall("\d+|\w+", a))
    b = map(fixup, re.findall("\d+|\w+", b))
    return cmp(a[:n], b[:n])



def setpriority(priority=2):
    """ Set The Priority of a Windows Process.  Priority is a value between 0-5 where
        2 is normal priority.  Sets the priority of the current Python process
        and limits the process to 2 logical processors """

    try:
        import win32process
        import ctypes
        from ctypes import wintypes

        priorityclasses = [win32process.IDLE_PRIORITY_CLASS,
                           win32process.BELOW_NORMAL_PRIORITY_CLASS,
                           win32process.NORMAL_PRIORITY_CLASS,
                           win32process.ABOVE_NORMAL_PRIORITY_CLASS,
                           win32process.HIGH_PRIORITY_CLASS,
                           win32process.REALTIME_PRIORITY_CLASS]

        # prepare the kernel functions
        kernel32 = ctypes.windll.kernel32
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.GetCurrentProcess.argtypes = []
        kernel32.GetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
        kernel32.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_int]
        kernel32.SetPriorityClass.argtypes = [wintypes.HANDLE, ctypes.c_int]

        # get the process handle 
        p = kernel32.GetCurrentProcess()
        
        # set process priority
        kernel32.SetPriorityClass(p, priorityclasses[priority])

        # limit the process to the first two available processors
        pmask = ctypes.c_int()
        smask = ctypes.c_int()
        kernel32.GetProcessAffinityMask(p, ctypes.byref(pmask), ctypes.byref(smask))
        smask = smask.value
        pmask = 0
        mask = 1
        cpu = 0
        while mask < 0x8000 and cpu < 2:
            if smask & mask:
                pmask |= mask
                cpu += 1
            mask = mask << 1
        kernel32.SetProcessAffinityMask(p, pmask)
        print "INFO: Available CPUs (bit mask) 0x%04X, Python process limited to 0x%04X"%(smask, pmask)
        
    except Exception as e:
        tb = GetExceptionTraceBack()[0]
        print "INFO: the process priority can not be raised because PyWin32 is not installed or an error occurred.\n      - %s->%s"%(tb, str(e))


'''
------------------------------------------------------------
MAIN APPLICATION
------------------------------------------------------------
'''
def main(args):
    ''' Create and start up main application
    '''    
    print "Starting PyCorder, please wait ...\n"
    setpriority(priority=4)
    app = Qt.QApplication(args)
    try:
        win = None
        win = MainWindow()
        win.showMaximized()
        if ShowConfirmationDialog:
            accept = Qt.QMessageBox.warning(None, "PyCorder Disclaimer", ConfirmationText, 
                                            "Accept", "Cancel", "", 1)
            if accept == 0:
                win.usageConfirmed = True
                app.exec_()
            else:
                win.close()
        else:
            win.usageConfirmed = True
            app.exec_()
    except Exception as e:
        tb = GetExceptionTraceBack()[0]
        Qt.QMessageBox.critical(None, "PyCorder", tb + " -> " + str(e))
        if win != None:
            win.close()
    
    # show the battery disconnection reminder
    if ShowBatteryReminder and win and win.usageConfirmed:
        DlgBatteryInfo().exec_()
    
    print "PyCorder terminated\n"
        
        
if __name__ == '__main__':
    main(sys.argv)
    