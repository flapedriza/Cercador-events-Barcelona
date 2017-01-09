#!/usr/bin/python
# -*- coding: utf-8 -*-
from cerca import *

lat = 41.3881262
lon = 2.1684163

ests = get_estacions()
parks = get_aparcaments()
esdev = get_esdeveniments()
es = set()
for i in range(5):
  es.add(esdev.pop())

genera_fitxer(es, ests, parks)


