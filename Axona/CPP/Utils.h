#include <sys/stat.h>
#include <fstream>
#include <iostream>
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

inline bool file_exists(const std::string& name) {
  struct stat buffer;
  return (stat(name.c_str(), &buffer) == 0);
}

inline std::string dir_from_file(const std::string& filename) {
  std::string directory;
  size_t last_slash_idx = filename.rfind('/');
  if (std::string::npos == last_slash_idx)
  {
      last_slash_idx = filename.rfind('\\');
  }
  if (std::string::npos != last_slash_idx)
  {
      directory = filename.substr(0, last_slash_idx+1);
  }
  return directory;
}