# How to install requirements for run_spike_interface.py

## C++ code for AxonaBinary
 1. Either download the executable from TBD or build the code.
 2. Add the location containing AxonaBinary.exe to PATH.

## SpikeInterface and klusta
 1. Clone my fork of spikesorters.
 2. Clone my fork of anything else.
 3. Clone spikeinterface (maybe I should fork all?)
 4. pip install . from spikeinterface or pip install spikeinterface

## Install phy for visualisation
```
git clone https://github.com/cortex-lab/phy.git
cd phy
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e .
pip install PyQtWebEngine
```