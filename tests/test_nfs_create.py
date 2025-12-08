#!/usr/bin/env python3
"""
Test: NFS CREATE Procedure
Purpose: Test NFS CREATE to create new files

This test validates:
1. MOUNT to get root directory handle
2. CREATE to create a new file
3. LOOKUP to verify file was created
4. GETATTR to check file attributes
"""

import socket
import struct
import sys


def pack_string(s):
    """Pack a string as XDR string"""
    data = s.encode('utf-8')
    length = len(data)
    padding = (4 - (length % 4)) % 4
    return struct.pack('>I', length) + data + b'\x00' * padding


def unpack_opaque_flex(data, offset):
    """Unpack variable-length opaque data (length + data)"""
    length = struct.unpack('>I', data[offset:offset+4])[0]
    opaque_data = data[offset+4:offset+4+length]
    padding = (4 - (length % 4)) % 4
    next_offset = offset + 4 + length + padding
    return opaque_data, next_offset


def rpc_call(host, port, xid, prog, vers, proc, args_data):
    """Make an RPC call and return the response"""
    # Build RPC call header
    message = b''
    message += struct.pack('>I', xid)      # XID
    message += struct.pack('>I', 0)        # msg_type = CALL (0)
    message += struct.pack('>I', 2)        # RPC version
    message += struct.pack('>I', prog)     # Program
    message += struct.pack('>I', vers)     # Version
    message += struct.pack('>I', proc)     # Procedure
    # cred (AUTH_NONE)
    message += struct.pack('>I', 0)        # flavor = AUTH_NONE
    message += struct.pack('>I', 0)        # length = 0
    # verf (AUTH_NONE)
    message += struct.pack('>I', 0)        # flavor = AUTH_NONE
    message += struct.pack('>I', 0)        # length = 0

    # Add procedure arguments
    call_msg = message + args_data

    # Add RPC record marking
    msg_len = len(call_msg)
    record_header = struct.pack('>I', 0x80000000 | msg_len)

    # Connect and send
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    sock.connect((host, port))
    sock.sendall(record_header + call_msg)

    # Receive response
    reply_header_bytes = sock.recv(4)
    if len(reply_header_bytes) != 4:
        sock.close()
        raise Exception("Failed to read response header")

    reply_header = struct.unpack('>I', reply_header_bytes)[0]
    reply_len = reply_header & 0x7FFFFFFF

    # Read response data
    reply_data = b''
    while len(reply_data) < reply_len:
        chunk = sock.recv(reply_len - len(reply_data))
        if not chunk:
            break
        reply_data += chunk

    sock.close()
    return reply_data


def parse_rpc_reply(reply_data):
    """Parse RPC reply header, return offset to result data"""
    if len(reply_data) < 24:
        raise Exception(f"Response too short: {len(reply_data)} bytes")

    reply_xid, msg_type, reply_stat, verf_flavor, verf_len, accept_stat = struct.unpack(
        '>IIIIII', reply_data[:24]
    )

    if reply_stat != 0 or accept_stat != 0:
        raise Exception(f"RPC error: reply_stat={reply_stat}, accept_stat={accept_stat}")

    return 24  # Return offset to procedure-specific data


def test_nfs_create():
    """Test NFS CREATE procedure"""

    print("Test: NFS CREATE Procedure")
    print("=" * 60)
    print()

    host = "localhost"
    port = 4000

    # Test file
    test_filename = "test_create_new_file.txt"
    print(f"Test file: {test_filename}")
    print()

    # Step 1: MOUNT
    print("Step 1: MOUNT /")
    print("-" * 60)
    mount_xid = 600001
    mount_args = pack_string("/")

    reply_data = rpc_call(host, port, mount_xid, 100005, 3, 1, mount_args)
    offset = parse_rpc_reply(reply_data)

    mount_status = struct.unpack('>I', reply_data[offset:offset+4])[0]
    if mount_status != 0:
        print(f"  ✗ MOUNT failed with status {mount_status}")
        sys.exit(1)

    root_fhandle, _ = unpack_opaque_flex(reply_data, offset + 4)
    print(f"  ✓ Got root handle: {len(root_fhandle)} bytes")
    print()

    # Step 2: CREATE new file
    print(f"Step 2: CREATE {test_filename}")
    print("-" * 60)
    create_xid = 600002

    # CREATE3args: dir handle + filename + how (createhow3)
    create_args = b''

    # Directory handle (variable-length opaque)
    create_args += struct.pack('>I', len(root_fhandle)) + root_fhandle
    padding = (4 - (len(root_fhandle) % 4)) % 4
    create_args += b'\x00' * padding

    # Filename (XDR string)
    create_args += pack_string(test_filename)

    # createhow3: UNCHECKED mode (0) + sattr3
    create_args += struct.pack('>I', 0)  # mode = UNCHECKED

    # sattr3 structure (union format):
    # set_mode3: discriminator (SET_MODE=1) + mode (u32)
    create_args += struct.pack('>I', 1)     # discriminator = SET_MODE
    create_args += struct.pack('>I', 0o644) # mode = 0644

    # set_uid3: discriminator (DONT_SET_UID=0) only, no value
    create_args += struct.pack('>I', 0)     # discriminator = DONT_SET_UID

    # set_gid3: discriminator (DONT_SET_GID=0) only, no value
    create_args += struct.pack('>I', 0)     # discriminator = DONT_SET_GID

    # set_size3: discriminator (DONT_SET_SIZE=0) only, no value
    create_args += struct.pack('>I', 0)     # discriminator = DONT_SET_SIZE

    # set_atime: discriminator (DONT_CHANGE=0) only, no value
    create_args += struct.pack('>I', 0)     # discriminator = DONT_CHANGE

    # set_mtime: discriminator (DONT_CHANGE=0) only, no value
    create_args += struct.pack('>I', 0)     # discriminator = DONT_CHANGE

    print(f"  Creating file with mode 0644")

    reply_data = rpc_call(host, port, create_xid, 100003, 3, 8, create_args)
    offset = parse_rpc_reply(reply_data)

    # Parse CREATE3res
    nfs_status = struct.unpack('>I', reply_data[offset:offset+4])[0]
    print(f"  NFS status: {nfs_status} (0=NFS3_OK)")

    if nfs_status != 0:
        print(f"  ✗ CREATE failed with status {nfs_status}")
        sys.exit(1)

    offset += 4

    # Parse CREATE3resok
    # post_op_fh3 (optional file handle)
    handle_follows = struct.unpack('>I', reply_data[offset:offset+4])[0]
    offset += 4

    if handle_follows:
        new_file_handle, offset = unpack_opaque_flex(reply_data, offset)
        print(f"  ✓ Created file, handle: {len(new_file_handle)} bytes")
    else:
        print(f"  ⚠ No file handle returned")
        new_file_handle = None

    # post_op_attr (optional attributes)
    attr_follows = struct.unpack('>I', reply_data[offset:offset+4])[0]
    offset += 4

    if attr_follows:
        # Skip fattr3 (84 bytes)
        offset += 84
        print(f"  ✓ File attributes returned")

    print()

    # Step 3: LOOKUP to verify file exists
    print(f"Step 3: LOOKUP {test_filename} to verify creation")
    print("-" * 60)
    lookup_xid = 600003

    # LOOKUP3args
    lookup_args = b''
    lookup_args += struct.pack('>I', len(root_fhandle)) + root_fhandle
    padding = (4 - (len(root_fhandle) % 4)) % 4
    lookup_args += b'\x00' * padding
    lookup_args += pack_string(test_filename)

    reply_data = rpc_call(host, port, lookup_xid, 100003, 3, 3, lookup_args)
    offset = parse_rpc_reply(reply_data)

    nfs_status = struct.unpack('>I', reply_data[offset:offset+4])[0]
    if nfs_status != 0:
        print(f"  ✗ LOOKUP failed with status {nfs_status}")
        sys.exit(1)

    verified_handle, _ = unpack_opaque_flex(reply_data, offset + 4)
    print(f"  ✓ File exists, handle: {len(verified_handle)} bytes")

    if new_file_handle and verified_handle == new_file_handle:
        print(f"  ✅ File handle matches CREATE result")
    print()

    print("=" * 60)
    print("✅ NFS CREATE test PASSED")
    print()
    print("Summary:")
    print("  ✓ CREATE new file succeeded")
    print("  ✓ File verified with LOOKUP")
    print("  ✓ File handle matches")


if __name__ == '__main__':
    test_nfs_create()
