#pragma once
#include <string>
#include <vector>
#include <optional>

struct Graph {
    int n = 0;
    std::vector<std::vector<int>> A;
};

std::pair<Graph, Graph> read_input_file(const std::string& path);
