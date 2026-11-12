#pragma once

#include "esphome.h"
#include "goats_diagnostics.h"

#include <algorithm>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <utility>
#include <cstring>
#include <dirent.h>
#include <string>
#include <sys/stat.h>
#include <unistd.h>
#include <vector>

#include "driver/spi_master.h"
#include "driver/sdspi_host.h"
#include "esp_vfs_fat.h"
#include "sdmmc_cmd.h"
#include "driver/gpio.h"
#include "ff.h"

namespace goats_sd_storage {

static constexpr const char *MOUNT_POINT = "/sdcard";
static constexpr const char *ROOT_DIR = "/sdcard/goats";
static constexpr const char *ARCHIVE_FILE = "/sdcard/goats/archive.gsa3";
static constexpr const char *LIVE_FILE = "/sdcard/goats/live.csv";
static constexpr const char *CHECKPOINT_FILE = "/sdcard/goats/session_checkpoint.gsa3";

static sdmmc_card_t *g_card = nullptr;
static bool g_ready = false;
static bool g_bus_initialized = false;
static FIL g_live{};
static bool g_live_is_open = false;
static uint32_t g_live_points = 0;
static uint32_t g_flush_counter = 0;
static bool g_writable = false;
static char g_live_track_file[40] = "SESSIONE";
static char g_live_date_file[16] = "DATA";
static char g_live_time_file[12] = "ORA";
static int g_last_errno = 0;
static std::string g_last_stage = "BOOT";
static int g_last_fresult = 0;
static int g_last_mount_err = 0;

static inline bool ready() { return g_ready; }
static inline sdmmc_card_t *card_handle() { return g_card; }

static inline bool prepare_for_usb_msc() {
  goats_diag_v1021::SdScope diag_scope(goats_diag_v1021::SdKind::FINALIZE);
  if (g_card == nullptr) {
    g_last_stage = "MSC_NO_CARD";
    return false;
  }

  if (g_live_is_open) {
    (void) f_sync(&g_live);
    (void) f_close(&g_live);
    g_live_is_open = false;
  }

  // Give exclusive filesystem ownership to the USB host while leaving
  // the SDSPI card object and SPI bus alive for raw sector access.
  const FRESULT fr = f_mount(nullptr, "0:", 1);
  if (fr != FR_OK && fr != FR_NOT_ENABLED) {
    g_last_fresult = static_cast<int>(fr);
    g_last_stage = "MSC_FAT_RELEASE_FAIL";
    return false;
  }

  g_ready = false;
  g_writable = false;
  g_last_fresult = static_cast<int>(FR_OK);
  g_last_stage = "MSC_USB_OWNS_SD";
  return true;
}

static inline void release_for_shutdown();
static inline bool writable() { return g_ready && g_writable; }
static inline int last_errno() { return g_last_errno; }
static inline const char *last_stage() { return g_last_stage.c_str(); }
static inline int last_mount_error() { return g_last_mount_err; }

static inline const char *esp_err_name_safe_(int err) {
  switch (err) {
    case ESP_OK: return "ESP_OK";
    case ESP_FAIL: return "ESP_FAIL";
    case ESP_ERR_NO_MEM: return "ESP_ERR_NO_MEM";
    case ESP_ERR_INVALID_ARG: return "ESP_ERR_INVALID_ARG";
    case ESP_ERR_INVALID_STATE: return "ESP_ERR_INVALID_STATE";
    case ESP_ERR_NOT_FOUND: return "ESP_ERR_NOT_FOUND";
    case ESP_ERR_NOT_SUPPORTED: return "ESP_ERR_NOT_SUPPORTED";
    case ESP_ERR_TIMEOUT: return "ESP_ERR_TIMEOUT";
    default: return esp_err_to_name(static_cast<esp_err_t>(err));
  }
}

static inline const char *last_mount_error_name() {
  return esp_err_name_safe_(g_last_mount_err);
}


static inline void set_error_(const char *stage, int err = 0) {
  g_last_stage = stage ? stage : "UNKNOWN";
  g_last_errno = err;
  g_last_fresult = 0;
  g_writable = false;
}

static inline void set_fatfs_error_(const char *stage, FRESULT fr) {
  g_last_stage = stage ? stage : "FATFS";
  g_last_errno = 0;
  g_last_fresult = static_cast<int>(fr);
  g_writable = false;
}

static inline void set_ok_(const char *stage) {
  g_last_stage = stage ? stage : "OK";
  g_last_errno = 0;
  g_last_fresult = 0;
  g_writable = true;
}

static inline int last_fresult() { return g_last_fresult; }

static inline const char *fresult_name_(int fr) {
  switch (fr) {
    case FR_OK: return "FR_OK";
    case FR_DISK_ERR: return "FR_DISK_ERR";
    case FR_INT_ERR: return "FR_INT_ERR";
    case FR_NOT_READY: return "FR_NOT_READY";
    case FR_NO_FILE: return "FR_NO_FILE";
    case FR_NO_PATH: return "FR_NO_PATH";
    case FR_INVALID_NAME: return "FR_INVALID_NAME";
    case FR_DENIED: return "FR_DENIED";
    case FR_EXIST: return "FR_EXIST";
    case FR_INVALID_OBJECT: return "FR_INVALID_OBJECT";
    case FR_WRITE_PROTECTED: return "FR_WRITE_PROTECTED";
    case FR_INVALID_DRIVE: return "FR_INVALID_DRIVE";
    case FR_NOT_ENABLED: return "FR_NOT_ENABLED";
    case FR_NO_FILESYSTEM: return "FR_NO_FILESYSTEM";
    case FR_MKFS_ABORTED: return "FR_MKFS_ABORTED";
    case FR_TIMEOUT: return "FR_TIMEOUT";
    case FR_LOCKED: return "FR_LOCKED";
    case FR_NOT_ENOUGH_CORE: return "FR_NOT_ENOUGH_CORE";
    case FR_TOO_MANY_OPEN_FILES: return "FR_TOO_MANY_OPEN_FILES";
    case FR_INVALID_PARAMETER: return "FR_INVALID_PARAMETER";
    default: return "FR_UNKNOWN";
  }
}

static inline const char *last_fresult_name() {
  return fresult_name_(g_last_fresult);
}

static inline const char *errno_name_(int e) {
  switch (e) {
    case 0: return "OK";
    case EROFS: return "EROFS";
    case EIO: return "EIO";
    case ENOSPC: return "ENOSPC";
    case EACCES: return "EACCES";
    case EPERM: return "EPERM";
    case ENOENT: return "ENOENT";
    case EEXIST: return "EEXIST";
    case ENOTDIR: return "ENOTDIR";
    case EINVAL: return "EINVAL";
    default: return "ERRNO";
  }
}

static inline const char *last_errno_name() {
  return errno_name_(g_last_errno);
}

static inline bool root_write_probe_() {
  if (!g_ready) {
    set_error_("ROOT_NOT_MOUNTED");
    return false;
  }

  // Step 1: strict 8.3 filename in FAT root.
  const TCHAR *root_file = "0:/TEST.TXT";
  static const uint8_t probe[] = {
      0x47,0x4F,0x41,0x54,0x53,0x2D,0x38,0x33
  };

  FIL file{};
  UINT written = 0;
  UINT read = 0;

  FRESULT fr = f_open(&file, root_file, FA_CREATE_ALWAYS | FA_WRITE);
  if (fr != FR_OK) {
    set_fatfs_error_("83_OPEN_W", fr);
    return false;
  }

  fr = f_write(&file, probe, sizeof(probe), &written);
  if (fr == FR_OK && written == sizeof(probe))
    fr = f_sync(&file);
  FRESULT close_fr = f_close(&file);
  if (fr == FR_OK && close_fr != FR_OK) fr = close_fr;

  if (fr != FR_OK || written != sizeof(probe)) {
    f_unlink(root_file);
    set_fatfs_error_("83_WRITE", fr);
    return false;
  }

  uint8_t verify[sizeof(probe)]{};
  fr = f_open(&file, root_file, FA_READ);
  if (fr != FR_OK) {
    f_unlink(root_file);
    set_fatfs_error_("83_OPEN_R", fr);
    return false;
  }

  fr = f_read(&file, verify, sizeof(verify), &read);
  close_fr = f_close(&file);
  if (fr == FR_OK && close_fr != FR_OK) fr = close_fr;
  f_unlink(root_file);

  if (fr != FR_OK || read != sizeof(probe) ||
      std::memcmp(probe, verify, sizeof(probe)) != 0) {
    set_fatfs_error_("83_VERIFY", fr);
    return false;
  }

  // Step 2: verify whether a simple 8.3 GOATS directory can be created.
  FILINFO info{};
  fr = f_stat("0:/GOATS", &info);
  if (fr == FR_NO_FILE || fr == FR_NO_PATH) {
    fr = f_mkdir("0:/GOATS");
    if (fr != FR_OK && fr != FR_EXIST) {
      set_fatfs_error_("GOATS_MKDIR", fr);
      return false;
    }
  } else if (fr != FR_OK) {
    set_fatfs_error_("GOATS_STAT", fr);
    return false;
  }

  fr = f_stat("0:/GOATS", &info);
  if (fr != FR_OK) {
    set_fatfs_error_("GOATS_VERIFY", fr);
    return false;
  }

  set_ok_("83_AND_GOATS_OK");
  return true;
}

struct SdFileInfo {
  std::string name;
  uint32_t size{0};
};

static inline bool valid_user_file_name_(const char *name) {
  if (!name || !name[0]) return false;
  const std::string n(name);
  if (n.size() > 80 || n == "." || n == "..") return false;
  if (n.find("..") != std::string::npos) return false;
  return n.find('/') == std::string::npos && n.find('\\') == std::string::npos;
}

static inline std::vector<SdFileInfo> list_files() {
  goats_diag_v1021::SdScope diag_scope(goats_diag_v1021::SdKind::READ);
  std::vector<SdFileInfo> out;
  if (!g_ready) return out;
  DIR *d = opendir(ROOT_DIR);
  if (!d) return out;
  struct dirent *e = nullptr;
  while ((e = readdir(d)) != nullptr) {
    if (!valid_user_file_name_(e->d_name)) continue;
    if (std::strcmp(e->d_name, "archive.tmp") == 0) continue;
    const std::string path = std::string(ROOT_DIR) + "/" + e->d_name;
    struct stat st{};
    if (stat(path.c_str(), &st) != 0 || !S_ISREG(st.st_mode)) continue;
    SdFileInfo item;
    item.name = e->d_name;
    item.size = static_cast<uint32_t>(std::min<off_t>(st.st_size, 0xFFFFFFFF));
    out.push_back(std::move(item));
  }
  closedir(d);
  std::sort(out.begin(), out.end(), [](const SdFileInfo &a, const SdFileInfo &b) {
    return a.name < b.name;
  });
  return out;
}

static inline FILE *open_read_file(const char *name, uint32_t &size) {
  goats_diag_v1021::SdScope diag_scope(goats_diag_v1021::SdKind::READ);
  size = 0;
  if (!g_ready || !valid_user_file_name_(name)) return nullptr;
  const std::string path = std::string(ROOT_DIR) + "/" + name;
  struct stat st{};
  if (stat(path.c_str(), &st) != 0 || !S_ISREG(st.st_mode) || st.st_size < 0 ||
      static_cast<uint64_t>(st.st_size) > 0xFFFFFFFFULL) return nullptr;
  FILE *f = std::fopen(path.c_str(), "rb");
  if (!f) return nullptr;
  size = static_cast<uint32_t>(st.st_size);
  return f;
}

static inline bool write_checkpoint(const std::vector<uint8_t> &data) {
  goats_diag_v1021::SdScope diag_scope(goats_diag_v1021::SdKind::CHECKPOINT);
  if (!g_ready || data.size() < 8) return false;
  const char *tmp = "/sdcard/goats/session_checkpoint.tmp";
  FILE *f = std::fopen(tmp, "wb");
  if (!f) return false;
  bool ok = std::fwrite(data.data(), 1, data.size(), f) == data.size();
  if (ok) ok = std::fflush(f) == 0;
  const int fd = fileno(f);
  if (ok && fd >= 0) ok = fsync(fd) == 0;
  std::fclose(f);
  if (!ok) { unlink(tmp); return false; }

  std::vector<uint8_t> verify(data.size());
  f = std::fopen(tmp, "rb");
  if (!f) { unlink(tmp); return false; }
  ok = std::fread(verify.data(), 1, verify.size(), f) == verify.size();
  std::fclose(f);
  if (!ok || verify != data) { unlink(tmp); return false; }

  unlink(CHECKPOINT_FILE);
  return rename(tmp, CHECKPOINT_FILE) == 0;
}

static inline bool read_checkpoint(std::vector<uint8_t> &data) {
  goats_diag_v1021::SdScope diag_scope(goats_diag_v1021::SdKind::READ);
  data.clear();
  if (!g_ready) return false;
  FILE *f = std::fopen(CHECKPOINT_FILE, "rb");
  if (!f) return false;
  std::fseek(f, 0, SEEK_END);
  const long n = std::ftell(f);
  std::rewind(f);
  if (n < 8 || n > 2 * 1024 * 1024) { std::fclose(f); return false; }
  data.resize(static_cast<size_t>(n));
  const bool ok = std::fread(data.data(), 1, data.size(), f) == data.size();
  std::fclose(f);
  if (!ok) data.clear();
  return ok;
}

static inline void remove_checkpoint() {
  goats_diag_v1021::SdScope diag_scope(goats_diag_v1021::SdKind::METADATA);
  if (g_ready) unlink(CHECKPOINT_FILE);
}

static inline bool ensure_dir_() {
  if (!g_ready) {
    set_error_("DIR_NOT_MOUNTED");
    return false;
  }

  // V11.0.2.23: directory management is done directly through FatFS.
  // Do not use POSIX stat()/mkdir() here: the card is already mounted and
  // the previous builds showed that the VFS view could disagree with FatFS.
  FILINFO info{};
  FRESULT fr = f_stat("0:/GOATS", &info);
  if (fr == FR_NO_FILE || fr == FR_NO_PATH) {
    fr = f_mkdir("0:/GOATS");
    if (fr != FR_OK && fr != FR_EXIST) {
      set_fatfs_error_("DIR_MKDIR_FAT", fr);
      return false;
    }
    fr = f_stat("0:/GOATS", &info);
  }

  if (fr != FR_OK) {
    set_fatfs_error_("DIR_STAT_FAT", fr);
    return false;
  }
  if ((info.fattrib & AM_DIR) == 0) {
    set_fatfs_error_("DIR_NOT_DIR", FR_INVALID_OBJECT);
    return false;
  }

  set_ok_("DIR_FATFS_OK");
  return true;
}

static inline bool write_probe_() {
  if (!g_ready) {
    set_error_("NOT_MOUNTED");
    return false;
  }
  if (!ensure_dir_()) return false;

  // V11.0.2.23: complete write/read/delete test directly inside 0:/GOATS.
  // This intentionally bypasses fopen/stat/mkdir VFS for the SD diagnostic.
  const TCHAR *name = "0:/GOATS/RWTEST.BIN";
  static const uint8_t probe[] = {
      0x47,0x4F,0x41,0x54,0x53,0x2D,0x52,0x57,0x2D,0x32,0x33
  };

  FIL file{};
  UINT written = 0;
  UINT read = 0;
  FRESULT fr = f_open(&file, name, FA_CREATE_ALWAYS | FA_WRITE);
  if (fr != FR_OK) {
    set_fatfs_error_("GOATS_OPEN_W", fr);
    return false;
  }

  fr = f_write(&file, probe, sizeof(probe), &written);
  if (fr == FR_OK && written == sizeof(probe)) fr = f_sync(&file);
  FRESULT close_fr = f_close(&file);
  if (fr == FR_OK && close_fr != FR_OK) fr = close_fr;
  if (fr != FR_OK || written != sizeof(probe)) {
    f_unlink(name);
    set_fatfs_error_("GOATS_WRITE", fr);
    return false;
  }

  uint8_t verify[sizeof(probe)]{};
  fr = f_open(&file, name, FA_READ);
  if (fr != FR_OK) {
    f_unlink(name);
    set_fatfs_error_("GOATS_OPEN_R", fr);
    return false;
  }

  fr = f_read(&file, verify, sizeof(verify), &read);
  close_fr = f_close(&file);
  if (fr == FR_OK && close_fr != FR_OK) fr = close_fr;

  if (fr != FR_OK || read != sizeof(probe) ||
      std::memcmp(probe, verify, sizeof(probe)) != 0) {
    f_unlink(name);
    set_fatfs_error_("GOATS_READ", fr);
    return false;
  }

  fr = f_unlink(name);
  if (fr != FR_OK && fr != FR_NO_FILE) {
    set_fatfs_error_("GOATS_DELETE", fr);
    return false;
  }

  g_writable = true;
  set_ok_("GOATS_RW_OK");
  return true;
}

static inline void recover_live_() {
  struct stat st{};
  if (stat(LIVE_FILE, &st) != 0) return;

  for (unsigned i = 1; i < 1000; ++i) {
    char name[96];
    std::snprintf(name, sizeof(name),
                  "/sdcard/goats/r%03u.csv", i);
    if (stat(name, &st) != 0) {
      rename(LIVE_FILE, name);
      return;
    }
  }
}

static inline bool setup() {
  goats_diag_v1021::SdScope diag_scope(goats_diag_v1021::SdKind::MOUNT);
  if (g_ready || g_card != nullptr) return g_ready;
  if (g_ready) return true;

  // JC4827W543 onboard TF slot (SDSPI):
  // CS=GPIO10, MOSI=GPIO11, SCK=GPIO12, MISO=GPIO13.
  //
  // ESP-IDF requires SD CMD/DATA lines to be pulled up in SPI mode.
  // Enable only the ESP32-S3 internal weak pull-ups as a diagnostic:
  //   GPIO10 = CS / DAT3
  //   GPIO11 = MOSI / CMD
  //   GPIO13 = MISO / DAT0
  // Do NOT alter GPIO12/SCK and do NOT reset/drive CS manually.
  gpio_pullup_en(GPIO_NUM_10);
  gpio_pulldown_dis(GPIO_NUM_10);
  gpio_pullup_en(GPIO_NUM_11);
  gpio_pulldown_dis(GPIO_NUM_11);
  gpio_pullup_en(GPIO_NUM_13);
  gpio_pulldown_dis(GPIO_NUM_13);
  delay(20);

  sdmmc_host_t host = SDSPI_HOST_DEFAULT();
  host.slot = SPI3_HOST;
  host.max_freq_khz = 4000;

  spi_bus_config_t bus_cfg{};
  bus_cfg.mosi_io_num = GPIO_NUM_11;
  bus_cfg.miso_io_num = GPIO_NUM_13;
  bus_cfg.sclk_io_num = GPIO_NUM_12;
  bus_cfg.quadwp_io_num = -1;
  bus_cfg.quadhd_io_num = -1;
  bus_cfg.max_transfer_sz = 4096;

  esp_err_t err = spi_bus_initialize(
      static_cast<spi_host_device_t>(host.slot),
      &bus_cfg,
      SPI_DMA_CH_AUTO);
  if (err == ESP_OK) {
    g_bus_initialized = true;
  } else if (err != ESP_ERR_INVALID_STATE) {
    g_ready = false;
    return false;
  }

  sdspi_device_config_t slot = SDSPI_DEVICE_CONFIG_DEFAULT();
  slot.gpio_cs = GPIO_NUM_10;
  slot.host_id = static_cast<spi_host_device_t>(host.slot);

  esp_vfs_fat_sdmmc_mount_config_t mount{};
  mount.format_if_mount_failed = false;
  mount.max_files = 8;
  mount.allocation_unit_size = 16 * 1024;

  // Conservative diagnostic: let SD power/signals settle before the
  // normal mount. No manual CS manipulation and no retry/unmount cycle.
  delay(750);

  g_last_mount_err = 0;
  err = esp_vfs_fat_sdspi_mount(
      MOUNT_POINT, &host, &slot, &mount, &g_card);
  if (err != ESP_OK) {
    g_last_mount_err = static_cast<int>(err);
    g_ready = false;
    g_writable = false;
    g_last_stage = "MOUNT_FAIL";
    g_last_errno = 0;
    g_last_fresult = 0;
    if (g_bus_initialized) {
      spi_bus_free(static_cast<spi_host_device_t>(host.slot));
      g_bus_initialized = false;
    }
    return false;
  }

  g_last_mount_err = ESP_OK;
  g_ready = true;
  if (!ensure_dir_()) return true;  // mounted but not writable
  recover_live_();
  write_probe_();
  return true;
}



// USB session download recovery.
// If the card was mounted at boot but g_ready later became false, setup()
// alone cannot recover because a stale g_card can remain. For a Manager read
// request we explicitly tear down the SDSPI state and mount it again.
static inline bool ensure_ready_for_usb_read(unsigned attempts = 3) {
  goats_diag_v1021::SdScope diag_scope(goats_diag_v1021::SdKind::MOUNT);
  if (attempts == 0) attempts = 1;

  // Lightweight recovery only: never tear down/remount SDSPI/VFS at runtime.
  // The card was already mounted successfully at boot; for a USB read request
  // we only probe the existing FatFS object and restore g_ready when accessible.
  for (unsigned attempt = 0; attempt < attempts; ++attempt) {
    FF_DIR dir{};
    FRESULT fr = f_opendir(&dir, "0:/GOATS");
    if (fr == FR_OK) {
      (void) f_closedir(&dir);
      g_ready = true;
      g_last_mount_err = 0;
      g_last_fresult = static_cast<int>(FR_OK);
      g_last_stage = "USB_PROBE_OK";
      return true;
    }

    g_last_fresult = static_cast<int>(fr);
    g_last_stage = "USB_PROBE_RETRY";

    // Short settle only; do not call release_for_shutdown()/setup().
    delay(150 + attempt * 150);
  }

  g_ready = false;
  g_last_stage = "USB_PROBE_FAIL";
  return false;
}


static inline bool fat_write_blob_atomic_(
    const char *final_name,
    const char *temp_name,
    const std::vector<uint8_t> &data,
    const char *stage_prefix) {
  if (!g_ready || !final_name || !temp_name || data.size() < 8) return false;
  if (!g_writable && !write_probe_()) return false;
  if (!ensure_dir_()) return false;

  FIL f{};
  FRESULT fr = f_open(&f, temp_name, FA_CREATE_ALWAYS | FA_WRITE);
  if (fr != FR_OK) {
    set_fatfs_error_(stage_prefix, fr);
    return false;
  }

  UINT total = 0;
  while (total < data.size()) {
    UINT written = 0;
    fr = f_write(&f, data.data() + total,
                 static_cast<UINT>(data.size() - total), &written);
    if (fr != FR_OK || written == 0) break;
    total += written;
  }
  if (fr == FR_OK && total == data.size()) fr = f_sync(&f);
  FRESULT close_fr = f_close(&f);
  if (fr == FR_OK && close_fr != FR_OK) fr = close_fr;

  if (fr != FR_OK || total != data.size()) {
    (void) f_unlink(temp_name);
    set_fatfs_error_(stage_prefix, fr == FR_OK ? FR_DISK_ERR : fr);
    return false;
  }

  // Verify the temporary blob byte-for-byte.
  fr = f_open(&f, temp_name, FA_READ);
  if (fr != FR_OK) {
    (void) f_unlink(temp_name);
    set_fatfs_error_("BLOB_VERIFY_OPEN", fr);
    return false;
  }
  std::vector<uint8_t> verify(data.size());
  UINT read = 0;
  fr = f_read(&f, verify.data(), static_cast<UINT>(verify.size()), &read);
  close_fr = f_close(&f);
  if (fr == FR_OK && close_fr != FR_OK) fr = close_fr;
  if (fr != FR_OK || read != verify.size() || verify != data) {
    (void) f_unlink(temp_name);
    set_fatfs_error_("BLOB_VERIFY", fr == FR_OK ? FR_INT_ERR : fr);
    return false;
  }

  (void) f_unlink(final_name);
  fr = f_rename(temp_name, final_name);
  if (fr != FR_OK) {
    (void) f_unlink(temp_name);
    set_fatfs_error_("BLOB_RENAME", fr);
    return false;
  }

  set_ok_("BLOB_SAVED");
  return true;
}

static inline bool fat_read_blob_(
    const char *name,
    std::vector<uint8_t> &data,
    size_t max_size = 2 * 1024 * 1024) {
  data.clear();
  if (!g_ready || !name) return false;

  FILINFO info{};
  FRESULT fr = f_stat(name, &info);
  if (fr != FR_OK || info.fsize < 8 || info.fsize > max_size) return false;

  FIL f{};
  fr = f_open(&f, name, FA_READ);
  if (fr != FR_OK) return false;

  data.resize(static_cast<size_t>(info.fsize));
  UINT read = 0;
  fr = f_read(&f, data.data(), static_cast<UINT>(data.size()), &read);
  FRESULT close_fr = f_close(&f);
  if (fr == FR_OK && close_fr != FR_OK) fr = close_fr;
  if (fr != FR_OK || read != data.size()) {
    data.clear();
    return false;
  }
  return true;
}

static inline bool write_archive(const std::vector<uint8_t> &data) {
  goats_diag_v1021::SdScope diag_scope(goats_diag_v1021::SdKind::METADATA);
  return fat_write_blob_atomic_(
      "0:/GOATS/ARCHIVE.GSA",
      "0:/GOATS/ARCHTMP.GSA",
      data,
      "ARCHIVE_WRITE");
}

static inline bool write_sector_file(uint32_t sid, const std::vector<uint8_t> &data) {
  goats_diag_v1021::SdScope diag_scope(goats_diag_v1021::SdKind::METADATA);
  if (!ready() || !sid) return false;
  char name[40], tmp[40];
  std::snprintf(name,sizeof(name),"0:/GOATS/E%06lu.GSE",(unsigned long)sid);
  std::snprintf(tmp,sizeof(tmp),"0:/GOATS/E%06lu.TMP",(unsigned long)sid);
  return fat_write_blob_atomic_(name,tmp,data);
}
static inline bool read_sector_file(uint32_t sid, std::vector<uint8_t> &data) {
  if (!ready() || !sid) return false;
  char name[40];
  std::snprintf(name,sizeof(name),"0:/GOATS/E%06lu.GSE",(unsigned long)sid);
  return fat_read_blob_(name,data);
}
static inline void remove_sector_file(uint32_t sid) {
  if (!ready() || !sid) return;
  char name[40];
  std::snprintf(name,sizeof(name),"0:/GOATS/E%06lu.GSE",(unsigned long)sid);
  (void) f_unlink(name);
}

static inline bool read_archive(std::vector<uint8_t> &data) {
  goats_diag_v1021::SdScope diag_scope(goats_diag_v1021::SdKind::READ);
  return fat_read_blob_("0:/GOATS/ARCHIVE.GSA", data);
}

static inline bool remove_archive() {
  goats_diag_v1021::SdScope diag_scope(goats_diag_v1021::SdKind::METADATA);
  if (!g_ready) return false;
  const FRESULT fr = f_unlink("0:/GOATS/ARCHIVE.GSA");
  return fr == FR_OK || fr == FR_NO_FILE;
}


// ============================================================
// V11/V10 SESSION PERSISTENCE V2
// Redundant compact metadata per session.
// archive.gsa3 remains the global index, while each session also has
// session_XXXXXX_meta.gsa3.  This avoids losing the whole list when a
// single archive commit fails.
// ============================================================
static inline bool write_session_meta(
    uint32_t session_id,
    const std::vector<uint8_t> &data) {
  goats_diag_v1021::SdScope diag_scope(goats_diag_v1021::SdKind::METADATA);
  if (!g_ready || session_id == 0 || data.size() < 8) return false;

  char final_name[32];
  char temp_name[32];
  std::snprintf(final_name, sizeof(final_name),
                "0:/GOATS/M%06lu.GSA",
                static_cast<unsigned long>(session_id));
  std::snprintf(temp_name, sizeof(temp_name),
                "0:/GOATS/T%06lu.GSA",
                static_cast<unsigned long>(session_id));

  return fat_write_blob_atomic_(
      final_name, temp_name, data, "META_WRITE");
}

static inline bool read_session_meta(
    uint32_t session_id,
    std::vector<uint8_t> &data) {
  goats_diag_v1021::SdScope diag_scope(goats_diag_v1021::SdKind::READ);
  if (!g_ready || session_id == 0) {
    data.clear();
    return false;
  }
  char name[32];
  std::snprintf(name, sizeof(name),
                "0:/GOATS/M%06lu.GSA",
                static_cast<unsigned long>(session_id));
  return fat_read_blob_(name, data, 128 * 1024);
}

static inline std::vector<uint32_t> list_session_meta_ids() {
  goats_diag_v1021::SdScope diag_scope(goats_diag_v1021::SdKind::READ);
  std::vector<uint32_t> ids;
  if (!g_ready) return ids;

  FF_DIR dir{};
  FILINFO info{};
  FRESULT fr = f_opendir(&dir, "0:/GOATS");
  if (fr != FR_OK) return ids;

  while (true) {
    fr = f_readdir(&dir, &info);
    if (fr != FR_OK || info.fname[0] == 0) break;
    unsigned long id = 0;
    char tail = 0;
    if (std::sscanf(info.fname, "M%06lu.GSA%c", &id, &tail) == 1 &&
        id > 0 && id <= 0xFFFFFFFFUL) {
      ids.push_back(static_cast<uint32_t>(id));
    }
  }
  f_closedir(&dir);
  std::sort(ids.begin(), ids.end());
  ids.erase(std::unique(ids.begin(), ids.end()), ids.end());
  return ids;
}

static inline void remove_session_meta(uint32_t session_id) {
  goats_diag_v1021::SdScope diag_scope(goats_diag_v1021::SdKind::METADATA);
  if (!g_ready || session_id == 0) return;
  char name[32];
  std::snprintf(name, sizeof(name),
                "0:/GOATS/M%06lu.GSA",
                static_cast<unsigned long>(session_id));
  (void) f_unlink(name);
  std::snprintf(name,sizeof(name),"0:/GOATS/M%06lu.TRC",(unsigned long)session_id);
  (void) f_unlink(name);
}

static inline void write_last_save_status(
    uint32_t session_id,
    bool meta_ok,
    bool archive_ok,
    bool trace_ok) {
  goats_diag_v1021::SdScope diag_scope(goats_diag_v1021::SdKind::METADATA);
  if (!g_ready) return;
  ensure_dir_();
  const char *name = "/sdcard/goats/last_save_status.txt";
  FILE *f = std::fopen(name, "wb");
  if (!f) return;
  std::fprintf(
      f,
      "session_id=%lu\nmeta=%s\narchive=%s\ntrace=%s\n",
      static_cast<unsigned long>(session_id),
      meta_ok ? "OK" : "ERR",
      archive_ok ? "OK" : "ERR",
      trace_ok ? "OK" : "ERR");
  std::fflush(f);
  const int fd = fileno(f);
  if (fd >= 0) fsync(fd);
  std::fclose(f);
}

static inline void sanitize_file_part_(
    const char *src, char *dst, size_t dst_size, const char *fallback) {
  if (!dst || dst_size == 0) return;
  size_t w = 0;
  const char *p = src ? src : "";
  bool last_sep = false;
  while (*p && w + 1 < dst_size) {
    unsigned char c = static_cast<unsigned char>(*p++);
    char out = 0;
    if ((c >= 'a' && c <= 'z')) out = static_cast<char>(c - 'a' + 'A');
    else if ((c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9')) out = static_cast<char>(c);
    else if (c == ' ' || c == '-' || c == '_' || c == '.') out = '_';
    if (!out) continue;
    if (out == '_') {
      if (last_sep || w == 0) continue;
      last_sep = true;
    } else {
      last_sep = false;
    }
    dst[w++] = out;
  }
  while (w > 0 && dst[w - 1] == '_') --w;
  dst[w] = '\0';
  if (w == 0) {
    std::snprintf(dst, dst_size, "%s", fallback ? fallback : "SESSIONE");
  }
}

static inline void normalize_date_file_(
    const char *src, char *dst, size_t dst_size) {
  if (!dst || dst_size == 0) return;
  unsigned a = 0, b = 0, c = 0;
  if (src && std::sscanf(src, "%u/%u/%u", &a, &b, &c) == 3) {
    // DD/MM/YYYY -> YYYYMMDD
    std::snprintf(dst, dst_size, "%04u%02u%02u", c, b, a);
    return;
  }
  if (src && std::sscanf(src, "%u-%u-%u", &a, &b, &c) == 3) {
    // YYYY-MM-DD -> YYYYMMDD
    std::snprintf(dst, dst_size, "%04u%02u%02u", a, b, c);
    return;
  }
  char digits[12]{};
  size_t w = 0;
  for (const char *p = src ? src : ""; *p && w + 1 < sizeof(digits); ++p) {
    if (*p >= '0' && *p <= '9') digits[w++] = *p;
  }
  digits[w] = '\0';
  std::snprintf(dst, dst_size, "%s", w ? digits : "DATA");
}

static inline void normalize_time_file_(
    const char *src, char *dst, size_t dst_size) {
  if (!dst || dst_size == 0) return;

  unsigned h = 0, m = 0, sec = 0;
  if (src && std::sscanf(src, "%u:%u:%u", &h, &m, &sec) == 3) {
    std::snprintf(dst, dst_size, "%02u%02u%02u", h, m, sec);
    return;
  }

  char digits[10]{};
  size_t w = 0;
  for (const char *p = src ? src : ""; *p && w + 1 < sizeof(digits); ++p) {
    if (*p >= '0' && *p <= '9') digits[w++] = *p;
  }
  digits[w] = '\0';

  // Keep HHMMSS when available.
  if (w >= 6) {
    std::snprintf(dst, dst_size, "%.6s", digits);
  } else {
    std::snprintf(dst, dst_size, "%s", w ? digits : "ORA");
  }
}

static inline bool trace_name_matches_id_(
    const char *name, uint32_t session_id) {
  if (!name || session_id == 0) return false;
  char suffix[24];
  std::snprintf(
      suffix, sizeof(suffix), "_S%06lu.CSV",
      static_cast<unsigned long>(session_id));
  const size_t n = std::strlen(name);
  const size_t s = std::strlen(suffix);
  if (n >= s && strcasecmp(name + n - s, suffix) == 0) return true;

  char legacy[24];
  std::snprintf(
      legacy, sizeof(legacy), "S%06lu.CSV",
      static_cast<unsigned long>(session_id));
  return strcasecmp(name, legacy) == 0;
}

// Map the archive's numeric session ID to its short progressive CSV name.
static inline bool trace_map_path_(uint32_t id, char *out, size_t out_size) {
  char path[64];
  std::snprintf(path, sizeof(path), "0:/GOATS/M%06lu.TRC", (unsigned long)id);
  FIL f{};
  if (f_open(&f, path, FA_READ) != FR_OK) return false;
  char buf[64]{};
  UINT count=0;
  const FRESULT fr=f_read(&f,buf,sizeof(buf)-1,&count);
  (void)f_close(&f);
  if(fr!=FR_OK || count<5) return false;
  buf[count]=0;
  // Store the entire short path, not arbitrary user-supplied paths.
  if(std::strncmp(buf,"0:/GOATS/",9)!=0 ||
     std::strstr(buf,"..")!=nullptr) return false;
  FILINFO info{};
  if(f_stat(buf,&info)!=FR_OK) return false;
  std::snprintf(out,out_size,"%s",buf);
  return true;
}
static inline bool save_trace_map_(uint32_t id, const char *path) {
  goats_diag_v1021::SdScope diag_scope(goats_diag_v1021::SdKind::METADATA);
  char filename[64];
  std::snprintf(filename,sizeof(filename),"0:/GOATS/M%06lu.TRC",(unsigned long)id);
  FIL f{};
  if(f_open(&f,filename,FA_WRITE|FA_CREATE_ALWAYS)!=FR_OK)return false;
  UINT written=0;
  const UINT len=(UINT)std::strlen(path);
  const FRESULT fr=f_write(&f,path,len,&written);
  const FRESULT sync=(fr==FR_OK && written==len)?f_sync(&f):FR_DISK_ERR;
  (void)f_close(&f);
  return sync==FR_OK;
}

static inline bool resolve_trace_path(
    uint32_t session_id, char *out, size_t out_size) {
  goats_diag_v1021::SdScope diag_scope(goats_diag_v1021::SdKind::READ);
  if (!out || out_size == 0 || session_id == 0) return false;

  // Progressive names need an explicit ID-to-name mapping.
  if (trace_map_path_(session_id, out, out_size)) return true;

  // Fast legacy path first.
  char legacy[64];
  std::snprintf(
      legacy, sizeof(legacy), "0:/GOATS/S%06lu.CSV",
      static_cast<unsigned long>(session_id));
  FILINFO st{};
  if (f_stat(legacy, &st) == FR_OK) {
    std::snprintf(out, out_size, "%s", legacy);
    return true;
  }

  FF_DIR dir{};
  FILINFO info{};
  if (f_opendir(&dir, "0:/GOATS") != FR_OK) return false;
  bool found = false;
  while (true) {
    const FRESULT fr = f_readdir(&dir, &info);
    if (fr != FR_OK || info.fname[0] == 0) break;
    if (info.fattrib & AM_DIR) continue;
    if (trace_name_matches_id_(info.fname, session_id)) {
      std::snprintf(out, out_size, "0:/GOATS/%s", info.fname);
      found = true;
      break;
    }
  }
  (void) f_closedir(&dir);
  return found;
}

static inline bool is_trace_csv_name_(const char *name) {
  if (!name) return false;
  const size_t n = std::strlen(name);
  if (n < 12) return false;
  if (n >= 4 && strcasecmp(name + n - 4, ".CSV") != 0) return false;
  if (std::strcmp(name, "LIVE.CSV") == 0 ||
      std::strcmp(name, "RECOV.CSV") == 0) return true;
  // TEST25: PPYMMNN.CSV, 8-character FAT basename.
  if (n == 12) {
    const auto alnum=[](char c) {return (c>='A'&&c<='Z') ||
       (c>='a'&&c<='z') || (c>='0'&&c<='9');};
    if(alnum(name[0]) && alnum(name[1]) && name[2]>='0' && name[2]<='9') {
      const char *months[]={"GE","FE","MZ","AP","MG","GI","LG","AG","SE","OT","NO","DI"};
      for(const char *month:months) {
        if(name[3]==month[0] && name[4]==month[1] &&
           name[5]>='0' && name[5]<='9' &&
           name[6]>='0' && name[6]<='9') return true;
      }
    }
  }
  return std::strstr(name, "_S") != nullptr || name[0] == 'S';
}

static inline bool fat_write_all_(FIL *file, const void *data, UINT size) {
  if (!file || !data) return false;
  const uint8_t *p = static_cast<const uint8_t *>(data);
  UINT total = 0;
  while (total < size) {
    UINT written = 0;
    const FRESULT fr = f_write(file, p + total, size - total, &written);
    if (fr != FR_OK) {
      set_fatfs_error_("LIVE_WRITE", fr);
      return false;
    }
    if (written == 0) {
      set_fatfs_error_("LIVE_WRITE_ZERO", FR_DISK_ERR);
      return false;
    }
    total += written;
  }
  return true;
}

static inline bool begin_live_session(
    const char *mode,
    const char *date_text,
    const char *time_text,
    const char *track_name) {
  goats_diag_v1021::SdScope diag_scope(goats_diag_v1021::SdKind::OPEN);
  sanitize_file_part_(
      track_name, g_live_track_file, sizeof(g_live_track_file),
      (mode && std::strcmp(mode, "FREE") == 0)
          ? "REGISTRAZIONE_LIBERA" : "CIRCUITO");
  normalize_date_file_(
      date_text, g_live_date_file, sizeof(g_live_date_file));
  normalize_time_file_(
      time_text, g_live_time_file, sizeof(g_live_time_file));
  if (!g_ready) {
    set_error_("LIVE_NOT_MOUNTED");
    return false;
  }

  // V11.0.2.24: the whole live trace remains on native FatFS.
  // No fopen/fprintf/fflush/fsync/FILE* is used for the recording path.
  if (!g_writable && !write_probe_()) return false;
  if (!ensure_dir_()) return false;

  if (g_live_is_open) {
    (void) f_sync(&g_live);
    (void) f_close(&g_live);
    g_live_is_open = false;
  }

  FRESULT fr = f_open(
      &g_live, "0:/GOATS/LIVE.CSV",
      FA_CREATE_ALWAYS | FA_WRITE);
  if (fr != FR_OK) {
    set_fatfs_error_("LIVE_FAT_OPEN", fr);
    return false;
  }
  g_live_is_open = true;

  char header[384];
  const int n = std::snprintf(
      header, sizeof(header),
      "# GOATS RT V11.0.2.24 FULL TRACE 25Hz\n"
      "# mode=%s,date=%s,time=%s,track=%s\n"
      "elapsed_ms,lap,latitude,longitude,speed_kmh,hdop,satellites\n",
      mode ? mode : "",
      date_text ? date_text : "",
      time_text ? time_text : "",
      track_name ? track_name : "");

  if (n <= 0 || static_cast<size_t>(n) >= sizeof(header) ||
      !fat_write_all_(&g_live, header, static_cast<UINT>(n))) {
    (void) f_close(&g_live);
    g_live_is_open = false;
    if (g_last_fresult == FR_OK) set_fatfs_error_("LIVE_HEADER", FR_INT_ERR);
    return false;
  }

  fr = f_sync(&g_live);
  if (fr != FR_OK) {
    (void) f_close(&g_live);
    g_live_is_open = false;
    set_fatfs_error_("LIVE_HEADER_SYNC", fr);
    return false;
  }

  g_live_points = 0;
  g_flush_counter = 0;
  set_ok_("LIVE_FAT_OPEN");
  return true;
}

static inline void append_live_point(
    uint32_t elapsed_ms,
    uint32_t lap,
    double latitude,
    double longitude,
    float speed_kmh,
    float hdop,
    int satellites) {
  goats_diag_v1021::SdScope diag_scope(goats_diag_v1021::SdKind::POINT);
  if (!g_ready || !g_live_is_open) return;

  char line[192];
  const int n = std::snprintf(
      line, sizeof(line),
      "%lu,%lu,%.7f,%.7f,%.1f,%.2f,%d\n",
      static_cast<unsigned long>(elapsed_ms),
      static_cast<unsigned long>(lap),
      latitude,
      longitude,
      speed_kmh,
      hdop,
      satellites);

  if (n <= 0 || static_cast<size_t>(n) >= sizeof(line) ||
      !fat_write_all_(&g_live, line, static_cast<UINT>(n))) {
    // Stop further writes after a real FatFS error instead of risking a crash.
    (void) f_close(&g_live);
    g_live_is_open = false;
    if (g_last_fresult == FR_OK) set_fatfs_error_("LIVE_FORMAT", FR_INT_ERR);
    return;
  }

  ++g_live_points;
  goats_diag_v1021::increment(&goats_diag_v1021::Counters::csv_points);
  if (++g_flush_counter >= 25) {
    goats_diag_v1021::SdScope diag_sync(goats_diag_v1021::SdKind::SYNC);
    const FRESULT fr = f_sync(&g_live);  // circa una volta al secondo a 25 Hz
    if (fr != FR_OK) {
      (void) f_close(&g_live);
      g_live_is_open = false;
      set_fatfs_error_("LIVE_SYNC", fr);
      return;
    }
    g_flush_counter = 0;
  }
}

// V11.0.2.55: chiusura senza archiviazione della sessione corrente.
static inline void discard_live_session() {
  goats_diag_v1021::SdScope diag_scope(goats_diag_v1021::SdKind::FINALIZE);
  if (g_live_is_open) {
    (void) f_close(&g_live);
    g_live_is_open = false;
  }
  if (g_ready) (void) f_unlink("0:/GOATS/LIVE.CSV");
  g_live_points = 0;
}

// Exact RLCD TEST25 PPYMMNN.CSV naming convention.
static inline bool progressive_trace_name_(char *out, size_t out_size) {
  if(!out || out_size<32 || std::strlen(g_live_date_file)!=8) return false;
  const char *d=g_live_date_file;
  for(int i=0;i<8;i++) if(d[i]<'0'||d[i]>'9') return false;
  const unsigned month=(unsigned)(d[4]-'0')*10u+(unsigned)(d[5]-'0');
  static const char *months[]={"GE","FE","MZ","AP","MG","GI","LG","AG","SE","OT","NO","DI"};
  if(month<1||month>12) return false;
  char a='A',b='U'; unsigned count=0;
  for(const char *c=g_live_track_file;*c && count<2;c++) {
    char ch=*c;
    if(ch>='a'&&ch<='z') ch=(char)(ch-32);
    if((ch>='A'&&ch<='Z')||(ch>='0'&&ch<='9')) {
      if(count==0)a=ch; else b=ch;
      count++;
    }
  }
  for(unsigned i=1;i<=99;i++) {
    std::snprintf(out,out_size,"0:/GOATS/%c%c%c%s%02u.CSV",
                  a,b,d[3],months[month-1],i);
    FILINFO info{};
    const FRESULT fr=f_stat(out,&info);
    if(fr==FR_NO_FILE || fr==FR_NO_PATH) return true;
    if(fr!=FR_OK) return false;
  }
  return false;
}

static inline bool finish_live_session(uint32_t session_id) {
  goats_diag_v1021::SdScope diag_scope(goats_diag_v1021::SdKind::FINALIZE);
  if (!g_live_is_open) {
    set_fatfs_error_("LIVE_NOT_OPEN", FR_INVALID_OBJECT);
    return false;
  }

  FRESULT fr = f_close(&g_live);
  g_live_is_open = false;
  if (fr != FR_OK) {
    set_fatfs_error_("LIVE_CLOSE", fr);
    return false;
  }

  const TCHAR *live_name = "0:/GOATS/LIVE.CSV";

  if (session_id == 0) {
    const TCHAR *failed = "0:/GOATS/RECOV.CSV";
    (void) f_unlink(failed);
    fr = f_rename(live_name, failed);
    if (fr != FR_OK) {
      set_fatfs_error_("LIVE_RECOVER_RENAME", fr);
      return false;
    }
    set_ok_("LIVE_RECOVERED");
    return true;
  }

  char final_name[144]{};
  if (!progressive_trace_name_(final_name,sizeof(final_name))) {
    // Preserve unique numeric fallback when date is not yet available.
    for(unsigned i=0;i<1000000;i++) {
      const unsigned id=(unsigned)((session_id+i)%1000000UL);
      std::snprintf(final_name,sizeof(final_name),"0:/GOATS/S%06u.CSV",id);
      FILINFO existing{};
      const FRESULT st=f_stat(final_name,&existing);
      if(st==FR_NO_FILE || st==FR_NO_PATH) break;
      if(st!=FR_OK || i==999999) {
        set_fatfs_error_("TRACE_NO_NAME",st); return false;
      }
    }
  }
  // Never unlink or overwrite an existing CSV.
  fr = f_rename(live_name,final_name);
  if(fr!=FR_OK) {
    set_fatfs_error_("LIVE_RENAME",fr); return false;
  }
  if(!save_trace_map_(session_id,final_name)) {
    set_fatfs_error_("TRACE_MAP_WRITE",FR_DISK_ERR); return false;
  }

  FILINFO info{};
  fr = f_stat(final_name, &info);
  if (fr != FR_OK) {
    set_fatfs_error_("LIVE_FINAL_STAT", fr);
    return false;
  }
  if (info.fsize == 0) {
    set_fatfs_error_("LIVE_FINAL_EMPTY", FR_INT_ERR);
    return false;
  }

  set_ok_("LIVE_SAVED");
  return true;
}

static inline size_t live_points() {
  return static_cast<size_t>(g_live_points);
}

static inline bool live_open() {
  return g_live_is_open;
}


struct SavedTraceRow {
  uint32_t elapsed_ms{0};
  uint32_t lap{0};
  double latitude{0.0};
  double longitude{0.0};
  float speed_kmh{0.0f};
  float hdop{0.0f};
  int satellites{0};
};

// V11.0.2.40: reload the complete 25 Hz trace saved on SD so the USB
// session archive can include all points, not only the capped RAM buffer.
template<typename Visitor>
static inline bool visit_saved_trace(
    uint32_t session_id,
    Visitor &&visitor,
    size_t max_rows = 65535) {
  goats_diag_v1021::SdScope diag_scope(goats_diag_v1021::SdKind::READ);
  if (!g_ready || session_id == 0 || max_rows == 0) return false;

  char name[160];
  if (!resolve_trace_path(session_id, name, sizeof(name))) {
    set_fatfs_error_("TRACE_EXPORT_NOT_FOUND", FR_NO_FILE);
    return false;
  }

  FIL file{};
  FRESULT fr = f_open(&file, name, FA_READ);
  if (fr != FR_OK) {
    set_fatfs_error_("TRACE_EXPORT_OPEN", fr);
    return false;
  }

  // V11.0.2.40:
  // - parse the CSV as a stream (no large SavedTraceRow vector);
  // - yield after every FatFS block so the ESP32 task watchdog is serviced.
  char io_buf[512];
  char line[224];
  size_t line_len = 0;
  size_t accepted = 0;
  bool read_error = false;

  auto consume_line = [&](const char *text) {
    if (accepted >= max_rows || text[0] == '\0' || text[0] == '#') return;
    if (std::strncmp(text, "elapsed_ms,", 11) == 0) return;

    unsigned long elapsed = 0, lap = 0;
    double lat = 0.0, lon = 0.0;
    float speed = 0.0f, hdop = 0.0f;
    int satellites = 0;
    const int parsed = std::sscanf(
        text, "%lu,%lu,%lf,%lf,%f,%f,%d",
        &elapsed, &lap, &lat, &lon, &speed, &hdop, &satellites);
    if (parsed != 7) return;

    SavedTraceRow row;
    row.elapsed_ms = static_cast<uint32_t>(elapsed);
    row.lap = static_cast<uint32_t>(lap);
    row.latitude = lat;
    row.longitude = lon;
    row.speed_kmh = speed;
    row.hdop = hdop;
    row.satellites = satellites;

    visitor(row);
    ++accepted;
  };

  while (accepted < max_rows) {
    UINT bytes_read = 0;
    fr = f_read(&file, io_buf, sizeof(io_buf), &bytes_read);
    if (fr != FR_OK) {
      set_fatfs_error_("TRACE_EXPORT_READ", fr);
      read_error = true;
      break;
    }
    if (bytes_read == 0) break;

    for (UINT i = 0; i < bytes_read && accepted < max_rows; ++i) {
      const char c = io_buf[i];
      if (c == '\r') continue;

      if (c == '\n') {
        line[line_len] = '\0';
        consume_line(line);
        line_len = 0;
      } else if (line_len + 1 < sizeof(line)) {
        line[line_len++] = c;
      } else {
        // Corrupt/oversized line: discard until the next newline.
        line_len = 0;
      }
    }

    // Important: reading/parsing thousands of points in one synchronous USB
    // command otherwise starves ESPHome/FreeRTOS and can reset the laptimer.
    delay(1);
  }

  if (!read_error && line_len > 0 && accepted < max_rows) {
    line[line_len] = '\0';
    consume_line(line);
  }

  const FRESULT close_fr = f_close(&file);
  if (close_fr != FR_OK) {
    set_fatfs_error_("TRACE_EXPORT_CLOSE", close_fr);
    return false;
  }
  if (read_error) return false;

  if (accepted == 0) {
    set_fatfs_error_("TRACE_EXPORT_EMPTY", FR_NO_FILE);
    return false;
  }

  set_ok_("TRACE_EXPORT_OK");
  return true;
}

// Compatibility helper retained for diagnostics/other callers.
// The USB session exporter uses visit_saved_trace() directly to avoid
// allocating a second full copy of the trace in RAM.
static inline bool read_saved_trace(
    uint32_t session_id,
    std::vector<SavedTraceRow> &rows,
    size_t max_rows = 65535) {
  rows.clear();
  const size_t initial_reserve = std::min<size_t>(max_rows, 4096);
  rows.reserve(initial_reserve);
  return visit_saved_trace(
      session_id,
      [&](const SavedTraceRow &row) {
        rows.push_back(row);
      },
      max_rows);
}

static inline void remove_trace(uint32_t session_id) {
  goats_diag_v1021::SdScope diag_scope(goats_diag_v1021::SdKind::METADATA);
  if (!g_ready || session_id == 0) return;
  char name[160];
  if (resolve_trace_path(session_id, name, sizeof(name))) {
    (void) f_unlink(name);
  }
  std::snprintf(name,sizeof(name),"0:/GOATS/M%06lu.TRC",(unsigned long)session_id);
  (void) f_unlink(name);
}

static inline void clear_session_files() {
  goats_diag_v1021::SdScope diag_scope(goats_diag_v1021::SdKind::METADATA);
  if (!g_ready) return;

  FF_DIR dir{};
  FILINFO info{};
  if (f_opendir(&dir, "0:/GOATS") != FR_OK) return;

  std::vector<std::string> names;
  while (true) {
    FRESULT fr = f_readdir(&dir, &info);
    if (fr != FR_OK || info.fname[0] == 0) break;
    if (info.fattrib & AM_DIR) continue;
    if (is_trace_csv_name_(info.fname) || info.fname[0] == 'M' ||
        std::strcmp(info.fname, "ARCHIVE.GSA") == 0) {
      names.emplace_back(info.fname);
    }
  }
  f_closedir(&dir);

  for (const auto &n : names) {
    const std::string full = std::string("0:/GOATS/") + n;
    (void) f_unlink(full.c_str());
  }
}


static inline void release_for_shutdown() {
  goats_diag_v1021::SdScope diag_scope(goats_diag_v1021::SdKind::FINALIZE);
  if (g_live_is_open) {
    (void) f_sync(&g_live);
    (void) f_close(&g_live);
    g_live_is_open = false;
  }
  if (g_card != nullptr) {
    esp_vfs_fat_sdcard_unmount(MOUNT_POINT, g_card);
    g_card = nullptr;
  }
  (void) spi_bus_free(SPI3_HOST);
  gpio_pullup_dis(GPIO_NUM_10); gpio_pulldown_dis(GPIO_NUM_10);
  gpio_pullup_dis(GPIO_NUM_11); gpio_pulldown_dis(GPIO_NUM_11);
  gpio_pullup_dis(GPIO_NUM_12); gpio_pulldown_dis(GPIO_NUM_12);
  gpio_pullup_dis(GPIO_NUM_13); gpio_pulldown_dis(GPIO_NUM_13);
  gpio_set_direction(GPIO_NUM_10, GPIO_MODE_INPUT);
  gpio_set_direction(GPIO_NUM_11, GPIO_MODE_INPUT);
  gpio_set_direction(GPIO_NUM_12, GPIO_MODE_INPUT);
  gpio_set_direction(GPIO_NUM_13, GPIO_MODE_INPUT);
  g_ready = false;
}

}  // namespace goats_sd_storage
