# Axona file manipulations

## Axona systems related files
The C++ code is designed to quickly shuffle the default Axona binary file which is slow to read and wasteful of space into something more efficient. The shuffling is written in C++ and is fast. Can also convert the binary into both Channels * samples and samples * channels dimensions.

The Python code is designed to sense check the faster C++ code by using numpy memmaps (far easier to code). Also provides some visualisation methods on raw data.

## Requirements

numpy and h5py for the Python code.
A C++ compiler for the C++ code in the CPP folder.

## Current Contents

- CPP: C++ code for shuffling and converting Axona raw binary files.
- Various Python files for binary reading, .inp reading, .eeg merging.
