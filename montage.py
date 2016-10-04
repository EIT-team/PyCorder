# -*- coding: utf-8 -*-
'''
Recording Montage Module

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
@date: $Date: 2013-07-03 17:26:26 +0200 (Mi, 03 Jul 2013) $
@version: 1.0

B{Revision:} $LastChangedRevision: 216 $
'''

from collections import defaultdict
import textwrap

from modbase import *
from tools.modview import GenericTableWidget


class MNT_Recording(ModuleBase):
    ''' Recording Montage
    Configure and use a recording montage
    '''

    def __init__(self, *args, **keys):
        ''' Constructor
        '''
        # initialize the base class, give a descriptive name
        ModuleBase.__init__(self, name="Recording Montage", **keys)    

        # XML parameter version
        # 1: initial version
        self.xmlVersion = 1 

        # initialize module variables
        self.data = None                # hold the data block we got from previous module
        self.dataavailable = False      # data available for output to next module 
        self.current_input_params = None         # backup of last received properties
        
        self.montage_channel_properties = np.array([])
        self.montage = Montage()
        
        self.hideRefChannels = True     # always hide or show reference channels
        self.refChannelNames = "none"
        self.hasDuplicateLabels = False
        
        self.needs_conversion = True    # amplifier montage needs to be converted (compatibility mode) 
        
    def setDefault(self):
        ''' Set all module parameters to default values
        '''
        self.needs_conversion = True
        self.montage.reset()

    def getMontageList(self):
        return self.montage.get_configuration_table(self.current_input_params.channel_properties)

    def get_configuration_pane(self):
        ''' Get the configuration pane
        @return: a QFrame object or None if you don't need a configuration pane
        '''
        cfgPane = _ConfigurationPane(self)
        self.connect(cfgPane, Qt.SIGNAL("dataChanged()"), self._configurationDataChanged)
        return cfgPane

    def _configurationDataChanged(self):
        self.needs_conversion = False
        # we need a copy of the input parameters to keep the original input
        params = copy.copy(self.current_input_params) 
        # propagate changes to connected modules
        self.update_receivers(self._apply_montage(params), propagate_only=True)

    def _get_group_indices(self, properties):
        # get indices and input channels of all different groups as dictionaries
        groups = defaultdict(list)
        groupchannels = defaultdict(dict)
        for idx, channel in enumerate(properties):
            groups[channel.inputgroup].append(idx)
            groupchannels[channel.inputgroup][channel.input] = idx
        return dict(groups), dict(groupchannels)

    def _create_output_selection(self, params):
        ''' Create index arrays for module data output 
        '''
        properties = params.channel_properties
        
        # get all active eeg channel indices (excluding reference channels)
        mask = lambda x: (x.group == ChannelGroup.EEG) and x.enable and not x.isReference
        channel_map = np.array(map(mask, properties))
        self.eeg_indices = np.nonzero(channel_map)[0]     # indices of all eeg channels

        # get the reference channel indices
        mask = lambda x: (x.group == ChannelGroup.EEG) and x.isReference
        channel_map = np.array(map(mask, properties))
        self.ref_indices = np.nonzero(channel_map)[0]     # indices of reference channel(s)
        
        # get output channel indices, depending on recording mode
        if params.recording_mode == RecordingMode.IMPEDANCE or params.recording_mode == RecordingMode.TEST:
            # get all enabled channel indices, including reference channels
            mask = lambda x: (x.enable == True) or ((x.group == ChannelGroup.EEG) and x.isReference)
        else:
            if self.hideRefChannels:
                # get all enabled channel indices, excluding reference channels
                mask = lambda x: (x.enable == True) and not ((x.group == ChannelGroup.EEG) and x.isReference)
            else:
                # get all enabled channel indices, including enabled reference channels
                mask = lambda x: (x.enable == True)
                
        channel_map = np.array(map(mask, properties))
        self.output_channel_indices = np.nonzero(channel_map)[0]     # indices of all enabled channels

        # append "REF" to the reference channel name and create the combined reference channel name
        refnames = []
        for prop in properties[self.ref_indices]:
            refnames.append(prop.name)
            prop.name = "REF_" + prop.name
            prop.refname = ""
        
        # combined reference channel names for storage and status display
        channelpropref = ""
        if params.recording_mode == RecordingMode.IMPEDANCE or params.recording_mode == RecordingMode.TEST:
            params.ref_channel_name = "none"
        else:
            if len(refnames) > 1:
                params.ref_channel_name = "AVG(" + " + ".join(refnames) + ")"
                channelpropref = "REF"
            elif len(refnames) == 1:
                params.ref_channel_name = "".join(refnames)
                channelpropref = "REF"
            else:
                params.ref_channel_name = "none"

        # set reference channel name for the affected eeg electrodes
        for prop in properties[self.eeg_indices]:
            prop.refname = channelpropref
        
        # reference channel names for display in the configuration pane
        if len(refnames) > 0:
            self.refChannelNames = " + ".join(refnames)
        else:
            self.refChannelNames = "none"

    def _validateChannelLabels(self):
        # search for duplicate channel labels
        labelList = [ch.name.lower() for ch in self.output_channel_properties if ch.enable ]
        labelDictionary = defaultdict(int)
        for l in labelList:
            labelDictionary[l] += 1
        if labelDictionary and max(labelDictionary.values()) > 1:
            return False
        return True

    def _apply_montage(self, params):
        # update the properties with montage settings
        for ch in params.channel_properties:
            if not self.montage.update_channel(ch):
                if not self.needs_conversion:
                    # switch off all channels not found in this montage
                    ch.enable = False
                    ch.isReference = False  
                self.montage.add(ch)
        
        # select output channels
        self._create_output_selection(params)
        self.output_channel_properties = np.array(params.channel_properties)[self.output_channel_indices]
        params.channel_properties = copy.deepcopy(self.output_channel_properties)
        if params.eeg_channels.size > 0:
            params.eeg_channels = params.eeg_channels[self.output_channel_indices]

        # send number of enabled channels for status display
        self.send_event(ModuleEvent(self._object_name,
                                    EventType.STATUS,
                                    info = "%d ch"%(len(self.output_channel_indices)),
                                    status_field="Channels"))

        # send reference channel names for status display
        self.send_event(ModuleEvent(self._object_name,
                                    EventType.STATUS,
                                    info = "REF: %s"%(params.ref_channel_name),
                                    status_field="Reference"))
        
        # check for duplicate labels and show warning
        if not self._validateChannelLabels():
            self.hasDuplicateLabels = True
            self.send_event(ModuleEvent(self._object_name,
                                        EventType.ERROR,
                                        info = "Pycorder detected duplicate channel names, please check the recording montage," +
                                               "otherwise this may cause problems in your analysis software",
                                        severity=ErrorSeverity.IGNORE))
        else:
            # remove the previous warning message from status line
            if self.hasDuplicateLabels:
                self.hasDuplicateLabels = False
                self.send_event(ModuleEvent("",
                                            EventType.MESSAGE,
                                            info = ""))
        
        return params        
        


    def process_update(self, params):
        ''' Get and store properties from previous module
        @param params: EEG_DataBlock object
        @return: EEG_DataBlock object  
        '''
        # keep the last property block for propagating changes during configuration
        self.current_input_params = copy.copy(params)
        # apply the montage settings
        params = self._apply_montage(params)
        return params


    def process_start(self):
        if self.output_channel_properties.size == 0:
            raise ModuleError(self._object_name, "no channels selected!")
            

    def process_input(self, datablock):
        ''' Get data from previous module
        @param datablock: EEG_DataBlock object 
        '''
        self.dataavailable = True       # signal data availability
        self.data = datablock           # get a local reference

        if datablock.recording_mode != RecordingMode.IMPEDANCE and datablock.recording_mode != RecordingMode.TEST:
            # average and subtract the reference channels
            if self.ref_indices.size > 0:
                # average reference channels
                reference = np.mean(self.data.eeg_channels[self.ref_indices], 0)
                # subtract reference
                self.data.eeg_channels[self.eeg_indices] -= reference
    
        # simple copy is three times faster than deepcopy
        #self.data.channel_properties = copy.deepcopy(self.output_channel_properties)
        self.data.channel_properties = self.output_channel_properties.copy()
        for idx in range(self.data.channel_properties.size):
            self.data.channel_properties[idx] = copy.copy(self.output_channel_properties[idx])
        
        self.data.eeg_channels = self.data.eeg_channels[self.output_channel_indices]


    
    def process_output(self):
        ''' Send data out to next module
        '''
        if not self.dataavailable:
            return None
        self.dataavailable = False
        return self.data
    
    def setXML(self, xml):
        ''' Set module properties from XML configuration file
        @param xml: complete objectify XML configuration tree, 
        module will search for matching values
        '''
        # reset everything to default values
        self.setDefault()
        
        # search my configuration data
        montage = xml.xpath("//MNT_Recording[@module='montage' and @instance='%i']"%(self._instance) )
        if len(montage) == 0:
            return      # configuration data not found, proceed with defaults
        
        cfg = montage[0]   # we should have only one montage instance from this type
        
        # check version, has to be lower or equal than current version
        version = cfg.get("version")
        if (version == None) or (int(version) > self.xmlVersion):
            self.send_event(ModuleEvent(self._object_name, EventType.ERROR, "XML Configuration: wrong version"))
            return
        version = int(version)

        # get the values
        try:
            # setup montage channel configuration from xml
            self.montage.setXML(cfg)
        except Exception as e:
            self.send_exception(e, severity=ErrorSeverity.NOTIFY)

    def getXML(self):
        ''' Get module properties for XML configuration file. 
        @return: objectify XML element
        '''
        if not self._validateChannelLabels():
            Qt.QMessageBox.critical(None, "PyCorder", "It is not possible to save a configuration that contains duplicate channel names.")
            raise Exception("configuration contains duplicate channel names")
        E = objectify.E
        channels = self.montage.getXML()
        montage = E.MNT_Recording( channels, 
                                   version=str(self.xmlVersion),
                                   instance=str(self._instance),
                                   module="montage")
        return montage


class Montage():
    ''' Montage dictionary
    '''
    def __init__(self):
        # XML parameter version
        # 1: initial version
        self.xmlVersion = 1 

        self.reset()
        
    def reset(self):
        ''' Reset the channel dictionary
        '''
        self.channel_dict = defaultdict(lambda: defaultdict(dict))   # dictionary with input group and input channel number as keys
    
    def add(self, channel):
        ''' add a channel to the dictionary
        @param channel: EEG_ChannelProperties object
        '''
        ch =  copy.copy(channel)
        # remove trailing and leading spaces from channel label
        ch.name = ch.name.strip()
        self.channel_dict[channel.inputgroup][channel.input][channel.group] = ch
        
    def has_channel(self, channel):
        ''' check if the dictionary has an entry for this channel
        @param channel: EEG_ChannelProperties object
        @return: True if channel entry available
        '''
        return self.channel_dict.has_key(channel.inputgroup) and\
             self.channel_dict[channel.inputgroup].has_key(channel.input) and\
             self.channel_dict[channel.inputgroup][channel.input].has_key(channel.group) 
             

    def get_channel(self, channel):
        ''' get channel from dictionary
        @param channel: EEG_ChannelProperties object
        @return: EEG_ChannelProperties object or None if channel is not available
        '''
        if not self.has_channel(channel):
            return None
        ch = self.channel_dict[channel.inputgroup][channel.input][channel.group]
        # remove trailing and leading spaces from channel label
        ch.name = ch.name.strip()
        return ch

    def update_channel(self, channel):
        ''' update the channel properties from montage settings
        @param channel: EEG_ChannelProperties object
        @return: True on success  
        '''        
        mntchannel = self.get_channel(channel)
        if mntchannel == None:
            return False
        
        channel.name = mntchannel.name
        channel.enable = mntchannel.enable
        channel.isReference = mntchannel.isReference
        channel.color = mntchannel.color
        channel.unit = mntchannel.unit
        return True

    def get_configuration_table(self, properties):
        ''' get the configuration table for the current input properties
        @param properties: current channel properties array
        @return: montage channel properties
        '''
        mntproperties = []
        for ch in properties:
            mntchannel = self.get_channel(ch)
            if mntchannel != None:
                mntproperties.append(mntchannel)
        return np.array(mntproperties)

    def setXML(self, xml):
        ''' Set module properties from XML configuration file
        @param xml: complete objectify XML configuration tree, 
        module will search for matching values
        '''
        self.reset()
        for chXML in xml.MontageChannels.iterchildren():
            channel = EEG_ChannelProperties("")
            channel.setXML(chXML)
            self.add(channel)
    
    def getXML(self):
        ''' Get module properties for XML configuration file. 
        @return: objectify XML element
        '''
        E = objectify.E
        channels = E.MontageChannels()
        for inputgroup in self.channel_dict.values():
            for inputnr in inputgroup.values():
                for channel in inputnr.values():
                    channels.append(channel.getXML())
        channels.attrib["version"] = str(self.xmlVersion)
        return channels






################################################################
# Configuration Pane
        
class _ConfigurationPane(Qt.QFrame):
    ''' Amplifier Test Module configuration pane.
    '''
    def __init__(self, module, *args):
        apply(Qt.QFrame.__init__, (self,) + args)
        
        # reference to our parent module
        self.module = module
        
        # Set tab name
        self.setWindowTitle("Recording Montage")
        
        # make it nice
        self.setFrameShape(Qt.QFrame.StyledPanel)
        self.setFrameShadow(Qt.QFrame.Raised)
        
        # base layout
        self.gridLayout = Qt.QGridLayout(self)

        # reference selection layout
        self.refLayout = Qt.QVBoxLayout()

        # create labels
        self.labelEeg = Qt.QLabel("EEG channels")
        self.labelOther = Qt.QLabel("Other channels")
        
        self.labelReference = Qt.QLabel("Selected Reference Channel(s)")
        self.labelReference.setAlignment(Qt.Qt.AlignCenter)
        self.labelReference.setStyleSheet('color: blue')

        self.labelReferenceSelection = Qt.QLabel("none")
        self.labelReferenceSelection.setAlignment(Qt.Qt.AlignCenter)
        self.labelReferenceSelection.setStyleSheet('color: blue')

        self.labelDuplicates = Qt.QLabel("Duplicate channel names detected!")
        self.labelDuplicates.setAlignment(Qt.Qt.AlignCenter)
        self.labelDuplicates.setStyleSheet('color: red')


        # create eeg channels table view
        self.channeltableEeg = GenericTableWidget(self)
        self.channeltableEeg.resizeColumnsToContents()
        self.channeltableEeg.setfnValidate(self.validateEEGChannelLabel)

        # create other channels table view
        self.channeltableOther = GenericTableWidget(self)
        self.channeltableOther.resizeColumnsToContents()
        self.channeltableOther.setfnValidate(self.validateAUXChannelLabel)

        self.resetChannelTables()
        
        # highlight reference channels
        lcs = lambda x: Qt.QColor(0, 0, 255) if x.isReference else None 
        self.channeltableEeg.setfnColorSelect(lcs)
        
        # set function for checkbox get values (x[0] = column number, x[1] = EEG_ChannelProperties object)
        if self.module.hideRefChannels:
            # get the "enable" column number
            columns = self.getCfgTableViewDescription(eeg=True)[0]
            colEnable = [c for c in range(len(columns)) if columns[c]["variable"] == "enable"][0] 
            # hide enable for reference channels 
            hideref = lambda x: None if x[0] != colEnable else (False if x[1].isReference else x[1].enable)
            self.channeltableEeg.setfnCheckBox(hideref)
        
        
        # add all items to the layouts
        self.refLayout.addWidget(self.labelReference)
        self.refLayout.addWidget(self.labelReferenceSelection)
        spacerItemRL1 = Qt.QSpacerItem(20, 40, Qt.QSizePolicy.Minimum, Qt.QSizePolicy.Expanding)
        self.refLayout.addItem(spacerItemRL1)
        self.refLayout.addWidget(self.labelDuplicates)
        
        self.gridLayout.addWidget(self.labelEeg, 0, 0)
        self.gridLayout.addWidget(self.channeltableEeg, 1, 0, 1, 2)
        self.gridLayout.addLayout(self.refLayout, 1, 2, 1, 1)

        self.gridLayout.addWidget(self.labelOther, 2, 0)
        self.gridLayout.addWidget(self.channeltableOther, 3, 0, 1, 3)
        
        # actions
        self.connect(self.channeltableEeg, Qt.SIGNAL("dataChanged()"), self._configurationDataChanged)
        self.connect(self.channeltableOther, Qt.SIGNAL("dataChanged()"), self._configurationDataChanged)


    def validateEEGChannelLabel(self, row, col, data):
        if col == 5:
            name = data[row].name.lower()
            enable = data[row].enable
            if enable and self.labelDictionary.has_key(name) and self.labelDictionary[name] > 1:
                return False
        return True

    def validateAUXChannelLabel(self, row, col, data):
        if col == 4:
            name = data[row].name.lower()
            enable = data[row].enable
            if enable and self.labelDictionary.has_key(name) and self.labelDictionary[name] > 1:
                return False
        return True

    def getCfgTableViewDescription(self, eeg=False):
        # fields from EEG_ChannelProperties
        if eeg:
            columns =  [
                        {'variable':'inputgroup', 'header':'Port', 'edit':False, 'editor':'combobox', 'indexed':True},
                        {'variable':'input', 'header':'Channel', 'edit':False, 'editor':'default'},
                        {'variable':'enable', 'header':'Enable', 'edit':True, 'editor':'default'},
                        {'variable':'isReference', 'header':'Reference', 'edit':True, 'editor':'default'},
                        {'variable':'group', 'header':'Group', 'edit':False, 'editor':'combobox', 'indexed':True},
                        {'variable':'name', 'header':'Name', 'edit':True, 'editor':'default'},
                       ]
            cblist = {'inputgroup':ChannelGroup.Name, 'group':ChannelGroup.Name}
        else:
            columns =  [
                        {'variable':'inputgroup', 'header':'Port', 'edit':False, 'editor':'combobox', 'indexed':True},
                        {'variable':'input', 'header':'Channel', 'edit':False, 'editor':'default'},
                        {'variable':'enable', 'header':'Enable', 'edit':True, 'editor':'default'},
                        {'variable':'group', 'header':'Group', 'edit':False, 'editor':'combobox', 'indexed':True},
                        #{'variable':'unit', 'header':'Unit', 'edit':True, 'editor':'default'},
                        {'variable':'name', 'header':'Name', 'edit':True, 'editor':'default'},
                       ]
            cblist = {'inputgroup':ChannelGroup.Name, 'group':ChannelGroup.Name}
        
        return columns, cblist

    def resetChannelTables(self):
        # split montage table into eeg and other channels
        montage = self.module.getMontageList()
        ch_map = np.array(map(lambda x: (x.group == ChannelGroup.EEG), montage))
        eeg_indices = np.nonzero(ch_map)[0]           # indices of all eeg channels

        if ch_map.shape[0]:
            other_indices = np.nonzero(np.invert(ch_map))[0]     # indices of all other channels
        else:
            other_indices = []

        # update table widgets
        description, cblist = self.getCfgTableViewDescription(eeg=True)
        self.channeltableEeg.setData(montage[eeg_indices], description, cblist)
        description, cblist = self.getCfgTableViewDescription(eeg=False)
        self.channeltableOther.setData(montage[other_indices], description, cblist)
        
        # reset label validation dictionary
        self.labelDictionary = defaultdict(int)


    def showRefChannels(self):
        labelText = textwrap.fill(self.module.refChannelNames, 30)
        self.labelReferenceSelection.setText(labelText)

    def showLabelValidation(self):
        labelList = [ch.name.lower() for ch in self.channeltableEeg.data if ch.enable ]
        labelList.extend([ch.name.lower() for ch in self.channeltableOther.data if ch.enable])
        self.labelDictionary = defaultdict(int)
        for l in labelList:
            self.labelDictionary[l] += 1
        if self.labelDictionary and max(self.labelDictionary.values()) > 1:
            self.labelDuplicates.show()
        else:
            self.labelDuplicates.hide()
        self.channeltableOther.reset()
        self.channeltableEeg.reset()

    def showEvent(self, event):
        self.resetChannelTables()
        self.showRefChannels()
        self.showLabelValidation()
        
    def _configurationDataChanged(self):
        self.emit(Qt.SIGNAL('dataChanged()'))
        self.showRefChannels()
        self.showLabelValidation()

if __name__ == '__main__':
    pass

