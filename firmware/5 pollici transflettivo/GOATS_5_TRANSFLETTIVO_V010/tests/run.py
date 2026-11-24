"""Run parser and actual component-loop tests with a minimal fake UART."""
from pathlib import Path
import argparse
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--sanitize", action="store_true")
args = parser.parse_args()

with tempfile.TemporaryDirectory() as temporary:
    tmp = Path(temporary)
    stubs = {
        "esphome/core/component.h": """#pragma once
namespace esphome {class Component {public: virtual ~Component()=default;
virtual void loop(){} virtual void dump_config(){}};}
""",
        "esphome/core/hal.h": """#pragma once
#include <cstdint>
namespace esphome {inline uint32_t simulated_ms=0;
inline uint32_t millis(){return simulated_ms;}}
""",
        "esphome/core/log.h": """#pragma once
#define ESP_LOGCONFIG(tag, ...) ((void)(tag))
""",
        "esphome/components/uart/uart.h": """#pragma once
#include <cstdint>
#include <cstddef>
#include <vector>
namespace esphome::uart {
enum UARTParityOptions {UART_CONFIG_PARITY_NONE};
class UARTComponent {public:
  void feed(const std::vector<uint8_t>&b){bytes=b;at=0;}
  size_t available(){return bytes.size()-at;}
  bool read_byte(uint8_t*b){if(!available())return false;*b=bytes[at++];return true;}
  size_t get_rx_buffer_size(){return 8192;}
private:std::vector<uint8_t>bytes;size_t at=0;
};
class UARTDevice {public:
  void set_uart_parent(UARTComponent*p){parent_=p;}
  size_t available(){return parent_->available();}
  bool read_byte(uint8_t*b){return parent_->read_byte(b);}
  void check_uart_settings(unsigned,unsigned,UARTParityOptions,unsigned){}
protected:UARTComponent*parent_=nullptr;
};
}
""",
    }
    for relative, content in stubs.items():
        target = tmp / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    component = root / "components/goats_core"
    flags = ["-std=c++17", "-Wall", "-Wextra", "-Werror"]
    if args.sanitize:
        flags += ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
    for test, sources in [
        ("test_nav_pvt", ["nav_pvt.cpp"]),
        ("test_goats_core", ["nav_pvt.cpp", "goats_core.cpp"]),
    ]:
        binary = tmp / test
        subprocess.run(
            ["g++", *flags, "-I", str(tmp), "-I", str(component),
             str(root / "tests" / (test + ".cpp")),
             *(str(component / source) for source in sources), "-o", str(binary)],
            check=True,
        )
        subprocess.run([str(binary)], check=True)
