#!/usr/bin/python3 -u
import socket
# import signal

TCP_IP = '127.0.0.1'
TCP_PORT = 5005
BUFFER_SIZE = 20  # Normally 1024, but we want fast response

# def signal_handler(signum, frame):
    # global running
    # print("Exiting")
    # running = False

# running = True

# signal.signal(signal.SIGINT, signal_handler)
# signal.signal(signal.SIGTERM, signal_handler)

while 1:
    print('inphasebridge started')
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((TCP_IP, TCP_PORT))
    s.listen(1)

    conn, addr = s.accept()
    print('Connection address:', addr)
    while 1:
        data = conn.recv(BUFFER_SIZE)
        if not data: 
            break
        print("received data:", data)
        conn.send(data)  # echo
    conn.close()
   # if not running:
       # s.shutdown()
       # s.close()
       # break
