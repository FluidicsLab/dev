
from time import time_ns
import pysoem

class DS402:

    MODE_CSP                = 8     # cyclic synchronous position
    MODE_CSV                = 9     # cyclic synchronous velocity
    MODE_CST                = 10    # cyclic synchronous torque
    MODE_CSTCA              = 11    # cyclic synchronous torque with commutation angle

    # status word
    NOT_READY_TO_SWITCH_ON  = 0     # xxx0 xxxx x0xx 0000
    READY_TO_SWITCH_ON      = 1     # xxx0 xxxx x01x 0001
    SWITCHED_ON             = 2     # xxx0 xxxx x1xx 0011
    OPERATION_ENABLED       = 4     # xxx0 xxxx x1xx 0111
    FAULT                   = 8
    
    QUICK_STOP              = 32
    SWITCH_ON_DISABLED      = 64    # xxx0 xxxx x1xx 0000
    WARNING                 = 128

    # control word LoByte
    FAULT_RESET             = '10000000'    # 1xxx xxxx 
    SHUTDOWN                = '00000110'    # 0xxx x110
    SWITCH_ON               = '00000111'    # 0xxx 0111
    ENABLE_OPERATION        = '00001111'    # 0xx0 1111
    
    """
    status                                              control

    xxx0 xxxx x0xx 0000     not ready to switch on
               |                                        
    xxx0 xxxx x1xx 0000     switch on disabled
                      |                                 0000 0000 0xxx x110       shutdown
    xxx0 xxxx x01x 0001     ready to switch on
                     |                                  0000 0000 0xxx x111       switch on
    xxx0 xxxx x1xx 0011     switched on
                    |                                   0000 0000 0xx0 1111       enable operation
    xxx0 xxxx x1xx 0111     operation enabled


    xxx0 xxxx x0xx 1111     fault reaction active
    xxx0 xxxx x0xx 1000     fault                       0000 0000 1xxx xxxx       fault reset

    
                                                        0000 0000 0xxx xx0x       disable voltage
                                                        0000 0000 0xxx x01x       
    """
    
    status = [
        NOT_READY_TO_SWITCH_ON, READY_TO_SWITCH_ON, SWITCHED_ON, OPERATION_ENABLED, 
        FAULT, QUICK_STOP, SWITCH_ON_DISABLED, WARNING]
    
    status_name = [
        'NOT_READ_TO_SWITCH_ON','READY_TO_SWITCH_ON', 'SWITCHED_ON', 'OPERATION_ENABLED', 
        'FAULT', 'QUICK_STOP', 'SWITCH_ON_DISABLED', 'WARNING']
    
    @staticmethod
    def __str__(state):
        return ",".join([f"{DS402.status_name[i]}" 
                        for i,s in enumerate(DS402.status) 
                            if ((s & state) == s) and (s not in [0])
                        ])
    @staticmethod
    def __get__(state):
        return [s for s in DS402.status if ((s & state) == s) and (s not in [0])]

    @staticmethod
    def __has__(value, state):
        return (state | value) == value

    @staticmethod
    def __transit__(value):

        # transition, state, index

        if DS402.__has__(value, DS402.FAULT):
            return [
                (DS402.FAULT_RESET, DS402.SWITCH_ON_DISABLED, 15)
                ]

        if DS402.__has__(value, DS402.OPERATION_ENABLED):
            return [
                (DS402.SWITCH_ON, DS402.SWITCHED_ON, 5), 
                (DS402.SHUTDOWN, DS402.READY_TO_SWITCH_ON, 8)
                ]
        
        if DS402.__has__(value, DS402.SWITCHED_ON):
            return [                
                (DS402.SHUTDOWN, DS402.READY_TO_SWITCH_ON, 6)
                ]

        if DS402.__has__(value, DS402.SWITCHED_ON):
            return [
                (DS402.ENABLE_OPERATION, DS402.OPERATION_ENABLED, 4)
                ]   
        
        if DS402.__has__(value, DS402.READY_TO_SWITCH_ON):
            return [
                (DS402.SHUTDOWN, DS402.SWITCH_ON, 3)
                ]

        if DS402.__has__(value, DS402.SWITCH_ON_DISABLED):
            return [
                (DS402.SHUTDOWN, DS402.READY_TO_SWITCH_ON, 2)
                ]    

        return []    
    
value = int('0000010000100001',2)

trans = DS402.__transit__(value)

print(f"{time_ns()} {trans}")



