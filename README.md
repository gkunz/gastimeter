# Gastimator

Gastimator is a simple tool to obtain readings from a gas meter by means of OCR (Optical Character Regonition). As OCR is not 100% accurate, the tool effectively provides a guestimate of the gas meter reading.

## Installation

Clone the repostory and install using pip - optionally in a virtually environment.

```
  git clone TODO
  pip3 install .
```

## Known issues

Gastimator uses [OpenCV](https://opencv.org/) to capture images from a connected camera. If running gastimator on a RaspberryPi on Debian Bullseye, note that OpenCV does not work (yet) with the new libcamera-based subsystem (link). A solution is to switch to the legacy camera interface (V4L).

## License
Gastimator is licensed under the [MIT license](https://spdx.org/licenses/MIT.html).
