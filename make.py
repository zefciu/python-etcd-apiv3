#!/usr/bin/env python
import os
import re
import sys
import subprocess as sp

if __name__ == '__main__':
    
    if not (os.path.islink('gogoproto')):
        os.symlink('protobuf/gogoproto', 'gogoproto')

    protos = sp.check_output(['find', 'etcd', '-name', '*.proto']).split('\n')
    protos.append('gogoproto/gogo.proto')
    try:
        plugin = sp.check_output(['which', 'grpc_python_plugin'])
    except sp.CalledProcessError:
        print("Didn't find python plugin for grpc")
    to_pack = []

    # Compile protobuf files
    for line in protos:
        if not line:
            continue  # Newline on the end of file
        # FIXME: After https://github.com/coreos/etcd/issues/5156
        # is resolved, the hack below should be gone
        if line.endswith('raft_internal.proto'):
            continue
        sp.check_call([
            'protoc',
            '-I.',
            '-Iprotobuf',
            '--python_out=.',
            '--plugin=protoc-gen-grpc=' + plugin.strip(),
            line
        ])
        to_pack.append(line[:-len('.proto')] + '_pb2.py')

    # Create __init__.py files
    paths = set()
    for file_ in to_pack:
        path = os.path.dirname(file_)
        while path:
            paths.add(path)
            path = os.path.dirname(path)
    for path in paths:
        init_file = os.path.join(path, '__init__.py')
        f = open(init_file, 'w')
        f.close()
        to_pack.append(init_file)

    # Find etcd version and create setup.py
    with open('etcd/version/version.go') as f:
        m = re.search(
            '^\s*Version\s*=\s*"([^"]+)"\s*$',
            f.read(),
            re.MULTILINE
        )
        if not m:
            print('Version not found!')
            sys.exit(1)
        version = m.group(1)
        with open('setup.py_tmpl') as inf, open('setup.py', 'w') as ouf:
            ouf.write(inf.read().format(version=version))


    # Create the MANIFEST
    to_pack.extend(['setup.py', 'README.rst', 'MANIFEST'])
    with open('MANIFEST', 'w') as f:
        f.write('\n'.join(to_pack))
