# Running spike sorting on Axona data
1. Record data in raw mode at 48kHz.
2. Setup the config file at config.cfg.
3. OPTIONAL Setup the channel mapping at channel_map.py if different than 16 tetrodes.
4. If not using all 16 tetrodes for spike sorting it would be preferable to modify the c++ code slightly - but it still works! (just not as efficient as possible)
5. pip install numpy matplotlib
6. python run_spike_interface.py

# How to install requirements for run_spike_interface.py

## C++ code for AxonaBinary
 1. Either download the executable from TBD or build the code.
 2. Add the location containing AxonaBinary.exe to PATH.

## Install SpikeInterface and klusta
```
git clone https://github.com/seankmartin/spikesorters
cd spikesorters
pip install -e .
cd ..
git clone https://github.com/seankmartin/spiketoolkit
cd spiketoolkit
pip install -e .
cd ..
git clone https://github.com/SpikeInterface/spikeextractors
cd spikeextractors
pip install -e .
cd ..
pip install spikeinterface
pip install Cython h5py tqdm
pip install click klusta klustakwik2
```

## Install phy for visualisation
```
git clone https://github.com/cortex-lab/phy.git
cd phy
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e .
pip install PyQtWebEngine
```
