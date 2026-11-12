#pragma once
#include <cstdio>
extern unsigned log_lines;
// Validate printf argument types as well as the report guard.
#define ESP_LOGW(tag, format, ...) do { char b[512]; std::snprintf(b, sizeof(b), format, __VA_ARGS__); ++log_lines; } while (false)
