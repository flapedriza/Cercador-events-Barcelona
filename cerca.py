#!/usr/bin/python3
# -*- coding: utf-8 -*-
import argparse
import re
import time
import unicodedata
import xml.etree.ElementTree as Xml
from ast import literal_eval
from datetime import date, datetime, timedelta
from math import radians, sin, cos, sqrt, asin
from urllib.request import urlopen

MODE_DEBUG = True

#######################################
################ Utils ################
#######################################

RADI_TERRA = 6367.4447


def elimina_accents(s):
    """
    Elimina tots els accents de l'entrada
    :param s: String amb possibles accents
    :return: String original amb tots els accents eliminats
    """
    s = s.replace('ñ', '\u0001')
    s = s.replace('ç', '\u0002')
    ret = ''.join(c for c in unicodedata.normalize('NFD', s)
                  if unicodedata.category(c) != 'Mn')
    ret = ret.replace('\u0001', 'ñ')
    return ret.replace('\u0002', 'ç')


def comptatemps(metode):
    """
    Decorador per a calcular el temps emprat en exacutar un mètode
    """

    def temps(*args, **kwargs):
        start = time.time()
        res = metode(*args, **kwargs)
        end = time.time()
        if MODE_DEBUG:
            print('{}: {} segons'
                  .format(metode.__name__, end - start))
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
    :param llista: Llista ordenada de tuples (distància, element)
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


def amb_bicis(ests):
    return [x for x in ests if x.disponible() and x.te_bicis()]


@comptatemps
def amb_lloc(ests):
    return [x for x in ests if x.disponible() and x.te_llocs()]


@comptatemps
def bicing_a_prop(ests, lat, lon, dist=0.5):
    ret = []
    for e in ests:
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
    :param url: URL del servei de l'ajuntament de Barcelona (opcional)
    :return: Llista amb les dades de totes les estacions de Bicing de Barcelona
    """
    ret = []
    with urlopen(url) as openurl:
        xml = openurl.read()
    reader = Xml.fromstring(xml)
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

RUTA_APARCAMENTS = 'search/queryresponse/list/list_items/row'


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
def aparcaments_a_prop(park, lat, lon, d=0.5):
    ret = []
    for a in park:
        dis = a.distancia(lat, lon)
        if dis <= d:
            insert((dis, a), ret)

    return [y for (x, y) in ret]


@comptatemps
def get_aparcaments(url=URL_APARCAMENTS):
    """
    Obté una llista amb totes les dades dels aparcaments del web
    service de l'ajuntament de Barcelona.
    :param url: URL del servei de l'ajuntament de Barcelona (opcional)
    :return: Llista amb les dades de tots els aparcaments de Barcelona
    """
    ret = []
    with urlopen(url) as openurl:
        xml = openurl.read()
    reader = Xml.fromstring(xml)
    parkings = reader.findall(RUTA_APARCAMENTS)
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

INICI_INFO_ESDEVENIMENT = 'http://guia.barcelona.cat/ca/detall/'

FORMAT_DATA = '%d/%m/%Y'

RUTA_ESDEVENIMENTS = 'search/queryresponse/list/list_items/row'

STRING_FORM = re.compile(r'[\"\']?\w+[\s\w*]*[\"\']?')


def to_date(x): return datetime.strptime(x, FORMAT_DATA).date()


class Esdeveniment(object):
    def __init__(self, xmlel):
        xmlel = xmlel.find('item')
        self.url_mes_info = INICI_INFO_ESDEVENIMENT + xmlel.items()[0][1]
        self.nom = xmlel.find('name').text.replace('"', '\"')
        try:
            addr = xmlel.find('address').text.strip().replace('"', '\"')
            self.adreça = addr if addr else 'Diferents ubicacions'
        except AttributeError:
            self.adreça = 'N/D'
        try:
            self.barri = xmlel.find('addresses/item/barri') \
                .text.replace('"', '\"')
        except AttributeError:
            self.barri = 'N/D'
        try:
            self.lat = float(xmlel.find('gmapx').text)
            self.lon = float(xmlel.find('gmapy').text)
        except AttributeError:
            self.lat = self.lon = float(0.0)
        try:
            self.lloc = xmlel.find('institutionname').text.replace('"', '\"')
        except AttributeError:
            self.lloc = 'N/D'
        try:
            interes = xmlel.find('interestinfo/item')
            self.info_interes = '{}: {}'.format(interes.find('label').text,
                                                interes.find('interinfo').text)
        except AttributeError:
            self.info_interes = 'N/D'
        data_inici = xmlel.find('begindate')
        if data_inici is not None:
            self.data_inici = to_date(data_inici.text)
            self.data_fi = to_date(xmlel.find('enddate').text)
        else:
            data = xmlel.find('date').text
            if data == 'Acte Permanent':
                self.data_inici = date.min
                self.data_fi = date.max
            else:
                self.data_inici = self.data_fi = \
                    to_date(xmlel.find('date').text)

    @comptatemps
    def aparcaments_propers(self, park):
        """
        Retorna una llista amb tots els aparcaments a menys de 500m del event
        :param park: Llista d'aparcaments
        :return: @description
        """
        return aparcaments_a_prop(park, self.lat, self.lon)

    @comptatemps
    def bicing_propers(self, ests):
        """
        Retorna una tupla que conté una llista amb les estacions de bicing
        amb bicicletes disponibles i les estacions de bicing amb llocs
        disponibles respectivament que es troben a menys de 500m de l'event
        :param ests: Llista d'estacions de bicing
        :return: @description
        """
        ests = bicing_a_prop(ests, self.lat, self.lon)
        return amb_bicis(ests), amb_lloc(ests)


@comptatemps
def get_esdeveniments(url=URL_ESDEVENIMENTS):
    """
    Obté una llista amb totes les dades dels esdeveniments de la ciutat del web
    service de l'ajuntament de Barcelona.
    :param url: URL del servei de l'ajuntament de Barcelona (opcional)
    :return: Llista amb les dades de tots els esdeveniments de Barcelona
    durant l'any actual.
    """
    ret = set()
    with urlopen(url) as openurl:
        xml = openurl.read()
    reader = Xml.fromstring(xml)
    esdevs = reader.findall(RUTA_ESDEVENIMENTS)
    for ev in esdevs:
        e = Esdeveniment(ev)
        ret.add(e)
    return ret


@comptatemps
def busca_esdeveniments(query, esdevs):
    try:
        if STRING_FORM.match(query) is None:
            quey = literal_eval(query)
    except:
        pass

    if isinstance(query, tuple):
        ret = set()
        for elem in query:
            ret = ret.union(busca_esdeveniments(elem,
                                                esdevs.difference(ret)))
        return ret
    elif isinstance(query, list):
        ret = esdevs
        for elem in query:
            ret = busca_esdeveniments(elem, ret)
        return ret
    elif isinstance(query, str):
        ret = set()
        for elem in esdevs:
            cerca = elimina_accents(query.lower())
            font = elimina_accents("{}|{}|{}".format(elem.nom, elem.lloc,
                                                     elem.barri).lower())
            if cerca in font:
                ret.add(elem)
        return ret
    else:
        raise Exception("El format de l'entrada no és correcte")


# TODO
def esdeveniments_periode(esdev, data, marge):
    ret = set()
    for esd in esdev:
        pass


#######################################
############### ARGPARSE ##############
#######################################

parser = argparse.ArgumentParser(description="Cerca esdeveniments a la ciutat"
                                             "de barcelona a partir de la seva "
                                             "descripció, ubicació o data")

parser.add_argument('--key', help='Termes de cerca', type=str, default='',
                    required=True)
parser.add_argument('--date', help='Dates a buscar', type=str, default='',
                    required=True)
parser.add_argument('--debug', '-d', action='store_true', help='Mode debug')

if __name__ == "__main__":
    parsed = parser.parse_args()
    MODE_DEBUG = parsed.debug
    try:
        estacions = get_estacions()
        aparcaments = get_aparcaments()
        print('Obtenint dades dels esdeveniments...')
        esdeveniments = get_esdeveniments()
    except:
        print('No s\'han pogut obtenir les dades d\'interet, comproveu la '
              'vostra connexió')
        exit()

    for i in busca_esdeveniments(literal_eval(parsed.key), esdeveniments):
        print(i.nom, i.lloc, i.adreça, i.data_inici, i.data_fi)
