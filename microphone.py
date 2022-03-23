import rp2
import array
from machine import Pin
from uctypes import addressof
import micropython

bit_sample_freq = 3_072_000 # PDM clock frequency Hz
steps = 8 # PIO clock steps per PDM clock cycle
pdm_clk = Pin(23)
pdm_data = Pin(22)

# 8 word raw sample buffer matching size joined RX FIFO
sample_buf = array.array('I', [0 for _ in range(8)])

# sample buffer
buf_len = 1024
buf0 = array.array('B', [0 for _ in range(buf_len)])
buf1 = array.array('B', [0 for _ in range(buf_len)])

# sample buffer wrapper                     [byte offset]
#   data[0] = buffer length                 [0]
#   data[1] = active buffer (0 or 1)        [4]
#   data[2] = index of current sample       [8]
#   data[3] = address of start of buffer 0  [12]
#   data[4] = address of start of buffer 1  [16]
data = array.array('I', [buf_len, 0, 0, addressof(buf0), addressof(buf1)] )

# tracks current/last active buffer
active_buf = 0

# sample PDM microphone using PIO
@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW, out_init=rp2.PIO.IN_LOW, fifo_join=rp2.PIO.JOIN_RX)
def sample() -> uint:
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

# count bits in 8 word sample and store into active buffer
# (python variants take longer than the sampling period)
#   r0 = sample_buf (8 word array)
#   r1 = data array
@micropython.asm_thumb
def store_pcm_sample(r0, r1) -> uint:
    # r2 = overloaded scratch variable

    # init
    ldr(r4, [r1, 12])           # r4 = address of start of buffer 0 (data[3])
    ldr(r2, [r1, 4])            # r2 = get active buffer (data[1])
    cmp(r2, 0)                  # if buf0 active
    beq(BUF0)                   #   skip
    ldr(r4, [r1, 16])           #   else: r4 = address of start of buffer 1 (data[4])
    label(BUF0)
    ldr(r3, [r1, 8])            # r3 = get index (data[2])
    add(r4, r4, r3)             # add buf index

    # sample buffer loop (SBL)
    mov(r5, 0)                  # r5 = current sample running set-bit count
    mov(r6, 0)                  # r6 = init index into 8 word sample_buf
    label(SBL_START)            # sample_buf loop START
    cmp(r6, 32)                 # 8 * 4 byte words = 32 bits
    beq(SBL_END)                # end of buffer? GOTO: sample_buf loop END

    # sample loop
    mov(r2, r0)                 # r2 = address of sample_buf
    add(r2, r2, r6)             # add sample_buf index
    ldr(r7, [r2, 0])            # r7 = current sample
    
    # Brian Kernighan method
    # https://developer.arm.com/documentation/ka002486/latest 
    label(SL_START)             # sample loop START
    cmp(r7, 0)                  # if sample decremented to zero
    beq(SL_END)                 # GOTO: Sample Loop END
    add(r5, 1)                  # increment sample set-bit count
    mov(r2, r7)                 # r2 = temp copy of sample
    sub(r2, 1)                  # subtract 1 (reverses LSB)
    and_(r7, r2)                # remove LSB from sample
    b(SL_START)                 # GOTO: Sample Loop START

    label(SL_END)               # sample loop END
    add(r6, 4)                  # increment sample counter one word
    b(SBL_START)                # GOTO: sample_buf loop STARTs

    label(SBL_END)              # sample buffer loop END

    # store sample set-bit count into active buf[index]
    strb(r5, [r4, 0])           # buf is a Byte array

    # increment and store buf index 
    ldr(r2, [r1, 0])            # r2 = buf_len
    add(r3, 1)                  # increment     
    cmp(r3, r2)                 # if index = buf_len?
    bne(SKIP_RESET)             #   GOTO: SKIP_RESET
    mov(r3, 0)                  # re-init index = 0

    # swap buffers
    ldr(r2, [r1, 4])            # r2 = get active buffer (to invert)
    cmp(r2, 0)
    beq(BUF1)                   # if buffer 0 is not active
    mov(r2, 0)                  #   make buffer 0 active
    b(UPD_BUF)
    label(BUF1)
    mov(r2, 1)                  #   else: make buffer 1 active
    label(UPD_BUF)
    str(r2, [r1, 4])            # store active buffer

    label(SKIP_RESET)
    str(r3, [r1, 8])            # store buf index back to data

# irq handler
#   get samples and store in buffer
#   p = irq (passed by StateMachine.irq)
def irq_handler(p):
    global active_buf
    sm.get(sample_buf)
    store_pcm_sample(sample_buf, data)
    # has active buffer switched?
    if active_buf != data[1]:
        # handle (now) inactive buffer
        micropython.schedule(buffer_handler, active_buf)
        active_buf = data[1]

# write samples out to wav file
f = 'output.wav'
from wavsimple import wav
w = wav('output.wav')
record_flag = False

def buffer_handler(inactive_buf):
    global record_flag
    if record_flag:
        w.write(eval(f'buf{inactive_buf}'))

# init and start the statemachine
sm = rp2.StateMachine(0, sample, freq=bit_sample_freq*steps, set_base=pdm_clk, in_base=pdm_data)
# hard interupt flag causes lockup?
sm.irq(handler=irq_handler) #, hard=True)
sm.active(True)

from time import sleep
sleep(1)
record_flag = True
sleep(10) # record 10 seconds of audio
record_flag = False
w.close()