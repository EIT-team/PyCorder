# -*- coding: utf-8 -*-
'''
System Check

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

import os, sys, traceback, platform
import datetime
from loadlibs import *

__version__ = "0.90.0"
'''Application Version'''

logentries = ""

def GetExceptionTraceBack():
    ''' Get last trace back info as tuple
    @return: tuple(string representation, filename, line number, module)
    '''
    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
    tb = traceback.extract_tb(exceptionTraceback)[-1]
    fn = os.path.split(tb[0])[1]
    txt = "%s, line %d, %s"%(fn, tb[1], tb[2])
    return tuple([txt, fn, tb[1], tb[2]])


def logIt(logentry):
    ''' Print and collect log entries
    @param logentry: log text 
    '''
    global logentries
    print logentry 
    logentries += logentry + "\r\n"
    
def logHeader():
    ''' Create header for log entries
    '''
    logIt("PyCorder System Check")
    logIt("=====================")
    logIt(datetime.datetime.now().strftime("%A, %d. %B %Y %I:%M%p\r\n"))
    

def checkOS():
    ''' Get operating system infos
    '''
    logIt("Operating System: %s"%(platform.platform()))
    logIt("Processor: %s"%(platform.processor()))
    logIt("Python: %s"%(sys.version))
    # required libs available?
    if len(import_log) == 0:
        # yes, print versions
        logIt("  NumPy: %s"%(np.__version__))
        logIt("  SciPy: %s"%(sc.__version__))
        logIt("  PyQt:  %s"%(Qt.QT_VERSION_STR))
        logIt("  PyQwt: %s"%(Qwt.QWT_VERSION_STR))
        logIt("  lxml:  %s"%(etree.__version__))
    else:
        logIt("One of the following modules are missing or have the wrong version:")
        logIt(import_log)
        raise Exception, "Python Libraries Missmatch"


def checkAmplifierBase():
    ''' Check amplifier base functionality
    '''
    amp = None
    logIt("ActiCHamp Base Functionality")
    try:
        log = "  Load DLL: "
        amp = ActiChamp()
        logIt(log+"OK")

        log = "  Connect HW: "
        amp.open()
        logIt(log+"OK")
        
        log = "  Initialize HW: "
        rate = CHAMP_RATE_10KHZ
        amp.setup(CHAMP_MODE_NORMAL, rate, 1)
        logIt(log+"OK")
        
        log = "  HW Configuration: "
        log += "EEG=%d, AUX=%d, TRG_IN=%d, TRG_OUT=%d "%(amp.properties.CountEeg,
                                                         amp.properties.CountAux,
                                                         amp.properties.TriggersIn,
                                                         amp.properties.TriggersOut)
        if amp.properties.CountEeg in range(32,161,32) and \
            amp.properties.CountAux == 8 and \
            amp.properties.TriggersIn == 8 and \
            amp.properties.TriggersOut == 8:
            logIt(log+"OK")
        else:
            raise Exception, "HW Configuration Missmatch"
        
        log = "  Start Acquisition: "
        amp.start()
        logIt(log+"OK")
            
        # read 2s of data
        print "  ... collecting data, please wait (~5s)" 
        log = "  Read Data: "
        eeg, trg, sct, atime, ptime, errors = readAmplifierData(amp, 2.0, 
                                                                amp.properties.CountEeg, 
                                                                amp.properties.CountAux)
        logIt(log+"OK")
        
        log = "  Stop Acquisition: "
        amp.stop()
        logIt(log+"OK")
        
        totalSamples = sct.shape[1]
        sampleTime = ptime / totalSamples
        utilization = sampleTime * sample_rate[rate] * 100
        missingSamples = (sct[0][-1] - sct[0][0] + 1) - totalSamples
        
        # check sample counter
        if missingSamples == 0:
            logIt("  Samplecounter: OK")
        else:
            logIt("  Samplecounter: %d missing samples FAILED"%(missingSamples))

        # check device errors
        if errors == 0:
            logIt("  Device Errors: 0 OK")
        else:
            logIt("  Device Errors: %d FAILED"%(errors))
        
        # check processing time
        log = "  Processing Time: %.0f%% "%(utilization)
        if utilization < 50.0:
            logIt(log + "OK")
        else:
            logIt(log + "FAILED")

        # TEST only
        if False:
            eeg[0] = 0.0
            eeg[2] *= 3.0
            eeg[5] = 0.0
            eeg[16] *= 0.8
            eeg[66] = 0.0
        
        # remove DC
        cut = 5.0 / sample_rate[rate] * 2.0
        b,a = signal.filter_design.butter(2, cut, 'high') 
        eeg = signal.lfilter(b, a, eeg)
        eeg = eeg[:,eeg.shape[1]/2:]

        # check for channels shorted and abnormal values
        rms = np.sqrt(np.mean(eeg*eeg, 1))          # calculate RMS
        rms_eeg = rms[:amp.properties.CountEeg]     # split eeg and aux channels
        rms_aux = rms[amp.properties.CountEeg:]

        #print rms_eeg
        #print rms_aux
        
        def checkRms(rms_values, rms_limit):
            # channels shorted (rms < limit)?
            mask = lambda x: (x < rms_limit)
            shorted = np.array(map(mask, rms_values))
    
            # search for abnormal values ( > +/-2*SD)
            channels_ok = np.nonzero(rms_values > rms_limit)
            num_outlier = 0
            while True:
                sd = np.std(rms_values[channels_ok])
                mean = rms_values[channels_ok].mean()
                mask = lambda x: ((x > mean + 3.0*sd) or (x < mean - 3.0*sd)) and x > rms_limit
                outlier = np.array(map(mask, rms_values))
                channels_ok = ~(shorted | outlier)
                if num_outlier == len(outlier):
                    break
                num_outlier = len(outlier)
            return shorted, outlier
                
        eeg_shorted, eeg_outlier = checkRms(rms_eeg, 0.1)    
        aux_shorted, aux_outlier = checkRms(rms_aux, 0.1)    
        
        # create channel display
        def createDispString(shorted, outlier, groupsize):
            channels = len(shorted)
            out_string = []
            for group in range(channels / groupsize):
                disp = []
                for n in range(group * groupsize, (group+1) * groupsize):
                    if n in np.nonzero(shorted)[0]:
                        disp.append("x")
                    else:
                        if n in np.nonzero(outlier)[0]:
                            disp.append("?")
                        else:
                            disp.append("-")
                out_string.append("%d  %s"%(group+1, "".join(disp)))
            return out_string
        
        log = "  Channel Data: "
        if np.any([eeg_shorted, eeg_outlier]) or np.any([aux_shorted, aux_outlier]):
            eeg_disp = createDispString(eeg_shorted, eeg_outlier, 32)
            aux_disp = createDispString(aux_shorted, aux_outlier, 8)
            log += "x=shorted, ?=outlier   FAILED"
            log += "\n    EEG channels\n       12345678901234567890123456789012\n"
            for n in range(len(eeg_disp)):
                log += "    " + eeg_disp[n] + "\n"
            log += "    AUX channels\n       12345678\n"
            log += "    " + aux_disp[0]
        else:
            log += "OK"
        logIt(log)
        
        #print eeg_shorted, eeg_outlier, aux_shorted, aux_outlier

        # close device
        log = "  Close Device: "
        amp.close()
        logIt(log+"OK")
    except Exception as e:
        logIt(log + "FAILED")
        try:
            if amp != None:
                amp.close()
        except:
            pass
        raise e

def readAmplifierData(amp, duration, eegChannels, auxChannels):
    ''' Read data stream from amplifier
    @param amp: amplifier object
    @param duration: data size in seconds
    @param eegChannels: number of eeg channels to read
    @param auxChannels: number of aux channels to read
    @return: channel data, trigger, sample counter, 
             acquisition time, processing time, device errors  
    '''
    dataChunks = int(duration / 0.05)
    # discard first second
    for n in range(0, 20):
        time.sleep(0.05)
        d, disconnected = amp.read(range(eegChannels + auxChannels),
                                   eegChannels,
                                   auxChannels)
        if d == None:
            raise Exception, "No data transfer from amplifier"
    
    # get initial error counter
    initialErrors = amp.getDeviceStatus()[1]
    
    # read data
    t = time.clock()
    processingTime = 0
    for n in range(0, dataChunks):
        time.sleep(0.05)
        tp = time.clock()
        d, disconnected = amp.read(range(eegChannels + auxChannels),
                                   eegChannels,
                                   auxChannels)
        processingTime += time.clock() - tp
        if d == None:
            raise Exception, "No data transfer from amplifier"
        if n == 0:
            eeg = d[0]
            trg = d[1]
            sct = d[2]
        else:
            eeg = np.append(eeg, d[0], 1)
            trg = np.append(trg, d[1], 1)
            sct = np.append(sct, d[2], 1)
    acquisitionTime = (time.clock()-t)*1000.0

    # get device error counter
    deviceErrors = amp.getDeviceStatus()[1] - initialErrors

    return eeg, trg, sct, acquisitionTime, processingTime, deviceErrors


    
if __name__ == '__main__':
    try:
        logHeader()
        checkOS()
        from actichamp_w import *
        from scipy import signal
        checkAmplifierBase()
        

    except Exception as e:
        tb = GetExceptionTraceBack()[0]
        logIt("\nERROR: " + tb + " -> " + str(e))
        logIt("Can't proceed system check")
    
    
    
    raw_input("\nPress RETURN to close this window ..." ) 
    sys.exit(1)
