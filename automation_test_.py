############################################### 
# this tool: Read run script and read log file content
#            to get fw version information
# Author: Ying Song
# Date:11/6/2024
###############################################

import sys
import time
from datetime import datetime
from pywinauto.application import Application

import os
import paramiko
import mmap
from scp import SCPClient

import tkinter as tk
import glob

import shutil
import zipfile


testfile = sys.argv[1]


serial_number = '0000'   #initial serial number
state = ''
assay_flag = 0
lastLogLine = 0
currentLine = 0
testcount = 5
all_done = 0

def ziplog():
    
    global serial_number
    testDataFolder='C:\GX\tools\g2testdata'
    # get date and time info
    dt_string = datetime.now().strftime("%Y%m%d%H%M")
    runInfo = 'DsTTR8CleanMod8_1min_'+ 'SN' +serial_number + '_' + dt_string 

    testDataZipFileName = runInfo + '.zip'
    if os.path.exists(testDataZipFileName):
        os.remove(testDataZipFileName)
    
    print('zip file...')
    with zipfile.ZipFile(testDataZipFileName, 'w') as myzip:
        myzip.write('log.pb')
        myzip.write('LogFile.txt')
        

def r_log(n):
   
    global serial_number
    global lastLogLine
    global state
    global assay_flag
    global all_done
    
    lastLogLine+=1
    # print("lastLogLine=",lastLogLine)    
    # print('runID=',n)

    fopen = open('LogFile.txt',mode='r+')      
    fread = fopen.readlines()

    x = 'Changed state to'
    y = '('
    z = 'GetSerialNumber: '

    assay_flag = 0
    first_idle_flag = 0
    runID = n
    
    currentLine = 0
    #lastLogLine = 0
    for line in fread:
       
        logtimestamp_start = line.find(';  ') + 1
        logtimestamp = line[logtimestamp_start : logtimestamp_start + 17]

        if currentLine >= lastLogLine:
            if runID==1 :  #first time to find serial number
                if z in line and all_done == 0:
                    #get 'serial number'
                    serial_last_4_pos = line.rfind(y) - 5
                    serial_number = line[serial_last_4_pos : serial_last_4_pos+4]                    
                    print('Get serial_number = ',serial_number)
                    all_done = 1           
            elif x in line :               
                start_pos = line.find(x) + len(x) + 1   #get (start_pos)               
                end_pos = line.rfind(y) - 1             #get (end_pos) 
                state = line[start_pos : end_pos]       #get current state
                if(state=='STATE_RUNNING_ASSAY'):                    
                    print("Assay is running")
                    assay_flag = 1
                elif((state=='STATE_ABORTING')and(assay_flag == 1)): 
                    print("Assay abort")
                    #lastLogLine=currentLine
                    print('STATE_ABORTING_currentLine=',currentLine)
                    ziplog()
                    assay_flag = 0
                    all_done = 1 
                    print(logtimestamp)                    
                    #app.window().Exit.click_input()
                    fopen.close()
                    break
                elif((state=='STATE_IDLE')and(assay_flag == 1)):
                    print("Assay done")
                    lastLogLine=currentLine
                    assay_flag = 0
                    ziplog()
                    #runID+=1
                    all_done = 1
                    print(logtimestamp)  
                    fopen.close()   
                    break
            if all_done == 1:         
                lastLogLine=currentLine
        currentLine+=1
#        print('currentLine=',currentLine)
        
def download_logs():
    gxminiFolderFullPath='/sandbox/gxmini/Logs/'
    gxminiLogPBPath='/sandbox/sicore/'
    ssh = paramiko.SSHClient() 

    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#    time.sleep(30)
    
    try:
        ssh.connect('10.11.14.2', username='root', password='')

    except TimeoutError:
        print('IP address is .3')
        ssh.connect('10.11.14.3', username='root', password='')
    
    if os.path.exists('log.pb'):
        #print("log.pb file exists.")
        os.remove("log.pb")
    if os.path.exists('LogFile.txt'):
        #print("LogFile.txt file exists.")
        os.remove("LogFile.txt")
    print('fetching file from G2...')
    with SCPClient(ssh.get_transport()) as scp:
        scp.get(gxminiLogPBPath+'log.pb')
        scp.get(gxminiFolderFullPath+'LogFile.txt')
    ssh.close()
                          

def main():
    global testfile
    global serial_number
    global lastLogLine
    global state
    global assay_flag
    global all_done
    
    app1 = Application(backend='uia').start('DTerm.exe')
    time.sleep(1)

    winTitle='DScript Terminal - v1009.002  '
    app = Application(backend= 'uia').connect(best_match=winTitle)
    time.sleep(0.5)
    app_window = app.window(best_match=winTitle)

    os.chdir('C:/GX/tools/DTerm')

    #all_done=0
    currentLine = 0
    lastLogLine=0
    runtime = datetime.now().strftime("%m/%d/%Y %H:%M:%S")  #03/03/23 09:49:36
    #print(runtime)
    runtime=runtime[:-13]+runtime[-11:]
    print(runtime)
    #print('testfile=',testfile)   #TC1057_sample_BC_assay
    run_cmd = "run " + testfile
    #print('run_cmd=',run_cmd) 
    runID=1
    count=1
    
#    while 1:
    while count < testcount:
        
        download_logs()
        r_log(runID)
        runID += 1
        
        app_window['Edit'].set_text(run_cmd)
        app_window['Enter:Button'].click_input()

        #time.sleep(10)
        #get log file to read status
        all_done = 0
        
        while all_done == 0 :
            time.sleep(60)
            download_logs()
            r_log(runID)
            #print('state=',state)
            #print('runID=',runID)
            if runID !=  1:            
                if state=='STATE_ABORTING':
                    assay_flag = 0
                    count = testcount + 1   #exit
                    break
                if state=='STATE_RUNNING_ASSAY':
                    assay_flag = 1
                if((state=='STATE_IDLE')and(assay_flag == 1)):
                    runID += 1
                    count += 1
                    assay_flag = 0
                    #print('runID_idle=',runID)
        runID += 1 
        
                # fopen = open('LogFile.txt',mode='r+')  
                
                # fread = fopen.readlines()

                # x = 'Changed state to'
                # y = '('
                # z = 'GetSerialNumber: '
                # assay_flag = 0
                # first_idle_flag = 0
                
                # currentLine = 0
                # for line in fread:
                   
                    # logtimestamp_start = line.find(';  ') + 1
                    # logtimestamp = line[logtimestamp_start : logtimestamp_start + 17]
                    # #print(logtimestamp)
                    # if currentLine >= lastLogLine and z in line:
                        # #get 'serial number'
                        # serial_last_4_pos = line.rfind(y) - 5
                        # serial_number = line[serial_last_4_pos : serial_last_4_pos+4]
                    # elif currentLine >= lastLogLine and x in line :
                    # #if logtimestamp>=runtime and x in line :

                        # #get (start_pos)
                        # start_pos = line.find(x) + len(x) + 1
                        # #get (end_pos)
                        # end_pos = line.rfind(y) - 1
                        # #get current state
                        # state = line[start_pos : end_pos]
                        # if(state=='STATE_RUNNING_ASSAY'):
                            # print("Assay is running")
                            # assay_flag = 1
                        # if((state=='STATE_ABORTING')and(assay_flag == 1)): 
                            # print("Assay abort")
                            # lastLogLine=currentLine
                            # ziplog(serial_number)
                            # all_done = 1          
                        # if((state=='STATE_IDLE')and(assay_flag == 1)):
                            # print("Assay done")
                            # lastLogLine=currentLine
                            # #zip log files
                            # ziplog(serial_number)
                            # all_done = 1
                            # #app.window().Exit.click_input()
                        
                    # currentLine+=1
                            
                # fopen.close()
            # else  #not first run 
                # print('runID=',runID,end=' ')

                # ssh = paramiko.SSHClient() 

                # ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                # time.sleep(30)
                
                # try:
                    # ssh.connect('10.11.14.2', username='root', password='')

                # except TimeoutError:
                    # print('IP address is .3')
                    # ssh.connect('10.11.14.3', username='root', password='')
                
                # if os.path.exists('log.pb'):
                    # #print("log.pb file exists.")
                    # os.remove("log.pb")
                # if os.path.exists('LogFile.txt'):
                    # #print("LogFile.txt file exists.")
                    # os.remove("LogFile.txt")
                # print('fetching file from G2...')
                # with SCPClient(ssh.get_transport()) as scp:
                    # scp.get(gxminiLogPBPath+'log.pb')
                    # scp.get(gxminiFolderFullPath+'LogFile.txt')
                # ssh.close()
           
                # fopen = open('LogFile.txt',mode='r+')  
                
                # fread = fopen.readlines()
            
pass
#main()
if __name__ == "__main__":
    main()      