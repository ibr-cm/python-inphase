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
        parameter, value = _parse_line(line.decode())

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

def _unescape(frame):
    # find all escape bytes
    indices = [i for i, x in enumerate(frame) if x == SERIAL_ESCAPE_BYTE]

    # unescape all bytes after escape bytes
    for i in indices:
        frame[i+1] = (frame[i+1] + SERIAL_ESCAPE_ADD) % 256

    # remove all escape bytes fround in the first step
    frame = bytearray([i for j, i in enumerate(frame) if j not in indices])

    return frame


def _parsePacket(frame):
    # remove frame delimiter
    frame = frame[1:-1]

    data = dict()

    unpack_str = '>BB'
    samples, step = unpack(unpack_str, frame[0:calcsize(unpack_str)])

    unpack_str_2 = '>3H4B'
    frequency_start, measurements, reflector_address, dist_meter, dist_centimeter, dist_quality, status = unpack(unpack_str_2, frame[calcsize(unpack_str):calcsize(unpack_str)+calcsize(unpack_str_2)])

    if (step == 0):  # by definition 0 step size is 0.5
        step = 0.5

    value_offset = calcsize(unpack_str)+calcsize(unpack_str_2)

    expected_frame_length = measurements * samples + value_offset

    if (expected_frame_length != len(frame)):
        print("frame invalid! length was:", len(frame), ", expected length is:", expected_frame_length)
        return None

    data['measurements'] = measurements
    data['samples'] = samples
    data['step'] = step
    data['reflector_address'] = reflector_address
    data['dist_meter'] = dist_meter
    data['dist_centimeter'] = dist_centimeter
    data['dist_quality'] = dist_quality
    data['status'] = status

    #print data

    data['frequencies'] = list()

    for i in range(measurements):
        data['frequencies'].append(frequency_start + i * step)

    data['values'] = list()
    values = unpack('>' + str(measurements*samples) + 'b', frame[value_offset:])

    for i in range(measurements):
        data['values'].append(list())
        for j in range(samples):
            data['values'][i].append(values[i*samples+j])

    return data
