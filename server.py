import socket, threading, random, pandas as pd, os, sys, re
from typing import List, Tuple

HOST = "127.0.0.1"
PORT = 65432
BACKLOG = 5
DELIM = "\n@@END@@\n"  # <-- end-of-message marker

def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())

def load_pairs(excel_path: str) -> List[Tuple[str, str]]:
    if not os.path.exists(excel_path):
        print(f"[ERROR] Excel file not found at: {excel_path}"); sys.exit(1)
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        print(f"[ERROR] Failed to read Excel file: {e}"); sys.exit(1)
    cols = {c.lower(): c for c in df.columns}
    if "country" not in cols or "capital" not in cols:
        print(f"[ERROR] Excel must contain 'Country' and 'Capital' columns. Found: {list(df.columns)}"); sys.exit(1)
    pairs = []
    for _, row in df.iterrows():
        c = str(row[cols["country"]]).strip()
        k = str(row[cols["capital"]]).strip()
        if c and k and c.lower() != "nan" and k.lower() != "nan":
            pairs.append((c, k))
    if not pairs:
        print("[ERROR] No valid (country, capital) rows in the Excel."); sys.exit(1)
    return pairs

class CapitalQuizServer:
    def __init__(self, excel_path: str, host: str = HOST, port: int = PORT):
        self.addr = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.pairs = load_pairs(excel_path)
        self.capital_to_country = {normalize(cap): country for country, cap in self.pairs}
        self.shutdown_flag = threading.Event()

    def start(self):
        self.sock.bind(self.addr); self.sock.listen(BACKLOG)
        print(f"[SERVER] Listening on {self.addr[0]}:{self.addr[1]} ...")
        try:
            while not self.shutdown_flag.is_set():
                try:
                    self.sock.settimeout(1.0)
                    conn, caddr = self.sock.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                print(f"[SERVER] Connected from {caddr}")
                self.handle_client(conn, caddr)
        finally:
            try: self.sock.close()
            except: pass
            print("[SERVER] Stopped.")

    def send_block(self, conn: socket.socket, text: str):
        try:
            conn.sendall((text + DELIM).encode("utf-8"))
        except Exception:
            pass

    def handle_client(self, conn: socket.socket, caddr):
        country, capital = random.choice(self.pairs)
        expected_norm = normalize(capital)
        max_attempts, attempts_used = 3, 0
        # initial block (2 lines)
        self.send_block(conn, f"What is the capital city of {country}?\nYour guess (or 'END' to finish): ")

        try:
            while True:
                data = conn.recv(4096)
                if not data:
                    print(f"[SERVER] {caddr} disconnected."); break
                guess_raw = data.decode("utf-8", errors="ignore").strip()
                guess_norm = normalize(guess_raw)

                if guess_raw.upper() == "END":
                    self.send_block(conn, "END received. Shutting down server. Closing connection.")
                    print("[SERVER] END received. Shutting down server.")
                    self.shutdown_flag.set()
                    break

                if guess_norm.isdigit():
                    self.send_block(conn, "Numeric input is not allowed for capital names. Connection will close.")
                    print(f"[SERVER] Numeric invalid input from {caddr}: {guess_raw}")
                    break

                if guess_norm == expected_norm:
                    self.send_block(conn, "Correct! Closing connection.")
                    print(f"[SERVER] {caddr} answered correctly for {country}.")
                    break

                # wrong attempt
                attempts_used += 1
                lines = []
                if guess_norm in self.capital_to_country:
                    other_country = self.capital_to_country[guess_norm]
                    lines.append(f"'{guess_raw}' is the capital of {other_country}, not {country}.")
                remaining = max_attempts - attempts_used
                if remaining <= 0:
                    lines.append(f"Maximum attempts reached; closing connection. The correct answer is {capital}.")
                    self.send_block(conn, "\n".join(lines))
                    print(f"[SERVER] {caddr} max attempts reached.")
                    break
                else:
                    lines.append(f"Wrong answer. Attempts Left: {remaining}.")
                    lines.append("Your guess (or 'END' to finish): ")
                    self.send_block(conn, "\n".join(lines))

        except Exception as e:
            print(f"[SERVER] Error with {caddr}: {e}")
        finally:
            try: conn.shutdown(socket.SHUT_RDWR)
            except: pass
            try: conn.close()
            except: pass
            print(f"[SERVER] Connection with {caddr} closed.")

def main():
    excel_path = sys.argv[1] if len(sys.argv) >= 2 else "country_capital_list.xlsx"
    CapitalQuizServer(excel_path, HOST, PORT).start()

if __name__ == "__main__":
    main()
