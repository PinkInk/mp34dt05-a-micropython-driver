# mp34dt05-a micropython driver
Using PIO sample the MP34DT05-A PDM Microphone on the Arduino Nano RP2040 
Connect dev board.

Currently samples 256 bits (8 No. 4 byte words - conveniently the capacity of 
combined PIO RX & TX buffers) using PIO, counts the set-bits in this meta-sample 
and stores the result as a 1-byte/8-bit PCM sample in the current of two 1kb double 
buffers.  Assembler is used for counting and storring samples, for performance.

Once each buffer is full a call to buffer_handler is raised, as a soft-irq, 
to deal with the samples.

As a proof of concept samples are written to output.wav.  Frequency and 
bits-per-sample are fixed, no decimation or further processing is occuring, hence
output is a 12kHz 8-bit mono audio file, from a bit sample rate of 3.072MHz.

Audio quality is terrible however the spoken word is easily discernable - "great success".

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
Start the state machine (i.e. start acquiring samples into buffers):
```python
pdm.start(pdm_clk, pdm_data, handler=buffer_handler)
```

## References
mp34dt05-a: https://www.st.com/resource/en/datasheet/mp34dt05-a.pdf

Arduino nano rp2040 connect schematic: https://docs.arduino.cc/hardware/nano-rp2040-connect#resources

PDM clock frequencies: https://3cfeqx1hf82y3xcoull08ihx-wpengine.netdna-ssl.com/wp-content/uploads/2016/05/AN-000111-PDM-Decimation-v1.0.pdf

Fast filtering: https://github.com/peterhinch/micropython-filters

### Notes

Only (yet) tested at frequency of 3.072MHz bit-samples.  Higher sample rates
may not work properly since the timing of the delay between clock rising edge and
valid sample data (>105ns) was calculated at this frequency only.

It *may* be possible to adjust `pdm.bit_sample_rate` or `pdm.buf_len`, but this
hasn't (yet) been tested.

Buffer handler, with the default sample rates and buffer length, must
complete in less than .085 seconds (time taken to fill a 1kB buffer).

PIO doesn't lend itself to being embedded in a micropython class (at least in 
the case of turning this into a driver class) since irq handler can't be passed 
`self`.
