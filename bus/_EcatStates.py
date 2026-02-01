import pysoem


#pysoem.NONE_STATE     #0
#pysoem.INIT_STATE     #1
#pysoem.PREOP_STATE    #2
#pysoem.BOOT_STATE     #3
#pysoem.SAFEOP_STATE   #4
#pysoem.OP_STATE       #8

#pysoem.STATE_ERROR    #16
#pysoem.STATE_ACK      #16   

class EcatStates:
    
    states = [pysoem.NONE_STATE,pysoem.BOOT_STATE,
              pysoem.INIT_STATE,pysoem.PREOP_STATE,pysoem.SAFEOP_STATE,pysoem.OP_STATE,
              pysoem.STATE_ERROR,pysoem.STATE_ACK]
    
    names = ['NONE','BOOT',
             'INIT','PREOP','SAFEOP','OP',
             'ERROR','ACK']
    
    @staticmethod
    def desc(state, desc=False):
        if not desc:
            return bin(state).replace('0b','').rjust(8,'0')
        return ",".join([f"{EcatStates.names[i]}" 
                         for i,s in enumerate(EcatStates.states) 
                         if ((s & state) == s) 
                         and (s not in [pysoem.NONE_STATE])
                         ])

    @staticmethod
    def has(state, states):
        return (state & states) == state
