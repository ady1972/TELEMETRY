#include "goats_m9n_cfg.h"
#include <iostream>
#include <iomanip>
int main(){
 esphome::uart::UARTComponent u;goats_cfg::configure(u);
 for(auto b:u.bauds)std::cout<<"B "<<b<<"\n";
 for(auto d:delays)std::cout<<"D "<<d<<"\n";
 for(const auto&f:u.writes){std::cout<<"F ";for(auto c:f)std::cout<<std::hex<<std::setw(2)<<std::setfill('0')<<unsigned(c);std::cout<<"\n";}
}
