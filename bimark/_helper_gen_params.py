import sys
import numpy as np
import random
def gen_bits(length):
    return "".join([str(random.randint(0,1)) for _ in range(int(length))])
def gen_delta(layers, pattern, const_val, d_min, d_max):
    layers = int(layers)
    if pattern == 'constant':
        return ",".join([str(const_val)] * layers)
    elif pattern == 'increasing':
        arr = np.linspace(float(d_min), float(d_max), layers)
        return ",".join([f"{x:.2f}" for x in arr])
    elif pattern == 'decreasing':
        arr = np.linspace(float(d_max), float(d_min), layers)
        return ",".join([f"{x:.2f}" for x in arr])
    return "1.0"
if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == 'bits': print(gen_bits(sys.argv[2]))
    elif mode == 'delta': print(gen_delta(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6]))
