#!/usr/bin/env python3.4

from tlcl.targets.python34.base import *
from tlcl.targets.python34.builtin import *

if __name__ == '__main__':
    i = Int(0x1020abcd)
    print('{:d}'.format(i))