#!/usr/bin/env python3
"""
Test: NFS REMOVE Procedure
Purpose: Test file removal functionality
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
    is_last = (reply_header & 0x80000000) != 0
    reply_len = reply_header & 0x7FFFFFFF

    print(f"  Response header: is_last={is_last}, length={reply_len}")

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
    """Parse RPC reply header"""
    if len(reply_data) < 24:
        raise Exception(f"Response too short: {len(reply_data)} bytes")

    reply_xid, msg_type, reply_stat, verf_flavor, verf_len, accept_stat = struct.unpack(
        '>IIIIII', reply_data[:24]
    )

    print(f"  Reply XID: {reply_xid}")
    print(f"  Reply stat: {reply_stat} (0=MSG_ACCEPTED)")
    print(f"  Accept stat: {accept_stat} (0=SUCCESS)")

    if reply_stat != 0 or accept_stat != 0:
        raise Exception(f"RPC error: reply_stat={reply_stat}, accept_stat={accept_stat}")

    return 24  # Return offset to NFS data


def test_remove(host, port):
    """Test REMOVE procedure"""
    print("\n=== Test: NFS REMOVE ===")

    # Step 1: Mount to get root file handle
    print("\n1. Calling MOUNT...")
    mount_args = pack_string("/tmp/nfs_exports")
    mount_reply = rpc_call(host, port, 1, 100005, 3, 1, mount_args)
    offset = parse_rpc_reply(mount_reply)

    # Parse MOUNT reply
    status = struct.unpack('>I', mount_reply[offset:offset+4])[0]
    if status != 0:
        raise Exception(f"MOUNT failed with status {status}")
    offset += 4

    root_handle, offset = unpack_opaque_flex(mount_reply, offset)
    print(f"  Got root handle: {len(root_handle)} bytes")

    # Step 2: CREATE a test file first
    print("\n2. Creating test file 'test_remove.txt'...")
    create_args = b''

    # where_dir (fhandle3)
    create_args += struct.pack('>I', len(root_handle))
    create_args += root_handle
    padding = (4 - (len(root_handle) % 4)) % 4
    create_args += b'\x00' * padding

    # name (filename3)
    create_args += pack_string("test_remove.txt")

    # how (createhow3) - UNCHECKED mode
    create_args += struct.pack('>I', 0)  # mode = UNCHECKED

    # sattr3 (attributes)
    create_args += struct.pack('>I', 1)     # set_mode = SET_MODE
    create_args += struct.pack('>I', 0o644) # mode value
    create_args += struct.pack('>I', 0)     # set_uid = default
    create_args += struct.pack('>I', 0)     # set_gid = default
    create_args += struct.pack('>I', 0)     # set_size = default
    create_args += struct.pack('>I', 0)     # set_atime = default
    create_args += struct.pack('>I', 0)     # set_mtime = default

    create_reply = rpc_call(host, port, 2, 100003, 3, 8, create_args)
    offset = parse_rpc_reply(create_reply)

    status = struct.unpack('>I', create_reply[offset:offset+4])[0]
    if status != 0:
        raise Exception(f"CREATE failed with status {status}")

    print("  File created successfully")

    # Step 3: REMOVE the file
    print("\n3. Calling REMOVE to delete 'test_remove.txt'...")
    remove_args = b''

    # dir (fhandle3)
    remove_args += struct.pack('>I', len(root_handle))
    remove_args += root_handle
    padding = (4 - (len(root_handle) % 4)) % 4
    remove_args += b'\x00' * padding

    # name (filename3)
    remove_args += pack_string("test_remove.txt")

    remove_reply = rpc_call(host, port, 3, 100003, 3, 12, remove_args)
    offset = parse_rpc_reply(remove_reply)

    # Parse REMOVE reply
    status = struct.unpack('>I', remove_reply[offset:offset+4])[0]
    offset += 4

    if status != 0:
        raise Exception(f"REMOVE failed with status {status}")

    print(f"  REMOVE status: NFS3_OK (0)")

    # post_op_attr (dir_wcc)
    attr_follows = struct.unpack('>I', remove_reply[offset:offset+4])[0]
    offset += 4

    if attr_follows:
        print(f"  Directory attributes present")
        # Skip fattr3 (84 bytes)
        offset += 84

    print(f"  Total response size: {len(remove_reply)} bytes")

    # Step 4: Verify file was removed by trying to LOOKUP
    print("\n4. Verifying file was removed (LOOKUP should fail)...")
    lookup_args = b''

    # dir (fhandle3)
    lookup_args += struct.pack('>I', len(root_handle))
    lookup_args += root_handle
    padding = (4 - (len(root_handle) % 4)) % 4
    lookup_args += b'\x00' * padding

    # name (filename3)
    lookup_args += pack_string("test_remove.txt")

    lookup_reply = rpc_call(host, port, 4, 100003, 3, 3, lookup_args)
    offset = parse_rpc_reply(lookup_reply)

    status = struct.unpack('>I', lookup_reply[offset:offset+4])[0]
    if status == 2:  # NFS3ERR_NOENT = 2
        print("  ✓ LOOKUP failed with NOENT - file was successfully removed")
    else:
        raise Exception(f"Expected NOENT (2), got status {status}")

    print("\n✓ REMOVE test passed!")


def test_remove_nonexistent(host, port):
    """Test REMOVE on nonexistent file"""
    print("\n=== Test: REMOVE Nonexistent File ===")

    # Step 1: Mount to get root file handle
    print("\n1. Calling MOUNT...")
    mount_args = pack_string("/tmp/nfs_exports")
    mount_reply = rpc_call(host, port, 5, 100005, 3, 1, mount_args)
    offset = parse_rpc_reply(mount_reply)

    status = struct.unpack('>I', mount_reply[offset:offset+4])[0]
    if status != 0:
        raise Exception(f"MOUNT failed with status {status}")
    offset += 4

    root_handle, offset = unpack_opaque_flex(mount_reply, offset)
    print(f"  Got root handle: {len(root_handle)} bytes")

    # Step 2: Try to REMOVE nonexistent file
    print("\n2. Trying to REMOVE nonexistent file 'does_not_exist.txt'...")
    remove_args = b''

    # dir (fhandle3)
    remove_args += struct.pack('>I', len(root_handle))
    remove_args += root_handle
    padding = (4 - (len(root_handle) % 4)) % 4
    remove_args += b'\x00' * padding

    # name (filename3)
    remove_args += pack_string("does_not_exist.txt")

    remove_reply = rpc_call(host, port, 6, 100003, 3, 12, remove_args)
    offset = parse_rpc_reply(remove_reply)

    # Parse REMOVE reply
    status = struct.unpack('>I', remove_reply[offset:offset+4])[0]

    if status == 2:  # NFS3ERR_NOENT = 2
        print(f"  ✓ REMOVE correctly returned NOENT (2)")
    else:
        raise Exception(f"Expected NOENT (2) for nonexistent file, got status {status}")

    print("\n✓ REMOVE nonexistent file test passed!")


if __name__ == '__main__':
    host = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 2049

    try:
        test_remove(host, port)
        test_remove_nonexistent(host, port)
    except Exception as e:
        print(f"\n✗ Test failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
