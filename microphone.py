import rp2
import array
from machine import Pin
from uctypes import addressof

# acquire pdm samples
#   into 8 word FIFO
clockspeed = 3_072_000 # PDM clock speed
steps = 8 # PIO clock steps per PDM clock cycle
pdm_clk = Pin(23)
pdm_data = Pin(22)
sample_buf = array.array('I', [0 for _ in range(8)])

# join RX/TX 4 word buffers into one 8 word RX buffer
@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW, out_init=rp2.PIO.IN_LOW, fifo_join=rp2.PIO.JOIN_RX)
def sample():
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


# sample buffer
buf_len = 1024
buf = array.array('B', [0 for _ in range(buf_len)])

# buffer data wrapper
#   data[0] = buffer length
#   data[1] = index of current sample
#   data[2] = address of start of buffer
data = array.array('I', [buf_len, 0, addressof(buf)] )

# r0 = sample_buf (8 word array)
# r1 = data array
@micropython.asm_thumb
def push(r0, r1):
    # r2 = overloaded scratch variable

    # init
    ldr(r3, [r1, 4])            # r3 = get buf index (data[1])
    ldr(r4, [r1, 8])            # r4 = address of start of buffer (data[2])
    add(r4, r4, r3)             # add buf index

    # sample buffer loop (SBL)
    mov(r5, 0)                  # r5 = current sample running set-bit count
    mov(r6, 0)                  # r6 = init pointer into 8 word sample_buf
    label(SBL_START)            # sample_buf loop START
    cmp(r6, 32)                 # 8 * 4 byte words = 32 bits
    beq(SBL_END)                # end of buffer? goto: sample_buf loop END

    # sample loop
    mov(r2, r0)                 # r2 = address of sample_buf
    add(r2, r2, r6)             # add sample_buf pointer
    ldr(r7, [r2, 0])            # r7 = current sample

    label(SL_START)             # sample loop START
    cmp(r7, 0)
    beq(SL_END)
    add(r5, 1)                  # increment bit counter
    mov(r2, r7)                 # temp copy of sample
    sub(r2, 1)                  # subtract 1 reverses LSB
    and_(r7, r2)                # remove LSB from sample
    b(SL_START)

    label(SL_END)               # sample loop END
    add(r6, 4)                  # increment sample counter one word
    label(SBL_END)              # sample buffer loop END

    # store sample bitcount (r5) into buffer[pointer] (r4)
    strb(r5, [r4, 0])           # buf is a Byte array

    # increment pointer
    ldr(r2, [r1, 0])            # r2 = buf_len
    add(r3, 1)                  # increment     
    cmp(r3, r2)                 # skip pointer = buf_len, else               
    beq(SKIP_ZERO)
    mov(r2, 0)                  # loop to start of buffer
    label(SKIP_ZERO)
    str(r3, [r1, 4])            # store pointer back to array


def irq_handler(p):
    sm.get(sample_buf)
    # push(sample_buf, data)

# init and start the statemachine
sm = rp2.StateMachine(0, sample, freq=clockspeed*steps, set_base=pdm_clk, in_base=pdm_data)
sm.irq(handler=irq_handler) #, hard=True)
sm.active(True)

# # timing test
# import time
# time.sleep(1) # wait for statemachine to initialise
# st = time.ticks_us()
# sp = pointer
# while pointer != sp: 
#     pass
# f'{time.ticks_diff(time.ticks_us(), st)/1e6:.4f} seconds'
