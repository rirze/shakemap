# stdlib imports
import sqlite3
import xml.etree.ElementTree as ET
import copy
from collections import OrderedDict
import re
import logging

# third party imports
import numpy as np

# local imports


TABLES = OrderedDict((
    ('station',
     OrderedDict((
         ('id', 'str primary key'),  # id is net.sta
         ('network', 'str'),
         ('code', 'str'),
         ('name', 'str'),
         ('lat', 'float'),
         ('lon', 'float'),
         ('elev', 'float'),
         ('vs30', 'float'),
         ('stddev', 'float'),
         ('instrumented', 'int')
     ))
     ),
    ('imt',
     OrderedDict((
         ('id', 'integer primary key'),
         ('imt_type', 'str')
     ))
     ),
    ('amp',
     OrderedDict((
         ('id', 'integer primary key'),
         ('station_id', 'str'),
         ('imt_id', 'int'),
         ('original_channel', 'str'),
         ('orientation', 'str'),
         ('amp', 'float'),
         ('stddev', 'float'),
         ('flag', 'str')
     ))
     )
))

#
# These are the netid's that indicate MMI data
#
CIIM_TUPLE = ('dyfi', 'mmi', 'intensity', 'ciim')


class StationList(object):
    """
    A class to facilitate reading ShakeMap formatted XML fies of peak
    amplitudes and MMI, and
    produce tables of station data. Seismic stations are considered to
    be 'instrumented'; MMI data is not instrumented and is indicated
    in the ShakeMap XML with a ``netid`` attribute of "DYFI," "MMI,"
    "INTENSITY," or "CIIM."

    .. note::
      Typically the user will call the class method :meth:`fromXML`
      to create a :class:`StationList` object the first time
      a set of station files are processed. (Or, as an alternative,
      the user can call :meth:`loadFromXML` and :meth:`fillTables`
      sequentially.)
      This will create a database at the location specified by the
      ``dbfile`` parameter to :meth:`fromXML`. Subsequent programs
      can use the default constructor to simply load ``dbfile``.

    """

    def __init__(self, db):
        """
        The default constructor reads a pre-built SQLite database of
        station data.

        Args:
            dbfile (str):
                A SQLite database file containing pre-processed
                station data.

        Returns:
            A :class:`StationList` object.

        """
        self.db = db
        self.cursor = self.db.cursor()

    def __del__(self):
        """
        Closes out the database when the object is destroyed.
        """
        self.db.commit()
        self.cursor.close()
        self.db.close()

#    def _load_features(self, xmlfile):
        # each station is a feature in a geojson file
        #        tree = ET.parse(xmlfile)
        #        root = tree.getroot()
        #        imt_translate = {}
        #        for sl in root.iter('stationlist'):
        #            for station in sl:
        #                feature = {'type':'Feature'}
        #                netid = station.attrib['netid']
        #                code = station.attrib['code']
        #                feature['id'] = '%s.%s' % (netid,code)
        #                lat = code = float(station.attrib['lat'])
        #                lon = code = float(station.attrib['lon'])
        #                feature['geometry'] = \
        #                    {'type':'Point','coordinates':[lon,lat]}
        #                properties = {}
        #                properties['name'] = station.attrib['name']
        #                properties['intensity_flag'] = station.attrib['']#??
        #                properties['distance'] = \
        #                    float(station.attrib['distance'])
        #                properties['location'] = station.attrib['loc']
        #                properties['code'] = station.attrib['code']
        #                properties['commType'] = station.attrib['commtype']
        #                properties['source'] = station.attrib['source']
        #                properties['network'] = station.attrib['netid']
        #                properties['instrumentType'] = \
        #                    station.attrib['insttype']
        #                properties['intensity'] = \
        #                    float(station.attrib['intensity'])
        #                channels = []
        #                for comp in station:
        #                    channel = {'name':comp.attrib['name']}
        #                    for component in comp:
        #                        pgmdict, imtset = self._getGroundMotions(
        #                            component, imt_translate)
#        pass

    @classmethod
    def loadFromSQL(cls, sql, dbfile=':memory:'):
        """
        Create a new object from saved SQL code (see :meth:`dumpToSQL`).

        Args:
            sql (str):
                SQL code to create and populate the database
            dbfile (str):
                The path to a file in which the database will reside.
                The default is ':memory:' for an in-memory database.

        Returns:
            :class:`Stationlist` object.
        """

        db = sqlite3.connect(dbfile)
        self = cls(db)
        self.cursor.executescript(sql)
        return self

    def dumpToSQL(self):
        """
        Dump the database as a string of SQL code (see :meth:`loadFromSQL`).

        Args:
            None

        Returns:
            A string of SQL sufficient to restore and repopulate the
            database.
        """

        return "\n".join(list(self.db.iterdump()))

    @classmethod
    def loadFromXML(cls, xmlfiles, dbfile=':memory:'):
        """
        Create a StationList object by reading one or more ShakeMap XML input
        files.

        Args:
            xmlfiles (sequence of str):
                Sequence of ShakeMap XML input files to read.
            dbfile (str):
                Path to a file into which to write the SQLite database.
                The default is ':memory:' for an in-memory database.

        Returns:
            :class:`StationList` object

        """
        # Create the database and tables
        db = sqlite3.connect(dbfile)
        self = cls(db)
        self._createTables()
        return self.addData(xmlfiles)

    def getGeoJson(self):
        jdict = {'type': 'FeatureCollection',
                 'features': []}

        self.cursor.execute(
            'SELECT id, network, code, name, lat, lon, elev, vs30, '
            'instrumented from station'
        )
        sta_rows = self.cursor.fetchall()

        for sta in sta_rows:
            # print('doing station %s' % (str(sta[2])))
            if str(sta[2]).startswith(sta[1] + '.'):
                myid = str(sta[2])
            else:
                myid = sta[1] + '.' + str(sta[2])
            feature = {
                'type': 'Feature',
                'id': myid,
                'properties': {
                    'code': str(sta[2]),
                    'name': sta[3],
                    'instrumentType': 'UNK' if sta[8] is True else 'OBSERVED',
                    'source': sta[1],
                    'network': sta[1],
                    'commType': 'UNK',
                    'location': '',
                    'intensity': None,
                    'intensity_flag': '',
                    'intensity_stddev': None,
                    'pga': None,
                    'pgv': None,
                    'distance': None,
                    'channels': []
                },
                'geometry': {
                    'type': 'Point',
                    'coordinates': [sta[5], sta[4]]
                }
            }
            self.cursor.execute(
                'SELECT a.amp, i.imt_type, a.original_channel, '
                'a.flag, a.stddev '
                'FROM amp a, imt i '
                'WHERE a.station_id = "%s" '
                'AND a.imt_id = i.id' % (str(sta[0]))
            )
            amp_rows = self.cursor.fetchall()
            channels = {}
            for amp in amp_rows:
                # print('doing channel %s imt %s' % (amp[2], amp[1]))
                sd_string = 'ln_sigma'
                if amp[2] not in channels:
                    channels[amp[2]] = {'name': amp[2], 'amplitudes': []}
                if amp[0] == 'NULL':
                    value = 'null'
                    sigma = 'null'
                else:
                    value = amp[0]
                    sigma = float('%.4f' % amp[4])
                if amp[1] == 'PGV':
                    if value != 'null':
                        value = float('%.4f' % (np.exp(value)))
                    units = 'cm/s'
                elif amp[1] == 'MMI':
                    if value != 'null':
                        value = float('%.1f' % (value))
                    units = 'intensity'
                    sd_string = 'sigma'
                else:
                    if value != 'null':
                        value = float('%.4f' % (np.exp(value) * 100))
                    units = '%g'
                this_amp = {'name': amp[1].lower(),
                            'value': value,
                            'units': units,
                            'flag': str(amp[3]),
                            sd_string: sigma
                            }
                channels[amp[2]]['amplitudes'].append(this_amp)
            for channel in channels.values():
                feature['properties']['channels'].append(channel)
            jdict['features'].append(feature)

        return jdict

    def addData(self, xmlfiles):
        """
        Create a StationList object by reading one or more ShakeMap XML input
        files.

        Args:
            xmlfiles (sequence of str):
                Sequence of ShakeMap XML input files to read.
        Returns:
            :class:`StationList` object

        """
        # Parse the xml into a dictionary
        stationdict = {}
        imtset = set()
        for xmlfile in xmlfiles:
            stationdict, ims = self._filter_station(xmlfile, stationdict)
            imtset |= ims
        # fill the database and create the object from it
        self._loadFromDict(stationdict, imtset)
        return self

    def _loadFromDict(self, stationdict, imtset):
        """
        Internal method to turn the station dictionary created from the
        ShakeMap XML input files into a SQLite database.

        Args:
            stationdictlist (list of stationdicts):
                A list of station dictionaries returned by _filter_station().
            dbfile (string):
                The path to which the SQLite database will be written.

        Returns:
            :class:`StationList` object
        """
        #
        # Get the current IMTs and their IDs and add any new ones
        #
        imts_in_db = self.getIMTtypes()
        new_imts = imtset - imts_in_db
        if any(new_imts):
            self.cursor.executemany('INSERT INTO imt (imt_type) VALUES (?)',
                                    zip(new_imts))
            self.db.commit()

        # Now get the updated list of IMTs and their IDs
        query = 'SELECT imt_type, id FROM imt'
        self.cursor.execute(query)
        imt_hash = dict(self.cursor.fetchall())

        #
        # Get the station codes for all the stations in the db
        #
        query = 'SELECT id FROM station'
        self.cursor.execute(query)
        sta_set = set([z[0] for z in self.cursor.fetchall()])

        #
        # Insert any new stations into the station table
        #
        station_rows = []
        for sta_id, station_tpl in stationdict.items():
            if sta_id in sta_set:
                continue
            else:
                sta_set.add(sta_id)
            station_attributes, comp_dict = station_tpl
            lat = station_attributes['lat']
            lon = station_attributes['lon']
            code = station_attributes['code']
            # the attributes dictionary may not have the same
            # netid that we created. Use instead the first part of
            # the station id
            netid = sta_id[0:sta_id.find('.')]
            network = netid
            name = station_attributes.get('name', None)
            elev = station_attributes.get('elev', None)
            vs30 = station_attributes.get('vs30', None)
            stddev = station_attributes.get('stddev', 0)

            instrumented = int(network.lower() not in CIIM_TUPLE)

            station_rows.append((sta_id, network, code, name, lat, lon,
                                 elev, vs30, stddev, instrumented))

        self.cursor.executemany(
            'INSERT INTO station (id, network, code, name, lat, lon, '
            'elev, vs30, stddev, instrumented) VALUES '
            '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', station_rows
        )
        self.db.commit()

        #
        # Now add the amps, first get the current set so we don't add
        # any duplicates; a unique amp will be (station_id, imt_id,
        # original_channel)
        #
        query = 'SELECT station_id, imt_id, original_channel FROM amp'
        self.cursor.execute(query)
        amp_rows = self.cursor.fetchall()
        # Create a unique identifier for each amp so we don't repeat any
        amp_set = set([str(v[0]) + '.' + str(v[1]) + '.' + str(v[2])
                       for v in amp_rows])

        #
        # Insert the amps for each component
        #
        amp_rows = []
        for sta_id, station_tpl in stationdict.items():
            station_attributes, comp_dict = station_tpl
            instrumented = int(station_attributes['netid'].lower()
                               not in CIIM_TUPLE)
            for original_channel, cdict in comp_dict.items():
                pgm_dict = cdict['amps']
                orientation = cdict['attrs'].get('orientation', None)
                orientation = self._getOrientation(original_channel,
                                                   orientation)
                for imt_type, imt_dict in pgm_dict.items():
                    if (instrumented == 0) and (imt_type != 'MMI'):
                        continue
                    imtid = imt_hash[imt_type]
                    amp_id = str(sta_id) + '.' + str(imtid) + '.' + \
                        str(original_channel)
                    if amp_id in amp_set:
                        continue
                    else:
                        amp_set.add(amp_id)
                    amp = imt_dict['value']
                    units = imt_dict['units']
                    stddev = imt_dict['stddev']
                    flag = imt_dict['flag']
                    if np.isnan(amp):
                        amp = 'NULL'
                        flag = 'G'
                    elif imt_type == 'MMI':
                        if amp <= 0:
                            amp = 'NULL'
                            flag = 'G'
                        else:
                            pass
                    elif imt_type == 'PGV':
                        if units == 'cm/s':
                            if amp <= 0:
                                amp = 'NULL'
                                flag = 'G'
                            else:
                                amp = np.log(amp)
                        elif units == 'ln(cm/s)':
                            pass
                        else:
                            raise ValueError('Unknown units %s in input'
                                             % units)
                    else:
                        if units == '%g':
                            if amp <= 0:
                                amp = 'NULL'
                                flag = 'G'
                            else:
                                amp = np.log(amp / 100.0)
                        elif units == 'ln(g)':
                            pass
                        else:
                            raise ValueError('Unknown units %s in input'
                                             % units)

                    amp_rows.append((sta_id, imtid, original_channel,
                                     orientation, amp, stddev, flag))

        self.cursor.executemany(
            'INSERT INTO amp (station_id, imt_id, original_channel, '
            'orientation, amp, stddev, flag) VALUES (?, ?, ?, ?, ?, ?, ?)',
            amp_rows
        )
        self.db.commit()
        return

    def getIMTtypes(self):
        """
        Return a set of IMT types found in the database

        Args:
            None

        Returns:
            A set of IMT types
        """
        self.cursor.execute('SELECT imt_type FROM imt')
        return set([z[0] for z in self.cursor.fetchall()])

    def getStationDictionary(self, instrumented=True):
        """
        Return a dictionary of the instrumented or non-instrumented
        stations. The keys describe the parameter, the values are Numpy
        arrays of the parameter in question.

        For the standard set of ShakeMap IMTs (mmi, pga, pgv, psa03, psa10,
        psa30), the keys in the dictionary would be:

        'id', 'network', 'code', 'name', 'lat', 'lon', 'elev', 'vs30',
        'stddev', 'instrumented', 'PGA', 'PGA_sd', 'PGV', 'PGA_sd',
        'SA(0.3)', 'SA(0.3)_sd, 'SA(1.0)', 'SA(1.0)_sd, 'SA(3.0)',
        'SA(3.0)_sd'

        For the non-instrumented dictionary, the keys would be:

        'id', 'network', 'code', 'name', 'lat', 'lon', 'elev', 'vs30',
        'stddev', 'instrumented', 'MMI', 'MMI_sd'

        The **id** column is **network** and **code** concatenated with a
        period (".") between them.

        All ground motion units are natural log units. Distances are in km.

        Args:
            instrumented (bool):
                Set to True if the dictionary is to contain the instrumented
                stations, or to False if the dictionary is to contain the
                non-instrumented (MMI) stations.

        Returns:
            dict, set: A dictionary of Numpy arrays, and a set specifying
            the IMTs found in the dictionary..
        """

        columns = list(TABLES['station'].keys())
        dstr = ', '.join(columns)
        self.cursor.execute(
            'SELECT %s FROM station where instrumented = %d' %
            (dstr, instrumented)
        )

        station_rows = self.cursor.fetchall()
        nstation_rows = len(station_rows)
        if not nstation_rows:
            return None, set()
        station_columns = list(zip(*station_rows))
        df = OrderedDict()
        for ic, col in enumerate(columns):
            df[col] = np.array(station_columns[ic])

        myimts = set()
        for imt in self.getIMTtypes():
            if (instrumented and 'MMI' in imt) or \
               (not instrumented and 'MMI' not in imt):
                continue
            df[imt] = np.full(nstation_rows, np.nan)
            df[imt + '_sd'] = np.full(nstation_rows, 0.0)
            myimts.update([imt])

        id_dict = dict(zip(df['id'], range(nstation_rows)))

        #
        # Get all of the unflagged amps with the proper orientation
        #
        self.cursor.execute(
            'SELECT a.amp, i.imt_type, a.station_id, a.stddev FROM '
            'amp a, station s, imt i WHERE a.flag = "0" '
            'AND s.id = a.station_id '
            'AND a.imt_id = i.id '
            'AND s.instrumented = %d AND a.orientation NOT IN ("Z", "U") '
            'AND a.amp IS NOT NULL' % (instrumented)
        )
        amp_rows = self.cursor.fetchall()

        #
        # Go through all the amps and put them into the data frame
        #
        for this_row in amp_rows:
            #
            # Set the cell to the peak amp
            #
            rowidx = id_dict[this_row[2]]
            cval = df[this_row[1]][rowidx]
            amp = this_row[0]
            stddev = this_row[3]
            if np.isnan(cval) or (cval < amp):
                df[this_row[1]][rowidx] = amp
                df[this_row[1] + '_sd'][rowidx] = stddev

        return df, myimts

    @staticmethod
    def _getOrientation(orig_channel, orient):
        """
        Return a character representing the orientation of a channel.

        Args:
            orig_channel (string):
                String representing the seed channel (e.g. 'HNZ'). The
                final character is assumed to be the (uppercase) orientation.
            orient (str or None):
                Gives the orientation of the channel, overriding channel
                codes that end in numbers. Must be one of 'h' (horizontal)
                or 'v' (vertical), or None if the orientation has not been
                explicitly specified in the "comp" element.

        Returns:
            Character representing the channel orientation. One of 'N',
            'E', 'Z', 'H' (for horizontal), or 'U' (for unknown).
        """
        if orig_channel == 'mmi' or orig_channel == 'DERIVED':
            orientation = 'H'           # mmi is arbitrarily horizontal
        elif orig_channel[-1] in ('N', 'E', 'Z'):
            orientation = orig_channel[-1]
        elif orig_channel == "UNK":   # Channel is "UNK"; assume horizontal
            orientation = 'H'
        elif orig_channel == 'H1' or orig_channel == 'H2':
            orientation = 'H'
        elif orig_channel[-1].isdigit():
            if orient == 'h':
                orientation = 'H'
            elif orient == 'v':
                orientation = 'Z'
            else:
                orientation = 'U'
        else:
            orientation = 'U'  # this is unknown
        return orientation

    @staticmethod
    def _getGroundMotions(comp, imt_translate):
        """
        Get a dictionary of peak ground motions (values and flags).
        Output keys are one of: [pga,pgv,psa03,psa10,psa30]
        Even if flags are not specified in the input, they will
        be guaranteed to at least have a flag of '0'.
        """
        pgmdict = {}
        imtset = set()
        for pgm in comp:
            if pgm.tag == '#text':
                continue
            key = pgm.tag
            if key not in imt_translate:
                if key in ('acc', 'pga'):
                    new_key = 'PGA'
                elif key in ('vel', 'pgv'):
                    new_key = 'PGV'
                elif 'mmi' in key:
                    new_key = 'MMI'
                elif 'psa' in key:
                    pp = get_imt_period(key)
                    new_key = 'SA(' + str(pp) + ')'
                else:
                    raise ValueError('Unknown amp type in input: %s' % key)
                imt_translate[key] = new_key
            else:
                new_key = imt_translate[key]
            key = new_key

            if 'value' in pgm.attrib:
                try:
                    value = float(pgm.attrib['value'])
                except ValueError:
                    logging.warn('Unknown value in XML: %s for amp: %s' %
                                 (pgm.attrib['value'], pgm.tag))
                    continue
            else:
                logging.warn('No value for amp %s' % pgm.tag)
                continue
            if 'flag' in pgm.attrib and pgm.attrib['flag'] != '':
                flag = pgm.attrib['flag']
            else:
                flag = '0'
            if 'ln_stddev' in pgm.attrib:
                stddev = float(pgm.attrib['ln_stddev'])
            else:
                stddev = 0
            if 'units' in pgm.attrib:
                units = pgm.attrib['units']
            else:
                if key == 'PGV':
                    units = 'cm/s'
                elif key == 'MMI':
                    units = 'intensity'
                else:
                    units = '%g'
            pgmdict[key] = {'value': value,
                            'flag': flag,
                            'stddev': stddev,
                            'units': units}
            imtset.add(key)
        return pgmdict, imtset, imt_translate

    def _filter_station(self, xmlfile, stationdict):
        """
        Filter individual xmlfile into a stationdict data structure.

        Args:
            xmlfile (string):
                Path to ShakeMap XML input file (or file-like object)
                containing station data.

        Returns:
            stationdict data structure
        """
        #
        # Strip off any namespace garbage that is prepended
        # to the tags
        #
        it = ET.iterparse(xmlfile)
        for _, el in it:
            if '}' in el.tag:
                el.tag = el.tag.split('}', 1)[1]
        #
        # Parse the cleaned up xml tree
        #
        imt_translate = {}
        imtset = set()
        root = it.root
        for sl in root.iter('stationlist'):
            for station in sl:
                if station.tag != 'station':
                    continue
                # look at the station attributes to figure out if this is a
                # DYFI-type station or a station with instruments measuring
                # PGA, PGV, etc.
                attributes = station.attrib.copy()
                if 'netid' in attributes:
                    netid = attributes['netid']
                    if not len(netid.strip()):
                        netid = 'unknown'
                else:
                    netid = 'unknown'
                    attributes['netid'] = netid
                instrumented = int(netid.lower() not in CIIM_TUPLE)

                if 'code' not in attributes:
                    logging.warn(
                        'Station does not have station code: skipping')
                    continue
                code = attributes['code']
                if code.startswith(netid + '.'):
                    sta_id = code
                    code = code.replace(netid + '.', '')
                else:
                    sta_id = netid + '.' + code

                if sta_id in stationdict:
                    compdict = stationdict[sta_id][1]
                else:
                    compdict = {}
                for comp in station:
                    if 'name' not in comp.attrib:
                        logging.warn(
                            'Unnamed component for station %s; skipping'
                            % (sta_id))
                        continue
                    compname = comp.attrib['name']
                    if 'Intensity Questionnaire' in str(compname):
                        compdict['mmi'] = {'amps': {}, 'attrs': {}}
                        continue
                    tpgmdict, ims, imt_translate = \
                        self._getGroundMotions(comp, imt_translate)
                    if compname in compdict:
                        pgmdict = compdict[compname]['amps']
                    else:
                        pgmdict = {}
                    pgmdict.update(tpgmdict)
                    # copy the VALUES, not REFERENCES, of the component list
                    # into our growing dictionary
                    compdict[compname] = {'attrs': copy.copy(comp.attrib),
                                          'amps': copy.copy(pgmdict)}
                    imtset |= ims
                if ('intensity' in attributes) and (instrumented == 0):
                    if 'mmi' not in compdict:
                        compdict['mmi'] = {'amps': {}, 'attrs': {}}
                    if 'intensity_stddev' in attributes:
                        stddev = float(attributes['intensity_stddev'])
                    else:
                        stddev = 0
                    compdict['mmi']['amps']['MMI'] = \
                        {'value': float(attributes['intensity']),
                         'stddev': stddev,
                         'flag': '0',
                         'units': 'intensity'}
                    imtset.add('MMI')
                stationdict[sta_id] = (attributes, copy.copy(compdict))
        return stationdict, imtset

    def _createTables(self):
        """
        Build the database tables.
        """
        for table in TABLES.keys():
            sql = 'CREATE TABLE %s (' % table
            nuggets = []
            for column, ctype in TABLES[table].items():
                nuggets.append('%s %s' % (column, ctype))
            sql += ','.join(nuggets) + ')'
            self.cursor.execute(sql)

        self.db.commit()
        return


def get_imt_period(imt):

    p = re.search(r'(?<=psa)\d+', imt)
    return float(p.group(0)[:-1] + '.' + p.group(0)[-1])
