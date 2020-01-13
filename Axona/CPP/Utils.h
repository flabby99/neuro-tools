#include <fstream>


long GetFileSize(std::string filename)
{
    long length;
    std::ifstream in(filename, std::ifstream::ate | std::ifstream::binary);
    length = in.tellg();
    return length;
}