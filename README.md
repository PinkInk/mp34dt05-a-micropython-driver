# mp34dt05-a microphone micropython
Read the MP34DT05-A PDM Microphone on the Arduino Nano RP2040 Connect 
development board.

Samples 256 bits (8 No. 4 byte words - the capacity of combined RX & TX buffers) 
using PIO.  Counts set-bits and stores a 1-byte/8-bit PCM sample in the current 
of two (default 1kB) buffers.  Switches buffers and calls an (optional) handler, 
via soft-irq, when each buffer is filled.  Assembly is used for counting and 
storring samples, for performance.

`test.py` is a proof of concept writing ~10 second of audio to output.wav via
wavsimple.py (an optional, and very crude, component).

Bits-per-sample is fixed, no decimation or further processing occurs.

Audio quality is terrible however the spoken word is easily discernable = "great success".

## Usage
Copy st34dt05a.py to board root folder, or `/lib`.

Import module:
```python
import st34dt05a as pdm
```

Define pins and handler function.  The handler function is called as a soft irq
when each of the buffers is filled, and passed the buffers index (0 or 1).  The 
utility function get_buffer(index) returns the actual buffer.
```python
pdm_clk = Pin(23) # mp34dt05-a clock pin
pdm_data = Pin(22) # mp34dt05-a data pin

def buffer_handler(inactive_buf):
    data = pdm.get_buffer(inactive_buf)
    # do something with the data
```

Default bit sampling rate is 3.072MHz, resulting in a 12KHz 8 bit PCM sample rate,
and can be adjusted by setting `pdm.bit_sample_freq` prior to starting sampling:
```python
pdm.bit_sample_freq = 8_000 * 256 # 2.048MHz, results in 8kB/s audio
```

Default buffer length is 1024 bytes, and can be adjusted by setting `pdm.buf_len`
prior to starting sampling:
```python
pdm.buf_len = 2048 # bytes
```

Initialise and start the state machine (i.e. start acquiring samples into buffers), 
handler is optional:
```python
pdm.init(pdm_clk, pdm_data, handler=buffer_handler)
pdm.start()
```

It may be useful to implicitly cease calling the soft irq buffer_handler by way
of stopping the state machine, in the case where a blocking operation e.g. long
file write, is required - otherwise the soft irq queue may be overrun:
```python
pdm.stop()
```

## References
mp34dt05-a: https://www.st.com/resource/en/datasheet/mp34dt05-a.pdf

Arduino nano rp2040 connect schematic: https://docs.arduino.cc/hardware/nano-rp2040-connect#resources

PDM clock frequencies: https://3cfeqx1hf82y3xcoull08ihx-wpengine.netdna-ssl.com/wp-content/uploads/2016/05/AN-000111-PDM-Decimation-v1.0.pdf

Fast filtering: https://github.com/peterhinch/micropython-filters

G.711 codecs: https://github.com/dystopiancode/pcm-g711/tree/master/pcm-g711

### Notes

Buffer handler, with the default sample rates and buffer length, must
complete in less than .085 seconds (the time taken to fill a 1kB buffer).
