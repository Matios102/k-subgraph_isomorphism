#pragma once
#include <string>
#include <vector>
#include <optional>

typedef std::vector<std::vector<int>> Matrix;

struct Graph {
    int n = 0;
    Matrix A;
};

std::pair<Graph, Graph> read_input_file(const std::string& path);
