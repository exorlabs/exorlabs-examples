// Test the exact ArduinoJson decoder used by the ESP32 against an HTTP payload file.
#include <fstream>
#include <iostream>
#include <sstream>
#include "parse_snapshot.h"
int main(int argc,char **argv)
{
    if(argc!=3)return 2;
    std::ifstream file(argv[1]);std::stringstream text;text<<file.rdbuf();
    StatsSnapshot snapshot={};
    if(!stats_parse(text.str().c_str(),argv[2],1234,&snapshot)){std::cerr<<"Schema rejected\n";return 1;}
    std::cout<<"PASS source="<<argv[2]<<" cpu="<<snapshot.cpu_percent<<" memory="<<snapshot.memory_percent
             <<" disk="<<snapshot.storage_percent<<" stale="<<snapshot.stale<<" simulated="<<snapshot.simulated<<"\n";
}
