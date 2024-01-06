# Gastimeter

`gastimeter` is a simple tool to obtain readings from a gas meter by means of OCR (Optical Character Regonition). As OCR is not 100% accurate, the tool effectively provides a guestimate of the gas meter reading - hence the name. 

## Installation

Clone the repository and install `gastimeter` using pip - optionally in a virtually environment.

```
  git clone https://github.com/gkunz/gastimeter.git
  cd gastimeter
  pip3 install .
```

## Known issues

`gastimeter` uses [OpenCV](https://opencv.org/) to capture images from a connected camera. If running `gastimeter` on a RaspberryPi on Debian Bullseye (or higher), note that [OpenCV does not work (yet)](https://github.com/opencv/opencv/issues/22820#issuecomment-1339283736) with the new libcamera subsystem. There are two possible workarounds:


### Use the legacy camera subsystem based on V4L2

Switch to the old camera subsystem using the following:

1. `sudo raspi-config`
1. Select ` Interface Options`
1. Select `Legacy Camera`

Note that this camera subsystem is deprecated and will be removed in the future.

### Use libcamera tooling

Use `libcamera-jpeg` to capture an image and feed this into `gastimeter` using the `--image` option.


## License
Gastimator is licensed under the [MIT license](https://spdx.org/licenses/MIT.html).
