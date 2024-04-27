import grpc
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
import time
import file_storage_pb2
import file_storage_pb2_grpc
import threading

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


class FileStorageServicer(file_storage_pb2_grpc.FileStorageServicer):
    def __init__(self, node_id, num_nodes):
        self.storage_folder = "received-files-from-content-provider"
        self.files_path = "file_info.json"
        if not os.path.exists(self.storage_folder):
            os.makedirs(self.storage_folder)
        if os.path.exists(self.files_path):
            with open(self.files_path, "r") as f:
                self.files = json.load(f)
        else:
            self.files = {}
        self.request_sequence_number = 0
        self.reply_count = 0
        self.node_id = node_id
        self.num_nodes = num_nodes
        self.using = False
        self.pending_requests = []
        self.reply_received = [False] * num_nodes
        self.request_lock = threading.Lock()

    def save_files_to_disk(self):
        with open(self.files_path, "w") as f:
            json.dump(self.files, f, indent=4)

    def update_request_sequence_number(self):
        with self.request_lock:
            self.request_sequence_number += 1
            return self.request_sequence_number

    def acquire_lock(self):
        with self.request_lock:
            self.using = True
            self.reply_count = 0
            self.request_sequence_number = self.update_request_sequence_number()
            self.pending_requests = [
                self.request_sequence_number] * self.num_nodes

        for node in range(self.num_nodes):
            if node != self.node_id:
                self.send_request(node, self.request_sequence_number)

        while self.reply_count < self.num_nodes - 1:
            pass

    def send_request(self, node, sequence_number):
        request = file_storage_pb2.MutexRequest(
            sequence_number=sequence_number, node_id=self.node_id)
        with grpc.insecure_channel(f'localhost:5005{node}') as channel:
            stub = file_storage_pb2_grpc.FileStorageStub(channel)
            stub.RequestContentProviderMutex(request)

    def release_lock(self):
        self.using = False
        self.reply_received = [False] * self.num_nodes
        for node in range(self.num_nodes):
            if node != self.node_id and self.pending_requests[node] != 0:
                self.send_release(node)

    def send_release(self, node):
        request = file_storage_pb2.MutexRequest(
            sequence_number=0, node_id=self.node_id)
        with grpc.insecure_channel(f'localhost:5005{node}') as channel:
            stub = file_storage_pb2_grpc.FileStorageStub(channel)
            stub.RequestContentProviderMutex(request)

    def RequestContentProviderMutex(self, request):
        with self.request_lock:
            self.request_sequence_number = max(
                self.request_sequence_number, request.sequence_number)
            if request.sequence_number == 0:
                self.reply_received[request.node_id] = False
            else:
                self.reply_received[request.node_id] = True

            if self.using or (self.pending_requests[request.node_id] != 0 and self.pending_requests[request.node_id] < request.sequence_number) or (self.pending_requests[request.node_id] == request.sequence_number and self.node_id < request.node_id):
                self.send_reply(request.node_id)
            else:
                self.pending_requests[request.node_id] = request.sequence_number

        return file_storage_pb2.MutexResponse(granted=True)

    def send_reply(self, node):
        request = file_storage_pb2.MutexRequest(
            sequence_number=0, node_id=self.node_id)
        with grpc.insecure_channel(f'localhost:5005{node}') as channel:
            stub = file_storage_pb2_grpc.FileStorageStub(channel)
            stub.RequestContentProviderMutex(request)

    def calculate_file_hash(self, data):
        return hashlib.sha256(data).hexdigest()

    def save_file(self, filename, data):
        file_hash = self.calculate_file_hash(data)
        if file_hash not in self.files.values():
            with open(os.path.join(self.storage_folder, filename), "wb") as f:
                f.write(data)
            self.files[filename] = file_hash
            self.save_files_to_disk()
            return True  # File saved successfully
        else:
            return False  # Duplicate file found, not saved


def serve(node_id, num_nodes):
    server = grpc.server(ThreadPoolExecutor(max_workers=10))
    file_storage_pb2_grpc.add_FileStorageServicer_to_server(
        FileStorageServicer(node_id, num_nodes), server)
    server.add_insecure_port(f'localhost:5005{node_id}')
    server.start()
    print(f"Server {node_id} started at port localhost:5005{node_id}")
    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        print("Server shutting down, due to interrupt")
        server.stop(0)


if __name__ == '__main__':
    num_nodes = 3  # Change this according to the number of nodes in the system
    threads = []
    for node_id in range(num_nodes):
        thread = threading.Thread(target=serve, args=(node_id, num_nodes))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()
