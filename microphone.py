import rp2
import array
from machine import Pin

buf_len = 1024 # bytes
buf = array.array('B', [0 for _ in range(buf_len)])
pointer = 0

# count set bits in word
#   asm is several times faster 
#   than tested python options
@micropython.asm_thumb
def bcount(r0):
    mov(r1, 0)      # r1 = set bit counter = 0
    label(LOOP)
    cmp(r0, 0)      # value is, or is decremented to, 0?
    beq(END)        # goto END if it EQuals 0
    add(r1, 1)      # increment bit count
    mov(r2, r0)     # temp copy of value
    sub(r2, 1)      # subtracting 1 reverses LSB
    and_(r0, r2)    # remove LSB from value
    b(LOOP)         # goto LOOP
    label(END)
    mov(r0, r1)     # return count as r0

# acquire pdm samples
#   into 8 word FIFO
clockspeed = int(3_072_000) # 3.072e6
steps = 8 # cpu steps per sample cycle
pdm_clk = Pin(23)
pdm_data = Pin(22)

@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW, out_init=rp2.PIO.IN_LOW, fifo_join=rp2.PIO.JOIN_RX)
def pdm():
    set(y, 8)                   # no. of word length samples
    label("WORDSTART")
    set(x, 30)                  # 32 bits per sample (- 2)
    label("SAMPLE")
    set(pins, 1)            [2] # set clock pin high
    in_(pins, 1)                # sample data pin into ISR 
                                # (>105ns after rising clock edge)
    set(pins, 0)            [2] # set clock pin low
    jmp(x_dec, "SAMPLE")        # loop
    # last bit sample 3 steps shorter accomodating
    # push, jmp and (re-)set x loop counter
    # TODO: accomodate irq & set y loop counter 
    #       (+2 instruction per 32 bit cycle) 
    set(pins, 1)            [2]
    in_(pins, 1)
    set(pins, 0)
    push(noblock)               # push ISR to to RX FIFO
    jmp(y_dec, "WORDSTART")
    irq(rel(0))                 # raise irq - consume RX FIFO in main

# irq handler
#   retrieve 8 word FIFO into intermediate buffer
#   count bits and stuff buffer 
sample_buf = array.array('I', [0 for _ in range(8)])

def irq_handler(p):
    global sample_buf, pointer, pointer
    sm.get(sample_buf)
    # TODO: implement without mem alloc and enable hard irq
    #       then recheck timing
    buf[pointer] = sum(map(bcount, sample_buf))
    pointer += 1 if pointer<buf_len-1 else -pointer

# init and start the statemachine
sm = rp2.StateMachine(0, pdm, freq=clockspeed*steps, set_base=pdm_clk, in_base=pdm_data)
sm.irq(handler=irq_handler) #, hard=True)
sm.active(True)

# time filling buffer ~= 0.28s
# whereas I expect ~= 0.085s
# i.e. around 3.2 x slower than expected?
import time
time.sleep(1) # wait until sm initialised and running
st = time.ticks_us()
sp = pointer
while pointer != sp: pass
f'{time.ticks_diff(time.ticks_us(), st)/1e6:.4f} seconds'
