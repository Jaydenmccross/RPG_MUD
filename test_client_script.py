# test_client_script.py
import socket
import time

HOST = "127.0.0.1"
PORT = 4000
DELAY = 0.5 # seconds

def send_and_recv(sock, message):
    print(f"Sending: {message.strip()}")
    sock.sendall((message + "\r\n").encode())
    time.sleep(DELAY)
    # For this test, we're not deeply inspecting responses, just sending.
    # In a real test client, you'd receive and parse responses.
    # try:
    #     response = sock.recv(4096).decode(errors='ignore')
    #     print(f"Received: {response.strip()}")
    #     return response
    # except socket.timeout:
    #     print("Socket timeout during recv")
    #     return ""
    # except Exception as e:
    #     print(f"Error during recv: {e}")
    #     return ""

def run_test():
    # Test 1: New Character Creation
    print("--- Test 1: New Character Creation ---")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST, PORT))
            s.settimeout(5) # Set a timeout for recv if we were using it

            time.sleep(DELAY) # Wait for initial welcome

            send_and_recv(s, "NEW")
            send_and_recv(s, "TestUserJules")
            send_and_recv(s, "password123")
            send_and_recv(s, "password123")
            send_and_recv(s, "Zarthus")

            # Race Selection - assuming "High Elf" is listed/selectable this way.
            # UserManager lists "Elf (High Elf)". Let's try that.
            send_and_recv(s, "Elf (High Elf)")
            send_and_recv(s, "yes")

            # Class Selection
            send_and_recv(s, "Wizard")
            send_and_recv(s, "yes")

            # In-game
            send_and_recv(s, "sheet")
            send_and_recv(s, "look") # Another simple command

        except ConnectionRefusedError:
            print("Connection refused. Is the server running?")
            return False
        except Exception as e:
            print(f"Error during Test 1: {e}")
            return False
    print("--- Test 1: New Character Creation input sequence sent ---\n")

    time.sleep(2) # Give server time to process logout/save

    # Test 2: Login and Verify
    print("--- Test 2: Login and Verify ---")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST, PORT))
            s.settimeout(5)
            time.sleep(DELAY)

            send_and_recv(s, "TestUserJules")
            send_and_recv(s, "password123")

            # In-game
            send_and_recv(s, "sheet")
            send_and_recv(s, "inventory")

        except ConnectionRefusedError:
            print("Connection refused for Test 2.")
            return False
        except Exception as e:
            print(f"Error during Test 2: {e}")
            return False

    print("--- Test 2: Login and Verify input sequence sent ---")
    return True

if __name__ == "__main__":
    success = run_test()
    if success:
        print("\nTest script finished sending inputs. Check server logs for errors and behavior.")
    else:
        print("\nTest script encountered an error.")
