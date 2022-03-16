
import rp2
import array
from machine import Pin
from uctypes import addressof

buf_len = 1024 # bytes

# count set bits in word ----------------------------------
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
# ---------------------------------------------------------

# decimate sample and store to buffer ---------------------
# 32 bytes of pdm data into 1 sample byte
# 
# data[0] = buffer length
# data[1] = sample bit counter (in bytes i.e. /8)
# data[2] = pointer
# data[3] = pointer to buffer
buf = bytearray(buf_len)
data = array.array('i', [buf_len, 32, 0, addressof(buf)])

# r0 = data array
# r1 = sample bits
@micropython.asm_thumb
def push(r0, r1):
    ldr(r2, [r0, 0])        # r2 = buf_len
    ldr(r3, [r0, 4])        # r3 = sample bit counter
    ldr(r4, [r0, 8])        # r4 = sample pointer
    ldr(r5, [r0, 12])       # r5 = start of buffer
    add(r5, r5, r4)         # offset r5 by sample pointer
    cmp(r3, 32)
    bne(NOCLEARSAMPLE)      # if this is a new sample slot
    mov(r6, 0)
    strb(r6, [r5, 0])       # zero it, in case this is an overwrite
    label(NOCLEARSAMPLE)
    ldrb(r6, [r5, 0])       # load the buffer value from pointer address into r6
    add(r6, r6, r1)         # add new sample bits (r1) to current sample
    strb(r6, [r5, 0])       # store the new value back into the buffer
    sub(r3, 1)              # decrement sample bit counter
    cmp(r3, 0)          
    bne(BIT_COUNTER)        # if zero
    add(r4, r4, 1)          # increment sample pointer
    cmp(r4, r2)
    blt(SAMPLE_POINTER)     # if sample pointer = buffer length 
    mov(r4, 0)              # reset sample pointer to beginning of buffer
    label(SAMPLE_POINTER)
    str(r4, [r0, 8])        # save the updated sample pointer back to array
    mov(r3, 32)             # reset sample bit counter
    label(BIT_COUNTER)
    str(r3, [r0, 4])        # save the updated sample bit counter back to array
# -----------------------------------------

# acquire samples -------------------------
# FIFO = 4 (or 8) words
# 1 word = 4 bytes = 32 bits
clockspeed = int(3_072_000) # 3.072e6
steps = 8 # cpu steps per sample cycle
pdm_clk = Pin(23)
pdm_data = Pin(22)

@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW, out_init=rp2.PIO.IN_LOW)#, fifo_join=rp2.PIO.JOIN_RX)
def pdm():
    # set(y, 8)                   # no. of word length samples
    # label("WORDSTART")
    set(x, 30)                  # bits per sample - 2
    label("SAMPLE")
    set(pins, 1)            [2] # set clock pin high
    in_(pins, 1)                # sample data pin into ISR 
                                # (>105ns after rising clock edge)
    set(pins, 0)            [2] # set clock pin low
    jmp(x_dec, "SAMPLE")        # loop
    # last sampling 3 steps shorter to accomodate
    # push, irq and (re-)set x loop counter 
    set(pins, 1)            [2]
    in_(pins, 1)
    set(pins, 0)
    push(noblock)               # push ISR to to RX FIFO
    # jmp(y_dec, "WORDSTART")
    irq(rel(0))                 # raise irq - consume RX FIFO in main

sm = rp2.StateMachine(0, pdm, freq=clockspeed*steps, set_base=pdm_clk, in_base=pdm_data)
# sm.irq(handler=lambda p: push(data, bcount(sm.get())))
sm.irq(handler=lambda p: print(sm.get()))
sm.active(True)
# -----------------------------------------
