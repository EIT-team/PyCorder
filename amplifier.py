# -*- coding: utf-8 -*-
'''
Acquisition Module

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
@version: 1.0
'''

from scipy import signal
from PyQt4 import Qt
from modbase import *
from actichamp_w import *
from res import frmActiChampOnline
from res import frmActiChampConfig
from operator import itemgetter
import textwrap
from devices.devcontainer import DeviceContainer

# enable active shielding mode
AMP_SHIELD_MODE = False

# allow multiple reference channels
AMP_MULTIPLE_REF = True

# hide the reference channel(s), works only without separate montage module 
AMP_HIDE_REF = True

# no channel selection within amplifier module, for use with an separate montage module.
AMP_MONTAGE = False

'''
------------------------------------------------------------
AMPLIFIER MODULE
------------------------------------------------------------
'''

class AMP_ActiChamp(ModuleBase):
    ''' ActiChamp EEG amplifier module 
    '''

    def __init__(self, *args, **keys):
        ''' Constructor
        '''
        ModuleBase.__init__(self, name="Amplifier", **keys)

        # XML parameter version
        # 1: initial version
        # 2: input device container added
        # 3: PLL external input 
        self.xmlVersion = 3

        # create hardware object
        self.amp = ActiChamp()      #: amplifier hardware object
        
        # set default channel configuration
        self.max_eeg_channels = 160         #: number of EEG channels for max. HW configuration
        self.max_aux_channels = 8           #: number of AUX channels for max. HW configuration
        self.channel_config = EEG_DataBlock.get_default_properties(self.max_eeg_channels, self.max_aux_channels)
        self.recording_mode = CHAMP_MODE_NORMAL

        # create dictionary of possible sampling rates
        self.sample_rates = []
        for rate in [100000.0, 50000.0, 25000.0, 10000.0, 5000.0, 2000.0, 1000.0, 500.0, 200.0]:
            base, div = self.amp.getSamplingRateBase(rate)
            if base >= 0:
                self.sample_rates.append({'rate':str(int(rate)), 'base':base, 'div':div, 'value':rate})
                
        self.sample_rate = self.sample_rates[7]
        self.binning = self.sample_rate['div']
        self.binningoffset = 0

        # set default data block
        if AMP_MONTAGE:
            self._create_channel_selection()
        else:
            self._create_all_channel_selection()
        
        # create the input device container
        self.inputDevices = DeviceContainer()
        
        # date and time of acquisition start
        self.start_time = datetime.datetime.now()
        
        # create online configuration pane
        self.online_cfg = _OnlineCfgPane(self)
        self.connect(self.online_cfg, Qt.SIGNAL("modeChanged(int)"), self._online_mode_changed)
        
        # impedance interval timer
        self.impedance_timer = time.clock()
        
        # batter check interval timer and last voltage warning string
        self.battery_timer = time.clock()
        self.voltage_warning = ""

        # skip the first received data blocks 
        self.skip_counter = 5
        self.blocking_counter = 0
        
        # reset hardware error counter and acquisition time out
        self.initialErrorCount = -1 
        self.acquisitionTimeoutCounter = 0
        self.test_counter = 0
        
    def get_online_configuration(self):
        ''' Get the online configuration pane
        '''
        return self.online_cfg

    def get_configuration_pane(self):
        ''' Get the configuration pane if available.
        Qt widgets are not reusable, so we have to create it every time
        '''
        Qt.QApplication.setOverrideCursor(Qt.Qt.WaitCursor)
        # read amplifier configuration
        self.amp.readConfiguration(self.sample_rate['base'], force=True)
        self.update_receivers()
        Qt.QApplication.restoreOverrideCursor()
        # create configuration pane
        if AMP_MONTAGE:
            config = _ConfigurationPane(self)
        else:
            config = _DeviceConfigurationPane(self)
        self.connect(config, Qt.SIGNAL("dataChanged()"), self._configuration_changed)
        self.connect(config, Qt.SIGNAL("emulationChanged(int)"), self._emulation_changed)
        self.connect(config, Qt.SIGNAL("rateChanged(int)"), self._samplerate_changed)
        return config

    def get_module_info(self):
        ''' Get information about this module for the about dialog
        @return: Serial numbers of amplifier and modules
        '''
        return self.amp.getDeviceInfoString()
    

    def _emulation_changed(self, index):
        ''' SIGNAL from configuration pane if emulation mode has changed
        '''
        try:
            self.amp.setEmulationMode(index)
        except Exception as e:
            self.send_exception(e)
        self.update_receivers()

    def _samplerate_changed(self, index):
        ''' SIGNAL from configuration pane if sample rate has changed
        '''
        Qt.QApplication.setOverrideCursor(Qt.Qt.WaitCursor)
        self.sample_rate = self.sample_rates[index]
        self.update_receivers()
        Qt.QApplication.restoreOverrideCursor()

    def _configuration_changed(self):
        ''' SIGNAL from configuration pane if values has changed
        '''
        self.update_receivers()
        
    def _online_mode_changed(self, new_mode):
        ''' SIGNAL from online configuration pane if recording mode has changed
        '''
        if self.amp.running:
            if not self.stop():
                self.online_cfg.updateUI(self.recording_mode)
                return

        if new_mode >= 0:
            Qt.QApplication.setOverrideCursor(Qt.Qt.WaitCursor)
            self.recording_mode = new_mode
            self.start()
            Qt.QApplication.restoreOverrideCursor()

    def _set_default_filter(self):
        ''' set all filter properties to HW filter values
        '''
        for channel in self.channel_config:
            channel.highpass = 0.0                  # high pass off
            channel.lowpass = 0.0                   # low pass off
            channel.notchfilter = False             # notch filter off

    def _check_reference(self):
        ''' check if selected reference channels are consistent with the global flag
        '''
        # nothing to do if multiple channels are allowed
        if AMP_MULTIPLE_REF:
            return
        # else keep the first reference channel only
        eeg_ref = np.array(map(lambda x: x.isReference, self.channel_config))
        ref_index = np.nonzero(eeg_ref)[0]     # indices of reference channel(s)
        for ch in self.channel_config[ref_index[1:]]:
            ch.isReference = False
        
        
    def setDefault(self):
        ''' Set all module parameters to default values
        '''
        emulation_mode = self.amp.getEmulationMode() > 0
        self.sample_rate = self.sample_rates[7]     # 500Hz sample rate     
        for channel in self.channel_config:
            channel.isReference = False
            if channel.group == ChannelGroup.EEG:
                channel.enable = True               # enable all EEG channels
                if (channel.input == 1) and not emulation_mode:
                    channel.isReference = True      # use first channel as reference
            else:
                channel.enable = False              # disable all AUX channels
        self._set_default_filter()
        self.inputDevices.reset()
        self.update_receivers()
                
    def stop(self, force=False):
        ''' Stop data acquisition
        @param force: force stop without query
        @return: True, if stop was accepted by attached modules
        '''
        # ask attached modules for acceptance
        if not force:
            if not self.query("Stop"):
                return False
        # stop it
        ModuleBase.stop(self)
        return True
        

    def process_event(self, event):
        ''' Handle events from attached receivers
        @param event: ModuleEvent
        '''
        # Command events
        if event.type == EventType.COMMAND:
            # check for new impedance color range values
            if event.info == "ImpColorRange":
                good, bad = event.cmd_value
                
                if self.recording_mode == CHAMP_MODE_IMPEDANCE:
                    self._thLock.acquire()
                    try:
                        self.amp.setImpedanceRange(good * 1000, bad * 1000)
                        self._thLock.release()
                    except Exception as e:
                        self._thLock.release()
                        self.send_exception(e, severity=ErrorSeverity.NOTIFY)
            
            # check for stop command
            if event.info == "Stop":
                if event.cmd_value == "force":
                    self.stop(force=True)
                else:
                    self.stop()
            
            # check for recording start command
            if event.info == "StartRecording":
                self._online_mode_changed(CHAMP_MODE_NORMAL)
            
            # check for impedance start command
            if event.info == "StartImpedance":
                self._online_mode_changed(CHAMP_MODE_IMPEDANCE)
            
            # check for trigger out command
            if event.info == "TriggerOut":
                self._thLock.acquire()
                try:
                    self.amp.setTrigger(event.cmd_value)
                    self._thLock.release()
                except Exception as e:
                    self._thLock.release()
                    self.send_exception(e, severity=ErrorSeverity.NOTIFY)

            # check for button LED command
            # cmd_value is a tuple with period and duty cycle
            if event.info == "SetLED":
                self._thLock.acquire()
                try:
                    self.amp.setButtonLed(event.cmd_value[0], event.cmd_value[1])
                    self._thLock.release()
                except Exception as e:
                    self._thLock.release()
                    self.send_exception(e, severity=ErrorSeverity.NOTIFY)
                    
            # check for acitve shield gain command
            # cmd_value is the gain from 1 to 100
            if event.info == "SetShieldGain":
                self._thLock.acquire()
                self.amp.activeShieldGain = event.cmd_value
                self._thLock.release()
                    
        # Error events
        if event.type == EventType.ERROR or event.type == EventType.LOG:
            # add device status info to "sample missing" events
            if "samples missing" in event.info:
                self._thLock.acquire()
                try:
                    errors = self.amp.getDeviceStatus()[1] - self.initialErrorCount
                    event.info += " (device errors = %d)"%errors
                    self._thLock.release()
                except Exception as e:
                    self._thLock.release()
                    event.info += " (%s)"%(str(e))
                 

    def process_start(self):
        ''' Open amplifier hardware and start data acquisition
        '''
        # reset variables
        self.eeg_data.sample_counter = 0
        self.acquisitionTimeoutCounter = 0
        self.battery_timer = 0
        self.test_counter = 0
        
        # open and setup hardware
        self.amp.open()

        # check battery
        ok,voltage = self._check_battery()
        if not ok:
            raise ModuleError(self._object_name, "battery low (%.1fV)!"%voltage)
        
        self.amp.setup(self.recording_mode, self.sample_rate['base'], self.sample_rate['div'])
        self.update_receivers()
        if len(self.channel_indices) == 0:
            raise ModuleError(self._object_name, "no input channels selected!")

        # check battery again
        ok,voltage = self._check_battery()
        if not ok:
            raise ModuleError(self._object_name, "battery low (%.1fV)!"%voltage)

        # start hardware
        self.amp.start()
        
        # set start time on first call
        self.start_time = datetime.datetime.now()

        # send status info
        if AMP_MONTAGE:
            info = "Start %s at %.0fHz with %d channels"%(CHAMP_Modes[self.recording_mode],\
                                                          self.eeg_data.sample_rate,\
                                                          len(self.channel_indices))
        else:
            if self.amp.hasPllOption() and self.amp.PllExternal:
                info = "Start %s at %.0fHz (ext. PLL)"%(CHAMP_Modes[self.recording_mode],\
                                             self.eeg_data.sample_rate)
            else:
                info = "Start %s at %.0fHz"%(CHAMP_Modes[self.recording_mode],\
                                             self.eeg_data.sample_rate)
            
        self.send_event(ModuleEvent(self._object_name, EventType.LOGMESSAGE, info))
        # send recording mode
        self.send_event(ModuleEvent(self._object_name,
                                    EventType.STATUS,
                                    info = self.recording_mode,  
                                    status_field="Mode"))
        # update button state
        self.online_cfg.updateUI(self.recording_mode)
        
        # skip the first received data blocks 
        self.skip_counter = 5
        self.blocking_counter = 0
        self.initialErrorCount = -1 
        
        
    def process_stop(self):
        ''' Stop data acquisition and close hardware object
        '''
        errors = 999
        try:
            errors = self.amp.getDeviceStatus()[1] - self.initialErrorCount   # get number of device errors
        except:
            pass
        try:
            if self.recording_mode == CHAMP_MODE_LED_TEST:
                self.amp.LedTest(0)
            self.amp.stop()
        except:
            pass
        try:
            self.amp.close()
        except:
            pass
        
        # send status info
        info = "Stop %s"%(CHAMP_Modes[self.recording_mode])
        if (errors > 0) and (self.recording_mode != CHAMP_MODE_IMPEDANCE) and (self.recording_mode != CHAMP_MODE_LED_TEST):
            info += " (device errors = %d)"%(errors)
        self.send_event(ModuleEvent(self._object_name, EventType.LOGMESSAGE, info))
        # send recording mode
        self.send_event(ModuleEvent(self._object_name,
                                    EventType.STATUS,
                                    info = -1,                  # stop
                                    status_field="Mode"))
        # update button state
        self.online_cfg.updateUI(-1)
        
               
    def _create_channel_selection(self):
        ''' Create index arrays of selected channels and prepare EEG_DataBlock 
        '''
        # get all active eeg channel indices (including reference channel)
        mask = lambda x: (x.group == ChannelGroup.EEG) and (x.enable | x.isReference) and (x.input <= self.amp.properties.CountEeg)
        eeg_map = np.array(map(mask, self.channel_config))
        self.eeg_indices = np.nonzero(eeg_map)[0]     # indices of all eeg channels

        # get all active aux channel indices
        mask = lambda x: (x.group == ChannelGroup.AUX) and x.enable and (x.input <= self.amp.properties.CountAux)
        eeg_map = np.array(map(mask, self.channel_config))
        self.aux_indices = np.nonzero(eeg_map)[0]     # indices of all aux channels
        self.property_indices = np.append(self.eeg_indices, self.aux_indices) 
        
        # adjust AUX indices to the actual available EEG channels
        self.aux_indices -= (self.max_eeg_channels - self.amp.properties.CountEeg)
        self.channel_indices = np.append(self.eeg_indices, self.aux_indices) 

        # create a new data block based on channel selection
        self.eeg_data = EEG_DataBlock(len(self.eeg_indices), len(self.aux_indices))
        self.eeg_data.channel_properties = copy.deepcopy(self.channel_config[self.property_indices])
        self.eeg_data.sample_rate = self.sample_rate['value']

        # get the reference channel indices
        #mask = lambda x: (x.group == ChannelGroup.EEG) and x.isReference and (x.input <= self.amp.properties.CountEeg)
        eeg_ref = np.array(map(lambda x: x.isReference, self.eeg_data.channel_properties))
        self.ref_index = np.nonzero(eeg_ref)[0]     # indices of reference channel(s)
        if len(self.ref_index) and not AMP_MULTIPLE_REF:
            # use only the first reference channel
            self.ref_index = self.ref_index[0:1]    
            idx = np.nonzero(map(lambda x: x not in self.ref_index, 
                                 range(0, len(self.eeg_indices)) 
                                 ) 
                             )[0]
            for prop in self.eeg_data.channel_properties[idx]:
                prop.isReference = False

        # append "REF" to the reference channel name and create the combined reference channel name
        refnames = []
        for prop in self.eeg_data.channel_properties[self.ref_index]:
            refnames.append(str(prop.name))
            prop.name = "REF_" + prop.name
            prop.refname = "REF"
            # global hide for all reference channels?
            if AMP_HIDE_REF:
                prop.enable = False
        if len(refnames) > 1:
            self.eeg_data.ref_channel_name = "AVG(" + "+".join(refnames) + ")"
        else:
            self.eeg_data.ref_channel_name = "".join(refnames)
        
        # remove reference channel if not in impedance mode
        self.ref_remove_index = self.ref_index
        if (self.recording_mode != CHAMP_MODE_IMPEDANCE) and len(self.ref_index):
            # set reference channel names for all other electrodes
            idx = np.nonzero(map(lambda x: x not in self.ref_index, 
                                 range(0, len(self.eeg_indices)) 
                                 ) 
                             )[0]
            for prop in self.eeg_data.channel_properties[idx]:
                prop.refname = "REF"

            '''            
            # remove single reference channel                 
            if AMP_HIDE_REF or not self.eeg_data.channel_properties[self.ref_index[0]].enable:
                self.eeg_data.channel_properties = np.delete(self.eeg_data.channel_properties, self.ref_index, 0)
                self.eeg_data.eeg_channels = np.delete(self.eeg_data.eeg_channels, self.ref_index, 0)
            '''
            # remove all disabled reference channels
            ref_dis = np.array(map(lambda x: x.isReference and not x.enable, 
                                   self.eeg_data.channel_properties))
            self.ref_remove_index = np.nonzero(ref_dis)[0]     # indices of disabled reference channels
            self.eeg_data.channel_properties = np.delete(self.eeg_data.channel_properties, self.ref_remove_index, 0)
            self.eeg_data.eeg_channels = np.delete(self.eeg_data.eeg_channels, self.ref_remove_index, 0)
        
        # prepare recording mode and anti aliasing filters
        self._prepare_mode_and_filters()


    def _create_all_channel_selection(self):
        ''' Create index arrays of all available channels and prepare EEG_DataBlock 
        '''
        # get all eeg channel indices
        mask = lambda x: (x.group == ChannelGroup.EEG) and (x.input <= self.amp.properties.CountEeg)
        eeg_map = np.array(map(mask, self.channel_config))
        self.eeg_indices = np.nonzero(eeg_map)[0]     # indices of all eeg channels

        # get all aux channel indices
        mask = lambda x: (x.group == ChannelGroup.AUX) and (x.input <= self.amp.properties.CountAux)
        eeg_map = np.array(map(mask, self.channel_config))
        self.aux_indices = np.nonzero(eeg_map)[0]     # indices of all aux channels
        self.property_indices = np.append(self.eeg_indices, self.aux_indices) 
        
        # adjust AUX indices to the actual available EEG channels
        self.aux_indices -= (self.max_eeg_channels - self.amp.properties.CountEeg)
        self.channel_indices = np.append(self.eeg_indices, self.aux_indices) 

        # create a new data block based on channel selection
        self.eeg_data = EEG_DataBlock(len(self.eeg_indices), len(self.aux_indices))
        self.eeg_data.channel_properties = copy.deepcopy(self.channel_config[self.property_indices])
        self.eeg_data.sample_rate = self.sample_rate['value']

        # reset the reference channel indices
        self.ref_index = np.array([])           # indices of reference channel(s)
        self.eeg_data.ref_channel_name = ""
        self.ref_remove_index = self.ref_index

        # prepare recording mode and anti aliasing filters
        self._prepare_mode_and_filters()




    def _prepare_mode_and_filters(self):
        # translate recording modes
        if (self.recording_mode == CHAMP_MODE_NORMAL) or (self.recording_mode == CHAMP_MODE_ACTIVE_SHIELD):
            self.eeg_data.recording_mode = RecordingMode.NORMAL
        elif self.recording_mode == CHAMP_MODE_IMPEDANCE:
            self.eeg_data.recording_mode = RecordingMode.IMPEDANCE
        elif self.recording_mode == CHAMP_MODE_TEST:
            self.eeg_data.recording_mode = RecordingMode.TEST

        # down sampling
        self.binning = self.sample_rate['div']
        self.binningoffset = 0

        # design anti-aliasing filter for down sampling
        # it's an Nth order lowpass Butterworth filter from scipy 
        # signal.filter_design.butter(N, Wn, btype='low')
        # N = filter order, Wn = cut-off frequency / nyquist frequency
        # f_nyquist = f_in / 2
        # f_cutoff = f_in / rate_divider * filter_factor
        # Wn = f_cutoff / f_nyquist = f_in / rate_divider * filter_factor / f_in * 2
        # Wn = 1 / rate_divider * 2 * filter_factor
        filter_order = 4
        filter_factor = 0.333
        rate_divider = self.binning
        Wn = 1.0 / rate_divider * 2.0 * filter_factor
        self.aliasing_b,self.aliasing_a = signal.filter_design.butter(filter_order, Wn, btype='low') 
        zi = signal.lfiltic(self.aliasing_b, self.aliasing_a, (0.0,))
        self.aliasing_zi = np.resize(zi, (len(self.channel_indices),len(zi)))

        # define which channels contains which impedance values
        self.eeg_data.eeg_channels[:,:] = 0
        if self.eeg_data.recording_mode == RecordingMode.IMPEDANCE:
            self.eeg_data.eeg_channels[self.eeg_indices,ImpedanceIndex.DATA] = 1
            self.eeg_data.eeg_channels[self.eeg_indices,ImpedanceIndex.GND] = 1


    def _check_battery(self):
        ''' Check amplifier battery voltages
        @return: state (ok=True, bad=False) and voltage
        '''
        # read battery state and internal voltages from amplifier
        state, voltages, faultyVoltages = self.amp.getBatteryVoltage()
        severe = ErrorSeverity.IGNORE
        if state == 1:
            severe = ErrorSeverity.NOTIFY
        elif state == 2:
            severe = ErrorSeverity.STOP
        
        # create and send faulty voltages warning message 
        v_warning = ""
        if len(faultyVoltages) > 0:
            severe = ErrorSeverity.NOTIFY
            v_warning = "Faulty internal voltage(s): "
            for u in faultyVoltages:
                v_warning += " %s"%(u)
            # warning already sent?
            if v_warning != self.voltage_warning:
                self.send_event(ModuleEvent(self._object_name, 
                                            EventType.ERROR, 
                                            info = v_warning,
                                            severity = severe))
        self.voltage_warning = v_warning
        
        # create and send status message
        voltage_info = "%.2fV"%(voltages.VDC) # battery voltage
        for u in faultyVoltages:
            voltage_info += "\n%s"%(u)
        self.send_event(ModuleEvent(self._object_name,
                                    EventType.STATUS,
                                    info = voltage_info,
                                    severity = severe,
                                    status_field="Battery"))
        return state < 2, voltages.VDC
        
    def process_update(self, params):
        ''' Prepare channel properties and propagate update to all connected receivers
        '''
        # update device sampling rate and get new configuration
        try:
            self.amp.readConfiguration(self.sample_rate['base'])
        except Exception as e:
            self.send_exception(e)
        # indicate amplifier simulation
        if self.amp.getEmulationMode() > 0:
            self.online_cfg.groupBoxMode.setTitle("Amplifier SIMULATION")
        else:
            self.online_cfg.groupBoxMode.setTitle("Amplifier")

        # create channel selection maps
        if AMP_MONTAGE:
            self._create_channel_selection()
            self.send_event(ModuleEvent(self._object_name,
                                        EventType.STATUS,
                                        info = "%d ch"%(len(self.channel_indices)),
                                        status_field="Channels"))
        else:
            self._create_all_channel_selection()
            try:
                self.inputDevices.process_update(self.eeg_data)
            except Exception as e:
                self.send_exception(e)
        
        # send current status as event
        self.send_event(ModuleEvent(self._object_name, 
                                    EventType.STATUS,
                                    info = "%.0f Hz"%(self.eeg_data.sample_rate),
                                    status_field = "Rate"))
        return copy.copy(self.eeg_data)
        
    def process_impedance(self):
        ''' Get the impedance values from amplifier
        and return the eeg data block
        '''
        # send values only once per second
        t = time.clock()
        if (t - self.impedance_timer) < 1.0:
            return None
        self.impedance_timer = t
        
        # get impedance values from device
        #imp = (np.arange(len(self.channel_indices))+1)*1000.0    # TODO: for testing only
        imp, disconnected = self.amp.readImpedances()
        # check data rate mismatch messages
        ''' suppress warning because it has no influence on the impedance measurement 
        if disconnected == CHAMP_ERR_MONITORING:
            self.send_event(ModuleEvent(self._object_name, 
                                        EventType.ERROR, 
                                        info = "USB data rate mismatch",
                                        severity = ErrorSeverity.NOTIFY))
        '''
        if imp == None:
            return None

        eeg_imp = imp[self.eeg_indices]
        gnd_imp = imp[-1]
        self.eeg_data.impedances = eeg_imp.tolist()
        self.eeg_data.impedances.append(gnd_imp)
        
        # invalidate the old impedance data list
        self.eeg_data.impedances = []
        
        # copy impedance values to data array
        self.eeg_data.eeg_channels = np.zeros((len(self.channel_indices), 10), 'd')
        self.eeg_data.eeg_channels[self.eeg_indices,ImpedanceIndex.DATA] = eeg_imp
        self.eeg_data.eeg_channels[self.eeg_indices,ImpedanceIndex.GND] = gnd_imp
        
        # dummy values for trigger and sample counter
        self.eeg_data.trigger_channel = np.zeros((1, 10), np.uint32)
        self.eeg_data.sample_channel = np.zeros((1, 10), np.uint32)

        # process connected input devices
        if not AMP_MONTAGE:
            self.inputDevices.process_input(self.eeg_data)

        # set recording time
        self.eeg_data.block_time = datetime.datetime.now()
                    
        # put it into the receiver queues
        eeg = copy.copy(self.eeg_data)
        return eeg

    def process_led_test(self):
        ''' toggle LEDs on active electrodes
        and return no eeg data
        '''
        # dummy read data
        d, disconnected = self.amp.read(self.channel_indices, len(self.eeg_indices), len(self.aux_indices))

        # toggle LEDs twice per second
        t = time.clock()
        if (t - self.impedance_timer) < 0.5:
            return None
        self.impedance_timer = t
        
        # toggle all LEDs between off, green and red
        if self.test_counter % 3 == 0:
            self.amp.LedTest(0)
        elif self.test_counter % 3 == 1:
            self.amp.LedTest(11)
        else:
            self.amp.LedTest(12)
        
        self.test_counter += 1
        return None
    
    def process_output(self):
        ''' Get data from amplifier
        and return the eeg data block
        '''
        t = time.clock()
        self.eeg_data.performance_timer = 0
        self.eeg_data.performance_timer_max = 0
        self.recordtime = 0.0

        # check battery voltage every 5s
        if (t - self.battery_timer) > 5.0 or self.battery_timer == 0:
            ok,voltage = self._check_battery()
            if not ok:
                raise ModuleError(self._object_name, "battery low (%.1fV)!"%voltage)
            self.battery_timer = t

        if self.recording_mode == CHAMP_MODE_IMPEDANCE:
            return self.process_impedance()

        if self.recording_mode == CHAMP_MODE_LED_TEST:
            return self.process_led_test()

        if self.amp.BlockingMode:
            self._thLock.release()
            try:
                d, disconnected = self.amp.read(self.channel_indices, 
                                                len(self.eeg_indices), len(self.aux_indices))
            finally:
                self._thLock.acquire()
            self.output_timer = time.clock()
        else:
            d, disconnected = self.amp.read(self.channel_indices, 
                                            len(self.eeg_indices), len(self.aux_indices))
        
        if d == None:
            self.acquisitionTimeoutCounter += 1
            # about 5s timeout
            if self.acquisitionTimeoutCounter > 100:
                self.acquisitionTimeoutCounter = 0
                raise ModuleError(self._object_name, "connection to hardware is broken!")
            # check data rate mismatch messages
            if disconnected == CHAMP_ERR_MONITORING:
                self.send_event(ModuleEvent(self._object_name, 
                                            EventType.ERROR, 
                                            info = "USB data rate mismatch",
                                            severity = ErrorSeverity.NOTIFY))
            return None
        else:
            self.acquisitionTimeoutCounter = 0
            

        # skip the first received data blocks 
        if self.skip_counter > 0:
            self.skip_counter -= 1
            return None
        # get the initial error counter
        if self.initialErrorCount < 0:
            self.initialErrorCount = self.amp.getDeviceStatus()[1]
            

        # down sample required?
        if self.binning > 1:
            # anti-aliasing filter
            filtered ,self.aliasing_zi = \
                signal.lfilter(self.aliasing_b, self.aliasing_a, d[0], zi=self.aliasing_zi) 
            # reduce reslution to avoid limit cycle
            # self.aliasing_zi = np.asfarray(self.aliasing_zi, np.float32) 

            self.eeg_data.eeg_channels = filtered[:, self.binningoffset::self.binning]
            self.eeg_data.trigger_channel = np.bitwise_or.reduce(d[1][:].reshape(-1, self.binning), axis=1).reshape(1,-1)
            self.eeg_data.sample_channel = d[2][:, self.binningoffset::self.binning] / self.binning
            self.eeg_data.sample_counter += self.eeg_data.sample_channel.shape[1]
        else:
            self.eeg_data.eeg_channels = d[0]
            self.eeg_data.trigger_channel = d[1]
            self.eeg_data.sample_channel = d[2]
            self.eeg_data.sample_counter += self.eeg_data.sample_channel.shape[1]

        # average, subtract and remove the reference channels
        if len(self.ref_index):
            '''
            # subtract
            for ref_channel in self.eeg_data.eeg_channels[self.ref_index]:
                self.eeg_data.eeg_channels[:len(self.eeg_indices)] -= ref_channel
                # restore reference channel
                self.eeg_data.eeg_channels[self.ref_index[0]] = ref_channel
                
            # remove single reference channel if not enabled
            if not (len(self.eeg_data.channel_properties) > self.ref_index[0] and
                    self.eeg_data.channel_properties[self.ref_index[0]].isReference ):
                self.eeg_data.eeg_channels = np.delete(self.eeg_data.eeg_channels, self.ref_index, 0)
            '''
            # average reference channels
            reference = np.mean(self.eeg_data.eeg_channels[self.ref_index], 0)

            # subtract reference
            self.eeg_data.eeg_channels[:len(self.eeg_indices)] -= reference

            # remove all disabled reference channels
            if len(self.ref_remove_index) > 0:
                self.eeg_data.eeg_channels = np.delete(self.eeg_data.eeg_channels, self.ref_remove_index, 0)
            
                
        # calculate date and time for the first sample of this block in s
        sampletime = self.eeg_data.sample_channel[0][0] / self.eeg_data.sample_rate
        self.eeg_data.block_time = self.start_time + datetime.timedelta(seconds=sampletime)

        # process connected input devices
        if not AMP_MONTAGE:
            self.inputDevices.process_input(self.eeg_data)

        # put it into the receiver queues
        eeg = copy.copy(self.eeg_data)

        self.recordtime = time.clock() - t

        return eeg
    
    def process_idle(self):
        ''' Check if record time exceeds 200ms over a period of 10 blocks
        and adjust idle time to record time
        '''
        if self.recordtime > 0.2:
            self.blocking_counter += 1
            # drop blocks if exceeded
            if self.blocking_counter > 10:
                self.skip_counter = 10
                self.blocking_counter = 0
        else:
            self.blocking_counter = 0
        
        # adjust idle time to record time
        idletime = max(0.06-self.recordtime, 0.02)

        if self.amp.BlockingMode:
            time.sleep(0.001)
        else:
            time.sleep(idletime)    # suspend the worker thread for 60ms
        
    def getXML(self):
        ''' Get module properties for XML configuration file
        @return: objectify XML element::
            <ActiChamp instance="0" version="1" module="amplifier">
                <channels>
                    ...
                </channels>
                <samplerate>1000</samplerate>
            </ActiChamp>
        '''
        E = objectify.E
        
        channels = E.channels()
        if AMP_MONTAGE:
            for channel in self.channel_config:
                channels.append(channel.getXML())

        # input device container
        devices = E.InputDeviceContainer(self.inputDevices.getXML())
            
        amplifier = E.AMP_ActiChamp(E.samplerate(self.sample_rate['value']),
                                    E.pllexternal(self.amp.PllExternal),
                                    channels, 
                                    devices,
                                    version=str(self.xmlVersion),
                                    instance=str(self._instance),
                                    module="amplifier")
        return amplifier
        
        
    def setXML(self, xml):
        ''' Set module properties from XML configuration file
        @param xml: complete objectify XML configuration tree, 
        module will search for matching values
        '''
        # set default values in case we get no configuration data
        self.inputDevices.reset()

        # search my configuration data
        amps = xml.xpath("//AMP_ActiChamp[@module='amplifier' and @instance='%i']"%(self._instance) )
        if len(amps) == 0:
            return      # configuration data not found, leave everything unchanged
        
        cfg = amps[0]   # we should have only one amplifier instance from this type
        
        # check version, has to be lower or equal than current version
        version = cfg.get("version")
        if (version == None) or (int(version) > self.xmlVersion):
            self.send_event(ModuleEvent(self._object_name, EventType.ERROR, "XML Configuration: wrong version"))
            return
        version = int(version)

        # get the values
        try:
            # setup channel configuration from xml
            for idx, channel in enumerate(cfg.channels.iterchildren()):
                self.channel_config[idx].setXML(channel)
            # reset filter properties to default values (because configuration has been moved to filter module)
            self._set_default_filter()
            # validate reference channel selection
            self._check_reference()
            # set closest matching sample rate
            sr = cfg.samplerate.pyval
            for rate in sorted(self.sample_rates, key=itemgetter('value')):
                if rate["value"] >= sr:
                    self.sample_rate = rate
                    break
            if version >= 2:
                # setup the input device configuration
                self.inputDevices.setXML(cfg.InputDeviceContainer)
            else:
                self.inputDevices.reset()
            if version >= 3:
                self.amp.PllExternal = cfg.pllexternal.pyval
            else:
                self.amp.PllExternal = 0
                
        except Exception as e:
            self.send_exception(e, severity=ErrorSeverity.NOTIFY)
            



'''
------------------------------------------------------------
AMPLIFIER MODULE ONLINE GUI
------------------------------------------------------------
'''

class _OnlineCfgPane(Qt.QFrame, frmActiChampOnline.Ui_frmActiChampOnline):
    ''' ActiChamp online configuration pane
    '''
    def __init__(self, amp, *args):
        ''' Constructor
        @param amp: parent module object
        '''
        apply(Qt.QFrame.__init__, (self,) + args)
        self.setupUi(self)
        self.amp = amp
       
        # set default values
        self.pushButtonStop.setChecked(True)

        # re-assign the shielding button 
        if not AMP_SHIELD_MODE:
            self.pushButtonStartShielding.setText("Electrode LED\nTest")
            
        # actions
        self.connect(self.pushButtonStartDefault, Qt.SIGNAL("clicked(bool)"), self._button_toggle)
        self.connect(self.pushButtonStartImpedance, Qt.SIGNAL("clicked(bool)"), self._button_toggle)
        self.connect(self.pushButtonStartShielding, Qt.SIGNAL("clicked(bool)"), self._button_toggle)
        self.connect(self.pushButtonStartTest, Qt.SIGNAL("clicked(bool)"), self._button_toggle)
        self.connect(self.pushButtonStop, Qt.SIGNAL("clicked(bool)"), self._button_toggle)
    
    def _button_toggle(self, checked):
        ''' SIGNAL if one of the push buttons is clicked
        '''
        if checked:
            mode = -1 #stop
            if self.pushButtonStartDefault.isChecked():
                mode = CHAMP_MODE_NORMAL
            elif self.pushButtonStartShielding.isChecked():
                if AMP_SHIELD_MODE:  
                    mode = CHAMP_MODE_ACTIVE_SHIELD
                else:
                    mode = CHAMP_MODE_LED_TEST
            elif self.pushButtonStartImpedance.isChecked(): 
                mode = CHAMP_MODE_IMPEDANCE
            elif self.pushButtonStartTest.isChecked():
                mode = CHAMP_MODE_TEST
            self.emit(Qt.SIGNAL('modeChanged(int)'), mode)
            
    def updateUI(self, mode):
        ''' Update user interface according to recording mode
        '''
        if mode == CHAMP_MODE_NORMAL:
            self.pushButtonStartDefault.setChecked(True)
        elif mode == CHAMP_MODE_ACTIVE_SHIELD or mode == CHAMP_MODE_LED_TEST:
            self.pushButtonStartShielding.setChecked(True)
        elif mode == CHAMP_MODE_IMPEDANCE:
            self.pushButtonStartImpedance.setChecked(True)
        elif mode == CHAMP_MODE_TEST:
            self.pushButtonStartTest.setChecked(True)
        else:
            self.pushButtonStop.setChecked(True)


'''
-----------------------------------------------------------------
AMPLIFIER MODULE CONFIGURATION GUI (with input device selection)
-----------------------------------------------------------------
'''

class _DeviceConfigurationPane(Qt.QFrame):
    ''' ActiChamp configuration pane
    '''
    def __init__(self, amplifier, *args):
        apply(Qt.QFrame.__init__, (self,) + args)
        
        # reference to our parent module
        self.amplifier = amplifier
        
        # Set tab name
        self.setWindowTitle("Amplifier")
        
        # make it nice
        self.setFrameShape(Qt.QFrame.StyledPanel)
        self.setFrameShadow(Qt.QFrame.Raised)
        
        # base layout
        self.gridLayout = Qt.QGridLayout(self)

        # spacers
        self.vspacer_1 = Qt.QSpacerItem(20, 40, Qt.QSizePolicy.Minimum, Qt.QSizePolicy.Expanding)
        self.vspacer_2 = Qt.QSpacerItem(20, 40, Qt.QSizePolicy.Minimum, Qt.QSizePolicy.Expanding)
        self.vspacer_3 = Qt.QSpacerItem(20, 40, Qt.QSizePolicy.Minimum, Qt.QSizePolicy.Expanding)
        self.hspacer_1 = Qt.QSpacerItem(20, 40, Qt.QSizePolicy.Expanding, Qt.QSizePolicy.Minimum)

        # create the amplifier GUI elements
        self.comboBoxSampleRate = Qt.QComboBox()
        self.comboBoxEmulation = Qt.QComboBox()
        self.label_Simulated = Qt.QLabel()
        
        self.labelPLL = Qt.QLabel("PLL Input")
        self.radioPllInternal = Qt.QRadioButton("Internal")
        self.radioPllExternal = Qt.QRadioButton("External")
        
        self.label_AvailableChannels = Qt.QLabel("Available channels: 32 EEG and 5 AUX")
        self.label_AvailableChannels.setSizePolicy(Qt.QSizePolicy.Expanding, Qt.QSizePolicy.Minimum)
        #self.label_AvailableChannels.setIndent(20)
        font = Qt.QFont("Ms Shell Dlg 2", 10)
        self.label_AvailableChannels.setFont(font)
        
        self.label_1 = Qt.QLabel("Sampling Rate")
        self.label_2 = Qt.QLabel("[Hz]")
        self.label_3 = Qt.QLabel("Simulation")
        self.label_4 = Qt.QLabel("Module(s)")
        
        # group amplifier elements
        self.groupAmplifier = Qt.QGroupBox("Amplifier Configuration")
        
        self.gridLayoutAmp = Qt.QGridLayout()
        self.gridLayoutAmp.addWidget(self.label_1, 0, 0)
        self.gridLayoutAmp.addWidget(self.comboBoxSampleRate, 0, 1)
        self.gridLayoutAmp.addWidget(self.label_2, 0, 2)
        self.gridLayoutAmp.addWidget(self.label_3, 1, 0)
        self.gridLayoutAmp.addWidget(self.comboBoxEmulation, 1, 1)
        self.gridLayoutAmp.addWidget(self.label_4, 1, 2)
        self.gridLayoutAmp.addWidget(self.label_Simulated, 2, 1, 1, 2)
        
        self.gridLayoutAmp.addWidget(self.labelPLL, 3, 0)
        self.gridLayoutAmp.addWidget(self.radioPllInternal, 3, 1)
        self.gridLayoutAmp.addWidget(self.radioPllExternal, 4, 1)
        self.gridLayoutAmp.addItem(self.vspacer_1, 5, 0, 1, 3)

        self.gridLayoutAmpGroup = Qt.QGridLayout()
        self.gridLayoutAmpGroup.addLayout(self.gridLayoutAmp, 0, 0, 2, 1)
        self.gridLayoutAmpGroup.addItem(self.hspacer_1, 0, 1)
        self.gridLayoutAmpGroup.addWidget(self.label_AvailableChannels, 0, 2)
        self.gridLayoutAmpGroup.addItem(self.vspacer_2, 1, 1)

        self.groupAmplifier.setLayout(self.gridLayoutAmpGroup)

        # get the device configuration widget
        self.device_cfg = self.amplifier.inputDevices.get_configuration_widget()

        # group device elements
        self.groupDevices = Qt.QGroupBox("Optional Input Devices")
        self.gridLayoutDeviceGroup = Qt.QGridLayout()
        self.gridLayoutDeviceGroup.addWidget(self.device_cfg, 0, 0)
        self.groupDevices.setLayout(self.gridLayoutDeviceGroup)
        
        # add all items to the main layout
        self.gridLayout.addWidget(self.groupAmplifier, 0, 0)
        self.gridLayout.addWidget(self.groupDevices, 1, 0)
        
        # actions
        self.connect(self.comboBoxSampleRate, Qt.SIGNAL("currentIndexChanged(int)"), self._samplerate_changed)
        self.connect(self.comboBoxEmulation, Qt.SIGNAL("currentIndexChanged(int)"), self._emulationChanged)
        self.connect(self.amplifier.inputDevices, Qt.SIGNAL("dataChanged()"), self._configurationDataChanged)

        # emulation combobox
        self.comboBoxEmulation.addItems(["off", "1", "2", "3", "4", "5"])
        self.comboBoxEmulation.setCurrentIndex(self.amplifier.amp.getEmulationMode())

        # sample rate combobox
        sr_index = -1
        for sr in self.amplifier.sample_rates:
            self.comboBoxSampleRate.addItem(sr['rate'])
            if sr == self.amplifier.sample_rate:
                sr_index = self.comboBoxSampleRate.count()-1
        self.comboBoxSampleRate.setCurrentIndex(sr_index)
        
        # available channels display
        self._updateAvailableChannels()
        
        # PLL configuration
        self.radioPllExternal.setChecked(self.amplifier.amp.PllExternal != 0)
        self.radioPllInternal.setChecked(self.amplifier.amp.PllExternal == 0)
        self.showPllParams(self.amplifier.amp.hasPllOption())
        self.connect(self.radioPllExternal, Qt.SIGNAL("toggled(bool)"), self._pllExternalToggled)

    def _samplerate_changed(self, index):
        ''' SIGNAL sample rate combobox value has changed
        '''
        if index >= 0:
            # notify parent about changes
            self.emit(Qt.SIGNAL('rateChanged(int)'), index)
            self._updateAvailableChannels()

    def _emulationChanged(self, index):
        ''' SIGNAL emulation mode combobox value has changed
        '''
        if index >= 0:
            # notify parent about changes
            self.emit(Qt.SIGNAL('emulationChanged(int)'),index)
            # simulated channels
            if index > 0:
                self.label_Simulated.setText("simulating %i + 8 channels"%(index * 32))
            else:
                self.label_Simulated.setText("")
            self._updateAvailableChannels()

    def _configurationDataChanged(self):
        self.emit(Qt.SIGNAL('dataChanged()'))
        
    def _updateAvailableChannels(self):
        eeg = self.amplifier.amp.properties.CountEeg
        aux = self.amplifier.amp.properties.CountAux
        if self.amplifier.amp.getEmulationMode() == 0:
            amp = "actiCHamp"
        else:
            amp = "Simulation"
        self.label_AvailableChannels.setText("Amplifier: %s\n\nAvailable channels: %d EEG and %d AUX"%(amp, eeg, aux))


    def showEvent(self, event):
        pass
    
    def showPllParams(self, show):
        self.labelPLL.setVisible(show)
        self.radioPllExternal.setVisible(show)
        self.radioPllInternal.setVisible(show)
        
    def _pllExternalToggled(self, checked):
        if checked:
            self.amplifier.amp.PllExternal = 1
        else:
            self.amplifier.amp.PllExternal = 0




'''
------------------------------------------------------------
AMPLIFIER MODULE CONFIGURATION GUI (with channel selection)
------------------------------------------------------------
'''

class _ConfigurationPane(Qt.QFrame, frmActiChampConfig.Ui_frmActiChampConfig):
    ''' ActiChamp configuration pane
    '''
    def __init__(self, amplifier, *args):
        ''' Constructor
        @param amplifier: parent module object
        '''
        apply(Qt.QFrame.__init__, (self,) + args)
        self.setupUi(self)
        self.tableViewChannels.horizontalHeader().setResizeMode(Qt.QHeaderView.ResizeToContents)
        self.tableViewAux.horizontalHeader().setResizeMode(Qt.QHeaderView.ResizeToContents)
        
        # setup content
        self.amplifier = amplifier

        # emulation combobox
        self.comboBoxEmulation.setCurrentIndex(self.amplifier.amp.getEmulationMode())

        # channel tables
        self._fillChannelTables()
        
        # sample rate combobox
        sr_index = -1
        for sr in self.amplifier.sample_rates:
            self.comboBoxSampleRate.addItem(sr['rate'])
            if sr == self.amplifier.sample_rate:
                sr_index = self.comboBoxSampleRate.count()-1
        self.comboBoxSampleRate.setCurrentIndex(sr_index)
        
        # reference channel display
        self.show_reference()
        
        # actions
        self.connect(self.comboBoxSampleRate, Qt.SIGNAL("currentIndexChanged(int)"), self._samplerate_changed)
        self.connect(self.tableViewAux.selectionModel(), Qt.SIGNAL("selectionChanged(QItemSelection, QItemSelection)"), self._selectionChanged)
        self.connect(self.comboBoxEmulation, Qt.SIGNAL("currentIndexChanged(int)"), self._emulationChanged)

    def _fillChannelTables(self):
        ''' Create and fill channel tables
        '''
        # EEG channel table, show available channels only
        mask = lambda x: (x.group == ChannelGroup.EEG) & (x.input <= self.amplifier.amp.properties.CountEeg)
        ch_map = np.array(map(mask, self.amplifier.channel_config))
        ch_indices = np.nonzero(ch_map)[0]     
        self.eeg_model = _ConfigTableModel(self.amplifier.channel_config[ch_indices])
        self.tableViewChannels.setModel(self.eeg_model)
        self.tableViewChannels.setItemDelegate(_ConfigItemDelegate())
        self.tableViewChannels.setEditTriggers(Qt.QAbstractItemView.AllEditTriggers)
        
        # AUX channel table, show available channels only
        mask = lambda x: (x.group == ChannelGroup.AUX) & (x.input <= self.amplifier.amp.properties.CountAux)
        #mask = lambda x: x.group == ChannelGroup.AUX
        ch_map = np.array(map(mask, self.amplifier.channel_config))
        ch_indices = np.nonzero(ch_map)[0]     
        self.aux_model = _ConfigTableModel(self.amplifier.channel_config[ch_indices])
        self.tableViewAux.setModel(self.aux_model)
        self.tableViewAux.setItemDelegate(_ConfigItemDelegate())
        self.tableViewAux.setEditTriggers(Qt.QAbstractItemView.AllEditTriggers)

        # simulated channels
        simulated_channels = self.comboBoxEmulation.currentIndex()
        if simulated_channels > 0:
            self.label_Simulated.setText("(simulating %i + 8 channels)"%(simulated_channels * 32))
        else:
            self.label_Simulated.setText("")

        # actions
        self.connect(self.eeg_model, Qt.SIGNAL("dataChanged(QModelIndex, QModelIndex)"), self._channeltable_changed)
        self.connect(self.aux_model, Qt.SIGNAL("dataChanged(QModelIndex, QModelIndex)"), self._channeltable_changed)
        
    def _channeltable_changed(self, topLeft, bottomRight):
        ''' SIGNAL data in channel table has changed
        '''
        # update reference channel display
        self.show_reference()
        # notify parent about changes
        self.emit(Qt.SIGNAL('dataChanged()'))

    def _samplerate_changed(self, index):
        ''' SIGNAL sample rate combobox value has changed
        '''
        if index >= 0:
            # notify parent about changes
            self.emit(Qt.SIGNAL('rateChanged(int)'), index)
            self._fillChannelTables()
            self.show_reference()

    def _emulationChanged(self, index):
        ''' SIGNAL emulation mode combobox value has changed
        '''
        if index >= 0:
            # notify parent about changes
            self.emit(Qt.SIGNAL('emulationChanged(int)'),index)
            self._fillChannelTables()
            self.show_reference()

    def _selectionChanged(self, selected, deselected):
        #print selected.indexes()
        pass
    
    def show_reference(self):
        ''' Display selected reference channel
        '''
        # get the selected reference channel index
        mask = lambda x: x.isReference & (x.group == ChannelGroup.EEG) & (x.input <= self.amplifier.amp.properties.CountEeg)
        ref = np.array(map(mask, self.amplifier.channel_config))
        ref_index = np.nonzero(ref)[0]
        # update display
        '''
        if len(ref_index) == 1:
            self.label_Reference.setText("Selected Reference Channel\r\nCh%d -> %s"%
                                         (self.amplifier.channel_config[ref_index[0]].input,
                                          self.amplifier.channel_config[ref_index[0]].name))
        '''
        if len(ref_index) > 0:
            labelText = "Selected Reference Channel(s)\r\n"
            chText = []
            for idx in ref_index[:10]:
                chText.append(u"%s"%(self.amplifier.channel_config[idx].name))
            if len(ref_index) > 10:
                chText.append("...")
            labelText += textwrap.fill(" + ".join(chText), 30)
            self.label_Reference.setText(labelText)
        else:
            self.label_Reference.setText("Selected Reference Channel\r\nNone")
           
           


            

class _ConfigTableModel(Qt.QAbstractTableModel):
    ''' EEG and AUX table data model for the configuration pane
    '''
    def __init__(self, data, parent=None, *args):
        ''' Constructor
        @param data: array of EEG_ChannelProperties objects
        '''
        Qt.QAbstractTableModel.__init__(self, parent, *args)
        self.arraydata = data
        # column description
        self.columns = [{'property':'input', 'header':'Channel', 'edit':False, 'editor':'default'},
                        {'property':'enable', 'header':'Enable', 'edit':True, 'editor':'default'},
                        #{'property':'lowpass', 'header':'High Cutoff', 'edit':False, 'editor':'combobox'},
                        #{'property':'highpass', 'header':'Low Cutoff', 'edit':False, 'editor':'combobox'},
                        #{'property':'notchfilter', 'header':'Notch', 'edit':False, 'editor':'default'},
                        {'property':'name', 'header':'Name', 'edit':True, 'editor':'default'},
                       ]

        # insert reference channel selection to column description for EEG channels
        if (len(data) > 0) and (data[0].group == ChannelGroup.EEG):
            self.columns.insert(2, 
                                {'property':'isReference', 'header':'Reference', 'edit':True, 'editor':'default'}
                                )
        
        # combo box list contents
        self.lowpasslist = ['off', '10', '20', '50', '100', '200', '500', '1000', '2000']
        self.highpasslist = ['off','0.01', '0.02', '0.05', '0.1', '0.2', '0.5', '1', '2', '5', '10']
        
    def _getitem(self, row, column):
        ''' Get amplifier property item based on table row and column
        @param row: row number
        @param column: column number
        @return:  QVariant property value
        ''' 
        if (row >= len(self.arraydata)) or (column >= len(self.columns)):
            return Qt.QVariant()
        
        # get channel properties
        property = self.arraydata[row]
        # get property name from column description
        property_name = self.columns[column]['property']
        # get property value
        if property_name == 'input':
            d = Qt.QVariant(property.input)
        elif property_name == 'enable':
            d = Qt.QVariant(property.enable)
        elif property_name == 'name':
            d = Qt.QVariant(property.name)
        elif property_name == 'lowpass':
            if property.lowpass == 0.0:
                d = Qt.QVariant('off')
            else:
                d = Qt.QVariant(property.lowpass)
        elif property_name == 'highpass':
            if property.highpass == 0.0:
                d = Qt.QVariant('off')
            else:
                d = Qt.QVariant(property.highpass)
        elif property_name == 'notchfilter':
            d = Qt.QVariant(property.notchfilter)
        elif property_name == 'isReference':
            d = Qt.QVariant(property.isReference)
        else:
            d = Qt.QVariant()
        return d

    def _setitem(self, row, column, value):
        ''' Set amplifier property item based on table row and column
        @param row: row number
        @param column: column number
        @param value: QVariant value object
        @return: True if property value was set, False if not
        ''' 
        if (row >= len(self.arraydata)) or (column >= len(self.columns)):
            return False
        # get channel properties
        property = self.arraydata[row]
        # get property name from column description
        property_name = self.columns[column]['property']
        # set channel property
        if property_name == 'enable':
            property.enable = value.toBool()
            return True
        elif property_name == 'name':
            n = value.toString()
            if n.isEmpty() or n.trimmed().isEmpty():
                return False
            property.name = value.toString()
            return True
        elif property_name == 'lowpass':
            property.lowpass,ok = value.toDouble()
            if property.group == ChannelGroup.EEG:
                for prop in self.arraydata:
                    prop.lowpass = property.lowpass
            return True
        elif property_name == 'highpass':
            property.highpass,ok = value.toDouble()
            if property.group == ChannelGroup.EEG:
                for prop in self.arraydata:
                    prop.highpass = property.highpass
            return True
        elif property_name == 'notchfilter':
            property.notchfilter = value.toBool()
            if property.group == ChannelGroup.EEG:
                for prop in self.arraydata:
                    prop.notchfilter = property.notchfilter
                self.reset()
            return True
        elif property_name == 'isReference':
            # available for EEG channels only
            if property.group == ChannelGroup.EEG:
                # remove previously selected reference channel in single channel mode
                if not AMP_MULTIPLE_REF:
                    if value.toBool() == True:
                        for prop in self.arraydata:
                            prop.isReference = False
                property.isReference = value.toBool()
                self.reset()
            return True
        return False
        
    def editorType(self, column):
        ''' Get the columns editor type from column description
        @param column: table column number
        @return: editor type as QVariant (string)
        ''' 
        if column >= len(self.columns):
            return Qt.QVariant()
        return Qt.QVariant(self.columns[column]['editor'])
    
    def comboBoxList(self, column):
        ''' Get combo box item list for column 'highpass' or 'lowpass'
        @param column: table column number
        @return: combo box item list as QVariant 
        '''
        if column >= len(self.columns):
            return Qt.QVariant()
        if self.columns[column]['property'] == 'lowpass':
            return Qt.QVariant(self.lowpasslist)
        elif self.columns[column]['property'] == 'highpass':
            return Qt.QVariant(self.highpasslist)
        else:
            return Qt.QVariant()
    
    def rowCount(self, parent):
        ''' Get the number of required table rows
        @return: number of rows
        '''
        if parent.isValid():
            return 0
        return len(self.arraydata)
    
    def columnCount(self, parent):
        ''' Get the number of required table columns
        @return: number of columns
        '''
        if parent.isValid():
            return 0
        return len(self.columns)
        
    def data(self, index, role): 
        ''' Abstract method from QAbstactItemModel to get cell data based on role
        @param index: QModelIndex table cell reference
        @param role: given role for the item referred to by the index
        @return: the data stored under the given role for the item referred to by the index
        '''
        if not index.isValid(): 
            return Qt.QVariant()
        
        # get the underlying data
        value = self._getitem(index.row(), index.column())
        
        if role == Qt.Qt.CheckStateRole:
            # hide/disable the reference channel
            if AMP_HIDE_REF:
                properties = self.arraydata[index.row()]
                property_name = self.columns[index.column()]['property']
                if property_name == "enable" and properties.isReference:
                    return Qt.Qt.Unchecked
            
            # set check state
            if value.type() == Qt.QMetaType.Bool:
                if value.toBool():
                    return Qt.Qt.Checked
                else:
                    return Qt.Qt.Unchecked
        
        elif (role == Qt.Qt.DisplayRole) or (role == Qt.Qt.EditRole):
            if value.type() != Qt.QMetaType.Bool:
                return value
        
        elif role == Qt.Qt.BackgroundRole:
            # change background color for reference channel
            property = self.arraydata[index.row()]
            #if (property.isReference) and (index.column() == 0):
            if (property.isReference):
                return Qt.QVariant( Qt.QColor(0, 0, 255))
            
        return Qt.QVariant()
    
    def flags(self, index):
        ''' Abstract method from QAbstactItemModel
        @param index: QModelIndex table cell reference
        @return: the item flags for the given index
        '''
        if not index.isValid():
            return Qt.Qt.ItemIsEnabled
        if not self.columns[index.column()]['edit']:
            return Qt.Qt.ItemIsEnabled
        value = self._getitem(index.row(), index.column())
        if value.type() == Qt.QMetaType.Bool:
            return Qt.QAbstractTableModel.flags(self, index) | Qt.Qt.ItemIsUserCheckable | Qt.Qt.ItemIsSelectable
        return Qt.QAbstractTableModel.flags(self, index) | Qt.Qt.ItemIsEditable
        
    def setData(self, index, value, role):
        ''' Abstract method from QAbstactItemModel to set cell data based on role
        @param index: QModelIndex table cell reference
        @param value: QVariant new cell data
        @param role: given role for the item referred to by the index
        @return: true if successful; otherwise returns false.
        '''
        if index.isValid(): 
            if role == Qt.Qt.EditRole:
                if not self._setitem(index.row(), index.column(), value):
                    return False
                self.emit(Qt.SIGNAL('dataChanged(QModelIndex, QModelIndex)'), index, index)
                return True
            elif role == Qt.Qt.CheckStateRole:
                if not self._setitem(index.row(), index.column(), Qt.QVariant(value == Qt.Qt.Checked)):
                    return False
                self.emit(Qt.SIGNAL('dataChanged(QModelIndex, QModelIndex)'), index, index)
                return True
        return False

    def headerData(self, col, orientation, role):
        ''' Abstract method from QAbstactItemModel to get the column header
        @param col: column number
        @param orientation: Qt.Horizontal = column header, Qt.Vertical = row header
        @param role: given role for the item referred to by the index
        @return: header
        '''
        if orientation == Qt.Qt.Horizontal and role == Qt.Qt.DisplayRole:
            return Qt.QVariant(self.columns[col]['header'])
        return Qt.QVariant()


class _ConfigItemDelegate(Qt.QStyledItemDelegate):  
    ''' Combobox item editor
    '''
    def __init__(self, parent=None):
        super(_ConfigItemDelegate, self).__init__(parent)
        
    def createEditor(self, parent, option, index):
        if index.model().editorType(index.column()) == 'combobox':
            combobox = Qt.QComboBox(parent)
            combobox.addItems(index.model().comboBoxList(index.column()).toStringList())
            combobox.setEditable(False)
            self.connect(combobox, Qt.SIGNAL('activated(int)'), self.emitCommitData)
            return combobox
        return Qt.QStyledItemDelegate.createEditor(self, parent, option, index)

    def setEditorData(self, editor, index):
        if index.model().columns[index.column()]['editor'] == 'combobox':
            text = index.model().data(index, Qt.Qt.DisplayRole).toString()
            i = editor.findText(text)
            if i == -1:
                i = 0
            editor.setCurrentIndex(i)
        Qt.QStyledItemDelegate.setEditorData(self, editor, index)


    def setModelData(self, editor, model, index):
        if model.columns[index.column()]['editor'] == 'combobox':
            model.setData(index, Qt.QVariant(editor.currentText()), Qt.Qt.EditRole)
            model.reset()
        Qt.QStyledItemDelegate.setModelData(self, editor, model, index)

    def emitCommitData(self):
        self.emit(Qt.SIGNAL('commitData(QWidget*)'), self.sender())



      
