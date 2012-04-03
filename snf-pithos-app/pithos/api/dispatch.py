from pithos.api.settings import (BACKEND_DB_MODULE, BACKEND_DB_CONNECTION,
                                    BACKEND_BLOCK_MODULE, BACKEND_BLOCK_PATH,
                                    BACKEND_QUEUE_MODULE, BACKEND_QUEUE_CONNECTION,
                                    BACKEND_QUOTA, BACKEND_VERSIONING)
from pithos.backends import connect_backend
from pithos.api.util import hashmap_md5

def update_md5(m):
    if m['resource'] != 'object' or m['details']['action'] != 'object update':
        return
    
    backend = connect_backend(db_module=BACKEND_DB_MODULE,
                              db_connection=BACKEND_DB_CONNECTION,
                              block_module=BACKEND_BLOCK_MODULE,
                              block_path=BACKEND_BLOCK_PATH,
                              queue_module=BACKEND_QUEUE_MODULE,
                              queue_connection=BACKEND_QUEUE_CONNECTION)
    backend.default_policy['quota'] = BACKEND_QUOTA
    backend.default_policy['versioning'] = BACKEND_VERSIONING
    
    path = m['value']
    account, container, name = path.split('/', 2)
    version = m['details']['version']
    meta = None
    try:
        meta = backend.get_object_meta(account, account, container, name, 'pithos', version)
        if meta['checksum'] == '':
            size, hashmap = backend.get_object_hashmap(account, account, container, name, version)
            checksum = hashmap_md5(backend, hashmap, size)
            backend.update_object_checksum(account, account, container, name, version, checksum)
            print 'INFO: Updated checksum for path "%s"' % (path,)
    except Exception, e:
        print 'WARNING: Can not update checksum for path "%s" (%s)' % (path, e)
    
    backend.close()
