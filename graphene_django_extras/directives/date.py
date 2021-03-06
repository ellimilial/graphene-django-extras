# -*- coding: utf-8 -*-
from datetime import date, datetime, timedelta, time

from dateutil import parser, relativedelta
from graphql import GraphQLArgument, GraphQLString

from .base import BaseExtraGraphQLDirective

__author__ = 'Ernesto'
__all__ = ('DateGraphQLDirective', )


DEFAULT_DATE_FORMAT = '%d %b %Y %H:%M:%S';
FORMATS_MAP = {
        # Year
        'YYYY': '%Y',
        'YY': '%y',

        # Week of year
        'WW': '%U',
        'W': '%W',

        # Day of Month
        # 'D': '%-d',  # Platform specific
        'DD': '%d',

        # Day of Year
        # 'DDD': '%-j',  # Platform specific
        'DDDD': '%j',

        # Day of Week
        'd': '%w',
        'ddd': '%a',
        'dddd': '%A',

        # Month
        # 'M': '%-m',  # Platform specific
        'MM': '%m',
        'MMM': '%b',
        'MMMM': '%B',

        # Hour
        # 'H': '%-H',  # Platform specific
        'HH': '%H',
        # 'h': '%-I',  # Platform specific
        'hh': '%I',

        # Minute
        # 'm': '%-M',  # Platform specific
        'mm': '%M',

        # Second
        # 's': '%-S',  # Platform specific
        'ss': '%S',

        # AM/PM
        # 'a': '',
        'A': '%p',

        # Timezone
        'ZZ': '%z',
        'z': '%Z'
    }


def str_in_dict_keys(s, d):
    for k in d:
        if s in k:
            return True
    return False


def _combine_date_time(d, t):
    if (d is not None) and (t is not None):
        return datetime(d.year, d.month, d.day, t.hour, t.minute, t.second)
    return None


def _parse(dt):
    """
    parse input to datetime
    """
    try:
        if isinstance(dt, datetime):
            return dt
        if isinstance(dt, date):
            return _combine_date_time(dt, time(0, 0, 0))
        if isinstance(dt, time):
            return _combine_date_time(date.today(), dt)
        if isinstance(dt, (int, float)):
            return datetime.fromtimestamp(dt)
        if isinstance(dt, (str, bytes)):
            return parser.parse(dt)
        return None
    except ValueError:
        return None


def _format_relativedelta(rdelta, full=False):
    if not isinstance(rdelta, relativedelta.relativedelta):
        raise ValueError('rdelta must be a relativedelta instance')
    keys = ('years', 'months', 'days', 'hours', 'minutes', 'seconds')
    result = []
    flag = None
    for k, v in rdelta.__dict__.items():
        if k in keys and v != 0:
            if flag is None:
                flag = True if v > 0 else False
            key = k
            if v == 1:
                key = key[:-1]
            if not full:
                return flag, '{} {}'.format(abs(v), key)
            else:
                result.append('{} {}'.format(abs(v), key))
    if len(result) == 0:
        return None, 'just now'
    if len(result) > 1:
        temp = result.pop()
        result = '{} and {}'.format(', '.join(result), temp)
    else:
        result = result[0]

    return flag, result


def _format_time_ago(dt, now=None, full=False, ago_in=False):

    if not isinstance(dt, timedelta):
        if now is None:
            now = datetime.now()
        dt = _parse(dt)
        now = _parse(now)

        if dt is None:
            raise ValueError('The parameter `dt` should be datetime timedelta, or datetime formatted string.')
        if now is None:
            raise ValueError('the parameter `now` should be datetime, or datetime formatted string.')

        result = relativedelta.relativedelta(dt, now)
        flag, result = _format_relativedelta(result, full)
        if ago_in and flag is not None:
            result = 'in {}'.format(result) if flag else '{} ago'.format(result)
        return result


def _format_dt(dt, format='default'):
    CUSTOM_FORMAT = {
        'time ago': _format_time_ago(dt, full=True, ago_in=True),
        'default': dt.strftime(DEFAULT_DATE_FORMAT),
        'iso': dt.strftime('%Y-%b-%dT%H:%M:%S'),
        'JS': dt.strftime('%a %b %d %Y %H:%M:%S'),
        'javascript': dt.strftime('%a %b %d %Y %H:%M:%S'),
    }

    if format.lower() in CUSTOM_FORMAT:
        return CUSTOM_FORMAT[format]

    if format in FORMATS_MAP:
        return dt.strftime(FORMATS_MAP[format])

    else:
        wrong_format_flag = False
        temp_format = ''
        translate_format_list = []
        for char in format:
            if char in (' ', ',', ':', '.', ';', '[', ']', '(', ')', '{', '}', '-', '_'):
                if temp_format != '':
                    translate_format_list.append(FORMATS_MAP.get(temp_format, ''))
                    temp_format = ''
                translate_format_list.append(char)
            else:
                if str_in_dict_keys('{}{}'.format(temp_format, char), FORMATS_MAP):
                    temp_format = '{}{}'.format(temp_format, char)
                else:
                    if temp_format != '':
                        translate_format_list.append(FORMATS_MAP.get(temp_format, ''))
                    if str_in_dict_keys(char, FORMATS_MAP):
                        temp_format = char
                    else:
                        wrong_format_flag = True
                        break

        if not wrong_format_flag:
            if temp_format !=  '':
                translate_format_list.append(FORMATS_MAP.get(temp_format, ''))
            return dt.strftime(''.join(translate_format_list))

        return 'Invalid format string'


class DateGraphQLDirective(BaseExtraGraphQLDirective):
    """
    Format the date from resolving the field by dateutil module.
    """
    @staticmethod
    def get_args():
        return {
            'format': GraphQLArgument(
                type=GraphQLString,
                description='A format given by dateutil module',
            ),
        }

    @staticmethod
    def resolve(value, directive, root, info, **kwargs):
        DEFAULT = datetime.now()
        format_argument = [arg for arg in directive.arguments if arg.name.value == 'format']
        format_argument = format_argument[0] if len(format_argument) > 0 else None

        format = format_argument.value.value if format_argument else 'default'
        dt = parser.parse(value, default=DEFAULT)
        try:
            return _format_dt(dt, format) or value
        except ValueError:
            return 'Invalid format string'
