#include "AxonaBinReader.h"
#include "Utils.h"
#include <fstream>
#include <iostream>
#include <array>
#include <charconv>
#include <chrono>
#include <vector>

int16_t AxonaBinReader::ConvertBytes(char b1, char b2)
{
	uint16_t us = (uint8_t)b1 * 256 + (uint8_t)b2;
	int16_t out = (int16_t) us;
	return out;
}

AxonaBinReader::AxonaBinReader()
{
}

AxonaBinReader::AxonaBinReader(std::string name)
{
	Init(name);
}

void AxonaBinReader::Init(std::string name)
{
	SetSetFname(name);
	std::string base_name = name.substr(0, name.length() - 4);
	std::string bin_name = base_name;
  std::string inp_name = base_name;
	bin_name.append(".bin");
	SetBinFname(bin_name);
	base_name.append("_shuff.bin");
	_out_fname = base_name;
  inp_name.append(".inp");
  _out_inpname = inp_name;
}

bool const AxonaBinReader::ToInp()
{
	long fsize = GetFileSize(GetBinFname());
	long total_samples = fsize / _chunksize;
	const int buff_size = _chunksize;
	
	std::vector<char> buffer(buff_size, 0);
	std::vector<uint64_t> digital_vals;
  //TODO This might be unnecessary, keep an eye on this!
  //char c = 'I';
  //digital_vals.push_back(65536 * (uint64_t)c);
  //c = 'O';
  //digital_vals.push_back(65536 * (uint64_t)c);

	std::ifstream infile;
	infile.open(_bin_fname, std::ios::binary | std::ios::in);
	int sample_count = 0;

  uint16_t last_input_val = 1000;
  uint16_t last_output_val = 1000;
	auto start = std::chrono::high_resolution_clock::now();
	while (infile.read(buffer.data(), buffer.size())) {	
		uint16_t input_val = (256 * buffer[8]) + buffer[9];
		uint16_t output_val = (256 * buffer[416]) + buffer[417];
		uint32_t timestamp = sample_count / 16;
		if (input_val != last_input_val) {
			char c = 'I';
			digital_vals.push_back(
				((uint64_t)timestamp * 16777216) + (65536 * (uint64_t)c) + (uint64_t)input_val);
      last_input_val = input_val;
		}
		if (output_val != last_output_val) {
			char c = 'O';
			digital_vals.push_back(
				((uint64_t)timestamp * 16777216) + (65536 * (uint64_t)c) + (uint64_t)output_val);
      last_output_val = output_val;
		}
	}
	infile.close();
	auto finish = std::chrono::high_resolution_clock::now();
	std::chrono::duration<double> elapsed = finish - start;
	std::cout << "Elapsed time to read: " << elapsed.count() << " s\n";
  std::cout << "Number of input output samples: " << digital_vals.size() << std::endl;

	start = std::chrono::high_resolution_clock::now();
	std::ofstream outfile (_out_inpname, std::ios::out | std::ios::binary);
	outfile << std::string("bytes_per_sample ") << 7 << std::endl;
	outfile << std::string("timebase ") << 1000 << std::endl;
	outfile << std::string("num_inp_samples ") << digital_vals.size() << std::endl;
	outfile << std::string("data_start");
	for (int i = 0; i < digital_vals.size(); ++i) {
    auto byte_arr = IntToBytes(digital_vals[i]);
		outfile.write(byte_arr.data(), 7);
	}
  outfile << std::string("data_end");
	outfile.close();
	finish = std::chrono::high_resolution_clock::now();
	elapsed = finish - start;
	std::cout << "Elapsed time to write: " << elapsed.count() << " s\n";
	return true;
}

bool const AxonaBinReader::Read()
{
	long fsize = GetFileSize(GetBinFname());
	long total_samples = fsize / _chunksize;
	total_samples *= _samples_per_chunk;
	std::cout << total_samples << std::endl;

	const int buff_size = _chunksize;
	std::vector<char> buffer(buff_size, 0);
	std::vector<std::vector<int16_t>> channel_data(
		_num_channels, std::vector<int16_t>(total_samples, 0));

	std::ifstream infile;
	infile.open(_bin_fname, std::ios::binary | std::ios::in);
	int sample_count = 0;

	auto start = std::chrono::high_resolution_clock::now();
	while (infile.read(buffer.data(), buffer.size())) {
		for (int i = _header_bytes; i < _chunksize - _trailer_bytes; i = i + _sample_bytes) {
			int compare_val = (i - _header_bytes) / 2;
			int row_sample = compare_val % _num_channels;
			int col_sample = sample_count + (compare_val / _num_channels);
			int16_t val = ConvertBytes(buffer[i + 1], buffer[i]);
			channel_data[_reverse_map_channels[row_sample]][col_sample] = val;
		}
		sample_count += 3;
	}
	infile.close();
	auto finish = std::chrono::high_resolution_clock::now();
	std::chrono::duration<double> elapsed = finish - start;
	std::cout << "Elapsed time to read: " << elapsed.count() << " s\n";

	start = std::chrono::high_resolution_clock::now();
	std::ofstream outfile (_out_fname, std::ios::out | std::ios::binary);
	const char header[5] = "bax1";
	outfile.write(header, 4);
	std::string str = std::to_string(total_samples);
	char const* pchar = str.c_str();
	outfile.write(pchar, sizeof(long));
	for (int i = 0; i < _num_channels; ++i) {
		outfile.write((char*)channel_data[i].data(), _sample_bytes * total_samples);
	}
	outfile.close();
	finish = std::chrono::high_resolution_clock::now();
	elapsed = finish - start;
	std::cout << "Elapsed time to write: " << elapsed.count() << " s\n";
	return true;
}

int main() {
	AxonaBinReader axbr{
		"C:\\Users\\smartin5\\Recordings\\Raw\\Raw_160819\\LCA7_34_35_36.set"};
	/*axbr.Read();*/
  axbr.ToInp();
}