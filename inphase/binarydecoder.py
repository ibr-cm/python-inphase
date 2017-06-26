from inphase.dataformat import Measurement, Node, Sample

from struct import unpack, calcsize
import time

# as defined in at86rf233.c
SERIAL_FRAME_START     = 0x3C      # "<" in ascii
SERIAL_FRAME_END       = 0x3E      # ">" in ascii
SERIAL_ESCAPE_BYTE     = 0x40      # "@" in ascii
SERIAL_ESCAPE_ADD      = 0x10      # add this to byte after escape


def decodeBinary(data, timestamp=True):
    """Returns parsed measurements from binary data, also returns remaining data that still needs parsing and clean data that does not contain any other binary data."""
    measurements = list()
    remaining_data = data
    clean_data = bytearray()

    while True:
        start = remaining_data.find(SERIAL_FRAME_START)

        if start == -1:
            # no start byte detected
            clean_data += remaining_data
            remaining_data = bytearray()
            break

        end = remaining_data.find(SERIAL_FRAME_END, start)
        if end == -1:
            # no end byte detected
            clean_data += remaining_data[0:start]
            remaining_data = remaining_data[start:]
            start = remaining_data.rfind(SERIAL_FRAME_START)
            if start != -1:
                clean_data += remaining_data[0:start]
                remaining_data = remaining_data[start:]
            break

        last_start = remaining_data.rfind(SERIAL_FRAME_START, start, end)
        if last_start != -1:
            if last_start > start:
                start = last_start

        # if we reach this, next frame is found

        # remove data before the frame from remaining data, it does not contain any more binary frames
        clean_data += remaining_data[0:start]
        # extract frame from remaining data
        raw_frame = remaining_data[start:end+1]
        # remaining data is now everything after the current frame
        remaining_data = remaining_data[end+1:]

        if len(raw_frame) == 2:
            # we have found an empty frame
            print("frame invalid! no data between start and stop symbol.")
            clean_data += raw_frame
            continue

        # now parse the frame contents
        frame = bytearray(raw_frame)

        # remove all byte stuffing instances
        frame = _unescape(frame)

        # unpack the byte sin the frame
        measurement_data = _parsePacket(frame)

        if not measurement_data:
            # frame was invalid, this means byte were lost on serial connection or we found frame delimiter that do not actually delimit a frame at all
            # add the frame to clean_data, as it is not a valid frame and might contain other output
            clean_data += raw_frame
            continue

        # set up a measurement in the correct data format
        reflector = Node({
            'uid': measurement_data['reflector_address']
            })

        samples = list()

        for freq, values in zip(measurement_data['frequencies'], measurement_data['values']):
            samples.append(Sample({
                'frequency': freq,
                'pmu_values': values
                }))

        measurement = Measurement({
            'dqi': measurement_data['dist_quality'],
            'measured_distance': measurement_data['dist_meter'] * 1000 + measurement_data['dist_centimeter'] * 10,
            'reflector': reflector,
            'samples': samples
            })

        if timestamp:
            measurement['timestamp'] = time.time()

        measurements.append(measurement)

    return measurements, remaining_data, clean_data


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
    unpack_str_2 = '>3H4B'
    minimum_frame_length = calcsize(unpack_str)+calcsize(unpack_str_2)

    if len(frame) < minimum_frame_length:
        print("frame invalid! length was:", len(frame), ", minimum length is:", minimum_frame_length)
        return None

    samples, step = unpack(unpack_str, frame[0:calcsize(unpack_str)])
    frequency_start, measurements, reflector_address, dist_meter, dist_centimeter, dist_quality, status = unpack(unpack_str_2, frame[calcsize(unpack_str):calcsize(unpack_str)+calcsize(unpack_str_2)])

    if (step == 0):  # by definition 0 step size is 0.5
        step = 0.5

    expected_frame_length = measurements * samples + minimum_frame_length

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
    values = unpack('>' + str(measurements*samples) + 'b', frame[minimum_frame_length:])

    for i in range(measurements):
        data['values'].append(list())
        for j in range(samples):
            data['values'][i].append(values[i*samples+j])

    return data
