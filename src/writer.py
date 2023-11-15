import numpy as np
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
from copy import deepcopy

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

def getNetworkCode():

    with open("networkCode.json", mode='r') as infile:
        
        networkCode = json.loads(infile.read())

    return networkCode

nC = getNetworkCode()


class Client:

    def getName(self):
        return self.name

    def write(self,data):
        nx = int(len(data)/self.N)
        message = struct.pack('<ii', nC["writer"]['update'],nx)
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
        message = struct.pack('<ii', nC["writer"]['connect'],self.N) 
        message += struct.pack('32s',self.name.encode('UTF-8'))

        self.clientTCP.sendall(message)
        code = struct.unpack('<i',self.clientTCP.recv(4))[0]
        print("connected : "+str(code))
        time.sleep(1)

    def __init__(self,N = 1):
        self.N = N
        self.port = nC["server"]["port"]
        self.ip = nC["server"]["ip"]

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
                    
                    if code == nC["writer"]["update"]:
                        N = filer["N"]
                        nMax = filer["nMax"]
                        nx = struct.unpack('<i',filer['connection'].recv(4))[0]
                        
                        while nx>nMax:
                            packed = filer['connection'].recv(N*nMax*8)
                            print("nx : "+str(nx)+" packed : "+str(len(packed)))
                            data = struct.unpack(N*nMax*'d',packed)
                            self.writeData(filer["path"] + "/" + filer["name"],N,data)
                            nx -= nMax
                        packed = filer['connection'].recv(N*nx*8)
                        data = struct.unpack(N*nx*'d',packed)
                        self.writeData(filer["path"] + "/" + filer["name"],N,data)
                    elif code != nC["writer"]['close']:
                        del filer
                        
                except Exception as ex:

                    if self.verbosity:
                        traceback.print_exception(type(ex), ex, ex.__traceback__)
                        
                    
            time.sleep(.01)

    def register(self,connection,client_address):
        connection.settimeout(100)
        code = struct.unpack('i',connection.recv(4))[0]
        print('------ code : '+ str(code))
        if code == nC["writer"]["connect"]:
            N = struct.unpack('i',connection.recv(4))[0]
            print("------ N : "+str(N))
            filePath = connection.recv(32).decode('UTF-8')
            print("------ id : "+str(filePath))
            pathed = getUUIDPath(filePath)
            path = pather(self.path0,pathed)
            name = "position.csv"
            filer = {"path" : path,"N" : N,"ip" : client_address[0],
                            "connection":connection,"name" : name,"nMax":int(np.floor(8191/N))}

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
                message = struct.pack('<i', nC["writer"]['connected'])
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

    def __init__(self,verbosity = False):
        self.verbosity = verbosity
        self.running = True
        self.path0 = nC["path"]
        self.filerList = []
        self.port = nC["server"]["port"]
        self.ip = nC["server"]["ip"]








def main():
    t0 = time.time()
    writer = Server()
    writer.start()
    while True:
        t = time.time()-t0
        time.sleep(360000)
        print(">>>>>>>>>>>> Writing Server is in service since " + str(int(t/3600)) +" hours")

if __name__ == '__main__':
    main()