import unittest
import time
import re
import logging

logger = logging.getLogger()

try:
    import coloredlogs
    coloredlogs.install(level='ERROR', logger=logger, fmt="%(levelname)s %(message)s")
except ImportError:
    logger.info("Module coloredlogs not found, using default logging")

# TODO: remove this and add to parser
regex_params = r"^(?P<param>\w+)(?P<sep>:\W*)(?P<desc>[\w ]*)"

REGEX_KEYVALUE = r"^(\s*)(?P<key>[\w\.]+)(?P<sep>:\s*)(?P<value>[\S ]*)"

def decodeParameters(data, timestamp=True):
    """Returns parsed parameters from data, also returns remaining data that still needs parsing and clean data that does not contain any parameters."""
    parameters = dict()
    remaining_data = data
    clean_data = bytearray()

    start = 0
    end = -1

    while True:
        start = 0
        logger.debug("> start {} end {}".format(start, end))
        logger.debug("remaining_data: %s" %  remaining_data)
        end = remaining_data.find(b'\r\n', start)
        if end == -1:
            break
        logger.debug((len("remaining_data b'")+end)*' '+"^")
        logger.debug("end {}".format(end))

        line = remaining_data[start:end]
        logger.debug("line: %s" % line)
        parameter, value = _parse_line(line.decode(errors='replace'))

        remaining_data = remaining_data[end+2:]

        start = end

        if parameter:
            parameters[parameter] = value
        else:
            logger.debug("ignoring %s" % line)
            clean_data += line + b'\r\n'

    logger.debug("parameters: %s" % parameters)
    logger.debug("remaining_data: %s" %  remaining_data)
    logger.debug("clean_data %s\n" % clean_data)

    return parameters, remaining_data, clean_data

def _parse_line(line_to_parse):
    # logger.debug("Parsing line: '{}'".format(line_to_parse))
    key = value = None
    for keyvalues in re.compile(REGEX_KEYVALUE).finditer(str(line_to_parse)):
        try:
            key = keyvalues.group('key')
            # logger.debug("key: {}({})".format(key, type(key)))
            value = keyvalues.group('value')
            # logger.debug("value: {}({})".format(value, type(value)))
            if _parse_kv(key, value):
                try:
                    # try to parse as number (dec, hex)
                    value = int(value, 0)
                except Exception:
                    # parse as string
                    pass

        except Exception as excpt:
            logger.debug("Exception: {}".format(type(excpt)))
            logger.error("no key-values")

    return key, value

def _parse_kv(key, value):
    if value == "Contiki> ":
        logger.debug("ignoring contiki-prompt '{}' '{}'".format(key, value))
        return False

    if key == "err":
        logger.error("INPHASE:"+str(value))
        return False
    elif key == "DBG":
        logger.debug("INPHASE:"+str(value))
        return False
    else:
        logger.debug("key:'{}'; value:'{}';".format(key, value))
        return True
