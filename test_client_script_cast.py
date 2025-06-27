# test_client_script_cast.py
import socket
import time

HOST = "127.0.0.1"
PORT = 4000
DELAY = 0.7

TARGET_MOB_NAME = "Training Dummy" # Or "Rat" or another known mob in start

def send_cmd(sock, message, silent=False):
    if not silent: print(f"Sending: {message.strip()}")
    sock.sendall((message + "\r\n").encode())
    time.sleep(DELAY)
    try:
        sock.recv(8192).decode(errors='ignore')
    except socket.timeout:
        pass
    except Exception:
        pass

def run_cast_test():
    print("\n--- Test: Wizard Fire Bolt ---")
    # Part 1: Wizard
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST, PORT))
            s.settimeout(3)
            time.sleep(DELAY)

            send_cmd(s, "NEW")
            send_cmd(s, "CasterUser")
            send_cmd(s, "casterpass")
            send_cmd(s, "casterpass")
            send_cmd(s, "Zappy")

            send_cmd(s, "High Elf")
            send_cmd(s, "yes")

            send_cmd(s, "Wizard")
            send_cmd(s, "yes")

            send_cmd(s, "sheet")
            print(f"INFO: Wizard L1 attempting 'cast \"fire bolt\" {TARGET_MOB_NAME}' (1st time)")
            send_cmd(s, f'cast "fire bolt" {TARGET_MOB_NAME}')

            print(f"INFO: Wizard L1 attempting 'cast \"fire bolt\" {TARGET_MOB_NAME}' again (should fail - action taken)")
            send_cmd(s, f'cast "fire bolt" {TARGET_MOB_NAME}')

            print("INFO: Wizard L1 attempting 'look' (should succeed - no action cost)")
            send_cmd(s, "look")

            print(f"INFO: Wizard L1 attempting 'cast \"fire bolt\" {TARGET_MOB_NAME}' again (should succeed - new turn)")
            send_cmd(s, f'cast "fire bolt" {TARGET_MOB_NAME}')

            print("INFO: Wizard L1 attempting 'cast \"fire bolt\"' (no target - should show usage)")
            send_cmd(s, 'cast "fire bolt"')


        except ConnectionRefusedError:
            print("CAST TEST (Wizard L1): Connection refused. Is the server running?")
            return False
        except Exception as e:
            print(f"Error during Cast Test (Wizard L1): {e}")
            return False
    print("--- Wizard L1 Cast test input sequence sent ---\n")

    time.sleep(2)

    # Part 2: Fighter (Non-Wizard)
    print("\n--- Test: Non-Wizard (Fighter) Cast ---")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST, PORT))
            s.settimeout(3)
            time.sleep(DELAY)

            send_cmd(s, "NEW")
            send_cmd(s, "NonCasterUser")
            send_cmd(s, "fighterpass")
            send_cmd(s, "fighterpass")
            send_cmd(s, "Bruiser")

            send_cmd(s, "Human")
            send_cmd(s, "yes")

            send_cmd(s, "Fighter")
            send_cmd(s, "yes")

            print(f"INFO: Attempting 'cast \"fire bolt\" {TARGET_MOB_NAME}' as Fighter (should fail)")
            send_cmd(s, f'cast "fire bolt" {TARGET_MOB_NAME}')
            send_cmd(s, "sheet")

        except ConnectionRefusedError:
            print("CAST TEST (Fighter): Connection refused.")
            return False
        except Exception as e:
            print(f"Error during Cast Test (Fighter): {e}")
            return False
    print("--- Non-Wizard (Fighter) Cast test input sequence sent ---")
    return True


if __name__ == "__main__":
    success = run_cast_test()
    if success:
        print("\nTest script for Cast finished sending inputs. Check server logs for detailed behavior and any errors.")
    else:
        print("\nTest script for Cast encountered an error.")
