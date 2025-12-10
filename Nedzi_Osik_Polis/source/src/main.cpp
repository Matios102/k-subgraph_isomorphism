#include <iostream>
#include <string>
#include <optional>

#include "exact.h"
#include "approx.h"

enum class Mode {
    Exact,
    Approx
};

static void print_usage(const char* progName) {
    std::cerr << "Usage: " << progName
              << " [exact|approx] [k] [input path] <output path>\n";
}

int main(int argc, char* argv[]) {
    if (argc < 4 || argc > 5) {
        print_usage(argv[0]);
        return 1;
    }

    const std::string modeStr   = argv[1];
    int k = std::stoi(argv[2]);
    const std::string inputPath = argv[3];
    std::optional<std::string> outputPath =
        (argc == 5) ? std::optional<std::string>(argv[4]) : std::nullopt;

    Mode mode;
    if (modeStr == "exact") {
        mode = Mode::Exact;
    } else if (modeStr == "approx") {
        mode = Mode::Approx;
    } else {
        std::cerr << "Unknown mode: " << modeStr << "\n";
        print_usage(argv[0]);
        return 1;
    }

    try {
        switch (mode) {
            case Mode::Exact:
                run_exact_algorithm(inputPath, outputPath, k);
                break;
            case Mode::Approx:
                run_approx_algorithm(inputPath, outputPath, k);
                break;
        }
    } catch (const std::exception& ex) {
        std::cerr << "Error: " << ex.what() << "\n";
        return 1;
    } catch (...) {
        std::cerr << "Unknown error.\n";
        return 1;
    }

    return 0;
}
