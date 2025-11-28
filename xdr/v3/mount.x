/* MOUNT Protocol v3 (RFC 1813) */
/* Program number: 100005 */

/* ===== Constants ===== */

const FHSIZE3 = 64;          /* Maximum file handle size */
const MNTPATHLEN = 1024;     /* Maximum path length */
const MNTNAMLEN = 255;       /* Maximum name length */

const MOUNT_PROGRAM = 100005;
const MOUNT_V3 = 3;

/* ===== Common Types ===== */

/* File handle - used across MOUNT and NFS */
typedef opaque fhandle3<FHSIZE3>;

/* Directory path - XDR string type */
typedef string dirpath<MNTPATHLEN>;

/* ===== MOUNT Status Codes ===== */

enum mountstat3 {
    MNT3_OK             = 0,     /* No error */
    MNT3ERR_PERM        = 1,     /* Not owner */
    MNT3ERR_NOENT       = 2,     /* No such file or directory */
    MNT3ERR_IO          = 5,     /* I/O error */
    MNT3ERR_ACCESS      = 13,    /* Permission denied */
    MNT3ERR_NOTDIR      = 20,    /* Not a directory */
    MNT3ERR_INVAL       = 22,    /* Invalid argument */
    MNT3ERR_NAMETOOLONG = 63,    /* Filename too long */
    MNT3ERR_NOTSUPP     = 10004, /* Operation not supported */
    MNT3ERR_SERVERFAULT = 10006  /* Server fault */
};

/* ===== MOUNT Procedures ===== */

/* MNT (1) - Mount a directory
 * Arguments: dirpath
 * Results: mountres3_ok or mountstat3 error
 */
struct mountres3_ok {
    fhandle3 fhandle;
    int auth_flavors<>;  /* Supported authentication flavors */
};

union mountres3 switch (mountstat3 fhs_status) {
    case MNT3_OK:
        mountres3_ok mountinfo;
    default:
        void;
};

/* UMNT (3) - Unmount a directory
 * Arguments: dirpath
 * Results: void
 */

/* NULL (0) - Ping test
 * Arguments: void
 * Results: void
 */
