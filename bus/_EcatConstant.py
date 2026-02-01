
import pysoem

class EcatConstant:

    BECKHOFF_VENDOR_ID = 0x0002

    STATE_NONE      = pysoem.NONE_STATE     #0
    STATE_INIT      = pysoem.INIT_STATE     #1
    STATE_PREOP     = pysoem.PREOP_STATE    #2
    STATE_BOOT      = pysoem.BOOT_STATE     #3
    STATE_SAFEOP    = pysoem.SAFEOP_STATE   #4
    STATE_OP        = pysoem.OP_STATE       #8
    STATE_ERROR     = pysoem.STATE_ERROR    #16
    STATE_ACK       = pysoem.STATE_ACK      #16   
