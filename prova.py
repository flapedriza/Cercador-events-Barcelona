#!/usr/bin/python
# -*- coding: utf-8 -*-
from cerca import *

lat = 41.3881262
lon = 2.1684163

ests = get_estacions()
parks = get_aparcaments()
esdev = get_esdeveniments()

park_prop = aparcaments_a_prop(parks, lat, lon)

est_prop = bicing_a_prop(ests, lat, lon)


