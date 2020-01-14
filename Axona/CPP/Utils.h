#include <fstream>
#include <vector>

long long GetFileSize(std::string filename)
{
    long long length;
    std::ifstream in(filename, std::ifstream::ate | std::ifstream::binary);
    length = in.tellg();
    return length;
}

std::vector<char> IntToBytes(uint64_t value)
{
  std::vector<char> result;
  result.push_back(value >> 48);
  result.push_back(value >> 40);
  result.push_back(value >> 32);
  result.push_back(value >> 24);
  result.push_back(value >> 16);
  result.push_back(value >> 8);
  result.push_back(value);
  return result;
}