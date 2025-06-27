# test_client_script_rest.py
import socket
import time

HOST = "127.0.0.1"
PORT = 4000
DELAY = 0.7 # Increased delay slightly for server processing

def send_cmd(sock, message):
    print(f"Sending: {message.strip()}")
    sock.sendall((message + "\r\n").encode())
    time.sleep(DELAY)
    # Basic recv to clear buffer, not for detailed validation here
    try:
        sock.recv(8192).decode(errors='ignore') # Read more data
    except socket.timeout:
        pass # Expected if server doesn't respond immediately to all
    except Exception:
        pass


def run_rest_test():
    print("\n--- Test: Fighter Rest and Second Wind ---")
    # Part 1: Create char, use SW, rest, use SW again
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST, PORT))
            s.settimeout(3)
            time.sleep(DELAY)

            send_cmd(s, "NEW")
            send_cmd(s, "RestTestUser")
            send_cmd(s, "testpass")
            send_cmd(s, "testpass")
            send_cmd(s, "RestyFighter")

            send_cmd(s, "Human")
            send_cmd(s, "yes")

            send_cmd(s, "Fighter")
            send_cmd(s, "yes")

            send_cmd(s, "sheet")
            print("INFO: Using Second Wind (1st time, at full HP)")
            send_cmd(s, "secondwind")
            print("INFO: Attempting Second Wind again (should fail)")
            send_cmd(s, "secondwind")

            print("INFO: Resting...")
            send_cmd(s, "rest")
            send_cmd(s, "sheet") # Check HP after rest

            print("INFO: Attempting Second Wind after rest (should succeed)")
            send_cmd(s, "secondwind")
            send_cmd(s, "sheet") # Check HP after second SW

        except ConnectionRefusedError:
            print("REST TEST (Part 1): Connection refused. Is the server running?")
            return False
        except Exception as e:
            print(f"Error during Rest Test (Part 1): {e}")
            return False
    print("--- Rest Test Part 1 input sequence sent ---\n")

    time.sleep(2) # Give server time to process logout/save

    # Part 2: Login, check SW persistence, rest, use SW
    print("--- Test: Rest and Second Wind (Part 2 - Post Login) ---")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST, PORT))
            s.settimeout(3)
            time.sleep(DELAY)

            send_cmd(s, "RestTestUser")
            send_cmd(s, "testpass")

            send_cmd(s, "sheet")
            print("INFO: Attempting Second Wind immediately after login (should fail as used state persists)")
            send_cmd(s, "secondwind")

            print("INFO: Resting again...")
            send_cmd(s, "rest")
            send_cmd(s, "sheet")

            print("INFO: Attempting Second Wind after 2nd rest (should succeed)")
            send_cmd(s, "secondwind")
            send_cmd(s, "sheet")


        except ConnectionRefusedError:
            print("REST TEST (Part 2): Connection refused.")
            return False
        except Exception as e:
            print(f"Error during Rest Test (Part 2): {e}")
            return False

    print("--- Rest Test Part 2 input sequence sent ---")
    return True


if __name__ == "__main__":
    success = run_rest_test()
    if success:
        print("\nTest script for rest finished sending inputs. Check server logs for detailed behavior and any errors.")
    else:
        print("\nTest script for rest encountered an error.")
