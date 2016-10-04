# -*- coding: utf-8 -*-
'''
Remote Data Access (RDA) Server Module

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
@version: 1.0
'''

from modbase import *
from socket import *
from select import *
from struct import *
from binascii import *
from ctypes import *

class RDAMessageType:
    ''' RDA Message Types
    '''
    START = 1           #: Setup / Start info
    DATA16 = 2          #: Block of 16-bit data
    STOP = 3            #: Data acquisition has been stopped
    DATA32 = 4          #: Block of 32-bit floating point data
    NEWSTATE = 5        #: Recorder state has been changed
    IMP_START = 6       #: Impedance measurement start
    IMP_DATA = 7        #: Impedance measurement data
    IMP_STOP = 8        #: Impedance measurement stop
    INFO = 9            #: Recorder info Header, sent after connection and when setup is changed
    KEEP_ALIVE = 10000  #: Sent periodically to check whether the connection is still alive


class RDA_Server(ModuleBase):
    ''' Transmit EEG data over network via TCP/IP 
    '''

    def __init__(self, *args, **keys):
        ''' Initialize module and create the accept thread
        '''
        ModuleBase.__init__(self, name="RDA Server", **keys)
        self.data = None
        self.dataavailable = False
        
        self._thServerLock = threading.Lock()
        
        self.params = None          #: last channel configuration
        self.clients = []           #: list of connected clients
        self.blockcount = 0         #: number of received data blocks
        self.showClientErrors = False   #: we don't want to see client performance problems  
        
        # define message header structures
        self.GUID = unhexlify("8E45584396C9864CAF4A98BBF6C91450") 
        self.hdr = "<16sLL"     # generic header: GUID, nSize, nType
        
        # create server socket
        #self.HOST = 'localhost'
        self.HOST = '0.0.0.0'
        self.PORT = 51244           #: 32-Bit data port
        self.ADDR = (self.HOST, self.PORT)
        self.serversock = socket(AF_INET, SOCK_STREAM)
        try:
            self.serversock.bind(self.ADDR)
            self.serversock.setblocking(0)
            self.serversock.listen(2)
        except:
            raise Exception("RDA Server: another TCP/IP server is already running on this port: %d\r\n"%(self.PORT) +
                            "Maybe there is already a running instance of BrainVision PyCorder "
                            "or BrainVision Recoder.")
            

        # create server thread
        self.serverthread_running = True
        self.serverthread = threading.Thread(target=self._accept_thread)
        self.serverthread.start()
        
        
    def terminate(self):
        ''' Shut down server socket
        '''
        self.serverthread_running = False
        self.serverthread.join(5.0)
        # close client sockets
        for client in self.clients[:]:
            client.terminate()
            self.clients.remove(client)
        self.serversock.close()
        
        
    def _accept_thread(self):
        ''' Server socket accept client connections
        '''
        aliveMsg = self.build_message(RDAMessageType.KEEP_ALIVE)
        while self.serverthread_running:

            # wait until module is initialized
            if self.params == None:
                time.sleep(0.05)
                continue
             
            # waiting for connection
            rd, wr, err = select([self.serversock],[],[], 0.05)
            if len(rd) > 0:
                # get the client socket and create a connection object
                clientsock, addr = self.serversock.accept()
                client = ClientConnection(clientsock, addr)
                # init client
                try:
                    sm = self.build_message(0)
                    client.send(sm)
                    si = self.build_message(RDAMessageType.INFO, self.params)
                    client.send(si)
    
                    if self.isRunning():
                        if self.params.recording_mode == RecordingMode.IMPEDANCE:
                            sm = self.build_message(RDAMessageType.IMP_START)
                            st = self.build_message(RDAMessageType.NEWSTATE, 3)
                        else:
                            sm = self.build_message(RDAMessageType.START, self.params)
                            st = self.build_message(RDAMessageType.NEWSTATE, 1)
                        client.send(st)
                        client.send(sm)
                    else:
                        st = self.build_message(RDAMessageType.NEWSTATE, 0)
                        client.send(st)
                except:
                    pass
                
                if client.connected:
                    self._thServerLock.acquire()
                    self.clients.append(client)
                    self._thServerLock.release()
                    self.send_event(ModuleEvent(self._object_name, EventType.LOGMESSAGE,
                                                "RDA Client connected: %s"%(str(addr))))

            # check connections
            self._thServerLock.acquire()
            for client in self.clients[:]:
                if not self.isRunning() or  self.params.recording_mode == RecordingMode.IMPEDANCE:
                    try:
                        client.send(aliveMsg)
                    except:
                        pass
                if not client.connected:
                    client.terminate()
                    self.clients.remove(client)
                    self.send_event(ModuleEvent(self._object_name, EventType.LOGMESSAGE,
                                                "RDA Client disconnected: %s"%(str(client.addr))))
            self._thServerLock.release()
                

        
    def process_input(self, datablock):
        ''' Build TCP/IP messages from data and send it to attached clients
        '''
        self.dataavailable = True
        self.data = datablock
        self.blockcount += 1

        # check for attached clients
        self._thServerLock.acquire()
        if len(self.clients) == 0:
            self._thServerLock.release()
            return
        self._thServerLock.release()

        # build impedance or data messages 
        if self.data.recording_mode == RecordingMode.IMPEDANCE:
            # build impedance message
            dm = self.build_message(RDAMessageType.IMP_DATA, datablock)
        else:
            # build data message
            dm = self.build_message(RDAMessageType.DATA32, datablock)
        
        # send data to attached clients
        self._thServerLock.acquire()
        for client in self.clients:
            try:
                client.send(dm)
            except:
                if self.showClientErrors:
                    self.send_event(ModuleEvent(self._object_name, EventType.ERROR,
                                                "RDA Client input queue FULL, overrun!", severity=ErrorSeverity.NOTIFY))
        self._thServerLock.release()


    def process_output(self):
        if not self.dataavailable:
            return None
        self.dataavailable = False
        return self.data

    def process_update(self, params):
        ''' Notify attached clients about channel configuration changes
        '''
        # copy settings
        self.params = copy.deepcopy(params)

        # notifiy attached clients
        self._thServerLock.acquire()
        if len(self.clients) > 0:
            si = self.build_message(RDAMessageType.INFO, self.params)
            for client in self.clients:
                try:
                    client.send(si)
                except:
                    if self.showClientErrors:
                        self.send_event(ModuleEvent(self._object_name, EventType.ERROR,
                                                    "RDA Client input queue FULL, overrun!", severity=ErrorSeverity.NOTIFY))
        self._thServerLock.release()
        
        return params

    
    def process_start(self):
        ''' Notify attached clients about state change
        '''
        self.blockcount = 0
        # notifiy attached clients
        if self.params.recording_mode == RecordingMode.IMPEDANCE:
            sm = self.build_message(RDAMessageType.IMP_START)
            st = self.build_message(RDAMessageType.NEWSTATE, 3)
        else:
            sm = self.build_message(RDAMessageType.START, self.params)
            st = self.build_message(RDAMessageType.NEWSTATE, 1)
        self._thServerLock.acquire()
        for client in self.clients:
            try:
                client.send(st)
                client.send(sm)
            except:
                if self.showClientErrors:
                    self.send_event(ModuleEvent(self._object_name, EventType.ERROR,
                                                "RDA Client input queue FULL, overrun!", severity=ErrorSeverity.NOTIFY))
        self._thServerLock.release()
        
    def process_stop(self):
        ''' Notify attached clients about state change
        '''
        if self.params.recording_mode == RecordingMode.IMPEDANCE:
            sm = self.build_message(RDAMessageType.IMP_STOP)
        else:
            sm = self.build_message(RDAMessageType.STOP)
        st = self.build_message(RDAMessageType.NEWSTATE, 0)
        self._thServerLock.acquire()
        for client in self.clients:
            try:
                client.send(st)
                client.send(sm)
            except:
                if self.showClientErrors:
                    self.send_event(ModuleEvent(self._object_name, EventType.ERROR,
                                                "RDA Client input queue FULL, overrun!", severity=ErrorSeverity.NOTIFY))
        self._thServerLock.release()
        
    
        
    def build_message(self, type, data=None):
        ''' Build a message buffer according to message type
        @param type: RDAMessageType
        @param data: data object to send
        @return: binary message blob
        '''
        if type == RDAMessageType.START:
            channels = len(data.channel_properties)
            samplingInterval = 1.0e6 / data.sample_rate     # sampling interval in us
            
            # create resolution byte array (we have a resolution of 1uV for all channels)
            res = [1.0] * channels
            resbyte = pack("<" + "d" * channels, *res)
            
            # create channel names byte array (null terminated strings)
            # use ansi code page 1252
            chn =[]
            for channel in data.channel_properties:
                chn.append(unicode(channel.name).encode("cp1252"))
            chnbyte = "\0".join(chn) + "\0"    
            
            # create message header
            hdr_start = Struct(self.hdr+ "Ld")      # start: nChannels, dSamplingInterval + data
            blocksize = hdr_start.size + len(resbyte) + len(chnbyte)
            hdrbyte = bytearray(hdr_start.pack(self.GUID, blocksize, type, channels, samplingInterval))
            
            # add data part
            hdrbyte.extend(resbyte)
            hdrbyte.extend(chnbyte)
            return hdrbyte 
            
        elif type == RDAMessageType.STOP:
            # create message header
            hdr_start = Struct(self.hdr)      
            blocksize = hdr_start.size
            hdrbyte = bytearray(hdr_start.pack(self.GUID, blocksize, type))
            return hdrbyte

        elif type == RDAMessageType.DATA32:
            # create data byte array
            nPoints = len(data.sample_channel[0])
            # convert data to float and write to data file
            d = data.eeg_channels.transpose()
            f = d.flatten().astype(np.float32)
            databyte = f.tostring()
            
            # create marker byte array
            nMarkers = len(data.markers)
            hdr_marker = Struct("<LlLl") # marker: nSize, nPosition, nPoints, nChannel + sTypeDesc
            mkrbyte = bytearray()
            for marker in data.markers:
                mdescription = marker.description.encode("utf-8") + "\0"
                mtype = marker.type.encode("utf-8") + "\0"
                msize = hdr_marker.size + len(mdescription) + len(mtype)
                mpos = marker.position - data.sample_channel[0][0] # marker position must be relative to this data block
                mpos = long(np.int64(mpos))
                mkr = bytearray(hdr_marker.pack(msize, mpos, long(marker.points), marker.channel))
                mkr.extend(mtype)
                mkr.extend(mdescription)
                mkrbyte.extend(mkr)

            # create message header
            hdr_start = Struct(self.hdr+ "LLL")      # data32: nBlock, nPoints, nMarkers + data + marker
            blocksize = hdr_start.size + len(databyte) + len(mkrbyte)
            hdrbyte = bytearray(hdr_start.pack(self.GUID, blocksize, type, self.blockcount, nPoints, nMarkers))

            # add data part
            hdrbyte.extend(databyte)
            hdrbyte.extend(mkrbyte)
            return hdrbyte 

        elif type == RDAMessageType.IMP_START:
            # create message header
            hdr_start = Struct(self.hdr)      
            blocksize = hdr_start.size
            hdrbyte = bytearray(hdr_start.pack(self.GUID, blocksize, type))
            return hdrbyte

        elif type == RDAMessageType.IMP_DATA:
            # create impedance data byte array
            nChannels = len(data.impedances)
            hdr_imp = Struct("<ffi") # impedance: fXPosition, fYPosition, nImpedance + suElectrodeName
            impbyte = bytearray()
            
            gndImpedance = None
            nChannels = 0
            for idx, ch in enumerate(self.params.channel_properties):
                fXPosition = (idx % 10) * 0.05 + 0.5
                fYPosition = (idx / 10) * 0.05 + 0.05
                valD = None
                valR = None
                # impedance value for data electrode available?
                if self.params.eeg_channels[idx, ImpedanceIndex.DATA] == 1:
                    valD = self._getImpedanceValue(data.eeg_channels[idx, ImpedanceIndex.DATA])

                # impedance value for reference electrode available?
                if self.params.eeg_channels[idx, ImpedanceIndex.REF] == 1:
                    valR = self._getImpedanceValue(data.eeg_channels[idx, ImpedanceIndex.REF])
                
                if valD != None:
                    if valR != None:
                        channelName =  ch.name + "+"
                    else:
                        channelName = ch.name
                    suElectrodeName = unicode(channelName).encode("utf-16le") + "\0\0"
                    imp = self._packImpedance(nChannels, valD, suElectrodeName)
                    impbyte.extend(imp)
                    nChannels += 1
                        
                if valR != None:
                    channelName = ch.name + "-"
                    suElectrodeName = unicode(channelName).encode("utf-16le") + "\0\0"
                    imp = self._packImpedance(nChannels, valR, suElectrodeName)
                    impbyte.extend(imp)
                    nChannels += 1

                
                # take the first available GND impedance
                if gndImpedance == None and self.params.eeg_channels[idx, ImpedanceIndex.GND] == 1:
                    gndImpedance = self._getImpedanceValue(data.eeg_channels[idx, ImpedanceIndex.GND])

            if gndImpedance != None:
                channelName = "GND"
                suElectrodeName = unicode(channelName).encode("utf-16le") + "\0\0"
                imp = self._packImpedance(nChannels, gndImpedance, suElectrodeName)
                impbyte.extend(imp)
                nChannels += 1
                
            # create message header
            hdr_start = Struct(self.hdr+ "L")      # Imp_Data: nChannels + impedance data
            blocksize = hdr_start.size + len(impbyte)
            hdrbyte = bytearray(hdr_start.pack(self.GUID, blocksize, type, nChannels))

            # add data part
            hdrbyte.extend(impbyte)
            return hdrbyte 

        elif type == RDAMessageType.IMP_STOP:
            # create message header
            hdr_start = Struct(self.hdr)      
            blocksize = hdr_start.size
            hdrbyte = bytearray(hdr_start.pack(self.GUID, blocksize, type))
            return hdrbyte
        
        elif type == RDAMessageType.INFO:
            channels = len(data.channel_properties)
            samplingInterval = 1.0e6 / data.sample_rate     # sampling interval in us
            
            # recorder version
            version = 2.0
            
            # create resolution byte array (we have a resolution of 1uV for all channels)
            res = [1.0] * channels
            resbyte = pack("<" + "d" * channels, *res)
            
            # create channel names byte array (null terminated strings)
            chn =[]
            for channel in data.channel_properties:
                chn.append(unicode(channel.name))
            chnbyte = "\0".join(chn) + "\0"    
            chnwbyte = chnbyte.encode("utf-16-le")
            
            # create channel unit byte array (null terminated strings)
            unit = [u"µV"] * channels
            unitbyte = "\0".join(unit) + "\0" 
            unitwbyte = unitbyte.encode("utf-16-le")

            # create message header
            hdr_start = Struct(self.hdr+ "dLd")      # start: dRecorderVersion, nChannels, dSamplingInterval + data
            blocksize = hdr_start.size + len(resbyte) + len(chnwbyte) + len(unitwbyte)
            hdrbyte = bytearray(hdr_start.pack(self.GUID, blocksize, type, version, channels, samplingInterval))
            
            # add data part
            hdrbyte.extend(resbyte)
            hdrbyte.extend(chnwbyte)
            hdrbyte.extend(unitwbyte)
            return hdrbyte 
            
        elif type == RDAMessageType.NEWSTATE:
            hdr_start = Struct(self.hdr + "i")      
            blocksize = hdr_start.size
            hdrbyte = bytearray(hdr_start.pack(self.GUID, blocksize, type, data))
            return hdrbyte

        elif type == RDAMessageType.KEEP_ALIVE:
            # create message header
            hdr_start = Struct(self.hdr)      
            blocksize = hdr_start.size
            hdrbyte = bytearray(hdr_start.pack(self.GUID, blocksize, type))
            return hdrbyte
        
        elif type == 0:
            hdr_start = Struct(self.hdr + "ii10s")      
            blocksize = hdr_start.size
            hdrbyte = bytearray(hdr_start.pack(self.GUID, blocksize, 100000, 1, 3, u"TEST\0".encode("utf-16")))
            return hdrbyte
        
    def _getImpedanceValue(self, impedance):
        if impedance >= CHAMP_IMP_INVALID:
            nImpedance = -1
        else:
            nImpedance = (impedance + 500) / 1000
        return nImpedance
        
    def _packImpedance(self, number, value, name):
        fXPosition = (number % 10) * 0.05 + 0.5
        fYPosition = (number / 10) * 0.05 + 0.05
        hdr_imp = Struct("<ffi") # impedance: fXPosition, fYPosition, nImpedance + suElectrodeName
        imp = bytearray(hdr_imp.pack(fXPosition, fYPosition, value))
        imp.extend(name)
        return imp
        
class ClientConnection():
    ''' Object holding a connected client
    '''
    def __init__(self, clientsock, addr):
        ''' Create data transmit thread
        @param clientsock: client socket
        @param addr: client IP address 
        '''
        self.sock = clientsock
        self.addr = addr
        self.transmit_queue = Queue.Queue(20)
        # start transmit thread
        self.connected = True
        self.clientthread = threading.Thread(target=self._transmit_thread)
        self.clientthread.start()
        
    def terminate(self):
        ''' Shut down client socket
        '''
        if self.connected:
            self.connected = False
            self.clientthread.join(5.0)
        self.sock.close()
        
    def send(self, message):
        ''' Put the message into the transmit queue
        '''
        if self.connected:
            self.transmit_queue.put(message, False)
    
    def _transmit_thread(self):
        ''' Get data from queue and send it over TCP/IP
        '''
        while self.connected:
            try:
                # get data from queue
                data = self.transmit_queue.get(False)
                # send it to client
                totalsent = 0
                while totalsent < len(data):
                    rd, wr, err = select([],[self.sock],[], 0.05)
                    if len(wr) > 0:
                        sent = self.sock.send(data[totalsent:])
                        if sent == 0:
                            raise RuntimeError, "socket connection broken"
                        totalsent = totalsent + sent
                
            except Queue.Empty:
                time.sleep(0.002)        # suspend thread (default = 2ms)
            except Exception as e:
                self.connected = False
        
        
        
        
                