# -*- coding: utf-8 -*-
'''
Remote Control Server

PyCorder remote control server for use with E-Prime® or Presentation® stimulus control software

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
@date: $Date: 2013-07-03 13:45:27 +0200 (Mi, 03 Jul 2013) $
@version: 1.0

B{Revision:} $LastChangedRevision: 214 $
'''
from PyQt4 import Qt
from socket import *
from select import *
import threading
import time
import sys
import Queue

from modbase import ModuleEvent
from modbase import EventType
from modbase import ErrorSeverity


class RemoteControlServer(Qt.QObject):
    ''' Receive remote commands over network via TCP/IP
    It opens a TCP/IP server on port 6700 and listens for a string as a command. 
    '''

    def __init__(self):
        ''' Initialize the server and create the accept thread
        '''
        Qt.QObject.__init__(self)
        self._object_name = "RemoteControlServer"
        self.clients = []               #: list of connected clients
        self.blockcount = 0             #: number of received data blocks
        self.feedbackEnabled = False    #: enable feedback to attached client
        
        self._thServerLock = threading.Lock()
        self.postponed = []
        
        # create server socket
        self.HOST = '0.0.0.0'
        self.PORT = 6700
        self.ADDR = (self.HOST, self.PORT)
        self.serversock = socket(AF_INET, SOCK_STREAM)
        try:
            self.serversock.bind(self.ADDR)
            self.serversock.setblocking(0)
            self.serversock.listen(2)
        except:
            raise Exception("Remote Control Server: another TCP/IP server is already running on this port: %d\r\n"%(self.PORT) +
                            "Maybe there is already a running instance of BrainVision PyCorder "
                            "or Remote Control for BrainVision Recoder.\n"
                            "Remote Control support will be not available for this session!")

        # create server thread
        self.serverthread_running = True
        self.serverthread = threading.Thread(target=self._accept_thread)
        self.serverthread.start()
        
        # recording started from remote control
        self.remoteRecording = False
        
        # initialize state variables
        self.resetControlState()
        
    def resetControlState(self):
        ''' Clear out the remote control state variables
        '''
        self.S_ConfigurationFile = ""
        self.S_SubjectID = ""
        self.S_ExperimentNr = ""

    def isInitialized(self):
        ret = (len(self.S_ConfigurationFile) > 0) &\
              (len(self.S_ExperimentNr) > 0) &\
              (len(self.S_SubjectID) > 0)
        return ret  

    def isClientConnected(self):
        ''' Check for a client connection
        '''
        return len(self.clients) > 0
            
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
        
    def send_event(self, event):
        ''' Send ModuleEvent objects to all connected slots.
        @param event: ModuleEvent object
        '''
        self.emit(Qt.SIGNAL('event(PyQt_PyObject)'), event)
        
    def send_feedback(self, feedback):
        ''' send feedback to attached client
        '''
        if not self.feedbackEnabled:
            return
        # prepare feedback string
        feedback = feedback.replace("\r", "")
        feedback = feedback.replace("\n", "")
        feedback = (feedback + "\r\n").encode("utf-8")
        for client in self.clients[:]:
            client.send(feedback)
        
    def postpone_feedback(self, cmd):
        self.postponed.append(cmd)
    
    
    def _accept_thread(self):
        ''' Server socket accept client connections
        '''
        while self.serverthread_running:
            # waiting for connection
            rd, wr, err = select([self.serversock],[],[], 0.2)
            if len(rd) > 0:
                # we want only one client connection
                if len(self.clients) > 0:
                    addr = self.clients[0].addr
                    self.send_event(ModuleEvent(self._object_name, EventType.ERROR,
                                                "Another remote client %s is already connected"%(str(addr)),
                                                severity=ErrorSeverity.IGNORE
                                                )
                                    )
                    clientsock, addr = self.serversock.accept()
                    clientsock.close()
                else:
                    # get the client socket and create a connection object
                    clientsock, addr = self.serversock.accept()
                    client = RemoteClientConnection(clientsock, addr, self)
                    
                    if client.connected:
                        self._thServerLock.acquire()
                        self.clients.append(client)
                        self._thServerLock.release()
                        self.send_event(ModuleEvent(self._object_name, EventType.LOGMESSAGE,
                                                    "Client connected %s"%(str(addr))))

            # check connections
            self._thServerLock.acquire()
            for client in self.clients[:]:
                if not client.connected:
                    client.terminate()
                    self.clients.remove(client)
                    self.send_event(ModuleEvent(self._object_name, EventType.LOGMESSAGE,
                                                "Client disconnected %s"%(str(client.addr))))
            self._thServerLock.release()
                

class RemoteClientConnection(Qt.QObject):
    ''' Object holding a connected remote client
    '''
    def __init__(self, clientsock, addr, parent_server):
        ''' Create data transmit thread
        @param clientsock: client socket
        @param addr: client IP address 
        '''
        Qt.QObject.__init__(self)
        self.ParentServer = parent_server
        self.sock = clientsock
        self.addr = addr
        self.transmit_queue = Queue.Queue(20)
        # start receive thread
        self.connected = True
        self.clientthread = threading.Thread(target=self._receive_thread)
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
    

    def _guessEncoding(self, data):
        ''' try different encodings and convert to unicode
        '''
        # these encodings should be in most likely order to save time
        encodings = [ "utf-8", "ascii", "cp1252", "utf_16", "utf_16_be", "utf_16_le"]
        for enc in encodings:
            try:
                ucode = unicode(data, enc)
                return ucode
            except:
                if enc == encodings[-1]:
                    raise Exception("command character encoding failed")       

    def _receive_thread(self):
        ''' Get data from client and send data to client
        '''
        while self.connected:
            try:
                # wait for data
                rd, wr, err = select([self.sock],[],[self.sock], 0.05)
                if len(err) > 0:
                    # socket error
                    self.connected = False
                elif len(rd) > 0:
                    # data received
                    data = self.sock.recv(2048)
                    if len(data) == 0:
                        # connection error
                        self.connected = False
                    else:
                        try:
                            cmd = self._guessEncoding(data).strip()
                            # we don't want empty commands
                            if len(cmd) > 0:
                                self.ParentServer.send_event(ModuleEvent(self.ParentServer._object_name, 
                                                                         EventType.COMMAND, "RemoteCommand", cmd_value=cmd))
                        except Exception as e:
                            self.ParentServer.send_event(ModuleEvent(self.ParentServer._object_name, 
                                                                     EventType.ERROR, str(e), severity=ErrorSeverity.IGNORE))
                # send response to client
                if not self.transmit_queue.empty():
                    try:
                        # get data from queue
                        data = self.transmit_queue.get(False)
                        # send it to client
                        totalsent = 0
                        while totalsent < len(data):
                            rd, wr, err = select([],[self.sock],[], 0.02)
                            if len(wr) > 0:
                                sent = self.sock.send(data[totalsent:])
                                if sent == 0:
                                    raise RuntimeError, "socket connection broken"
                                totalsent = totalsent + sent
                    except Queue.Empty:
                        time.sleep(0.002)        # suspend thread (default = 2ms)
                            
            except Exception as e:
                self.connected = False
        


