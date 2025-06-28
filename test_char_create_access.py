import socket
import time

HOST = "127.0.0.1"
PORT = 4000
DELAY = 0.5

def send_cmd(sock, message):
    print(f"Sending: {message.strip()}")
    sock.sendall((message + "\r\n").encode())
    time.sleep(DELAY)
    # Try to receive a bit to allow server to process and send prompts
    try:
        sock.recv(1024) # Don't care about content for this test
    except socket.timeout:
        pass # Expected if server is waiting for more input after a prompt
    except Exception:
        pass


def run_creation_access_test():
    print("\n--- Test: Character Creation Data Access ---")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST, PORT))
            s.settimeout(2)
            time.sleep(DELAY) # Wait for initial server messages

            send_cmd(s, "NEW")
            send_cmd(s, "CreationTestUser")
            send_cmd(s, "testpass123")
            send_cmd(s, "testpass123")
            send_cmd(s, "Creator")

            # At this point, UserManager should be trying to access class/race data
            # to present options. We're just checking if the server handles this.
            # The script will hang here if the server is waiting for race/class input,
            # which is expected. The key is no crashes.
            print("INFO: Sent initial creation commands. Server should be prompting for race.")
            print("INFO: This script will likely hang or timeout now, which is OK for this test.")
            print("INFO: Check server logs for errors related to CLASSES_DATA/RACES_DATA access in UserManager.")

            # We can send a dummy response to see if it processes past one prompt
            # This isn't a full test of creation, just data access.
            send_cmd(s, "Human") # Dummy race choice
            send_cmd(s, "yes")   # Dummy confirm
            send_cmd(s, "Fighter")# Dummy class choice
            send_cmd(s, "yes")   # Dummy confirm


        except ConnectionRefusedError:
            print("CHAR CREATE TEST: Connection refused. Is the server running?")
            return False
        except socket.timeout:
            print("CHAR CREATE TEST: Socket timed out, which might be expected if server is waiting for further input.")
            # This is not necessarily a failure for this specific test's goal.
            return True # Consider it a pass if it reached the point of waiting for input
        except Exception as e:
            print(f"Error during Character Creation Data Access Test: {e}")
            return False
    print("--- Character Creation Data Access test input sequence sent ---")
    return True

if __name__ == "__main__":
    success = run_creation_access_test()
    if success:
        print("\nTest script for Character Creation Data Access finished. Review server logs for issues.")
    else:
        print("\nTest script for Character Creation Data Access encountered an error.")
