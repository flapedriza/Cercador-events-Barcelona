#!/usr/bin/python3
# -*- coding: utf-8 -*-
import argparse
import webbrowser
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

FORMAT_DATA = '%d/%m/%Y'


def to_date(x, format_data=FORMAT_DATA):
    return datetime.strptime(x, format_data).date()


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
    Decorador per a calcular el temps emprat en executar un mètode
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
    Càlcul de la distància entre dos punts geogràfics
    mitjançant la fórmula del Haversine
    :param lat: Latitud del primer punt geogràfic
    :param lon: Longitud del primer punt geogràfic
    :param lat2: Latitud del segon punt geogràfic
    :param lon2: Longitud del segon punt geogràfic
    :return: Distància
    """
    radi_terra = 6367.4447
    lat, lon, lat2, lon2 = map(radians, [lat, lon, lat2, lon2])

    dlat = lat2 - lat
    dlon = lon2 - lon
    a = sin(dlat / 2) ** 2 + cos(lat) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))

    return c * radi_terra


def insert(elem, llista, start=None, end=None):
    """
    Inserta una tupla (ordre, element) en una llista d'elements ordenada
    pel primer element.
    :param elem: Element a insertar
    :param llista: Llista ordenada de tuples (ordre, element)
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


def amb_lloc(ests):
    return [x for x in ests if x.disponible() and x.te_llocs()]


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

RUTA_ESDEVENIMENTS = 'search/queryresponse/list/list_items/row'

STRING_FORM = re.compile(r'[\"\']?\w+[\s\w*]*[\"\']?')


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
                    to_date(data)

    def aparcaments_propers(self, park):
        """
        Retorna una llista amb tots els aparcaments a menys de 500m del event
        :param park: Llista d'aparcaments
        :return: @description
        """
        return aparcaments_a_prop(park, self.lat, self.lon)

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
        raise Exception("El format del paràmetre key no és correcte")


def entre_dates(es, dat):
    if isinstance(dat, tuple):
        data = to_date(dat[0])
        data_inici = data + timedelta(days=dat[1])
        data_fi = data + timedelta(days=dat[2])
    elif isinstance(dat, str):
        data = data_inici = data_fi = to_date(dat)
    else:
        raise Exception('Format del paràmetre date no vàlid')

    if data_inici <= es.data_fi and data_fi >= es.data_inici:
        if es.data_inici == date.min:
            dif = timedelta.max
        else:
            diff1 = abs(data - es.data_inici)
            diff2 = abs(data - es.data_fi)
            dif = min(diff1, diff2)
        return dif, True
    else:
        return timedelta.max, False


@comptatemps
def esdeveniments_periode(esdev, dates):
    ret = []
    if isinstance(dates, list):
        for e in esdev:
            llista = map(lambda x: entre_dates(e, x), dates)
            dif = llista[0][0]
            overlaps = False
            for l in llista:
                if l[1]:
                    overlaps = True
                    if l[0] < dif:
                        dif = l[0]
            if overlaps:
                insert((dif, e), ret)

    elif isinstance(dates, str) or isinstance(dates, tuple):
        for e in esdev:
            tupl = entre_dates(e, dates)
            if tupl[1]:
                insert((tupl[0], e), ret)
    else:
        raise Exception("El format del paràmetre date no és correcte")
    return [l[1] for l in ret]


#######################################
################# HTML ################
#######################################

def base_template():
    with open('templates/table.html', 'r') as templ:
        template = templ.read()
    return template


def row_template():
    with open('templates/row.html', 'r') as templ:
        template = templ.read()
    return template


def genera_ul(llista):
    ll = '\t<ul>\n'
    for elem in llista:
        ll += '\t\t<li>' + elem.__str__() + '</li>\n'
    ll += '\t</ul>'
    return ll


def llista_bicing(bicings):
    ll = '\t<ul>\n<li>Estacions amb bicis:\n'
    ll += genera_ul(bicings[0])
    ll += '</li>\n<li>Estacions amb lloc:\n'
    ll += genera_ul(bicings[1])
    ll += '</li>\n</ul>'
    return ll


def genera_fila(esdeveniment, bicing, parking):
    template = row_template()
    bicing = esdeveniment.bicing_propers(bicing)
    parking = esdeveniment.aparcaments_propers(parking)
    llista_bicis = llista_bicing(bicing)
    llista_parkings = genera_ul(parking)
    data_inici = 'Permanent' if esdeveniment.data_inici == date.min else \
        esdeveniment.data_inici.strftime('%d/%m/%Y')
    data_fi = 'Permanent' if esdeveniment.data_fi == date.max else \
        esdeveniment.data_fi.strftime('%d/%m/%Y')
    template = template.format(esdeveniment.nom,
                               esdeveniment.lloc,
                               data_inici,
                               data_fi,
                               esdeveniment.barri,
                               esdeveniment.adreça,
                               esdeveniment.info_interes,
                               llista_parkings,
                               llista_bicis,
                               esdeveniment.url_mes_info)
    return template


def genera_taula(llista_esd, bicings, parkings):
    template = base_template()
    files = ''
    for esd in llista_esd:
        files += genera_fila(esd, bicings, parkings) + '\n'
    return template.format(files)


@comptatemps
def genera_fitxer(llesd, bicis, parkings):
    taula = genera_taula(llesd, bicis, parkings)
    with open('resultat.html', 'w') as fitxer:
        fitxer.write(taula)


#######################################
############### ARGPARSE ##############
#######################################

parser = argparse.ArgumentParser(description="Cerca esdeveniments a la ciutat"
                                             "de barcelona a partir de la seva "
                                             "descripció, ubicació o data")

parser.add_argument('--key', '-k', help='Termes de cerca', type=str, default='',
                    required=False)
parser.add_argument('--date', help='Dates a buscar', type=str, default='',
                    required=False)
parser.add_argument('--debug', '-d', action='store_true', help='Mode debug')

parser.add_argument('--open', '-o', action='store_true',
                    help='Obrir fitxer HTML al acabar')


@comptatemps
def main():
    parsed = parser.parse_args()
    global MODE_DEBUG
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

    if parsed.key:
        try:
            esdeveniments = busca_esdeveniments(literal_eval(parsed.key),
                                                esdeveniments)
        except Exception as ex:
            print(ex)
            exit()
    if parsed.date:
        try:
            esdeveniments = esdeveniments_periode(esdeveniments,
                                                  literal_eval(parsed.date))
        except Exception as ex:
            print(ex)
            exit()
    print('Generant taula HTML...')
    genera_fitxer(esdeveniments, estacions, aparcaments)
    if parsed.open:
        webbrowser.open('resultat.html')


if __name__ == "__main__":
    main()
