#pragma once
#include <string>
#include <vector>
#include <optional>
#include <iosfwd>
#include <iostream>

typedef std::vector<std::vector<int>> Matrix;

struct Graph
{
    int n = 0;
    Matrix A;
};

std::pair<Graph, Graph> read_input_file(const std::string &path);

void print_result(const Graph &G,
                  const Graph &H,
                  const Matrix &extension,
                  std::ostream &out = std::cout,
                  bool enableColor = true);
