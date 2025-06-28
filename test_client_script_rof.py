# test_client_script_rof.py
import socket
import time

HOST = "127.0.0.1"
PORT = 4000
DELAY = 0.8 # Slightly increased delay for server processing & potential effect messages
TARGET_MOB_NAME = "Training Dummy" # Or "Rat"

def send_cmd(sock, message, silent=False):
    if not silent: print(f"Sending: {message.strip()}")
    sock.sendall((message + "\r\n").encode())
    time.sleep(DELAY)
    try:
        # Attempt to read, but don't rely on its content for this script's pass/fail
        response_bytes = sock.recv(8192)
        # if not silent and response_bytes:
        #     print(f"Received: {response_bytes.decode(errors='ignore').strip()}")
    except socket.timeout:
        if not silent: print("Socket timeout during recv.")
        pass
    except Exception as e:
        if not silent: print(f"Recv error: {e}")
        pass

def run_rof_test():
    print("\n--- Test: Wizard Ray of Frost ---")
    # Part 1: Wizard
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST, PORT))
            s.settimeout(3)
            time.sleep(DELAY) # Initial server welcome messages

            send_cmd(s, "NEW", silent=True)
            send_cmd(s, "FrostyUser")
            send_cmd(s, "frostypass")
            send_cmd(s, "frostypass")
            send_cmd(s, "Elsa")

            send_cmd(s, "High Elf")
            send_cmd(s, "yes")

            send_cmd(s, "Wizard")
            send_cmd(s, "yes")

            send_cmd(s, "sheet")
            print(f"INFO: Wizard L1 attempting 'cast \"ray of frost\" {TARGET_MOB_NAME}' (1st time)")
            send_cmd(s, f'cast "ray of frost" {TARGET_MOB_NAME}')

            print(f"INFO: Wizard L1 attempting 'cast \"ray of frost\" {TARGET_MOB_NAME}' again (should fail - action taken)")
            send_cmd(s, f'cast "ray of frost" {TARGET_MOB_NAME}')

            print("INFO: Wizard L1 attempting 'look' (should succeed - no action cost)")
            send_cmd(s, "look")

            print(f"INFO: Wizard L1 attempting 'cast \"ray of frost\" {TARGET_MOB_NAME}' again (should succeed - new turn)")
            send_cmd(s, f'cast "ray of frost" {TARGET_MOB_NAME}')

            print("INFO: Wizard L1 attempting 'cast \"ray of frost\"' (no target - should show usage)")
            send_cmd(s, 'cast "ray of frost"')


        except ConnectionRefusedError:
            print("ROF TEST (Wizard L1): Connection refused. Is the server running?")
            return False
        except Exception as e:
            print(f"Error during ROF Test (Wizard L1): {e}")
            return False
    print("--- Wizard L1 Ray of Frost test input sequence sent ---\n")

    time.sleep(2)

    # Part 2: Fighter (Non-Wizard)
    print("\n--- Test: Non-Wizard (Fighter) Ray of Frost ---")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST, PORT))
            s.settimeout(3)
            time.sleep(DELAY)

            send_cmd(s, "NEW", silent=True)
            send_cmd(s, "NonFrostUser")
            send_cmd(s, "fighterpass")
            send_cmd(s, "fighterpass")
            send_cmd(s, "NotElsa")

            send_cmd(s, "Human")
            send_cmd(s, "yes")

            send_cmd(s, "Fighter")
            send_cmd(s, "yes")

            print(f"INFO: Attempting 'cast \"ray of frost\" {TARGET_MOB_NAME}' as Fighter (should fail)")
            send_cmd(s, f'cast "ray of frost" {TARGET_MOB_NAME}')
            send_cmd(s, "sheet")

        except ConnectionRefusedError:
            print("ROF TEST (Fighter): Connection refused.")
            return False
        except Exception as e:
            print(f"Error during ROF Test (Fighter): {e}")
            return False
    print("--- Non-Wizard (Fighter) Ray of Frost test input sequence sent ---")
    return True


if __name__ == "__main__":
    success = run_rof_test()
    if success:
        print("\nTest script for Ray of Frost finished sending inputs. Check server logs for detailed behavior and any errors.")
    else:
        print("\nTest script for Ray of Frost encountered an error.")
