import unittest
import time
import re
import logging

logger = logging.getLogger()

try:
    import coloredlogs
    coloredlogs.install(level='DEBUG', logger=logger, fmt="%(levelname)s %(message)s")
except ImportError:
    logger.info("Module coloredlogs not found, using default logging")

# TODO: remove this and add to parser
regex_params = r"^(?P<param>\w+)(?P<sep>:\W*)(?P<desc>[\w ]*)"

REGEX_KEYVALUE = r"^(\s*)(?P<key>[\w\.]+)(?P<sep>:\s*)(?P<value>[\S ]*)"

def decodeParameters(data, timestamp=True):
    """Returns parsed parameters from data, also returns remaining data that still needs parsing and clean data that does not contain any parameters."""
    parameters = list()
    remaining_data = data
    clean_data = bytearray()


    if data != b'':
        # logger.debug("data: %s" % data)
        lines = data.split(b'\r\n')

        for line in lines[:-1]:
            # logger.debug("line: %s" % line)
            parameter = _parse_line(line.decode())
            if parameter:
                parameters.append(parameter)
            else:
                clean_data += line + b'\r\n'

        remaining_data = lines[-1:]

        remaining_data[-1] += b'\r\n'

        # while True:
            # start = remaining_data.find(SERIAL_FRAME_START)
            # end = remaining_data.find(SERIAL_FRAME_END, start)

            # if start == -1:
                # # no start byte detected
                # break
            # if end == -1:
                # # no end byte detected
                # break

            # if we reach this, next frame is found

            # # remove data before the frame from remaining data, it does not contain any more binary frames
            # clean_data += remaining_data[0:start]
            # # extract frame from remaining data
            # raw_frame = remaining_data[start:end+1]
            # # remaining data is now everything after the current frame
            # remaining_data = remaining_data[end+1:]

            # # now parse the frame contents
            # frame = bytearray(raw_frame)

            # # remove all byte stuffing instances
            # frame = _unescape(frame)

            # # unpack the byte sin the frame
            # parameter_data = _parsePacket(frame)

            # if not parameter_data:
                # # frame was invalid, this means byte were lost on serial connection or we found frame delimiter that do not actually delimit a frame at all
                # # add the frame to clean_data, as it is not a valid frame and might contain other output
                # clean_data += raw_frame
                # continue

            # # set up a parameter in the correct data format
            # reflector = Node({
                # 'uid': parameter_data['reflector_address']
                # })

            # samples = list()

            # for freq, values in zip(parameter_data['frequencies'], parameter_data['values']):
                # samples.append(Sample({
                    # 'frequency': freq,
                    # 'pmu_values': values
                    # }))

            # parameter = parameter({
                # 'dqi': parameter_data['dist_quality'],
                # 'measured_distance': parameter_data['dist_meter'] * 1000 + parameter_data['dist_centimeter'] * 10,
                # 'reflector': reflector,
                # 'samples': samples
                # })

            # if timestamp:
                # parameter['timestamp'] = time.time()

        logger.debug("parameters: %s" % parameters)
        logger.debug("remaining_data: %s" %  remaining_data)
        logger.debug("clean_data %s\n" % clean_data)

    return parameters, remaining_data, clean_data

def _parse_line(line_to_parse):
    received_data = {}
    # logger.debug("Parsing line: '{}'".format(line_to_parse))
    for keyvalues in re.compile(REGEX_KEYVALUE).finditer(str(line_to_parse)):
        try:
            key = keyvalues.group('key')
            # logger.debug("key: {}({})".format(key, type(key)))
            value = keyvalues.group('value')
            # logger.debug("value: {}({})".format(value, type(value)))
            if _parse_kv(key, value):
                try:
                    received_data[key] = int(value)
                except Exception:
                    received_data[key] = int(value)

        except Exception as excpt:
            logger.debug("Exception: {}".format(type(excpt)))
            logger.error("no key-values")
    return received_data

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
