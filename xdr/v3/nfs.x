/* NFS Protocol v3 (RFC 1813) */
/* Program number: 100003 */

/* ===== Constants ===== */

const FHSIZE3 = 64;
const NFS_PROGRAM = 100003;
const NFS_V3 = 3;

/* Maximum sizes */
const COOKIEVERFSIZE = 8;
const CREATEVERFSIZE = 8;
const WRITEVERFSIZE = 8;

/* ===== Common Types ===== */

typedef opaque fhandle3<FHSIZE3>;
typedef unsigned hyper uint64;
typedef hyper int64;
typedef unsigned int uint32;
typedef int int32;
typedef string filename3<>;
typedef string nfspath3<>;
typedef unsigned hyper fileid3;
typedef unsigned hyper cookie3;
typedef opaque cookieverf3[COOKIEVERFSIZE];
typedef opaque createverf3[CREATEVERFSIZE];
typedef opaque writeverf3[WRITEVERFSIZE];

/* ===== NFS Status Codes ===== */

enum nfsstat3 {
    NFS3_OK             = 0,
    NFS3ERR_PERM        = 1,
    NFS3ERR_NOENT       = 2,
    NFS3ERR_IO          = 5,
    NFS3ERR_NXIO        = 6,
    NFS3ERR_ACCES       = 13,
    NFS3ERR_EXIST       = 17,
    NFS3ERR_XDEV        = 18,
    NFS3ERR_NODEV       = 19,
    NFS3ERR_NOTDIR      = 20,
    NFS3ERR_ISDIR       = 21,
    NFS3ERR_INVAL       = 22,
    NFS3ERR_FBIG        = 27,
    NFS3ERR_NOSPC       = 28,
    NFS3ERR_ROFS        = 30,
    NFS3ERR_MLINK       = 31,
    NFS3ERR_NAMETOOLONG = 63,
    NFS3ERR_NOTEMPTY    = 66,
    NFS3ERR_DQUOT       = 69,
    NFS3ERR_STALE       = 70,
    NFS3ERR_REMOTE      = 71,
    NFS3ERR_BADHANDLE   = 10001,
    NFS3ERR_NOT_SYNC    = 10002,
    NFS3ERR_BAD_COOKIE  = 10003,
    NFS3ERR_NOTSUPP     = 10004,
    NFS3ERR_TOOSMALL    = 10005,
    NFS3ERR_SERVERFAULT = 10006,
    NFS3ERR_BADTYPE     = 10007,
    NFS3ERR_JUKEBOX     = 10008
};

/* ===== File Types ===== */

enum ftype3 {
    NF3REG    = 1,  /* Regular file */
    NF3DIR    = 2,  /* Directory */
    NF3BLK    = 3,  /* Block device */
    NF3CHR    = 4,  /* Character device */
    NF3LNK    = 5,  /* Symbolic link */
    NF3SOCK   = 6,  /* Socket */
    NF3FIFO   = 7   /* FIFO */
};

/* ===== Time Specification ===== */

struct nfstime3 {
    uint32 seconds;
    uint32 nseconds;
};

/* ===== File Attributes ===== */

struct fattr3 {
    ftype3 type;
    uint32 mode;
    uint32 nlink;
    uint32 uid;
    uint32 gid;
    uint64 size;
    uint64 used;
    uint64 rdev;
    uint64 fsid;
    uint64 fileid;
    nfstime3 atime;
    nfstime3 mtime;
    nfstime3 ctime;
};

/* ===== GETATTR Procedure (1) ===== */

struct GETATTR3args {
    fhandle3 object;
};

struct GETATTR3resok {
    fattr3 obj_attributes;
};

union GETATTR3res switch (nfsstat3 status) {
    case NFS3_OK:
        GETATTR3resok resok;
    default:
        void;
};

/* ===== LOOKUP Procedure (3) ===== */

struct LOOKUP3args {
    fhandle3 what_dir;
    filename3 name;
};

struct LOOKUP3resok {
    fhandle3 object;
    fattr3 obj_attributes;
    fattr3 dir_attributes;
};

struct LOOKUP3resfail {
    fattr3 dir_attributes;
};

union LOOKUP3res switch (nfsstat3 status) {
    case NFS3_OK:
        LOOKUP3resok resok;
    default:
        LOOKUP3resfail resfail;
};

/* ===== READ Procedure (6) ===== */

struct READ3args {
    fhandle3 file;
    uint64 offset;
    uint32 count;
};

struct READ3resok {
    fattr3 file_attributes;
    uint32 count;
    bool eof;
    opaque data<>;
};

struct READ3resfail {
    fattr3 file_attributes;
};

union READ3res switch (nfsstat3 status) {
    case NFS3_OK:
        READ3resok resok;
    default:
        READ3resfail resfail;
};

/* ===== NULL Procedure (0) ===== */
/* Arguments: void */
/* Results: void */
