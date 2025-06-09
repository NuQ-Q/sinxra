import socket
import threading
import time
import uuid
from pynput import keyboard, mouse
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Button, Controller as MouseController

class KeyboardMirrorClient:
    def __init__(self, server_ip):
        self.peer_id = str(uuid.uuid4())[:8]
        self.server_ip = server_ip
        self.port = 5555
        self.running = True
        self.keyboard = KeyboardController()
        self.mouse = MouseController()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.users_online = 0
        self.is_emulating = False  

        
        self.keys_to_mirror = {
            
            keyboard.Key.space: 'space',
            keyboard.Key.enter: 'enter',
            keyboard.Key.tab: 'tab',
            
            # Цифровые клавиши
            keyboard.KeyCode.from_char('1'): '1',
            keyboard.KeyCode.from_char('2'): '2',
            keyboard.KeyCode.from_char('3'): '3',
            keyboard.KeyCode.from_char('4'): '4',
            
            # Буквенные клавиши
            keyboard.KeyCode.from_char('b'): 'b',
            keyboard.KeyCode.from_char('r'): 'r',
            
            # Кнопка мыши
            'lmb': 'lmb'
        }

        self.connect_to_server()
        threading.Thread(target=self.receive_messages, daemon=True).start()

    def connect_to_server(self):
        while self.running:
            try:
                print(f"[{self.peer_id}] Подключение к серверу {self.server_ip}...")
                self.socket.connect((self.server_ip, self.port))
                self.socket.send(self.peer_id.encode('utf-8'))
                print(f"[{self.peer_id}] Успешно подключен к серверу")
                return
            except Exception as e:
                print(f"[{self.peer_id}] Ошибка подключения: {e}. Повтор через 5 сек...")
                time.sleep(5)

    def receive_messages(self):
        while self.running:
            try:
                data = self.socket.recv(1024).decode('utf-8')
                if not data:
                    print(f"[{self.peer_id}] Сервер разорвал соединение")
                    self.reconnect()
                    break

                if data.startswith("COUNT:"):
                    self.users_online = int(data.split(":")[1])
                    print(f"[{self.peer_id}] Пользователей онлайн: {self.users_online}")
                elif data.startswith("FROM:") and ":KEY:" in data:
                    _, sender_id, _, key = data.split(":", 3)
                    if sender_id != self.peer_id:  
                        print(f"[{self.peer_id}] Получено действие от {sender_id}: {key}")
                        self.emulate_action(key)
            except Exception as e:
                print(f"[{self.peer_id}] Ошибка приема: {e}")
                self.reconnect()
                break

    def reconnect(self):
        if not self.running:
            return
        print(f"[{self.peer_id}] Переподключение...")
        self.socket.close()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect_to_server()
        threading.Thread(target=self.receive_messages, daemon=True).start()

    def send_action(self, key):
        if not self.running or self.is_emulating: 
            return
        try:
            message = f"FROM:{self.peer_id}:KEY:{key}"
            self.socket.send(message.encode('utf-8'))
        except Exception as e:
            print(f"[{self.peer_id}] Ошибка отправки: {e}")
            self.reconnect()

    def emulate_action(self, key):
        self.is_emulating = True  
        try:
            if key == 'lmb':
                self.mouse.press(Button.left)
                time.sleep(0.05)
                self.mouse.release(Button.left)
            elif key in ['1', '2', '3', '4', 'b', 'r']:
                
                self.keyboard.press(key)
                time.sleep(0.05)
                self.keyboard.release(key)
            else:
                
                k = getattr(Key, key)
                self.keyboard.press(k)
                time.sleep(0.05)
                self.keyboard.release(k)
        except Exception as e:
            print(f"[{self.peer_id}] Ошибка эмуляции: {e}")
        finally:
            self.is_emulating = False  

    def on_press(self, key):
        try:
            
            if key in self.keys_to_mirror and not self.is_emulating:
                self.send_action(self.keys_to_mirror[key])
            elif hasattr(key, 'char') and key.char in ['1', '2', '3', '4', 'b', 'r'] and not self.is_emulating:
                
                self.send_action(key.char)
        except Exception as e:
            print(f"[{self.peer_id}] Ошибка обработки клавиши: {e}")

    def on_click(self, x, y, button, pressed):
        if not self.is_emulating and button == mouse.Button.left and pressed:
            self.send_action('lmb')

    def run(self):
        print(f"[{self.peer_id}] Клиент запущен. ID: {self.peer_id}")
        print("Поддерживаемые клавиши: Space, Enter, Tab, 1-4, b, r, LMB")

        keyboard_listener = keyboard.Listener(on_press=self.on_press)
        mouse_listener = mouse.Listener(on_click=self.on_click)

        keyboard_listener.start()
        mouse_listener.start()

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"[{self.peer_id}] Остановка...")
            self.running = False
            keyboard_listener.stop()
            mouse_listener.stop()
            self.socket.close()

if __name__ == "__main__":
    server_ip = input("Введите IP сервера: ").strip()
    client = KeyboardMirrorClient(server_ip)
    client.run()