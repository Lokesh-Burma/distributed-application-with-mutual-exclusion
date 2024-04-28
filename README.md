# Distributed Application with Mutual Exclusion

## Overview

This distributed file storage application enables multiple client nodes to upload and download files from a cluster of storage nodes. The storage nodes utilize a shared-mutex algorithm to ensure consistency when accessing files. Clients can upload files and they can download files by requesting them from the storage node. Communication between clients and storage nodes is facilitated by protobuf definitions and gRPC stubs.

## Storage Nodes

- Each storage node runs a gRPC server implementing the FileStorage service.
- Nodes communicate with each other using the RequestMutex and ReleaseMutex RPCs to coordinate file access.
- Uploaded files are saved to disk, and metadata about the files is maintained in a JSON file.

## Clients

- Client nodes can upload and download files via the FileStorage gRPC service.
- To upload a file, a client acquires a mutex before uploading.
- To download, a client requests the file data from any storage node server.

## Building and Running

1. Use the Python gRPC tools to generate the protobuf and gRPC code.
   `python3.9 -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. file_storage.proto`
2. Run Server
   `python3.9 server.py`
3. Run Content Provider to generate file and store it in server
   `python3.9 content_provider.py filename.txt "hello world"`
4. Run User to download file from server
   `python3.9 user.py filename.txt`
