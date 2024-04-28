import os
import grpc
import file_storage_pb2_grpc
import file_storage_pb2
import sys
import time


class ContentProviderClient:
    def __init__(self, process_id):
        self.process_id = process_id
        self.token = -1

    def connect_to_server(self, server_address):
        self.channel = grpc.insecure_channel(server_address)
        self.stub = file_storage_pb2_grpc.FileStorageStub(self.channel)
        print(
            f"Process {self.process_id} connected to server at {server_address}")

    def request_mutex(self):
        request = file_storage_pb2.RequestMutexParams(
            process_id=self.process_id, token=self.token)
        response = self.stub.RequestMutex(request)
        print(f"Process {self.process_id} got mutex: {response.granted}")
        return response.granted

    def release_mutex(self):
        request = file_storage_pb2.ReleaseMutexParams(
            process_id=self.process_id)
        response = self.stub.ReleaseMutex(request)
        print(f"Process {self.process_id} released mutex: {response.granted}")
        return response.granted

    def upload_file(self, filename, data):
        request = file_storage_pb2.Content(filename=filename, data=data)
        response = self.stub.UploadFile(request)
        if response.success:
            print(
                f"Process {os.getpid()} uploaded file '{filename}' successfully")
        else:
            print(
                f"Process {os.getpid()} failed to upload file '{filename}', {response.error}")
        return response.success


def main():
    server_address = '172.31.12.146:50051'  # 'localhost:50051 for local testing'

    content_provider = ContentProviderClient(os.getpid())
    content_provider.connect_to_server(server_address)

    if (len(sys.argv) != 3):
        print("Usage: python content_provider.py <filename> <content>")
        exit()

    filename = sys.argv[1] if sys.argv[1] else "file1.txt"
    content = sys.argv[2] if sys.argv[2] else "Hello World"

    try:
        mutex_granted = False
        while not mutex_granted:
            mutex_granted = content_provider.request_mutex()
            if mutex_granted:
                data = content.encode('utf-8')
                content_provider.upload_file(filename, data)
                content_provider.release_mutex()
            else:
                print(
                    f"Process {os.getpid()} failed to acquire mutex for file '{filename}', retrying after 15 seconds...")
                time.sleep(15)
    except KeyboardInterrupt:
        print(f"Process {os.getpid()} interrupted")


if __name__ == '__main__':
    main()
