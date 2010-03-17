#!/usr/bin/env python
"""
This script scrapes data on licenses granted by the Virginia Department of
Alcoholic Beverage Control.

By default, the data is saved to a CSV file, though the ABCScraper
class can be easily hooked into to do with the data what the user wishes.

The ABC has information on two types of licenses on its Web site: retail
licenses (those provided to bars and stores) and banquet licenses (temporary
licenses for special events). Both can be scraped using this script.

Usage:

    $ ./get_licenses.py -t retail # Download retail licenses.
    $ ./get_licenses.py -t banquet # Download banquet licenses.

If no arguments are given, retail licenses are the default.

"""
__author__ = 'Aaron Bycoffe (bycoffe@gmail.com)'
__version__ = '0.1'
__copyright__ = 'Copyright (c) 2010 Aaron Bycoffe'
__license__ = 'Two-clause BSD. See LICENSE.'

import csv
from optparse import OptionParser
import re
import urllib
import urllib2


class ABCScraperError(Exception):
    pass


class ABCScraper(object):

    def __init__(self, city_id, task='retail'):

        # Take care of some differences in how we collect and save
        # the two different types of licenses. Mostly everything else
        # is abstracted to handle either type.
        if task == 'retail':
            self.task = 'licenseedata'
            self.fields = ['Trade Name', 'Mixed Renewal Date', 'License',
                           'Origination Date', 'Establishment Type',
                           'Privilege Description',
                           'Mixed Beverage Privilege Description',
                           'Mixed Privilege Status', 'Mixed Expiration Date',
                           'Effective Date', 'Renewal Date',
                           'Mixed Effective Date', 'Expiration Date', 'Address',
                           'Privilege Status', 'Establishment Sub-Type',
                           'Company Name']
        elif task == 'banquet':
            self.task = 'banquetlist'
            self.fields = ['Trade Name', 'Privilege Status',
                           'Privilege Description', 'Effective Date',
                           'Banquet Dates', 'Location Name', 'Reponsible Person',
                           'Approved Date', 'Address', 'Territory-Agent Name',
                           'Region', 'Expiration Date']
        else:
            raise ABCScraperError('Invalid license type entered. Choices are retail and banquet')

        self.city_id = city_id
        self.url = 'http://www.abc.state.va.us/licenseeSearch/jsp/controller.jsp'


    def get_licensee_numbers(self):
        # The license number is included in the URL
        # querystring listed next to each license.
        return re.findall(r'controller\.jsp\?task=(?:licenseedata|banquetdata)&license=(?P<license>\d+)',
                      self._get_page(self.url, self._url_values()))


    def _get_page(self, url, values):
        req = urllib2.Request(self.url, urllib.urlencode(values))
        response = urllib2.urlopen(req)
        return response.read()


    def _url_values(self):
        values = {'task': self.task,
                  'start': '1',
                  'last': '100000',
                  'currpage': '1',
                  'county': self.city_id,
                  }

        # Somewhat different querystrings are needed depending
        # on the license type being requested.
        if self.task == 'licenseedata':
            values.update({
                'estabTypeChanged': '0',
                'license': '',
                'wbStatus': '',
                'mbStatus': '',
                'esttype': '',
                'estsubtype': '',
                'establishment': '',
                'city': '',
                'zip': '',
                'expDate':'',
                'Submit':'Find',
                'tax': 'displaylist',
                })
        elif self.task == 'banquetlist':
            values.update({
                'frmDate': '',
                'endDate': '',
                'status': '',
            })
        return values


    def _clean_field(self, field):
        field = field.strip()
        field = field.replace('<br>', ' ')
        field = field.replace('&nbsp;', ' ')
        field = re.sub(r'\s\s+', ' ', field)
        return field.strip()


    def get_license_data(self, licensee_id):
        if self.task == 'banquetlist':
            task = 'banquetdata'
        else:
            task = self.task

        values = {'license': licensee_id,
                  'task': task,
                  }
        page = self._get_page(self.url, values)

        table = re.search(r'\<table.*?\<\/table\>', page, re.S).group()
        rows = re.findall('<tr>.*?<\/tr>', table, re.S)[1:]
        data = {}
        for row in rows:
            match = re.search(r'class="Bold">(?P<field>.*?)<\/td>\s+<td>(?P<value>.*?)<\/td>',
                    row, re.S)
            if match:
                groups = match.groupdict()

                field = self._clean_field(groups['field'])
                value = self._clean_field(groups['value'])
                if field in data:
                    field = 'Mixed %s' % field
                data[field] = value
        return data


    def save_data(self, data, filename):
        writer = csv.DictWriter(open(filename, 'a'), self.fields)
        writer.writerow(data)


def _main():
    # The type of license we're inerested in can be given
    # as a command line argument. The default is retail.
    parser = OptionParser()
    parser.add_option('-t',
                      '--type',
                      dest='task',
                      help='banquet or retail')
    options, args = parser.parse_args()
    task = options.task or 'retail'

    filename = (r'retail_licensees.csv' if task == 'retail' else r'banquet_licensees.csv')

    # For a full list of city IDs, parse the City/County select box at 
    # http://www.abc.state.va.us/licenseeSearch/jsp/controller.jsp?task=retaillicense
    city_ids = [117, # Norfolk
                125, # Virginia Beach
                126, # Chesapeake
                124, # Suffolk
                119, # Portsmouth
               ]
    for city_id in city_ids:
        scraper = ABCScraper(city_id, task)
        for number in scraper.get_licensee_numbers():
            data = scraper.get_license_data(number)
            scraper.save_data(data, filename)


if __name__ == '__main__':
    _main()

