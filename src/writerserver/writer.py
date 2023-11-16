# MIT License

# Copyright (c) 2021 Renaud Bastien

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import socket
import time
import threading
import struct
import traceback
import sys
import re
import json
import uuid
import os



codes = {"connect" : 4200, "connected" : 4201, "update" : 4202, "close" : 4203,
         "path" : 4205, "fileName" : 4206, "setNumber" : 4207}

def getUUID():
    return uuid.uuid4().hex

def getUUIDPath(uu):
    return [uu[0:2],uu[2:4],uu[4:6],uu[6:8],uu[8:]]

def pather(path,params = []):
    if not os.path.exists(path):
        os.makedirs(path)
    for param in params:
        path = path + '/' + str(param)
        if not os.path.exists(path):
            os.makedirs(path)
    return path

class Client:

    def getName(self):
        return self.name

    def write(self,data):
        nx = int(len(data)/self.N)
        message = struct.pack('<ii', codes['update'],nx)
        message += struct.pack(len(data)*'d',*data)
        self.clientTCP.sendall(message)


    def start(self):
        while not self.binded:
            try:
                self.clientTCP.connect((self.ip,self.port))
                self.binded = True
            except:
                print('- Give Status -- connection failed')
                self.binded = False   
                time.sleep(2)
        message = struct.pack('<ii', codes['connect'],self.N) 
        message += struct.pack('32s',self.name.encode('UTF-8'))

        self.clientTCP.sendall(message)
        code = struct.unpack('<i',self.clientTCP.recv(4))[0]
        print("connected : "+str(code))
        time.sleep(1)

    def stop(self):
        message = struct.pack('<i', codes['close'])
        self.clientTCP.sendall(message)

    def __init__(self,N = 1,ip = "localhost",port = 1234):
        self.N = N
        self.port = port
        self.ip = ip

        self.binded = False

        self.name = getUUID()

        self.clientTCP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clientTCP.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 

class Server:

    def writeData(self,path,N,data):
        nx = int(len(data)/N)
        line = ''
        for k in range(0,nx):
            line += ','.join(map(str, data[k*N:(k+1)*N]))+'\n'
        f = open(path,"a")
        f.write(line)
        f.close()

    def update(self):
        while self.running:
            for filer in self.filerList:
                try:
                    code = struct.unpack('<i',filer['connection'].recv(4))[0]
                    if code == codes["update"]:
                        N = filer["N"]
                        nx = struct.unpack('<i',filer['connection'].recv(4))[0]
                        messageLength = N*nx*8
                        receivedLength = 0
                        packed = b''
                        while receivedLength<messageLength:
                            received = filer['connection'].recv(messageLength-receivedLength)
                            receivedLength += len(received)
                            packed +=received
                        data = struct.unpack(N*nx*'d',packed)
                        self.writeData(filer["path"] + "/" + filer["name"],N,data)
                    elif code == codes['close']:
                        del filer
                        
                except Exception as ex:

                    if self.verbosity:
                        traceback.print_exception(type(ex), ex, ex.__traceback__)
                        
                    
            time.sleep(.01)

    def register(self,connection,client_address):
        connection.settimeout(.1)
        code = struct.unpack('i',connection.recv(4))[0]
        print('------ code : '+ str(code))
        if code == codes["connect"]:
            N = struct.unpack('i',connection.recv(4))[0]
            print("------ N : "+str(N))
            filePath = connection.recv(32).decode('UTF-8')
            print("------ id : "+str(filePath))
            pathed = getUUIDPath(filePath)
            path = pather(self.path0,pathed)
            name = "position.csv"
            filer = {"path" : path,"N" : N,"ip" : client_address[0],
                            "connection":connection,"name" : name}

            return filer




    def registerNew(self,ip,port):
        backlog = 1  # how many connections to accept
        maxsize = 28
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        #server.settimeout(10)
        binded = False
        print((ip,port))
        while not binded:
            try:
                server.bind((ip,port))
                binded = True
            except Exception as ex:
                print('- Give Status -- binding failed : '+str((ip,port)))
                if self.verbosity:
                    traceback.print_exception(type(ex), ex, ex.__traceback__)
                binded = False
                time.sleep(2)
        server.listen(1)
        while self.running:
            print('--- waiting for a connection')
            try:
                connection, client_address = server.accept()
                print('------ Connection coming from ' + str(client_address))
                filer = self.register(connection,client_address)
                self.filerList.append(filer)
                message = struct.pack('<i', codes['connected'])
                filer["connection"].sendall(message)
            except Exception as ex:
                if self.verbosity:
                    traceback.print_exception(type(ex), ex, ex.__traceback__)


    def manager(self):
        registerThread = threading.Thread(target=self.registerNew, args=(self.ip, self.port,))
        registerThread.daemon = True
        registerThread.start()  



    def start(self):
        self.managerThread = threading.Thread(target=self.manager)
        self.managerThread.daemon = True
        self.managerThread.start()
        self.updateThread = threading.Thread(target=self.update)
        self.updateThread.daemon = True
        self.updateThread.start()

    def __init__(self,path = "./",ip = "localhost",port = 1234,verbosity = False):
        self.verbosity = verbosity
        self.running = True
        self.path0 = path
        self.filerList = []
        self.port = port
        self.ip = ip
