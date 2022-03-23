from time import sleep
from wavsimple import wav

# import and init the library
import st34dt05a as pdm

w = wav('output.wav')
record_flag = False

def buffer_handler(inactive_buf):
    global record_flag
    if record_flag:
        w.write(eval(f'pdm.buf{inactive_buf}'))

# assign the buffer handler
pdm.buffer_handler = buffer_handler

# start the state machine
pdm.sm.active(True)
sleep(1) # takes some time for StateMachine to start

# record and save 10 seconds of audio samples
record_flag = True
sleep(10) # record 10 seconds of audio
record_flag = False
w.close()