# content_provider.py
import grpc
import sys
import time
import file_storage_pb2
import file_storage_pb2_grpc
import random

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


class ContentProviderClient:
    def __init__(self, node_id, num_nodes):
        self.node_id = node_id
        self.num_nodes = num_nodes

    def connect_to_server(self, server_address):
        self.channel = grpc.insecure_channel(server_address)
        self.stub = file_storage_pb2_grpc.FileStorageStub(self.channel)

    def upload_file(self, filename, data):
        request = file_storage_pb2.Content(filename=filename, data=data)
        response = self.stub.UploadFile(request)
        return response.success

    def request_mutex(self):
        request = file_storage_pb2.MutexRequest(
            sequence_number=0, node_id=self.node_id)
        response = self.stub.RequestContentProviderMutex(request)
        return response.granted

    def release_mutex(self):
        request = file_storage_pb2.MutexRequest(
            sequence_number=0, node_id=self.node_id)
        response = self.stub.ReleaseContentProviderMutex(request)
        return response.granted


def main():
    num_nodes = 2  # number of Content Providers in the node
    node_id = random.randint(0, num_nodes - 1)
    server_address = 'localhost:5005' + \
        str(node_id)  # Update with the server address
    print(f"Node {node_id} connecting to server at {server_address}")
    content_provider = ContentProviderClient(node_id, num_nodes)
    content_provider.connect_to_server(server_address)

    # Check if filename and content string are provided as command-line arguments
    if len(sys.argv) != 3:
        print("Usage: python content_provider.py <filename> <content>")
        # sys.exit(1)
    # sys.argv[1] = "file1.txt"
    # sys.argv[2] = "Hello World!"
    filename = "file1.txt"  # sys.argv[1]
    content = "Hello World!"  # sys.argv[2]

    try:
        # Acquire mutex before uploading file
        mutex_granted = content_provider.request_mutex()
        if mutex_granted:
            data = content.encode()  # Convert content string to bytes
            success = content_provider.upload_file(filename, data)
            if success:
                print(f"File '{filename}' uploaded successfully")
            else:
                print(f"Failed to upload file '{filename}' (duplicate file)")
            # Release mutex after uploading file
            content_provider.release_mutex()
        else:
            print("Failed to acquire mutex")
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
