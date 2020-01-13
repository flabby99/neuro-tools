#pragma once
#include <string>
class AxonaBinReader
{
	std::string _set_fname;
	std::string _bin_fname;
	std::string _out_fname;

	int _remap_channels[64] = {
		32, 33, 34, 35, 36, 37, 38, 39,
		0, 1, 2, 3, 4, 5, 6, 7,
		40, 41, 42, 43, 44, 45, 46, 47,
		8, 9, 10, 11, 12, 13, 14, 15,
		48, 49, 50, 51, 52, 53, 54, 55,
		16, 17, 18, 19, 20, 21, 22, 23,
		56, 57, 58, 59, 60, 61, 62, 63,
		24, 25, 26, 27, 28, 29, 30, 31 };

	int _reverse_map_channels[64] = {
		8, 9, 10, 11, 12, 13, 14, 15,
		24, 25, 26, 27, 28, 29, 30, 31,
		40, 41, 42, 43, 44, 45, 46, 47,
		56, 57, 58, 59, 60, 61, 62, 63,
		0, 1, 2, 3, 4, 5, 6, 7,
		16, 17, 18, 19, 20, 21, 22, 23,
		32, 33, 34, 35, 36, 37, 38, 39,
		48, 49, 50, 51, 52, 53, 54, 55 };

	const int _sample_bytes = 2;
	const int _channel_bytes = 128;
	const int _header_bytes = 32;
	const int _chunksize = 432;
	const int _trailer_bytes = 16;
	const int _samples_per_chunk = 3;
	int _num_channels = 64;

	int16_t ConvertBytes(char b1, char b2);
public:
	AxonaBinReader();
	AxonaBinReader(std::string name);
	void Init(std::string name);
	bool const Read();
	inline const std::string& GetSetFname() { return _set_fname; }
	inline void SetSetFname(const std::string& name) {
		_set_fname = name;
	}
	inline const std::string& GetBinFname() { return _bin_fname; }
	inline void SetBinFname(const std::string& name) {
		_bin_fname = name;
	}
};

