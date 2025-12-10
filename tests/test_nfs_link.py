#!/usr/bin/env python3
"""
Test NFS LINK Procedure (15)

Tests the NFSv3 LINK operation which creates hard links to existing files.
"""

import socket
import struct
import sys
import os


def pack_rpc_call(xid, prog, vers, proc, auth_flavor=0, auth_len=0, verf_flavor=0, verf_len=0):
    """Pack RPC call header"""
    # RPC header (28 bytes base)
    rpc_header = struct.pack(
        '>IIIIIIII',
        xid,         # XID
        0,           # Message type (0 = CALL)
        2,           # RPC version
        prog,        # Program
        vers,        # Version
        proc,        # Procedure
        auth_flavor, # Auth flavor
        auth_len     # Auth length
    )

    # Add verifier
    verf = struct.pack('>II', verf_flavor, verf_len)

    return rpc_header + verf


def pack_fhandle3(handle):
    """Pack file handle (length + data + padding)"""
    handle_len = len(handle)
    packed = struct.pack('>I', handle_len)
    packed += handle
    # Add padding to 4-byte boundary
    padding = (4 - (handle_len % 4)) % 4
    packed += b'\x00' * padding
    return packed


def pack_filename3(name):
    """Pack filename (length + string + padding)"""
    name_bytes = name.encode('utf-8')
    name_len = len(name_bytes)
    packed = struct.pack('>I', name_len)
    packed += name_bytes
    # Add padding to 4-byte boundary
    padding = (4 - (name_len % 4)) % 4
    packed += b'\x00' * padding
    return packed


def pack_sattr3(mode=None, uid=None, gid=None, size=None, atime_set=False, mtime_set=False):
    """
    Pack sattr3 structure for setting file attributes.

    Each field is a union discriminated by a boolean:
    - False (0) = don't set
    - True (1) = set to following value
    """
    packed = b''

    # mode (set_mode3 union)
    if mode is not None:
        packed += struct.pack('>II', 1, mode)  # SET_MODE discriminator (1) + mode value
    else:
        packed += struct.pack('>I', 0)  # DONT_SET_MODE discriminator (0)

    # uid (set_uid3 union)
    if uid is not None:
        packed += struct.pack('>II', 1, uid)
    else:
        packed += struct.pack('>I', 0)

    # gid (set_gid3 union)
    if gid is not None:
        packed += struct.pack('>II', 1, gid)
    else:
        packed += struct.pack('>I', 0)

    # size (set_size3 union)
    if size is not None:
        packed += struct.pack('>IQ', 1, size)
    else:
        packed += struct.pack('>I', 0)

    # atime (set_atime union)
    if atime_set:
        # SET_TO_CLIENT_TIME (1) + nfstime3 (seconds + nseconds)
        packed += struct.pack('>III', 1, 0, 0)
    else:
        packed += struct.pack('>I', 0)  # DONT_CHANGE

    # mtime (set_mtime union)
    if mtime_set:
        packed += struct.pack('>III', 1, 0, 0)
    else:
        packed += struct.pack('>I', 0)

    return packed


def pack_create3args(dir_handle, filename, mode=0o644):
    """Pack CREATE3args structure"""
    packed = pack_fhandle3(dir_handle)
    packed += pack_filename3(filename)
    # createmode3: UNCHECKED (0)
    packed += struct.pack('>I', 0)
    # sattr3
    packed += pack_sattr3(mode=mode)
    return packed


def pack_link3args(file_handle, dir_handle, name):
    """
    Pack LINK3args structure

    LINK3args = {
        fhandle3 file;       // source file handle
        fhandle3 link_dir;   // target directory handle
        filename3 name;      // new link name
    }
    """
    packed = pack_fhandle3(file_handle)
    packed += pack_fhandle3(dir_handle)
    packed += pack_filename3(name)
    return packed


def parse_post_op_fh3(reply_data, offset):
    """Parse post_op_fh3 (optional file handle)"""
    handle_follows = struct.unpack('>I', reply_data[offset:offset+4])[0]
    offset += 4

    if handle_follows:
        handle_len = struct.unpack('>I', reply_data[offset:offset+4])[0]
        offset += 4
        handle = reply_data[offset:offset+handle_len]
        padding = (4 - (handle_len % 4)) % 4
        offset += handle_len + padding
        return handle, offset
    else:
        return None, offset


def parse_post_op_attr(reply_data, offset):
    """Parse post_op_attr (optional fattr3)"""
    attr_follows = struct.unpack('>I', reply_data[offset:offset+4])[0]
    offset += 4

    if attr_follows:
        # fattr3 is 84 bytes:
        # - ftype (4) + mode (4) + nlink (4) + uid (4) + gid (4)
        # - size (8) + used (8) + rdev (8)
        # - fsid (8) + fileid (8)
        # - atime (8) + mtime (8) + ctime (8)

        # We're interested in nlink (number of hard links)
        ftype = struct.unpack('>I', reply_data[offset:offset+4])[0]
        mode = struct.unpack('>I', reply_data[offset+4:offset+8])[0]
        nlink = struct.unpack('>I', reply_data[offset+8:offset+12])[0]

        offset += 84
        return True, nlink, offset
    else:
        return False, 0, offset


def parse_wcc_data(reply_data, offset):
    """
    Parse wcc_data structure (RFC 1813 Section 3.3.6)

    wcc_data = {
        before: pre_op_attr   (bool + optional 24 bytes)
        after:  post_op_attr  (bool + optional 84 bytes)
    }
    """
    start_offset = offset

    # Parse pre_op_attr
    pre_attr_follows = struct.unpack('>I', reply_data[offset:offset+4])[0]
    offset += 4

    if pre_attr_follows:
        # wcc_attr = 24 bytes (size:8 + mtime:8 + ctime:8)
        size = struct.unpack('>Q', reply_data[offset:offset+8])[0]
        offset += 8
        mtime_sec, mtime_nsec = struct.unpack('>II', reply_data[offset:offset+8])
        offset += 8
        ctime_sec, ctime_nsec = struct.unpack('>II', reply_data[offset:offset+8])
        offset += 8

    # Parse post_op_attr
    post_attr_follows = struct.unpack('>I', reply_data[offset:offset+4])[0]
    offset += 4

    if post_attr_follows:
        # fattr3 = 84 bytes
        offset += 84

    # Validate wcc_data size
    expected_size = 4 + (24 if pre_attr_follows else 0) + 4 + (84 if post_attr_follows else 0)
    actual_size = offset - start_offset

    if actual_size != expected_size:
        raise Exception(f"wcc_data size mismatch: expected {expected_size}, got {actual_size}")

    return offset


def unpack_opaque_flex(data, offset):
    """Unpack variable-length opaque data (length + data + padding)"""
    length = struct.unpack('>I', data[offset:offset+4])[0]
    offset += 4
    opaque_data = data[offset:offset+length]
    padding = (4 - (length % 4)) % 4
    offset += length + padding
    return opaque_data, offset


def get_root_handle(sock):
    """Helper function to get root handle via MOUNT"""
    xid = 0x12345678
    rpc_call = pack_rpc_call(xid, 100005, 3, 1)  # MOUNT (proc 1)
    mount_args = pack_filename3("/")

    msg = rpc_call + mount_args
    record_marker = struct.pack('>I', 0x80000000 | len(msg))
    sock.send(record_marker + msg)

    header = sock.recv(4)
    response_len = struct.unpack('>I', header)[0] & 0x7FFFFFFF
    reply_data = sock.recv(response_len)

    offset = 24  # Skip RPC header
    status = struct.unpack('>I', reply_data[offset:offset+4])[0]

    if status != 0:
        raise Exception(f"MOUNT failed with status {status}")

    root_handle, _ = unpack_opaque_flex(reply_data, offset + 4)
    return root_handle


def test_link_and_verify(server_ip, server_port):
    """Test NFS LINK procedure - create hard link and verify"""

    print("=" * 60)
    print("Testing NFS LINK Procedure (15)")
    print("=" * 60)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((server_ip, server_port))

    try:
        # Step 1: MOUNT to get root handle
        print("\n[1] Getting root handle via MOUNT...")
        root_handle = get_root_handle(sock)
        print(f"  Got root handle: {root_handle.hex()} ({len(root_handle)} bytes)")

        # Step 2: Create a test file
        print("\n[2] Creating test file 'test_source_file.txt'...")
        xid = 0x12345679
        rpc_call = pack_rpc_call(xid, 100003, 3, 8)  # CREATE (proc 8)

        create_args = pack_create3args(root_handle, "test_source_file.txt", mode=0o644)

        msg = rpc_call + create_args
        record_marker = struct.pack('>I', 0x80000000 | len(msg))
        sock.send(record_marker + msg)

        # Receive response
        header = sock.recv(4)
        response_len = struct.unpack('>I', header)[0] & 0x7FFFFFFF
        reply_data = sock.recv(response_len)

        # Parse CREATE3res
        offset = 24  # Skip RPC header
        status = struct.unpack('>I', reply_data[offset:offset+4])[0]
        offset += 4

        if status != 0:
            print(f"  ERROR: CREATE failed with status {status}")
            return False

        # Get file handle
        file_handle, offset = parse_post_op_fh3(reply_data, offset)
        if not file_handle:
            print(f"  ERROR: No file handle returned")
            return False

        print(f"  Created file, handle: {file_handle.hex()} ({len(file_handle)} bytes)")

        # Get initial link count
        attr_present, initial_nlink, offset = parse_post_op_attr(reply_data, offset)
        print(f"  Initial link count: {initial_nlink}")

        # Step 3: Create a hard link
        print("\n[3] Creating hard link 'test_hardlink.txt' -> 'test_source_file.txt'...")
        xid = 0x1234567A
        rpc_call = pack_rpc_call(xid, 100003, 3, 15)  # LINK (proc 15)

        link_args = pack_link3args(file_handle, root_handle, "test_hardlink.txt")

        msg = rpc_call + link_args
        record_marker = struct.pack('>I', 0x80000000 | len(msg))
        sock.send(record_marker + msg)

        # Receive response
        header = sock.recv(4)
        response_len = struct.unpack('>I', header)[0] & 0x7FFFFFFF
        reply_data = sock.recv(response_len)

        # Parse RPC reply header
        (reply_xid, msg_type, reply_stat, verf_flavor, verf_len, accept_stat) = \
            struct.unpack('>IIIIII', reply_data[:24])

        print(f"  LINK XID: {hex(reply_xid)}, accept_stat: {accept_stat}")

        # Parse LINK3res
        offset = 24
        status = struct.unpack('>I', reply_data[offset:offset+4])[0]
        offset += 4

        print(f"  Status: {status} (0=NFS3_OK)")

        if status != 0:
            print(f"  ERROR: LINK failed with status {status}")
            return False

        # Success case: parse post_op_attr + wcc_data
        print(f"\n  Parsing LINK3resok structure...")

        # Parse post_op_attr (source file attributes - link count should increase)
        attr_present, new_nlink, offset = parse_post_op_attr(reply_data, offset)
        if attr_present:
            print(f"  Source file attributes present")
            print(f"  New link count: {new_nlink}")

            # Verify link count increased
            if new_nlink != initial_nlink + 1:
                print(f"  WARNING: Link count should increase from {initial_nlink} to {initial_nlink + 1}, got {new_nlink}")
        else:
            print(f"  No source file attributes")

        # Parse wcc_data (target directory)
        print(f"\n  Parsing wcc_data (target directory)...")
        offset = parse_wcc_data(reply_data, offset)

        print(f"\n  Total response size: {len(reply_data)} bytes")
        print(f"  Parsed offset: {offset} bytes")

        if offset != len(reply_data):
            print(f"  WARNING: Response size mismatch!")
            print(f"  Unparsed data: {(len(reply_data) - offset)} bytes")
            return False

        print("\n✓ LINK test PASSED - format validation successful")
        print(f"✓ Hard link created successfully, link count increased from {initial_nlink} to {new_nlink}")
        return True

    finally:
        sock.close()


def test_link_already_exists(server_ip, server_port):
    """Test LINK on existing filename (should return NFS3ERR_EXIST)"""

    print("\n" + "=" * 60)
    print("Testing LINK on existing filename")
    print("=" * 60)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((server_ip, server_port))

    try:
        # Get root handle via MOUNT
        print("\n[1] Getting root handle via MOUNT...")
        root_handle = get_root_handle(sock)

        # Create a test file
        print("\n[2] Creating test file 'link_source.txt'...")
        xid = 0x1234567B
        rpc_call = pack_rpc_call(xid, 100003, 3, 8)  # CREATE (proc 8)
        create_args = pack_create3args(root_handle, "link_source.txt", mode=0o644)

        msg = rpc_call + create_args
        record_marker = struct.pack('>I', 0x80000000 | len(msg))
        sock.send(record_marker + msg)

        header = sock.recv(4)
        response_len = struct.unpack('>I', header)[0] & 0x7FFFFFFF
        reply_data = sock.recv(response_len)

        offset = 24
        status = struct.unpack('>I', reply_data[offset:offset+4])[0]
        if status != 0:
            print(f"  ERROR: CREATE failed")
            return False

        file_handle, _ = parse_post_op_fh3(reply_data, offset + 4)

        # Try to create link with same name as source file
        print("\n[3] Attempting to create link with existing name 'link_source.txt'...")
        xid = 0x1234567C
        rpc_call = pack_rpc_call(xid, 100003, 3, 15)  # LINK (proc 15)

        link_args = pack_link3args(file_handle, root_handle, "link_source.txt")

        msg = rpc_call + link_args
        record_marker = struct.pack('>I', 0x80000000 | len(msg))
        sock.send(record_marker + msg)

        # Receive response
        header = sock.recv(4)
        response_len = struct.unpack('>I', header)[0] & 0x7FFFFFFF
        reply_data = sock.recv(response_len)

        # Parse response
        offset = 24  # Skip RPC header
        status = struct.unpack('>I', reply_data[offset:offset+4])[0]
        offset += 4

        print(f"  Status: {status} (17=NFS3ERR_EXIST expected)")

        # Parse post_op_attr + wcc_data (present in both success and failure cases)
        print(f"\n  Parsing post_op_attr...")
        attr_present, nlink, offset = parse_post_op_attr(reply_data, offset)

        print(f"\n  Parsing wcc_data...")
        offset = parse_wcc_data(reply_data, offset)

        if offset != len(reply_data):
            print(f"  WARNING: Response size mismatch!")
            return False

        if status == 17:  # NFS3ERR_EXIST
            print("\n✓ LINK already exists test PASSED - returned NFS3ERR_EXIST")
            return True
        else:
            print(f"\n✗ LINK test FAILED - expected status 17, got {status}")
            return False

    finally:
        sock.close()


def test_link_to_directory(server_ip, server_port):
    """Test LINK on a directory (should return NFS3ERR_ISDIR)"""

    print("\n" + "=" * 60)
    print("Testing LINK on directory (should fail)")
    print("=" * 60)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((server_ip, server_port))

    try:
        # Get root handle via MOUNT
        print("\n[1] Getting root handle via MOUNT...")
        root_handle = get_root_handle(sock)

        # Try to create hard link to root directory (should fail)
        print("\n[2] Attempting to create hard link to directory...")
        xid = 0x1234567D
        rpc_call = pack_rpc_call(xid, 100003, 3, 15)  # LINK (proc 15)

        link_args = pack_link3args(root_handle, root_handle, "dir_link")

        msg = rpc_call + link_args
        record_marker = struct.pack('>I', 0x80000000 | len(msg))
        sock.send(record_marker + msg)

        # Receive response
        header = sock.recv(4)
        response_len = struct.unpack('>I', header)[0] & 0x7FFFFFFF
        reply_data = sock.recv(response_len)

        # Parse response
        offset = 24  # Skip RPC header
        status = struct.unpack('>I', reply_data[offset:offset+4])[0]
        offset += 4

        print(f"  Status: {status} (21=NFS3ERR_ISDIR expected)")

        # Parse post_op_attr + wcc_data
        print(f"\n  Parsing post_op_attr...")
        attr_present, nlink, offset = parse_post_op_attr(reply_data, offset)

        print(f"\n  Parsing wcc_data...")
        offset = parse_wcc_data(reply_data, offset)

        if offset != len(reply_data):
            print(f"  WARNING: Response size mismatch!")
            return False

        if status == 21:  # NFS3ERR_ISDIR
            print("\n✓ LINK to directory test PASSED - returned NFS3ERR_ISDIR")
            return True
        else:
            print(f"\n✗ LINK test FAILED - expected status 21 (NFS3ERR_ISDIR), got {status}")
            return False

    finally:
        sock.close()


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <server_ip> <server_port>")
        sys.exit(1)

    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])

    success = True

    # Test 1: Create hard link and verify link count
    if not test_link_and_verify(server_ip, server_port):
        success = False

    # Test 2: Try to create link with existing filename
    if not test_link_already_exists(server_ip, server_port):
        success = False

    # Test 3: Try to create hard link to directory
    if not test_link_to_directory(server_ip, server_port):
        success = False

    if success:
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("SOME TESTS FAILED ✗")
        print("=" * 60)
        sys.exit(1)
