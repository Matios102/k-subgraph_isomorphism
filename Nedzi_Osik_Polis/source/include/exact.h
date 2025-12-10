#pragma once
#include <optional>
#include <string>
#include "io.h"

void run_exact_algorithm(const std::string &inputPath,
                         const std::optional<std::string> &outputPath,
                         int k);
