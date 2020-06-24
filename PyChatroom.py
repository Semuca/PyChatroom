import errno
import select
import socket
import threading
from tkinter import *

root = Tk()
root.geometry("800x450+0+0")
root.minsize(200, 55)

history = ""

baseIP = socket.gethostbyname_ex(socket.gethostname())[-1]
port = 7000
headerLength = 10

chat = Label(root, text = history, justify = LEFT, anchor = SW, bg = "black", fg = "white", font = "Helvetica 12")
chat.pack(expand = True, fill = BOTH)

entryText = StringVar()

entry = Entry(root, bg = "black", fg = "white", insertbackground = "white", insertborderwidth = 50, font = "Helvetica 12", relief = SUNKEN, cursor = "xterm", state = DISABLED, textvariable = entryText)
entry.pack(fill = X)
entry.pack_propagate(False)

class SetupWindow:
    def __init__(self):
        self.window = Toplevel(root)
        self.window.minsize(270, 100)
        self.tab = "Join"
        self.joinTab = Button(self.window, text = "Join", command = self.ChangeStateJoin)
        self.joinTab.grid(row = 0, column = 0, sticky = W+E+N+S)
        self.setupTab = Button(self.window, text = "Host", command = self.ChangeStateSetup)
        self.setupTab.grid(row = 0, column = 1, sticky = W+E+N+S)
        self.exitButton = Button(self.window, text = "Exit", command = root.destroy)
        self.exitButton.grid(row = 0, column = 2, sticky = W+E+N+S)
        self.ipLabel = Label(self.window, text = "IP")
        self.ipLabel.grid(row = 1, column = 0)
        self.ip = StringVar()
        self.ipEntry = Entry(self.window, textvariable = self.ip)
        self.ipEntry.grid(row = 1, column = 1, sticky = W+E+N+S, columnspan = 2)
        self.setupIPLabel = Label(self.window, text = baseIP[-1])
        self.usernameLabel = Label(self.window, text = "Username")
        self.usernameLabel.grid(row = 2, column = 0)
        self.username = StringVar()
        self.usernameEntry = Entry(self.window, textvariable = self.username)
        self.usernameEntry.grid(row = 2, column = 1, sticky = W+E+N+S, columnspan = 2)
        self.activeJoinButton = Button(self.window, text = "Join!", command = self.JoinServer)
        self.activeJoinButton.grid(row = 3, column = 2, sticky = W+E+N+S)
        self.activeSetupButton = Button(self.window, text = "Host!", command = self.HostServer)
        self.window.grid_columnconfigure(0, weight = 5)
        self.window.grid_columnconfigure(1, weight = 5)
        self.window.grid_columnconfigure(2, weight = 1)

    def ChangeStateJoin(self):
        if (self.tab != "Join"):
            self.tab = "Join"
            self.activeJoinButton.grid(row = 3, column = 2, sticky = W+E+N+S)
            self.ipEntry.grid(row = 1, column = 1, sticky = W+E+N+S, columnspan = 2)
            self.activeSetupButton.grid_remove()
            self.setupIPLabel.grid_remove()

    def ChangeStateSetup(self):
        if (self.tab != "Setup"):
            self.tab = "Setup"
            self.activeJoinButton.grid_remove()
            self.ipEntry.grid_remove()
            self.activeSetupButton.grid(row = 3, column = 2, sticky = W+E+N+S)
            self.setupIPLabel.grid(row = 1, column = 1)

    def JoinServer(self):
        setupWindow.window.withdraw()
        entry.config(state = NORMAL)
        entry.bind("<Return>", self.SendMessage)
        self.socket = Client(self.ip.get(), self.username.get())

    def HostServer(self):
        setupWindow.window.withdraw()
        entry.config(state = NORMAL)
        entry.bind("<Return>", self.SendMessage)
        self.socket = Server(baseIP[-1], self.username.get())

    def SendMessage(self, event):
        message = entryText.get()
        if (message != ""):
            InsertText(f"{self.socket.username} : {message}")
            packagedMessage = message.encode("utf-8")
            messageHeader = f"{len(packagedMessage):<{headerLength}}".encode("utf-8")
            entry.delete(0, END)
            self.socket.SendMessage(messageHeader + packagedMessage)

class Server():
    def __init__(self, ip, username):
        self.username = username
        self.socketObj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socketObj.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socketObj.bind((ip, port))
        self.socketObj.listen()
        self.running = True
        self.socketList = [self.socketObj]
        self.clients = {}
        self.server = threading.Thread(target = self.Server)
        self.server.start()
        InsertText(f"Server hosted on {ip}")

    def Server(self):
        while self.running:
            readSockets, _, exceptionSockets = select.select(self.socketList, [], self.socketList)
            for notifiedSocket in readSockets:
                if (notifiedSocket == self.socketObj):
                    clientSocket, clientAddress = self.socketObj.accept()
                    user = self.ReceiveMessage(clientSocket)
                    if (user == False):
                        continue
                    self.socketList.append(clientSocket)
                    self.clients[clientSocket] = user
                    InsertText(f"{user['data'].decode('utf-8')} has joined the server")
                else:
                    message = self.ReceiveMessage(notifiedSocket)
                    if (message == False):
                        InsertText(f"{self.clients[notifiedSocket]['data'].decode('utf-8')} has left the server")
                        self.socketList.remove(notifiedSocket)
                        del self.clients[notifiedSocket]
                        continue
                    user = self.clients[notifiedSocket]
                    InsertText(f"{user['data'].decode('utf-8')} : {message['data'].decode('utf-8')}")
                    for clientSocket in self.clients:
                        if (clientSocket != notifiedSocket):
                            clientSocket.send(user["header"] + user["data"] + message["header"] + message["data"])
            for notifiedSocket in exceptionSockets:
                self.socketList.remove(notifiedSocket)
                del self.clients[notifiedSocket]
                
    def ReceiveMessage(self, clientSocket):
        try:
            messageHeader = clientSocket.recv(headerLength)
            if (len(messageHeader) == None):
                return False
            messageLength = int(messageHeader.decode("utf-8"))
            return {"header" : messageHeader, "data" : clientSocket.recv(messageLength)}
        except:
            return False

    def SendMessage(self, message):
        packagedUsername = self.username.encode("utf-8")
        usernameHeader = f"{len(packagedUsername):<{headerLength}}".encode("utf-8")
        for clientSocket in self.clients:
            clientSocket.send(usernameHeader + packagedUsername + message)
            
class Client():
    def __init__(self, ip, username):
        self.username = username
        self.running = True
        packagedUsername = username.encode("utf-8")
        usernameHeader = f"{len(packagedUsername):<{headerLength}}".encode("utf-8")
        self.socketObj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socketObj.connect((ip, port))
        self.socketObj.send(usernameHeader + packagedUsername)
        InsertText(f"Connected to {ip}")
        self.client = threading.Thread(target = self.Client)
        self.client.start()

    def Client(self):
        while self.running:
            try:
                usernameHeader = self.socketObj.recv(headerLength)
                if (len(usernameHeader) == None):
                    InsertText("The server has disconnected")
                usernameLength = int(usernameHeader.decode("utf-8"))
                username = self.socketObj.recv(usernameLength).decode("utf-8")
                messageHeader = self.socketObj.recv(headerLength)
                messageLength = int(messageHeader.decode("utf-8"))
                message = self.socketObj.recv(messageLength).decode("utf-8")
                InsertText(f"{username} : {message}")
            except IOError as e:
                if (e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK):
                    root.destroy()
                continue
            except:
                root.destroy()

    def SendMessage(self, message):
        self.socketObj.send(message)

def InsertText(newText):
    global history
    history = f"{history}\n {newText}"
    chat.configure(text = history)
    
setupWindow = SetupWindow()

root.mainloop()
