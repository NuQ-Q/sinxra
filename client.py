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
        self.socket = None
        self.users_online = 0
        self.connection_active = False

        # Клавиши для зеркалирования (добавлены 'r' и 'g')
        self.keys_to_mirror = {
            keyboard.Key.space: 'space',
            keyboard.Key.enter: 'enter',
            keyboard.Key.tab: 'tab',
            keyboard.Key.esc: 'esc',
            'r': 'r',  # Добавлена клавиша R
            'g': 'g',  # Добавлена клавиша G
            'lmb': 'lmb'
        }

        self.connect_to_server()
        threading.Thread(target=self.receive_messages, daemon=True).start()

    def connect_to_server(self):
        while self.running and not self.connection_active:
            try:
                print(f"[{self.peer_id}] Подключение к серверу {self.server_ip}...")
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(5)
                self.socket.connect((self.server_ip, self.port))
                self.socket.send(self.peer_id.encode('utf-8'))
                self.connection_active = True
                print(f"[{self.peer_id}] Успешно подключен к серверу")
                print(f"[{self.peer_id}] Ваш ID: {self.peer_id}")
            except Exception as e:
                print(f"[{self.peer_id}] Ошибка подключения: {e}")
                if self.running:
                    print(f"[{self.peer_id}] Повторная попытка через 5 секунд...")
                    time.sleep(5)

    def receive_messages(self):
        while self.running:
            try:
                if not self.connection_active:
                    time.sleep(1)
                    continue

                data = self.socket.recv(1024)
                if not data:
                    print(f"[{self.peer_id}] Соединение с сервером разорвано")
                    self.reconnect()
                    continue

                data = data.decode('utf-8').strip()
                if data.startswith("COUNT:"):
                    self.users_online = int(data.split(":")[1])
                    print(f"[{self.peer_id}] Пользователей онлайн: {self.users_online}")
                elif data.startswith("FROM:") and ":KEY:" in data:
                    _, sender_id, _, key = data.split(":", 3)
                    if sender_id != self.peer_id:
                        print(f"[{self.peer_id}] Получено действие от {sender_id}: {key}")
                        self.emulate_action(key)

            except socket.timeout:
                continue
            except Exception as e:
                print(f"[{self.peer_id}] Ошибка приема данных: {e}")
                self.reconnect()

    def reconnect(self):
        if not self.running:
            return
        
        self.connection_active = False
        try:
            self.socket.close()
        except:
            pass
        
        print(f"[{self.peer_id}] Переподключение к серверу...")
        self.connect_to_server()

    def send_action(self, key):
        if not self.connection_active:
            return

        try:
            message = f"FROM:{self.peer_id}:KEY:{key}"
            self.socket.send(message.encode('utf-8'))
        except Exception as e:
            print(f"[{self.peer_id}] Ошибка отправки действия: {e}")
            self.reconnect()

    def emulate_action(self, key):
        try:
            if key == 'lmb':
                self.mouse.press(Button.left)
                time.sleep(0.05)
                self.mouse.release(Button.left)
            elif key in ['r', 'g']:  # Обработка буквенных клавиш
                self.keyboard.press(key)
                time.sleep(0.05)
                self.keyboard.release(key)
            else:
                k = getattr(Key, key, None)
                if k:
                    self.keyboard.press(k)
                    time.sleep(0.05)
                    self.keyboard.release(k)
        except Exception as e:
            print(f"[{self.peer_id}] Ошибка эмуляции действия: {e}")

    def on_press(self, key):
        try:
            # Обработка обычных символов
            if hasattr(key, 'char') and key.char in ['r', 'g']:
                self.send_action(key.char)
            # Обработка специальных клавиш
            elif key in self.keys_to_mirror:
                self.send_action(self.keys_to_mirror[key])
        except Exception as e:
            print(f"[{self.peer_id}] Ошибка обработки клавиши: {e}")

    def on_click(self, x, y, button, pressed):
        if button == mouse.Button.left and pressed:
            self.send_action('lmb')

    def run(self):
        print(f"[{self.peer_id}] Клиент запущен. Для выхода нажмите Ctrl+C")

        keyboard_listener = keyboard.Listener(on_press=self.on_press)
        mouse_listener = mouse.Listener(on_click=self.on_click)

        keyboard_listener.start()
        mouse_listener.start()

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n[{self.peer_id}] Остановка клиента...")
            self.running = False
            keyboard_listener.stop()
            mouse_listener.stop()
            try:
                self.socket.close()
            except:
                pass
            print(f"[{self.peer_id}] Клиент остановлен")

if __name__ == "__main__":
    server_ip = input("Введите IP-адрес сервера: ").strip()
    client = KeyboardMirrorClient(server_ip)
    client.run()