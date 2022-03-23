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
output is a 12kHz 8-bit mono audio file.

Audio quality is terrible and the noise ceiling is very high however, since 
voice is easily discernable, I consider it a "great success".

## Notes

PIO doesn't lend itself to being embedded in a micropython class (at least in 
the case of turning this into a driver class) since irq handler can't be passed 
`self`.

## References
mp34dt05-a: https://www.st.com/resource/en/datasheet/mp34dt05-a.pdf

Arduino nano rp2040 connect schematic: https://docs.arduino.cc/hardware/nano-rp2040-connect#resources

PDM clock frequencies: https://3cfeqx1hf82y3xcoull08ihx-wpengine.netdna-ssl.com/wp-content/uploads/2016/05/AN-000111-PDM-Decimation-v1.0.pdf

Fast filtering: https://github.com/peterhinch/micropython-filters