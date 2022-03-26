from time import sleep
from wavsimple import wav
from machine import Pin
import st34dt05a as pdm

pdm_clk = Pin(23)
pdm_data = Pin(22)

# wav file
w = wav('output.wav')
record_flag = False

def buffer_handler(inactive_buf):
    global record_flag
    if record_flag:

        w.write(pdm.get_buffer(inactive_buf))

pdm.start(pdm_clk, pdm_data, handler=buffer_handler)

sleep(1) # takes some time for StateMachine to start

# record and save 10 seconds of audio samples
record_flag = True
sleep(10) # record 10 seconds of audio
record_flag = False
w.close()