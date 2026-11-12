#pragma once

#include <algorithm>
#include <cstdint>
#include <string>
#include <vector>

struct GoatsBleTransferState {
  bool enabled{false};
  bool connected{false};
  bool transfer_active{false};
  uint32_t last_activity_ms{0};
  size_t offset{0};
  std::vector<uint8_t> archive;
  std::vector<uint8_t> chunk;
};

static GoatsBleTransferState GOATS_BLE;

inline void goats_ble_setup() { GOATS_BLE = GoatsBleTransferState{}; }

inline void goats_ble_enable(uint32_t now_ms) {
  GOATS_BLE.enabled = true;
  GOATS_BLE.last_activity_ms = now_ms;
}

inline void goats_ble_disable() {
  GOATS_BLE = GoatsBleTransferState{};
}

inline void goats_ble_on_connect(uint32_t now_ms) {
  GOATS_BLE.connected = true;
  GOATS_BLE.last_activity_ms = now_ms;
}

inline void goats_ble_on_disconnect() {
  GOATS_BLE.connected = false;
  GOATS_BLE.transfer_active = false;
  GOATS_BLE.offset = 0;
  GOATS_BLE.chunk.clear();
}

inline void goats_ble_handle_command(const std::string &command,
                                     uint32_t now_ms) {
  GOATS_BLE.last_activity_ms = now_ms;

  if (command == "GET") {
    GOATS_BLE.archive = goats_sessions_export_blob();
    GOATS_BLE.offset = 0;
    GOATS_BLE.transfer_active = true;
  } else if (command == "CANCEL") {
    GOATS_BLE.transfer_active = false;
    GOATS_BLE.offset = 0;
    GOATS_BLE.chunk.clear();
  }
}

inline bool goats_ble_transfer_active() {
  return GOATS_BLE.transfer_active;
}

inline void goats_ble_prepare_next_chunk() {
  GOATS_BLE.chunk.clear();
  if (!GOATS_BLE.transfer_active) return;

  if (GOATS_BLE.offset >= GOATS_BLE.archive.size()) {
    GOATS_BLE.chunk = {'E', 'N', 'D'};
    GOATS_BLE.transfer_active = false;
    return;
  }

  constexpr size_t CHUNK_DATA = 176;
  const size_t count = std::min(
      CHUNK_DATA, GOATS_BLE.archive.size() - GOATS_BLE.offset);
  const uint32_t offset = static_cast<uint32_t>(GOATS_BLE.offset);

  GOATS_BLE.chunk.reserve(count + 4);
  GOATS_BLE.chunk.push_back(offset & 0xFF);
  GOATS_BLE.chunk.push_back((offset >> 8) & 0xFF);
  GOATS_BLE.chunk.push_back((offset >> 16) & 0xFF);
  GOATS_BLE.chunk.push_back((offset >> 24) & 0xFF);
  GOATS_BLE.chunk.insert(
      GOATS_BLE.chunk.end(),
      GOATS_BLE.archive.begin() + GOATS_BLE.offset,
      GOATS_BLE.archive.begin() + GOATS_BLE.offset + count);
  GOATS_BLE.offset += count;
  GOATS_BLE.last_activity_ms = millis();
}

inline std::vector<uint8_t> goats_ble_chunk() {
  return GOATS_BLE.chunk;
}

inline std::vector<uint8_t> goats_ble_status_bytes(bool connected) {
  std::string value;
  if (!GOATS_BLE.enabled) value = "OFF";
  else if (GOATS_BLE.transfer_active) value = "TRANSFER";
  else if (connected) value = "CONNECTED";
  else value = "READY";
  return std::vector<uint8_t>(value.begin(), value.end());
}

inline bool goats_ble_should_auto_disable(uint32_t now_ms) {
  return GOATS_BLE.enabled &&
         !GOATS_BLE.transfer_active &&
         static_cast<uint32_t>(
             now_ms - GOATS_BLE.last_activity_ms) >= 300000UL;
}
