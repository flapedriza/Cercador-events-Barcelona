#!/usr/bin/python
# -*- coding: utf-8 -*-
from cerca import *

lat = 41.3881262
lon = 2.1684163

ests = get_estacions()
parks = get_aparcaments()

park_prop = aparcaments_a_prop(parks, lat, lon)

est_prop = bicing_a_prop(ests, lat, lon)

print('Num. aparcaments {}'.format(len(park_prop)))
print('Num. estacionss {}'.format(len(est_prop)))

print(park_prop[0])

print(est_prop[0])