#pragma once
namespace esphome {struct Component {
 virtual ~Component()=default;
 virtual void setup(){} virtual void loop(){} virtual void dump_config(){}
};}
