#include "io.h"
#include <fstream>
#include <stdexcept>
#include <sstream>

static Graph read_single_graph(std::ifstream& in) {
    Graph G;

    std::string line;

    while (std::getline(in, line)) {
        if (!line.empty()) break;
    }
    if (line.empty())
        throw std::runtime_error("Unexpected end of file while reading vertex count.");

    std::istringstream iss(line);
    if (!(iss >> G.n) || G.n <= 0)
        throw std::runtime_error("Invalid vertex count in input.");

    G.A.assign(G.n, std::vector<int>(G.n, 0));

    for (int i = 0; i < G.n; ++i) {
        if (!std::getline(in, line))
            throw std::runtime_error("Not enough rows for adjacency matrix.");

        std::istringstream row(line);
        for (int j = 0; j < G.n; ++j) {
            if (!(row >> G.A[i][j]))
                throw std::runtime_error("Malformed adjacency matrix row.");
        }
    }

    return G;
}

std::pair<Graph, Graph> read_input_file(const std::string& path) {
    std::ifstream in(path);
    if (!in.is_open()) {
        throw std::runtime_error("Cannot open input file: " + path);
    }

    Graph G1 = read_single_graph(in);
    Graph G2 = read_single_graph(in);

    return {G1, G2};
}
