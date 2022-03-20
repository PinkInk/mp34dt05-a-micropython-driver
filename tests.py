# timing test
#   expect cira 0.085s to fill 1kB buffer + timing overhead
#   python PDM->PCM and store variants took 4-5 times longer
#   assembly PDM->PCM and store variants time @ ~0.095 seconds
#       which matches timing of simply incrementing a counter on sm.irq 
import time
st = time.ticks_us()
sp = data[2]
while data[2] != sp: 
    pass

f'{time.ticks_diff(time.ticks_us(), st)/1e6:.4f} seconds'
