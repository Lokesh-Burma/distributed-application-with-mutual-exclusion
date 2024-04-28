import grpc
from concurrent.futures import ThreadPoolExecutor
import file_storage_pb2_grpc
import file_storage_pb2
import os
import json
import threading
import hashlib
import time


class FileStorageServicer(file_storage_pb2_grpc.FileStorageServicer):
    def __init__(self):
        self.isCriticalSectionInUse = False
        self.lock = threading.Lock()
        self.pending_requests = []
        self.storage_folder = "received-files-from-content-provider"
        self.files_path = "file_info.json"
        if not os.path.exists(self.storage_folder):
            os.makedirs(self.storage_folder)
        if os.path.exists(self.files_path):
            with open(self.files_path, "r") as f:
                self.files = json.load(f)
        else:
            self.files = {}

    def RequestMutex(self, request, context):
        print(
            f"\nProcess {request.process_id} requested mutex, with token {request.token}")
        try:
            if request.process_id not in self.pending_requests:
                self.pending_requests.append(request.process_id)
                print(
                    f"Process {request.process_id} added to pending requests")

            if (self.pending_requests[0] == request.process_id and not self.isCriticalSectionInUse):
                self.lock.acquire()
                self.isCriticalSectionInUse = True
                print(
                    f"Process {request.process_id} acquired mutex")
                return file_storage_pb2.MutexResponse(granted=True, token=0)

            else:
                print(
                    f"Critical section is in use, Process {request.process_id} denied mutex")
                return file_storage_pb2.MutexResponse(granted=False, token=self.getToken(request.process_id))
        except Exception as e:
            print(e)
            return file_storage_pb2.MutexResponse(granted=False, token=self.getToken(request.process_id))

    def getToken(self, process_id):
        return self.pending_requests.index(process_id)

    def ReleaseMutex(self, request, context):
        self.isCriticalSectionInUse = False
        self.lock.release()
        if len(self.pending_requests) != 0:
            self.pending_requests.pop(0)
        print(
            f"Process {request.process_id} released mutex\n")
        return file_storage_pb2.MutexResponse(granted=True)

    def UploadFile(self, request, context):
        file_hash = self.calculate_file_hash(request.data)
        if file_hash not in self.files.values() and request.filename not in self.files.keys():
            time.sleep(60)
            with open(f"{self.storage_folder}/{request.filename}", "wb") as f:
                f.write(request.data)
            self.files[request.filename] = file_hash
            self.save_files_info()
            print(f"File {request.filename} uploaded successfully")
            return file_storage_pb2.UploadResponse(success=True, error="")
        elif request.filename in self.files.keys():
            print(f"file with same name already exists")
            return file_storage_pb2.UploadResponse(success=False, error="file with same name already exists")
        elif file_hash in self.files.values():
            print(f"file with same text data already exists")
            return file_storage_pb2.UploadResponse(success=False, error="file with same text data already exists")

    def calculate_file_hash(self, data):
        return hashlib.sha256(data).hexdigest()

    def save_files_info(self):
        with open(self.files_path, "w") as f:
            json.dump(self.files, f)

    def DownloadFile(self, request, context):
        print(f"Received Download file request {request.filename}")
        if request.filename in self.files:
            time.sleep(60)
            with open(f"{self.storage_folder}/{request.filename}", "rb") as f:
                data = f.read()
            print(f"File {request.filename} transferred successfully\n")
            return file_storage_pb2.Content(filename=request.filename, data=data)
        else:
            print(f"File {request.filename} does not exist\n")
            return file_storage_pb2.Content(filename=request.filename, data="")


if __name__ == '__main__':
    server_address = '172.31.12.146:50051'  # 'localhost:50051' for local testing

    server = grpc.server(ThreadPoolExecutor(max_workers=10))
    file_storage_pb2_grpc.add_FileStorageServicer_to_server(
        FileStorageServicer(), server)
    server.add_insecure_port(server_address)
    server.start()
    print(f"Server started listening at port {server_address}")
    server.wait_for_termination()
