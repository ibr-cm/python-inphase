SPEED_OF_LIGHT = 299792458  # speed of light
DEFAULT_FREQ_SPACING = 0.5  # Step between two frequencies in MHz
MAX_DISTANCE = SPEED_OF_LIGHT / (float(DEFAULT_FREQ_SPACING) * 10**6) * 0.5  # effective wavelength and maximum distance
