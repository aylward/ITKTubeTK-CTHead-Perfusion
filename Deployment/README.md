## Installation

Install the following pip packages:
```
pip install pywin32 pyinstaller==4.7 monai ffmpeg-python av numpy
pip install --pre itk-tubetk
```

Then, install the MONAI extras: https://docs.monai.io/en/latest/installation.html#installing-the-recommended-dependencies.

Finally, build and install itkARGUS from the ARGUS folder in this repo. You will need to follow the ITK python packaging guide for this step.
Note that it is ideal to install itk-tubetk with the `--pre` flag prior to installing itkARGUS.

Edit the run function in `worker.py` to run your own code.

## build

1. `pyinstaller argus.spec` from within the conda env, and verify that argus.exe works without an env.
2. Download NSSM and put the 32-bit `nssm.exe` file in this same directory.
3. Open the inno setup app and compile the final installer.

## running

For dev, you can run `server.py` for the server and `cli.py` for the cli.

For a prod installation, the server will be autostarted for you. All you need to run is `argus-cli` from the command prompt.