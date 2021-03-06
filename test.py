from time import sleep
from wavsimple import wav
from machine import Pin
import st34dt05a as pdm

pcm_rate = 8_000 # Hz - default is 12kHz i.e. 3.072MHz bit-sample rate
pdm.bit_sample_freq = pcm_rate * 256

pdm_clk = Pin(23)
pdm_data = Pin(22)

w = wav('output.wav', SampleRate=pcm_rate)
record_flag = False

def buffer_handler(inactive_buf):
    global record_flag
    if record_flag:
        w.write(pdm.get_buffer(inactive_buf))

pdm.init(pdm_clk, pdm_data, handler=buffer_handler)
pdm.start()

sleep(1) # wait whilst StateMachine inits

record_flag = True
sleep(10)
record_flag = False

w.close()
