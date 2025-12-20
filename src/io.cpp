#include "io.h"
#include <fstream>
#include <stdexcept>
#include <sstream>
#include <iostream>

#ifndef _WIN32
#include <unistd.h>
#endif

#ifdef _WIN32
#include <windows.h>
#endif

static Graph read_single_graph(std::ifstream &in)
{
    Graph G;

    std::string line;

    while (std::getline(in, line))
    {
        if (!line.empty())
            break;
    }
    if (line.empty())
        throw std::runtime_error("Unexpected end of file while reading vertex count.");

    std::istringstream iss(line);
    if (!(iss >> G.n) || G.n <= 0)
        throw std::runtime_error("Invalid vertex count in input.");

    G.A.assign(G.n, std::vector<int>(G.n, 0));

    for (int i = 0; i < G.n; ++i)
    {
        if (!std::getline(in, line))
            throw std::runtime_error("Not enough rows for adjacency matrix.");

        std::istringstream row(line);
        for (int j = 0; j < G.n; ++j)
        {
            if (!(row >> G.A[i][j]))
                throw std::runtime_error("Malformed adjacency matrix row.");
        }
    }

    return G;
}

std::pair<Graph, Graph> read_input_file(const std::string &path)
{
    std::ifstream in(path);
    if (!in.is_open())
    {
        throw std::runtime_error("Cannot open input file: " + path);
    }

    Graph G1 = read_single_graph(in);
    Graph G2 = read_single_graph(in);

    return {G1, G2};
}

#ifdef _WIN32
static bool enable_virtual_terminal_colors()
{
    HANDLE handle = GetStdHandle(STD_OUTPUT_HANDLE);
    if (handle == INVALID_HANDLE_VALUE)
    {
        return false;
    }

    DWORD mode = 0;
    if (!GetConsoleMode(handle, &mode))
    {
        return false;
    }

    if (mode & ENABLE_VIRTUAL_TERMINAL_PROCESSING)
    {
        return true;
    }

    return SetConsoleMode(handle, mode | ENABLE_VIRTUAL_TERMINAL_PROCESSING);
}
#endif

void print_result(const Graph &G,
                  const Graph &H,
                  const Matrix &extension,
                  std::ostream &out,
                  bool enableColor)
{
    if (static_cast<int>(extension.size()) != H.n)
    {
        throw std::runtime_error("Extension matrix dimensions must match graph H.");
    }
    for (const auto &row : extension)
    {
        if (static_cast<int>(row.size()) != H.n)
        {
            throw std::runtime_error("Extension matrix dimensions must match graph H.");
        }
    }

    Graph extendedH = H;
    long long cost = 0;

    for (int i = 0; i < H.n; ++i)
    {
        for (int j = 0; j < H.n; ++j)
        {
            extendedH.A[i][j] += extension[i][j];
            cost += extension[i][j];
        }
    }

    bool colorEnabled = enableColor && (&out == &std::cout);
#ifdef _WIN32
    if (colorEnabled)
    {
        colorEnabled = enable_virtual_terminal_colors();
    }
#else
    if (colorEnabled)
    {
        colorEnabled = ::isatty(::fileno(stdout));
    }
#endif

    auto print_matrix = [&](const Matrix &M, bool highlight)
    {
        for (int i = 0; i < H.n; ++i)
        {
            for (int j = 0; j < H.n; ++j)
            {
                bool added = highlight && extension[i][j] > 0;
                if (colorEnabled && added)
                {
                    out << "\x1b[31m" << M[i][j] << "\x1b[0m";
                }
                else
                {
                    out << M[i][j];
                }
                if (j + 1 < H.n)
                {
                    out << ' ';
                }
            }
            out << "\n";
        }
    };

    out << "Input:\n";
    out << "G:\n";
    print_matrix(G.A, false);
    out << "H:\n";
    print_matrix(H.A, false);

    out << "Extension of H:\n";
    print_matrix(extendedH.A, true);

    out << "Metric: " << cost << "\n";
}
