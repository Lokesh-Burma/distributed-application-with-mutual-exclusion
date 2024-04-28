# user.py
import grpc
import sys
import file_storage_pb2
import file_storage_pb2_grpc


class UserClient:
    def __init__(self):
        server_address = '172.31.12.146:50051'
        self.channel = grpc.insecure_channel(server_address)
        self.stub = file_storage_pb2_grpc.FileStorageStub(self.channel)

    def download_file(self, filename):
        request = file_storage_pb2.DownloadRequest(filename=filename)
        response = self.stub.DownloadFile(request)
        if response.data == '':
            print(f"Failed to download file '{filename}'")
        else:
            print(f"Downloaded file '{filename}' successfully")
        return response.data


def main():
    user = UserClient()

    if len(sys.argv) != 2:
        print("Usage: python user.py <filename>")
        sys.exit(1)

    filename = sys.argv[1]
    print(f"Downloading file '{filename}' from server...")

    try:
        data = user.download_file(filename)
        print(f"Contents of file '{filename}':")
        print(data)
    except grpc.RpcError as e:
        print(f"Failed to download file '{filename}': {e.details()}")


if __name__ == '__main__':
    main()
