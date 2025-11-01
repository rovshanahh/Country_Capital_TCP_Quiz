import socket, sys

HOST = "127.0.0.1"
PORT = 65432
DELIM = "\n@@END@@\n"

def recv_block(sock: socket.socket) -> str:
    buf = ""
    while DELIM not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            return buf  # connection closed
        buf += chunk.decode("utf-8", errors="ignore")
    msg, _sep, _rest = buf.partition(DELIM)
    return msg

def main():
    if len(sys.argv) > 1 and sys.argv[1].lower() == "--help":
        print("Usage: python3 client.py [host] [port]"); return
    host = sys.argv[1] if len(sys.argv) >= 2 else HOST
    port = int(sys.argv[2]) if len(sys.argv) >= 3 else PORT

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))

        while True:
            msg = recv_block(s)
            if not msg:
                print("[CLIENT] Server closed the connection."); break
            print(msg)  

            if any(kw in msg for kw in [
                "Closing connection",
                "Connection will close",
                "Maximum attempts reached",
                "Correct",
                "END received. Shutting down server",
            ]):
                break

            user_input = input("> ")
            s.sendall((user_input + "\n").encode("utf-8"))

if __name__ == "__main__":
    main()





