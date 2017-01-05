#!/usr/bin/python
# -*- coding: utf-8 -*-
from math import radians, sin, cos, sqrt, asin
from urllib.request import urlopen
import xml.etree.ElementTree as XML
import datetime
import time

MODE_DEBUG = True
#######################################
################ Utils ################
#######################################
def comptatemps(metode):
    def temps(*args, **kwargs):
        start = time.time()
        res = metode(*args, **kwargs)
        end = time.time()
        if MODE_DEBUG:
            print ('{}: {} segons' \
                .format(metode.__name__, end-start))
        return res
    return temps

def haversine(lat, lon, lat2, lon2):
    """
    Càlcul de la distància entre un punt geogràfic i l'estació
    mitjançant la fórmula de Haversine
    :param lat: Latitud del primer punt geogràfic
    :param lon: Longitud del primer punt geogràfic
    :param lat2: Latitud del segon punt geogràfic
    :param lon2: Longitud del segon punt geogràfic
    :return: Distància
    """
    RADI_TERRA = 6367.4447

    lat, lon, lat2, lon2 = map(radians, [lat, lon, lat2, lon2])

    dlat = lat2 - lat
    dlon = lon2 - lon
    a = sin(dlat / 2) ** 2 + cos(lat) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))

    return c * RADI_TERRA

    

def insert(elem, llista, start=None, end=None):
    """
    Inserta una tupla (distància, element) en una llista d'elements ordenada
    per distància.
    :param elem: Element a insertar
    :param llista: Llista ordenada de tuples (distància, estació)
    :param start: Paràmetre opcional per a les crides recursives
    :param end: Paràmetre opcional per a les crides recursives
    """
    if start is None:
        start = 0
    if end is None:
        end = len(llista) - 1
    middle = start + int((end - start) / 2)

    if len(llista) == 0:
        llista.append(elem)
        return
    if elem[0] > llista[end][0]:
        llista.insert(end + 1, elem)
        return
    if elem[0] <= llista[start][0]:
        llista.insert(start, elem)
        return
    if start >= end:
        return
    if elem[0] < llista[middle][0]:
        insert(elem, llista, start, middle - 1)
        return
    if elem[0] > llista[middle][0]:
        insert(elem, llista, middle + 1, end)
        return
    

    
#######################################
############## ESTACIONS ##############
#######################################

URL_BICING = 'http://wservice.viabicing.cat/getstations.php?v=1'


class Estacio(object):
    """
    Estació de bicing
    """

    attrs = {
        'id': int,
        'street': str,
        'lat': float,
        'long': float,
        'streetNumber': str,
        'status': str,
        'slots': int,
        'bikes': int,
    }

    def __str__(self):
        num = self.streetNumber if self.streetNumber else 'S/N'
        return '{} - {}, {} ({} llocs | {} bicis)' \
            .format(self.id, self.street, num, self.slots, self.bikes)

    def disponible(self):
        return self.status == 'OPN'

    def te_llocs(self):
        return self.slots > 0

    def te_bicis(self):
        return self.bikes > 0

    def distancia(self, lat, lon):
        return haversine(self.lat, self.long, lat, lon)


def amb_bicis(estacions):
    return [x for x in estacions if x.disponible() and x.te_bicis()]

@comptatemps
def amb_lloc(estacions):
    return [x for x in estacions if x.disponible() and x.te_llocs()]

@comptatemps
def bicing_a_prop(estacions, lat, lon, dist=0.5):
    ret = []
    for e in estacions:
        dis = e.distancia(lat, lon)
        if dis <= dist:
            insert((dis, e), ret)
            if len(ret) == 5:
                break

    return [y for (x, y) in ret]

@comptatemps
def get_estacions(url=URL_BICING):
    """
    Obté una llista amb totes les dades de les estacions de bicing del web
    service de l'ajuntament de Barcelona.
    :param url: URL del servei de l'ajuntament de Barcelona
    :return: Llista amb les dades de totes les estacions de Bicing de Barcelona
    """
    ret = []
    with urlopen(url) as openurl:
        xml = openurl.read()
    reader = XML.fromstring(xml)
    for elem in reader.findall('station'):
        e = Estacio()
        for k, v in Estacio.attrs.items():
            text = elem.find(k).text
            e.__setattr__(k, v(text))
        ret.append(e)
    return ret


#######################################
############# APARCAMENTS #############
#######################################

URL_APARCAMENTS = 'http://www.bcn.cat/tercerlloc/Aparcaments.xml'


class Aparcament(object):
    attrs = {
        'id': int,
        'name': str,
        'address': str,
        'gmapx': float,
        'gmapy': float,
    }

    def __str__(self):
        return '{} - {}'.format(self.name, self.address)

    def distancia(self, lat, lon):
        return haversine(self.gmapx, self.gmapy, lat, lon)

@comptatemps
def aparcaments_a_prop(aparcaments, lat, lon, d=0.5):
    ret = []
    for a in aparcaments:
        dis = a.distancia(lat, lon)
        if dis <= d:
            insert((dis, a), ret)

    return [y for (x, y) in ret]

@comptatemps
def get_aparcaments(url=URL_APARCAMENTS):
    ret = []
    with urlopen(url) as openurl:
        xml = openurl.read()
    reader = XML.fromstring(xml)
    parkings = reader.findall('search/queryresponse/list/list_items/row')
    for park in parkings:
        p = Aparcament()
        for k, v in Aparcament.attrs.items():
            text = park.find('item/' + k).text
            p.__setattr__(k, v(text))
        ret.append(p)
    return ret
    
#######################################
############ ESDEVENIMENTS ############
#######################################

URL_ESDEVENIMENTS = 'http://www.bcn.cat/tercerlloc/agenda_cultural.xml'

FORMAT_DATA = '%d/%m/%Y'

RUTA_ROWS = 'search/queryresponse/list/list_items/row'

to_date = lambda x: datetime.datetime.strptime(x, FORMAT_DATA).date()

class Esdeveniment(object):
    def __init__(self, xmlel):
        xmlel = xmlel.find('item')
        self.nom = xmlel.find('name').text
        self.adreça = xmlel.find('address').text
        interes = xmlel.find('interestinfo/item')
        if interes:
            self.info_interes = interes.find('label').text + ': ' + \
                interes.find('interinfo')
        else:
            self.info_interes = None
        
