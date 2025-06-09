import socket
import threading
import time
from collections import defaultdict

class KeyboardMirrorServer:
    def __init__(self, port=5555):
        self.port = port
        self.clients = {}  
        self.running = True
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.lock = threading.Lock()

    def start(self):
        try:
            self.socket.bind(('0.0.0.0', self.port))
            self.socket.listen(5)
            print(f"[SERVER] Сервер запущен на порту {self.port}. Ожидание подключений...")
            print(f"[SERVER] Для остановки нажмите Ctrl+C")

            while self.running:
                try:
                    conn, addr = self.socket.accept()
                    threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()
                except Exception as e:
                    if self.running:
                        print(f"[SERVER] Ошибка при принятии соединения: {e}")
        except Exception as e:
            print(f"[SERVER] Критическая ошибка: {e}")
        finally:
            self.stop()

    def broadcast_count(self):
        """Отправляет всем клиентам текущее количество подключений"""
        count = len(self.clients)
        message = f"COUNT:{count}"
        with self.lock:
            disconnected = []
            for peer_id, client in self.clients.items():
                try:
                    client["conn"].send(message.encode('utf-8'))
                except Exception as e:
                    print(f"[SERVER] Ошибка отправки COUNT клиенту {peer_id}: {e}")
                    disconnected.append(peer_id)
            
            for peer_id in disconnected:
                self.remove_client(peer_id)

    def remove_client(self, peer_id):
        """Безопасное удаление клиента"""
        with self.lock:
            if peer_id in self.clients:
                try:
                    self.clients[peer_id]["conn"].close()
                except:
                    pass
                del self.clients[peer_id]
                print(f"[SERVER] Клиент {peer_id} отключен. Осталось: {len(self.clients)}")
                self.broadcast_count()

    def handle_client(self, conn, addr):
        peer_id = None
        try:
           
            peer_id = conn.recv(1024).decode('utf-8').strip()
            if not peer_id:
                print(f"[SERVER] Пустой peer_id от {addr}")
                conn.close()
                return

            with self.lock:
                self.clients[peer_id] = {"conn": conn, "addr": addr}
            
            print(f"[SERVER] Новое подключение: {peer_id} ({addr[0]})")
            print(f"[SERVER] Всего подключено: {len(self.clients)}")
            self.broadcast_count()

            while self.running:
                data = conn.recv(1024)
                if not data:
                    break

                data = data.decode('utf-8').strip()
                if data.startswith("FROM:") and ":KEY:" in data:
                    _, sender_id, _, key = data.split(":", 3)
                    print(f"[SERVER] Пересылаю действие от {sender_id}: {key}")

                    with self.lock:
                        disconnected = []
                        for pid, client in self.clients.items():
                            if pid != sender_id:  # Отправляем всем, кроме отправителя
                                try:
                                    client["conn"].send(data.encode('utf-8'))
                                except Exception as e:
                                    print(f"[SERVER] Ошибка отправки клиенту {pid}: {e}")
                                    disconnected.append(pid)
                        
                        for pid in disconnected:
                            self.remove_client(pid)

        except Exception as e:
            print(f"[SERVER] Ошибка обработки клиента {peer_id}: {e}")
        finally:
            if peer_id:
                self.remove_client(peer_id)

    def stop(self):
        print("\n[SERVER] Остановка сервера...")
        self.running = False
        with self.lock:
            for peer_id in list(self.clients.keys()):
                self.remove_client(peer_id)
        try:
            self.socket.close()
        except:
            pass
        print("[SERVER] Сервер остановлен")

if __name__ == "__main__":
    server = KeyboardMirrorServer()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()