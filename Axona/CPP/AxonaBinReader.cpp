#include "AxonaBinReader.h"
#include "Utils.h"
#include <fstream>
#include <iostream>
#include <array>
#include <chrono>
#include <vector>

int16_t AxonaBinReader::ConvertBytes(char b1, char b2)
{
	uint16_t us = (uint8_t)b1 * 256 + (uint8_t)b2;
	int16_t out = (int16_t)us;
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
	long long fsize = GetFileSize(GetBinFname());
	long long total_samples = fsize / _chunksize;
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
	uint32_t sample_count = 0;

	uint16_t last_input_val = 1000;
	uint16_t last_output_val = 1000;
	auto start = std::chrono::high_resolution_clock::now();
	while (infile.read(buffer.data(), buffer.size()))
	{
		uint16_t input_val = (256 * (uint8_t)buffer[9]) + (uint8_t)buffer[8];
		uint16_t output_val = (256 * (uint8_t)buffer[417]) + (uint8_t)buffer[416];
		uint32_t timestamp = sample_count;
		if (input_val != last_input_val)
		{
			char c = 'I';
			digital_vals.push_back(
				((uint64_t)timestamp * 16777216) + (65536 * (uint64_t)c) + (uint64_t)input_val);
			last_input_val = input_val;
		}
		if (output_val != last_output_val)
		{
			char c = 'O';
			digital_vals.push_back(
				((uint64_t)timestamp * 16777216) + (65536 * (uint64_t)c) + (uint64_t)output_val);
			last_output_val = output_val;
		}
		sample_count += 1;
	}
	infile.close();
	auto finish = std::chrono::high_resolution_clock::now();
	std::chrono::duration<double> elapsed = finish - start;
	std::cout << "Elapsed time to read: " << elapsed.count() << " s\n";
	std::cout << "Number of input output samples: " << digital_vals.size() << std::endl;

	start = std::chrono::high_resolution_clock::now();
	std::ofstream outfile(_out_inpname, std::ios::out | std::ios::binary);
	outfile << std::string("bytes_per_sample ") << 7 << std::endl;
	outfile << std::string("timebase ") << 16000 << std::endl;
	outfile << std::string("num_inp_samples ") << digital_vals.size() << std::endl;
	outfile << std::string("data_start");
	for (int i = 0; i < digital_vals.size(); ++i)
	{
		auto byte_arr = IntToBytes(digital_vals[i]);
		outfile.write(byte_arr.data(), 7);
	}
	outfile << std::string("data_end");
	outfile.close();
	finish = std::chrono::high_resolution_clock::now();
	elapsed = finish - start;
	std::cout << "Elapsed time to write: " << elapsed.count() << " s\n";
	std::cout << "Result is at: " << _out_inpname << std::endl;
	return true;
}

bool const AxonaBinReader::Read()
{
  long long fsize = GetFileSize(GetBinFname());
  long long total_samples = fsize / _chunksize;
  total_samples *= _samples_per_chunk;
  std::cout << "Total samples " << total_samples << std::endl;

  const int buff_size = _chunksize;
  const int out_samples = 480000;
  std::vector<char> buffer(buff_size, 0);
  std::vector<std::vector<int16_t>> channel_data(
    _num_channels, std::vector<int16_t>(out_samples, 0));

  std::ifstream infile;
  infile.open(_bin_fname, std::ios::binary | std::ios::in);
  int sample_count = 0;
  /*uint64_t packet_number = 0;
  uint64_t last_packet_number = 0;*/

  auto start = std::chrono::high_resolution_clock::now();
  std::ofstream outfile(_out_fname, std::ios::out | std::ios::binary);
  const char header[5] = "bax1";
  outfile.write(header, 4);
  std::string str = std::to_string(total_samples);
  char const* pchar = str.c_str();
  outfile.write(pchar, 4);
  while (infile.read(buffer.data(), buffer.size()))
  {
    for (int i = _header_bytes; i < _chunksize - _trailer_bytes; i = i + _sample_bytes)
    {
      int compare_val = (i - _header_bytes) / 2;
      int row_sample = compare_val % _num_channels;
      int col_sample = (sample_count % out_samples) + (compare_val / _num_channels);
      int16_t val = ConvertBytes(buffer[i + 1], buffer[i]);
      channel_data[_reverse_map_channels[row_sample]][col_sample] = val;
    }

    /*packet_number = (16777216 * (uint8_t)buffer[7]) + (65536 * (uint8_t)buffer[6]) + (256 * (uint8_t)buffer[5]) + (uint8_t)buffer[4];
    if (last_packet_number != (packet_number - 1) && last_packet_number != 0)
    {
      std::cout << "Unorded packet number is " << packet_number << std::endl;
      uint8_t fi = (uint8_t)buffer[7];
      uint8_t se = (uint8_t)buffer[6];
      uint8_t th = (uint8_t)buffer[5];
      uint8_t fo = (uint8_t)buffer[4];
      std::cout << "Bytes " << (unsigned)fi << " " << (unsigned)se << " " << (unsigned)th << " " << (unsigned)fo << std::endl;
    }*/
    //last_packet_number = packet_number;
    sample_count += 3;
    if ((sample_count % out_samples == 0) || sample_count == total_samples) {
      // TODO change for the last write
      int num_samples_to_write = out_samples;
      if (sample_count == total_samples && total_samples % 3 != 0) {
        num_samples_to_write = total_samples % out_samples;
      }
      std::cout << "Writing samples " << num_samples_to_write << std::endl;
      int sample_size_to_write = _sample_bytes * num_samples_to_write;
      for (int i = 0; i < _num_channels; ++i)
      {
        outfile.write((char*)channel_data[i].data(), sample_size_to_write);
      }
    }
  }
infile.close();
outfile.close();
auto finish = std::chrono::high_resolution_clock::now();
std::chrono::duration<double> elapsed = finish - start;
std::cout << "Elapsed time to read and write: " << elapsed.count() << " s\n";
return true;
}

int main(int argc, char **argv)
{
	if (argc < 2)
	{
		std::cout << "Please enter at least one command line argument - the location of the .set file to convert" << std::endl;
		exit(-1);
	}
	std::string location(argv[1]);
	if (!file_exists(location))
	{
		std::cout << location << " is not a valid file path" << std::endl;
		exit(-1);
	}
	AxonaBinReader axbr{location};
	std::cout << "Converting " << location << std::endl;
	if (argc >= 3)
	{
		axbr.Read();
	}
	else
	{
		axbr.ToInp();
	}
}