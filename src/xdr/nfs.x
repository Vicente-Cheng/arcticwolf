/* NFS and MOUNT Protocol Types */
/* Unified XDR specification for all NFS-related operations */

/* ===== Common Constants ===== */

const FHSIZE3 = 64;          /* Maximum file handle size */

/* ===== Program Numbers ===== */

const MOUNT_PROGRAM = 100005;
const MOUNT_V3 = 3;

const NFS_PROGRAM = 100003;
const NFS_V3 = 3;

/* ===== Common Types ===== */

/* File handle */
typedef opaque fhandle3<FHSIZE3>;

/* ===== MOUNT Protocol (Program 100005) ===== */

/* MOUNT status codes */
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

/* MOUNT response */
struct mountres3 {
    mountstat3 status;
    fhandle3 fhandle;  /* Only valid if status == MNT3_OK */
};

/* ===== NFS Protocol (Program 100003) ===== */

/* NFS status codes */
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

/* File types */
enum ftype3 {
    NF3REG    = 1,  /* Regular file */
    NF3DIR    = 2,  /* Directory */
    NF3BLK    = 3,  /* Block device */
    NF3CHR    = 4,  /* Character device */
    NF3LNK    = 5,  /* Symbolic link */
    NF3SOCK   = 6,  /* Socket */
    NF3FIFO   = 7   /* FIFO */
};

/* GETATTR response */
struct getattr3resok {
    ftype3 ftype;
    unsigned int mode;
    unsigned int nlink;
    unsigned int uid;
    unsigned int gid;
    unsigned hyper size;
    unsigned hyper used;
};

struct getattr3res {
    nfsstat3 status;
    getattr3resok obj_attributes;  /* Only valid if status == NFS3_OK */
};
